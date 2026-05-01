from omegaconf import DictConfig
import hydra
import logging

from ppa_symmetric_info import Runner

log = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg: DictConfig):
    log.info("Starting the runner")
    runner = Runner(cfg)

    #runner.preprocess_data()
    runner.load_data()          # next step: load scenario CSVs for the optimizer
    # runner.solve_nbs_model()    # TODO: port ContractNegotiation from Code/
    # runner.export_results()     # TODO: port save_results_to_csv from Code/
    # runner.visualize_results()  # TODO: port Plotting_Class from Code/


if __name__ == "__main__":
    main()
