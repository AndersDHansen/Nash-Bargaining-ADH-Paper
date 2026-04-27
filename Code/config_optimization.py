"""Configuration for optimization and sensitivity analysis (main_forecast.py)."""

import os

import numpy as np

# ── Output paths (relative to Code/) ──
PLOTS_FOLDER = os.path.join(os.path.dirname(__file__), "Plots")
RESULTS_FOLDER = os.path.join(os.path.dirname(__file__), "Results")

# ── Model parameters ──
A_L = 0.5                # Load risk aversion
A_G = 0.5                # Generator risk aversion
SCENARIO_TIME_HORIZON = 20   # Must match generated scenarios
OPT_TIME_HORIZON = 20        # Optimization horizon (years)
NUM_SCENARIOS = 500           # Must match generated scenarios

D_G = 0.00               # Generator discount rate
D_L = 0.00               # Load discount rate

# ── Boolean flags ──
MONTE_PRICE = False       # Use Monte Carlo price scenarios
BARTER = True            # McCormick relaxation
SENSITIVITY = False       # Run sensitivity analyses
DISCOUNT = True           # Include discounting in objective

# ── Negotiation ──
TAU_L = 0.5               # Load negotiation power [0, 1]
TAU_G = 1 - TAU_L        # Generator negotiation power
CONTRACT_TYPE = "Baseload"  # "Baseload" or "PAP"

# ── Sensitivity analysis ──
SELECTED_ANALYSES: list[str] = ["elasticity_vs_risk"]
NUM_SENSITIVITY = 5

A_G_VALUES = np.array([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
A_L_VALUES = np.array([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
TAU_L_VALUES = np.linspace(0, 1, NUM_SENSITIVITY)
TAU_G_VALUES = 1 - TAU_L_VALUES

# ── Contract / system bounds (used in dataloader.py) ──
GENERATOR_CONTRACT_CAPACITY = 30      # MW
RETAIL_PRICE = 0 * 1e-3               # EUR/MWh
STRIKEPRICE_MIN = 40 * 1e-3           # EUR/MWh
STRIKEPRICE_MAX = 120 * 1e-3          # EUR/MWh (overwritten by load_data_from_provider)
GAMMA_MAX = 1
ALPHA = 0.95                          # CVaR confidence level
