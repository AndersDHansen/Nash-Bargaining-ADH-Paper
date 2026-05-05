import numpy as np
import pandas as pd
from pathlib import Path

from omegaconf import DictConfig

from ..utils import get_logger

log = get_logger(__name__)


class DataLoader:
    def __init__(self, config: DictConfig):
        self._load_config(config)
        self._load_scenarios()
        self._prepare_model_inputs()
        log.info(
            "Data loaded: %d scenarios, %d years, contract=%s, barter=%s",
            self.num_scenarios,
            self.years,
            self.contract_type,
            self.barter,
        )

    @staticmethod
    def _read_csv(
        directory: Path, kind: str, years: int, num_scenarios: int
    ) -> pd.DataFrame:
        fname = f"{kind}_scenarios_reduced_{years}y_{num_scenarios}s.csv"
        df = pd.read_csv(directory / fname, index_col=0)
        df.index = pd.to_datetime(df.index)
        return df

    def _load_config(self, cfg: DictConfig):
        self.config = cfg  # stored so downstream classes can save it without re-passing
        scen_gen = cfg.scenario_gen
        exp = cfg.experiment

        # Time / scenario dimensions
        self.years = scen_gen.years
        self.periods = list(range(self.years))
        self.num_scenarios = scen_gen.num_scenarios_reduced
        self.scenarios = list(range(self.num_scenarios))
        self.monte_price = scen_gen.monte_price

        # Risk / negotiation
        self.A_L = exp.A_L
        self.A_G = exp.A_G
        self.tau_L = exp.tau_L
        self.tau_G = 1.0 - exp.tau_L
        self.alpha = exp.alpha
        self.D_G = exp.D_G
        self.D_L = exp.D_L
        self.K_G_price = exp.K_G_price
        self.K_L_price = exp.K_L_price
        self.K_G_prod = exp.K_G_prod
        self.K_L_prod = exp.K_L_prod

        # Contract bounds
        self.generator_contract_capacity = exp.generator_contract_capacity
        self.strikeprice_min = exp.strikeprice_min
        self.strikeprice_max = exp.strikeprice_max
        self.gamma_max = exp.gamma_max
        self.contract_amount_min = 0
        self.contract_amount_max = self.generator_contract_capacity * 8760 * 1e-3  # GWh/year

        # Run-level flags (all now inside the experiment file)
        self.contract_type = exp.contract_type
        self.barter = exp.barter
        self.discount = exp.discount

        # Paths
        self.path_scenarios = Path(cfg.paths.processed.dir) / f"scenarios_reduced_{self.num_scenarios}"
        self.path_results = Path(cfg.paths.results.dir) / exp.run_type / exp.sim_name
        self.path_plots = self.path_results / cfg.paths.results.plots

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
  
        log.info("Strike price bounds: %.4f to %.4f", self.strikeprice_min, self.strikeprice_max)

    def _prepare_model_inputs(self):
        price      = self.price.to_numpy()        # (years, scenarios)
        production = self.production.to_numpy()
        capture_rate = self.capture_rate.to_numpy()
        load       = self.load.to_numpy()
        load_cr    = self.load_cr.to_numpy()
        prob       = self.prob                    # (scenarios,)

        # Discount factors — shape (years, 1) so they broadcast over scenarios
        if self.discount:
            self.discount_factors_G = (1 / (1 + self.D_G) ** np.arange(self.years))[:, None]
            self.discount_factors_L = (1 / (1 + self.D_L) ** np.arange(self.years))[:, None]
        else:
            self.discount_factors_G = np.ones((self.years, 1))
            self.discount_factors_L = np.ones((self.years, 1))

        # Expected price and production per year — shape (years, 1) for broadcasting
        expected_price      = (price      * prob).sum(axis=1, keepdims=True)
        expected_production = (production * prob).sum(axis=1, keepdims=True)

        # Biased scenario distributions — shape (years, scenarios)
        self.price_G      = price      + self.K_G_price * expected_price
        self.price_L      = price      + self.K_L_price * expected_price
        self.production_G = production + self.K_G_prod  * expected_production   # Belief of G
        self.production_L = production + self.K_L_prod  * expected_production   # Belief of L

        # --- Capture prices (true distribution, used for post-processing) ---
        # Seller (generator): revenue rate per unit production
        self.capture_price_G     = capture_rate * price          # (years, scenarios)
        self.capture_price_G_avg = (self.capture_price_G * prob).sum(axis=1, keepdims=True)

        # Buyer (load): cost rate per unit consumption
        self.capture_price_L     = load_cr * price               # (years, scenarios)
        self.capture_price_L_avg = (self.capture_price_L * prob).sum(axis=1, keepdims=True)

        # --- Biased capture prices (each party's belief, used in model constraints) ---
        # Generator believes prices are price_G; load believes prices are price_L
        self.capture_price_G_biased = capture_rate * self.price_G  # (years, scenarios)
        self.capture_price_L_biased = load_cr      * self.price_L  # (years, scenarios)

        # --- No-contract per-scenario earnings, summed over years (with discounting) ---
        # Generator: sells renewable production at capture rate × biased price
        self.earnings_nc_G = (
            self.discount_factors_G * capture_rate * self.price_G * self.production_G
        ).sum(axis=0)  # (scenarios,)

        # Load: buys electricity at load_cr × biased price
        self.earnings_nc_L = (
            self.discount_factors_L * load * (-load_cr * self.price_L)
        ).sum(axis=0)  # (scenarios,)

        # --- Precomputed terms for model constraints (Baseload) ---
        # Discounted price sums per scenario: sum_t disc_t * lambda^i_{t,omega}
        self.lambda_disc_G = (self.discount_factors_G * self.price_G).sum(axis=0)  # (scenarios,)
        self.lambda_disc_L = (self.discount_factors_L * self.price_L).sum(axis=0)  # (scenarios,)

        # Sum of discount factors: sum_t disc_t  (scalar coefficient on S*M in earnings)
        self.disc_G_sum = float(self.discount_factors_G.sum())
        self.disc_L_sum = float(self.discount_factors_L.sum())

        # Probability-weighted expected values (scalar, for objective expressions)
        self.E_earnings_nc_G  = float((prob * self.earnings_nc_G).sum())
        self.E_earnings_nc_L  = float((prob * self.earnings_nc_L).sum())
        self.E_lambda_disc_G  = float((prob * self.lambda_disc_G).sum())
        self.E_lambda_disc_L  = float((prob * self.lambda_disc_L).sum())

        # --- CVaR of no-contract earnings (left tail, worst outcomes) ---
        cvar_nc_G = self._cvar_left(self.earnings_nc_G, prob)
        cvar_nc_L = self._cvar_left(self.earnings_nc_L, prob)

        # Disagreement points: U_i = (1 - A_i)*E[earnings] + A_i*CVaR[earnings]
        self.zeta_G = (1 - self.A_G) * self.E_earnings_nc_G + self.A_G * cvar_nc_G
        self.zeta_L = (1 - self.A_L) * self.E_earnings_nc_L + self.A_L * cvar_nc_L

        log.info("Disagreement points: zeta_G=%.4f, zeta_L=%.4f", self.zeta_G, self.zeta_L)

    def _cvar_left(self, x: np.ndarray, prob: np.ndarray) -> float:
        """Expected value of x in the worst (1-alpha) probability mass."""
        order  = np.argsort(x)
        x_s    = x[order]
        p_s    = prob[order]
        tail   = 1.0 - self.alpha
        # probability mass already accumulated before each scenario
        prev_cum = np.concatenate([[0.0], np.cumsum(p_s)[:-1]])
        weights  = np.minimum(p_s, np.maximum(0.0, tail - prev_cum))
        return float((weights * x_s).sum() / tail)

    # @AndersDHansen do we need this function to exist?
    def _compute_strike_boundaries(self):
        pass