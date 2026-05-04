from pathlib import Path
import gurobipy as gb
from .utils import get_logger

logger = get_logger(__name__)


class ModelNashBargaining:
    def __init__(self, data):
        self.data = data
        self.m = gb.Model()
        self._directories()

        logger.info("Nash Barganining model initalized")

    def run(self):
        self.build_variables()
        self.build_constraints()
        self.build_obj_func()
        self.solve()

    def _directories(self):
        self.path_res = Path(self.data.path_results)
        self.path_res.mkdir(parents=True, exist_ok=True)

        self.path_figures = self.path_res / "figures"
        self.path_figures.mkdir(parents=True, exist_ok=True)

    def build_variables(self):
        self._build_gen_vars()

        if self.data.contract_type == "pap":
            self._build_pap_vars()

        elif self.data.contract_type == "baseload":
            self._build_baseload_vars()

    def _build_gen_vars(self):

        logger.info("General variables added")

    def _build_pap_vars(self):

        logger.info("Vairables specific to Pay-as-produced added")

    def _build_baseload_vars(self):

        logger.info("Vairables specific to Baseload added")

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
        logger.info("Results extracted")

    def _save_model_files(self):

        self.m.write(str(self.path_res / "model.lp"))
        self.m.write(str(self.path_res / "model.mps"))
        logger.info("Model files saved to %s", self.path_res)
