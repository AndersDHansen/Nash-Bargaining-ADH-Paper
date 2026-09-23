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

The first run generates and reduces the Monte Carlo scenarios, which takes a few
minutes; afterwards they are cached in `data/processed/` and reused. Delete that
folder to force regeneration.

A single run writes to `results/single_run/{sim_name}/`, a sweep to
`results/sensitivity/{sim_name}_{sweep}/`.

Figures are built from those results, not from a fresh solve:

```bash
uv run python -m ppa_symmetric_info.plotting.value_creation
uv run python -m ppa_symmetric_info.plotting.value_allocation
uv run python -m ppa_symmetric_info.plotting.case_study
```

Each writes into `figures/` and reports clearly which sweep to run first if its inputs
are missing.

## Layout

```
main.py                       Hydra entry point
config/
  config.yaml                 composition defaults
  experiment/                 contract type and model parameters
  scenario_gen/               Monte Carlo and reduction settings
  sensitivity/                sweep definitions
  paths/                      filesystem layout
src/ppa_symmetric_info/
  runner.py                   pipeline: preprocess, load, solve, postprocess
  model.py                    Gurobi model of the bargaining problem
  data_ops/                   scenario generation, reduction, loading, sweeps
  analysis/                   closed-form solver used to verify the optimiser
  plotting/                   paper figures
data/raw/                     wind, price and consumption inputs
data/processed/               generated scenarios (git-ignored)
results/                      solver output (git-ignored)
figures/                      generated figures
docs/                         documentation source (mkdocs)
```

`analysis/` solves the same problem in closed form without Gurobi. It is verified
against the solver to 1e-6 and is the fastest way to reproduce the contracted-quantity
results.

## Documentation

`docs/source/` covers the model, every configuration key and the output schema:

```bash
uv run mkdocs serve -f docs/mkdocs.yaml
```

| Page | Contents |
| --- | --- |
| `index.md` | What the model does and the objective it solves |
| `installation.md` | Setup with uv or conda |
| `quickstart.md` | Running the pipeline and approximate run times |
| `model.md` | Mathematical formulation |
| `configuration.md` | Every config key, and what moves the contracted quantity |

## Run times

Indicative, on the 500-scenario reduced set:

| Step | Time |
| --- | --- |
| Scenario generation, 100k draws | ~5 min |
| Reduction to 500 scenarios | ~1 min |
| Single solve | ~7 min |
| Risk aversion sweep, 11 x 11 | several hours |
