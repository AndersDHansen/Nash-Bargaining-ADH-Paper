# Design: Contract Parameters Sensitivity Figure

**Date:** 2026-05-24  
**Status:** Approved  
**Notebook:** `results/plotting_notebook.ipynb`

---

## Goal

Add one notebook cell that produces a publication-quality 2×2 figure showing how the Nash bargaining outcomes — strike price S and contract volume M — vary across the (A_G, A_L) risk-aversion grid.

---

## Data sources

Both files live in `results/sensitivity/default_baseload_risk_aversion/` (same `BASE` constant already defined in cell `f7f8d8e5`).

| File | Variable | Units |
|---|---|---|
| `grid_S_EUR_MWh.csv` | Strike price S | EUR/MWh |
| `grid_M_MWh_h.csv` | Contract volume M | MW (hourly average) |

**CSV structure:** standard pivot table — no MultiIndex, no scenario dimension.  
Read with `pd.read_csv(f"{BASE}/grid_S_EUR_MWh.csv", index_col=0)`.  
- Row index = A_G values (15 rows, 0 → 1 in steps of 1/14)  
- Column headers = A_L values (15 cols, same grid)

---

## Figure layout

`fig, axes = plt.subplots(2, 2, figsize=(11, 8))`

| Panel | Position | Content |
|---|---|---|
| (a) | top-left | Heatmap of S [EUR/MWh] over full 15×15 grid |
| (b) | top-right | Line plot of S — 3 lines at fixed A_G, sweeping A_L |
| (c) | bottom-left | Heatmap of M [MW] over full 15×15 grid |
| (d) | bottom-right | Line plot of M — 3 lines at fixed A_G, sweeping A_L |

---

## Panel specifications

### Heatmaps — panels (a) and (c)

- Y-axis: A_G (rows of the CSV, 0 at bottom → 1 at top via `origin="upper"` flip or explicit yticks)
- X-axis: A_L (columns of the CSV)
- Rendered with `ax.pcolormesh` or `seaborn.heatmap`
- Colormaps: `"viridis"` for S, `"plasma"` for M (both greyscale-safe)
- Colorbars attached to each heatmap with unit label (EUR/MWh / MW)
- Three **horizontal dashed lines** drawn at A_G = 0.2857, 0.5, 0.7143 (the slice values), coloured to match the corresponding lines in panels (b)/(d), linewidth 0.8, alpha 0.7

### Line plots — panels (b) and (d)

- X-axis: A_L (column headers cast to float, 0 → 1)
- Y-axis: S [EUR/MWh] for (b), M [MW] for (d)
- **Three lines**, one per fixed A_G value:

| Legend label | Actual grid value | Colour (S panel) | Colour (M panel) |
|---|---|---|---|
| A_G = 0.25 | 0.2857 (4/14) | `#90CAF9` (light blue) | `#FFCC80` (light orange) |
| A_G = 0.50 | 0.5000 (7/14) | `#1E88E5` (mid blue)   | `#FB8C00` (mid orange)   |
| A_G = 0.75 | 0.7143 (10/14)| `#0D47A1` (dark blue)  | `#BF360C` (dark orange)  |

- Legend in each line-plot panel; no legend in heatmap panels
- Grid: `alpha=0.3`

### Grid value selection

`np.isclose()` is used to select rows matching a target A_G. Targets are the exact grid values (0.2857, 0.5, 0.7143); legend strings are rounded display labels ("0.25", "0.50", "0.75").

---

## Shared style

- `figsize=(11, 8)`
- `fig.subplots_adjust(hspace=0.35, wspace=0.35)` (room for colorbars and axis labels)
- Panel labels "(a)"–"(d)" added via `ax.set_title("(x)  ...", loc="left", fontsize=11)`
- X-axis label "Load risk aversion $A_L$" on bottom panels (c) and (d); tick labels suppressed on top panels (a) and (b) via `sharex` or manual hiding
- Y-axis label "Generator risk aversion $A_G$" on heatmaps; value-unit label on line plots
- `rcParams`: `font.size = 11`, `axes.labelsize = 11`, `legend.fontsize = 9`
- Saved: `plt.savefig("contract_params_sensitivity.png", dpi=150, bbox_inches="tight")`

---

## Notebook placement and dependencies

- **Cell position:** append after cell `013b620c` (uplift cell)
- **Dependencies:** requires cell `f7f8d8e5` to have been run first (defines `BASE`)
- **No new shared helpers** — grid loading is two one-liners, no weighted stats needed
- Introduces no changes to any existing cell

---

## Out of scope

- Contour overlays
- Annotating cell values on the heatmap
- The `earnings_nc_G/L` uplift cell (separate effort, blocked on sensitivity re-run)
