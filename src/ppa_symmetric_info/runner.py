from .utils import get_logger
from .data_ops import DataLoader, DataPreprocessor, DataPostprocessor
from .model import ModelNashBargaining

log = get_logger(__name__)


class Runner:
    """Orchestrates the full modelling pipeline.

    Stages run in order:
      1. preprocess_data  — generate and reduce Monte Carlo scenarios (skipped if cached)
      2. load_data        — read scenario CSVs and config into a DataLoader
      3. solve_nbs_model  — build and solve the Nash Bargaining model with Gurobi
      4. export_results   — write results to CSV / JSON
      5. visualize_results — produce plots

    For a single base-case run, call run(). Sensitivity analysis will wrap
    stages 3-4 in a parameter loop on top of the same DataLoader instance.
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
        self.load_data()
        self.solve_nbs_model()
        self.postprocess_data()
        self.visualize_results()

    def preprocess_data(self):
        """Generate Monte Carlo scenarios and reduce to representatives.

        Checks for a cached result first and skips generation if already done.
        """
        DataPreprocessor(self.config).run()

    def load_data(self):
        """Read scenario CSVs and all config parameters into a DataLoader.

        After this step, self.data holds the scenario matrices and every
        scalar the model needs. Nothing downstream touches the config directly.
        """
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
