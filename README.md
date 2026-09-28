# Nash Bargaining for Renewable PPAs

A Nash bargaining model for Power Purchase Agreements between a renewable generator
and a corporate buyer. Given Monte Carlo scenarios of prices, production and
consumption, it solves for the strike price and the contracted quantity that a
bargaining solution produces when both parties are risk averse.

Both parties value a contract with a mean-CVaR utility,
`u_i = (1 - A_i) E[pi_i] + A_i CVaR_alpha(pi_i)`, and the terms maximise the weighted
Nash product of their gains over the merchant position, so bargaining power enters
explicitly through the weights.

Two settlement structures are supported:

| Structure | Contracted quantity | Decision variables |
| --- | --- | --- |
| Baseload | Fixed volume `M` each period | `S`, `M` |
| Pay-as-produced | Share `gamma` of realised production | `S`, `gamma` |

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- Gurobi with a valid license; academic licenses are free from
  [gurobi.com/academia](https://www.gurobi.com/academia/academic-program-and-licenses/)

## Setup

```bash
git clone https://github.com/AndersDHansen/Nash-Bargaining-ADH-Paper.git
cd Nash-Bargaining-ADH-Paper
uv sync
```

## Running

Configuration is composed by [Hydra](https://hydra.cc) from the groups in `config/`.
Any value can be overridden on the command line.

```bash
# base case, pay-as-produced
uv run python main.py

# baseload instead
uv run python main.py experiment=default_baseload

# override parameters
uv run python main.py experiment.A_G=0.7 experiment.A_L=0.3 experiment.tau_L=0.3

# a sensitivity sweep
uv run python main.py sensitivity=risk_aversion
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
