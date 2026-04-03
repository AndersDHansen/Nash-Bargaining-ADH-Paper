# Nash Bargaining for Power Purchase Agreements

Stochastic optimisation framework for negotiating Corporate Power Purchase Agreements (CPPAs) between a renewable-energy generator and a corporate load, using Nash bargaining theory, CVaR-based risk management, and Monte Carlo scenario analysis.

## Purpose

This repository accompanies a master's thesis that models the contract negotiation between two parties:

- **Generator** — a renewable energy producer (wind/solar) selling electricity
- **Load** — a corporate consumer purchasing electricity under a PPA

The framework determines optimal **strike prices** and **contract amounts** by solving a Nash bargaining problem subject to individual rationality constraints. It supports two contract structures:

| Contract Type | Description |
|---|---|
| **Baseload** | Fixed volume delivered every period |
| **Pay-As-Produced (PAP)** | Volume follows actual renewable production |

## Prerequisites

- **Python** 3.10+
- **Gurobi** optimiser with a valid license (academic licenses are free)
- The Python packages listed below

### Key Dependencies

| Package | Use |
|---|---|
| `gurobipy` | Mixed-integer / nonlinear optimisation (Nash bargaining) |
| `numpy`, `pandas` | Data handling |
| `scipy` | Statistical distributions, optimisation fallback |
| `matplotlib`, `seaborn` | Plotting |
| `scikit-learn`, `scikit-learn-extra` | K-Medoids scenario reduction |
| `statsmodels` | Time-series modelling for scenario generation |
| `tqdm` | Progress bars |

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/Thesis-Repository.git
cd Thesis-Repository

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

# Install dependencies
pip install numpy pandas scipy matplotlib seaborn scikit-learn scikit-learn-extra statsmodels gurobipy tqdm jupyter
```

> **Note:** Gurobi requires a separate license. See [gurobi.com/academia](https://www.gurobi.com/academia/academic-program-and-licenses/) for free academic licenses.

## Quickstart

All executable code lives in the `Code/` directory.

### 1. Generate scenarios

```bash
cd Code
python generate_scenarios.py
```

This creates Monte Carlo price, production, load, and capture-rate scenario files in `Code/scenarios/`.

### 2. Run the main analysis

```bash
python main_forecast.py
```

Runs contract negotiation, sensitivity analyses, and saves results to `Code/Results/` and plots to `Code/Plots/`.

### 3. Interactive exploration (Jupyter)

Open any of the notebooks for interactive analysis:

```bash
jupyter notebook Min_Max_strikeprices.ipynb
```

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
| `Code/.env.example` | Copy to `.env` and set `DROPBOX_FIGURES_DIR` to enable Overleaf figure export |

> **Note:** `.env` is gitignored and will not be committed. Copy `.env.example` to `.env` and fill in your local paths before running.

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


