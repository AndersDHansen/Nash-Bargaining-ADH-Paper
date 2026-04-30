from omegaconf import DictConfig, OmegaConf
import hydra
import logging

from ppa_symmetric_info import Runner

log = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg: DictConfig):
    log.info("Starting the runner")
    runner = Runner(cfg)
    runner.run()


if __name__ == "__main__":
    main()
