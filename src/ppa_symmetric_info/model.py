import types

import numpy as np
import gurobipy as gp

from ppa_symmetric_info.utils import get_logger

log = get_logger(__name__)


class ContractNegotiation:
    def __init__(self, data):
        self.data = data
        self.contract_type = data.contract_type

        # Simple namespaces to group results, variables, and constraints
        self.results = types.SimpleNamespace()
        self.variables = types.SimpleNamespace()
        self.constraints = types.SimpleNamespace()

        self._initialize_model_data()
        self._compute_strike_boundaries()
        self._build_model()

    # ── Stage 1: derived statistics and disagreement points ──────────────────

    def _initialize_model_data(self):
        """Compute discount factors, biased scenario views, and disagreement utilities.

        Populates self.data with:
          - discount_factors_G_arr / discount_factors_L_arr  (T x 1)
          - price_G, price_L         (biased price views per party)
          - production_G, production_L
          - net_earnings_no_contract_priceG_G / priceL_L  (per-scenario vectors)
          - CVaR_no_contract_priceG_G / priceL_L
          - Zeta_G, Zeta_L           (disagreement-point utilities)
          - SR_star_new, SU_star_new (strike-price thresholds at M=0, Baseload only)
        """
        # TODO: port from Code/contract_negotiation.py -> _initialize_model_data()
        pass

    # ── Stage 2: strike-price boundaries via scipy ───────────────────────────

    def _compute_strike_boundaries(self):
        """Find strike-price boundaries (SR*, SU*) via scipy optimisation.

        Baseload: SLSQP at M = contract_amount_max.
        PAP:      trust-constr at gamma = 0.
        Results stored as self.data.SR_star_new and self.data.SU_star_new.
        """
        # TODO: port from Code/contract_negotiation.py -> _compute_strike_boundaries()
        pass

    # ── Stage 3: Gurobi model ────────────────────────────────────────────────

    def _build_model(self):
        """Create Gurobi model, set params, build variables + constraints + objective."""
        self.model = gp.Model("Nash Bargaining")
        self.model.Params.NonConvex = 2
        self.model.Params.FeasibilityTol = 1e-6
        self.model.Params.OutputFlag = 0
        self.model.Params.TimeLimit = 420
        self.model.Params.ObjScale = 1e-6

        self._build_variables()

        if self.contract_type == "PAP":
            self._build_constraints_pap()
            self._build_objective_pap()
        else:
            self._build_constraints_baseload()
            self._build_objective_baseload()

        self.model.update()

    def _build_variables(self):
        """Add decision variables shared by both contract types."""
        # TODO: port from Code/contract_negotiation.py -> _build_variables()
        pass

    def _build_common_constraints(self):
        """Add constraints shared by Baseload and PAP (strike price bounds, log linking)."""
        # TODO: port from Code/contract_negotiation.py -> _build_common_constraints()
        pass

    def _build_constraints_baseload(self):
        """Add Baseload-specific constraints (contract amount bounds, CVaR eta)."""
        self._build_common_constraints()
        # TODO: port from Code/contract_negotiation.py -> _build_constraints()
        pass

    def _build_constraints_pap(self):
        """Add PAP-specific constraints (gamma bounds, CVaR eta)."""
        self._build_common_constraints()
        # TODO: port from Code/contract_negotiation.py -> _build_constraints_PAP()
        pass

    def _set_nash_objective(self, UG, UL):
        """Set the Nash bargaining objective given utility expressions UG and UL.

        Dispatches on tau_G / tau_L:
          - tau_G == 1: maximise UG subject to UL >= Zeta_L
          - tau_L == 1: maximise UL subject to UG >= Zeta_G
          - otherwise:  maximise tau_G * log(UG - Zeta_G) + tau_L * log(UL - Zeta_L)
        """
        # TODO: port from Code/contract_negotiation.py -> _set_nash_objective()
        pass

    def _build_objective_baseload(self):
        """Build expected utility expressions and objective for Baseload."""
        # TODO: port from Code/contract_negotiation.py -> _build_objective()
        pass

    def _build_objective_pap(self):
        """Build expected utility expressions and objective for PAP."""
        # TODO: port from Code/contract_negotiation.py -> _build_objectives_PAP()
        pass

    # ── Stage 4: solve and extract ───────────────────────────────────────────

    def solve(self):
        """Solve the model and extract results. Raises if not optimal."""
        self.model.optimize()
        if self.model.status != GRB.OPTIMAL:
            self.results.optimal = False
            raise RuntimeError(f"Model did not solve to optimality (status {self.model.status})")
        self.results.optimal = True
        self._extract_results()
        self._log_results()

    def _extract_results(self):
        """Read variable values from the solved model into self.results."""
        # TODO: port from Code/contract_negotiation.py -> _save_results()
        pass

    def _log_results(self):
        """Log key results."""
        # TODO: port from Code/contract_negotiation.py -> display_results()
        pass
