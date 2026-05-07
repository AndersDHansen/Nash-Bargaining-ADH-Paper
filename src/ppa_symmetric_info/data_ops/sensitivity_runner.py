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


def build_sensitivity_grid(sens_cfg) -> list[dict]:
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
        return [{"tau_L": float(tl)} for tl in tau_L]

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


def run_sensitivity(config) -> None:
    """Run the full sensitivity sweep defined by config.sensitivity and save results."""
    sens = config.sensitivity
    grid = build_sensitivity_grid(sens)
    n_points = len(grid)

    out_path = (
        Path(config.paths.results.sensitivity_dir)
        / f"{config.experiment.sim_name}_{sens.type}"
    )
    out_path.mkdir(parents=True, exist_ok=True)

    results = []
    for i, point in enumerate(grid):
        log.info("Sensitivity point %d/%d: %s", i + 1, n_points, point)

        cfg = OmegaConf.merge(config, {"experiment": point})
        data = DataLoader(cfg)

        # disagreement_point overrides a value computed inside DataLoader, not a config param.
        if sens.type == "disagreement_point":
            data.d_G = float(sens.d_G_override)

        model = ModelNashBargaining(data)
        model.run()

        dp = DataPostprocessor(model)
        dp.extract_results()

        results.append({**point, **dp.scalars})

    combined = pd.DataFrame(results)
    combined.to_csv(out_path / "results_combined.csv", index=False)
    _save_grids(combined, sens.type, out_path)
    log.info("Sensitivity complete: %d points, results saved to %s", n_points, out_path)


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
