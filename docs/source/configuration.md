# Configuration

Configuration is managed by [Hydra](https://hydra.cc). All config files live in `config/` and are composed at runtime from the groups listed below.

The top-level composition is defined in `config/config.yaml`:

```yaml
defaults:
  - paths: default
  - scenario_gen: default
  - experiment: baseload    # switch to pap for PAP contract
  - sensitivity: default
  - _self_

run_sensitivity: false
```

## experiment

The experiment file is the **single source of truth for a simulation run**. It merges contract settings and model parameters in one place. Two base files are provided:

| File | Contract | sim_name |
| --- | --- | --- |
| `config/experiment/baseload.yaml` | Baseload | `base_baseload` |
| `config/experiment/pap.yaml` | PAP | `base_pap` |

Switch experiment from the CLI:

```bash
python main.py experiment=pap
```

### experiment parameters

| Key | Default (baseload) | Description |
| --- | --- | --- |
| `sim_name` | `base_baseload` | Output folder name. Results land in `results/{run_type}/{sim_name}/`. |
| `run_type` | `single_run` | Top-level results subfolder: `single_run` or `sensitivity`. |
| `discount` | `true` | Apply time-value discounting to annual cash flows. |
| `contract_type` | `baseload` | `baseload` or `pap`. |
| `barter` | `true` | Enable barter mechanism (baseload only). |
| `A_L` | `0.5` | Load risk aversion. `0` = risk-neutral, `1` = full CVaR. |
| `A_G` | `0.5` | Generator risk aversion. |
| `tau_L` | `0.5` | Load negotiation power in [0, 1]. Generator power is `1 - tau_L`. |
| `alpha` | `0.95` | CVaR confidence level. |
| `D_G` | `0.0` | Generator annual discount rate. |
| `D_L` | `0.0` | Load annual discount rate. |
| `K_G_price` | `0.0` | Generator price belief bias. `>0` = optimistic, `<0` = pessimistic. |
| `K_L_price` | `0.0` | Load price belief bias. |
| `K_G_prod` | `0.0` | Generator production belief bias. |
| `K_L_prod` | `0.0` | Load production belief bias. |
| `generator_contract_capacity` | `30` | Generator capacity in MW. Must match `scenario_gen.capacity_mw`. |
| `retail_price` | `0.001` | Retail electricity price paid by load outside the contract [EUR/MWh]. |
| `strikeprice_min` | `0.040` | Strike price lower bound [EUR/MWh]. |
| `strikeprice_max_factor` | `1.2` | Upper bound multiplier: `strikeprice_max = factor × E[price × load_capture_rate]`. |
| `gamma_max` | `1.0` | Maximum contract share for PAP contracts. |

To create a new experiment (e.g., high risk aversion), copy `baseload.yaml`, change `sim_name`, and adjust the parameters.

## scenario_gen

`config/scenario_gen/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `years` | `20` | Simulation horizon in years. |
| `num_scenarios_mc` | `100000` | Number of Monte Carlo draws. |
| `num_scenarios_reduced` | `500` | Number of representative scenarios after K-means reduction. |
| `monte_price` | `false` | Use Monte Carlo price paths instead of OU process. |
| `start_time` | `"2025-01-01"` | Simulation start date. |
| `seed` | `42` | Random seed for reproducibility. |
| `capacity_mw` | `30` | Generator nameplate capacity in MW. |

Presets for alternative scenario counts:

```bash
python main.py scenario_gen=100_scenarios    # fast testing
python main.py scenario_gen=2000_scenarios
python main.py scenario_gen=5000_scenarios
```

## sensitivity

`config/sensitivity/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `selected_analyses` | `[elasticity_vs_risk]` | List of analyses to run. |
| `num_sensitivity` | `5` | Number of steps in linear sweeps. |
| `A_G_values` | `[0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]` | Generator risk aversion grid. |
| `A_L_values` | `[0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]` | Load risk aversion grid. |

## paths

`config/paths/default.yaml`

```yaml
paths:
  root: "${hydra:runtime.cwd}"
  results:
    dir:   "${paths.root}/results"
    plots: "figures"
  processed:
    dir: "${paths.root}/data/processed"
```
