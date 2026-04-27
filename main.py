from omegaconf import DictConfig, OmegaConf
import hydra
import ppa_symmetric_info

@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg:DictConfig):
    print("Hello from nash-bargaining-adh-paper!")
    print(cfg)

if __name__ == "__main__":
    main()
