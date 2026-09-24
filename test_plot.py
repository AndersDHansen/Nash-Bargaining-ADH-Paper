"""Rebuild the figures from results already on disk, without re-solving.

uv run python test_plot.py
uv run python test_plot.py experiment=default_pap
"""

import hydra

import ppa_symmetric_info


@hydra.main(version_base=None, config_name="config", config_path="config")
def main(cfg):
    runner = ppa_symmetric_info.Runner(cfg)
    runner.plot_figures()


if __name__ == "__main__":
    main()
