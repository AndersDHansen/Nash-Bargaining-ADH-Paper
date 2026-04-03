"""
Sensitivity analysis module for contract negotiation.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import copy
from tqdm import tqdm
from contract_negotiation import ContractNegotiation
from utils import weighted_expected_value
import gurobipy as gp


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _tag(df: pd.DataFrame, factor_name: str) -> pd.DataFrame:
    """Tag a DataFrame with a Factor column."""
    out = df.copy()
    out['Factor'] = factor_name
    return out


# ---------------------------------------------------------------------------
# Generic sensitivity runner
# ---------------------------------------------------------------------------

def _run_sensitivity(
    name: str,
    input_data_base: 'InputData',
    param_grid: list,
    modify_fn: Callable[..., dict[str, Any]],
    desc: str = "",
    collect_earnings: bool = False,
    earnings_fn: Callable[..., dict[str, Any]] | None = None,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """Generic loop for sensitivity analyses.

    Parameters
    ----------
    name : str
        Human-readable name printed at start/end.
    input_data_base : object
        Base input data (deep-copied each iteration).
    param_grid : list
        Each element is passed to *modify_fn* (can be scalar or tuple).
    modify_fn : callable(input_data_copy, param) -> dict
        Mutates the copy in-place **and** returns a dict of extra columns
        for the results row.
    desc : str
        tqdm progress bar description.
    collect_earnings : bool
        If True, also collect per-iteration earnings DataFrames.
    earnings_fn : callable(input_data_copy, contract_model, param) -> dict
        Required when *collect_earnings* is True.  Returns a dict whose
        values are arrays (one per scenario) to build an earnings DataFrame.

    Returns
    -------
    results_df  or  (results_df, earnings_df)
    """
    print(f"\n--- Starting {name} ---")
    results_list = []
    earnings_list = [] if collect_earnings else None

    for param in tqdm(param_grid, desc=desc or name):
        current_input_data = copy.deepcopy(input_data_base)
        extra = {}

        try:
            extra = modify_fn(current_input_data, param)

            contract_model = ContractNegotiation(current_input_data)
            contract_model.run()

            result_dict = {
                'StrikePrice': contract_model.results.strike_price,
                'ContractAmount': contract_model.results.contract_amount_hour,
                'Utility_G': contract_model.results.utility_G,
                'Utility_L': contract_model.results.utility_L,
                'ThreatPoint_G': contract_model.data.Zeta_G,
                'ThreatPoint_L': contract_model.data.Zeta_L,
                'Nash_Product': contract_model.results.Nash_Product,
                'NashProductLog': contract_model.results.objective_value,
            }

            # PAP gamma
            if (hasattr(current_input_data, 'contract_type')
                    and current_input_data.contract_type == "PAP"
                    and hasattr(contract_model.results, 'gamma')):
                result_dict['Gamma'] = contract_model.results.gamma

            # Merge extra columns from modify_fn
            result_dict.update(extra)
            results_list.append(result_dict)

            # Earnings collection
            if collect_earnings and earnings_fn is not None:
                earn_dict = earnings_fn(current_input_data, contract_model, param)
                earnings_list.append(pd.DataFrame(earn_dict))

        except Exception as e:
            print(f"Error in {name} for param={param}: {e}")
            nan_dict = {
                'StrikePrice': np.nan,
                'ContractAmount': np.nan,
                'Utility_G': np.nan,
                'Utility_L': np.nan,
                'ThreatPoint_G': np.nan,
                'ThreatPoint_L': np.nan,
                'Nash_Product': np.nan,
                'NashProductLog': np.nan,
            }
            nan_dict.update({k: np.nan for k in extra})
            results_list.append(nan_dict)

            if collect_earnings and earnings_fn is not None:
                # Build a single-row NaN earnings frame using the extra keys
                # plus standard earnings keys
                earn_nan = {k: [np.nan] for k in extra}
                earn_nan.update({'Revenue_G': [np.nan], 'Revenue_L': [np.nan]})
                earnings_list.append(pd.DataFrame(earn_nan))

        # Clean up
        del contract_model

    results_df = pd.DataFrame(results_list)

    print(f"\n--- {name} Complete ---")

    if collect_earnings:
        earnings_df = pd.concat(earnings_list, ignore_index=True)
        return results_df, earnings_df
    return results_df


# ---------------------------------------------------------------------------
# Pattern A wrappers (return results_df only)
# ---------------------------------------------------------------------------

def run_price_bias_sensitivity_analysis(input_data_base: 'InputData') -> pd.DataFrame:
    """Performs sensitivity analysis on price bias factors."""
    K_factors = [-0.1, -0.05, -0.01, 0, 0.01, 0.05, 0.1]
    param_grid = [(kg, kl) for kg in K_factors for kl in K_factors]

    def modify_fn(data, param):
        kg, kl = param
        data.K_G_price = kg
        data.K_L_price = kl
        return {'KG_Factor': kg, 'KL_Factor': kl,
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Price Bias Sensitivity Analysis", input_data_base, param_grid,
        modify_fn, desc="Testing bias combinations")


def run_production_bias_sensitivity_analysis(input_data_base: 'InputData') -> pd.DataFrame:
    """Performs sensitivity analysis on production bias factors."""
    K_factors = [-0.1, -0.05, -0.01, 0, 0.01, 0.05, 0.1]
    param_grid = [(kg, kl) for kg in K_factors for kl in K_factors]

    def modify_fn(data, param):
        kg, kl = param
        data.K_G_prod = kg
        data.K_L_prod = kl
        return {'KG_Factor': kg, 'KL_Factor': kl,
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Production Bias Sensitivity Analysis", input_data_base, param_grid,
        modify_fn, desc="Testing bias combinations")


def run_capture_rate_sensitivity_analysis(input_data_base: 'InputData') -> pd.DataFrame:
    """Performs sensitivity analysis on capture rate values (mean shift)."""
    multipliers = [-0.4, -0.3, -0.2, -0.15, -0.1, -0.05, 0,
                   0.05, 0.1, 0.15, 0.2, 0.3, 0.4]

    def modify_fn(data, mult):
        expected_capture = weighted_expected_value(data.capture_rate, data.PROB)
        data.capture_rate = data.capture_rate + expected_capture * mult
        return {'CaptureRate_Change': 1 + mult,
                'Avg_G_Capture_Rate': data.capture_rate.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Capture Rate Sensitivity Analysis", input_data_base, multipliers,
        modify_fn, desc="Testing capture rate multipliers")


def run_price_sensitivity_analysis(input_data_base: 'InputData', sensitivity_type: str) -> pd.DataFrame:
    """Performs sensitivity analysis on price values."""
    multipliers = [-0.4, -0.3, -0.2, -0.15, -0.1, -0.05, 0,
                   0.05, 0.1, 0.15, 0.2, 0.3, 0.4]

    def modify_fn(data, mult):
        expected_price = weighted_expected_value(data.price_true, data.PROB)
        if sensitivity_type == "mean":
            data.price_true = data.price_true + expected_price * mult
        elif sensitivity_type == "std":
            data.price_true = expected_price + (1 + mult) * (data.price_true - expected_price)
        return {'Price_Change': 1 + mult,
                'Avg_G_Price': data.price_true.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Price Sensitivity Analysis", input_data_base, multipliers,
        modify_fn, desc="Testing price multipliers")


def run_production_sensitivity_analysis(input_data_base: 'InputData', sensitivity_type: str) -> pd.DataFrame:
    """Performs sensitivity analysis on production rate values."""
    multipliers = [-0.4, -0.3, -0.2, -0.15, -0.1, -0.05, 0,
                   0.05, 0.1, 0.15, 0.2, 0.3, 0.4]

    def modify_fn(data, mult):
        expected_production = weighted_expected_value(data.production, data.PROB)
        if sensitivity_type == "mean":
            data.production = data.production + expected_production * mult
        elif sensitivity_type == "std":
            data.production = expected_production + (1 + mult) * (data.production - expected_production)
        return {'Production_Change': 1 + mult,
                'Avg_Production': data.production.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Production Sensitivity Analysis", input_data_base, multipliers,
        modify_fn, desc="Testing Production multipliers")


def run_load_capture_rate_sensitivity_analysis(input_data_base: 'InputData') -> pd.DataFrame:
    """Performs sensitivity analysis on load capture rate values."""
    multipliers = [-0.4, -0.3, -0.2, -0.15, -0.1, -0.05, 0,
                   0.05, 0.1, 0.15, 0.2, 0.3, 0.4]

    def modify_fn(data, mult):
        expected_load = weighted_expected_value(data.load_CR, data.PROB)
        data.load_CR = data.load_CR + expected_load * mult
        return {'Load_CaptureRate_Change': 1 + mult,
                'Avg_Load_Capture_Rate': data.load_CR.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Load Capture Rate Sensitivity Analysis", input_data_base, multipliers,
        modify_fn, desc="Testing load capture rate multipliers")


def run_load_scenario_sensitivity_analysis(input_data_base: 'InputData', sensitivity_type: str) -> pd.DataFrame:
    """Performs sensitivity analysis on load rate values."""
    multipliers = [-0.4, -0.3, -0.2, -0.15, -0.1, -0.05, 0,
                   0.05, 0.1, 0.15, 0.2, 0.3, 0.4]

    def modify_fn(data, mult):
        expected_load = weighted_expected_value(data.load_scenarios, data.PROB)
        if sensitivity_type == "mean":
            data.load_scenarios = data.load_scenarios + expected_load * mult
        elif sensitivity_type == "std":
            data.load_scenarios = expected_load + (1 + mult) * (data.load_scenarios - expected_load)
        return {'Load_Change': 1 + mult,
                'Avg_Load': data.load_scenarios.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Load Scenario Sensitivity Analysis", input_data_base, multipliers,
        modify_fn, desc="Testing load scenario multipliers")


def run_load_generation_ratio_sensitivity_analysis(input_data_base: 'InputData') -> pd.DataFrame:
    """Sensitivity analysis for varying the Load/Generation ratio."""
    ratio_values = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
    base_mean_load = input_data_base.load_scenarios.mean().mean()
    base_mean_gen = input_data_base.production.mean().mean()

    def modify_fn(data, ratio):
        new_mean_load = ratio * base_mean_gen
        scale_factor = new_mean_load / base_mean_load
        data.load_scenarios = data.load_scenarios * scale_factor
        return {'Load_Gen_Ratio': ratio,
                'Avg_Load': data.load_scenarios.mean().mean(),
                'Avg_Gen': data.production.mean().mean(),
                'A_G': data.A_G, 'A_L': data.A_L}

    return _run_sensitivity(
        "Load/Generation Ratio Sensitivity Analysis", input_data_base,
        ratio_values, modify_fn, desc="Testing Load/Gen ratios")


# ---------------------------------------------------------------------------
# Pattern B wrappers (return results_df, earnings_df)
# ---------------------------------------------------------------------------

def run_risk_sensitivity_analysis(input_data_base: 'InputData', A_G_values: np.ndarray, A_L_values: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Runs the ContractNegotiation for different combinations of A_G and A_L."""
    param_grid = [(a_G, a_L) for a_G in A_G_values for a_L in A_L_values]

    def modify_fn(data, param):
        a_G, a_L = param
        data.A_G = a_G
        data.A_L = a_L
        return {'A_G': a_G, 'A_L': a_L}

    def earnings_fn(data, model, param):
        a_G, a_L = param
        return {
            'A_G': a_G,
            'A_L': a_L,
            'Revenue_G': model.results.earnings_G.values,
            'Revenue_L': model.results.earnings_L.values,
        }

    return _run_sensitivity(
        "Risk Aversion Sensitivity Analysis", input_data_base, param_grid,
        modify_fn, desc="Iterating A_G x A_L",
        collect_earnings=True, earnings_fn=earnings_fn)


def run_negotiation_power_sensitivity_analysis(input_data_base: 'InputData', tau_G_values: np.ndarray, tau_L_values: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Runs the ContractNegotiation for different combinations of tau G and tau L."""
    param_grid = list(zip(tau_G_values, tau_L_values))

    def modify_fn(data, param):
        tau_G, tau_L = param
        data.tau_G = tau_G
        data.tau_L = tau_L
        return {'A_G': data.A_G, 'A_L': data.A_L,
                'tau_G': tau_G, 'tau_L': tau_L}

    def earnings_fn(data, model, param):
        tau_G, tau_L = param
        return {
            'A_G': data.A_G,
            'A_L': data.A_L,
            'tau_G': tau_G,
            'tau_L': tau_L,
            'Revenue_G': model.results.earnings_G.values,
            'Revenue_L': model.results.earnings_L.values,
            'CR_L_Revenue': model.results.earnings_L_CP.values,
            'CR_G_Revenue': model.results.earnings_G_CP.values,
        }

    return _run_sensitivity(
        "Negotation Power Sensitivity Analysis", input_data_base, param_grid,
        modify_fn, desc="Iterating tau_G",
        collect_earnings=True, earnings_fn=earnings_fn)


def run_cvar_alpha_sensitivity_analysis(input_data_base: 'InputData') -> tuple[pd.DataFrame, pd.DataFrame]:
    """Runs the ContractNegotiation for different combinations of beta G and beta L."""
    alpha_values = np.array([0.95])

    def modify_fn(data, alpha):
        data.alpha = alpha
        return {'alpha': alpha}

    def earnings_fn(data, model, alpha):
        return {
            'alpha': alpha,
            'Revenue_G': model.results.earnings_G.values,
            'Revenue_L': model.results.earnings_L.values,
        }

    return _run_sensitivity(
        "Alpha Sensitivity Analysis", input_data_base, alpha_values,
        modify_fn, desc="Iterating alpha",
        collect_earnings=True, earnings_fn=earnings_fn)


# ---------------------------------------------------------------------------
# Leave-as-is functions (structurally different)
# ---------------------------------------------------------------------------

def run_capture_price_analysis(input_data_base: 'InputData') -> tuple[pd.DataFrame, pd.DataFrame]:
    """Performs sensitivity analysis on capture price value from simulations."""
    current_input_data = copy.deepcopy(input_data_base)

    if current_input_data.contract_type == "PAP":
        avg_price = weighted_expected_value(current_input_data.capture_rate * current_input_data.price_true, current_input_data.PROB)
        # Set constraints for strike pices equal to the capture price of the generator
    else:
        avg_price = weighted_expected_value(current_input_data.price_true, current_input_data.PROB)


    current_input_data.strikeprice_max = avg_price
    current_input_data.strikeprice_min = avg_price  # Set Average price as the comparison case - since that is the 'base price'

        # Use a fresh copy for each iteration
    print(f"\n--- Starting Capture Price Sensitivity Analysis with Capture Price = {avg_price} ---")
    try:

        contract_model = ContractNegotiation(current_input_data)

        contract_model.run()

        # Create base result dictionary
        result_dict = {
            'Capture_Price': [avg_price],
            'StrikePrice': [contract_model.results.strike_price],
            'A_G': [current_input_data.A_G],
            'A_L': [current_input_data.A_L],
            'ContractAmount': [contract_model.results.contract_amount_hour],
            'Utility_G': [contract_model.results.utility_G],
            'Utility_L': [contract_model.results.utility_L],
            'ThreatPoint_G': [contract_model.data.Zeta_G],
            'ThreatPoint_L': [contract_model.data.Zeta_L],
            'Nash_Product': [(contract_model.results.utility_G - contract_model.data.Zeta_G) *
                            (contract_model.results.utility_L - contract_model.data.Zeta_L)]
        }

        # Add contract-type specific metrics
        if hasattr(current_input_data, 'contract_type'):
            if current_input_data.contract_type == "PAP":
                if hasattr(contract_model.results, 'gamma'):
                    result_dict['Gamma'] = contract_model.results.gamma
            elif current_input_data.contract_type == "Baseload":
                # Add Baseload-specific metrics if needed
                pass

          # Create earnings results for histograms
        earnings_df = pd.DataFrame({
            'A_G': current_input_data.A_G,
            'A_L': current_input_data.A_L,
            'Revenue_G_CP': contract_model.results.earnings_G.values,
            'Revenue_L_CP': contract_model.results.earnings_L.values,

        })


    except Exception as e:
        print(f"Error for capture rate multiplier={avg_price}: {str(e)}")
        result_dict = {
            'CaptureRate_Change': [avg_price],
            'Avg_G_Capture_Rate': [np.nan],
            'A_G': [current_input_data.A_G],
            'A_L': [current_input_data.A_L],
            'StrikePrice': [np.nan],
            'ContractAmount': [np.nan],
            'Utility_G': [np.nan],
            'Utility_L': [np.nan],
            'ThreatPoint_G': [np.nan],
            'ThreatPoint_L': [np.nan],
            'Nash_Product': [np.nan]
        }
        earnings_df = pd.DataFrame({
                    'A_G': [current_input_data.A_G],
                    'A_L': [current_input_data.A_L],
                    'Revenue_G': [np.nan],
                    'Revenue_L': [np.nan],

                })

    # Clean up
    del contract_model

# Add analysis of results
    results_df = pd.DataFrame(result_dict)

    return results_df, earnings_df

def _run_boundary_analysis(input_data_base: 'InputData', bias_type: str) -> list[dict[str, Any]]:
    """Compute feasibility masks on a 2D grid of bias factors and return for plotting/saving.

    Parameters
    ----------
    input_data_base : InputData
        Base input data (deep-copied each grid cell).
    bias_type : str
        ``"price"`` to sweep K_G_price / K_L_price, or
        ``"production"`` to sweep K_G_prod / K_L_prod.
    """
    label = "Price Bias" if bias_type == "price" else "Production Bias"
    print(f"\n--- Infeasibility Boundary Analysis ({label}) ---")

    risk_aversion_scenarios = [
        {'A_G': 0.1, 'A_L': 0.1, 'label': 'A_G=0.1, A_L=0.1', 'linestyle': '-',  'linewidth': 3.0, 'color': 'blue'},
        {'A_G': 0.5, 'A_L': 0.5, 'label': 'A_G=0.5, A_L=0.5', 'linestyle': '-',  'linewidth': 2.5, 'color': 'green'},
        {'A_G': 0.1, 'A_L': 0.5, 'label': 'A_G=0.1, A_L=0.5', 'linestyle': ':',  'linewidth': 2.0, 'color': 'red'},
        {'A_G': 0.5, 'A_L': 0.1, 'label': 'A_G=0.5, A_L=0.1', 'linestyle': '-.', 'linewidth': 2.0, 'color': 'magenta'},
        {'A_G': 0.9, 'A_L': 0.9, 'label': 'A_G=0.9, A_L=0.9', 'linestyle': '--', 'linewidth': 1.8, 'color': 'orange'},
    ]

    KL_range = np.linspace(-0.30, 0.30, 7)
    KG_range = np.linspace(-0.30, 0.30, 7)
    KL_grid, KG_grid = np.meshgrid(KL_range, KG_range)

    all_results = []

    for scenario in risk_aversion_scenarios:
        print(f"Analyzing scenario: {scenario['label']}")
        feas_mask = np.full_like(KL_grid, np.nan, dtype=float)  # 1=feasible, 0=infeasible, NaN=unknown
        pos_contract_mask = np.zeros_like(KL_grid, dtype=float)

        for i in tqdm(range(KG_grid.shape[0]), desc=f"KG grid {scenario['label']}"):
            for j in range(KL_grid.shape[1]):
                current = copy.deepcopy(input_data_base)
                current.A_G = scenario['A_G']
                current.A_L = scenario['A_L']

                if bias_type == "price":
                    current.K_G_price = float(KG_grid[i, j])
                    current.K_L_price = float(KL_grid[i, j])
                else:
                    current.K_G_prod = float(KG_grid[i, j])
                    current.K_L_prod = float(KL_grid[i, j])

                try:
                    cm = ContractNegotiation(current)
                    cm.model.Params.OutputFlag = 0
                    cm.model.Params.InfUnbdInfo = 1
                    cm.model.Params.FeasibilityTol = 1e-6
                    cm.run()

                    status = cm.model.Status
                    if status == gp.GRB.OPTIMAL:
                        feas_mask[i, j] = 1.0
                        try:
                            ca = getattr(cm.results, 'contract_amount', getattr(cm.results, 'contract_amount_hour', 0.0))
                            pos_contract_mask[i, j] = 1.0 if ca and ca > 1e-5 else 0.0
                        except Exception:
                            pos_contract_mask[i, j] = 0.0
                    elif status in (gp.GRB.INFEASIBLE, gp.GRB.INF_OR_UNBD):
                        feas_mask[i, j] = 0.0
                    else:
                        pass
                except Exception:
                    pass
                finally:
                    try:
                        del cm
                    except Exception:
                        pass

        all_results.append({
            'scenario': scenario,
            'feas_mask': feas_mask,
            'pos_contract_mask': pos_contract_mask,
            'KL_grid': KL_grid,
            'KG_grid': KG_grid,
            'contract_grid': np.full_like(KL_grid, np.nan, dtype=float),
            'boundary_points': [],
            'KL_range': KL_range,
            'KG_range': KG_range,
        })

        n_total = KL_grid.size
        n_feas = int(np.nansum(feas_mask))
        n_infeas = int(np.nansum(1 - feas_mask[np.isfinite(feas_mask)]))
        n_nan = int(np.sum(~np.isfinite(feas_mask)))
        print(f"  Feasible: {n_feas}/{n_total}, Infeasible: {n_infeas}/{n_total}, Unknown: {n_nan}/{n_total}")

    return all_results


def run_no_contract_boundary_analysis_price(input_data_base: 'InputData') -> list[dict[str, Any]]:
    """Compute feasibility masks on a 2D grid of price-bias factors."""
    return _run_boundary_analysis(input_data_base, bias_type="price")


def run_no_contract_boundary_analysis_production(input_data_base: 'InputData') -> list[dict[str, Any]]:
    """Compute feasibility masks on a 2D grid of production-bias factors."""
    return _run_boundary_analysis(input_data_base, bias_type="production")

def run_negotiation_power_vs_risk_sensitivity_analysis(
    input_data_base: 'InputData',
    A_G_values: np.ndarray,
    A_L_values: np.ndarray,
    tau_L_values: np.ndarray,
) -> pd.DataFrame:
    """
    Sweep negotiation power across multiple risk-aversion pairs.

    For each (A_G, A_L) pair and each tau_L in tau_L_values (with tau_G = 1 - tau_L),
    run the ContractNegotiation and collect StrikePrice, ContractAmount, utilities, and Nash product.

    Returns a tidy DataFrame with columns:
      [A_G, A_L, tau_G, tau_L, StrikePrice, ContractAmount, Utility_G, Utility_L,
       NashProductLog, Nash_Product, ThreatPoint_G, ThreatPoint_L, (Gamma if PAP)]
    """
    print("\n--- Starting Negotiation Power vs Risk-Aversion Sensitivity ---")
    results_list = []

    # Defensive copy of inputs to lists for iteration
    tau_L_values = np.array(tau_L_values)

    for a_G in tqdm(A_G_values, desc="A_G grid"):
        for a_L in tqdm(A_L_values, desc="A_L grid", leave=False):
            for tau_L in tau_L_values:
                tau_G = 1.0 - tau_L
                current = copy.deepcopy(input_data_base)
                current.A_G = a_G
                current.A_L = a_L
                current.tau_L = tau_L
                current.tau_G = tau_G

                try:
                    model = ContractNegotiation(current)
                    model.run()

                    rec = {
                        'A_G': a_G,
                        'A_L': a_L,
                        'tau_G': tau_G,
                        'tau_L': tau_L,
                        'StrikePrice': model.results.strike_price,
                        'ContractAmount': getattr(model.results, 'contract_amount_hour', getattr(model.results, 'contract_amount', np.nan)),
                        'Utility_G': model.results.utility_G,
                        'Utility_L': model.results.utility_L,
                        'NashProductLog': model.results.objective_value,
                        'Nash_Product': model.results.Nash_Product,
                        'ThreatPoint_G': model.data.Zeta_G,
                        'ThreatPoint_L': model.data.Zeta_L,
                    }
                    if hasattr(current, 'contract_type') and current.contract_type == "PAP":
                        if hasattr(model.results, 'gamma'):
                            rec['Gamma'] = model.results.gamma
                    results_list.append(rec)
                except Exception as e:
                    print(f"Error for A_G={a_G}, A_L={a_L}, tau_L={tau_L}: {e}")
                    results_list.append({
                        'A_G': a_G,
                        'A_L': a_L,
                        'tau_G': tau_G,
                        'tau_L': tau_L,
                        'StrikePrice': np.nan,
                        'ContractAmount': np.nan,
                        'Utility_G': np.nan,
                        'Utility_L': np.nan,
                        'NashProductLog': np.nan,
                        'Nash_Product': np.nan,
                        'ThreatPoint_G': np.nan,
                        'ThreatPoint_L': np.nan,
                    })
                finally:
                    try:
                        del model
                    except Exception:
                        pass

    results_df = pd.DataFrame(results_list)
    print("\n--- Negotiation Power vs Risk-Aversion Sensitivity Complete ---")
    return results_df

def run_elasticity_vs_risk_sensitivity_analysis(input_data_base: 'InputData', A_G_values: np.ndarray, A_L_values: np.ndarray) -> pd.DataFrame:
    """Run all factor sensitivity analyses across multiple A_L values for each fixed A_G.
    Returns a long DataFrame with a 'Factor' label so plotting can compute local elasticities per (A_G, A_L, Factor).
    """
    print("\n--- Starting Elasticity-vs-Risk Sensitivity Analysis ---")
    all_rows = []

    for a_g in tqdm(A_G_values, desc="Fixed A_G values"):
        for a_l in tqdm(A_L_values, desc="Varying A_L values", leave=False):
            current_input = copy.deepcopy(input_data_base)
            current_input.A_G = float(a_g)
            current_input.A_L = float(a_l)

            try:
                # Price sensitivity
                df_price_mean = run_price_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="mean")
                df_price_mean = _tag(df_price_mean, 'Price Sensitivity (Expected)')

                df_price_std = run_price_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="std")
                df_price_std = _tag(df_price_std, 'Price Sensitivity (Expected)')

                # Production sensitivity
                df_prod_mean = run_production_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="mean")
                df_prod_mean = _tag(df_prod_mean, 'Production (Expected)')

                df_prod_std = run_production_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="std")
                df_prod_std = _tag(df_prod_std, 'Production (Std)')

                # Load scenario sensitivity
                df_load_mean = run_load_scenario_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="mean")
                df_load_mean = _tag(df_load_mean, 'Load Sensitivity (Expected)')

                df_load_std = run_load_scenario_sensitivity_analysis(copy.deepcopy(current_input), sensitivity_type="std")
                df_load_std = _tag(df_load_std, 'Load Sensitivity (Std)')

                # Capture rates
                df_cr_gen = run_capture_rate_sensitivity_analysis(copy.deepcopy(current_input))
                df_cr_gen = _tag(df_cr_gen, 'Prod. Capture Rate (Expected)')

                df_cr_load = run_load_capture_rate_sensitivity_analysis(copy.deepcopy(current_input))
                df_cr_load = _tag(df_cr_load, 'Load. Capture Rate (Expected)')

                # Accumulate
                all_rows.extend([
                    df_price_mean, df_price_std,
                    df_prod_mean, df_prod_std,
                    df_load_mean, df_load_std,
                    df_cr_gen, df_cr_load,
                ])
            except Exception as e:
                print(f"Elasticity-vs-Risk block failed for A_G={a_g}, A_L={a_l}: {e}")
                continue

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True, sort=False)
    print("\n--- Elasticity-vs-Risk Sensitivity Analysis Complete ---")
    return combined

def run_bias_vs_risk_elasticity_sensitivity_analysis(input_data_base: 'InputData', A_G_values: np.ndarray, A_L_values: np.ndarray) -> pd.DataFrame:

    """Run all factor sensitivity analyses across multiple A_L values for each fixed A_G.
    Returns a long DataFrame with a 'Factor' label so plotting can compute local elasticities per (A_G, A_L, Factor).
    """
    print("\n--- Starting Elasticity-vs-Risk Sensitivity Analysis ---")
    all_rows = []

    for a_g in tqdm(A_G_values, desc="Fixed A_G values"):
        for a_l in tqdm(A_L_values, desc="Varying A_L values", leave=False):
            current_input = copy.deepcopy(input_data_base)
            current_input.A_G = float(a_g)
            current_input.A_L = float(a_l)

            try:
                # Price sensitivity
                df_price_bias = run_price_bias_sensitivity_analysis(copy.deepcopy(current_input))
                df_price_bias = _tag(df_price_bias, 'Price Bias')



                df_production_bias = run_production_bias_sensitivity_analysis(copy.deepcopy(current_input))
                df_production_bias = _tag(df_production_bias, 'Production Bias')

                # Accumulate
                all_rows.extend([
                    df_price_bias, df_production_bias,

                ])
            except Exception as e:
                print(f"Elasticity-vs-Risk block failed for A_G={a_g}, A_L={a_l}: {e}")
                continue

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True, sort=False)
    print("\n--- Elasticity-vs-Risk Sensitivity Analysis Complete ---")
    return combined


############## Unncessary Sensitivity Analysis Functions ##############
