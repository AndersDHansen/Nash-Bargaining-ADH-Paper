from ppa_symmetric_info.utils import get_logger

import gurobipy as gb


log = get_logger(__name__)


class ContractNegotiation:
    def __init__(self, data, config):
        log.info("The model for the contract negotiation is alive")
        self.data = data
        self.config = config
        
        # Modules to be exectued
        
        self.initialize_model_data()
        self.compute_strike_bnoudaries()
        self.build_model()
        
        
    def initialize_model_data(self):
        pass
    
    def compute_strike_boundaries(self):
        pass
    
    def build_model(self):
        pass