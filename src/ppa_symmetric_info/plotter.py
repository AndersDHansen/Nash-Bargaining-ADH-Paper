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
        # self.case_study_summary()
        self.bargaining_set()
        self.risk_preferences()

    def case_study_summary(self):
        """Figure 1 - price, energy and capture-rate bands over the tenor."""
        c, bd = self.p.colour, self.p.bands
        n = self.cfg.scenario_gen.num_scenarios_reduced
        tag = f"reduced_{self.cfg.scenario_gen.years}y_{n}s"
        d = self.root / "data" / "processed" / f"scenarios_reduced_{n}"

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
        """The bargaining set, and what fixes the contracted quantity."""
        fig, axs = plt.subplots(1, 2, figsize=(self.p.width.double, 2.0))

        fig.tight_layout(pad=0.4)
        fig.savefig(self.fig_dir / "bargaining_set.pdf", bbox_inches="tight")
        log.info("wrote %s", self.fig_dir / "bargaining_set.pdf")
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

    def fig4_bargaining_power(self):
        """Effect of the buyer's bargaining power.

        Against tau_L, both structures on each panel: (a) negotiated strike,
        (b) generator's share of the joint gain, (c) contracted quantity.

        Panel (c) is a horizontal line for baseload. That is the result, not an
        empty plot: keep it and say so in the caption.

        Needs: bargaining_power sweep for both experiments.
        Message: under baseload power decides only the price; under PAP it also,
        marginally, decides the size of the deal. The three A_L curves converge at
        tau_L = 1, where the buyer pays the generator's reservation strike, which
        does not depend on A_L.
        """
        raise NotImplementedError("fig4_bargaining_power")

    def fig5_earnings(self):
        """Contracted earnings, and who ends up carrying the risk.

        Rows are generator and buyer, columns baseload and pay-as-produced. Each
        panel shows the weighted mean with P10-P90 and P5-P95 bands against A_L at
        A_G = self.a_g_slice, with the merchant baseline (earnings_nc_*) dotted.

        Bands go through weighted_percentiles(..., axis=0): the earnings grids have
        scenarios on the rows.

        Needs: risk_aversion sweep for both experiments.
        Message: baseload stabilises the buyer and widens the generator's
        distribution; PAP does the opposite. This is the one place the two
        structures may be compared on levels, because earnings are euros against a
        common baseline while the joint gain is risk-adjusted per party.
        """
        raise NotImplementedError("fig5_earnings")

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
