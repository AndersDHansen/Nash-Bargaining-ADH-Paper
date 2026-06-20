from pathlib import Path
import itertools

import numpy as np
import pandas as pd
from omegaconf import OmegaConf

from ..utils import get_logger
from .data_loader import DataLoader
from .data_postprocessor import DataPostprocessor
from ..model import ModelNashBargaining

log = get_logger(__name__)

# Scalar keys produced by DataPostprocessor per contract type — used to build NaN
# fallback rows when a solve point is infeasible or unbounded.
_SCALAR_KEYS: dict[str, list[str]] = {
    "baseload": [
        "objective_value", "S_EUR_MWh", "SR_star", "SU_star", "disagreement_G", "disagreement_L",
        "delta_G", "delta_L", "nash_product", "utility_G", "utility_L",
        "cvar_G", "cvar_L", "utility_G_cp", "utility_L_cp", "M_GWh_year", "M_MWh_h",
    ],
    "pap": [
        "objective_value", "S_EUR_MWh", "SR_star", "SU_star", "disagreement_G", "disagreement_L",
        "delta_G", "delta_L", "nash_product", "utility_G", "utility_L",
        "cvar_G", "cvar_L", "utility_G_cp", "utility_L_cp", "gamma", "M_GWh_year", "M_MWh_h",
    ],
}
_EARNINGS_COLS = [
    "earnings_G", "earnings_L", "earnings_G_cp", "earnings_L_cp",
    "earnings_nc_G", "earnings_nc_L",
]


def build_sensitivity_grid(sens_cfg, config) -> list[dict]:
    """Return a list of parameter dicts, one per solve point, from the sensitivity config."""
    t = sens_cfg.type

    if t == "risk_aversion":
        A_G = np.linspace(sens_cfg.A_G.start, sens_cfg.A_G.end, sens_cfg.A_G.n)
        A_L = np.linspace(sens_cfg.A_L.start, sens_cfg.A_L.end, sens_cfg.A_L.n)
        return [
            {"A_G": float(ag), "A_L": float(al)}
            for ag, al in itertools.product(A_G, A_L)
        ]

    if t == "bargaining_power":
        tau_L = np.linspace(sens_cfg.tau_L.start, sens_cfg.tau_L.end, sens_cfg.tau_L.n)
        if hasattr(sens_cfg, "A_L"):
            A_G = float(sens_cfg.A_G)
            A_L = list(sens_cfg.A_L.discrete)
            return [
                {"tau_L": float(tl), "A_G": A_G, "A_L": float(al)}
                for tl, al in itertools.product(tau_L, A_L)
            ]
        return [{"tau_L": float(tl)} for tl in tau_L]

    if t == "contract_size":
        A_G = float(sens_cfg.A_G)
        A_L = list(sens_cfg.A_L.discrete)
        tau_L = list(sens_cfg.tau_L.discrete)
        if config.experiment.contract_type == "baseload":
            M_MW = np.linspace(sens_cfg.M_MW.start, sens_cfg.M_MW.end, sens_cfg.M_MW.n)
            return [
                {"generator_contract_capacity": float(m), "fix_contract_size": True,
                 "A_G": A_G, "A_L": float(al), "tau_L": float(tl)}
                for m, al, tl in itertools.product(M_MW, A_L, tau_L)
            ]
        else:  # pap
            gamma = np.linspace(sens_cfg.gamma.start, sens_cfg.gamma.end, sens_cfg.gamma.n)
            return [
                {"gamma_max": float(g), "fix_contract_size": True,
                 "A_G": A_G, "A_L": float(al), "tau_L": float(tl)}
                for g, al, tl in itertools.product(gamma, A_L, tau_L)
            ]

    if t == "asymmetric_info":
        K_G = np.linspace(
            sens_cfg.K_G_price.start, sens_cfg.K_G_price.end, sens_cfg.K_G_price.n
        )
        K_L = np.linspace(
            sens_cfg.K_L_price.start, sens_cfg.K_L_price.end, sens_cfg.K_L_price.n
        )
        return [
            {"K_G_price": float(kg), "K_L_price": float(kl)}
            for kg, kl in itertools.product(K_G, K_L)
        ]

    if t == "disagreement_point":
        # Scalar override, not an experiment param — handled as a special case in sensitivity_run.
        return [{}]

    raise ValueError(f"Unknown sensitivity type: {t!r}")


def _solve_point(config, point, sens):
    """Solve one sweep point; return (scalars, earnings).

    On solve failure the scalars are NaN, except the reservation strikes SR*/SU* which
    are analytic and stay valid regardless of solver status.
    """
    cfg = OmegaConf.merge(config, {"experiment": point})
    data = DataLoader(cfg)

    # disagreement_point overrides a value computed inside DataLoader, not a config param.
    if sens.type == "disagreement_point":
        data.d_G = float(sens.d_G_override)

    model = ModelNashBargaining(data)
    model.run()

    dp = DataPostprocessor(model)
    try:
        dp.extract_results()
        return dp.scalars, dp.earnings
    except Exception:
        log.warning("Model status %d — no solution, recording NaN", model.m.Status)
        keys = _SCALAR_KEYS.get(data.contract_type, _SCALAR_KEYS["baseload"])
        scalars = {k: float("nan") for k in keys}
        scalars["SR_star"], scalars["SU_star"] = data.SR_star, data.SU_star
        earnings = pd.DataFrame(
            float("nan"), index=range(data.num_scenarios), columns=_EARNINGS_COLS
        )
        return scalars, earnings


def run_sensitivity(config) -> None:
    """Run the full sensitivity sweep defined by config.sensitivity and save results."""
    sens = config.sensitivity
    out_path = (
        Path(config.paths.results.sensitivity_dir)
        / f"{config.experiment.sim_name}_{sens.type}"
    )
    out_path.mkdir(parents=True, exist_ok=True)

    if sens.type == "load_risk_aversion":
        _run_load_risk_aversion(config, sens, out_path)
        return

    grid = build_sensitivity_grid(sens, config)
    n_points = len(grid)

    results = []
    earnings_list = []
    for i, point in enumerate(grid):
        log.info("Sensitivity point %d/%d: %s", i + 1, n_points, point)
        scalars, earnings = _solve_point(config, point, sens)
        results.append({**point, **scalars})
        earnings_list.append((point, earnings))

    combined = pd.DataFrame(results)
    combined.to_csv(out_path / "results_combined.csv", index=False)
    _save_grids(combined, sens.type, out_path)
    _save_earnings_grids(earnings_list, sens.type, out_path)
    log.info("Sensitivity complete: %d points, results saved to %s", n_points, out_path)


def _run_load_risk_aversion(config, sens, out_path) -> None:
    """A_L Monte-Carlo at fixed A_G: distribution of S*, SR*, SU*, and contract volume.

    Baseload runs twice over the SAME draws — variable M, then M pinned to the mean
    optimal M (M̄). PAP is single-pass (gamma is always optimised; no M-fixed concept).
    """
    rng = np.random.default_rng(sens.seed)
    A_L = rng.normal(sens.A_L.mean, sens.A_L.std, sens.n_samples).clip(*sens.A_L.clip)
    base = {"A_G": float(sens.A_G), "tau_L": float(sens.tau_L)}

    def sweep(extra):
        rows = []
        for i, al in enumerate(A_L):
            point = {**base, "A_L": float(al), **extra}
            log.info("load_risk_aversion %d/%d: A_L=%.4f %s", i + 1, len(A_L), al, extra or "")
            scalars, _ = _solve_point(config, point, sens)
            rows.append({**point, **scalars, "feasible": not np.isnan(scalars["S_EUR_MWh"])})
        return pd.DataFrame(rows)

    if config.experiment.contract_type == "baseload":
        df_var = sweep({})
        df_var.to_csv(out_path / "results_Mvar.csv", index=False)
        M_bar = float(df_var.loc[df_var["feasible"], "M_MWh_h"].mean())
        log.info("Mean optimal M (M̄) = %.4f MWh — re-running with M fixed", M_bar)
        sweep({"fixed_M_MW": M_bar}).to_csv(out_path / "results_Mfix.csv", index=False)
    else:
        sweep({}).to_csv(out_path / "results.csv", index=False)
    log.info("load_risk_aversion complete: %d draws, saved to %s", len(A_L), out_path)


# Maps cartesian sensitivity types to their (row, column) parameter names.
_CARTESIAN_PARAMS: dict[str, tuple[str, str]] = {
    "risk_aversion":  ("A_G", "A_L"),
    "asymmetric_info": ("K_G_price", "K_L_price"),
}


def _save_grids(combined: pd.DataFrame, sens_type: str, out_path: Path) -> None:
    """For 2D cartesian sweeps, write one pivot-table CSV per scalar metric."""
    if sens_type not in _CARTESIAN_PARAMS:
        return
    row_param, col_param = _CARTESIAN_PARAMS[sens_type]
    scalar_cols = [c for c in combined.columns if c not in (row_param, col_param)]
    for metric in scalar_cols:
        pivot = combined.pivot(index=row_param, columns=col_param, values=metric)
        pivot.to_csv(out_path / f"grid_{metric}.csv")
    log.info("Grid CSVs written for %d metrics", len(scalar_cols))


def _save_earnings_grids(
    earnings_list: list[tuple[dict, pd.DataFrame]], sens_type: str, out_path: Path
) -> None:
    """For 2D cartesian sweeps, write one CSV per earnings column.

    Rows = scenarios, columns = (row_param, col_param) MultiIndex.
    """
    if sens_type not in _CARTESIAN_PARAMS:
        return
    row_param, col_param = _CARTESIAN_PARAMS[sens_type]
    metrics = earnings_list[0][1].columns
    for metric in metrics:
        data = {
            (point[row_param], point[col_param]): df[metric].values
            for point, df in earnings_list
        }
        out_df = pd.DataFrame(data, index=earnings_list[0][1].index)
        out_df.columns = pd.MultiIndex.from_tuples(out_df.columns, names=[row_param, col_param])
        out_df.to_csv(out_path / f"{metric}.csv")
    log.info("Earnings grid CSVs written for %d metrics", len(metrics))
