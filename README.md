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
