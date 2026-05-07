# Nash Bargaining for Power Purchase Agreements

Optimization model for PPA contract negotiation between a renewable energy generator and a corporate load. The model finds the contract terms (strike price and volume) that maximize the asymmetric Nash product of both parties' utilities, where utility combines expected earnings and CVaR risk aversion.

Full documentation: run `mkdocs serve -f docs/mkdocs.yaml` and open `http://localhost:8000`.

## Prerequisites

- Python 3.13+
- Gurobi with a valid license ([academic licenses](https://www.gurobi.com/academia/academic-program-and-licenses/) are free)
- [uv](https://github.com/astral-sh/uv) (recommended) or conda

## Installation

```bash
git clone https://github.com/<your-username>/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync
```

With conda:

```bash
conda env create -f envs/environment.yaml
conda activate nash-bargaining
pip install -e .
```

## Usage

```bash
# Base case (PAP contract, default config)
python main.py

# Switch to baseload contract
python main.py experiment=default_baseload

# Override parameters from the command line
python main.py experiment.A_L=0.3 experiment.A_G=0.7

# Run a sensitivity analysis
python main.py run_sensitivity=true sensitivity=risk_aversion
python main.py run_sensitivity=true sensitivity=bargaining_power
```

## Folder structure

```text
Nash-Bargaining-ADH-Paper/
├── config/
│   ├── config.yaml                      # Top-level Hydra composition
│   ├── experiment/                      # default_baseload.yaml, default_pap.yaml
│   ├── paths/                           # default.yaml
│   ├── scenario_gen/                    # default.yaml, 100/2000/5000 presets
│   └── sensitivity/                     # default, risk_aversion, bargaining_power, ...
├── data/                                # Raw input data (not tracked by git)
├── docs/                                # MkDocs documentation
├── results/
│   ├── single_run/{sim_name}/           # Base case outputs
│   └── sensitivity/{sim_name}_{type}/  # Sensitivity sweep outputs
├── src/
│   └── ppa_symmetric_info/
│       ├── data_ops/                    # DataLoader, DataPreprocessor, DataPostprocessor
│       ├── model.py                     # Gurobi model
│       ├── runner.py                    # Pipeline orchestration
│       └── utils.py
├── Code/                                # Legacy code (reference only)
├── main.py
├── pyproject.toml
└── uv.lock
```
<<<<<<< HEAD
=======

See `Analysis_Execution_Guide.md` in `Code/` for a step-by-step guide to the notebook analyses.

## Data Flow

```
Raw Data (Code/Data/)
    │
    ▼
generate_scenarios.py  →  Code/scenarios/*.csv
                                │
                                ▼
                    scenario_reduction.py  →  Code/scenarios/*_reduced_*.csv
                                                    │
                                                    ▼
                                        main_forecast.py  →  Code/Results/*.csv
                                                           →  Code/Plots/*.png
                                                    │
                                                    ▼
                                        Jupyter notebooks (interactive exploration)
```

## Two Workflows

### Scenario Generation

Run **once** (or whenever input data changes), then reuse the generated scenarios:

1. `generate_scenarios.py` — reads raw data from `Code/Data/`, produces full Monte Carlo scenario sets in `Code/scenarios/`
2. `scenario_reduction.py` — applies K-Medoids clustering to reduce scenarios, writing `*_reduced_*.csv` files back to `Code/scenarios/`

### Optimization & Analysis

Run as many times as needed for different contract configurations or sensitivity sweeps:

- `main_forecast.py` — reads the reduced scenarios, solves the Nash bargaining problem, runs sensitivity analyses, and writes results to `Code/Results/` and figures to `Code/Plots/`

## Configuration

| File | Purpose |
|---|---|
| `Code/config_scenarios.py` | Parameters for scenario generation (number of simulations, horizons, data paths) |
| `Code/config_optimization.py` | Parameters for optimization and sensitivity analysis (risk levels, negotiation power, contract types) |

## Folder Structure

```
Thesis-Repository/
├── Code/
│   ├── Data/                  # Raw input data
│   │   ├── Solar/             # Solar production profiles (2020-2024)
│   │   ├── Wind/              # Wind production profiles (2020-2024)
│   │   ├── EnergyReport.csv   # Historical energy market data
│   │   └── ConsumptionIndustry.csv
│   ├── Plots/                 # Generated figures
│   ├── Results/               # CSV/JSON output from analyses
│   ├── scenarios/             # Generated Monte Carlo scenario files
│   │
│   ├── main_forecast.py       # Main entry point — runs negotiation + sensitivity
│   ├── contract_negotiation.py # Nash bargaining solver (Gurobi + SciPy)
│   ├── Barter_Set.py          # Barter set computation and visualisation
│   ├── sensitivity_analysis.py # Parameter sweeps (risk, bias, negotiation power)
│   ├── visualization.py       # Plotting utilities
│   ├── dataloader.py          # Scenario loading and InputData class
│   ├── utils.py               # Shared helpers (CVaR, forecasts, strike-price bounds)
│   ├── generate_scenarios.py  # Monte Carlo scenario generation
│   ├── run_negotiation_vs_risk.py # Negotiation-vs-risk comparison script
│   ├── Plot_visualizations.py # Re-plot from saved results
│   │
│   ├── Min_Max_strikeprices.ipynb      # Main interactive analysis notebook
│   ├── SR_SU_testing.ipynb             # Strike-price bound testing
│   ├── Quickplots.ipynb                # Quick exploratory plots
│   ├── Time_sensitivity.ipynb          # Time-horizon sensitivity
│   ├── Barter_Set_Visualizer.ipynb     # Barter set exploration
│   ├── scenario_reduction.ipynb        # Scenario reduction demo
│   ├── test_cvar.ipynb                 # CVaR validation
│   └── Analysis_Execution_Guide.md     # Step-by-step notebook guide
│
├── Project_Extensions_direction.drawio  # Project roadmap diagram
├── .gitignore
└── README.md
```


>>>>>>> master
