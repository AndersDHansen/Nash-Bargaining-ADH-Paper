"""Configuration for scenario generation (generate_scenarios.py)."""

import pandas as pd

# ── Monte Carlo settings ──
YEARS = 20
NUM_SCENARIOS = 100_000
MONTE_PRICE = False
START_TIME = pd.Timestamp("2025-01-01")
SEED = 42

# ── Data source paths (relative to repository root) ──
WIND_CSV = "Code/Data/Wind/combined_wind_data.csv"
SOLAR_CSV = "Code/Data/Solar/combined_solar_data.csv"
PRICE_CSV = "Code/Data/EnergyReport.csv"
CONSUMPTION_CSV = "Code/Data/ConsumptionIndustry.csv"

# ── Generator ──
CAPACITY_MW = 30

# ── Output ──
OUTPUT_DIR = "Code/scenarios"
