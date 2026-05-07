# Configuration

Configuration is managed by [Hydra](https://hydra.cc). All config files live in `config/` and are composed at runtime from the groups below.

The top-level file is `config/config.yaml`:

```yaml
defaults:
  - paths: default
  - scenario_gen: default
  - experiment: default_pap    # switch to default_baseload for the baseload contract
  - sensitivity: default
  - _self_

run_sensitivity: false
```

---

## experiment

The experiment file is the single source of truth for a simulation run. It specifies the contract type, all model parameters, and the output folder name.

Two base files are provided:

| File | Contract |
| --- | --- |
| `config/experiment/default_baseload.yaml` | Baseload |
| `config/experiment/default_pap.yaml` | Pay-As-Produced |

Switch from the command line:

```bash
python main.py experiment=default_baseload
```

### Parameters

| Key | Description | Default (baseload) | Default (PAP) |
| --- | --- | --- | --- |
| `sim_name` | Output folder name | `default_baseload` | `default_pap` |
| `run_type` | Results subfolder (`single_run` or `sensitivity`) | `single_run` | `single_run` |
| `contract_type` | `baseload` or `pap` | `baseload` | `pap` |
| `barter` | Enable barter mechanism | `true` | `false` |
| `discount` | Apply time-value discounting | `false` | `false` |
| `D_G` | Generator annual discount rate | `0.0` | `0.08` |
| `D_L` | Load annual discount rate | `0.0` | `0.08` |
| `A_G` | Generator risk aversion (0 = risk-neutral, 1 = CVaR only) | `0.5` | `0.5` |
| `A_L` | Load risk aversion | `0.5` | `0.5` |
| `tau_L` | Load bargaining power in [0, 1]; generator gets `1 - tau_L` | `0.5` | `0.5` |
| `alpha` | CVaR confidence level | `0.95` | `0.95` |
| `K_G_price` | Generator price belief bias (0 = unbiased) | `0.0` | `0.0` |
| `K_L_price` | Load price belief bias | `0.0` | `0.0` |
| `K_G_prod` | Generator production belief bias | `0.0` | `0.0` |
| `K_L_prod` | Load production belief bias | `0.0` | `0.0` |
| `generator_contract_capacity` | Generator nameplate capacity in MW | `30` | `30` |
| `strikeprice_min` | Strike price lower bound in EUR/MWh | `0.040` | `0.040` |
| `strikeprice_max` | Strike price upper bound in EUR/MWh | `0.200` | `0.200` |
| `gamma_max` | Maximum contract share (PAP only) | `1.0` | `1.0` |

To create a new experiment, copy one of the base files, set a new `sim_name`, and adjust the parameters:

```bash
cp config/experiment/default_baseload.yaml config/experiment/high_risk.yaml
# edit high_risk.yaml: set sim_name: high_risk, A_G: 0.9, A_L: 0.9
python main.py experiment=high_risk
```

---

## scenario_gen

`config/scenario_gen/default.yaml`

| Key | Default | Description |
| --- | --- | --- |
| `years` | `20` | Contract horizon in years |
| `num_scenarios_mc` | `100000` | Monte Carlo draws |
| `num_scenarios_reduced` | `500` | Representative scenarios after K-means reduction |
| `monte_price` | `false` | Use normal price sampling instead of OU process |
| `start_time` | `2025-01-01` | Reference start date for scenario time index |
| `seed` | `42` | Random seed |
| `capacity_mw` | `30` | Generator nameplate capacity in MW (must match `experiment.generator_contract_capacity`) |

Presets for alternative scenario counts:

```bash
python main.py scenario_gen=100_scenarios    # fast testing
python main.py scenario_gen=2000_scenarios
python main.py scenario_gen=5000_scenarios
```

Scenario files are cached in `data/processed/scenarios_reduced_{n}/`. Delete that folder to force regeneration.

---

## sensitivity

Sensitivity configs define the parameter grid for a sweep run. Each file has a `type` field that tells the runner which parameters to vary.

Activate a sweep with:

```bash
python main.py run_sensitivity=true sensitivity=risk_aversion
```

### Available configs

**`config/sensitivity/risk_aversion.yaml`**

Sweeps $A_G$ and $A_L$ jointly (cartesian product).

```yaml
type: risk_aversion

A_G:
  start: 0.0
  end: 1.0
  n: 11        # 11 x 11 = 121 solves

A_L:
  start: 0.0
  end: 1.0
  n: 11
```

**`config/sensitivity/bargaining_power.yaml`**

Sweeps `tau_L` from 0 (all power to generator) to 1 (all power to load).

```yaml
type: bargaining_power

tau_L:
  start: 0.0
  end: 1.0
  n: 11
```

**`config/sensitivity/asymmetric_info.yaml`**

Sweeps price belief bias parameters. Deferred until the writing phase confirms which dimensions matter.

```yaml
type: asymmetric_info

K_G_price:
  start: -0.5
  end: 0.5
  n: 11

K_L_price:
  start: -0.5
  end: 0.5
  n: 11
```

**`config/sensitivity/disagreement_point.yaml`**

Sanity check: forces the generator's disagreement point to zero.

```yaml
type: disagreement_point
d_G_override: 0.0
```

Grids are generated at runtime with `numpy.linspace(start, end, n)`, which always includes both endpoints.

---

## paths

`config/paths/default.yaml`

All paths use Hydra interpolation and are resolved relative to the working directory at runtime. You generally do not need to edit this file.

```yaml
root: "${hydra:runtime.cwd}"

results:
  dir:             "${paths.root}/results"
  sensitivity_dir: "${paths.root}/results/sensitivity"
  plots:           "figures"

processed:
  dir: "${paths.root}/data/processed"
```

### Output directory structure

| Run type | Output location |
| --- | --- |
| Base case | `results/single_run/{sim_name}/` |
| Sensitivity sweep | `results/sensitivity/{sim_name}_{sensitivity_type}/` |

Each base-case run writes:

| File | Contents |
| --- | --- |
| `results_summary.csv` | Scalar results: strike price, utilities, Nash product, surpluses |
| `results_earnings.csv` | Per-scenario earnings for both parties under contract and at capture price |
| `model.lp` | Gurobi LP file |
| `model.mps` | Gurobi MPS file |
| `config.yaml` | Resolved Hydra config for this run |
| `run.log` | Full pipeline log |

Each sensitivity sweep writes a single `results_combined.csv` with one row per grid point plus all scalar results.
