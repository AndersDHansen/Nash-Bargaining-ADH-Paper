from .utils import get_logger
from .data_ops import DataLoader, DataPreprocessor, DataPostprocessor, run_sensitivity
from .model import ModelNashBargaining

log = get_logger(__name__)


class Runner:
    """The workflow manager of the full modelling pipeline.

    Stages run in order:
      1. preprocess_data   — generate and reduce Monte Carlo scenarios (skipped if cached)
      2. load_data         — read scenario CSVs and config into a DataLoader
      3. solve_nbs_model   — build and solve the Nash Bargaining model with Gurobi
      4. postprocess_data  — extract and save results
      5. visualize_results — produce plots

    For sensitivity analysis, stages 2-4 are delegated to run_sensitivity().
    """

    def __init__(self, config):
        self.config = config
        log.info(
            "Runner initialized: contract=%s, sim=%s, sensitivity=%s",
            config.experiment.contract_type,
            config.experiment.sim_name,
            config.run_sensitivity,
        )

    def run(self):
        self.preprocess_data()

        if not self.config.run_sensitivity:
            self.single_run()
        else:
            self.sensitivity_run()

    def single_run(self):
        """Run the base-case pipeline: load data, solve, postprocess, visualise."""
        self.load_data()
        self.solve_nbs_model()
        self.postprocess_data()
        self.visualize_results()

    def sensitivity_run(self):
        """Run the sensitivity sweep defined in config.sensitivity."""
        run_sensitivity(self.config)

    def preprocess_data(self):
        """Generate Monte Carlo scenarios and reduce to representatives."""
        DataPreprocessor(self.config).run()

    def load_data(self):
        """Read scenario CSVs and config into a DataLoader."""
        self.data = DataLoader(self.config)

    def solve_nbs_model(self):
        """Build and solve the Nash Bargaining model for the current data."""
        self.nbs_model = ModelNashBargaining(self.data)
        self.nbs_model.run()

    def postprocess_data(self):
        """Extract and save results from the solved model."""
        DataPostprocessor(self.nbs_model).run()

    def visualize_results(self):
        # TODO: port Plotting_Class from Code/plotting/
        pass
