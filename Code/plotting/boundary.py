"""Boundary analysis plotting methods."""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from sklearn.linear_model import LinearRegression
from utils import calculate_cvar_left, weighted_expected_value
from .base import cmap_red_green


class BoundaryPlotsMixin:
    """Mixin providing boundary analysis plotting methods."""

    def _plot_no_contract(self, filename=None):
        """Plots histograms of no-contract revenues and threat point evolution."""
        # Create first figure for histograms
        fig1, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Plot histograms of no-contract revenues
        ax_G = axes[0]
        ax_L = axes[1]

        # Scale values to 10^5 for better readability
        G_values = self.cm_data.net_earnings_no_contract_G_df.sum().values / 1e5
        L_values = self.cm_data.net_earnings_no_contract_L.values / 1e5

        # Create histogram bins
        bins_G = np.linspace(min(G_values), max(G_values), 19)
        bins_L = np.linspace(min(L_values), max(L_values), 19)

        # Plot histograms



        # Create second figure for threat point evolution

        # Calculate threat points for different risk aversion values
        risk_aversion_values = np.linspace(0, 1, 4)
        zeta_G_values = []
        zeta_L_values = []

        # Calculate CVaR values (constant for all risk aversion values)
        cvar_G = calculate_cvar_left(self.cm_data.net_earnings_no_contract_G,self.cm_data.PROB, self.cm_data.alpha)
        cvar_L = calculate_cvar_left(self.cm_data.net_earnings_no_contract_L,self.cm_data.PROB, self.cm_data.alpha)
        mean_G = self.cm_data.net_earnings_no_contract_G.mean()
        mean_L = self.cm_data.net_earnings_no_contract_L.mean()

        # Calculate threat points for different risk aversion values
        for A in risk_aversion_values:
            zeta_G = (1-A)*mean_G + A*cvar_G
            zeta_L = (1-A)*mean_L + A*cvar_L
            zeta_G_values.append(zeta_G/1e5)
            zeta_L_values.append(zeta_L/1e5)

        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']

        ax_G.hist(G_values, bins=bins_G, alpha=0.6, color='blue', density=False)
        for i,zeta in enumerate(zeta_G_values):
            current_color = colors[i % len(colors)]  # Cycle through colors
            ax_G.axvline(zeta, linestyle="--", color=current_color, label=f'A_G={risk_aversion_values[i]:.2f} - Threat Point: {zeta:.2f}')
        ax_G.set_title('Generator (G) No-Contract Revenue Distribution', fontsize=self.titlesize)
        ax_G.set_xlabel('Generator Revenue ($ x 10^5)', fontsize=self.labelsize)
        ax_G.set_ylabel('Frequency', fontsize=self.labelsize)
        ax_G.grid(True, axis='y', linestyle='--', alpha=0.7)
        ax_G.legend()

        ax_L.hist(L_values, bins=bins_L, alpha=0.6, color='green', density=False)
        for i,zeta in enumerate(zeta_L_values):
            current_color = colors[i % len(colors)]
            ax_L.axvline(zeta, linestyle="--", color=current_color, label=f'A_L={risk_aversion_values[i]:.2f} - Threat Point: {zeta:.2f}')
        ax_L.set_title('Load (L) No-Contract Revenue Distribution', fontsize=self.titlesize)
        ax_L.set_xlabel('Load Revenue ($ x 10^5)', fontsize=self.labelsize)
        ax_L.set_ylabel('Frequency', fontsize=self.labelsize)
        ax_L.grid(True, axis='y', linestyle='--', alpha=0.7)
        ax_L.legend()

        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            print(f"Plot saved to {filepath}")
            fig1.savefig(filepath.replace('.', '_hist.'))
            print(f"Plots saved to {filepath}")
            plt.close(fig1)
        else:
            plt.show()

    def _plot_no_contract_boundaries(self, sensitivity_type, filename=None):
        """
        Plot the no-contract boundaries for different risk aversion scenarios.

        Parameters:
        -----------
        type:  str
            Type of boundary to plot. price or production
        filename : str, optional
            Path to save the plot. If None, the plot will be displayed.
        """
        plt.figure(figsize=(12, 8))
        xlim = (-31, 31)
        ylim = (-31, 31)

        if sensitivity_type == "price":
            boundary_results = self.boundary_results_price
        elif sensitivity_type == "production":
            boundary_results = self.boundary_results_production
        else:
            boundary_results = []

        # Prepare axis
        ax = plt.gca()

        # Plot each scenario's feasible shading and boundary contour; else fallback
        for result in boundary_results:
            scenario = result['scenario']

            if 'feas_mask' in result and 'KL_grid' in result and 'KG_grid' in result:
                KL_grid = np.array(result['KL_grid'])
                KG_grid = np.array(result['KG_grid'])
                feas_mask = np.array(result['feas_mask'])
                try:
                    # Shading: fill feasible region for this scenario (no legend entry)
                    ax.contourf(KL_grid * 100, KG_grid * 100, feas_mask,
                                levels=[0.5, 1.1], colors=[scenario['color']],
                                alpha=0.15, antialiased=True, zorder=1)
                    # Boundary curve on top
                    ax.contour(KL_grid * 100, KG_grid * 100, feas_mask,
                               levels=[0.5], colors=[scenario['color']],
                               linestyles=[scenario['linestyle']], linewidths=[scenario['linewidth']], zorder=3)
                    # Legend proxy for the line
                    ax.plot([], [], color=scenario['color'], linestyle=scenario['linestyle'],
                            linewidth=scenario['linewidth'], label=scenario['label'])
                except Exception as e:
                    print(f"Contour plotting failed for {scenario['label']}: {e}. Falling back to points/regression.")
                    # Fallback to regression through boundary points if present
                    boundary_points = np.array(result.get('boundary_points', []))
                    if len(boundary_points) >= 2:
                        lowest_boundary = self._extract_lowest_boundary(boundary_points)
                        if lowest_boundary is not None and len(lowest_boundary) >= 2:
                            n_space = np.linspace(xlim[0]*1e-2, xlim[1]*1e-2, 100)
                            X = lowest_boundary[:, 0].reshape(-1, 1)
                            y = lowest_boundary[:, 1]
                            model = LinearRegression().fit(X, y)
                            X_pred = n_space.reshape(-1, 1)
                            boundary = model.predict(X_pred)
                            sns.lineplot(x=n_space*100, y=boundary*100, label=scenario['label'],
                                         linestyle=scenario['linestyle'], linewidth=scenario['linewidth'], color=scenario['color'], zorder=3)
                            sns.scatterplot(x=lowest_boundary[:, 0]*100, y=lowest_boundary[:, 1]*100, s=90, alpha=0.5,
                                            color=scenario['color'], edgecolor='black')
            else:
                # Legacy behavior: use boundary_points with regression
                boundary_points = np.array(result.get('boundary_points', []))
                if len(boundary_points) < 2:
                    print(f"Skipping scenario {scenario['label']} due to insufficient boundary points.")
                    continue
                lowest_boundary = self._extract_lowest_boundary(boundary_points)
                if lowest_boundary is None or len(lowest_boundary) < 2:
                    print(f"Skipping scenario {scenario['label']} due to insufficient boundary points after filtering.")
                    continue
                n_space = np.linspace(xlim[0]*1e-2, xlim[1]*1e-2, 100)
                X = lowest_boundary[:, 0].reshape(-1, 1)
                y = lowest_boundary[:, 1]
                model = LinearRegression().fit(X, y)
                X_pred = n_space.reshape(-1, 1)
                boundary = model.predict(X_pred)
                sns.lineplot(x=n_space*100, y=boundary*100, label=scenario['label'],
                             linestyle=scenario['linestyle'], linewidth=scenario['linewidth'], color=scenario['color'])
                sns.scatterplot(x=lowest_boundary[:, 0]*100, y=lowest_boundary[:, 1]*100, s=90, alpha=0.5,
                                color=scenario['color'], edgecolor='black')

        # Add labels and formatting
        if sensitivity_type == "price":
            plt.xlabel(r'Load price bias $K^L$ (% of $\mathbb{E}[\mathrm{price}]$)', fontsize=self.labelsize)
            plt.ylabel(r'Generator price bias $K^G$ (% of $\mathbb{E}[\mathrm{price}]$)', fontsize=self.labelsize)
        elif sensitivity_type == "production":
            plt.xlabel(r'Load production bias $K^L$ (% of $\mathbb{E}[\mathcal{P}^G]$)', fontsize=self.labelsize)
            plt.ylabel(r'Generator production bias $K^G$ (% of $\mathbb{E}[\mathcal{P}^G]$)', fontsize=self.labelsize)
        plt.title(f'{self.cm_data.contract_type}-{sensitivity_type}: Contract Boundaries for Different Risk Aversion Levels', fontsize=self.titlesize)
        plt.grid(True, alpha=0.3)
        plt.legend(loc="upper left")
        plt.axhline(y=0, color='k', linewidth=2)
        plt.axvline(x=0, color='k', linewidth=2)

        # Set the x and y axis limits similar to the figure
        plt.xlim(xlim[0], xlim[1])
        plt.ylim(ylim[0], ylim[1])

        plt.tight_layout()
        plt.subplots_adjust(top=0.92)

        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {filename}")
        else:
            plt.show()

    def _plot_no_contract_boundaries_all(self,sensitivity_type, filename=None):
            # Helper method for the comprehensive visualization

        if sensitivity_type == "price":
            self.boundary_results = self.boundary_results_price
        elif sensitivity_type == "production":
            self.boundary_results = self.boundary_results_production


        def _plot_boundary_on_axis(ax, result):
            """Plot a single boundary on a given axis (use contour if feas_mask available)."""
            scenario = result['scenario']
            if 'feas_mask' in result and 'KL_grid' in result and 'KG_grid' in result:
                KL_grid = np.array(result['KL_grid'])
                KG_grid = np.array(result['KG_grid'])
                feas_mask = np.array(result['feas_mask'])
                # Shading behind the curve: fill feasible region
                ax.contourf(KL_grid*100, KG_grid*100, feas_mask,
                            levels=[0.5, 1.1], colors=[scenario['color']], alpha=0.15, antialiased=True)
                # Boundary curve
                cs = ax.contour(KL_grid*100, KG_grid*100, feas_mask,
                                levels=[0.5], colors=[scenario['color']],
                                linestyles=[scenario['linestyle']], linewidths=[scenario['linewidth']])
                # Add a proxy handle for legend instead of accessing cs.collections
                ax.plot([], [], color=scenario['color'], linestyle=scenario['linestyle'],
                        linewidth=scenario['linewidth'], label=f"A_G={scenario['A_G']}, A_L={scenario['A_L']}")
            else:
                lowest_boundary = self._extract_lowest_boundary(result.get('boundary_points', []))
                if lowest_boundary is None or len(lowest_boundary) < 2:
                    print(f"Skipping scenario {scenario['label']} due to insufficient boundary points after filtering.")
                    return
                X = lowest_boundary[:, 0].reshape(-1, 1)
                y = lowest_boundary[:, 1]
                model = LinearRegression().fit(X, y)
                xlim = [-31, 31]
                n_space = np.linspace(xlim[0]/100, xlim[1]/100, 100)
                X_pred = n_space.reshape(-1, 1)
                boundary = model.predict(X_pred)
                sns.lineplot(x=n_space*100, y=boundary*100,
                             label=f"A_G={scenario['A_G']}, A_L={scenario['A_L']}",
                             linestyle=scenario['linestyle'], linewidth=scenario['linewidth'],
                             color=scenario['color'], ax=ax)



        """
        Create a visualization specifically showing how asymmetry in risk aversion
        affects the no-contract boundaries.
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

        # Filter scenarios by type
        sym_scenarios = [r for r in self.boundary_results
                        if abs(r['scenario']['A_G'] - r['scenario']['A_L']) < 1e-6]
        asym_scenarios = [r for r in self.boundary_results
                        if abs(r['scenario']['A_G'] - r['scenario']['A_L']) >= 1e-6]

        # Plot 1: All symmetrical cases
        for result in sym_scenarios:
            _plot_boundary_on_axis(ax1, result)
        ax1.set_title("Symmetrical Risk Aversion (A_G = A_L)", fontsize=self.titlesize)
        ax1.legend()

        # Plot 2: All asymmetrical cases
        for result in asym_scenarios:
            _plot_boundary_on_axis(ax2, result)
        ax2.set_title("Asymmetrical Risk Aversion (A_G ≠ A_L)", fontsize=self.titlesize)
        ax2.legend()

        # Plot 3: Fixed A_G, varying A_L
        fixed_ag_scenarios = [r for r in self.boundary_results if r['scenario']['A_G'] == 0.5]
        for result in fixed_ag_scenarios:
            _plot_boundary_on_axis(ax3, result)
        ax3.set_title("Fixed Generator Risk Aversion (A_G = 0.5)", fontsize=self.titlesize)
        ax3.legend()

        # Plot 4: Fixed A_L, varying A_G
        fixed_al_scenarios = [r for r in self.boundary_results if r['scenario']['A_L'] == 0.5]
        for result in fixed_al_scenarios:
            _plot_boundary_on_axis(ax4, result)
        ax4.set_title("Fixed Load Risk Aversion (A_L = 0.5)", fontsize=self.titlesize)
        ax4.legend()

        # Common formatting
        for ax in [ax1, ax2, ax3, ax4]:
            if sensitivity_type == "price":
                ax.set_xlabel('Load price bias KL (% of E[price])', fontsize=self.labelsize)
                ax.set_ylabel('Generator price bias KG (% of E[price])', fontsize=self.labelsize)
            elif sensitivity_type == "production":
                ax.set_xlabel('Load production bias KL (% of E[production])', fontsize=self.labelsize)
                ax.set_ylabel('Generator production bias KG (% of E[production])', fontsize=self.labelsize)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(-30, 30)
            ax.set_ylim(-30, 30)
            ax.axhline(y=0, color='k',linewidth=2)
            ax.axvline(x=0, color='k',linewidth=2)

        plt.tight_layout()
        plt.subplots_adjust(top=0.92)

        fig.suptitle(f'{self.cm_data.contract_type}-{sensitivity_type}: Contract Boundaries', fontsize=self.suptitlesize)

        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
        else:
            plt.show()

    def _extract_lowest_boundary(self,boundary_points):
                """
                Extract the lowest boundary line by selecting the minimum KG value for each KL.

                Parameters:
                -----------
                boundary_points : list of tuples
                    List of (KL, KG) points representing the boundary.

                Returns:
                --------
                lowest_boundary : ndarray
                    Array of (KL, KG) points representing the lowest boundary line.
                """
                boundary_points = np.array(boundary_points)
                # Round KL values slightly to avoid floating-point precision issues
                if len(boundary_points) < 2:
                    print(f"Skipping scenario due to insufficient boundary points.")
                    return
                boundary_points[:, 0] = np.round(boundary_points[:, 0], 6)


                # Create a dictionary to store the minimum KG for each KL
                kl_to_min_kg = {}

                for kl, kg in boundary_points:
                    if kl not in kl_to_min_kg or kg < kl_to_min_kg[kl]:
                        kl_to_min_kg[kl] = kg


                # Convert the dictionary back to an array
                lowest_boundary = np.array([[kl, kg] for kl, kg in kl_to_min_kg.items()])
                # Sort by KL for plotting
                lowest_boundary = lowest_boundary[np.argsort(lowest_boundary[:, 0])]

                # tst

                    # Group by KG values
                kg_values = lowest_boundary[:, 1]
                unique_kg = np.unique(kg_values)

                filtered_rows = []

                # For each unique KG value
                for kg in unique_kg:
                    # Get all rows with this KG value
                    mask = kg_values == kg
                    matching_rows = lowest_boundary[mask]

                    if len(matching_rows) > 1:
                        # Multiple rows with the same KG value, keep the one with highest KL
                        best_row_idx = np.argmin(matching_rows[:, 0])
                        filtered_rows.append(matching_rows[best_row_idx])
                    else:
                        # Only one row with this KG value
                        filtered_rows.append(matching_rows[0])
                filtered_boundary = np.array(filtered_rows)

                return filtered_boundary
