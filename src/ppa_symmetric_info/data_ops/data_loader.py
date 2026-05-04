import numpy as np
import pandas as pd
from dataclasses import dataclass
from pathlib import Path

from omegaconf import DictConfig

from ppa_symmetric_info.utils import get_logger

log = get_logger(__name__)


@dataclass
class DataLoader:
    config: DictConfig

    def __post_init__(self):
        self._load_config()
        self._load_scenarios()
        log.info(
            "Data loaded: %d scenarios, %d years, contract=%s, barter=%s",
            self.num_scenarios, self.years, self.contract_type, self.barter,
        )

    def _load_config(self):
        cfg = self.config
        scen_gen = cfg.scenario_gen
        params = cfg.opt_params

        # Time / scenario dimensions
        self.years = scen_gen.years
        self.periods = list(range(self.years))
        self.num_scenarios = scen_gen.num_scenarios_reduced
        self.scenarios = list(range(self.num_scenarios))
        self.monte_price = scen_gen.monte_price

        # Risk / negotiation
        self.A_L = params.A_L
        self.A_G = params.A_G
        self.tau_L = params.tau_L
        self.tau_G = 1.0 - params.tau_L
        self.alpha = params.alpha
        self.D_G = params.D_G
        self.D_L = params.D_L
        self.K_G = params.K_G
        self.K_L = params.K_L

        # Contract bounds
        self.generator_contract_capacity = params.generator_contract_capacity
        self.retail_price = params.retail_price
        self.strikeprice_min = params.strikeprice_min
        self.gamma_max = params.gamma_max
        self.contract_amount_min = 0
        self.contract_amount_max = self.generator_contract_capacity * 8760 * 1e-3  # GWh/year

        # Run-level flags (top-level in config.yaml, barter via contract/*.yaml)
        self.contract_type = cfg.contract_type
        self.barter = cfg.barter
        self.discount = cfg.discount

        # Paths
        self.path_scenarios = Path(cfg.paths.processed.dir) / f"scenarios_reduced_{self.num_scenarios}"
        self.path_results = Path(cfg.paths.output.results)
        self.path_plots = Path(cfg.paths.output.plots)

    def _load_scenarios(self):
        years, n = self.years, self.num_scenarios
        d = self.path_scenarios

        self.price = self._read_csv(d, "price", years, n)
        self.production = self._read_csv(d, "production", years, n)
        self.capture_rate = self._read_csv(d, "capture_rate", years, n)
        self.load = self._read_csv(d, "load", years, n)
        self.load_cr = self._read_csv(d, "load_capture_rate", years, n)

        prob_path = d / f"probabilities_scenarios_reduced_{years}y_{n}s.csv"
        self.prob = pd.read_csv(prob_path)["Probability"].to_numpy()

        # Align all column names to price's columns
        cols = self.price.columns
        for df in (self.production, self.capture_rate, self.load, self.load_cr):
            df.columns = cols

        # strikeprice_max: 1.2x the probability-weighted mean load capture price
        capture_price_load = self.price * self.load_cr
        self.strikeprice_max = float((capture_price_load * self.prob).sum(axis=1).mean()) * 1.2
        log.info("Strike price bounds: %.4f to %.4f", self.strikeprice_min, self.strikeprice_max)

    @staticmethod
    def _read_csv(directory: Path, kind: str, years: int, num_scenarios: int) -> pd.DataFrame:
        fname = f"{kind}_scenarios_reduced_{years}y_{num_scenarios}s.csv"
        df = pd.read_csv(directory / fname, index_col=0)
        df.index = pd.to_datetime(df.index)
        return df