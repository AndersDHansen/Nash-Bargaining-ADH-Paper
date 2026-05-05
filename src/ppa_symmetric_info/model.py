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

        Nash surplus (delta_G, delta_L): utility minus disagreement point for each party.
        Log variables (log_delta_*): auxiliary vars for linearising the log Nash product.
        Strike price (S): the contract price negotiated between generator and load.
        CVaR threshold (cvar_zeta_*): Value-at-Risk level per party, scalar, used in CVaR definition.
        CVaR shortfall (eta_*): per-scenario excess loss beyond the VaR threshold, indexed by scenario.
        """
        EPS = 1e-8

        # Surplus of each party = utility under contract minus disagreement point.
        # Strictly positive lower bound so that log(surplus) is always defined.
        self.v.delta_G = self.m.addVar(lb=EPS, name="delta_G")
        self.v.delta_L = self.m.addVar(lb=EPS, name="delta_L")

        # Auxiliary vars for log-linearisation of the Nash product objective.
        # Linked to delta_* via addGenConstrLog in _build_common_cons.
        self.v.log_delta_G = self.m.addVar(name="log_delta_G")
        self.v.log_delta_L = self.m.addVar(name="log_delta_L")

        # Contract strike price [EUR/GWh], bounded by market-feasibility limits.
        self.v.S = self.m.addVar(
            lb=self.data.strikeprice_min,
            ub=self.data.strikeprice_max,
            name="S",
        )

        # VaR threshold for each party's CVaR computation (paper: zeta^S, zeta^B).
        # Unbounded because the threshold can be negative when losses are large.
        self.v.cvar_zeta_G = self.m.addVar(lb=-gb.GRB.INFINITY, name="cvar_zeta_G")
        self.v.cvar_zeta_L = self.m.addVar(lb=-gb.GRB.INFINITY, name="cvar_zeta_L")

        # Per-scenario shortfall above the VaR threshold (paper: eta^S_omega, eta^B_omega).
        # Non-negative by definition: shortfall is zero when the scenario loss is below the threshold.
        self.v.eta_G = self.m.addVars(self.data.scenarios, lb=0.0, name="eta_G")
        self.v.eta_L = self.m.addVars(self.data.scenarios, lb=0.0, name="eta_L")

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

        logger.info("Common constraints added")

    def _build_pap_cons(self):

        logger.info("Constraints specific to Pay-as-produced added")

    def _build_baseload_cons(self):

        logger.info("Constraints specific to Baseload added")

    # Build the objective funtion
    def build_obj_func(self):

        if self.data.contract_type == "pap":
            self._build_obj_pap()
        elif self.data.contract_type == "baseload":
            self._build_obj_baseload()

    def _build_obj_pap(self):
        logger.info("Objective created for PAP contract")

    def _build_obj_baseload(self):
        logger.info("Objective created for Baseload contract")

    # Solve the actual model
    def solve(self):
        logger.info("Solving the model...")
        self.m.optimize()
        if self.m.Status != gb.GRB.OPTIMAL:
            logger.warning("Model did not reach optimality. Status: %d", self.m.Status)
            return
        logger.info("Model solved. Extracting results...")
        self._extract_results()
        self._save_model_files()

    # Extract the results
    def _extract_results(self):
        # vars(SimpleNamespace) returns the underlying __dict__ of name→gurobi_obj pairs.
        # Only collect scalar gb.Var entries; indexed tuplediicts (eta_*) are CVaR auxiliaries
        # and are skipped here — add a separate export if per-scenario values are needed.
        scalars = {
            name: var.X
            for name, var in vars(self.v).items()
            if isinstance(var, gb.Var)
        }
        pd.Series(scalars, name="value").to_csv(self.path_results_csv, header=True)
        logger.info("Results extracted to %s", self.path_results_csv)

    def _save_model_files(self):
        self.m.write(str(self.path_model_lp))
        self.m.write(str(self.path_model_mps))
        logger.info("Model files saved to %s", self.path_sim)
