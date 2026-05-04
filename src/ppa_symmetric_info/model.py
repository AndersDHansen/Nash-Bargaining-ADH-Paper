import gurobipy as gb
from .utils import get_logger

logger = get_logger(__name__)


class ModelNashBargaining:
    def __init__(self, data):
        self.data = data
        self.m = gb.Model()

        logger.info("Nash Barganining model initalized")

    def run(self):
        self.build_variables()
        self.build_constraints()
        self.build_obj_func()
        self.solve()

    # Build model variables

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

    def build_obj_func(self):

        if self.data.contract_type == "pap":
            self._build_obj_pap()
        elif self.data.contract_type == "baseload":
            self._build_obj_baseload()

    def _build_obj_pap(self):
        logger.info("Objective created for PAP contract")

    def _build_obj_baseload(self):
        logger.info("Objective created for Baseload contract")

    def solve(self):
        logger.info("Solving the model...")
        self.m.optimize()
        if self.m.Status != gb.GRB.OPTIMAL:
            logger.warning("Model did not reach optimality. Status: %d", self.m.Status)
            return
        logger.info("Model solved. Extracting results...")
        self._extract_results()

    def _extract_results(self):
        logger.info("Results extracted")
