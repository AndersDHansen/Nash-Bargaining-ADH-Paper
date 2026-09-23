# Nash Bargaining for Power Purchase Agreements

Nash bargaining model for a Power Purchase Agreement between a renewable generator
and a corporate buyer. Given price, production and consumption scenarios, it solves
for the strike price and the contracted volume that a bargaining solution would
produce, with mean-CVaR risk preferences on both sides.

This branch archives the codebase from the MSc thesis it accompanies. It is kept for
reference and is no longer developed.

Two settlement structures are supported:

| Structure | Contracted volume |
|---|---|
| Baseload | Fixed in every period |
| Pay-as-produced (PAP) | A share of realised production |

## Requirements

- Python 3.10 or later
- Gurobi with a valid license; academic licenses are free from
  [gurobi.com/academia](https://www.gurobi.com/academia/academic-program-and-licenses/)

## Setup

```bash
git clone https://github.com/AndersDHansen/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
git checkout legacy

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r Code/requirements.txt
```

## Running

The scripts were written at different times and do not agree on a working
directory, so each one below is launched the way it expects. All of them use flat
imports, hence `PYTHONPATH=Code`.

```bash
# 1. Monte Carlo scenarios -> Code/scenarios/*.csv   (run from the repository root)
PYTHONPATH=Code python Code/generate_scenarios.py

# 2. K-medoids reduction -> Code/scenarios/*_reduced_*.csv   (run from Code/)
cd Code && python scenario_reduction.py && cd ..

# 3. Negotiation and sensitivity sweeps -> Code/Results/, Code/Plots/   (repository root)
PYTHONPATH=Code python Code/main_forecast.py
```

Step 1 is slow and only needs repeating when the raw data or the scenario settings
change. Steps 2 and 3 are cheap to rerun.

`scenario_reduction.py` was exported from a notebook: it has no `__main__` guard and
its horizon and scenario count are hardcoded near the top rather than read from
`config_scenarios.py`. Edit them there if you change the generation settings.

## Configuration

| File | Controls |
|---|---|
| `Code/config_scenarios.py` | Scenario generation: horizon, number of draws, plant capacity, input paths |
| `Code/config_optimization.py` | Risk aversion, bargaining power, contract type, which sensitivity sweeps run |

The scenario horizon and count in `config_optimization.py` must match the files
actually present in `Code/scenarios/`, since they are used to build the filenames.

## Layout

```
Code/
  generate_scenarios.py      Monte Carlo price, production, load, capture rates
  scenario_reduction.py      K-medoids reduction of the generated scenarios
  main_forecast.py           Entry point: negotiation plus sensitivity sweeps
  contract_negotiation.py    Nash bargaining solver (Gurobi, SciPy fallback)
  sensitivity_analysis.py    Parameter sweeps over risk, bias and bargaining power
  Barter_Set.py              Barter set computation and plots
  Min_Max_strikeprices.py    Reservation strike bounds
  SR_SU_testing.py           Checks on those bounds
  run_negotiation_vs_risk.py Negotiated terms against risk aversion
  dataloader.py              Scenario loading and the InputData container
  utils.py                   CVaR helpers, forecast provider, strike bounds
  visualization.py           Plotting used by main_forecast
  Plot_visualizations.py     Re-plots from saved results without re-solving
  plotting/                  Figure modules: barter, boundary, earnings, sensitivity
  Data/                      Raw inputs: wind, solar, prices, industrial consumption
  scenarios/                 Generated and reduced scenario CSVs
  Results/                   Solver output (git-ignored)
  Plots/                     Generated figures (git-ignored)
```

## Data

`Code/Data/` holds hourly wind and solar profiles for 2020-2024, Danish day-ahead
prices, and an industrial consumption profile. Solar files are present but the
scenario generation is configured for wind.
