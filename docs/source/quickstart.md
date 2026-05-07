# Quick Start

## 1. Run the pipeline

```bash
python main.py
```

This runs three stages automatically:

1. **Scenario generation** - Monte Carlo sampling (OU price process, Weibull production, Beta load). Skipped if output files are already cached in `data/processed/`.
2. **Scenario reduction** - K-means reduction to the configured representative set (default: 500 scenarios).
3. **Nash bargaining** - builds and solves the Gurobi optimization model, then writes results to `results/single_run/default_pap/`.

The default config runs the PAP contract. To run baseload:

```bash
python main.py experiment=default_baseload
```

## 2. Override parameters

Any config value can be overridden at the command line:

```bash
# Change risk aversion for both parties
python main.py experiment.A_L=0.3 experiment.A_G=0.7

# Change bargaining power
python main.py experiment.tau_L=0.3

# Use a preset scenario count
python main.py scenario_gen=100_scenarios

# Enable time-value discounting
python main.py experiment.discount=true
```

## 3. Run a sensitivity analysis

```bash
# Risk aversion sweep (A_G x A_L grid)
python main.py run_sensitivity=true sensitivity=risk_aversion

# Bargaining power sweep (tau_L from 0 to 1)
python main.py run_sensitivity=true sensitivity=bargaining_power
```

Results land in `results/sensitivity/{sim_name}_{sensitivity_type}/results_combined.csv`.

To change the grid, edit the corresponding file in `config/sensitivity/`. The `n` parameter controls how many points `numpy.linspace` generates.

## 4. Force scenario regeneration

Delete the cached files and re-run:

```bash
rm -rf data/processed/
python main.py
```

## Approximate run times

| Step | Time |
| --- | --- |
| Scenario generation (100k MC draws) | ~5 min |
| Scenario reduction to 500 | ~1 min |
| Single Nash bargaining solve | ~7 min |
| Risk aversion sweep (11 x 11 = 121 solves) | ~14 hours |
| Bargaining power sweep (11 solves) | ~1.5 hours |
