import logging
import pandas as pd
from pathlib import Path
from types import SimpleNamespace
import gurobipy as gb
from omegaconf import OmegaConf
from .utils import get_logger

logger = get_logger(__name__)


class ModelNashBargaining:
    def __init__(self, data):
        self.data = data

        self._setup_gurobi_model()
        self._directories()

        logger.info("Nash Barganining model initalized")

    # Runner function to sequentially execute the workflow
    def run(self):
        self.build_variables()
        self.build_constraints()
        self.build_obj_func()
        self.solve()

    def _setup_gurobi_model(self):
        self.m = gb.Model()
        self.m.Params.NonConvex = 2  # Allow bilinear terms (S×M, gamma×S)
        self.m.Params.FeasibilityTol = 1e-6  # Constraint violation tolerance
        self.m.Params.OutputFlag = 0  # Suppress Gurobi console output
        self.m.Params.TimeLimit = 420  # Hard stop at 7 minutes
        self.m.Params.ObjScale = 1e-6  # Rescale log objective for numerical stability
        self.v = SimpleNamespace()  # Namespace for all Gurobi decision variables

    def _directories(self):
        # Path hierarchy — explicit attributes for every level
        self.path_results_root = Path(self.data.path_results).parent.parent  # results/
        self.path_run_type = Path(self.data.path_results).parent  # results/single_run/
        self.path_sim = Path(self.data.path_results)  # results/single_run/sim_name/
        self.path_figures = self.path_sim / "figures"

        # File paths
        self.path_model_lp = self.path_sim / "model.lp"
        self.path_model_mps = self.path_sim / "model.mps"
        self.path_results_csv = self.path_sim / "results.csv"
        self.path_config = self.path_sim / "config.yaml"
        self.path_log = self.path_sim / "run.log"

        # Create directories
        self.path_sim.mkdir(parents=True, exist_ok=True)
        self.path_figures.mkdir(exist_ok=True)

        # Save the resolved Hydra config for this run
        OmegaConf.save(self.data.config, self.path_config)

        # Add a file handler so the full pipeline log is captured in run.log
        handler = logging.FileHandler(self.path_log, mode="w")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] - %(message)s")
        )
        logging.getLogger().addHandler(handler)

    def build_variables(self):
        self._build_common_vars()

        if self.data.contract_type == "pap":
            self._build_pap_vars()

        elif self.data.contract_type == "baseload":
            self._build_baseload_vars()

    def _build_common_vars(self):
        """Add decision variables shared by both PAP and Baseload contracts.

        - Nash surplus (delta_G, delta_L): utility minus disagreement point for each party.
        - Log variables (log_delta_*): auxiliary vars for linearising the log Nash product.
        - Strike price (S): the contract price negotiated between generator and load.
        - CVaR threshold (cvar_zeta_*): Value-at-Risk level per party, scalar, used in CVaR definition.
        - CVaR shortfall (eta_*): per-scenario excess loss beyond the VaR threshold, indexed by scenario.
        """
        EPS = 1e-8

        # Utility of each party — unbounded below because load utility is a net cost (negative).
        # Positivity is enforced on the Nash surplus (delta_*) not on the utility itself.
        self.v.u_G = self.m.addVar(lb=-gb.GRB.INFINITY, name="u_G")
        self.v.u_L = self.m.addVar(lb=-gb.GRB.INFINITY, name="u_L")

        # Surplus of each party = utility under contract minus disagreement point.
        # Strictly positive lower bound so that log(surplus) is always defined.
        self.v.delta_G = self.m.addVar(lb=EPS, name="delta_G")
        self.v.delta_L = self.m.addVar(lb=EPS, name="delta_L")

        # Auxiliary vars for log-linearisation of the Nash product objective.
        # Unbounded below: log(delta) can be negative if delta < 1.
        # Linked to delta_* via addGenConstrLog in _build_common_cons.
        self.v.log_delta_G = self.m.addVar(lb=-gb.GRB.INFINITY, name="log_delta_G")
        self.v.log_delta_L = self.m.addVar(lb=-gb.GRB.INFINITY, name="log_delta_L")

        # Contract strike price [EUR/GWh], bounded by market-feasibility limits.
        self.v.S = self.m.addVar(
            lb=self.data.strikeprice_min,
            ub=self.data.strikeprice_max,
            name="S",
        )

        # VaR threshold for each party's CVaR computation (paper: zeta^S, zeta^B).
        # Unbounded because the threshold can be negative when losses are large.
        self.v.zeta_G = self.m.addVar(lb=-gb.GRB.INFINITY, name="zeta_G")
        self.v.zeta_L = self.m.addVar(lb=-gb.GRB.INFINITY, name="zeta_L")

        # Per-scenario shortfall above the VaR threshold (paper: eta^S_omega, eta^B_omega).
        # Non-negative by definition: shortfall is zero when the scenario loss is below the threshold.
        self.v.eta_G = self.m.addMVar(
            shape=self.data.num_scenarios, lb=0.0, name="eta_G"
        )
        self.v.eta_L = self.m.addMVar(
            shape=self.data.num_scenarios, lb=0.0, name="eta_L"
        )

        logger.info("Common variables added")

    def _build_pap_vars(self):
        """Add decision variables specific to the Pay-as-Produced contract.

        Share (gamma): fraction of the generator's actual production sold under the contract.
        """
        # Contract share in [0, gamma_max]; bilinear with S and production in the utility expressions.
        self.v.gamma = self.m.addVar(lb=0, ub=self.data.gamma_max, name="gamma")
        logger.info("Variables specific to Pay-as-Produced added")

    def _build_baseload_vars(self):
        """Add decision variables specific to the Baseload contract.

        Contract amount (M): fixed volume [GWh] delivered each period under the contract.
        """
        # Fixed delivery volume [GWh], bounded by contractually feasible range.
        self.v.M = self.m.addVar(
            lb=self.data.contract_amount_min,
            ub=self.data.contract_amount_max,
            name="M",
        )
        logger.info("Variables specific to Baseload added")

    # Build constraints
    def build_constraints(self):
        self._build_common_cons()

        if self.data.contract_type == "pap":
            self._build_pap_cons()
        elif self.data.contract_type == "baseload":
            self._build_baseload_cons()

    def _build_common_cons(self):

        # Natural log constraints
        self.m.addGenConstrLog(
            self.v.delta_G, self.v.log_delta_G, name="cons_log_delta_G"
        )
        self.m.addGenConstrLog(
            self.v.delta_L, self.v.log_delta_L, name="cons_log_delta_L"
        )
        logger.info("Common constraints added")

    def _build_pap_cons(self):

        logger.info("Constraints specific to Pay-as-produced added")

    def _build_baseload_cons(self):

        # Utility constraints — shape (years, scenarios), summed over years then weighted by prob.
        # Uses biased capture prices (asymmetric info) and discount factors, matching the thesis eq.
        earnings_G_matrix = self.data.discount_factors_G * (
            self.data.capture_price_G_biased * self.data.production_G
            + (self.v.S - self.data.price_G) * self.v.M
        )

        # Load's uncontracted cost uses its own consumption (load) at the biased capture price,
        # not the generator's production (production_L is a PAP-specific quantity).
        earnings_L_matrix = self.data.discount_factors_L * (
            -self.data.capture_price_L_biased * self.data.load_np
            + (self.data.price_L - self.v.S) * self.v.M
        )

        # Utility = expected profit + risk-aversion-weighted left-tail CVaR
        self.m.addConstr(
            self.v.u_G
            == (1 - self.data.A_G) * self.data.prob @ earnings_G_matrix.sum(axis=0)
            + self.data.A_G
            * (
                self.v.zeta_G
                - (1 / (1 - self.data.alpha)) * (self.data.prob @ self.v.eta_G)
            ),
            name="u_G_baseload",
        )
        self.m.addConstr(
            self.v.u_L
            == (1 - self.data.A_L) * self.data.prob @ earnings_L_matrix.sum(axis=0)
            + self.data.A_L
            * (
                self.v.zeta_L
                - (1 / (1 - self.data.alpha)) * (self.data.prob @ self.v.eta_L)
            ),
            name="u_L_baseload",
        )

        # Nash surplus = utility under contract minus disagreement point (precomputed in data_loader)
        self.m.addConstr(
            self.v.delta_G == self.v.u_G - self.data.zeta_G, name="nash_surplus_G"
        )
        self.m.addConstr(
            self.v.delta_L == self.v.u_L - self.data.zeta_L, name="nash_surplus_L"
        )

        # CVaR constraints — one per scenario (bilinear S×M handled by NonConvex=2).
        # earnings_G[s] = earnings_nc_G[s] + (disc_G_sum * S - lambda_disc_G[s]) * M
        # eta_G[s] >= zeta_G - earnings_G[s]
        self.m.addConstrs(
            (
                self.v.eta_G[s]
                >= self.v.zeta_G
                - self.data.earnings_nc_G[s]
                - (self.data.disc_G_sum * self.v.S - self.data.lambda_disc_G[s])
                * self.v.M
                for s in range(self.data.num_scenarios)
            ),
            name="eta_G_cvar",
        )
        # earnings_L[s] = earnings_nc_L[s] + (lambda_disc_L[s] - disc_L_sum * S) * M
        # eta_L[s] >= zeta_L - earnings_L[s]
        self.m.addConstrs(
            (
                self.v.eta_L[s]
                >= self.v.zeta_L
                - self.data.earnings_nc_L[s]
                - (self.data.lambda_disc_L[s] - self.data.disc_L_sum * self.v.S)
                * self.v.M
                for s in range(self.data.num_scenarios)
            ),
            name="eta_L_cvar",
        )

        logger.info("Constraints specific to Baseload added")

    # Build the objective funtion
    def build_obj_func(self):

        self.m.setObjective(
            (self.data.tau_G * self.v.log_delta_G + self.data.tau_L * self.v.log_delta_L),
            gb.GRB.MAXIMIZE,
        )
        logger.info("Objective function created")

    # Solve the actual model
    def solve(self):
        logger.info("Solving the model...")
        self.m.optimize()

        if self.m.Status == gb.GRB.INFEASIBLE:
            logger.error("Model is infeasible. Computing IIS...")
            self._compute_iis()
            return

        if self.m.Status != gb.GRB.OPTIMAL:
            logger.warning("Model did not reach optimality. Status: %d", self.m.Status)
            return

        logger.info("Model solved. Extracting results...")
        self._extract_results()
        self._save_model_files()

    def _compute_iis(self):
        self.m.computeIIS()
        path_iis = self.path_sim / "model.ilp"
        self.m.write(str(path_iis))
        logger.error("IIS written to %s", path_iis)

        logger.error("Infeasible constraints:")
        for c in self.m.getConstrs():
            if c.IISConstr:
                logger.error("  CONSTR  %s", c.ConstrName)
        for v in self.m.getVars():
            if v.IISLB:
                logger.error("  LB      %s >= %g", v.VarName, v.LB)
            if v.IISUB:
                logger.error("  UB      %s <= %g", v.VarName, v.UB)
        for gc in self.m.getGenConstrs():
            if gc.IISGenConstr:
                logger.error("  GENCON  %s", gc.GenConstrName)

    # Extract the results
    def _extract_results(self):
        # vars(SimpleNamespace) returns the underlying __dict__ of name→gurobi_obj pairs.
        # Only collect scalar gb.Var entries; indexed tuplediicts (eta_*) are CVaR auxiliaries
        # and are skipped here — add a separate export if per-scenario values are needed.
        scalars = {
            name: var.X for name, var in vars(self.v).items() if isinstance(var, gb.Var)
        }
        pd.Series(scalars, name="value").to_csv(self.path_results_csv, header=True)
        logger.info("Results extracted to %s", self.path_results_csv)

    def _save_model_files(self):
        self.m.write(str(self.path_model_lp))
        self.m.write(str(self.path_model_mps))
        logger.info("Model files saved to %s", self.path_sim)
