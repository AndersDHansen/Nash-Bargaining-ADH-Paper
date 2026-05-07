import numpy as np
import pandas as pd
from pathlib import Path

from omegaconf import DictConfig

from ..utils import get_logger, cvar_left

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
        """Unpack all Hydra config fields into typed instance attributes."""
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
        if cfg.run_sensitivity:
            sens_type = cfg.sensitivity.type
            self.path_results = (
                Path(cfg.paths.results.sensitivity_dir)
                / f"{exp.sim_name}_{sens_type}"
            )
        else:
            self.path_results = Path(cfg.paths.results.dir) / exp.run_type / exp.sim_name
        self.path_plots = self.path_results / cfg.paths.results.plots

    def _load_scenarios(self):
        """Read scenario CSVs into numpy arrays (years × scenarios) and load scenario probabilities."""
        years, n = self.years, self.num_scenarios
        d = self.path_scenarios

        price_df        = self._read_csv(d, "price", years, n)
        production_df   = self._read_csv(d, "production", years, n)
        capture_rate_df = self._read_csv(d, "capture_rate", years, n)
        load_df         = self._read_csv(d, "load", years, n)
        load_cr_df      = self._read_csv(d, "load_capture_rate", years, n)

        prob_path = d / f"probabilities_scenarios_reduced_{years}y_{n}s.csv"
        self.prob = pd.read_csv(prob_path)["Probability"].to_numpy()

        # Align column names then convert to numpy — all scenario arrays are (years, scenarios)
        cols = price_df.columns
        for df in (production_df, capture_rate_df, load_df, load_cr_df):
            df.columns = cols

        self.price        = price_df.to_numpy()
        self.production   = production_df.to_numpy()
        self.capture_rate = capture_rate_df.to_numpy()
        self.load         = load_df.to_numpy()
        self.load_cr      = load_cr_df.to_numpy()

        log.info("Strike price bounds: %.4f to %.4f", self.strikeprice_min, self.strikeprice_max)

    def _prepare_model_inputs(self):
        """Derive all model inputs — biased distributions, capture prices, precomputed contract terms, and disagreement points."""
        price        = self.price         # (years, scenarios) numpy — set in _load_scenarios
        production   = self.production
        capture_rate = self.capture_rate
        load         = self.load
        load_cr      = self.load_cr
        prob         = self.prob          # (scenarios,)

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

        # --- Precomputed terms for model constraints (PAP) ---
        # Per-scenario discounted production sum for G: sum_t disc_t * P^G_{t,omega}
        # Coefficient on gamma*S in both the utility and CVaR constraints.
        self.pap_prod_disc_G = (self.discount_factors_G * self.production_G).sum(axis=0)  # (scenarios,)

        # Per-scenario coefficient on gamma in load's utility/CVaR: sum_t disc_t * P^G_{t,omega} * CR^G_{t,omega} * lambda^L_{t,omega}
        # Load values the contracted wind volume at the generator's capture rate × load's biased price.
        self.pap_gamma_coeff_L = (
            self.discount_factors_L * self.production_G * capture_rate * self.price_L
        ).sum(axis=0)  # (scenarios,)

        # Per-scenario coefficient on gamma*S in load's utility/CVaR: -sum_t disc_t * P^G_{t,omega}
        self.pap_prod_disc_L = (self.discount_factors_L * self.production_G).sum(axis=0)  # (scenarios,)

        # Probability-weighted scalars for PAP utility constraints
        self.E_pap_prod_disc_G  = float((prob * self.pap_prod_disc_G).sum())
        self.E_pap_gamma_coeff_L = float((prob * self.pap_gamma_coeff_L).sum())
        self.E_pap_prod_disc_L  = float((prob * self.pap_prod_disc_L).sum())

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
        cvar_nc_G = cvar_left(self.earnings_nc_G, prob, self.alpha)
        cvar_nc_L = cvar_left(self.earnings_nc_L, prob, self.alpha)

        # Disagreement points (threat points): d_i = (1 - A_i)*E[earnings] + A_i*CVaR[earnings]
        # Named d_G/d_L to distinguish from zeta_G/zeta_L Gurobi variables (CVaR VaR thresholds).
        self.d_G = (1 - self.A_G) * self.E_earnings_nc_G + self.A_G * cvar_nc_G
        self.d_L = (1 - self.A_L) * self.E_earnings_nc_L + self.A_L * cvar_nc_L

        log.info("Disagreement points: d_G=%.4f, d_L=%.4f", self.d_G, self.d_L)

    # @AndersDHansen do we need this function to exist?
    def _compute_strike_boundaries(self):
        pass