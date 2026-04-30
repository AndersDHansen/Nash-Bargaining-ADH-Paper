from dataclasses import dataclass, field
from omegaconf import DictConfig
from pathlib import Path
import logging

log = logging.getLogger(__name__)


@dataclass
class DataLoader:
    """Reads config and stores all parameters as attributes."""

    config: DictConfig

    def __post_init__(self):
        log.info("DataLoader initialized")
        self._load()

    def _load(self):
        log.info("Loading parameters from config...")
        cfg = self.config
        sc = cfg.scenarios
        params = cfg.opt_params
        p = cfg.paths

        # Scenario
        self.years = sc.years
        self.periods = list(range(self.years))
        self.num_scenarios_sim = sc.num_scenarios
        self.num_scenarios_opt = params.num_scenarios
        self.seed = sc.seed
        self.capacity_mw = sc.capacity_mw
        self.start_time = sc.start_time

        # Optimization
        self.generator_contract_capacity = params.generator_contract_capacity
        self.retail_price = params.retail_price
        self.strikeprice_min = params.strikeprice_min
        self.strikeprice_max = params.strikeprice_max
        self.gamma_max = params.gamma_max
        self.opt_time_horizon = params.opt_time_horizon
        self.scenario_time_horizon = params.scenario_time_horizon

        # Risk
        self.A_L = params.A_L
        self.A_G = params.A_G
        self.tau_L = params.tau_L
        self.alpha = params.alpha
        self.D_G = params.D_G
        self.D_L = params.D_L
        self.K_G = params.K_G
        self.K_L = params.K_L

        # Contract
        self.contract_type = cfg.contract_type
        self.barter = cfg.barter
        self.discount = params.discount

        # Sensitivity
        self.sensitivity = params.sensitivity
        self.selected_analyses = cfg.sensitivity.selected_analyses
        self.num_sensitivity = cfg.sensitivity.num_sensitivity
        self.A_G_values = list(cfg.sensitivity.A_G_values)
        self.A_L_values = list(cfg.sensitivity.A_L_values)

        # Paths
        self.path_wind = Path(p.data.wind)
        self.path_solar = Path(p.data.solar)
        self.path_price = Path(p.data.price)
        self.path_consumption = Path(p.data.consumption)
        self.path_scenarios = Path(p.output.scenarios)
        self.path_plots = Path(p.output.plots)
        self.path_results = Path(p.output.results)
        self.path_run_dir = Path(p.output.run_dir)
        
        # Params inferred
        self.contract_amount_min = 0
        self.contract_amount_max = self.generator_contract_capacity * 8760 * 1e-3  # GWh/year
    

        log.info("Config parameters loaded successfully")
