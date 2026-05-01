from dataclasses import dataclass, field
from pathlib import Path

from omegaconf import DictConfig

from ppa_symmetric_info.data_ops.scenario_generation import run_scenarios
from ppa_symmetric_info.data_ops.scenario_reduction import reduce_scenarios
from ppa_symmetric_info.utils import get_logger

log = get_logger(__name__)


@dataclass
class DataPreprocessor:
    config: DictConfig
    _reduced_dir: Path = field(init=False)
    _mc_dir: Path = field(init=False)

    def __post_init__(self):
        sg = self.config.scenario_gen
        processed_dir = Path(self.config.paths.processed.dir)

        mc_label = f"mc_normal_prices_{sg.num_scenarios_mc}" if sg.monte_price else f"mc_{sg.num_scenarios_mc}"
        self._mc_dir = processed_dir / mc_label
        self._reduced_dir = processed_dir / f"scenarios_reduced_{sg.num_scenarios_reduced}"

        self._mc_dir.mkdir(parents=True, exist_ok=True)
        self._reduced_dir.mkdir(parents=True, exist_ok=True)

        if self._reduced_scenarios_exist():
            log.info("Reduced scenarios already cached (%dy, %d) — nothing to do.", sg.years, sg.num_scenarios_reduced)
            return

        log.info("No cached scenarios found — running generation + reduction.")
        self._generate_mc_scenarios()
        self._reduce_scenarios()

    def _generate_mc_scenarios(self) -> None:
        sg = self.config.scenario_gen
        p = self.config.paths
        log.info("MC generation: %d scenarios x %dy, seed=%d", sg.num_scenarios_mc, sg.years, sg.seed)
        run_scenarios(
            years=sg.years,
            num_scenarios=sg.num_scenarios_mc,
            start_time=sg.start_time,
            price_csv_path=str(p.raw.price),
            prod_csv_path=str(p.raw.wind),
            consumption_csv_path=str(p.raw.consumption),
            capacity_mw=sg.capacity_mw,
            output_dir=str(self._mc_dir),
            seed=sg.seed,
            monte_price=sg.monte_price,
        )

    def _reduce_scenarios(self) -> None:
        sg = self.config.scenario_gen
        log.info("K-means reduction: %d MC -> %d representative, seed=%d", sg.num_scenarios_mc, sg.num_scenarios_reduced, sg.seed)
        reduce_scenarios(
            scenarios_dir=self._mc_dir,
            output_dir=self._reduced_dir,
            years=sg.years,
            num_scenarios_mc=sg.num_scenarios_mc,
            num_scenarios_reduced=sg.num_scenarios_reduced,
            monte_price=sg.monte_price,
            seed=sg.seed,
        )

    def _reduced_scenarios_exist(self) -> bool:
        sg = self.config.scenario_gen
        # probabilities file is always written last — its presence means a complete run
        sentinel = self._reduced_dir / f"probabilities_scenarios_reduced_{sg.years}y_{sg.num_scenarios_reduced}s.csv"
        return sentinel.exists()