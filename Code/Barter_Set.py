import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import linregress
from utils import calculate_cvar_left, _left_tail_mask, _left_tail_weighted_sum
from scipy.interpolate import interp1d
import copy


class Barter_Set:
    def __init__(self, data, results):
        self.data = data
        self.results = results
        self.n = 2000  # Number of points for plotting

        if self.data.contract_type == "PAP":
            self.BS_strike_min =  self.data.SR_star_new
            self.BS_strike_max =  self.data.SU_star_new
        else:
            # Numerical buffer (2 EUR/MWh in GWh units) to extend range for visualization
            self.BS_strike_min =   self.data.SR_star_new-2*1e-3
            self.BS_strike_max =   self.data.SU_star_new+2*1e-3
        print(f"{self.BS_strike_min*1e3:.4f} EUR/MWh")
        print(f"{self.BS_strike_max*1e3:.4f} EUR/MWh")


    

    def cvar_derivative_wrt_M_L(self, M_base, earnings_base, price_matrix, strike, alpha, dx=1e-4):
        """
        Estimate gradient of CVaR with respect to contract share M (gamma) for the Load-side in PAP.
        """
        epsilon = dx

        if self.data.contract_type == "PAP":
            gamma_plus = M_base + epsilon
            gamma_minus = M_base - epsilon

            # Constant across gamma
            EuL = (-self.data.price_L * self.data.load_CR * self.data.load_scenarios).sum(axis=0)

            # Contracted revenue depends on gamma
            con_plus = (gamma_plus * self.data.production_L * (self.data.price_G * self.data.capture_rate - strike)).sum(axis=0)
            con_minus = (gamma_minus * self.data.production_L * (self.data.price_G * self.data.capture_rate - strike)).sum(axis=0)

            rev_plus = EuL + con_plus
            rev_minus = EuL + con_minus

            cvar_plus = calculate_cvar_left(rev_plus,self.data.PROB, self.data.alpha)
            cvar_minus = calculate_cvar_left(rev_minus, self.data.PROB, self.data.alpha)

        else:
            M_plus = M_base + epsilon
            M_minus = M_base - epsilon

            rev_plus = (self.data.discount_factors_L_arr * M_plus * (price_matrix - strike)).sum(axis=0)
            rev_minus = (self.data.discount_factors_L_arr * M_minus * (price_matrix - strike)).sum(axis=0)

            cvar_plus = calculate_cvar_left(earnings_base + rev_plus,self.data.PROB, self.data.alpha)
            cvar_minus = calculate_cvar_left(earnings_base + rev_minus, self.data.PROB, self.data.alpha)

        return (cvar_plus - cvar_minus) / (2 * epsilon)

    def cvar_derivative_wrt_M_G(self, M_base, earnings_base, price_matrix, strike, alpha, dx=1e-4):
        """
        Estimate gradient of CVaR with respect to contract share M (gamma) for the Generator-side in PAP.
        """
        epsilon = dx

        if self.data.contract_type == "PAP":
            gamma_plus = M_base + epsilon
            gamma_minus = M_base - epsilon

            # Generator revenue with gamma_plus
            rev_plus = (
                (1 - gamma_plus) * self.data.production_G * self.data.price_G * self.data.capture_rate + gamma_plus * self.data.production_G * strike
            ).sum(axis=0)

            # Generator revenue with gamma_minus
            rev_minus = (
                (1 - gamma_minus) * self.data.production_G * self.data.price_G * self.data.capture_rate + gamma_minus * self.data.production_G * strike
            ).sum(axis=0)

            cvar_plus = calculate_cvar_left(rev_plus,self.data.PROB, alpha)
            cvar_minus = calculate_cvar_left(rev_minus, self.data.PROB, alpha)

        else:
            M_plus = M_base + epsilon
            M_minus = M_base - epsilon

            rev_plus = (self.data.discount_factors_G_arr * M_plus * (strike - price_matrix)).sum(axis=0)
            rev_minus = (self.data.discount_factors_G_arr * M_minus * (strike - price_matrix)).sum(axis=0)

            cvar_plus = calculate_cvar_left(earnings_base + rev_plus,self.data.PROB, alpha)
            cvar_minus = calculate_cvar_left(earnings_base + rev_minus,self.data.PROB,alpha)

        return (cvar_plus - cvar_minus) / (2 * epsilon)
    
    def expectation_derivative_wrt_M_L(self, M_base, earnings_base, price_matrix, strike, dx=1e-4):
        """
        Estimate the gradient of the expected value of earnings with respect to contract volume M.
        """
        epsilon = dx
        if self.data.contract_type =="PAP":
        
            gamma_plus = M_base + epsilon
            gamma_minus = M_base - epsilon

            EuL = (-self.data.price_L * self.data.load_CR * self.data.load_scenarios).sum(axis=0)

            # Fix: Use price_L instead of price_G
            con_plus = (gamma_plus * self.data.production_L * (self.data.price_L * self.data.capture_rate - strike)).sum(axis=0)
            con_minus = (gamma_minus * self.data.production_L * (self.data.price_L * self.data.capture_rate - strike)).sum(axis=0)

            rev_plus = EuL + con_plus
            rev_minus = EuL + con_minus
            expected_plus = (self.data.PROB * rev_plus).sum()
            expected_minus = (self.data.PROB * rev_minus).sum()
        else:
            M_plus = M_base + epsilon
            M_minus = M_base - epsilon

            rev_plus = (self.data.discount_factors_L_arr * M_plus * (price_matrix - strike)).sum(axis=0)
            rev_minus = (self.data.discount_factors_L_arr * M_minus * (price_matrix - strike)).sum(axis=0)

            # Calculate expected earnings for M_plus and M_minus
            expected_plus = (self.data.PROB * (earnings_base + rev_plus)).sum()
            expected_minus = (self.data.PROB * (earnings_base + rev_minus)).sum()


        # Return the finite difference approximation of the derivative
        return (expected_plus - expected_minus) / (2 * epsilon)

    def expectation_derivative_wrt_M_G(self, M_base, earnings_base, price_matrix, strike, dx=1e-4):
        """
        Estimate the gradient of the expected value of earnings with respect to contract volume M.
        """
        epsilon = dx
        if self.data.contract_type == "PAP":
            gamma_plus = M_base + epsilon
            gamma_minus = M_base - epsilon
            
            rev_plus = ((1-gamma_plus) * self.data.production_G * self.data.price_G * self.data.capture_rate + 
                        gamma_plus * self.data.production_G * strike).sum(axis=0)
            # Fix: Use gamma_minus instead of gamma_plus
            rev_minus = ((1-gamma_minus) * self.data.production_G * self.data.price_G * self.data.capture_rate + 
                        gamma_minus * self.data.production_G * strike).sum(axis=0)

            expected_plus = (self.data.PROB * rev_plus).sum()
            expected_minus = (self.data.PROB * rev_minus).sum()

        else:
            M_plus  = M_base  + epsilon
            M_minus = M_base - epsilon

            rev_plus = (self.data.discount_factors_G_arr * M_plus * (strike - price_matrix)).sum(axis=0)
            rev_minus = (self.data.discount_factors_G_arr * M_minus * (strike - price_matrix)).sum(axis=0)

            expected_plus = (self.data.PROB * (earnings_base + rev_plus)).sum()
            expected_minus = (self.data.PROB * (earnings_base + rev_minus)).sum()


        return (expected_plus - expected_minus) / (2 * epsilon)

    def Utility_G(self, strike,volume):

        """
        strike : Strike Price [float]
        volume : Contract volume [float] or percentage [float] in PAP
        """

        if self.data.contract_type == "PAP":
            # For each scenario, sum production over time, then apply contract fraction
            earnings = ((1-volume) * self.data.production_G * self.data.price_G * self.data.capture_rate + volume * self.data.production_G * strike).sum(axis=0)
            # earnings: scenario-wise
            CVaR_G = calculate_cvar_left(earnings,self.data.PROB, self.data.alpha) 
        
        else:
            rev_contract = (self.data.discount_factors_G_arr * volume * (strike - self.data.price_G)).sum(axis=0)
            no_contract = self.data.net_earnings_no_contract_priceG_G

            earnings = no_contract + rev_contract

            CVaR_G = calculate_cvar_left(earnings,self.data.PROB, self.data.alpha)

        Utility = (1 - self.data.A_G) * (self.data.PROB * earnings).sum() + self.data.A_G * CVaR_G
        return Utility

    def Utility_L(self, strike,volume):
        if self.data.contract_type =="PAP":


            # Load contract revenue
            EuL = (-self.data.price_L * self.data.load_CR * self.data.load_scenarios).sum(axis=0) # Sum across time periods for each scenario
            SML =   (volume* self.data.production_L * self.data.price_L * self.data.capture_rate -  volume * strike * self.data.production_L).sum(axis=0) # Sum across time periods for each scenario

            earnings = EuL + SML
            CVaR_L = calculate_cvar_left(earnings,self.data.PROB, self.data.alpha)
        else:
            rev_contract = (self.data.discount_factors_L_arr * volume * (self.data.price_L - strike)).sum(axis=0)
            no_contract = self.data.net_earnings_no_contract_priceL_L

            earnings = no_contract + rev_contract

            CVaR_L = calculate_cvar_left(earnings,self.data.PROB, self.data.alpha)

        Utility =(1-self.data.A_L)*(self.data.PROB*earnings).sum() + self.data.A_L * CVaR_L
        
        
        return Utility

    def _Revenue_G(self, strike, volume):
        if self.data.contract_type == "PAP":
            # Generator revenue = (1-γ)×PG×CR×W + γ×S×W
            pi_G = ((1-volume) * self.data.production_G * self.data.price_G * self.data.capture_rate + 
                    volume * self.data.production_G * strike).sum(axis=0)
        else: 
            pi_G = self.data.net_earnings_no_contract_priceG_G + (self.data.discount_factors_G_arr * volume * (strike - self.data.price_G)).sum(axis=0)
        return pi_G

    def _Revenue_L(self, strike, volume):
        if self.data.contract_type == "PAP":
            # Load revenue = -PL×CR×L + γ×W×(PL×CR - S)
            # Base load cost
            EuL = (-self.data.price_L * self.data.load_CR * self.data.load_scenarios).sum(axis=0)
            # Contract revenue: volume of production at (market price - strike)
            SML = (volume * self.data.production_L * (self.data.price_L * self.data.capture_rate - strike)).sum(axis=0)
            pi_L = EuL + SML
        else:
            pi_L = self.data.net_earnings_no_contract_priceL_L + (self.data.discount_factors_L_arr * volume * (self.data.price_L - strike)).sum(axis=0)
        return pi_L
    
    def _dS_PAP(self,S,gamma):
            """
            Analytical derivative dU_L/dU_G with respect to strike price S (Lemma 2).
            Computes -[dU_L/dS] / [dU_G/dS] for the PAP contract type.
            """
            pi_G = self._Revenue_G(S, gamma)
            pi_L = self._Revenue_L(S, gamma)

            ord_G, bidx_G = _left_tail_mask(pi_G,self.data.PROB, self.data.alpha)
            ord_L, bidx_L = _left_tail_mask(pi_L, self.data.PROB, self.data.alpha)

            prod = self.data.production.sum()

            tail_G = _left_tail_weighted_sum(self.data.PROB, prod, ord_G, bidx_G, self.data.alpha)
            tail_L = _left_tail_weighted_sum(self.data.PROB, prod, ord_L, bidx_L, self.data.alpha)

            num =  (1-self.data.A_L)*(self.data.PROB * prod).sum() + self.data.A_L * tail_L
            den =  (1-self.data.A_G)*(self.data.PROB * prod).sum() + self.data.A_G * tail_G

            return - num / den
    
    def _dgamma_PAP(self,S,gamma):
        """
        Analytical derivative dU_L/dU_G with respect to contract fraction gamma (Lemma 5).
        Computes [dU_L/dgamma] / [dU_G/dgamma] for the PAP contract type.
        """
        pi_G = self._Revenue_G(S, gamma)
        pi_L = self._Revenue_L(S, gamma)

        ord_G, bidx_G = _left_tail_mask(pi_G,self.data.PROB, self.data.alpha)
        ord_L, bidx_L = _left_tail_mask(pi_L, self.data.PROB, self.data.alpha)


        rev_G = (self.data.production_G * (S - self.data.price_G * self.data.capture_rate)).sum(axis=0)

        rev_L = (self.data.production_L * (self.data.price_L * self.data.capture_rate - S)).sum(axis=0)

        expected_G = (self.data.PROB * rev_G).sum()
        expected_L = (self.data.PROB * rev_L).sum()

        tail_G = _left_tail_weighted_sum(self.data.PROB, rev_G, ord_G, bidx_G, self.data.alpha)
        tail_L = _left_tail_weighted_sum(self.data.PROB, rev_L, ord_L, bidx_L, self.data.alpha)

        return ((1-self.data.A_L)*expected_L + self.data.A_L * tail_L)/((1-self.data.A_G)*expected_G + self.data.A_G * tail_G)
        
    def compute_lemma2_slope(self):
        """
        Compute the Lemma 2 slope (dS) by fixing contract amount M and
        varying strike price S, then fitting a linear regression.

        Returns the numerical slope value.
        """
        if self.data.contract_type == "PAP":
            M_fixed = 1  # [0,1] for PAP
        else:
            M_fixed = 0.5 * (self.data.contract_amount_min + self.data.contract_amount_max)

        S_space = np.linspace(self.BS_strike_min - 3 * 1e-3, self.BS_strike_max + 3 * 1e-3, self.n)

        V_Lemma2 = np.zeros((self.n, 2))
        for i, S in enumerate(S_space):
            V_Lemma2[i, 0] = self.Utility_G(S, M_fixed)
            V_Lemma2[i, 1] = self.Utility_L(S, M_fixed)

        slope, intercept, r_value, p_value, std_err = linregress(V_Lemma2[:, 0], V_Lemma2[:, 1])
        print(f"R Value: {r_value:.4f}")
        print(f"Numerical Slope of Lemma 2 curve: {slope:.4f}")

        if self.data.contract_type == "PAP":
            pap_slope = np.empty(self.n)
            for i, S in enumerate(S_space):
                pap_slope[i] = self._dS_PAP(S, M_fixed)
            theo_slope = pap_slope.mean()
            print(f"Theoretical Slope of Lemma 2 should be:{theo_slope:.4f}")
        else:
            if self.data.Discount == True:
                t = np.arange(self.data.n_time)
                lem_2_L = (1 / ((1 + self.data.d_L) ** t)).sum()
                lem_2_G = (1 / ((1 + self.data.d_G) ** t)).sum()
                slope_theo = -lem_2_L / lem_2_G
                print(f"Theoretical Slope of Lemma 2 should be:{slope_theo:.4f}")
            else:
                print(f"Theoretical Slope of Lemma 2 should be:{-1:f}")

        return slope

    def Plotting_Barter_Set_Lemma2(self):
        """
        Plot the utility possibility curve for Lemma 2:
        Fix contract amount M, vary strike price S from S^R to S^U.
        """
        slope = self.compute_lemma2_slope()

        if self.data.contract_type == "PAP":
            M_fixed = 1  # [0,1] for PAP
        else:
            M_fixed = 0.5 * (self.data.contract_amount_min + self.data.contract_amount_max)

        S_space = np.linspace(self.BS_strike_min - 3 * 1e-3, self.BS_strike_max + 3 * 1e-3, self.n)

        V_Lemma2 = np.zeros((self.n, 2))
        for i, S in enumerate(S_space):
            V_Lemma2[i, 0] = self.Utility_G(S, M_fixed)
            V_Lemma2[i, 1] = self.Utility_L(S, M_fixed)

        if self.data.contract_type == "PAP":
            pap_slope = np.empty(self.n)
            for i, S in enumerate(S_space):
                pap_slope[i] = self._dS_PAP(S, M_fixed)

        plt.figure(figsize=(10, 6))
        plt.plot(V_Lemma2[:, 0], V_Lemma2[:, 1], label='Lemma 2 Curve (M fixed)', color='purple')
        plt.scatter(V_Lemma2[0, 0], V_Lemma2[0, 1], color='purple', marker='o', s=100, label='Start (S = S^R)')
        plt.scatter(V_Lemma2[-1, 0], V_Lemma2[-1, 1], color='purple', marker='*', s=100, label='End (S = S^U)')
        if self.data.contract_type == "PAP":
            plt.plot(pap_slope, label='Theoretical Slope', color='orange', linestyle='--')
        plt.annotate(f"Slope: {slope:.4f}",
             xy=(V_Lemma2[self.n//2, 0], V_Lemma2[self.n//2, 1]),
             xytext=(30, 30), textcoords='offset points',
             color='purple', fontsize=10,
             arrowprops=dict(arrowstyle="->", color='purple'))
        plt.xlabel('Utility G')
        plt.ylabel('Utility L')
        plt.legend()
        plt.grid()
        plt.title(f'Lemma 2: Utility Set for Fixed M={M_fixed:.2f} MWh, S in [{self.BS_strike_min*1e3}, {self.BS_strike_max*1e3}] EUR/MWh')
        plt.show()

        plt.figure(figsize=(10, 6))
        plt.scatter(V_Lemma2[:, 0], V_Lemma2[:, 1], color='purple', marker='o', s=50, label='Start (S = S^R)')
        plt.annotate(f"Slope: {slope:.4f}",
             xy=(V_Lemma2[self.n//2, 0], V_Lemma2[self.n//2, 1]),
             xytext=(30, 30), textcoords='offset points',
             color='purple', fontsize=10,
             arrowprops=dict(arrowstyle="->", color='purple'))
        plt.xlabel('Utility G')
        plt.ylabel('Utility L')
        plt.legend()
        plt.grid()
        plt.title(f'Lemma 2: Utility Set for Fixed M={M_fixed:.2f} MWh, S in [{self.BS_strike_min*1e3}, {self.BS_strike_max*1e3}] EUR/MWh')
        plt.show()

        return slope

    def calculate_utility_derivative(self, M_space, V_1_Low, V_2_High, plotting=False):
        # Initial slope calculations

        if self.data.contract_type == "PAP":
            dS_SR = np.zeros(self.n)
            dS_SU = np.zeros(self.n)

            for i in range(self.n):
                dS_SR[i] = self._dS_PAP(self.BS_strike_min, M_space[i])
                dS_SU[i] = self._dS_PAP(self.BS_strike_max, M_space[i])

        step_size = M_space[1] - M_space[0]  # Step size
        duG_1 = np.gradient(V_1_Low[:,0],step_size,edge_order=1)
        duL_1 = np.gradient(V_1_Low[:,1],step_size,edge_order=1)
        slope_1 = duL_1 / duG_1

        duG_2 = np.gradient(V_2_High[:,0],step_size,edge_order=1)
        duL_2 = np.gradient(V_2_High[:,1],step_size,edge_order=1)
        slope_2 = duL_2 / duG_2

        if plotting:
            fig, axes = plt.subplots(1, 2, figsize=(14, 10))
            ax_1 = axes[0]
            ax_2 = axes[1]

            ax_1.plot(M_space, slope_1, label='Slope Curve 1', color='blue'  )
            if self.data.contract_type == "PAP":
                ax_1.plot(M_space, dS_SR, label='dS Curve 1', color='black', linestyle='--')
            else:
                ax_1.axhline(self.dS, color='black', linestyle='--', label='dS Threshold')
            ax_2.plot(M_space, slope_2, label='Slope Curve 2', color='red'  )
            if self.data.contract_type == "PAP":
                ax_2.plot(M_space, dS_SU, label='dS Curve 2', color='black', linestyle='--')
            else:
                ax_2.axhline(self.dS, color='black', linestyle='--', label='dS Threshold')
            plt.show()
   

        # Lemma 5 MR (L)
        cvgradientv1_L =  self.cvar_derivative_wrt_M_L(M_space[0],self.data.net_earnings_no_contract_priceL_L, self.data.price_L, self.BS_strike_min, self.data.alpha, dx=step_size)
        cvgradientv1_G =  self.cvar_derivative_wrt_M_G(M_space[0],self.data.net_earnings_no_contract_priceG_G, self.data.price_G, self.BS_strike_min, self.data.alpha, dx=step_size)
        Egradientv1_L = self.expectation_derivative_wrt_M_L(M_space[0],self.data.net_earnings_no_contract_priceL_L, self.data.price_L, self.BS_strike_min, dx=step_size)
        Egradientv1_G = self.expectation_derivative_wrt_M_G(M_space[0],self.data.net_earnings_no_contract_priceG_G, self.data.price_G, self.BS_strike_min, dx=step_size)


        # Lemma 5 MU (L )
        cvgradientv2_L =  self.cvar_derivative_wrt_M_L(M_space[-1],self.data.net_earnings_no_contract_priceL_L, self.data.price_L, self.BS_strike_max, self.data.alpha, dx=step_size)
        cvgradientv2_G =  self.cvar_derivative_wrt_M_G(M_space[-1],self.data.net_earnings_no_contract_priceG_G, self.data.price_G, self.BS_strike_max, self.data.alpha, dx=step_size)
        Egradientv2_L = self.expectation_derivative_wrt_M_L(M_space[-1],self.data.net_earnings_no_contract_priceL_L, self.data.price_L, self.BS_strike_max, dx=step_size)
        Egradientv2_G = self.expectation_derivative_wrt_M_G(M_space[-1],self.data.net_earnings_no_contract_priceG_G, self.data.price_G, self.BS_strike_max, dx=step_size)

        if self.data.contract_type == "PAP":
            uL_duG_theoretical_MR = ((1-self.data.A_L)*Egradientv1_L + self.data.A_L * cvgradientv1_L)/((1-self.data.A_G)*Egradientv1_G + self.data.A_G * cvgradientv1_G)
            uL_duG_theoretical_MU = ( (1-self.data.A_L)*Egradientv2_L+ self.data.A_L * cvgradientv2_L)/((1-self.data.A_G)*Egradientv2_G + self.data.A_G * cvgradientv2_G)

        else:
            uL_duG_theoretical_MR = ((1-self.data.A_L)*Egradientv1_L + self.data.A_L * cvgradientv1_L)/((1-self.data.A_G)*Egradientv1_G + self.data.A_G * cvgradientv1_G)
            uL_duG_theoretical_MU = ((1-self.data.A_L)*Egradientv2_L + self.data.A_L * cvgradientv2_L)/((1-self.data.A_G)*Egradientv2_G + self.data.A_G * cvgradientv2_G)

        print("Slope of Utility Curve 1 (MR):")
        print(slope_1[0])
        print(slope_1[-1])
        print("Gradients analytical")
        print(uL_duG_theoretical_MR)
        print(uL_duG_theoretical_MU)
        print("Theoreotical slopes for MR and MU: finite difference")
  
    
        if self.data.contract_type == "PAP":
            self.dS_min = self._dS_PAP(self.BS_strike_min, M_space[0])
            self.dS_max = self._dS_PAP(self.BS_strike_min, M_space[-1])
        else:
            self.dS_min = self.dS
            self.dS_max = self.dS
       
        if slope_1[0] < self.dS_min:
            cond_MR = True
        else:
            cond_MR = False
        
        if slope_1[-1] > self.dS_max:
            cond_MU = True
        else:
            cond_MU = False


        # Find first crossing points
        if self.data.contract_type == "PAP":
            mask_negative_v1 = slope_1 > dS_SR
            mask_positive_v2 = slope_2 < dS_SU
        else:
            mask_negative_v1 = slope_1 > self.dS
            mask_positive_v2 = slope_2 < self.dS
        first_index_negative_v1 = np.argmax(mask_negative_v1)
        first_index_positive_v2 = np.argmax(mask_positive_v2)
        M_SR = M_space[first_index_negative_v1]
        M_SU = M_space[first_index_positive_v2]

        if cond_MR == False and cond_MU == False:
            print("No Barter Set exists, as the conditions of Lemma 5 are not satisfied.")
            M_SR, M_SU = M_SU,M_SU
            return cond_MR,cond_MU,None, None, M_SR, M_SU, None, None
        elif cond_MR == True and cond_MU == False:
            print("Barter Set exists, no concave part in the utility curves")
            if self.data.contract_type == "PAP":
                M_SR = 1
                M_SU = 1
            else:
                M_SR = self.data.contract_amount_min
                M_SU = self.data.contract_amount_max
            return cond_MR,cond_MU,None, None, M_SR, M_SU ,None , None
        else :
            print("Barter Set exists, concave part in the utility curves")

        return cond_MR,cond_MU,slope_1, slope_2, M_SR, M_SU ,first_index_negative_v1 , first_index_positive_v2
    
    def Plotting_Barter_Set(self):

        self.dS = self.compute_lemma2_slope()

        V_1_Low= np.zeros((self.n,2))
        V_2_High = np.zeros((self.n,2))

      
        if self.data.contract_type == "PAP":
            # For PAP, we need to calculate the contract amount as a percentage of production
            M_space = np.linspace(0, 1, self.n)
        else:
            M_space = np.linspace(self.data.contract_amount_min, self.data.contract_amount_max, self.n)
        
        u_opt_curve = np.zeros((self.n,2))
        nash_product_curve =np.zeros(self.n)


        # Calculate the utility for each contract revenue
        for i in range(len(M_space)):            #Curve 1 
            V_1_Low[i,0] = self.Utility_G(self.BS_strike_min, M_space[i]) - self.data.Zeta_G
            V_1_Low[i,1] = self.Utility_L(self.BS_strike_min, M_space[i]) - self.data.Zeta_L
            #Curve 2
            V_2_High[i,0] = self.Utility_G(self.BS_strike_max , M_space[i]) - self.data.Zeta_G
            V_2_High[i,1] = self.Utility_L(self.BS_strike_max , M_space[i]) - self.data.Zeta_L


            if self.results.optimal:
                # Convert EUR/MWh back to EUR/GWh (internal units)
                strike_internal = self.results.strike_price * 1e-3
                u_opt_curve[i,0] = self.Utility_G(strike_internal, M_space[i]) - self.data.Zeta_G
                u_opt_curve[i,1] = self.Utility_L(strike_internal, M_space[i]) - self.data.Zeta_L
                nash_product_curve[i] = (u_opt_curve[i,0])*(u_opt_curve[i,1])

     
        plt.figure(figsize=(10, 6))
        plt.plot(u_opt_curve[:,0], nash_product_curve, label='Curve 1 $S^R$', color='blue')
        plt.show()
        cond_MR,cond_MU,slope_1, slope_2, M_SR,M_SU, first_index_v1,first_index_v2= self.calculate_utility_derivative(M_space,V_1_Low, V_2_High)
        # Utility at the optimal contract amounts M_SR and M_SU
        UG_Low_Mopt = self.Utility_G(self.BS_strike_min, M_SR) - self.data.Zeta_G
        UL_Low_Mopt = self.Utility_L(self.BS_strike_min, M_SR) - self.data.Zeta_L
        UG_High_Mopt = self.Utility_G(self.BS_strike_max, M_SU) - self.data.Zeta_G
        UL_High_Mopt = self.Utility_L(self.BS_strike_max, M_SU) - self.data.Zeta_L

        # Normalized disagreement point: utilities are already shifted by Zeta
        self.disagreement_point = [0, 0]

        # Keeping SR constant and plotting through MR to MU (Curve 1)
        plt.figure(figsize=(10, 6))
        plt.plot(V_1_Low[:,0], V_1_Low[:,1], label='Curve 1 $S^R$', color='blue')
        plt.plot(V_2_High[:,0], V_2_High[:,1], label='Curve 2 $S^U$', color='red')

        arrow_positions = np.linspace(0,1,10)  # Positions along the curve (as fractions)
        for pos in arrow_positions:
            point_idx = int(len(V_1_Low) * pos)
            if point_idx + 1 < len(V_1_Low):
                plt.annotate('', 
                    xy=(V_1_Low[point_idx+1,0], V_1_Low[point_idx+1,1]),
                    xytext=(V_1_Low[point_idx,0], V_1_Low[point_idx,1]),
                    arrowprops=dict(arrowstyle='->', color='blue', lw=2),
                    annotation_clip=True)

        # Add multiple direction arrows for Curve 2 (red)
        for pos in arrow_positions:
            point_idx = int(len(V_2_High) * pos)
            if point_idx + 1 < len(V_2_High):
                plt.annotate('', 
                    xy=(V_2_High[point_idx+1,0], V_2_High[point_idx+1,1]),
                    xytext=(V_2_High[point_idx,0], V_2_High[point_idx,1]),
                    arrowprops=dict(arrowstyle='->', color='red', lw=2),
                    annotation_clip=True)

        if cond_MR==True:
            # Plot Optimal Contract Amount Point with fixed price SR and SU
            MSR_point = [UG_Low_Mopt, UL_Low_Mopt]
            MSU_point = [UG_High_Mopt, UL_High_Mopt]

            if self.results.optimal:

                if self.data.contract_type == "PAP":
                    plt.scatter(UG_Low_Mopt, UL_Low_Mopt, color='green', marker='o', s=150, label=fr'V1 $\gamma$ = {100*M_SR:.2f}%, M* = ({self.data.generator_contract_capacity * M_SR:.2f} MW)')
                    plt.scatter(UG_High_Mopt, UL_High_Mopt, color='green', marker='*', s=150, label=fr'V1 $\gamma$ = {100*M_SU:.2f}%, M* = ({self.data.generator_contract_capacity * M_SU:.2f} MW)')
                else:
             

                    plt.scatter(UG_Low_Mopt, UL_Low_Mopt, color='green', marker='o', s=150, label=f'V1 M* = ({M_SR /8760*1e3:.2f} MWh)')
                    plt.scatter(UG_High_Mopt, UL_High_Mopt, color='green', marker='*', s=150, label=f'V2 M* = ({M_SU/8760*1e3:.2f} MWh)')


                utility = [self.results.utility_G - self.data.Zeta_G, self.results.utility_L - self.data.Zeta_L]
                self.plot_barter_curve( MSR_point, MSU_point, utility)


                plt.scatter(self.results.utility_G-self.data.Zeta_G, self.results.utility_L-self.data.Zeta_L, color='red', marker='o', s=150, label='Optimization Result (G,L)')

                for pos in arrow_positions:
                    point_idx = int(len(V_2_High) * pos)
                    if point_idx + 1 < len(V_2_High):
                        plt.annotate('', 
                            xy=(u_opt_curve[point_idx+1,0], u_opt_curve[point_idx+1,1]),
                            xytext=(u_opt_curve[point_idx,0], u_opt_curve[point_idx,1]),
                            arrowprops=dict(arrowstyle='->', color='purple', lw=2.5),
                            annotation_clip=True)
                plt.plot(u_opt_curve[:,0], u_opt_curve[:,1], color='purple', linestyle='--', label='Optimal S* Utility Curve', lw=2.5)


        plt.axvline(x=self.disagreement_point[0], color='black', linestyle='--', alpha=0.7)
        plt.axhline(y=self.disagreement_point[1], color='black', linestyle='--', alpha=0.7)
        plt.scatter(self.disagreement_point[0], self.disagreement_point[1], color='black', marker='o', s=150, label='Disagreement point')

        plt.xlabel(f'$Utility - Disagreement Point (G) $',fontsize=20)
        plt.ylabel(f'$Utility - Disagreement Point (L) $',fontsize=20)

        plt.xticks(fontsize=18)
        plt.yticks(fontsize=18)

        plt.title(f'Barter Set(Normalized): {self.data.contract_type} A_G={self.data.A_G:.2f}, A_L={self.data.A_L:.2f}',fontsize=21)


        plt.legend(fontsize=14)
        plt.grid()
        plt.show()

   
        print("Done")

    def plot_multiple_barter_sets(self, AG_values, AL_values):
        """
        Plot barter sets for different risk aversion pairs (A_G, A_L).
        Each pair gets its own color and label.
        Only the barter curve and shaded region are plotted.
        """
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        colors = cm.viridis(np.linspace(0, 1, len(AG_values) * len(AL_values)))

        color_idx = 0

        plt.figure(figsize=(6, 6))

        for AG in AG_values:
            for AL in AL_values:
                # Set risk aversion for this pair
                self.data.A_G = AG
                self.data.A_L = AL

                zeta_G = self.Utility_G(self.BS_strike_min, 0)
                zeta_L = self.Utility_L(self.BS_strike_min, 0)

                # Recompute barter set for this pair
                V_1_Low = np.zeros((self.n, 2))
                V_2_High = np.zeros((self.n, 2))
                if self.data.contract_type == "PAP":
                    M_space = np.linspace(0, 1, self.n)
                else:
                    M_space = np.linspace(self.data.contract_amount_min, self.data.contract_amount_max, self.n)

                for i in range(len(M_space)):
                    V_1_Low[i, 0] = self.Utility_G(self.BS_strike_min, M_space[i]) - zeta_G
                    V_1_Low[i, 1] = self.Utility_L(self.BS_strike_min, M_space[i]) - zeta_L
                    V_2_High[i, 0] = self.Utility_G(self.BS_strike_max, M_space[i]) - zeta_G
                    V_2_High[i, 1] = self.Utility_L(self.BS_strike_max, M_space[i]) - zeta_L

                # Find optimal contract points
                cond_MR, cond_MU, slope_1, slope_2, M_SR, M_SU, _, _ = self.calculate_utility_derivative(M_space, V_1_Low, V_2_High)
                UG_Low_Mopt = self.Utility_G(self.BS_strike_min, M_SR) - zeta_G
                UL_Low_Mopt = self.Utility_L(self.BS_strike_min, M_SR) - zeta_L
                UG_High_Mopt = self.Utility_G(self.BS_strike_max, M_SU) - zeta_G
                UL_High_Mopt = self.Utility_L(self.BS_strike_max, M_SU) - zeta_L

                MR_point = [UG_Low_Mopt, UL_Low_Mopt]
                MU_point = [UG_High_Mopt, UL_High_Mopt]

                # Slope and intersections (normalized)
                slope_opt = np.round((MU_point[1] - MR_point[1]) / (MU_point[0] - MR_point[0]), 8)
                b_opt = MR_point[1] - slope_opt * MR_point[0]
                vertical_intersect_y = slope_opt * 0 + b_opt  # zeta_G normalized to 0
                horizontal_intersect_x = (0 - b_opt) / slope_opt  # zeta_L normalized to 0

                # Create barter set region polygon (normalized)
                vertices = np.array([
                    [0, 0],  # Start at normalized threat point
                    [0, vertical_intersect_y],  # Vertical intersection
                    [horizontal_intersect_x, 0],  # Horizontal intersection
                    [0, 0]  # Back to start
                ])

                plt.plot([MR_point[0], MU_point[0]], [MR_point[1], MU_point[1]], color=colors[color_idx],  linestyle='--', alpha=0.7)

                label = f"A_G={AG:.2f}, A_L={AL:.2f}"

                plt.plot(V_1_Low[:, 0], V_1_Low[:, 1], color=colors[color_idx], label=label, linewidth=2.5)
                plt.plot(V_2_High[:, 0], V_2_High[:, 1], color=colors[color_idx], linewidth=2.5)
                plt.scatter(V_1_Low[0, 0], V_1_Low[0, 1], color='black', marker='o', s=125)
                polygon = plt.Polygon(vertices, facecolor=colors[color_idx], alpha=0.2, edgecolor=None)
                plt.gca().add_patch(polygon)
                color_idx += 1

        plt.xlabel(f'$Utility - Disagreement Point (G)$',fontsize=20)
        plt.ylabel(f'$Utility - Disagreement Point (L)$',fontsize=20)
        plt.xticks(fontsize=18)
        plt.yticks(fontsize=18)
        plt.title(f'Barter Sets(Normalized): {self.data.contract_type} for Different Risk Aversion Pairs', fontsize=21)
        plt.legend(fontsize=18, loc='center left')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.show()