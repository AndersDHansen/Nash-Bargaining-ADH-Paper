from ppa_symmetric_info.utils import get_logger

import gurobipy as gb


log = get_logger(__name__)


class ContractNegotiation:
    def __init__(self, data, config):
        log.info("ContractNegotiation initialized")
        self.data = data
        self.config = config

        self.initialize_model_data()
        self.compute_strike_boundaries()
        self.build_model()

    def initialize_model_data(self):
        # TODO: port from Code/contract_negotiation.py -> _initialize_model_data()
        pass

    def compute_strike_boundaries(self):
        # TODO: port from Code/contract_negotiation.py -> _compute_strike_boundaries()
        pass

    def build_model(self):
        # TODO: port from Code/contract_negotiation.py -> _build_variables() + _build_constraints() + _build_objective()
        pass