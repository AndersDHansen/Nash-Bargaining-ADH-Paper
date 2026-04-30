from ppa_symmetric_info.utils import get_logger
from ppa_symmetric_info.data_ops import DataLoader
from ppa_symmetric_info.data_ops import DataPreprocessor
from ppa_symmetric_info.model import ContractNegotiation

log = get_logger(__name__)


class Runner:
    def __init__(self, config):
        self.config = config
        log.info(
            "Runner initialized with config: contract_type=%s, sensitivity=%s",
            config.contract_type,
            config.sensitivity,
        )

    def run(self):
        log.info("Starting full workflow")
        self.preprocess_data()  # generate scenario CSVs from raw wind/solar/price data
        self.load_data()  # load config params + read those CSVs into InputData
        self.solve_nbs_model()
        self.export_results()
        self.visualize_results()

    def preprocess_data(self):
        log.info("START - Scenario generation and reduction")

        DataPreprocessor(self.config)

        log.info("END - Scenario generation and reduction")

    def load_data(self):
        log.info(
            "START - Data loading | scenarios=%d, monte_price=%s",
            self.config.opt_params.num_scenarios,
            self.config.scenarios.monte_price,
        )
        self.data = DataLoader(self.config)
        log.info(
            "END - Data loading | paths resolved, %d opt scenarios ready",
            self.data.num_scenarios_opt,
        )

    def solve_nbs_model(self):
        log.info("START - Nash Bargaining Solution")

        self.model = ContractNegotiation(self.config, self.data)

        log.info("END - Nash Bargaining Solution")

    def export_results(self):
        log.info("START - Exporting results | output_dir=%s", self.data.path_results)
        # TODO: save_results_to_csv
        log.info("END - Exporting results")

    def visualize_results(self):
        log.info("START - Generating plots | output_dir=%s", self.data.path_plots)
        # TODO: Plotting_Class
        log.info("END - Generating plots")
