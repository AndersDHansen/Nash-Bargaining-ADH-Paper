"""
Contract negotiation implementation using Nash bargaining solution.

Internal units
--------------
- Strike price S : EUR/GWh  (displayed as EUR/MWh via  S * 1e3)
- Contract amount M : GWh/year  (Baseload) or dimensionless fraction gamma (PAP)
- Electricity prices (lambda) : EUR/GWh
- Production / load volumes : GWh per time period
- Earnings / utilities : EUR (summed over time periods and scenarios)
"""
import numpy as np
import gurobipy as gp
import pandas as pd
from gurobipy import GRB
from utils import (Expando, _calculate_S_star_BL_G,_calculate_S_star_BL_L, _calculate_S_star_PAP_L, calculate_cvar_left, _left_tail_weighted_sum, _left_tail_mask, _calculate_S_star_PAP_G, compute_cvar_derivative_mixed , weighted_expected_value
                    )
from Barter_Set import Barter_Set
import os
from scipy.optimize import minimize, NonlinearConstraint




class ContractNegotiation:
    def __init__(self, input_data):
        """Initialize contract negotiation model with loaded scenarios.

        Args:
            input_data: Input data object containing loaded scenarios and parameters
        """        
        self.data = input_data
        self.relax = getattr(self.data, 'relax', False)
        self.contract_type = getattr(self.data, 'contract_type', 'Baseload')
        self.results = Expando()
        self.variables = Expando()
        self.constraints = Expando()
        
        self.plots_dir = os.path.join(os.path.dirname(__file__), 'Plots')
        os.makedirs(self.plots_dir, exist_ok=True)
        
   
            
        # Compute derived data (statistics, biased distributions, disagreement points)
        # then find strike-price boundaries via scipy, and finally build the
        # Gurobi Nash bargaining model.
        self._initialize_model_data()
        self._compute_strike_boundaries()
        self._build_model()
            
    
    def _initialize_model_data(self):
        """Compute derived statistics from loaded scenarios.

        Populates self.data with discount factors, biased price/production
        distributions, disagreement-point utilities (Zeta_G, Zeta_L), and
        initial strike-price thresholds (SR_star_new, SU_star_new at M=0).
        """
        # Data is already loaded in __init__

        ################### Calculate basic statistics from loaded scenarios #######
    
        if self.data.Discount == True:
            print("Discounting is applied in the calculations.")
            discount_factors_G = 1 / (1 + self.data.d_G) ** np.arange(self.data.n_time)
            self.data.discount_factors_G_arr = discount_factors_G[:, None]

            discount_factors_L = 1 / (1 + self.data.d_L) ** np.arange(self.data.n_time)
            self.data.discount_factors_L_arr = discount_factors_L[:, None]

        else:
            self.data.discount_factors_G_arr = np.ones((len(self.data.TIME),1))
            self.data.discount_factors_L_arr = np.ones((len(self.data.TIME),1))


        ####### Prices ########
        self.data.expected_price = weighted_expected_value(self.data.price_true, self.data.PROB)
        # Calculate scenario sums and expectations
        self.data.lambda_sum_true_per_scenario = self.data.price_true.sum(axis=0)
        self.data.expected_lambda_sum_true = (self.data.PROB*self.data.lambda_sum_true_per_scenario).sum()

        # Calculate CVaR^P(λ∑) - CVaR of the sum over T (using TRUE distribution)
        # Assumes calculate_cvar returns the expected value of the variable *given* it's in the alpha-tail
        self.data.tail_lambda_sum = calculate_cvar_left(self.data.lambda_sum_true_per_scenario,self.data.PROB, self.data.alpha)
        # Calculate CVaR^P(-λ∑) - CVaR of the negative sum over T (using TRUE distribution)
        # This corresponds to the risk of high LMPs
        self.data.neg_tail_lambda_sum = -calculate_cvar_left(-self.data.lambda_sum_true_per_scenario, self.data.PROB, self.data.alpha)

               
        ########### Capture Prices ##########
        # Calculate capture prices using loaded capture rates
        self.data.Capture_price_G = self.data.price_true * self.data.capture_rate
        self.data.Capture_price_G_avg = weighted_expected_value(self.data.Capture_price_G, self.data.PROB)

        # Per Scenario
        self.data.production_per_scenario = self.data.production.sum(axis=0)
        self.data.expected_production = weighted_expected_value(self.data.production, self.data.PROB)
        
        # Asymmetric information: each party forms biased price beliefs.
        # K_G_price / K_L_price shift the true price distribution by a fraction
        # of the mean, so generator and load-serving entity (LSE) negotiate
        # under different (potentially optimistic or pessimistic) price views.
        self.data.price_G = (self.data.K_G_price * self.data.expected_price) + self.data.price_true
        self.data.price_L = (self.data.K_L_price * self.data.expected_price) + self.data.price_true
        self.data.lambda_sum_G_per_scenario = self.data.price_G.sum(axis=0)
        self.data.lambda_sum_L_per_scenario = self.data.price_L.sum(axis=0)

        # Analogous production bias: each party may over-/under-estimate
        # future renewable production by K_G_prod / K_L_prod of the mean.
        self.data.production_G = (self.data.K_G_prod * self.data.expected_production) + self.data.production
        self.data.production_L = (self.data.K_L_prod * self.data.expected_production) + self.data.production


        # Using loaded capture rate and production scenarios
        self.data.net_earnings_no_contract_G_df = pd.DataFrame(
            self.data.capture_rate * self.data.production * self.data.price_true
        )
        # Calculate true net earnings for generator with correct price distribution
        self.data.net_earnings_no_contract_true_G = self.data.net_earnings_no_contract_G_df.sum(axis=0)
        
        # Calculate biased net earnings for generator with price bias K_G
        self.data.net_earnings_no_contract_priceG_G_df = pd.DataFrame(
            self.data.capture_rate * self.data.production_G * self.data.price_G
        )
        # Apply discounting to net earnings if enabled

        if self.data.Discount == True:
            self.data.net_earnings_no_contract_priceG_G =  (self.data.discount_factors_G_arr * self.data.net_earnings_no_contract_priceG_G_df).sum(axis=0)
            # Calculate load earnings with true and biased prices
            self.data.net_earnings_no_contract_priceL_L = (self.data.discount_factors_L_arr * (self.data.load_scenarios * (  -  self.data.load_CR *self.data.price_L))).sum(axis=0)
        else:
            self.data.net_earnings_no_contract_priceG_G = self.data.net_earnings_no_contract_priceG_G_df.sum(axis=0)
            # Calculate load earnings with true and biased prices
            self.data.net_earnings_no_contract_priceL_L = (self.data.load_scenarios * ( -self.data.load_CR *self.data.price_L)).sum(axis=0)

        # Calculate CVaR for no-contract scenarios

        self.data.CVaR_no_contract_priceG_G = calculate_cvar_left(self.data.net_earnings_no_contract_priceG_G,self.data.PROB, self.data.alpha)
        self.data.CVaR_no_contract_priceL_L = calculate_cvar_left(self.data.net_earnings_no_contract_priceL_L,self.data.PROB, self.data.alpha)

        # Disagreement (threat) point: the utility each party obtains if no
        # contract is signed.  Used as the fall-back payoff in the Nash
        # bargaining problem.  U_i = (1-A_i)*E[earnings] + A_i*CVaR[earnings].
        self.data.Zeta_G = ((1 - self.data.A_G) * (self.data.PROB * self.data.net_earnings_no_contract_priceG_G).sum() + self.data.A_G * self.data.CVaR_no_contract_priceG_G)
        self.data.Zeta_L = ((1 - self.data.A_L) * (self.data.PROB * self.data.net_earnings_no_contract_priceL_L).sum() + self.data.A_L * self.data.CVaR_no_contract_priceL_L)

        time_periods = self.data.price_true.shape[0]
    
        self.data.K_G_lambda_Sigma = self.data.K_G_price * self.data.expected_lambda_sum_true
        self.data.K_L_lambda_Sigma = self.data.K_L_price * self.data.expected_lambda_sum_true

        if self.data.contract_type == 'Baseload': 
            if self.data.Discount == True:                
                discounted_prices_G = (self.data.price_G * self.data.discount_factors_G_arr)
                discounted_prices_L = (self.data.price_L * self.data.discount_factors_L_arr)
                
                # Sum over time for each scenario
                lambda_sum_G_discounted = discounted_prices_G.sum(axis=0)
                lambda_sum_L_discounted = discounted_prices_L.sum(axis=0)
                
                # Expected values with discounting
                expected_lambda_sum_discounted_G = (self.data.PROB * lambda_sum_G_discounted).sum()
                expected_lambda_sum_discounted_L = (self.data.PROB * lambda_sum_L_discounted).sum()
                
                # Get masks using discounted earnings
                ord_G, bidx_G = _left_tail_mask(
                    self.data.net_earnings_no_contract_priceG_G,
                    self.data.PROB, 
                    self.data.alpha
                )

                 # Get masks using discounted earnings
                ord_L, bidx_L = _left_tail_mask(
                    self.data.net_earnings_no_contract_priceL_L,
                    self.data.PROB, 
                    self.data.alpha
                )
    
                # Calculate CVaR terms with discounted values
                tail_G = _left_tail_weighted_sum(
                    self.data.PROB,
                    lambda_sum_G_discounted,  # Use discounted sum
                    ord_G, bidx_G, 
                    self.data.alpha
                )

                tail_L = _left_tail_weighted_sum(
                    self.data.PROB,
                    lambda_sum_L_discounted,  # Use discounted sum
                    ord_L, bidx_L, 
                    self.data.alpha
                )

                self.data.term2_G_new =  (
                    ((1-self.data.A_G) * expected_lambda_sum_discounted_G + 
                    self.data.K_G_lambda_Sigma) + 
                    self.data.A_G * tail_G
                ) / ( self.data.discount_factors_G_arr.sum())

                # Calculate terms with discounted values
                self.data.term3_L_new = (
                    ((1-self.data.A_L) * expected_lambda_sum_discounted_L + 
                    self.data.K_L_lambda_Sigma) + 
                    self.data.A_L * tail_L
                ) / ( self.data.discount_factors_L_arr.sum())

             
            else:

                ord_G, bidx_G = _left_tail_mask(
                    self.data.net_earnings_no_contract_priceG_G,
                    self.data.PROB, 
                    self.data.alpha
                )

                 # Get masks using discounted earnings
                ord_L, bidx_L = _left_tail_mask(
                    self.data.net_earnings_no_contract_priceL_L,
                    self.data.PROB, 
                    self.data.alpha
                )

                # Calculate CVaR terms with discounted values
                tail_G = _left_tail_weighted_sum(
                    self.data.PROB,
                    self.data.lambda_sum_true_per_scenario,  # Per-scenario price sum
                    ord_G, bidx_G,
                    self.data.alpha
                )

                tail_L = _left_tail_weighted_sum(
                    self.data.PROB,
                    self.data.lambda_sum_true_per_scenario,  # Per-scenario price sum
                    ord_L, bidx_L,
                    self.data.alpha
                )
                
                self.data.term2_G_new = (
                    ((1-self.data.A_G) * self.data.expected_lambda_sum_true + 
                    self.data.K_G_lambda_Sigma) + 
                    self.data.A_G * tail_G
                ) / time_periods
                # SR* numerator for LSE, decomposed for readability:
                #   risk_neutral = E[sum_lambda]  (expected total price)
                #   price_bias   = K_L * E[sum_lambda]  (LSE's price belief shift)
                #   cvar_adjustment = A_L * (CVaR_tail - E[sum_lambda])
                #                  = A_L * tail_L - A_L * E[sum_lambda]
                risk_neutral_L = self.data.expected_lambda_sum_true
                price_bias_L = self.data.K_L_lambda_Sigma
                cvar_adjustment_L = self.data.A_L * tail_L - self.data.A_L * self.data.expected_lambda_sum_true
                self.data.term3_L_new = (risk_neutral_L + price_bias_L + cvar_adjustment_L) / time_periods
                
            
            # SR* (Eq. 27): lower bound of the bargaining zone (in EUR/GWh)
            self.data.SR_star_new = np.min([self.data.term2_G_new, self.data.term3_L_new])
            # SU* (Eq. 28): upper bound of the bargaining zone (in EUR/GWh)
            self.data.SU_star_new = np.max([self.data.term2_G_new, self.data.term3_L_new])

            
            print(f"Initial Threshold at M=0 SR* [EUR/MWh]: {self.data.SR_star_new*1e3:.3f}")
            print(f"Initial Threshold at M=0 SU* [EUR/MWh]: {self.data.SU_star_new*1e3:.3f}")

    def _compute_strike_boundaries(self):
        """Find strike-price boundaries via scipy optimisation.

        For Baseload contracts, uses SLSQP to find the generator- and
        load-side strike boundaries at the maximum contract amount.
        For PAP contracts, uses trust-constr to find boundaries at gamma=0.
        Results are printed but not stored (Baseload initial thresholds
        were already set by _initialize_model_data; PAP thresholds are
        stored here as SR_star_new / SU_star_new).
        """
        if self.data.contract_type == 'Baseload':
            production_G = self.data.production_G
            price_G = self.data.price_G
            capture_rate = self.data.capture_rate
            price_L = self.data.price_L
            load_CR = self.data.load_CR
            load_scenarios = self.data.load_scenarios

            M = self.data.contract_amount_max
            direction = 1

            def constraint_S_star_G_pos(x):
                S_star = _calculate_S_star_BL_G(
                    x, M, self.data.A_G, self.data.alpha,
                    production_G, price_G, capture_rate, self.data.PROB,direction,
                    discount_rate=self.data.d_G, n_time=self.data.n_time
                )
                return S_star

            def constraint_S_star_L_pos(x):
                S_star = _calculate_S_star_BL_L(
                    x, M, self.data.A_L, self.data.alpha,
                     price_L, load_CR, load_scenarios, self.data.PROB,direction,
                    discount_rate=self.data.d_L, n_time=self.data.n_time
                )
                return S_star

            nonlinear_constraint_S_star_G_pos = NonlinearConstraint(constraint_S_star_G_pos, 0, np.inf)
            nonlinear_constraint_S_star_L_pos = NonlinearConstraint(constraint_S_star_L_pos, 0, np.inf)

            bounds = [(self.data.strikeprice_min, self.data.strikeprice_max)]
            initial_guess = (self.data.strikeprice_max / 2)
            initial_guess_L = (self.data.strikeprice_max)

            result_G_pos = minimize(
            _calculate_S_star_BL_G,
            x0=initial_guess,
            args=(M, self.data.A_G, self.data.alpha, production_G, price_G, capture_rate, self.data.PROB,direction,
                    self.data.d_G, self.data.n_time),
            bounds=bounds,
            constraints=[nonlinear_constraint_S_star_G_pos],
            method='SLSQP',
            options={'disp': False, 'maxiter': 1000, 'gtol': 1e-6,}
            )

            result_L_pos = minimize(
            _calculate_S_star_BL_L,
            x0=initial_guess_L,
            args=(M, self.data.A_L, self.data.alpha,
                 price_L,
                load_CR, load_scenarios, self.data.PROB,direction,
                self.data.d_L, self.data.n_time),
            bounds=bounds,
            constraints=[nonlinear_constraint_S_star_L_pos],
            method='SLSQP',
            options={'disp': False, 'maxiter': 1000, 'gtol': 1e-6,}
            )

            print(f"Strike boundaries at M_max (Baseload): G={result_G_pos.x[0]*1e3:.4f}, L={result_L_pos.x[0]*1e3:.4f} EUR/MWh")
        else:
            bounds = [(self.data.strikeprice_min-0.02, self.data.strikeprice_max)]
            initial_guess = (self.data.strikeprice_min-0.01)
            initial_guess_L = (self.data.strikeprice_max)
            gamma = 0

            def constraint_S_star_G(x):
                S_star = _calculate_S_star_PAP_G(x, gamma,self.data.A_G, self.data.alpha, self.data.production_G, self.data.price_G,self.data.capture_rate,self.data.PROB)
                return S_star

            def constraint_S_star_L(x):
                S_star = _calculate_S_star_PAP_L(x, gamma,self.data.A_L, self.data.alpha, self.data.production_L, self.data.price_L,self.data.capture_rate,self.data.load_CR,self.data.load_scenarios,self.data.PROB)
                return S_star

            nonlinear_constraint_S_star_G = NonlinearConstraint(constraint_S_star_G, 0, np.inf)
            nonlinear_constraint_S_star_L = NonlinearConstraint(constraint_S_star_L, 0, np.inf)

            result_G = minimize(
                _calculate_S_star_PAP_G,
                x0=initial_guess,
                args=(gamma,self.data.A_G, self.data.alpha, self.data.production_G, self.data.price_G,self.data.capture_rate,self.data.PROB),
                bounds=bounds,
                constraints=[nonlinear_constraint_S_star_G],
                method='trust-constr',
                options={'disp': True, 'maxiter': 1000,'gtol': 1e-10,}
            )
            result_L = minimize(
                _calculate_S_star_PAP_L,
                x0=initial_guess,
                args=(gamma,self.data.A_L, self.data.alpha, self.data.production_L, self.data.price_L,self.data.capture_rate,self.data.load_CR,self.data.load_scenarios,self.data.PROB),
                bounds=bounds,
                constraints=[nonlinear_constraint_S_star_L],
                method='trust-constr',
                options={'disp': True, 'maxiter': 1000,'gtol': 1e-10,}
            )

            self.data.SR_star_new = result_G.x[0]
            self.data.SU_star_new = result_L.x[0]

            print(f"Strike boundaries (PAP): G={self.data.SR_star_new*1e3:.4f}, L={self.data.SU_star_new*1e3:.4f} EUR/MWh")
     
    def _build_variables(self):
        """Build optimization variables for contract negotiation."""
        # Auxiliary variables for logarithmic terms
        EPS = 1e-8
        self.variables.arg_G = self.model.addVar(lb=EPS, name="UG_minus_ZetaG")
        self.variables.arg_L = self.model.addVar(lb=EPS, name="UL_minus_ZetaL")

        # Define logarithmic terms
        self.variables.log_arg_G = self.model.addVar(lb=EPS, name="log_arg_G")
        self.variables.log_arg_L = self.model.addVar(lb=EPS, name="log_arg_L")

        # Strike price variable
        self.variables.S = self.model.addVar(
            lb=self.data.strikeprice_min,
            ub=self.data.strikeprice_max,
            name='Strike_Price'
        )

        # Contract amount variable (differs by contract type)
        if self.contract_type == 'PAP':
            self.variables.gamma = self.model.addVar(
                lb=0,
                ub=self.data.gamma_max,
                name='Proportion of production to go to PAP contract '
            )
        else:
            self.variables.M = self.model.addVar(
                lb=self.data.contract_amount_min,
                ub=self.data.contract_amount_max,
                name='Contract Amount'
            )

        # CVaR auxiliary variables (the VaR threshold in the CVaR linearisation).
        # Not to be confused with self.data.Zeta_G / Zeta_L which are the
        # disagreement-point utilities (see _initialize_model_data).
        self.variables.cvar_aux_G = self.model.addVar(
            name='CVaR_Auxiliary_G',
            lb=-gp.GRB.INFINITY, ub=gp.GRB.INFINITY)
        self.variables.cvar_aux_L = self.model.addVar(
            name='CVaR_Auxiliary_L',
            lb=-gp.GRB.INFINITY, ub=gp.GRB.INFINITY)

        self.variables.eta_G = self.model.addVars(
            self.data.SCENARIOS_L,
            name='Auxillary_Variable_G',
            lb=0,
            ub=gp.GRB.INFINITY
        )

        self.variables.eta_L = self.model.addVars(
            self.data.SCENARIOS_L,
            name='Auxillary_Variable_L',
            lb=0,
            ub=gp.GRB.INFINITY
        )

        self.model.update()

    def _build_common_constraints(self):
        """Build constraints shared by both Baseload and PAP contracts."""
        # Strike price constraints
        self.constraints.strike_price_constraint_max = self.model.addLConstr(
            self.variables.S <= self.data.strikeprice_max,
            name='Strike_Price_Constraint_Max'
        )

        self.constraints.strike_price_constraint_min = self.model.addLConstr(
            self.variables.S >= self.data.strikeprice_min,
            name='Strike_Price_Constraint_Min'
        )

        # Logarithmic constraints
        self.model.addGenConstrLog(self.variables.arg_G, self.variables.log_arg_G, "log_G")
        self.model.addGenConstrLog(self.variables.arg_L, self.variables.log_arg_L, "log_L")

    def _build_constraints(self):
        """Build constraints for Baseload contract negotiation."""
        self._build_common_constraints()

        # Contract amount constraints
        self.constraints.contract_amount_constraint_max = self.model.addLConstr(
           self.variables.M <= self.data.contract_amount_max,
            name='Contract Amount Constraint Max'
        )
        self.constraints.contract_amount_constraint_min = self.model.addLConstr(
            self.data.contract_amount_min <= self.variables.M,
            name='Contract Amount Constraint Min'
        )

        capture_rate_array = self.data.capture_rate.values
        price_G_array = self.data.price_G.values
        production_G_array = self.data.production_G.values
        load_scenarios_array = self.data.load_scenarios.values
        load_CR_array = self.data.load_CR.values
        price_L_array = self.data.price_L.values

        # Pre-compute constant terms for each scenario
        generator_const_per_scenario = (
            self.data.discount_factors_G_arr * capture_rate_array * price_G_array * production_G_array
        ).sum(axis=0)  # Sum over time for each scenario

        load_const_per_scenario = (
            -self.data.discount_factors_L_arr * load_scenarios_array * load_CR_array * price_L_array
        ).sum(axis=0)  # Sum over time for each scenario

        # Batch create eta_G constraints
        self.constraints.eta_G_constraint = self.model.addConstrs(
        (self.variables.eta_G[s] >=
         self.variables.cvar_aux_G - (generator_const_per_scenario[s] +
         gp.quicksum(self.data.discount_factors_G_arr[t,0] * (self.variables.S - price_G_array[t,s]) * self.variables.M
                     for t in self.data.TIME))
         for s in self.data.SCENARIOS_L),
        name='Eta_Aversion_Constraint_G'
    )

    # Batch create eta_L constraints
        self.constraints.eta_L_constraint = self.model.addConstrs(
        (self.variables.eta_L[s] >=
         self.variables.cvar_aux_L - (load_const_per_scenario[s] +
         gp.quicksum(self.data.discount_factors_L_arr[t,0] * (price_L_array[t,s] - self.variables.S) * self.variables.M
                     for t in self.data.TIME))
         for s in self.data.SCENARIOS_L),
        name='Eta_Aversion_Constraint_L'
    )

        self.model.update()

    def _build_constraints_PAP(self):
        """Build constraints for PAP contract negotiation."""
        self._build_common_constraints()

        # Contract amount constraints
        self.constraints.gamma_max = self.model.addLConstr(
           self.variables.gamma <= self.data.gamma_max,
            name='Contract Amount Constraint Max'
        )
        self.constraints.gamma_min = self.model.addLConstr(
            0 <= self.variables.gamma,
            name='Contract Amount Constraint Min'
        )

        # Pre-extract all data as numpy arrays
        production_G_vals = self.data.production_G.values  # Shape: (time, scenarios)
        capture_rate_vals = self.data.capture_rate.values  # Shape: (time, scenarios)
        price_G_vals = self.data.price_G.values  # Shape: (time, scenarios)
        price_L_vals = self.data.price_L.values  # Shape: (time, scenarios)
        load_CR_vals = self.data.load_CR.values  # Shape: (time, scenarios)
        load_scenarios_vals = self.data.load_scenarios.values  # Shape: (time, scenarios)
        production_L_vals = self.data.production_L.values  # Shape: (time, scenarios)

        # Pre-compute coefficients for each scenario
        # Generator constraints - coefficients for gamma*S term
        gamma_S_coeff_G_per_scenario = production_G_vals.sum(axis=0)  # Sum over time for each scenario

        # Generator constraints - constant terms for (1-gamma) term
        const_G_per_scenario = (capture_rate_vals * price_G_vals * production_G_vals).sum(axis=0)

        # Load constraints - constant terms
        const_L_per_scenario = (-price_L_vals * load_CR_vals * load_scenarios_vals).sum(axis=0)

        # Load constraints - coefficients for gamma term
        gamma_coeff_L_per_scenario = (production_L_vals * price_L_vals * capture_rate_vals).sum(axis=0)

        # Load constraints - coefficients for gamma*S term
        gamma_S_coeff_L_per_scenario = -production_L_vals.sum(axis=0)

        self.constraints.eta_G_constraint = self.model.addConstrs(
        (self.variables.eta_G[s] >= (
            self.variables.cvar_aux_G
            - self.variables.gamma * self.variables.S * gamma_S_coeff_G_per_scenario[s]
            - (1 - self.variables.gamma) * const_G_per_scenario[s]
            ) for s in range(len(self.data.SCENARIOS_L))),
            name='Eta_Aversion_Constraint_G'
        )

        self.constraints.eta_L_constraint = self.model.addConstrs(
            (self.variables.eta_L[s] >= (
        self.variables.cvar_aux_L
            - const_L_per_scenario[s]
            - self.variables.gamma * gamma_coeff_L_per_scenario[s]
            - self.variables.gamma * self.variables.S * gamma_S_coeff_L_per_scenario[s]
        ) for s in range(len(self.data.SCENARIOS_L))),
        name='Eta_Aversion_Constraint_L'
        )

    def _set_nash_objective(self, UG, UL):
        """Set the Nash bargaining objective given utility expressions.

        Dispatches based on tau_G/tau_L to either maximize one party's
        utility (with a non-negativity constraint on the other) or
        maximize the weighted log Nash product.
        """
        if self.data.tau_G == 1:
            self.model.setObjective((UG - self.data.Zeta_G), GRB.MAXIMIZE)
            self.model.addConstr(UL - self.data.Zeta_L >= 1e-8, "UL_non_negative")
        elif self.data.tau_L == 1:
            self.model.setObjective((UL - self.data.Zeta_L), GRB.MAXIMIZE)
            self.model.addConstr(UG - self.data.Zeta_G >= 1e-8, "UG_non_negative")
        else:
            # Link auxiliary variables to expressions
            self.model.addConstr(self.variables.arg_G == (UG - self.data.Zeta_G), "arg_G_constr")
            self.model.addConstr(self.variables.arg_L == (UL - self.data.Zeta_L), "arg_L_constr")
            self.model.setObjective(
                (self.data.tau_G * self.variables.log_arg_G + self.data.tau_L * self.variables.log_arg_L),
                GRB.MAXIMIZE
            )

    def _build_objectives_PAP(self):
        """Build the objective function for PAP contract negotiation."""
        # Pre-extract all data as numpy arrays
        prob_vals = self.data.PROB  # Shape: (scenarios,)
        production_G_vals = self.data.production_G.values  # Shape: (time, scenarios)
        capture_rate_vals = self.data.capture_rate.values  # Shape: (time, scenarios)
        price_G_vals = self.data.price_G.values  # Shape: (time, scenarios)
        price_L_vals = self.data.price_L.values  # Shape: (time, scenarios)
        load_CR_vals = self.data.load_CR.values  # Shape: (time, scenarios)
        load_scenarios_vals = self.data.load_scenarios.values  # Shape: (time, scenarios)
        production_L_vals = self.data.production_L.values  # Shape: (time, scenarios)

        # Pre-compute coefficients for all scenarios at once
        # Generator utility coefficients
        gamma_coeff_G = (prob_vals * production_G_vals).sum()  # Coefficient for gamma*S
        non_gamma_coeff_G = (prob_vals * capture_rate_vals *
                            price_G_vals * production_G_vals).sum()  # Constant coefficient for (1-gamma) term

        # Load utility coefficients
        load_base_cost = -(prob_vals * price_L_vals * load_CR_vals *
                        load_scenarios_vals).sum()  # Constant term

        gamma_price_coeff_L = (prob_vals * production_L_vals *
                            price_L_vals * capture_rate_vals).sum()  # Coefficient for gamma

        gamma_S_coeff_L = -(prob_vals * production_L_vals).sum()  # Coefficient for gamma*S

        # CVaR coefficients
        eta_G_sum = gp.quicksum(self.data.PROB[s] * self.variables.eta_G[s]
                            for s in self.data.SCENARIOS_L)
        eta_L_sum = gp.quicksum(self.data.PROB[s] * self.variables.eta_L[s]
                            for s in self.data.SCENARIOS_L)

        # Build expressions using pre-computed coefficients
        EuG = (self.variables.gamma * self.variables.S * gamma_coeff_G +
            (1 - self.variables.gamma) * non_gamma_coeff_G)

        EuL = (load_base_cost +
            self.variables.gamma * gamma_price_coeff_L +
            self.variables.gamma * self.variables.S * gamma_S_coeff_L)

        # CVaR calculations
        CVaRG = self.variables.cvar_aux_G - (1/(1-self.data.alpha)) * eta_G_sum
        CVaRL = self.variables.cvar_aux_L - (1/(1-self.data.alpha)) * eta_L_sum

        # Calculate utilities with risk aversion
        UG = (1-self.data.A_G) * EuG + self.data.A_G * CVaRG
        UL = (1-self.data.A_L) * EuL + self.data.A_L * CVaRL

        self._set_nash_objective(UG, UL)
        print(f"Objective: maximize {'UG (tau_G=1)' if self.data.tau_G == 1 else 'UL (tau_L=1)' if self.data.tau_L == 1 else 'weighted log Nash product'}")

    def _build_objective(self):
        """Build the objective function for Baseload contract negotiation."""
        # Pre-extract all data as numpy arrays
        prob_vals = self.data.PROB  # Shape: (scenarios,)
        capture_rate_vals = self.data.capture_rate.values  # Shape: (time, scenarios)
        price_G_vals = self.data.price_G.values  # Shape: (time, scenarios)
        production_G_vals = self.data.production_G.values  # Shape: (time, scenarios)
        load_scenarios_vals = self.data.load_scenarios.values  # Shape: (time, scenarios)
        load_CR_vals = self.data.load_CR.values  # Shape: (time, scenarios)
        price_L_vals = self.data.price_L.values  # Shape: (time, scenarios)

        # Pre-compute all coefficients using vectorized operations
        # Generator utility components
        gen_revenue_const = np.sum(prob_vals * capture_rate_vals *
                          price_G_vals * production_G_vals *
                          self.data.discount_factors_G_arr)

        # Coefficients for S and M terms in generator utility
        S_coeff_G = np.sum(prob_vals * self.data.discount_factors_G_arr) # Coefficient for S*M
        M_coeff_G = -np.sum(prob_vals* price_G_vals * self.data.discount_factors_G_arr)  # Coefficient for M

       # Load utility components with discounting
        load_revenue_const = np.sum(prob_vals * load_scenarios_vals *
                                (- load_CR_vals * price_L_vals) * self.data.discount_factors_L_arr)

        # Load coefficients with discounting
        S_coeff_L = -np.sum(prob_vals * self.data.discount_factors_L_arr)  # Coefficient for S*M
        M_coeff_L = np.sum(prob_vals * price_L_vals * self.data.discount_factors_L_arr)  # Coefficient for M

        # CVaR components
        eta_G_sum = gp.quicksum(self.data.PROB[s] * self.variables.eta_G[s]
                            for s in self.data.SCENARIOS_L)
        eta_L_sum = gp.quicksum(self.data.PROB[s] * self.variables.eta_L[s]
                            for s in self.data.SCENARIOS_L)

        # Build expressions using pre-computed coefficients
        EuG = (gen_revenue_const +
                S_coeff_G * self.variables.S * self.variables.M +
                M_coeff_G * self.variables.M)

        EuL = (load_revenue_const +
            S_coeff_L * self.variables.S * self.variables.M +
            M_coeff_L * self.variables.M)

        # CVaR calculations
        CVaRG = self.variables.cvar_aux_G - (1/(1-self.data.alpha)) * eta_G_sum
        CVaRL = self.variables.cvar_aux_L - (1/(1-self.data.alpha)) * eta_L_sum

        # Calculate utilities with risk aversion
        UG = (1-self.data.A_G) * EuG + self.data.A_G * CVaRG
        UL = (1-self.data.A_L) * EuL + self.data.A_L * CVaRL

        self.model.update()

        self._set_nash_objective(UG, UL)
        self.model.update()
        print(f"Objective: maximize {'UG (tau_G=1)' if self.data.tau_G == 1 else 'UL (tau_L=1)' if self.data.tau_L == 1 else 'weighted log Nash product'}")

    def _build_model(self):
        """Initialize and build the complete optimization model."""
        self.model = gp.Model(name='Nash Bargaining Model')
        self.model.Params.NonConvex = 2
        self.model.Params.FeasibilityTol = 1e-6
        self.model.Params.OutputFlag = 0  # Suppress output
        self.model.Params.TimeLimit = 420  # Set time limit to 7 minutes

        self.model.Params.ObjScale   = 1e-6

        self._build_variables()

        if self.contract_type == 'PAP':
            self._build_constraints_PAP()
            self._build_objectives_PAP()
        else:
            self._build_constraints()
            self._build_objective()
        self.model.update()

    def _save_results(self):
        """Save optimization results."""
        # Save objective value, strike price, and contract amount
        self.results.objective_value = self.model.ObjVal
        self.results.strike_price = self.variables.S.x * 1e3
        if self.contract_type == 'PAP':
            self.results.contract_amount = self.variables.gamma.x  * self.data.generator_contract_capacity * self.data.hours_in_year # yearly
            self.results.gamma = self.variables.gamma.x
            self.results.contract_amount_hour = self.results.gamma * self.data.generator_contract_capacity  # hourly

        else:
            self.results.contract_amount = self.variables.M.x  # GWh/year
            self.results.contract_amount_hour = self.results.contract_amount / 8760 * 1e3  # Convert GWh/year to MWh/hour
        self.results.capture_price = self.data.expected_price

        # Save their 'actual' values based on the true distribution 
        strike = self.variables.S.x
        # Calculate revenues with contract
        if self.contract_type == 'PAP':
            EuG = ((1-self.results.gamma)* self.data.capture_rate * self.data.price_G * self.data.production_G).sum(axis=0)
            SMG = (self.results.gamma * self.data.production_G * strike).sum(axis=0)   # Sum across time periods for each scenario
            
            
            
            EuL = (-self.data.price_L * self.data.load_CR * self.data.load_scenarios).sum(axis=0) # Sum across time periods for each scenario
            SML =   (self.results.gamma* self.data.production_L * self.data.price_L * self.data.capture_rate -  self.results.gamma * strike * self.data.production_L).sum(axis=0) # Sum across time periods for each scenario

            SMG_CP =   (self.results.gamma * self.data.production_G *  self.data.Capture_price_G_avg).sum(axis=0)   # Sum across time periods for each scenario
            SML_CP =     (self.results.gamma* self.data.production_L * self.data.price_L * self.data.capture_rate -  self.results.gamma * self.data.Capture_price_G_avg * self.data.production_L).sum(axis=0) # Sum across time periods for each scenario

            CV_CP_G = calculate_cvar_left(EuG + SMG_CP,self.data.PROB, self.data.alpha)
            CV_CP_L = calculate_cvar_left(EuL + SML_CP, self.data.PROB, self.data.alpha)

            # Calculate utilities with capture price
            self.results.utility_G_CP = (1-self.data.A_G) * (self.data.PROB* (EuG + SMG_CP)).sum() + self.data.A_G * CV_CP_G
            self.results.utility_L_CP = (1-self.data.A_L) * (self.data.PROB* (EuL + SML_CP)).sum() + self.data.A_L * CV_CP_L

            # Calculate expected earnings for G and L
            self.results.earnings_G_CP = EuG + SMG_CP
            self.results.earnings_L_CP = EuL + SML_CP
        else:
            EuG = self.data.net_earnings_no_contract_priceG_G
            EuL = self.data.net_earnings_no_contract_priceL_L
            SMG = ((strike - self.data.price_G  ) * self.results.contract_amount * self.data.discount_factors_G_arr).sum(axis=0)  # Sum across time periods for each scenario
            SML = ((self.data.price_L - strike) * self.results.contract_amount * self.data.discount_factors_L_arr).sum(axis=0)  # Sum across time periods for each scenario

            # Calculate CP_load price

            SMG_CP = ((self.data.Capture_price_G_avg - self.data.price_G) * self.results.contract_amount * self.data.discount_factors_G_arr).sum(axis=0)  # Sum across time periods for each scenario
            SML_CP = ((self.data.price_L- self.data.Capture_price_G_avg) * self.results.contract_amount * self.data.discount_factors_L_arr).sum(axis=0)  # Sum across time periods for each scenario

            CV_CP_G = calculate_cvar_left(EuG + SMG_CP,self.data.PROB, self.data.alpha)
            CV_CP_L = calculate_cvar_left(EuL + SML_CP,self.data.PROB, self.data.alpha)

            # Calculate utilities with capture price
            self.results.utility_G_CP = (1-self.data.A_G) * (self.data.PROB* (EuG + SMG_CP)).sum() + self.data.A_G * CV_CP_G
            self.results.utility_L_CP = (1-self.data.A_L) * (self.data.PROB* (EuL + SML_CP)).sum() + self.data.A_L * CV_CP_L

            # Calculate expected earnings for G and L
            self.results.earnings_G_CP = EuG + SMG_CP
            self.results.earnings_L_CP = EuL + SML_CP
        
        # Calculate CVaR for L and G
        self.results.CVaRG = calculate_cvar_left(EuG + SMG,self.data.PROB, self.data.alpha)
        self.results.CVaRL = calculate_cvar_left(EuL + SML,self.data.PROB, self.data.alpha)

        self.results.utility_G = (1-self.data.A_G) * (self.data.PROB*(EuG + SMG)).sum() + self.data.A_G * self.results.CVaRG
        self.results.utility_L = (1-self.data.A_L) * (self.data.PROB*(EuL + SML)).sum() + self.data.A_L * self.results.CVaRL
        self.results.Nash_Product = ((self.results.utility_G - self.data.Zeta_G)) * (self.results.utility_L - self.data.Zeta_L)

        print(f"CVaR auxiliary (VaR threshold) G: {self.variables.cvar_aux_G.x:.5f}")
        print(f"CVaR auxiliary (VaR threshold) L: {self.variables.cvar_aux_L.x:.5f}")

        # Save accumulated revenues
        self.results.earnings_G = EuG + SMG
        self.results.earnings_L = EuL + SML
        # Calculate Alternative Net earnings if capture price was used 

    def run(self):
        """Run the optimization model."""
        self.model.optimize()

        if self.model.status == GRB.OPTIMAL:
            self._save_results()
            self.display_results()
            self.results.optimal = True

            if self.data.Barter == True:
                BS = Barter_Set(self.data, self.results)
                BS.Plotting_Barter_Set()

        else:
            self.results.optimal = False
            raise RuntimeError(f"Optimization of {self.model.ModelName} was not successful")

    def display_results(self):
        """Display optimization results."""
        print("\n-------------------   RESULTS GUROBI  -------------------")
        print(f"Optimal Objective Value (Log): {self.results.objective_value:.5f}")
        print(f"Optimal Objective Value {np.exp(self.results.objective_value):.5f}")
        print(f"Nash Product with optimal S and M: {self.results.Nash_Product:.5f}")
        print(f"Optimal Strike Price(EUR/MWh): {self.results.strike_price:.5f}")
        if self.contract_type == 'PAP':
            print(f"Optimal Contract Capacity (%): {self.results.gamma:.5f}")
        print(f"Optimal Contract Amount(GWh/year): {self.results.contract_amount:.5f}")
        print(f"Optimal Contract Amount(MWh): {self.results.contract_amount_hour:.5f}")
        print(f"Optimal Utility for G: {self.results.utility_G:.5f}")
        print(f"Optimal Utility for L: {self.results.utility_L:.5f}")
        print(f"Threat Point G: {self.data.Zeta_G:.5f}")
        print(f"Threat Point L: {self.data.Zeta_L:.5f}")
        print(f"Delta G: {self.results.utility_G - self.data.Zeta_G:.5f}")
        print(f"Delta L: {self.results.utility_L - self.data.Zeta_L:.5f}")

