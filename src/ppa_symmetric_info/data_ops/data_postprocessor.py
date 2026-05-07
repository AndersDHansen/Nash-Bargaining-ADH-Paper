import pandas as pd
from ..utils import get_logger, cvar_left

logger = get_logger(name=__name__)


class DataPostprocessor:
    def __init__(self, model):
        self.model = model
        self.data = model.data

        logger.info("DataPostprocessor initialized")

    def run(self):
        """Extract results from the solved model and persist them to disk."""
        self.extract_results()
        self.save_results()

    def extract_results(self):
        """Compute post-solve scalars and per-scenario earnings for both parties."""
        d = self.data
        v = self.model.v
        S = v.S.X

        earnings_G, earnings_L = self._contract_earnings(S)
        earnings_G_cp, earnings_L_cp = self._capture_price_earnings()

        cvar_G = cvar_left(earnings_G, d.prob, d.alpha)
        cvar_L = cvar_left(earnings_L, d.prob, d.alpha)
        utility_G = (1 - d.A_G) * float((d.prob * earnings_G).sum()) + d.A_G * cvar_G
        utility_L = (1 - d.A_L) * float((d.prob * earnings_L).sum()) + d.A_L * cvar_L

        delta_G = utility_G - d.d_G
        delta_L = utility_L - d.d_L

        self.scalars = {
            "objective_value":  self.model.m.ObjVal,
            "S_EUR_MWh":        S * 1e3,
            "disagreement_G":   d.d_G,
            "disagreement_L":   d.d_L,
            "delta_G":          delta_G,
            "delta_L":          delta_L,
            "nash_product":     delta_G * delta_L,
            "utility_G":        utility_G,
            "utility_L":        utility_L,
            "cvar_G":           cvar_G,
            "cvar_L":           cvar_L,
            "utility_G_cp":     (1 - d.A_G) * float((d.prob * earnings_G_cp).sum()) + d.A_G * cvar_left(earnings_G_cp, d.prob, d.alpha),
            "utility_L_cp":     (1 - d.A_L) * float((d.prob * earnings_L_cp).sum()) + d.A_L * cvar_left(earnings_L_cp, d.prob, d.alpha),
            **self._contract_scalars(S),
        }

        self.earnings = pd.DataFrame({
            "earnings_G":    earnings_G,
            "earnings_L":    earnings_L,
            "earnings_G_cp": earnings_G_cp,
            "earnings_L_cp": earnings_L_cp,
        })

        logger.info(
            "Results extracted: S=%.4f EUR/MWh, delta_G=%.4f, delta_L=%.4f, Nash=%.6f",
            S * 1e3, delta_G, delta_L, delta_G * delta_L,
        )

    def save_results(self):
        """Write scalars and per-scenario earnings to CSV in the simulation output directory."""
        pd.Series(self.scalars, name="value").to_csv(
            self.model.path_sim / "results_summary.csv", header=True
        )
        self.earnings.to_csv(self.model.path_sim / "results_earnings.csv")
        logger.info("Results saved to %s", self.model.path_sim)

    def _contract_earnings(self, S):
        """Return per-scenario earnings arrays (earnings_G, earnings_L) under the negotiated contract."""
        d = self.data
        v = self.model.v
        if d.contract_type == "baseload":
            M = v.M.X
            settlement_G = M * (d.disc_G_sum * S - d.lambda_disc_G)
            settlement_L = M * (d.lambda_disc_L - d.disc_L_sum * S)
        else:
            gamma = v.gamma.X
            settlement_G = gamma * (S * d.pap_prod_disc_G - d.earnings_nc_G)
            settlement_L = gamma * (d.pap_gamma_coeff_L - S * d.pap_prod_disc_L)
        return d.earnings_nc_G + settlement_G, d.earnings_nc_L + settlement_L

    def _capture_price_earnings(self):
        """Counterfactual earnings if the contract strike price equalled the average capture price."""
        d = self.data
        v = self.model.v
        cp_G_disc = float((d.discount_factors_G * d.capture_price_G_avg).sum())
        cp_L_disc = float((d.discount_factors_L * d.capture_price_G_avg).sum())
        if d.contract_type == "baseload":
            M = v.M.X
            settlement_G_cp = M * (cp_G_disc - d.lambda_disc_G)
            settlement_L_cp = M * (d.lambda_disc_L - cp_L_disc)
        else:
            gamma = v.gamma.X
            cp_pap_G = (d.discount_factors_G * d.capture_price_G_avg * d.production_G).sum(axis=0)
            cp_pap_L = (d.discount_factors_L * d.production_G * d.capture_price_G_avg).sum(axis=0)
            settlement_G_cp = gamma * (cp_pap_G - d.earnings_nc_G)
            settlement_L_cp = gamma * (d.pap_gamma_coeff_L - cp_pap_L)
        return d.earnings_nc_G + settlement_G_cp, d.earnings_nc_L + settlement_L_cp

    def _contract_scalars(self, S):
        """Return contract-type-specific scalar results (volume, unit conversions)."""
        d = self.data
        v = self.model.v
        if d.contract_type == "baseload":
            M = v.M.X
            return {"M_GWh_year": M, "M_MWh_h": M / 8760 * 1e3}
        else:
            gamma = v.gamma.X
            return {
                "gamma":       gamma,
                "M_GWh_year":  gamma * d.generator_contract_capacity * 8760 * 1e-3,
                "M_MWh_h":     gamma * d.generator_contract_capacity,
            }

