# Design: Scenario Summary Statistics Cell

**Date:** 2026-05-24
**Status:** Approved
**Notebook:** `results/plotting_notebook.ipynb`

---

## Goal

Add one notebook cell that computes and displays probability-weighted summary statistics (mean and std) for the three key scenario input variables — electricity price, renewable production, and capture rate — collapsed across all years and scenarios into a single table.

---

## Formula

For variable $X$ shaped `(T years, S scenarios)` with scenario probabilities $p_s$:

1. Per-scenario annual mean: `x_s = mean_t(X[t, s])`
2. Probability-weighted mean: `mu = sum_s p_s * x_s`
3. Probability-weighted std: `sigma = sqrt(sum_s p_s * (x_s - mu)^2)`

---

## Data sources

All files read from `../data/processed/scenarios_reduced_2000/` (relative to notebook CWD `results/`).

| File | Variable | Shape | Notes |
|---|---|---|---|
| `price_scenarios_reduced_20y_2000s.csv` | Price | (20 × 2000) | Units must be verified at read time; multiply by 1e3 if stored as kEUR/MWh to convert to EUR/MWh |
| `production_scenarios_reduced_20y_2000s.csv` | Production | (20 × 2000) | GWh/year |
| `capture_rate_scenarios_reduced_20y_2000s.csv` | Capture rate | (20 × 2000) | Dimensionless (0–1) |
| `probabilities_scenarios_reduced_20y_2000s.csv` | Probabilities | (2000,) | Normalise before use |

CSV format: `index_col=0`, datetime index (rows = years, columns = scenario IDs).

---

## Outputs

### 1. Notebook display

A `pandas.DataFrame` with 3 rows and columns `["Mean", "Std"]`, displayed via `display()` or left as the final expression in the cell.

| Variable | Mean | Std |
|---|---|---|
| Price [EUR/MWh] | … | … |
| Production [GWh/year] | … | … |
| Capture rate | … | … |

### 2. CSV export

Saved to `scenario_summary_stats.csv` in the `results/` directory (relative path `"scenario_summary_stats.csv"`).

### 3. LaTeX snippet

Printed to notebook output via `print()` for direct copy-paste into paper. Format:

```latex
\begin{tabular}{lrr}
\toprule
Variable & Mean & Std \\
\midrule
Price [EUR/MWh] & ... & ... \\
...
\bottomrule
\end{tabular}
```

---

## Notebook placement and dependencies

- **Cell position:** append after the last existing cell (`93a4ac26`)
- **Dependencies:** none — this cell defines its own `SCEN_PATH` locally and does not depend on `BASE` or any other variable from earlier cells
- **No changes to existing cells**

---

## Out of scope

- Per-year breakdowns
- Load / load capture rate statistics
- Visualisations (histograms, box plots)
