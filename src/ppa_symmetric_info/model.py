import logging
from pathlib import Path
import gurobipy as gb
from omegaconf import OmegaConf
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
        self.m.write(str(self.path_model_lp))
        self.m.write(str(self.path_model_mps))
        logger.info("Model files saved to %s", self.path_sim)
