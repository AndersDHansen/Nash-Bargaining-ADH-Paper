# Configuration

Configuration is managed by [Hydra](https://hydra.cc). All config files live in `config/` and are composed at runtime from the groups listed below.

The top-level composition is defined in `config/config.yaml`:

```yaml
defaults:
  - scenarios: default
  - optimization: default
  - contract: baseload
  - sensitivity: default
  - paths: default
  - _self_
```

## optimization

`config/optimization/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `A_L` | `0.5` | Load risk aversion. `0` = risk-neutral, `1` = full CVaR. |
| `A_G` | `0.5` | Generator risk aversion. |
| `tau_L` | `0.5` | Load negotiation power in $[0, 1]$. Generator power is `1 - tau_L`. |
| `alpha` | `0.95` | CVaR confidence level. |
| `D_G` | `0.0` | Generator discount rate. |
| `D_L` | `0.0` | Load discount rate. |
| `scenario_time_horizon` | `20` | Years. Must match generated scenarios. |
| `opt_time_horizon` | `20` | Optimization horizon in years. |
| `num_scenarios` | `500` | Number of reduced scenarios to use. |
| `monte_price` | `false` | Use Monte Carlo price paths instead of historical. |
| `discount` | `true` | Apply discounting in the objective. |
| `sensitivity` | `false` | Run all sensitivity analyses after the base case. |
| `generator_contract_capacity` | `30` | Generator capacity in MW. |
| `strikeprice_min` | `0.040` | Strike price lower bound in EUR/MWh. |
| `strikeprice_max` | `0.120` | Strike price upper bound in EUR/MWh (may be overridden by load data). |
| `gamma_max` | `1.0` | Maximum contract share for PAP contracts. |

## contract

Two options selectable at the CLI with `contract=baseload` or `contract=pap`.

`config/contract/baseload.yaml`

```yaml
contract_type: "Baseload"
barter: true
```

`config/contract/pap.yaml`

```yaml
contract_type: "PAP"
barter: false
```

## scenarios

`config/scenarios/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `years` | `20` | Simulation horizon in years. |
| `num_scenarios` | `100000` | Number of Monte Carlo draws. |
| `monte_price` | `false` | Use Monte Carlo price paths. |
| `start_time` | `"2025-01-01"` | Simulation start date. |
| `seed` | `42` | Random seed for reproducibility. |
| `capacity_mw` | `30` | Generator nameplate capacity in MW. |

## sensitivity

`config/sensitivity/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `selected_analyses` | `[elasticity_vs_risk]` | List of analyses to run. |
| `num_sensitivity` | `5` | Number of steps in linear sweeps. |
| `A_G_values` | `[0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]` | Generator risk aversion grid. |
| `A_L_values` | `[0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]` | Load risk aversion grid. |

`tau_L` sweep values are computed at runtime as `np.linspace(0, 1, num_sensitivity)`.

## paths

`config/paths/default.yaml`

Paths are composed via interpolation from a single root:

```yaml
paths:
  root: "${hydra:runtime.cwd}"
  data:
    dir: "${paths.root}/data"
    wind: "${paths.data.dir}/Wind/combined_wind_data.csv"
    ...
  output:
    scenarios: "${paths.root}/simulations"
    run_dir:   "${hydra:runtime.output_dir}"
    plots:     "${hydra:runtime.output_dir}/plots"
    results:   "${hydra:runtime.output_dir}/results"
```

To change the data location, override only `paths.data.dir`; all file paths follow automatically.