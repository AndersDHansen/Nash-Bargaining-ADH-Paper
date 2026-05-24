# Contract Parameters Sensitivity Figure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append one notebook cell to `results/plotting_notebook.ipynb` that produces a publication-quality 2×2 figure showing strike price S and contract volume M sensitivity across the (A_G, A_L) risk-aversion grid.

**Architecture:** Single self-contained cell that loads two pivot-table CSVs, renders a 2×2 matplotlib figure (heatmaps + line slices), and saves to PNG. Depends on `BASE` defined in the existing base cell `f7f8d8e5`; introduces no shared helpers.

**Tech Stack:** Python, pandas, numpy, matplotlib, `mpl_toolkits` (colorbar), Jupyter via `NotebookEdit`

---

## File map

| Action | Path |
|---|---|
| Modify (append cell) | `results/plotting_notebook.ipynb` |
| Output (written by cell) | `results/contract_params_sensitivity.png` |
| Read-only inputs | `results/sensitivity/default_baseload_risk_aversion/grid_S_EUR_MWh.csv` |
| Read-only inputs | `results/sensitivity/default_baseload_risk_aversion/grid_M_MWh_h.csv` |

---

## Task 1: Verify data shape

**Files:**
- Read: `results/sensitivity/default_baseload_risk_aversion/grid_S_EUR_MWh.csv`
- Read: `results/sensitivity/default_baseload_risk_aversion/grid_M_MWh_h.csv`

- [ ] **Step 1: Confirm both CSVs exist and have 15×15 shape**

Run in terminal (from `results/` directory or adjust path):

```bash
cd "C:/Users/AndersDHansen/Documents/Nash-Bargaining-ADH-Paper/results"
python - <<'EOF'
import pandas as pd
df_s = pd.read_csv("sensitivity/default_baseload_risk_aversion/grid_S_EUR_MWh.csv", index_col=0)
df_m = pd.read_csv("sensitivity/default_baseload_risk_aversion/grid_M_MWh_h.csv",   index_col=0)
print("S shape:", df_s.shape)
print("M shape:", df_m.shape)
print("A_G index (first 3):", df_s.index[:3].tolist())
print("A_L cols  (first 3):", df_s.columns[:3].tolist())
EOF
```

Expected output:
```
S shape: (15, 15)
M shape: (15, 15)
A_G index (first 3): ['0.0', '0.07142857142857142', '0.14285714285714285']
A_L cols  (first 3): ['0.0', '0.07142857142857142', '0.14285714285714285']
```

If either file is missing or the shape is wrong, stop — the sensitivity sweep has not been run with the current config.

---

## Task 2: Add the notebook cell

**Files:**
- Modify: `results/plotting_notebook.ipynb` — append new code cell after last cell (`048a9231`)

The cell uses `pcolormesh` for heatmaps and plain `ax.plot` for line slices. `np.argmin(np.abs(...))` selects the nearest A_G row for each target value (0.25, 0.50, 0.75), because the grid is evenly spaced at 1/14 steps and those targets are not exact grid values.

- [ ] **Step 1: Add the cell using NotebookEdit**

Use the `NotebookEdit` tool with `new_cell` action, targeting `results/plotting_notebook.ipynb`, inserted after cell id `048a9231`. Cell type: `code`. Cell source:

```python
# ── Contract parameters: S and M sensitivity (heatmap + A_G slices) ──────────
# Produces a 2×2 figure:
#   (a) heatmap of S [EUR/MWh]    (b) line slices of S at 3 A_G values
#   (c) heatmap of M [MW]         (d) line slices of M at 3 A_G values
# Requires BASE to be defined (run base cell f7f8d8e5 first).
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from mpl_toolkits.axes_grid1 import make_axes_locatable

# ── data ──────────────────────────────────────────────────────────────────────
df_S = pd.read_csv(f"{BASE}/grid_S_EUR_MWh.csv", index_col=0)
df_M = pd.read_csv(f"{BASE}/grid_M_MWh_h.csv",   index_col=0)

ag_vals = df_S.index.astype(float).values    # shape (15,)
al_vals = df_S.columns.astype(float).values  # shape (15,)

# ── slice config ──────────────────────────────────────────────────────────────
# Target A_G values; nearest grid points are 4/14≈0.2857, 7/14=0.5, 10/14≈0.7143
AG_TARGETS  = [0.25,      0.50,      0.75     ]
AG_LABELS   = ["0.25",    "0.50",    "0.75"   ]
COLORS_S    = ["#90CAF9", "#1E88E5", "#0D47A1"]  # light → dark blue
COLORS_M    = ["#FFCC80", "#FB8C00", "#BF360C"]  # light → dark orange

# Nearest grid indices for each target
ag_idxs = [int(np.argmin(np.abs(ag_vals - t))) for t in AG_TARGETS]

# ── style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({"font.size": 11, "axes.labelsize": 11, "legend.fontsize": 9})

fig, axes = plt.subplots(2, 2, figsize=(11, 8))
fig.subplots_adjust(hspace=0.40, wspace=0.45)

AL_mesh, AG_mesh = np.meshgrid(al_vals, ag_vals)  # both shape (15,15)

def add_heatmap(ax, data, cmap, unit_label, panel_label, slice_colors):
    """Render pcolormesh heatmap with colorbar and A_G slice markers."""
    pcm = ax.pcolormesh(AL_mesh, AG_mesh, data, cmap=cmap, shading="nearest")
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.08)
    cb = fig.colorbar(pcm, cax=cax)
    cb.set_label(unit_label, fontsize=9)
    cb.ax.tick_params(labelsize=8)
    # Horizontal dashed lines at A_G slice values
    for idx, color in zip(ag_idxs, slice_colors):
        ax.axhline(ag_vals[idx], color=color, linestyle="--", linewidth=0.9, alpha=0.8)
    ax.set_ylabel("Generator risk aversion $A_G$", fontsize=10)
    ax.set_title(panel_label, loc="left", fontsize=11)
    ax.tick_params(labelsize=9)

def add_lineplot(ax, data, colors, unit_label, panel_label):
    """Render three A_G slice lines."""
    for idx, color, lbl in zip(ag_idxs, colors, AG_LABELS):
        ax.plot(al_vals, data.iloc[idx].values,
                color=color, linewidth=1.8, label=f"$A_G$ = {lbl}")
    ax.set_ylabel(unit_label, fontsize=10)
    ax.set_title(panel_label, loc="left", fontsize=11)
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=9)

# ── panels ────────────────────────────────────────────────────────────────────
add_heatmap( axes[0, 0], df_S.values, "viridis", "EUR/MWh",
             "(a)  Strike price $S$",       COLORS_S)
add_lineplot(axes[0, 1], df_S,         COLORS_S, "Strike price $S$ [EUR/MWh]",
             "(b)  $S$ — slices")

add_heatmap( axes[1, 0], df_M.values, "plasma",  "MW",
             "(c)  Contract volume $M$",    COLORS_M)
add_lineplot(axes[1, 1], df_M,         COLORS_M, "Contract volume $M$ [MW]",
             "(d)  $M$ — slices")

# X-axis labels only on bottom row
axes[1, 0].set_xlabel("Load risk aversion $A_L$", fontsize=10)
axes[1, 1].set_xlabel("Load risk aversion $A_L$", fontsize=10)
# Suppress x tick labels on top row
for ax in axes[0]:
    ax.tick_params(labelbottom=False)

plt.savefig("contract_params_sensitivity.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved → results/contract_params_sensitivity.png")
```

- [ ] **Step 2: Verify the cell was appended**

Open `results/plotting_notebook.ipynb` and confirm a new code cell appears at the end containing the line `add_heatmap(axes[0, 0], df_S.values, "viridis"`.

---

## Task 3: Run and inspect the figure

- [ ] **Step 1: Run the notebook up to and including the new cell**

In Jupyter, restart the kernel and run all cells (or run cell `f7f8d8e5` first to define `BASE`, then run the new cell).

Expected: no errors, `contract_params_sensitivity.png` is written to `results/`.

- [ ] **Step 2: Visually inspect the figure**

Open `results/contract_params_sensitivity.png`. Check:

| Check | Expected |
|---|---|
| 2×2 layout | Top row = S panels, bottom row = M panels |
| Heatmap colour direction | S: viridis (dark purple low, yellow high); M: plasma |
| Dashed lines on heatmaps | Three horizontal dashes matching the slice line colours |
| Line plot panel (b) | 3 blue lines (light/mid/dark), x-axis 0→1 |
| Line plot panel (d) | 3 orange lines (light/mid/dark), x-axis 0→1 |
| Colorbars | EUR/MWh on (a), MW on (c) |
| Panel labels | (a) top-left, (b) top-right, (c) bottom-left, (d) bottom-right |

- [ ] **Step 3: Fix any visual issues before committing**

Common issues and fixes:
- *Heatmap A_G axis is flipped (0 at top)*: add `ax.invert_yaxis()` inside `add_heatmap` after `pcolormesh`.
- *Colorbar overlaps subplot*: increase `wspace` in `fig.subplots_adjust`.
- *Legend covers data*: change `loc="best"` to `loc="upper left"` or `loc="lower right"` in `add_lineplot`.

---

## Task 4: Commit

- [ ] **Step 1: Stage and commit**

```bash
cd "C:/Users/AndersDHansen/Documents/Nash-Bargaining-ADH-Paper"
git add results/plotting_notebook.ipynb
git commit -m "feat: add contract params sensitivity figure (S and M heatmap + slices)

2x2 figure: heatmaps of S [EUR/MWh] and M [MW] over full (A_G, A_L) grid,
with A_G=0.25/0.50/0.75 line slices in right-column panels.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

Do **not** commit `results/contract_params_sensitivity.png` — output files are in `.gitignore` (or should be treated as derived artefacts).
