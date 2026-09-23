"""The paper's figures, one method per figure.

    from ppa_symmetric_info.plotting import Plotter
    Plotter().plot_all_figures()

Sweeps are not run here. A figure whose inputs are missing raises MissingResults
naming the command that produces them, so a stale or empty plot is never written.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import plotter_config as cfg
from ..utils import get_logger

log = get_logger(__name__)


class MissingResults(FileNotFoundError):
    """A figure's input sweep has not been run yet."""


class Plotter:
    """Builds every figure in the results section.

    Parameters
    ----------
    n_scenarios, years:
        Identify the reduced scenario set under data/processed/.
    a_g_slice:
        Generator risk aversion at which figures 4 and 5 slice the risk-aversion grid.
    outdir:
        Where figures are written. Defaults to figures/ in the repo root.
    """

    BASELOAD = "default_baseload"
    PAP = "default_pap"

    FIGURES = {
        "fig1_scenarios": "4.1  scenario bands",
        "fig2_bargaining_set": "4.2  bargaining set and contracted quantity",
        "fig3_risk_preferences": "4.3  strike and joint gain over risk preferences",
        "fig4_bargaining_power": "4.4  effect of bargaining power",
        "fig5_earnings": "4.5  contracted earnings",
        "fig6_price_beliefs": "4.6  divergent price beliefs",
    }

    def __init__(
        self,
        n_scenarios: int = 2000,
        years: int = 20,
        a_g_slice: float = 0.5,
        outdir: str | Path | None = None,
    ):
        self.root = self._repo_root()
        self.n_scenarios = n_scenarios
        self.years = years
        self.a_g_slice = a_g_slice
        self.results = self.root / "results"
        self.processed = self.root / "data" / "processed"
        self.outdir = Path(outdir) if outdir else self.root / "figures"
        cfg.apply_style()

    # ------------------------------------------------------------------
    # paths and loading
    # ------------------------------------------------------------------
    @staticmethod
    def _repo_root() -> Path:
        """Walk up from this file to the directory holding pyproject.toml."""
        for d in Path(__file__).resolve().parents:
            if (d / "pyproject.toml").exists():
                return d
        raise RuntimeError(
            "repository root not found: no pyproject.toml above this file"
        )

    @staticmethod
    def _require(path: Path, how_to_make_it: str) -> Path:
        if not path.exists():
            raise MissingResults(
                f"\n  missing: {path}\n  generate it with:\n      {how_to_make_it}\n"
            )
        return path

    def _sweep_dir(self, experiment: str, sweep: str) -> Path:
        return self.results / "sensitivity" / f"{experiment}_{sweep}"

    def _how(self, experiment: str, sweep: str) -> str:
        return f"uv run python main.py experiment={experiment} sensitivity={sweep}"

    def scenarios(self) -> dict[str, pd.DataFrame]:
        """The reduced scenario set: rows are periods, columns are scenarios.

        The 'probability' entry is a Series over scenarios and is NOT uniform --
        pass it to the weighted helpers below rather than averaging naively.
        """
        tag = f"reduced_{self.years}y_{self.n_scenarios}s"
        d = self._require(
            self.processed / f"scenarios_reduced_{self.n_scenarios}",
            "uv run python main.py",
        )
        out = {
            key: pd.read_csv(d / f"{stem}_scenarios_{tag}.csv", index_col=0)
            for key, stem in [
                ("price", "price"),
                ("production", "production"),
                ("capture_rate", "capture_rate"),
                ("load", "load"),
                ("load_capture_rate", "load_capture_rate"),
            ]
        }
        probs = pd.read_csv(d / f"probabilities_scenarios_{tag}.csv")
        out["probability"] = (
            probs["Probability"] if "Probability" in probs else probs.iloc[:, 0]
        )
        return out

    def grid(self, experiment: str, sweep: str, metric: str) -> pd.DataFrame:
        """One metric pivoted over a 2-D sweep. Only risk_aversion and asymmetric_info."""
        path = self._sweep_dir(experiment, sweep) / f"grid_{metric}.csv"
        self._require(path, self._how(experiment, sweep))
        return pd.read_csv(path, index_col=0)

    def combined(self, experiment: str, sweep: str) -> pd.DataFrame:
        """Long-format table, one row per solved point. Written by every sweep."""
        path = self._sweep_dir(experiment, sweep) / "results_combined.csv"
        self._require(path, self._how(experiment, sweep))
        return pd.read_csv(path)

    def earnings(self, experiment: str, sweep: str, metric: str) -> pd.DataFrame:
        """Per-scenario earnings across a 2-D sweep.

        Rows are scenarios, columns a MultiIndex over the two swept parameters.
        `metric` is one of earnings_G, earnings_L, earnings_G_cp, earnings_L_cp,
        earnings_nc_G, earnings_nc_L (nc = no contract, the merchant baseline).
        """
        path = self._sweep_dir(experiment, sweep) / f"{metric}.csv"
        self._require(path, self._how(experiment, sweep))
        return pd.read_csv(path, header=[0, 1], index_col=0)

    def summary(self, sim_name: str) -> pd.Series:
        """results_summary.csv from a single run, as a Series indexed by metric."""
        path = self.results / "single_run" / sim_name / "results_summary.csv"
        self._require(path, f"uv run python main.py experiment.sim_name={sim_name}")
        return pd.read_csv(path, index_col=0)["value"]

    def joint_gain(self, experiment: str, sweep: str) -> pd.DataFrame:
        """delta_G + delta_L. Derived here; the model does not emit it."""
        return self.grid(experiment, sweep, "delta_G") + self.grid(
            experiment, sweep, "delta_L"
        )

    def generator_share(self, experiment: str, sweep: str) -> pd.DataFrame:
        """Generator's share of the joint gain, in [0, 1]."""
        d_G = self.grid(experiment, sweep, "delta_G")
        d_L = self.grid(experiment, sweep, "delta_L")
        return d_G / (d_G + d_L)

    # ------------------------------------------------------------------
    # probability-weighted statistics
    #
    # Scenario probabilities span roughly two orders of magnitude after k-means
    # reduction, so an unweighted mean or percentile is wrong, not merely
    # imprecise. Every band and every mean in the paper goes through these.
    # ------------------------------------------------------------------
    @staticmethod
    def weighted_percentiles(
        df: pd.DataFrame,
        probs,
        qs=(5, 10, 50, 90, 95),
        axis: int = 1,
    ) -> pd.DataFrame:
        """Weighted percentiles along the scenario axis.

        axis=1 when scenarios are columns (the scenario files), axis=0 when they
        are rows (the earnings grids). Returns one column per entry of `qs`.
        """
        values = df.to_numpy(dtype=float)
        labels = df.index if axis == 1 else df.columns
        if axis == 0:
            values = values.T
        w = np.asarray(probs, dtype=float).ravel()
        if w.size != values.shape[1]:
            raise ValueError(
                f"probabilities has {w.size} entries but the scenario axis has "
                f"{values.shape[1]}"
            )
        w = w / w.sum()

        order = np.argsort(values, axis=1)
        out = np.empty((values.shape[0], len(qs)))
        for i in range(values.shape[0]):
            o = order[i]
            cw = np.cumsum(w[o])
            idx = np.clip(np.searchsorted(cw, np.asarray(qs) / 100.0), 0, len(o) - 1)
            out[i] = values[i, o[idx]]
        return pd.DataFrame(out, index=labels, columns=list(qs))

    @staticmethod
    def weighted_mean(df: pd.DataFrame, probs, axis: int = 1) -> pd.Series:
        """Probability-weighted mean along the scenario axis. See weighted_percentiles."""
        values = df.to_numpy(dtype=float)
        labels = df.index if axis == 1 else df.columns
        if axis == 0:
            values = values.T
        w = np.asarray(probs, dtype=float).ravel()
        w = w / w.sum()
        return pd.Series(values @ w, index=labels)

    # ==================================================================
    # Figure 1 -- Section 4.1
    # ==================================================================
    def fig1_scenarios(self):
        """Scenario bands over the tenor.

        Panels: (a) wind production, (b) buyer consumption, (c) day-ahead price,
        (d) generator and buyer capture rates. Weighted median with P25-P75 and
        P5-P95 bands.

        Needs: data/processed/scenarios_reduced_{n}/
        Message: the two capture rates differ, and that difference is what makes the
        contract worth anything. Label them, do not bury them in panel (d).
        """
        raise NotImplementedError("fig1_scenarios")

    # ==================================================================
    # Figure 2 -- Section 4.2
    # ==================================================================
    def fig2_bargaining_set(self):
        """The bargaining set, and what fixes the contracted quantity.

        Panels: (a) bargaining set under baseload, (b) under pay-as-produced,
        (c) contracted quantity against buyer size.

        Panels (a) and (b) must be TRACED, not drawn as a line through two extreme
        strikes: sweep tau_L and plot the attained (delta_G, delta_L). The baseload
        frontier then has slope exactly -1 and the PAP one about -0.986, which is
        the structural point of the whole section.

        Needs: bargaining_power sweep for both experiments.
        Panel (c) needs a sweep over load_scale, which has no config and no branch
        in build_sensitivity_grid yet.

        Message: baseload separates creating from dividing value exactly; PAP does
        not, and the failure is second-order.
        """
        raise NotImplementedError("fig2_bargaining_set")

    # ==================================================================
    # Figure 3 -- Section 4.3
    # ==================================================================
    def fig3_risk_preferences(self):
        """Negotiated strike and joint gain over the risk-aversion grid.

        Heatmaps over (A_G, A_L) at tau_L = 0.5:
        (a) strike, baseload      (b) strike, pay-as-produced
        (c) joint gain, baseload  (d) joint gain, pay-as-produced

        The contracted quantity is deliberately not a panel: over this grid it moves
        by only 1.15x under baseload and 1.21x under PAP, so both panels would read
        as flat. Those ranges go in the text, and the quantity gets Figure 2(c).

        Needs: risk_aversion sweep for both experiments.
        Message: the strike responds strongly to risk preferences; the joint gain
        rises with risk aversion on both sides and is exactly zero when both parties
        are risk neutral. Mark that corner.
        """
        raise NotImplementedError("fig3_risk_preferences")

    # ==================================================================
    # Figure 4 -- Section 4.4
    # ==================================================================
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

    # ==================================================================
    # Figure 5 -- Section 4.5
    # ==================================================================
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

    # ==================================================================
    # Figure 6 -- Section 4.6, only if the belief bias stays in the paper
    # ==================================================================
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

    # ------------------------------------------------------------------
    # driver
    # ------------------------------------------------------------------
    def save(self, fig, name: str) -> None:
        """Write one figure as PDF for the paper and PNG for reading."""
        self.outdir.mkdir(parents=True, exist_ok=True)
        fig.savefig(self.outdir / f"{name}.pdf")
        fig.savefig(self.outdir / f"{name}.png", dpi=cfg.DPI)
        plt.close(fig)
        log.info("wrote    %s", self.outdir / f"{name}.pdf")

    def plot_all_figures(self, only: list[str] | None = None) -> None:
        """Build every figure, reporting rather than failing on missing inputs."""
        for name, label in self.FIGURES.items():
            if only and name not in only:
                continue
            try:
                fig = getattr(self, name)()
            except MissingResults as e:
                log.warning("skipped  %-22s %s", name, e)
            except NotImplementedError:
                log.info("todo     %-22s %s", name, label)
            else:
                self.save(fig, name)
