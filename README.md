# Nash Bargaining for Power Purchase Agreements

Optimization framework for PPA contract negotiation between a renewable energy generator and a corporate load, using Nash bargaining theory, CVaR risk aversion, and Monte Carlo scenario analysis.

Full documentation is available via MkDocs (see [Documentation](#documentation)).

## Overview

The framework finds optimal strike prices and contract amounts by solving a Nash bargaining problem subject to CVaR-based individual rationality constraints. Two contract structures are supported:

| Contract type | Description |
| --- | --- |
| Baseload | Fixed volume `M` (GWh/year) delivered each period |
| Pay-As-Produced (PAP) | Share `γ` of actual renewable production |

## Prerequisites

- Python 3.13+
- Gurobi optimizer with a valid license ([academic licenses](https://www.gurobi.com/academia/academic-program-and-licenses/) are free)
- [uv](https://github.com/astral-sh/uv) (recommended) or conda

## Installation

```bash
git clone https://github.com/<your-username>/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync
```

Or with conda:

```bash
conda env create -f envs/environment.yaml
conda activate nash-bargaining
pip install -e .
```

## Usage

### Run the full pipeline

```bash
python main.py
```

This runs scenario generation (if not cached), scenario reduction, and the Nash bargaining optimization.

### Override parameters from the CLI

```bash
# Switch to Pay-As-Produced contract
python main.py contract=pap

# Change risk aversion
python main.py opt_params.A_L=0.3 opt_params.A_G=0.7

# Use a preset scenario count
python main.py scenario_gen=2000_scenarios

# Enable time-value discounting
python main.py discount=true

# Run sensitivity analyses
python main.py run_sensitivity=true
```

## Configuration

Config files live in `config/` and are managed by [Hydra](https://hydra.cc). The top-level composition is in `config/config.yaml`.

| Group | File(s) | Controls |
| --- | --- | --- |
| `opt_params` | `config/opt_params/default.yaml` | Risk aversion, negotiation power, CVaR level, strike price bounds |
| `contract` | `config/contract/{baseload,pap}.yaml` | Contract type and barter flag |
| `scenario_gen` | `config/scenario_gen/default.yaml` (+ presets) | Monte Carlo settings, time horizon, seed, scenario count |
| `sensitivity` | `config/sensitivity/default.yaml` | Parameter sweep ranges |
| `paths` | `config/paths/default.yaml` | Data input and output directories |

## Folder Structure

```text
Nash-Bargaining-ADH-Paper/
├── config/                   # Hydra configuration
│   ├── config.yaml
│   ├── contract/             # baseload.yaml, pap.yaml
│   ├── opt_params/           # default.yaml
│   ├── paths/                # default.yaml
│   ├── scenario_gen/         # default.yaml, 100_scenarios.yaml, 2000_scenarios.yaml, 5000_scenarios.yaml
│   └── sensitivity/          # default.yaml
├── data/                     # Raw input data (wind, solar, load)
├── docs/                     # MkDocs documentation source
├── envs/                     # Conda environment file
├── src/
│   └── ppa_symmetric_info/   # Python package
│       ├── data_ops/         # DataLoader, DataPreprocessor, scenario generation & reduction
│       ├── model.py          # Nash bargaining optimization (Gurobi)
│       ├── runner.py         # Pipeline orchestration
│       └── utils.py          # Logging helpers
├── Code/                     # Legacy code (reference only, do not run)
├── main.py                   # Entry point (Hydra-managed)
├── pyproject.toml
└── uv.lock
```

## Documentation

```bash
mkdocs serve -f docs/mkdocs.yaml
```

Then open <http://localhost:8000>.
