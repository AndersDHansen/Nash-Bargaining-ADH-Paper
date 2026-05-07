"""K-means scenario reduction.

Reads Monte Carlo CSVs, clusters scenarios in the joint (pi_G, pi_L) revenue space,
picks the scenario nearest each centroid as its representative, and writes reduced CSVs.

Ported from Code/scenario_reduction.py.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)


def _mc_filename(kind: str, years: int, num_mc: int, monte_price: bool) -> str:
    if monte_price:
        return f"{kind}_scenarios_monte_{years}y_{num_mc}s.csv"
    return f"{kind}_scenarios_{years}y_{num_mc}s.csv"


def reduce_scenarios(
    *,
    scenarios_dir: Path,
    output_dir: Path,
    years: int,
    num_scenarios_mc: int,
    num_scenarios_reduced: int,
    monte_price: bool = False,
    seed: int = 42,
) -> None:
    """K-means reduction: reads MC CSVs from scenarios_dir, writes reduced CSVs to output_dir."""
    log.info(
        "Reducing %d Monte Carlo scenarios to %d representatives (from %s)",
        num_scenarios_mc, num_scenarios_reduced, scenarios_dir,
    )

    def _load(kind: str) -> pd.DataFrame:
        path = scenarios_dir / _mc_filename(kind, years, num_scenarios_mc, monte_price)
        df = pd.read_csv(path, index_col=0)
        df.index = pd.to_datetime(df.index)
        return df

    prices_df = _load("price")
    prod_df   = _load("production")
    CR_df     = _load("capture_rate")
    load_df   = _load("load")
    LR_df     = _load("load_capture_rate")

    # Drop scenarios where any year's price falls outside the per-year 1st-99th percentile band
    lower = prices_df.quantile(0.01, axis=1)
    upper = prices_df.quantile(0.99, axis=1)
    within = prices_df.ge(lower, axis=0) & prices_df.le(upper, axis=0)
    keep_mask = within.all(axis=0) & prices_df.notna().all(axis=0)  # boolean Series over columns
    keep_cols = keep_mask.index[keep_mask]

    n_before = prices_df.shape[1]
    if len(keep_cols) == 0:
        log.warning("Outlier filter removed all %d scenarios — skipping filter (too few scenarios).", n_before)
        keep_cols = prices_df.columns
    prices_df = prices_df[keep_cols]
    prod_df   = prod_df[keep_cols]
    CR_df     = CR_df[keep_cols]
    load_df   = load_df[keep_cols]
    LR_df     = LR_df[keep_cols]
    log.info("Outlier filter: kept %d of %d scenarios", len(keep_cols), n_before)

    # Build 2-D revenue feature space: generator profit (pi_G) and load cost (pi_L)
    prices = prices_df.values.T   # shape: (scenarios, years)
    prod   = prod_df.values.T
    cr     = CR_df.values.T
    load   = load_df.values.T
    lr     = LR_df.values.T

    pi_G = np.sum(prices * prod * cr, axis=1)
    pi_L = np.sum(-prices * load * lr, axis=1)
    features_scaled = StandardScaler().fit_transform(np.column_stack([pi_G, pi_L]))

    log.info("Running k-means with k=%d (seed=%d)", num_scenarios_reduced, seed)
    kmeans = KMeans(n_clusters=num_scenarios_reduced, random_state=seed, n_init=10, init="k-means++")
    labels = kmeans.fit_predict(features_scaled)
    centroids = kmeans.cluster_centers_

    # For each cluster, pick the actual scenario closest to the centroid
    rep_indices: list[int] = []
    rep_probs: list[float] = []
    n_total = features_scaled.shape[0]

    for k in range(num_scenarios_reduced):
        mask = labels == k
        idx_in_cluster = np.where(mask)[0]
        if len(idx_in_cluster) == 0:
            log.warning("Cluster %d is empty — skipping", k)
            continue
        dists = np.linalg.norm(features_scaled[mask] - centroids[k], axis=1)
        rep_indices.append(int(idx_in_cluster[np.argmin(dists)]))
        rep_probs.append(len(idx_in_cluster) / n_total)

    rep_idx = np.array(rep_indices)
    rep_probs_arr = np.array(rep_probs)
    log.info("Selected %d representative scenarios (prob sum=%.6f)", len(rep_idx), rep_probs_arr.sum())

    # Save all six output files
    output_dir.mkdir(parents=True, exist_ok=True)
    time_index = prices_df.index
    col_names = [f"Scenario_{i + 1}" for i in range(len(rep_idx))]
    pattern = f"{{type}}_scenarios_reduced_{years}y_{num_scenarios_reduced}s.csv"

    for kind, arr in {
        "price":             prices[rep_idx].T,
        "production":        prod[rep_idx].T,
        "capture_rate":      cr[rep_idx].T,
        "load":              load[rep_idx].T,
        "load_capture_rate": lr[rep_idx].T,
    }.items():
        path = output_dir / pattern.format(type=kind)
        pd.DataFrame(arr, index=time_index, columns=col_names).to_csv(path)

    prob_path = output_dir / pattern.format(type="probabilities")
    pd.DataFrame({"Probability": rep_probs_arr}).to_csv(prob_path, index=False)
    log.info("Wrote reduced scenarios to %s", output_dir)
