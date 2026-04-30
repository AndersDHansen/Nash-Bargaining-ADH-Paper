import logging

from ppa_symmetric_info.data_ops import DataLoader

log = logging.getLogger(__name__)


class Runner:
    def __init__(self, config):
        self.config = config
        log.info("Runner initialized")

    def load_data(self):
        """
        Load the data for the main analysis
        """
        log.info("Starting the first part of the data pipeline")
        self.data = DataLoader(self.config)
        log.info("Finished loading the data")

    def run(self):
        """
        Run all the workflow
        """
        log.info("Start running the whole workflow")
        self.load_data()
