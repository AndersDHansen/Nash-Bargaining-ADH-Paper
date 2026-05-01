from dataclasses import dataclass
from omegaconf import DictConfig
from pathlib import Path
import logging

log = logging.getLogger(__name__)


@dataclass
class DataLoader:
    """Reads config and stores all parameters as typed attributes.

    Separates data/preprocessing params (cfg.data) from optimization params
    (cfg.opt_params) so each config group has a single clear purpose.
    """

    config: DictConfig

    def __post_init__(self):
        log.info("DataLoader initialized")
        self._load()

    def _load(self):
        cfg = self.config
        data = cfg.scenario_gen
        params = cfg.opt_params
        p = cfg.paths

        # ── Scenario / data params (from config/scenario_gen/default.yaml) ──
        self.years = data.years
        self.periods = list(range(self.years))
        self.num_scenarios_mc = data.num_scenarios_mc
        self.num_scenarios_opt = data.num_scenarios_reduced
        self.seed = data.seed
        self.capacity_mw = data.capacity_mw
        self.start_time = data.start_time
        self.monte_price = data.monte_price

        # ── Optimization params (from config/opt_params/default.yaml) ──
        self.A_L = params.A_L
        self.A_G = params.A_G
        self.tau_L = params.tau_L
        self.alpha = params.alpha
        self.D_G = params.D_G
        self.D_L = params.D_L
        self.K_G = params.K_G
        self.K_L = params.K_L
        self.opt_time_horizon = params.opt_time_horizon
        self.discount = params.discount

        # ── Contract bounds ──
        self.generator_contract_capacity = params.generator_contract_capacity
        self.retail_price = params.retail_price
        self.strikeprice_min = params.strikeprice_min
        self.strikeprice_max = params.strikeprice_max
        self.gamma_max = params.gamma_max
        self.contract_amount_min = 0
        self.contract_amount_max = self.generator_contract_capacity * 8760 * 1e-3  # GWh/year

        # ── Contract type (from config/contract/*.yaml) ──
        self.contract_type = cfg.contract_type
        self.barter = cfg.barter

        # ── Sensitivity (from config/sensitivity/default.yaml) ──
        self.run_sensitivity = cfg.run_sensitivity
        self.selected_analyses = list(cfg.sensitivity.selected_analyses)
        self.num_sensitivity = cfg.sensitivity.num_sensitivity
        self.A_G_values = list(cfg.sensitivity.A_G_values)
        self.A_L_values = list(cfg.sensitivity.A_L_values)

        # ── Paths (from config/paths/default.yaml) ──
        self.path_wind = Path(p.raw.wind)
        self.path_solar = Path(p.raw.solar)
        self.path_price = Path(p.raw.price)
        self.path_consumption = Path(p.raw.consumption)
        # Scenarios live in a subfolder named by the reduction count, matching DataPreprocessor output.
        self.path_scenarios = Path(p.processed.dir) / f"scenarios_reduced_{self.num_scenarios_opt}"
        self.path_plots = Path(p.output.plots)
        self.path_results = Path(p.output.results)
        self.path_run_dir = Path(p.output.run_dir)

        log.info(
            "Config loaded | scenarios=%d opt, %d MC | horizon=%dy | contract=%s",
            self.num_scenarios_opt,
            self.num_scenarios_mc,
            self.years,
            self.contract_type,
        )
