# Configuration

Configuration is managed by [Hydra](https://hydra.cc). All config files live in `config/` and are composed at runtime from the groups listed below.

The top-level composition is defined in `config/config.yaml`:

```yaml
defaults:
  - paths: default
  - scenario_gen: default
  - contract: baseload
  - opt_params: default
  - sensitivity: default
  - _self_

run_sensitivity: false
discount: true
```

## opt_params

`config/opt_params/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `A_L` | `0.5` | Load risk aversion. `0` = risk-neutral, `1` = full CVaR. |
| `A_G` | `0.5` | Generator risk aversion. |
| `tau_L` | `0.5` | Load negotiation power in [0, 1]. Generator power is `1 - tau_L`. |
| `alpha` | `0.95` | CVaR confidence level. |
| `D_G` | `0.0` | Generator annual discount rate. `0.0` = no discounting. |
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

## contract

Two options selectable at the CLI with `contract=baseload` or `contract=pap`.

`config/contract/baseload.yaml`

```yaml
contract_type: baseload
barter: true
```

`config/contract/pap.yaml`

```yaml
contract_type: pap
barter: false
```

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

Presets for alternative scenario counts are available as drop-in overrides:

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
  processed:
    dir: "${paths.root}/data/processed"
  output:
    results: "${hydra:runtime.output_dir}/results"
    plots:   "${hydra:runtime.output_dir}/plots"
```

To change the data location, override only `paths.data.dir`; all file paths follow automatically.
