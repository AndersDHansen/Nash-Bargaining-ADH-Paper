import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from omegaconf import OmegaConf
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .utils import cvar_left, get_logger

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
        # Base case: the large Buyer (load_scale 1.0). Folders under results/sensitivity.
        self.exp_bl, self.exp_pap = "baseload_large_buyer", "pap_large_buyer"
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
                "savefig.pad_inches": 0.02,  # tight crop without the 0.1 in default margin
                "pdf.fonttype": 42,  # TrueType, not Type 3: required by most journals
                "ps.fonttype": 42,
            }
        )

    def plot_all_figures(self) -> None:
        """Plot every figure in the paper."""
        log.info("Plotting all figures for the paper")
        self.case_study_summary()
        self.toy_barter_set()
        self.barter_set()
        self.risk_preferences()
        self.joint_surplus()
        self.bargaining_power()
        self.strike_vs_size()
        self.earnings()
        self.surplus_parts()
        self.buyer_size()
        self.price_beliefs()

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
        label(axs[1], q[0, 4], "Load", c.buyer, above=True)
        axs[1].set_ylabel("Energy [GWh/yr]")

        q = band(axs[2], "capture_rate", c.generator)
        label(axs[2], q[0, 4], "Generator", c.generator, above=True)
        q = band(axs[2], "load_capture_rate", c.buyer)
        label(axs[2], q[0, 4], "Load", c.buyer, above=True)
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
        axs[1].set_ylim(60, 180)
        axs[1].set_yticks([60, 90, 120, 150, 180])
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

    def barter_set(self):
        """Section 4.2 - barter set of the base case in the surplus plane, zoomed on it:
        baseload (top), PAP (bottom), in the layout of Anders' figure.

        Dark and light blue: the contracts at the strike bounds 40 and 200
        EUR/MWh as the quantity grows from zero; both start at the disagreement point, since
        zero quantity gives zero surplus. Red: the contracts at the agreed quantity (M* or
        gamma*) for every strike, dashed where one party is worse off; its solid part is the
        frontier of the barter set B (shaded). Circle: the NBS. Colours as in toy_barter_set.

        Surpluses come from the scenarios (Section 2); the agreed contract from the
        risk_aversion sweep at the base case (A_G = A_L = 0.5, tau_L = 0.5). Checked against
        the solver: the first-unit strikes (SR_star, SU_star) and the frontier end points of
        the bargaining_power sweep (tau_L = 0 and 1) are reproduced exactly.
        Needs: risk_aversion sweep for both experiments.
        """
        RED, GREEN, BLUE, CYAN = "#E64B35", "#00A087", "#3C5488", "#4DBBD5"  # toy_barter_set
        rows = [  # experiment, title, quantity column, cap, label of the agreed quantity
            (self.exp_bl, "Baseload", "M_MWh_h", 30.0, "$M^* = {:.2f}$ MW"),
            (self.exp_pap, "Pay-as-produced", "gamma", 1.0, r"$\gamma^* = {:.0f}$"),
        ]
        if not self._available("barter_set", [(e, "risk_aversion") for e, *_ in rows]):
            return None
        sc = self._scenarios()
        p, T = sc["p"], sc["price"].shape[0]
        L, P = sc["price"].sum(0), sc["production"].sum(0)  # price and output summed over years
        gm = (sc["capture_rate"] * sc["price"] * sc["production"]).sum(0)  # Generator merchant
        lim = (-5, 31)  # MEUR

        def root(f):
            """Strike in [40, 200] EUR/MWh at which the increasing function f crosses zero."""
            lo, hi = 40.0, 200.0
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
            return (lo + hi) / 2

        fig, axs = plt.subplots(2, 1, figsize=(self.p.width.single, 4.9), layout="constrained")
        for ax, (exp, title, q_key, cap, label) in zip(axs, rows):
            # base case from the experiment config: the sweep's saved config holds the
            # last grid point (A_G = A_L = 1), not the base case
            e = OmegaConf.load(self.root / "config" / "experiment" / f"{exp}.yaml")
            A_G, A_L = float(e.A_G), float(e.A_L)
            lm = -e.load_scale * (sc["load_capture_rate"] * sc["price"] * sc["load"]).sum(0)
            U = lambda x, A: (1 - A) * (x @ p) + A * cvar_left(x, p, e.alpha)
            d_G, d_L = U(gm, A_G), U(lm, A_L)
            if e.contract_type == "baseload":  # what one MW pays the Generator at strike S
                unit = lambda S: 8.76 * (S / 1e3 * T - L)
            else:  # what the whole output pays the Generator at strike S
                unit = lambda S: S / 1e3 * P - gm
            w = lambda q, S: (U(gm + q * unit(S), A_G) - d_G, U(lm - q * unit(S), A_L) - d_L)

            d = pd.read_csv(self.root / "results" / "sensitivity" / f"{exp}_risk_aversion" / "results_combined.csv")
            r = d[np.isclose(d.A_G, A_G) & np.isclose(d.A_L, A_L)].iloc[0]  # agreed contract
            q_star = r[q_key]
            lo, hi = root(lambda S: w(q_star, S)[0]), root(lambda S: -w(q_star, S)[1])

            for S, colour in ((40.0, BLUE), (200.0, CYAN)):  # strike bounds, quantity 0 to cap
                ax.plot(*np.array([w(q, S) for q in np.linspace(0, cap, 61)]).T, color=colour, lw=1)
            ax.plot(*np.array([w(q_star, S) for S in np.linspace(40, 200, 161)]).T, color=RED, lw=0.8, ls="--")
            front = np.array([w(q_star, S) for S in np.linspace(lo, hi, 60)])
            ax.fill(np.r_[0, front[:, 0]], np.r_[0, front[:, 1]], color=RED, alpha=0.35, lw=0)
            ax.plot(*front.T, color=RED, lw=1.5)
            x, y = front[1]  # label the frontier, just above its upper-left end
            ax.text(x + 0.9, y + 0.9, label.format(q_star), color=RED, rotation=-45, rotation_mode="anchor")
            ax.plot(r.delta_G, r.delta_L, "o", color=GREEN, mfc="white", ms=5, mew=1.2)
            ax.plot(0, 0, "ko", ms=3)  # disagreement point
            ax.axhline(0, color="k", lw=0.4)
            ax.axvline(0, color="k", lw=0.4)
            ticks = [0, 10, 20, 30]
            ax.set(
                xlim=lim, ylim=lim, aspect="equal", xticks=ticks, yticks=ticks, title=title,
                ylabel="Load surplus $w_L$ [MEUR]",
            )
            log.info(
                "barter_set %s: agreed %.3f, accepted strikes %.1f-%.1f, NBS %.2f / %.2f (computed %.2f / %.2f)",
                title, q_star, lo, hi, r.delta_G, r.delta_L, *w(q_star, r.S_EUR_MWh),
            )

        axs[-1].set_xlabel("Generator surplus $w_G$ [MEUR]")  # same axes in both panels
        handles = [
            Patch(color=RED, alpha=0.35, lw=0, label=r"Barter set $\mathbf{B}$"),
            Line2D([], [], color=RED, lw=1.5, label="Agreed quantity"),
            Line2D([], [], color=BLUE, lw=1, label=r"$\underset{\_\!\_}{S}$ = 40 EUR/MWh"),
            Line2D([], [], color=CYAN, lw=1, label=r"$\overline{S}$ = 200 EUR/MWh"),
            Line2D([], [], color=GREEN, marker="o", mfc="white", ls="", ms=5, label="NBS"),
            Line2D([], [], color="k", marker="o", ls="", ms=3, label="Disagreement point"),
        ]
        fig.legend(handles=handles, loc="outside upper center", ncol=3, frameon=False)

        out = self.fig_dir / "barter_set.pdf"
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
            (self.exp_bl, "baseload", "M_MWh_h", "Quantity $M^*$ [MW]"),
            (self.exp_pap, "pap", "gamma", r"Share $\gamma^*$ [-]"),
        ]
        if not self._available(
            "risk_preferences", [(e[0], "risk_aversion") for e in exps]
        ):
            return None
        cmap = LinearSegmentedColormap.from_list(
            "diverging", list(self.p.cmap.diverging)
        )
        cmap.set_bad(self.p.cmap.masked)

        def heat(ax, g, label, vmin=None, vmax=None):
            h = (g.index[1] - g.index[0]) / 2
            ext = [g.columns[0] - h, g.columns[-1] + h, g.index[0] - h, g.index[-1] + h]
            im = ax.imshow(
                g.to_numpy(), origin="lower", extent=ext, aspect="auto", cmap=cmap,
                vmin=vmin, vmax=vmax,
            )
            ax.set_ylabel("Generator risk aversion $A_G$")
            return fig.colorbar(im, ax=ax, label=label)

        figs = []
        for exp, name, qkey, qlabel in exps:
            S = self._get_grid("risk_aversion", exp, "S_EUR_MWh")
            Q = self._get_grid("risk_aversion", exp, qkey)
            Q.loc[0.0, 0.0] = (
                np.nan
            )  # J = 0 at the origin, so the quantity is arbitrary

            fig, axs = plt.subplots(2, 1, figsize=(self.p.width.single, 4.6), sharex=True)
            heat(axs[0], S, "Strike $S^*$ [EUR/MWh]")
            if name == "pap":
                # Fixed 0-1 scale: the share is 1 in every cell, so the panel is one colour
                heat(axs[1], Q, qlabel, vmin=0, vmax=1)
            else:
                cb = heat(axs[1], Q, qlabel)
                # The volume scale runs from the Generator's preferred volume (A_L = 0)
                # to the Buyer's (A_G = 0): label both ends. White mark: the Buyer's
                # expected consumption (Lesia's meeting point 2).
                lo, hi = np.nanmin(Q.to_numpy()), np.nanmax(Q.to_numpy())
                cb.set_ticks([lo, 10, 12, 14, hi], labels=[f"{lo:.1f}", "10", "12", "14", f"{hi:.1f}"])
                sc = self._scenarios()
                ls = OmegaConf.load(
                    self.root / "results" / "sensitivity" / f"{exp}_risk_aversion" / "config.yaml"
                ).experiment.load_scale
                cb.ax.axhline(ls * (sc["load"].mean(0) @ sc["p"]) / 8.76, color="w", lw=1.5)
            axs[-1].set_xlabel("Load risk aversion $A_L$")

            out = self.fig_dir / f"risk_preferences_{name}.pdf"
            fig.savefig(out, bbox_inches="tight")
            log.info("wrote %s", out)
            figs.append(fig)
        return figs

    def joint_surplus(self):
        """Joint surplus W = w_G + w_L over the risk grid: baseload (top), PAP (bottom).

        Lesia's meeting point 11. One colour scale per panel, as in risk_preferences:
        the structures are compared per party (earnings, surplus_parts), not through W.
        The split is not drawn: at tau_L = 0.5 the Generator's share of W is 0.49-0.50
        in every cell, so its map would be one colour. (0, 0) is masked: no risk aversion,
        no value.

        Needs: risk_aversion sweep for both experiments.
        """
        exps = [(self.exp_bl, "Baseload"), (self.exp_pap, "Pay-as-produced")]
        if not self._available(
            "joint_surplus", [(e, "risk_aversion") for e, _ in exps]
        ):
            return None
        cmap = LinearSegmentedColormap.from_list(
            "diverging", list(self.p.cmap.diverging)
        )
        cmap.set_bad(self.p.cmap.masked)

        fig, axs = plt.subplots(
            2, 1, figsize=(self.p.width.single, 4.6), sharex=True, layout="constrained"
        )
        for ax, (exp, title) in zip(axs, exps):
            W = self._get_grid("risk_aversion", exp, "delta_G") + self._get_grid(
                "risk_aversion", exp, "delta_L"
            )
            W.loc[0.0, 0.0] = np.nan
            h = (W.index[1] - W.index[0]) / 2
            ext = [W.columns[0] - h, W.columns[-1] + h, W.index[0] - h, W.index[-1] + h]
            im = ax.imshow(
                W.to_numpy(), origin="lower", extent=ext, aspect="auto", cmap=cmap
            )
            fig.colorbar(im, ax=ax, label="Joint surplus $W$ [MEUR]")
            ax.set_title(title)
            ax.set_ylabel("Generator risk aversion $A_G$")
        axs[-1].set_xlabel("Load risk aversion $A_L$")

        out = self.fig_dir / "joint_surplus.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

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
        exps = [(self.exp_bl, "Baseload"), (self.exp_pap, "Pay-as-produced")]
        if not self._available(
            "bargaining_power", [(e, "bargaining_power") for e, _ in exps]
        ):
            return None
        fig, ax = plt.subplots(figsize=(self.p.width.single, 3.0), layout="constrained")

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
        levels = [
            Line2D([0], [0], color=c, label=f"$A_L$ = {v:.2f}")
            for v, c in zip(a_l, self.p.levels)
        ]
        structures = [
            Line2D([0], [0], color=self.p.colour.neutral, ls=st, label=name)
            for st, (_, name) in zip([self.p.style.baseload, self.p.style.pap], exps)
        ]
        # legend above the plot, filled by column: row 1 = A_L, row 2 = structure
        handles = [levels[0], structures[0], levels[1], structures[1], levels[2]]
        fig.legend(
            handles=handles,
            loc="outside upper center",
            ncol=3,
            frameon=False,
            handlelength=1.5,
            columnspacing=1.0,  # fits the column at 9 pt
        )
        ax.set_xlim(0, 1)
        ax.set_xlabel(r"Load bargaining power $\tau_L$")
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
        the optimal size is drawn for the base-case A_L
        (experiment config).
        The tau_L = 1 lines coincide for all A_L: a Buyer with full power pays the
        Generator's reservation strike, which does not depend on A_L.

        Needs: contract_size and bargaining_power sweeps for both experiments.
        """
        exps = [
            (self.exp_bl, "M_MWh_h", "Contract volume $M$ [MW]"),
            (self.exp_pap, "gamma", r"Contract share $\gamma$ [-]"),
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
        # only the A_L values currently listed in the sweep config are drawn
        shown = list(
            OmegaConf.load(
                self.root / "config" / "sensitivity" / "contract_size.yaml"
            ).A_L.discrete
        )
        styles = {}  # A_L -> line style, collected over both panels for the legend
        for ax, (exp, q, xlabel) in zip(axs, exps):
            # sizes past the point where the band closes have no agreement: NaN rows
            d = read(exp, "contract_size").dropna(subset=[q, "S_EUR_MWh"])
            d = d[np.isclose(d.A_L.to_numpy()[:, None], shown).any(axis=1)]
            taus, a_ls = sorted(d.tau_L.unique()), sorted(d.A_L.unique())
            style = dict(zip(a_ls, list(self.p.level_styles)[-len(a_ls) :]))
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
            opt = bp[
                np.isclose(bp.A_L, float(self.cfg.experiment.A_L))
                & np.isclose(bp.tau_L, 0.5)
            ][q].iloc[0]
            ax.axvline(opt, color=self.p.colour.neutral, ls="--", lw=0.8)
            ax.set_xlim(left=0)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Strike $S$ [EUR/MWh]")
        axs[0].set_ylim(100, 145)
        axs[0].set_yticks(range(100, 146, 5))
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
        """Contracted earnings against each party's risk aversion, and who carries the risk.

        Rows Generator and Buyer (shared y per row), columns baseload and PAP. Three files:
        earnings (against A_L at A_G = 0.5), earnings_ag (against A_G at A_L = 0.5) and
        earnings_wide (both side by side, for a full-width figure). Bands as in the
        case-study figure: weighted P5-P95, P25-P75 and median over the 2000 scenarios.
        Dotted lines: merchant (no-contract) P5, median and P95, which do not depend on
        risk aversion. Earnings are totals over the 20-year tenor. This is the one place
        the structures are compared on levels: earnings are euros against a common
        baseline, the joint gain is not.

        Needs: risk_aversion sweep for both experiments.
        """
        exps = [(self.exp_bl, "Baseload"), (self.exp_pap, "Pay-as-produced")]
        if not self._available("earnings", [(e, "risk_aversion") for e, _ in exps]):
            return None
        c, bd = self.p.colour, self.p.bands
        w = self._scenarios()["p"]
        qs = sorted((*bd.outer, *bd.inner, bd.centre))  # P5, P25, P50, P75, P95
        xlabels = {"A_L": "Load risk aversion $A_L$", "A_G": "Generator risk aversion $A_G$"}
        files = {}

        def slice_pct(exp, key, x_name):
            """Weighted percentiles along x_name ("A_L" or "A_G") with the other risk
            aversion at 0.5; scenarios are the rows."""
            if (exp, key) not in files:
                files[exp, key] = pd.read_csv(
                    self.root / "results" / "sensitivity" / f"{exp}_risk_aversion" / f"{key}.csv",
                    header=[0, 1],
                    index_col=0,
                )
            df = files[exp, key]
            a = {
                "A_G": df.columns.get_level_values(0).astype(float),
                "A_L": df.columns.get_level_values(1).astype(float),
            }
            keep = np.isclose(a["A_G" if x_name == "A_L" else "A_L"], 0.5)
            return a[x_name][keep].to_numpy(), wpct(df.loc[:, keep].to_numpy().T, w, qs)

        handles = [
            Patch(facecolor="0.3", alpha=bd.alpha_outer, label="P5-P95"),
            Patch(facecolor="0.3", alpha=bd.alpha_inner, label="P25-P75"),
            Line2D([0], [0], color="0.3", label="Median"),
            Line2D([0], [0], color=c.neutral, ls=":", label="Merchant P5/P50/P95"),
        ]
        figs = []
        layouts = [("earnings", ["A_L"]), ("earnings_ag", ["A_G"]), ("earnings_wide", ["A_L", "A_G"])]
        for name, xs in layouts:
            wide = len(xs) == 2
            fig, axs = plt.subplots(
                2,
                2 * len(xs),
                figsize=(self.p.width.double, 3.4) if wide else (self.p.width.single, 4.2),
                sharex=True,
                sharey="row",
                layout="constrained",
            )
            for k, x_name in enumerate(xs):
                for j, (exp, title) in enumerate(exps):
                    col = 2 * k + j
                    for i, (party, colour) in enumerate([("G", c.generator), ("L", c.buyer)]):
                        ax = axs[i, col]
                        x, q = slice_pct(exp, f"earnings_{party}", x_name)
                        ax.fill_between(
                            x, q[:, 0], q[:, 4], color=colour, alpha=bd.alpha_outer, lw=0
                        )
                        ax.fill_between(
                            x, q[:, 1], q[:, 3], color=colour, alpha=bd.alpha_inner, lw=0
                        )
                        ax.plot(x, q[:, 2], color=colour)
                        _, m = slice_pct(exp, f"earnings_nc_{party}", x_name)
                        for n in (0, 2, 4):  # merchant P5, median, P95
                            ax.axhline(m[0, n], color=c.neutral, ls=":", lw=0.8)
                    axs[0, col].set_title(title)
                    axs[1, col].set_xlabel(xlabels[x_name])
            axs[0, 0].set_ylabel("Generator earnings [MEUR]")
            axs[1, 0].set_ylabel("Load earnings [MEUR]")
            fig.legend(
                handles=handles, loc="outside upper center", ncol=4 if wide else 2, frameon=False
            )

            out = self.fig_dir / f"{name}.pdf"
            fig.savefig(out, bbox_inches="tight")
            log.info("wrote %s", out)
            figs.append(fig)
        return figs

    def surplus_parts(self):
        """Each party's surplus at the base case, split into a money and a risk part.

        Lesia's meeting points 5 and 7. With U = E - A (E - CVaR), the surplus is exactly
            w_i = (E[x_i] - E[x_i^0]) + A_i [(E - CVaR)(x_i^0) - (E - CVaR)(x_i)],
        the expected payment the party receives plus its risk aversion times the risk the
        contract removes (x_i: earnings with the contract, x_i^0: merchant). Positive parts
        stack upwards, negative ones downwards; the dot is w_i. A_G = A_L = 0.5, tau_L = 0.5.

        Needs: risk_aversion sweep for both experiments.
        """
        exps = [(self.exp_bl, "Baseload"), (self.exp_pap, "PAP")]
        if not self._available(
            "surplus_parts", [(e, "risk_aversion") for e, _ in exps]
        ):
            return None
        a_g = a_l = 0.5
        c = self.p.colour
        p = self._scenarios()["p"]

        def earnings(exp, key):
            """Earnings per scenario at (a_g, a_l) of the risk_aversion sweep."""
            df = pd.read_csv(
                self.root / "results" / "sensitivity" / f"{exp}_risk_aversion" / f"{key}.csv",
                header=[0, 1],
                index_col=0,
            )
            ag = df.columns.get_level_values(0).astype(float)
            al = df.columns.get_level_values(1).astype(float)
            return df.loc[:, np.isclose(ag, a_g) & np.isclose(al, a_l)].to_numpy()[:, 0]

        alpha = float(self.cfg.experiment.alpha)
        risk = lambda x: x @ p - cvar_left(x, p, alpha)  # E - CVaR
        fig, axs = plt.subplots(
            1, 2, figsize=(self.p.width.single, 2.4), sharey=True, layout="constrained"
        )
        parties = [("G", "Generator", c.generator, a_g), ("L", "Load", c.buyer, a_l)]
        for ax, (party, name, colour, A) in zip(axs, parties):
            for j, (exp, label) in enumerate(exps):
                x = earnings(exp, f"earnings_{party}")
                x0 = earnings(exp, f"earnings_nc_{party}")
                money, removed = (x - x0) @ p, A * (risk(x0) - risk(x))
                up = down = 0.0
                for v, shade in ((removed, 1.0), (money, 0.45)):
                    ax.bar(j, v, 0.6, bottom=up if v >= 0 else down, color=colour, alpha=shade, lw=0)
                    up, down = (up + v, down) if v >= 0 else (up, down + v)
                ax.plot(j, money + removed, "o", color="k", ms=3.5)
                log.info(
                    "surplus_parts %s %s: payment %+.2f, risk %+.2f, surplus %.2f MEUR",
                    name, label, money, removed, money + removed,
                )
            ax.axhline(0, color=c.neutral, lw=0.5)
            ax.set_xticks([0, 1], [label for _, label in exps])
            ax.set_title(name)
        axs[0].set_ylabel("Surplus [MEUR]")

        handles = [
            Patch(facecolor="0.3", alpha=0.45, label="Expected payment received"),
            Patch(facecolor="0.3", label=r"$A_i\times$ risk removed"),
            Line2D([], [], color="k", marker="o", ls="", ms=3.5, label="Surplus $w_i$"),
        ]
        fig.legend(handles=handles, loc="outside upper center", ncol=2, frameon=False)

        out = self.fig_dir / "surplus_parts.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def buyer_size(self):
        """Section 4.6 - agreed contract size against the Buyer's risk aversion
        (A_G = 0.5, tau_L = 0.5) for the three Buyer sizes. Top: baseload volume.
        Bottom: PAP share.

        Every line starts at the Generator's preferred size (A_L = 0) and moves towards
        that Buyer's own preferred size: up for the large Buyer, flat for the similar
        one, down for the small one. The large Buyer's PAP share stays at the cap.
        Dotted lines: each Buyer's expected consumption (top, MW) and its consumption
        relative to the plant's output in value (bottom; 2.11 for the large Buyer, above
        the cap, so not drawn).

        Needs: risk_aversion_line sweep for {baseload,pap}_{large,similar,small}_buyer.
        """
        sizes = [  # dark = large, as in the other three-level figures
            ("large", "Large load", self.p.levels[2]),
            ("similar", "Similar load", self.p.levels[1]),
            ("small", "Small load", self.p.levels[0]),
        ]
        rows = [
            ("baseload", "M_MWh_h", "Volume $M^*$ [MW]"),
            ("pap", "gamma", r"Share $\gamma^*$ [-]"),
        ]
        sweeps = [(f"{s}_{n}_buyer", "risk_aversion_line") for s, *_ in rows for n, *_ in sizes]
        if not self._available("buyer_size", sweeps):
            return None

        # Dotted reference per Buyer (Lesia's meeting point 8), for load_scale 1: expected
        # consumption in MW (baseload); consumption over the plant's output in value (PAP),
        # since a share hedges the value of the output, not its energy.
        sc = self._scenarios()
        E = lambda x: x @ sc["p"]
        ref = {
            "baseload": E(sc["load"].mean(0)) / 8.76,
            "pap": E((sc["load_capture_rate"] * sc["price"] * sc["load"]).sum(0))
            / E((sc["capture_rate"] * sc["price"] * sc["production"]).sum(0)),
        }

        fig, axs = plt.subplots(
            2, 1, figsize=(self.p.width.single, 4.2), sharex=True, layout="constrained"
        )
        for ax, (struct, q, ylabel) in zip(axs, rows):
            for size, label, colour in sizes:
                folder = (
                    self.root
                    / "results"
                    / "sensitivity"
                    / f"{struct}_{size}_buyer_risk_aversion_line"
                )
                d = pd.read_csv(folder / "results_combined.csv")
                d = d[np.isclose(d.A_G, 0.5)].sort_values("A_L")
                ax.plot(d.A_L, d[q], color=colour, label=label)
                r = OmegaConf.load(folder / "config.yaml").experiment.load_scale * ref[struct]
                if struct == "baseload" or r <= 1.05:  # large Buyer's PAP ratio is above the cap
                    ax.axhline(r, color=colour, ls=":", lw=1.0)
                log.info("buyer_size %s %s: reference %.2f", struct, size, r)
            ax.set_ylabel(ylabel)
        axs[1].set_xlim(0, 1)
        axs[1].set_xlabel("Load risk aversion $A_L$")
        handles = axs[0].get_legend_handles_labels()[0] + [
            Line2D([], [], color=self.p.colour.neutral, ls=":", lw=1.0, label="Expected consumption")
        ]
        fig.legend(handles=handles, loc="outside upper center", ncol=2, frameon=False)

        out = self.fig_dir / "buyer_size.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def price_beliefs(self):
        """Heterogeneous price beliefs: joint gain and contract size against the gap.

        The belief gap is K_L - K_G (Buyer's minus Generator's shift of the expected
        price, as a fraction of it). The joint gain depends almost only on the gap, so
        each line is the mean over all (K_G, K_L) pairs with that gap and the band
        spans their min and max. Bottom: size as a fraction of its cap (M / 30 MW,
        gamma / 1). Below a gap of about -0.2 no contract is signed; above zero the
        contract becomes a bet both sides expect to win, and the gain is perceived,
        not realised. Gaps limited to [-0.5, 0.5], where every gap has >= 11 pairs.
        Colour alone tells the structures apart, so both lines are solid.

        Needs: asymmetric_info sweep for both experiments.
        """
        blue, red = self.p.cmap.diverging[1], self.p.cmap.diverging[7]
        exps = [
            (self.exp_bl, "Baseload", "M_MWh_h", 30.0, blue),
            (self.exp_pap, "Pay-as-produced", "gamma", 1.0, red),
        ]
        if not self._available(
            "price_beliefs", [(e, "asymmetric_info") for e, *_ in exps]
        ):
            return None

        fig, axs = plt.subplots(
            2, 1, figsize=(self.p.width.single, 4.2), sharex=True, layout="constrained"
        )
        for exp, name, q, cap, colour in exps:
            d = pd.read_csv(
                self.root
                / "results"
                / "sensitivity"
                / f"{exp}_asymmetric_info"
                / "results_combined.csv"
            )
            d["J"] = d.delta_G + d.delta_L
            d["size"] = d[q] / cap
            d["gap"] = (d.K_L_price - d.K_G_price).round(3)
            d = d[d.gap.abs() <= 0.5 + 1e-9]
            g = d.groupby("gap")
            for ax, col in zip(axs, ("J", "size")):
                ax.fill_between(
                    g[col].min().index,
                    g[col].min(),
                    g[col].max(),
                    color=colour,
                    alpha=0.15,
                    lw=0,
                )
                ax.plot(g[col].mean(), color=colour, label=name)

        for ax in axs:
            ax.axvline(0, color=self.p.colour.neutral, lw=0.5)  # common beliefs
        axs[0].set_ylabel("Joint surplus $W$ [MEUR]")
        axs[1].set_ylabel("Contract size / maximum [-]")
        axs[1].set_ylim(0, 1.05)
        axs[1].set_xlim(-0.5, 0.5)
        axs[1].set_xlabel(r"Belief gap $K_L - K_G$ [-]")
        fig.legend(
            *axs[0].get_legend_handles_labels(),
            loc="outside upper center",
            ncol=2,
            frameon=False,
        )

        out = self.fig_dir / "price_beliefs.pdf"
        fig.savefig(out, bbox_inches="tight")
        log.info("wrote %s", out)
        return fig

    def toy_barter_set(self):
        """Section 3.2 - toy barter sets in the three cases, plus two mapping figures.

        One stylised model for both structures. A contract is a quantity x in [0, 1]
        (the cap is 1) and a strike S. The surpluses over the disagreement point are

            w_G(x, S) = x (S - sG) - cG x^2 - k/2 (x S)^2
            w_L(x, S) = x (sL - S) - cL x^2 - k/2 (x S)^2

        - sG, sL: first-unit break-even strikes, so (C1) is sG < sL.
        - cG, cL: each extra unit hedges less, so the value of an extra unit falls.
        - k: risk of the strike payment z = x S. Baseload has k = 0: the strike moves
          money one for one, every constant-quantity line has slope -1 and the barter
          set is a right triangle. PAP has k > 0: the strike multiplies a random output,
          so the lines bend and the barter set has a curved frontier.
        Both surpluses are concave in (x, z), as Theorems 1 and 2 require.

        Needs no results. Own look, agreed for this figure (Nature palette, 7 pt), so the
        rcParams are set locally. Writes barter_set_cases (in the paper), barter_set_map_strike
        and barter_set_map_quantity.
        """
        RED, CYAN, GREEN, BLUE = "#E64B35", "#4DBBD5", "#00A087", "#3C5488"  # NPG colours
        GREY = "0.80"
        SR, SU = 0.15, 0.85  # strike bounds S^R, S^U
        CASES = {  # (sG, sL, cG, cL)
            "Case 1: interior": (0.25, 0.75, 0.30, 0.30),
            "Case 2: no agreement": (0.60, 0.40, 0.30, 0.30),
            "Case 3: cap": (0.20, 0.80, 0.04, 0.04),
        }
        LIMITS = {  # axis range per case
            "Case 1: interior": (-0.053, 0.16),
            "Case 2: no agreement": (-0.053, 0.16),
            "Case 3: cap": (-0.20, 0.60),
        }
        ROWS = {"Baseload": (0.0, "volume $M$"), "PAP": (0.6, r"share $\gamma$")}  # k, x label
        CAP_LABEL = {"Baseload": r"$\overline{M}$", "PAP": "1"}  # label of the quantity cap on the x axis

        def surpluses(x, S, sG, sL, cG, cL, k):
            """Surpluses of the Generator and the Buyer at quantity x and strike S."""
            wG = x * (S - sG) - cG * x**2 - k / 2 * (x * S) ** 2
            wL = x * (sL - S) - cL * x**2 - k / 2 * (x * S) ** 2
            return wG, wL

        def marginal_strikes(x, sG, sL, cG, cL, k):
            """Marginal break-even strikes s_G(x), s_L(x): they solve d w_i / d x = 0,
            a quadratic in S when k > 0."""
            if k == 0:
                return sG + 2 * cG * x, sL - 2 * cL * x
            kx = np.maximum(k * x, 1e-12)
            with np.errstate(invalid="ignore"):  # no real root: no strike makes the unit worth it
                mG = (1 - np.sqrt(1 - 4 * kx * (sG + 2 * cG * x))) / (2 * kx)
                mL = (-1 + np.sqrt(1 + 4 * kx * (sL - 2 * cL * x))) / (2 * kx)
            return mG, mL

        def nash(p, k, tau_G=0.5):
            """Weighted NBS by grid search: (x, S, w_G, w_L), or None if no agreement."""
            X, S = np.meshgrid(np.linspace(0, 1, 401), np.linspace(SR, SU, 401))
            wG, wL = surpluses(X, S, *p, k)
            ok = (wG > 0) & (wL > 0)
            if not ok.any():
                return None
            obj = np.where(
                ok,
                tau_G * np.log(np.where(ok, wG, 1)) + (1 - tau_G) * np.log(np.where(ok, wL, 1)),
                -np.inf,
            )
            i = np.unravel_index(obj.argmax(), obj.shape)
            return X[i], S[i], wG[i], wL[i]

        def surplus_axes(ax, lim):
            """Surplus-plane panel: disagreement point at the origin, equal scales."""
            ax.plot(0, 0, "ko", ms=2.5)
            ax.axhline(0, color="k", lw=0.4)
            ax.axvline(0, color="k", lw=0.4)
            ax.set(xlim=lim, ylim=lim, aspect="equal", xticks=[0], yticks=[0],
                   xlabel="$w_G$", ylabel="$w_L$")

        for row, (k, _) in ROWS.items():  # check: a cap case must give 1 for every bargaining power
            for name, p in CASES.items():
                q = [None if (n := nash(p, k, t)) is None else round(float(n[0]), 3)
                     for t in (0.25, 0.5, 0.75)]
                log.info("%s %s: agreed quantity for tau_G 0.25 / 0.5 / 0.75: %s", row, name, q)

        x = np.linspace(0, 1, 300)
        S = np.linspace(SR, SU, 200)

        with mpl.rc_context():
            mpl.rcdefaults()
            mpl.rcParams.update(
                {
                    "font.family": "sans-serif",
                    "font.sans-serif": list(self.p.font.family),
                    "mathtext.fontset": "custom",
                    "mathtext.rm": "sans",
                    "mathtext.it": "sans:italic",
                    "font.size": 7,
                    "axes.titlesize": 8,
                    "axes.labelsize": 8,
                    "legend.fontsize": 6,
                    "pdf.fonttype": 42,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.linewidth": 0.5,
                }
            )

            # ---- Figure 1: the three cases
            fig, axs = plt.subplots(2, 4, figsize=(7.1, 4.3), layout="constrained")
            fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02, wspace=0, hspace=0)
            for r, (row, (k, xlabel)) in enumerate(ROWS.items()):
                # contract space, Case 1: strike bounds and the two marginal break-even strikes
                ax = axs[r, 0]
                p = CASES["Case 1: interior"]
                mG, mL = marginal_strikes(x, *p, k)
                ax.axhline(SU, color=CYAN, lw=1, label=r"Highest strike $\overline{S}$")
                ax.axhline(SR, color=BLUE, lw=1, label=r"Lowest strike $\underset{\_\!\_}{S}$")
                ax.plot(x, mG, "k", lw=1, label="Generator break-even $s_G(x)$")
                ax.plot(x, mL, "k--", lw=1, label="Load break-even $s_L(x)$")
                ax.set_box_aspect(1)  # square, like the surplus panels
                ax.fill_between(x, mG, mL, where=mL >= mG, color=GREY)  # units that create value
                ax.set(xlim=(0, 1), ylim=(0, 1), xticks=[0, 1], xticklabels=["0", CAP_LABEL[row]],
                       yticks=[], xlabel=xlabel, ylabel=f"{row}\nstrike $S$")
                if r == 0:
                    ax.set_title("Contract space")

                # surplus plane: constant-quantity lines, images of the strike bounds, barter set, NBS
                for c, (name, p) in enumerate(CASES.items(), start=1):
                    ax = axs[r, c]
                    lim = LIMITS[name]
                    env_g = np.linspace(*lim, 900)
                    env = np.full_like(env_g, -np.inf)
                    for xi in np.linspace(0.02, 1, 45):
                        wG, wL = surpluses(xi, S, *p, k)
                        ax.plot(wG, wL, color=GREY, lw=0.6, zorder=0)  # one quantity, strike S^R to S^U
                        env = np.maximum(env, np.interp(env_g, wG, wL, left=-np.inf, right=-np.inf))
                    ax.plot(*surpluses(x, SR, *p, k), color=BLUE, lw=1)  # image of the edge S = S^R
                    ax.plot(*surpluses(x, SU, *p, k), color=CYAN, lw=1)  # image of the edge S = S^U
                    top = np.where(env_g >= 0, np.maximum(env, 0), 0)
                    ax.fill_between(env_g, 0, top, where=top > 0, color=RED, alpha=0.6, lw=0)  # B
                    n = nash(p, k)
                    if n is not None:  # Nash curve: w_G w_L = constant, the highest that touches B
                        g = np.linspace(1e-3, lim[1], 300)
                        ax.plot(g, n[2] * n[3] / g, color=GREEN, lw=1)
                        ax.plot(n[2], n[3], "o", color=GREEN, ms=3.5, mfc="white", mew=0.9)  # NBS
                    surplus_axes(ax, lim)
                    if r == 0:
                        ax.set_title(name)
            handles = axs[0, 0].get_legend_handles_labels()[0] + [
                Line2D([], [], color=GREY, lw=0.8, label="Fixed quantity"),
                Patch(color=RED, alpha=0.6, label=r"Barter set $\mathbf{B}$"),
                Line2D([], [], color=GREEN, lw=1, label="Nash product"),
                Line2D([], [], color=GREEN, marker="o", mfc="white", ls="", ms=3.5, label="NBS"),
            ]
            fig.legend(handles=handles, loc="outside upper center", ncol=4, fontsize=7,
                       frameon=False, borderpad=0.8)
            out = self.fig_dir / "barter_set_cases.pdf"
            fig.savefig(out)
            log.info("wrote %s", out)

            # ---- Figures 2 and 3: how the contract box maps
            # Lines in the contract space (left) and the same lines in the surplus plane (right).
            p, lim = CASES["Case 1: interior"], LIMITS["Case 1: interior"]
            shades = LinearSegmentedColormap.from_list("shades", ["#1B2A4A", BLUE, "#C9D3EA"])
            for what in ("strike", "quantity"):
                fig2, axs = plt.subplots(2, 2, figsize=(3.5, 3.6), layout="constrained")
                for r, (row, (k, xlabel)) in enumerate(ROWS.items()):
                    values = np.linspace(SR, SU, 9) if what == "strike" else np.linspace(0.1, 1, 9)
                    for v, colour in zip(values, shades(np.linspace(0, 1, len(values)))):
                        if what == "strike":  # horizontal line: one strike, every quantity
                            xs, Ss = x, np.full_like(x, v)
                        else:  # vertical line: one quantity, every strike
                            xs, Ss = np.full_like(S, v), S
                        axs[r, 0].plot(xs, Ss, color=colour, lw=1)
                        axs[r, 1].plot(*surpluses(xs, Ss, *p, k), color=colour, lw=1)
                    axs[r, 0].set(xlim=(0, 1), ylim=(0, 1), xticks=[], yticks=[], xlabel=xlabel,
                                  ylabel=f"{row}\nstrike $S$")
                    surplus_axes(axs[r, 1], lim)
                axs[0, 0].set_title("Contract space")
                axs[0, 1].set_title("Surplus plane")
                out = self.fig_dir / f"barter_set_map_{what}.pdf"
                fig2.savefig(out)
                log.info("wrote %s", out)
        return fig

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

    def _scenarios(self):
        """The reduced scenarios as arrays (years x scenarios) and their probabilities p.

        Units of the data files: price in MEUR/GWh, energy in GWh per year. The load is the
        large Buyer's (load_scale 1); scale it by the experiment's load_scale.
        """
        sg = self.cfg.scenario_gen
        n = sg.num_scenarios_reduced
        d = self.root / "data" / "processed" / f"scenarios_reduced_{n}"
        tag = f"reduced_{sg.years}y_{n}s"
        keys = ("price", "production", "capture_rate", "load", "load_capture_rate")
        s = {
            k: pd.read_csv(d / f"{k}_scenarios_{tag}.csv", index_col=0).to_numpy(float)
            for k in keys
        }
        p = pd.read_csv(d / f"probabilities_scenarios_{tag}.csv")["Probability"]
        s["p"] = p.to_numpy(float) / p.sum()
        return s

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
