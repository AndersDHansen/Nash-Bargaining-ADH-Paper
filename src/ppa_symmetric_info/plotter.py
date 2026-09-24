import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .utils import get_logger

log = get_logger(__name__)
# PDF font subsetting logs every step at INFO under Hydra's root logger
logging.getLogger("fontTools").setLevel(logging.WARNING)


def wpct(a, w, qs):
    """Probability-weighted percentiles across the scenario axis (columns).

    The reduced scenarios carry weights spanning ~2 orders of magnitude, so an
    unweighted percentile is wrong, not just imprecise. Returns (periods, len(qs)).
    """
    o = np.argsort(a, axis=1)
    cw = np.cumsum(np.take(w, o), axis=1)
    k = (cw[:, :, None] >= np.asarray(qs) / 100).argmax(axis=1)
    return np.take_along_axis(a, np.take_along_axis(o, k, 1), 1)


class Plotter:
    def __init__(self, cfg):
        self.cfg = cfg
        self.p = cfg.plotting
        self.root = Path(cfg.paths.root)
        self.fig_dir = self.root / "figures"
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self.apply_style()

    def apply_style(self):
        """rcParams shared by every figure. Elsevier allows Arial; 7 pt at final size."""
        f = self.p.font
        mpl.rcParams.update(
            {
                "font.family": "sans-serif",
                "font.sans-serif": list(f.family),
                "font.size": f.size,
                "axes.titlesize": f.size,
                "axes.labelsize": f.size,
                "xtick.labelsize": f.size,
                "ytick.labelsize": f.size,
                "legend.fontsize": f.size,
                "legend.frameon": False,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.linewidth": 0.6,
                "xtick.major.width": 0.6,
                "ytick.major.width": 0.6,
                "lines.linewidth": 1.0,
                "savefig.dpi": self.p.dpi,
                "pdf.fonttype": 42,  # TrueType, not Type 3: required by most journals
                "ps.fonttype": 42,
            }
        )

    def plot_all_figures(self) -> None:
        """Plot every figure in the paper."""
        log.info("Plotting all figures for the paper")
        self.case_study_summary()
        self.bargaining_set()
        self.risk_preferences()
        self.bargaining_power()
        self.strike_vs_size()
        self.earnings()

    def case_study_summary(self):
        """Figure 1 - price, energy and capture-rate bands over the tenor."""
        c, bd = self.p.colour, self.p.bands
        n = self.cfg.scenario_gen.num_scenarios_reduced
        tag = f"reduced_{self.cfg.scenario_gen.years}y_{n}s"
        d = self.root / "data" / "processed" / f"scenarios_reduced_{n}"
        if not (d / f"probabilities_scenarios_{tag}.csv").exists():
            log.warning(
                "case_study skipped: %s not found. Generate the scenarios with: "
                "uv run main.py sensitivity=default",
                d,
            )
            return None

        def read(key, scale=1.0):
            return pd.read_csv(d / f"{key}_scenarios_{tag}.csv", index_col=0) * scale

        # Pale = P5-P95, darker = P25-P75, line = weighted median
        def band(ax, key, colour, scale=1.0):
            qs = (*bd.outer[:1], *bd.inner, bd.centre, *bd.outer[1:])
            q = wpct(read(key, scale).to_numpy(float), w, sorted(qs))
            ax.fill_between(
                years, q[:, 0], q[:, 4], color=colour, alpha=bd.alpha_outer, lw=0
            )
            ax.fill_between(
                years, q[:, 1], q[:, 3], color=colour, alpha=bd.alpha_inner, lw=0
            )
            ax.plot(years, q[:, 2], color=colour)
            return q

        def label(ax, y, text, colour, above):
            ax.annotate(
                text,
                (years[0], y),
                xytext=(1, 3 if above else -3),
                textcoords="offset points",
                color=colour,
                fontsize=self.p.font.size,
                va="bottom" if above else "top",
            )

        w = pd.read_csv(d / f"probabilities_scenarios_{tag}.csv")[
            "Probability"
        ].to_numpy()
        w = w / w.sum()
        years = pd.to_datetime(read("price").index).year.to_numpy()

        fig, axs = plt.subplots(1, 3, figsize=(self.p.width.double, 2.0))

        band(axs[0], "price", c.price, 1e3)
        axs[0].set_ylabel("Price [EUR/MWh]")

        # Share a panel: gap sets the volume ratio
        q = band(axs[1], "production", c.generator)
        label(axs[1], q[0, 4], "Generator", c.generator, above=True)
        q = band(axs[1], "load", c.buyer, float(self.cfg.experiment.load_scale))
        label(axs[1], q[0, 4], "Buyer", c.buyer, above=True)
        axs[1].set_ylabel("Energy [GWh/yr]")

        q = band(axs[2], "capture_rate", c.generator)
        label(axs[2], q[0, 4], "Generator", c.generator, above=True)
        q = band(axs[2], "load_capture_rate", c.buyer)
        label(axs[2], q[0, 4], "Buyer", c.buyer, above=True)
        axs[2].set_ylabel("Capture rate [-]")

        # Set xlim
        for ax in axs:
            ax.set_xlim(years[0], years[-1])
            ax.set_xticks(range(years[0], years[-1] + 1, 5))
            # Set gridlines
            ax.grid(
                linestyle="dashed", alpha=0.2, color="gray", linewidth=0.4, zorder=0
            )

        # Set ylim + yticks (explicit ticks so they land on the bounds, not the
        # nearest "nice" number a locator would pick)
        axs[0].set_ylim(0, 250)
        axs[1].set_ylim(45, 120)
        axs[1].set_yticks([45, 60, 75, 90, 105, 120])
        axs[2].set_ylim(0.6, 1.1)
        axs[2].set_yticks([0.6, 0.7, 0.8, 0.9, 1.0, 1.1])

        # Shared legend for what the shading means (same in every panel)
        handles = [
            Patch(facecolor="0.3", alpha=bd.alpha_outer, label="P5-P95"),
            Patch(facecolor="0.3", alpha=bd.alpha_inner, label="P25-P75"),
            Line2D([0], [0], color="0.3", label="Median"),
        ]
        fig.legend(
            handles=handles,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.5, 1.08),
            frameon=False,
            fontsize=self.p.font.size,
        )

        fig.tight_layout(pad=0.4)
        fig.savefig(self.fig_dir / "case_study.pdf", bbox_inches="tight")
        log.info("wrote %s", self.fig_dir / "case_study.pdf")
        return fig

    def bargaining_set(self):
        """Bargaining set in gain space, one single-column panel per structure.

        Each tau_L of the bargaining_power sweep gives one Nash solution on the
        Pareto frontier, so the (delta_G, delta_L) pairs trace the frontier. The
        shaded area between it and the axes is the bargaining set, the origin is
        the disagreement point, the star is the symmetric solution (tau_L = 0.5)
        and the small markers show tau_L = 0, 0.25, ..., 1. Equal aspect, so the
        slope (-1 baseload, -1.017 PAP) is drawn true. Uses the middle A_L.

        Needs: bargaining_power sweep for both experiments.
        """
        exps = [("default_baseload", "Baseload"), ("default_pap", "Pay-as-produced")]
        if not self._available(
            "bargaining_set", [(e, "bargaining_power") for e, _ in exps]
        ):
            return None

        fig, axs = plt.subplots(
            2, 1, figsize=(self.p.width.single, 5.6), layout="constrained"
        )
        for ax, (exp, title) in zip(axs, exps):
            d = pd.read_csv(
                self.root
                / "results"
                / "sensitivity"
                / f"{exp}_bargaining_power"
                / "results_combined.csv"
            )
            a_l = sorted(d.A_L.unique())
            f = d[np.isclose(d.A_L, a_l[len(a_l) // 2])].sort_values("delta_G")
            dG, dL = f.delta_G.clip(lower=0), f.delta_L.clip(lower=0)

            # bargaining set: origin, then along the frontier
            ax.fill(
                np.r_[0, dG, 0],
                np.r_[0, dL, 0],
                color=self.p.levels[1],
                alpha=0.15,
                lw=0,
            )
            ax.plot(dG, dL, color=self.p.levels[2])
            ticks = f[np.isclose(f.tau_L % 0.25, 0) | np.isclose(f.tau_L % 0.25, 0.25)]
            ax.plot(ticks.delta_G, ticks.delta_L, "o", color=self.p.levels[2], ms=2.5)
            nash = f[np.isclose(f.tau_L, 0.5)]
            ax.plot(nash.delta_G, nash.delta_L, "*", color=self.p.levels[2], ms=8)
            ax.plot(0, 0, "o", color=self.p.colour.neutral, ms=4)

            top = 1.08 * max(dG.max(), dL.max())
            ax.set_xlim(-0.03 * top, top)
            ax.set_ylim(-0.03 * top, top)
            ax.set_aspect("equal")
            ax.set_title(title)
            ax.set_xlabel(r"Generator gain $\Delta_G$ [MEUR]")
            ax.set_ylabel(r"Buyer gain $\Delta_L$ [MEUR]")

        out = self.fig_dir / "bargaining_set.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def risk_preferences(self):
        """Figures 3 and 4 - strike (top) and contracted quantity (bottom) over the
        risk grid, one single-column figure per structure.

        One colourbar per panel: the structures differ by ~30 EUR/MWh and the
        quantities have different units. The diverging map is not centred, so the
        pale middle is the midpoint of each panel's own range; quantity moves only
        x1.12 (M) and x1.22 (gamma), so state the ranges in the caption. The joint
        gain is left out: it is additive, J = A_G*r_G + A_L*r_L, so r_G and r_L go
        in a table instead.

        Needs: risk_aversion sweep for both experiments.
        """
        exps = [
            ("default_baseload", "baseload", "M_MWh_h", "Quantity $M^*$ [MW]"),
            ("default_pap", "pap", "gamma", r"Share $\gamma^*$ [-]"),
        ]
        if not self._available(
            "risk_preferences", [(e[0], "risk_aversion") for e in exps]
        ):
            return None
        cmap = LinearSegmentedColormap.from_list(
            "diverging", list(self.p.cmap.diverging)
        )
        cmap.set_bad(self.p.cmap.masked)

        def heat(ax, g, label):
            h = (g.index[1] - g.index[0]) / 2
            ext = [g.columns[0] - h, g.columns[-1] + h, g.index[0] - h, g.index[-1] + h]
            im = ax.imshow(
                g.to_numpy(), origin="lower", extent=ext, aspect="auto", cmap=cmap
            )
            fig.colorbar(im, ax=ax, label=label)
            ax.set_ylabel("Generator risk aversion $A_G$")

        figs = []
        for exp, name, qkey, qlabel in exps:
            S = self._get_grid("risk_aversion", exp, "S_EUR_MWh")
            Q = self._get_grid("risk_aversion", exp, qkey)
            Q.loc[0.0, 0.0] = (
                np.nan
            )  # J = 0 at the origin, so the quantity is arbitrary

            fig, axs = plt.subplots(
                2, 1, figsize=(self.p.width.single, 4.6), sharex=True
            )
            heat(axs[0], S, "Strike $S^*$ [EUR/MWh]")
            heat(axs[1], Q, qlabel)
            axs[1].set_xlabel("Buyer risk aversion $A_L$")

            out = self.fig_dir / f"risk_preferences_{name}.pdf"
            fig.savefig(out, bbox_inches="tight")
            log.info("wrote %s", out)
            figs.append(fig)
        return figs

    def bargaining_power(self):
        """Strike against the Buyer's bargaining power tau_L.

        One single-column panel: three A_L levels (colour) for both structures
        (line style), A_G fixed by the sweep. The strike is linear in tau_L, from
        the Buyer's reservation strike at tau_L = 0 to the Generator's at
        tau_L = 1, so the lines fan out towards tau_L = 0: the value of bargaining
        power grows with the Buyer's risk aversion. Quantity and joint gain do
        not move with tau_L (baseload exactly, PAP within ~2%), and the
        Generator's share of the gain is 1 - tau_L: say both in the text.

        Needs: bargaining_power sweep for both experiments.
        """
        exps = [("default_baseload", "Baseload"), ("default_pap", "Pay-as-produced")]
        if not self._available(
            "bargaining_power", [(e, "bargaining_power") for e, _ in exps]
        ):
            return None
        fig, ax = plt.subplots(figsize=(self.p.width.single, 2.8))

        for exp, _ in exps:
            d = pd.read_csv(
                self.root
                / "results"
                / "sensitivity"
                / f"{exp}_bargaining_power"
                / "results_combined.csv"
            )
            style = self.p.style.baseload if "baseload" in exp else self.p.style.pap
            for (_, s), c in zip(d.groupby("A_L"), self.p.levels):
                s = s.sort_values("tau_L")
                ax.plot(s.tau_L, s.S_EUR_MWh, ls=style, color=c)

        a_l = sorted(d.A_L.unique())
        handles = [
            Line2D([0], [0], color=c, label=f"$A_L$ = {v:.2f}")
            for v, c in zip(a_l, self.p.levels)
        ] + [
            Line2D([0], [0], color=self.p.colour.neutral, ls=st, label=name)
            for st, (_, name) in zip([self.p.style.baseload, self.p.style.pap], exps)
        ]
        # the empty band between the two structures holds the legend
        ax.legend(handles=handles, ncol=2, loc="center")
        ax.set_xlim(0, 1)
        ax.set_xlabel(r"Buyer bargaining power $\tau_L$")
        ax.set_ylabel("Strike $S^*$ [EUR/MWh]")

        out = self.fig_dir / "bargaining_power.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def strike_vs_size(self):
        """Strike negotiated at a fixed contract size, for three bargaining powers.

        Top baseload (x = M), bottom pay-as-produced (x = gamma), both at A_L of the
        sweep. The tau_L = 0 and tau_L = 1 lines are the Buyer's and the Generator's
        reservation strikes, so the range between them is the range of
        mutually acceptable prices at that size. It narrows with size; under
        baseload it closes (no agreement, NaN rows, dropped), under PAP it is still
        open at gamma = 1. Markers show the sweep grid. The dashed line is
        the optimal size from the bargaining_power sweep at tau_L = 0.5. Colour is
        tau_L, line style A_L, and the shading spans the A_L curves of each tau_L;
        the optimal size is drawn for the middle A_L.
        The tau_L = 1 lines coincide for all A_L: a Buyer with full power pays the
        Generator's reservation strike, which does not depend on A_L.

        Needs: contract_size and bargaining_power sweeps for both experiments.
        """
        exps = [
            ("default_baseload", "M_MWh_h", "Contract volume $M$ [MW]"),
            ("default_pap", "gamma", r"Contract share $\gamma$ [-]"),
        ]
        sweeps = [
            (e, s) for e, *_ in exps for s in ("contract_size", "bargaining_power")
        ]
        if not self._available("strike_vs_size", sweeps):
            return None

        def read(exp, sens):
            return pd.read_csv(
                self.root
                / "results"
                / "sensitivity"
                / f"{exp}_{sens}"
                / "results_combined.csv"
            )

        fig, axs = plt.subplots(
            2, 1, figsize=(self.p.width.single, 4.6), layout="constrained"
        )
        styles = {}  # A_L -> line style, collected over both panels for the legend
        for ax, (exp, q, xlabel) in zip(axs, exps):
            # sizes past the point where the band closes have no agreement: NaN rows
            d = read(exp, "contract_size").dropna(subset=[q, "S_EUR_MWh"])
            taus, a_ls = sorted(d.tau_L.unique()), sorted(d.A_L.unique())
            mid = a_ls[len(a_ls) // 2]  # optimal size shown for this A_L
            style = dict(zip(a_ls, self.p.level_styles if len(a_ls) > 1 else ["-"]))
            styles.update(style)
            for (t, al), s in d.groupby(["tau_L", "A_L"]):
                s = s.sort_values(q)
                ax.plot(
                    s[q], s.S_EUR_MWh, color=self.p.levels[taus.index(t)], ls=style[al]
                )

            # per tau_L, shade the spread across A_L (zero width at tau_L = 1)
            for t, c in zip(taus, self.p.levels):
                pv = d[np.isclose(d.tau_L, t)].pivot_table(
                    index=q, columns="A_L", values="S_EUR_MWh"
                )
                ax.fill_between(
                    pv.index, pv.min(axis=1), pv.max(axis=1), color=c, alpha=0.15, lw=0
                )

            bp = read(exp, "bargaining_power")
            opt = bp[np.isclose(bp.A_L, mid) & np.isclose(bp.tau_L, 0.5)][q].iloc[0]
            ax.axvline(opt, color=self.p.colour.neutral, ls="--", lw=0.8)
            ax.set_xlim(left=0)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Strike $S$ [EUR/MWh]")
        axs[0].set_ylim(100, 140)
        axs[0].set_yticks(range(100, 141, 5))
        axs[1].set_ylim(70, 110)
        axs[1].set_yticks(range(70, 111, 10))

        # legend above the figure: row 1 = tau_L (colour), row 2 = A_L (line style)
        tau_h = [
            Line2D([0], [0], color=c, label=rf"$\tau_L$ = {t:.1f}")
            for t, c in zip(taus, self.p.levels)
        ]
        al_h = [
            Line2D(
                [0],
                [0],
                color=self.p.colour.neutral,
                ls=styles[a],
                label=f"$A_L$ = {a:.2f}",
            )
            for a in sorted(styles)
        ]
        # legend fills by column: row 1 = tau_L, row 2 = A_L, padded with blanks
        # when the counts differ; a single A_L needs no line-style row
        if len(al_h) > 1:
            n = max(len(tau_h), len(al_h))
            blank = Line2D([], [], alpha=0, label=" ")
            tau_h += [blank] * (n - len(tau_h))
            al_h += [blank] * (n - len(al_h))
            handles = [h for pair in zip(tau_h, al_h) for h in pair]
        else:
            handles = tau_h
        ncol = len(handles) // 2 if len(al_h) > 1 else len(handles)
        fig.legend(
            handles=handles, loc="outside upper center", ncol=ncol, frameon=False
        )

        out = self.fig_dir / "strike_vs_size.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def earnings(self):
        """Contracted earnings against A_L at A_G = 0.5, and who carries the risk.

        Rows Generator and Buyer (shared y per row), columns baseload and PAP.
        Bands as in the case-study figure: weighted P5-P95, P25-P75 and median over
        the 2000 scenarios. Dotted lines: merchant (no-contract) P5, median and P95,
        which do not depend on A_L. Earnings are totals over the 20-year tenor.
        This is the one place the structures are compared on levels: earnings are
        euros against a common baseline, the joint gain is not.

        Needs: risk_aversion sweep for both experiments.
        """
        exps = [("default_baseload", "Baseload"), ("default_pap", "Pay-as-produced")]
        if not self._available("earnings", [(e, "risk_aversion") for e, _ in exps]):
            return None
        a_g = 0.5
        c, bd = self.p.colour, self.p.bands
        sg = self.cfg.scenario_gen
        w = pd.read_csv(
            self.root
            / "data"
            / "processed"
            / f"scenarios_reduced_{sg.num_scenarios_reduced}"
            / f"probabilities_scenarios_reduced_{sg.years}y_{sg.num_scenarios_reduced}s.csv"
        )["Probability"].to_numpy()
        w = w / w.sum()
        qs = sorted((*bd.outer, *bd.inner, bd.centre))  # P5, P25, P50, P75, P95

        def slice_pct(exp, key):
            """Weighted percentiles per A_L at A_G = a_g; scenarios are the rows."""
            df = pd.read_csv(
                self.root
                / "results"
                / "sensitivity"
                / f"{exp}_risk_aversion"
                / f"{key}.csv",
                header=[0, 1],
                index_col=0,
            )
            ag = df.columns.get_level_values(0).astype(float)
            al = df.columns.get_level_values(1).astype(float)
            keep = np.isclose(ag, a_g)
            return al[keep].to_numpy(), wpct(df.loc[:, keep].to_numpy().T, w, qs)

        fig, axs = plt.subplots(
            2,
            2,
            figsize=(self.p.width.single, 4.2),
            sharex=True,
            sharey="row",
            layout="constrained",
        )
        for j, (exp, title) in enumerate(exps):
            for i, (party, colour) in enumerate([("G", c.generator), ("L", c.buyer)]):
                ax = axs[i, j]
                x, q = slice_pct(exp, f"earnings_{party}")
                ax.fill_between(
                    x, q[:, 0], q[:, 4], color=colour, alpha=bd.alpha_outer, lw=0
                )
                ax.fill_between(
                    x, q[:, 1], q[:, 3], color=colour, alpha=bd.alpha_inner, lw=0
                )
                ax.plot(x, q[:, 2], color=colour)
                _, m = slice_pct(exp, f"earnings_nc_{party}")
                for k in (0, 2, 4):  # merchant P5, median, P95
                    ax.axhline(m[0, k], color=c.neutral, ls=":", lw=0.8)
            axs[0, j].set_title(title)
            axs[1, j].set_xlabel("Buyer risk aversion $A_L$")
        axs[0, 0].set_ylabel("Generator earnings [MEUR]")
        axs[1, 0].set_ylabel("Buyer earnings [MEUR]")

        handles = [
            Patch(facecolor="0.3", alpha=bd.alpha_outer, label="P5-P95"),
            Patch(facecolor="0.3", alpha=bd.alpha_inner, label="P25-P75"),
            Line2D([0], [0], color="0.3", label="Median"),
            Line2D([0], [0], color=c.neutral, ls=":", label="Merchant P5/P50/P95"),
        ]
        fig.legend(handles=handles, loc="outside upper center", ncol=2, frameon=False)

        out = self.fig_dir / "earnings.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def fig6_price_beliefs(self):
        """Divergent price beliefs.

        Panels: (a) the region of the belief plane where an agreement exists,
        (b) the joint gain against the belief gap K_G - K_L.

        Needs: asymmetric_info sweep for the PAP experiment.
        Message: only the gap matters, not the level, and the gain a gap creates is
        speculative rather than hedging value. Keep it visually separate from the
        risk-transfer gain so the two are never read as additive.
        """
        raise NotImplementedError("fig6_price_beliefs")

    def _available(self, figure, sweeps):
        """True if every (experiment, sweep) result exists; otherwise log how to make it.

        results_combined.csv is written last by run_sensitivity, so its presence
        means the sweep finished. Figures return None when this is False.
        """
        missing = [
            (e, s)
            for e, s in sweeps
            if not (
                self.root
                / "results"
                / "sensitivity"
                / f"{e}_{s}"
                / "results_combined.csv"
            ).exists()
        ]
        for e, s in missing:
            log.warning(
                "%s skipped: results/sensitivity/%s_%s not found. Generate it with: "
                "uv run main.py experiment=%s sensitivity=%s",
                figure,
                e,
                s,
                e,
                s,
            )
        return not missing

    def _get_grid(self, sens, exp, metric):
        df = pd.read_csv(
            self.root
            / "results"
            / "sensitivity"
            / f"{exp}_{sens}"
            / f"grid_{metric}.csv",
            index_col=0,
        )
        df.columns = df.columns.astype(float)

        df.columns = np.round(df.columns, decimals=3)

        df.index = np.round(df.index, decimals=3)
        return df
