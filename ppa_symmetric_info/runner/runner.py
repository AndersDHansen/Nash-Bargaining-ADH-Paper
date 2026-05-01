from ppa_symmetric_info.utils import get_logger
from ppa_symmetric_info.data_ops import DataLoader
from ppa_symmetric_info.data_ops import DataPreprocessor
from ppa_symmetric_info.model import ContractNegotiation

log = get_logger(__name__)


class Runner:
    def __init__(self, config):
        self.config = config
        log.info(
            "Runner initialized | contract_type=%s, run_sensitivity=%s",
            config.contract_type,
            config.run_sensitivity,
        )

    def run(self):
        """Execute the full pipeline end-to-end."""
        log.info("Starting full workflow")
        self.preprocess_data()
        self.load_data()
        self.solve_nbs_model()
        self.export_results()
        self.visualize_results()

    def preprocess_data(self):
        """Stage 1+2: generate Monte Carlo scenarios and reduce to representatives."""
        log.info("START - Scenario generation and reduction")
        DataPreprocessor(self.config)
        log.info("END - Scenario generation and reduction")

    def load_data(self):
        """Read config params and wire up scenario CSV paths into DataLoader."""
        log.info(
            "START - Data loading | opt_scenarios=%d, monte_price=%s",
            self.config.data.num_scenarios_reduced,
            self.config.data.monte_price,
        )
        self.data = DataLoader(self.config)
        log.info(
            "END - Data loading | %d opt scenarios, horizon=%dy",
            self.data.num_scenarios_opt,
            self.data.years,
        )

    def solve_nbs_model(self):
        """Solve the Nash Bargaining problem with Gurobi."""
        log.info("START - Nash Bargaining Solution")
        self.model = ContractNegotiation(self.data, self.config)
        log.info("END - Nash Bargaining Solution")

    def export_results(self):
        log.info("START - Exporting results | output_dir=%s", self.data.path_results)
        # TODO: port save_results_to_csv from Code/main_forecast.py
        log.info("END - Exporting results")

    def visualize_results(self):
        log.info("START - Generating plots | output_dir=%s", self.data.path_plots)
        # TODO: port Plotting_Class from Code/plotting/
        log.info("END - Generating plots")