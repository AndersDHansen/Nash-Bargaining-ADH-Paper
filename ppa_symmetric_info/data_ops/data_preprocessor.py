from dataclasses import dataclass
from omegaconf import DictConfig
from ppa_symmetric_info.utils import get_logger

log = get_logger(__name__)

@dataclass
class DataPreprocessor:
    config: DictConfig

    def __post_init__(self):
        log.info("I am Iron mannnn")

        # TODO: generate_scenarios + scenario_reduction

        pass
