# Quick Start

## 1. Generate scenarios

Run once, or whenever the input data in `data/` changes:

```bash
python -m ppa_symmetric_info.generate_scenarios
python -m ppa_symmetric_info.scenario_reduction
```

This writes Monte Carlo scenario files to `simulations/`. Generation uses an Ornstein-Uhlenbeck price process, Weibull production, and Beta load distributions over the configured time horizon.

## 2. Run the negotiation

```bash
python main.py
```

Results and plots are written to `outputs/<date>/<time>/` by Hydra.

## 3. Override parameters

Any config value can be overridden from the command line:

```bash
# Switch to Pay-As-Produced contract
python main.py contract=pap

# Change risk aversion for both parties
python main.py optimization.A_L=0.3 optimization.A_G=0.7

# Run all sensitivity analyses
python main.py optimization.sensitivity=true
```

## 4. Re-plot without re-running

```bash
python -m ppa_symmetric_info.Plot_visualizations
```

Loads the most recent results from `outputs/` and regenerates figures without calling Gurobi.

## Typical run times

| Step | Time |
| --- | --- |
| Scenario generation (100k) | ~5 min |
| Scenario reduction (to 500) | ~1 min |
| Nash bargaining (500 scenarios) | ~7 min |
| Sensitivity sweep (14 analyses) | ~60 min |