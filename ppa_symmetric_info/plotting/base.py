"""
Base mixin class for the plotting package.
"""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from utils import calculate_cvar_left, weighted_expected_value
from sklearn.linear_model import LinearRegression
from matplotlib.colors import LinearSegmentedColormap, to_rgb
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick

cmap_red_green=LinearSegmentedColormap.from_list('rg',["r", "w", "g"], N=256)
# Create a custom colormap that transitions from white to very light gray



class PlottingBase:
    """
    Handles plotting of results from the power system contract negotiation simulation.
    """
    def __init__(self, contract_model_data, CP_results_df, CP_earnings_df,
                 risk_sensitivity_df, risk_earnings_df,
                 price_bias_sensitivity_df,
                 price_sensitivity_mean_df, price_sensitivity_std_df,
                 production_bias_sensitivity_df,
                 production_sensitivity_mean_df, production_sensitivity_std_df,
                 load_sensitivity_mean_df, load_sensitivity_std_df,
                 gen_CR_sensitivity_df, load_CR_sensitivity_df,
                 boundary_results_df_price, boundary_results_df_production, negotiation_sensitivity_df,negotiation_earnings_df,
                 negotiation_vs_risk_df,elasticity_vs_risk_df , bias_risk_elasticity_df,
                 styles=None):

        self.cm_data = contract_model_data
        self.CP_results_df = CP_results_df
        self.CP_earnings_df = CP_earnings_df
        self.risk_sensitivity_df = risk_sensitivity_df
        self.earnings_risk_sensitivity_df = risk_earnings_df
        self.price_bias_sensitivity_df = price_bias_sensitivity_df
        self.production_bias_sensitivity_df = production_bias_sensitivity_df
        self.price_sensitivity_mean_df = price_sensitivity_mean_df
        self.price_sensitivity_std_df = price_sensitivity_std_df
        self.production_sensitivity_mean_df = production_sensitivity_mean_df
        self.production_sensitivity_std_df = production_sensitivity_std_df
        self.load_sensitivity_mean_df = load_sensitivity_mean_df
        self.load_sensitivity_std_df = load_sensitivity_std_df
        self.load_CR_sensitivity_df = load_CR_sensitivity_df
        self.gen_CR_sensitivity_results = gen_CR_sensitivity_df
        self.boundary_results_price = boundary_results_df_price
        self.boundary_results_production = boundary_results_df_production
        self.negotiation_sensitivity_df = negotiation_sensitivity_df
        self.negotiation_earnings_df = negotiation_earnings_df
        self.negotiation_vs_risk_df = negotiation_vs_risk_df
        self.elasticity_vs_risk_df = elasticity_vs_risk_df
        self.bias_risk_elasticity_df = bias_risk_elasticity_df
        # plotting styles
        self.legendsize = 12+2
        self.labelsize = 16+2
        self.titlesize = 17+2
        self.suptitlesize = 19+1
        #self.alpha_sensitivity_df = alpha_sensitivity_df
        #self.alpha_earnings_df = alpha_earnings_df

        self.plots_dir = os.path.join(os.path.dirname(__file__), 'Plots')
        os.makedirs(self.plots_dir, exist_ok=True)

    def _safe_local_elasticity_single(self, df_in: pd.DataFrame, factor_col: str, metric_col: str, baseline: float) -> float | None:
        """Single-metric local elasticity with central difference or local linear fit. Returns float or None/NaN.
        E = (dY/dX) * (X0 / Y0), never fills NaN with zeros.
        """
        if df_in is None or df_in.empty:
            return np.nan
        cols = [factor_col, metric_col]
        if any(c not in df_in.columns for c in cols):
            return np.nan
        df = df_in[cols].copy()
        df = df[np.isfinite(df[factor_col]) & np.isfinite(df[metric_col])]
        if df.empty:
            return np.nan
        df = df.sort_values(factor_col)
        # Round to 5 decimals to remove floating noise
        x = df[factor_col].astype(float).round(5).values
        y = df[metric_col].astype(float).round(5).values
        # Find neighbors around baseline
        left = np.where(x < baseline)[0]
        right = np.where(x > baseline)[0]
        y0 = np.nan
        slope = np.nan
        eq = np.where(np.isclose(x, baseline))[0]
        if eq.size > 0:
            y0 = y[eq[0]]
        if left.size > 0 and right.size > 0:
            iL = left[-1]
            iR = right[0]
            xL, yL = x[iL], y[iL]
            xR, yR = x[iR], y[iR]
            if xR != xL:
                slope = (yR - yL) / (xR - xL)
                if not np.isfinite(y0):
                    y0 = yL + (baseline - xL) * slope
        if not np.isfinite(slope):
            if x.size >= 2 and np.unique(x).size >= 2:
                k = min(5, x.size)
                order = np.argsort(np.abs(x - baseline))[:k]
                coeffs = np.polyfit(x[order], y[order], deg=1)
                slope = coeffs[0]
                y0 = np.polyval(coeffs, baseline)
        if not np.isfinite(slope) or not np.isfinite(y0) or np.isclose(y0, 0.0):
            return np.nan
        return float(slope * (baseline / y0))

    def _color_for_risk(self, value: float, kind: str = 'A_L'):
        """Return a consistent color for a given risk value (A_L or A_G),
        aligned with the Set2 palette used elsewhere.
        We snap to a canonical set of values for stable colors across plots.
        """
        try:
            v = round(float(value), 2)
        except Exception:
            v = value
        canonical = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
        base_pal = sns.color_palette('Set2', n_colors=len(canonical))
        # Slightly darken to avoid too-light tones
        pal = [tuple(min(1.0, max(0.0, c*0.85)) for c in rgb) for rgb in base_pal]
        if v in canonical:
            idx = canonical.index(v)
        else:
            # Nearest bucket for unseen value
            idx = np.searchsorted(canonical, v)
            idx = max(0, min(idx, len(canonical)-1))
        return pal[idx]
