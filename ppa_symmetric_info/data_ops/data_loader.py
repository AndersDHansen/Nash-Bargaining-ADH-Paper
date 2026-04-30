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
        opt = cfg.opt_params
        p = cfg.paths

        # Scenario
        self.years = sc.years
        self.num_scenarios_sim = sc.num_scenarios
        self.num_scenarios_opt = opt.num_scenarios
        self.seed = sc.seed
        self.capacity_mw = sc.capacity_mw
        self.start_time = sc.start_time

        # Optimization
        self.generator_contract_capacity = opt.generator_contract_capacity
        self.retail_price = opt.retail_price
        self.strikeprice_min = opt.strikeprice_min
        self.strikeprice_max = opt.strikeprice_max
        self.gamma_max = opt.gamma_max
        self.opt_time_horizon = opt.opt_time_horizon
        self.scenario_time_horizon = opt.scenario_time_horizon

        # Risk
        self.A_L = opt.A_L
        self.A_G = opt.A_G
        self.tau_L = opt.tau_L
        self.alpha = opt.alpha
        self.D_G = opt.D_G
        self.D_L = opt.D_L

        # Contract
        self.contract_type = cfg.contract_type
        self.barter = cfg.barter
        self.discount = opt.discount

        # Sensitivity
        self.sensitivity = opt.sensitivity
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

        log.info("Config parameters loaded successfully")
