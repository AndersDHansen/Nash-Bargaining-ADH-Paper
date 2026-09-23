"""Locate and load model outputs for the figure scripts.

Every figure declares its inputs through these loaders rather than reading paths
inline. Two reasons: a missing sweep fails loudly with an instruction to run it,
instead of silently producing a stale or empty plot; and when the output schema
changes there is one place to fix.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

def _repo_root() -> Path:
    """Walk up from this file until the directory holding pyproject.toml."""
    for d in Path(__file__).resolve().parents:
        if (d / "pyproject.toml").exists():
            return d
    raise RuntimeError("repository root not found: no pyproject.toml above this file")


REPO = _repo_root()
RESULTS = REPO / "results"
DATA = REPO / "data" / "processed"

# Where figures are written, inside this repo.
PAPER_FIGURES = REPO / "figures"


class MissingResults(FileNotFoundError):
    """Raised when a figure's input sweep has not been run yet."""


def _require(path: Path, how_to_make_it: str) -> Path:
    if not path.exists():
        raise MissingResults(
            f"\n  missing: {path}\n  generate it with:\n      {how_to_make_it}\n"
        )
    return path


# ---------------------------------------------------------------------------
# scenario inputs (Section 4.1)
# ---------------------------------------------------------------------------


def scenario_dir(n_scenarios: int = 2000, years: int = 20) -> Path:
    return DATA / f"scenarios_reduced_{n_scenarios}"


def load_scenarios(n_scenarios: int = 2000, years: int = 20) -> dict[str, pd.DataFrame]:
    """Return the reduced scenario set as {name: DataFrame(years x scenarios)}."""
    d = scenario_dir(n_scenarios)
    tag = f"reduced_{years}y_{n_scenarios}s"
    _require(d, "uv run python main.py experiment=default_pap")
    out = {}
    for key, stem in [
        ("price", f"price_scenarios_{tag}"),
        ("production", f"production_scenarios_{tag}"),
        ("capture_rate", f"capture_rate_scenarios_{tag}"),
        ("load", f"load_scenarios_{tag}"),
        ("load_capture_rate", f"load_capture_rate_scenarios_{tag}"),
    ]:
        out[key] = pd.read_csv(d / f"{stem}.csv", index_col=0)
    probs = pd.read_csv(d / f"probabilities_scenarios_{tag}.csv")
    out["probability"] = (
        probs["Probability"] if "Probability" in probs else probs.iloc[:, 0]
    )
    return out


# ---------------------------------------------------------------------------
# sweeps (Sections 4.2 and 4.3)
# ---------------------------------------------------------------------------


def sweep_dir(experiment: str, sweep: str) -> Path:
    return RESULTS / "sensitivity" / f"{experiment}_{sweep}"


def load_grid(experiment: str, sweep: str, metric: str) -> pd.DataFrame:
    """One pivoted metric from a 2-D sweep, e.g. metric='gamma' or 'S_EUR_MWh'."""
    d = sweep_dir(experiment, sweep)
    path = d / f"grid_{metric}.csv"
    _require(
        path,
        f"uv run python main.py experiment={experiment} sensitivity={sweep}",
    )
    return pd.read_csv(path, index_col=0)


def load_combined(experiment: str, sweep: str) -> pd.DataFrame:
    """The long-format table of every solved point in a sweep."""
    path = sweep_dir(experiment, sweep) / "results_combined.csv"
    _require(
        path,
        f"uv run python main.py experiment={experiment} sensitivity={sweep}",
    )
    return pd.read_csv(path)


def load_single(sim_name: str) -> pd.Series:
    """results_summary.csv from a single run, as a Series indexed by metric name."""
    path = RESULTS / "single_run" / sim_name / "results_summary.csv"
    _require(path, f"uv run python main.py experiment.sim_name={sim_name}")
    return pd.read_csv(path, index_col=0)["value"]


def joint_surplus(experiment: str, sweep: str) -> pd.DataFrame:
    """delta_G + delta_L over a 2-D sweep. Not emitted by the model, derived here."""
    return load_grid(experiment, sweep, "delta_G") + load_grid(
        experiment, sweep, "delta_L"
    )


def surplus_share_G(experiment: str, sweep: str) -> pd.DataFrame:
    """Generator's share of the joint surplus, in [0,1]."""
    d_G = load_grid(experiment, sweep, "delta_G")
    d_L = load_grid(experiment, sweep, "delta_L")
    return d_G / (d_G + d_L)
