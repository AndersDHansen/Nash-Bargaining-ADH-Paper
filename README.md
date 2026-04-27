# Nash Bargaining for Power Purchase Agreements

Optimization framework for PPA contract negotiation between a renewable energy generator and a corporate load, using Nash bargaining theory, CVaR risk aversion, and Monte Carlo scenario analysis.

Full documentation is available via MkDocs (see [Documentation](#documentation)).

## Overview

The framework finds optimal strike prices and contract amounts by solving a Nash bargaining problem subject to CVaR-based individual rationality constraints. Two contract structures are supported:

| Contract type | Description |
|---|---|
| Baseload | Fixed volume delivered each period |
| Pay-As-Produced (PAP) | Volume follows actual renewable production |

## Prerequisites

- Python 3.10+
- Gurobi optimizer with a valid license ([academic licenses](https://www.gurobi.com/academia/academic-program-and-licenses/) are free)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
git clone https://github.com/<your-username>/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync   # or: pip install -e .
```

Copy `.env.example` to `.env` and set `DROPBOX_FIGURES_DIR` if you want figures exported to Overleaf/Dropbox.

## Usage

### 1. Generate and reduce scenarios (run once)

```bash
python -m ppa_symmetric_info.generate_scenarios
python -m ppa_symmetric_info.scenario_reduction
```

Scenario files are written to `simulations/`.

### 2. Run contract negotiation

```bash
python main.py
```

Results and plots land in `outputs/<date>/<time>/` (Hydra-managed).

Override any parameter from the CLI:

```bash
python main.py contract=pap
python main.py optimization.A_L=0.3 optimization.tau_L=0.6
python main.py optimization.sensitivity=true
```

## Configuration

Config files live in `config/` and are managed by [Hydra](https://hydra.cc). Switch contract types or sweep parameters without touching Python:

| Group | File | Controls |
| --- | --- | --- |
| `optimization` | `config/optimization/default.yaml` | Risk aversion, negotiation power, CVaR level, horizons |
| `contract` | `config/contract/{baseload,pap}.yaml` | Contract type and McCormick relaxation flag |
| `scenarios` | `config/scenarios/default.yaml` | Monte Carlo settings, time horizon, seed |
| `sensitivity` | `config/sensitivity/default.yaml` | Parameter sweep ranges and selected analyses |
| `paths` | `config/paths/default.yaml` | Data inputs and output directories |

## Folder Structure

```
Nash-Bargaining-ADH-Paper/
├── config/                  # Hydra configuration
│   ├── config.yaml
│   ├── contract/            # baseload.yaml, pap.yaml
│   ├── optimization/
│   ├── paths/
│   ├── scenarios/
│   └── sensitivity/
├── data/                    # Raw input data
│   ├── Wind/
│   ├── Solar/
│   ├── EnergyReport.csv
│   └── ConsumptionIndustry.csv
├── docs/                    # MkDocs documentation source
├── ppa_symmetric_info/      # Python package
│   ├── contract_negotiation.py
│   ├── generate_scenarios.py
│   ├── scenario_reduction.py
│   ├── main_forecast.py
│   ├── sensitivity_analysis.py
│   ├── dataloader.py
│   ├── utils.py
│   └── plotting/
├── simulations/             # Generated scenario files
├── outputs/                 # Hydra run outputs (date-stamped)
├── Code/                    # Legacy code (reference only)
├── main.py                  # Entry point
├── pyproject.toml
└── Makefile
```

## Documentation

```bash
mkdocs serve -f docs/mkdocs.yaml
```

Then open <http://localhost:8000>.
