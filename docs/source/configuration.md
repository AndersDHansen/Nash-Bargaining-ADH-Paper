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

| Key | Description | Baseload | PAP |
| --- | --- | --- | --- |
| `sim_name` | Output folder name | `default_baseload` | `default_pap` |
| `contract_type` | `baseload` or `pap` | `baseload` | `pap` |
| `barter` | Use the barter-set formulation | `true` | `false` |
| `discount` | Apply time-value discounting | `false` | `false` |
| `D_G`, `D_L` | Annual discount rates; `0.0` weights all years equally | `0.0` | `0.0` |
| `A_G`, `A_L` | Risk aversion, `0` = risk neutral, `1` = CVaR only | `0.5`, `0.5` | `0.5`, `0.8` |
| `tau_L` | Buyer's share of the Nash surplus; generator gets `1 - tau_L` | `0.5` | `0.5` |
| `alpha` | CVaR tail probability | `0.95` | `0.95` |
| `K_G_price`, `K_L_price` | Bias on the believed mean price; `>0` optimistic | `0.0` | `0.0` |
| `K_G_prod`, `K_L_prod` | Bias on the believed mean production | `0.0` | `0.0` |
| `generator_contract_capacity` | Nameplate capacity [MW]; must match `scenario_gen.capacity_mw` | `30` | `30` |
| `fix_contract_size` | Fix the quantity so only the strike is optimised | `false` | `false` |
| `fixed_M_MW` | Pin `M` [MW] instead of optimising; `null` = optimise | `null` | not used |
| `strikeprice_min/max` | Strike bounds [EUR/GWh] | `0.040`, `0.200` | `0.040`, `0.200` |
| `gamma_max` | Physical cap on the contracted share | not used | `1.0` |
| `hedge_ratio_max` | Treasury cap, as a fraction of the buyer's own exposure; `null` = off | not used | `null` |
| `load_scale` | Multiplies the buyer's consumption after loading | `1.0` | `0.6` |

Utility is `u_i = (1 - A_i) * E[pi_i] + A_i * CVaR_alpha[pi_i]`.

### The strike bounds are an input box, not the bargaining range

`strikeprice_min` and `strikeprice_max` are a box on the decision variable. The
economically meaningful range is the endogenous viable band `[S^R*, S^U*]`, which the
model derives and reports in `results_summary.csv`. The box must be strictly wider than
that band or it will bind and the reported optimum will be an artefact of the bounds.

### What moves the contracted quantity

Under PAP the negotiated share `gamma*` is driven far more by the buyer's size than by
either party's risk preferences. In order of influence:

| Knob | Effect |
| --- | --- |
| `load_scale` | Dominant. Sets the buyer's consumption relative to plant output. |
| `gamma_max` | The physical cap. At `1.0` it binds on many settings, so a reported `gamma* = 1.0000` is a boundary solution, not an interior one. Raise it to see where the unconstrained optimum sits. |
| `hedge_ratio_max` | Optional treasury cap. Limits the contract to a fraction of the buyer's own exposure. `null` disables it. |
| `A_G`, `A_L` | Move the strike substantially; the quantity much less. |
| `K_G_price`, `K_L_price` | A belief gap creates surplus neither party earns, and inflates the quantity. Keep at `0.0` for a symmetric-information base case. |

The buyer hedges value rather than volume: because renewable output is cannibalised, one
MWh of production hedges only `CR_G / CR_L` MWh of consumption. The relevant ratio is
therefore the **value ratio**, `(CR_L x consumption) / (CR_G x production)`, and the share
reaches the cap once that ratio passes one, i.e. once consumption exceeds `CR_G / CR_L` of
production.

### Why `hedge_ratio_max` exists

The contract is a financial CfD: nothing is physically delivered and the buyer resells any
surplus at market, so there is no physical penalty for over-contracting and the model will
exploit that. The real limit is a hedge-designation rule, since a corporate treasury may
not hold a hedge larger than the exposure it hedges. With it set, the binding cap is
`min(gamma_max, hedge_ratio_max * consumption / production)`.

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

Presets for alternative reduction levels:

```bash
python main.py scenario_gen=100_scenarios    # fast testing
python main.py scenario_gen=2000_scenarios
python main.py scenario_gen=5000_scenarios
```

The same effect without a preset file:

```bash
python main.py scenario_gen.num_scenarios_reduced=2000
```

Scenario files are cached in `data/processed/scenarios_reduced_{n}/`. Delete that folder to force regeneration.

---

## sensitivity

Sensitivity configs define the parameter grid for a sweep run. Each file has a `type` field that tells the runner which parameters to vary.

Activate a sweep with:

```bash
python main.py sensitivity=risk_aversion
```

### Available sweeps

| Config | Varies | Grid |
| --- | --- | --- |
| `risk_aversion` | `A_G` x `A_L` | 11 x 11 = 121 solves |
| `bargaining_power` | `tau_L` at three fixed `A_L` | 101 x 3 |
| `contract_size` | `M_MW` (baseload) or `gamma` (PAP), at three `A_L` and three `tau_L` | 40 x 3 x 3 |
| `asymmetric_info` | `K_G_price` x `K_L_price` | 10 x 10 |
| `load_risk_aversion` | Monte Carlo draws of `A_L` | 500 samples |
| `disagreement_point` | Forces `d_G` to zero | sanity check only |

Ranges are written as `{start, end, n}` and expanded with `numpy.linspace`, which includes
both endpoints. A fixed list is written as `{discrete: [...]}`. A scalar pins that
parameter for the sweep.

```yaml
# config/sensitivity/risk_aversion.yaml
type: risk_aversion

A_G: {start: 0.0, end: 1.0, n: 11}
A_L: {start: 0.0, end: 1.0, n: 11}
```

`load_risk_aversion` is different in kind: instead of a grid it draws `A_L` from
`{mean, std, clip}` and re-solves per draw, producing a distribution of acceptable
strikes rather than a surface. Baseload runs twice over the same draws, once with the
quantity optimised and once with it pinned to the mean optimum.

---

## paths

`config/paths/default.yaml`

All paths use Hydra interpolation and are resolved relative to the working directory at runtime. You generally do not need to edit this file.

```yaml
root: "${hydra:runtime.cwd}"

raw:
  dir:         "${paths.root}/data/raw"
  wind:        "${paths.raw.dir}/Wind/combined_wind_data.csv"
  price:       "${paths.raw.dir}/EnergyReport.csv"
  consumption: "${paths.raw.dir}/ConsumptionIndustry.csv"

processed:
  dir: "${paths.root}/data/processed"

results:
  dir:             "${paths.root}/results"
  sensitivity_dir: "${paths.root}/results/sensitivity"
  plots:           "figures"
```

Processed scenarios are written to subfolders named from the `scenario_gen` settings:

| Folder | Contents |
| --- | --- |
| `mc_{num_scenarios_mc}/` | Raw Monte Carlo draws, OU prices (`monte_price: false`) |
| `mc_normal_prices_{num_scenarios_mc}/` | Raw Monte Carlo draws, normal prices (`monte_price: true`) |
| `scenarios_reduced_{num_scenarios_reduced}/` | K-means representatives, read by the optimiser |

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
