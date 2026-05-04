# Quick Start

## 1. Run the pipeline

```bash
python main.py
```

This runs three stages automatically:

1. **Scenario generation** — Monte Carlo sampling (OU price process, Weibull production, Beta load). Skipped if output files are already cached in `data/processed/`.
2. **Scenario reduction** — K-means reduction to the configured representative set (default: 500 scenarios).
3. **Nash bargaining** — builds and solves the Gurobi optimization model.

## 2. Override parameters

Any config value can be overridden at the command line:

```bash
# Switch to Pay-As-Produced contract
python main.py contract=pap

# Change risk aversion for both parties
python main.py opt_params.A_L=0.3 opt_params.A_G=0.7

# Use a preset scenario count
python main.py scenario_gen=2000_scenarios

# Enable time-value discounting
python main.py discount=true

# Run all sensitivity analyses after the base case
python main.py run_sensitivity=true
```

## 3. Force scenario regeneration

Delete the cached files and re-run:

```bash
rm -rf data/processed/
python main.py
```

## Typical run times

| Step | Approximate time |
| --- | --- |
| Scenario generation (100k MC draws) | ~5 min |
| Scenario reduction (to 500) | ~1 min |
| Nash bargaining (500 scenarios) | ~7 min |
| Sensitivity sweep (14 analyses) | ~60 min |
