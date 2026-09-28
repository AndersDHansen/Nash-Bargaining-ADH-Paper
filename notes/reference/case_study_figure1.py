"""Section 4.1, case study setup: production, load, price, and capture-rate bands.

Standalone script, no dependency on the shared plotting/ helpers. Run directly:
    uv run python plotting/case_study.py
"""


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator
from omegaconf import OmegaConf

from .io import REPO
path_data = REPO / "data" / "processed" / "scenarios_reduced_2000"
tag = "reduced_20y_2000s"
fig_dir = REPO / "figures" / "case_study"
fig_dir.mkdir(parents=True, exist_ok=True)

# Read load_scale from the actual experiment config rather than hardcoding it, so this
# plot always matches whatever the model is really run with. See default_pap.yaml's
# own comments: load_scale is the dominant lever on gamma*, so silently plotting the
# unscaled load here would visually contradict the sensitivity results.
_exp_cfg = OmegaConf.load(REPO / "config" / "experiment" / "default_pap.yaml")
LOAD_SCALE = float(_exp_cfg.load_scale)

probs = pd.read_csv(path_data / f"probabilities_scenarios_{tag}.csv")[
    "Probability"
].to_numpy(dtype=float)
probs = probs / probs.sum()

# Okabe-Ito colorblind-safe palette
orange = "#e69f00"
cyan = "#56b4e9"
green = "#009e73"
yellow = "#f0e442"
blue = "#0072b2"
red = "#d55e00"
pink = "#cc79a7"

COL_SELLER = orange
COL_BUYER = cyan

panels = [
    ("production", "Power [GWh/yr]", COL_SELLER, 1.0),
    ("load", f"Load [GWh/yr]  ($\\times${LOAD_SCALE:g} scale)", COL_BUYER, LOAD_SCALE),
    ("price", "Price [EUR/MWh]", green, 1e3),
]

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "lines.linewidth": 1.0,
    }
)


def weighted_percentiles(df, probs, qs=(5, 25, 50, 75, 95)):
    a = df.to_numpy(dtype=float)
    order = np.argsort(a, axis=1)
    out = {}
    for q in qs:
        vals = []
        for t in range(a.shape[0]):
            idx = order[t]
            cw = np.cumsum(probs[idx])
            k = int(np.searchsorted(cw, q / 100.0))
            vals.append(a[t, idx[min(k, len(idx) - 1)]])
        out[q] = np.array(vals)
    return out


def load_panel(key, scale):
    df = pd.read_csv(path_data / f"{key}_scenarios_{tag}.csv", index_col=0) * scale
    years = pd.to_datetime(df.index).year.to_numpy()
    return df, years


def finish_axis(ax, ylabel):
    ax.xaxis.set_major_locator(MultipleLocator(3))
    ax.margins(x=0)
    ax.tick_params(axis="x", rotation=90)
    ax.grid(True, color="gray", alpha=0.2, linewidth=0.3)
    ax.set_axisbelow(True)
    ax.set_ylabel(ylabel)


# --- fan chart: probability-weighted percentile bands ----------------------
fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.1))

for ax, (key, ylabel, colour, scale) in zip(axs.flat, panels):
    df, years = load_panel(key, scale)
    b = weighted_percentiles(df, probs)

    ax.fill_between(years, b[5], b[95], color=colour, alpha=0.15, linewidth=0)
    ax.fill_between(years, b[25], b[75], color=colour, alpha=0.35, linewidth=0)
    ax.plot(years, b[50], color=colour, linewidth=1.0)
    finish_axis(ax, ylabel)
    if key == "production":
        ax.set_ylim(80, 160)
    # "load" is deliberately left to autoscale: at load_scale != 1.0 it lives on a
    # different physical magnitude than production, and forcing a shared axis would
    # either squash it flat or clip it -- both actively hide the scaling.

ax = axs.flat[3]
for key, label, colour in [
    ("capture_rate", "Seller", COL_SELLER),
    ("load_capture_rate", "Buyer", COL_BUYER),
]:
    df, years = load_panel(key, 1.0)
    b = weighted_percentiles(df, probs, qs=(25, 50, 75))
    ax.fill_between(years, b[25], b[75], color=colour, alpha=0.3, linewidth=0)
    ax.plot(years, b[50], color=colour, linewidth=1.0, label=label)
finish_axis(ax, "Capture rate [-]")
ax.legend(frameon=False, fontsize=8, loc="lower left")

fig.tight_layout(pad=0.5)
fig.savefig(fig_dir / "scenario_overview_bands.pdf", bbox_inches="tight")

# --- spaghetti: every scenario, probability-weighted median on top --------
fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.1))

for ax, (key, ylabel, colour, scale) in zip(axs.flat, panels):
    df, years = load_panel(key, scale)
    median = weighted_percentiles(df, probs, qs=(50,))[50]

    ax.plot(years, df.to_numpy(dtype=float), color=colour, alpha=0.03, linewidth=0.2)
    ax.plot(years, median, color=colour, linewidth=1.1)
    finish_axis(ax, ylabel)
    if key == "production":
        ax.set_ylim(80, 160)
    # "load" is deliberately left to autoscale: at load_scale != 1.0 it lives on a
    # different physical magnitude than production, and forcing a shared axis would
    # either squash it flat or clip it -- both actively hide the scaling.

ax = axs.flat[3]
for key, label, colour in [
    ("capture_rate", "Seller", COL_SELLER),
    ("load_capture_rate", "Buyer", COL_BUYER),
]:
    df, years = load_panel(key, 1.0)
    median = weighted_percentiles(df, probs, qs=(50,))[50]
    ax.plot(years, df.to_numpy(dtype=float), color=colour, alpha=0.03, linewidth=0.2)
    ax.plot(years, median, color=colour, linewidth=1.1, label=label)
finish_axis(ax, "Capture rate [-]")
ax.legend(frameon=False, fontsize=8, loc="lower left")

fig.tight_layout(pad=0.5)
fig.savefig(fig_dir / "scenario_overview_spaghetti.pdf", bbox_inches="tight")

plt.show()
