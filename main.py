from omegaconf import DictConfig, OmegaConf
import hydra
from ppa_symmetric_info.runner import Runner

@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg:DictConfig):
    runner = Runner(cfg)
    print(runner.config)
    print("Hello from nash-bargaining-adh-paper!")

if __name__ == "__main__":
    main()
