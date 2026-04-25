"""Earnings and distribution plotting methods."""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from utils import calculate_cvar_left, weighted_expected_value
from .base import cmap_red_green


class EarningsPlotsMixin:
    """Mixin providing earnings and distribution plotting methods."""

    def _plot_earnings_histograms(self, fixed_A_G, A_L_to_plot, filename=None):
        """
        Plots histograms of G and L net earnings for different risk aversion levels.
        """

        earnings_df =  self.earnings_risk_sensitivity_df
        filtered_results = earnings_df[
        (earnings_df['A_G'] == fixed_A_G) &
        (earnings_df['A_L'].isin(A_L_to_plot)) &
        (~earnings_df['Revenue_G'].isna()) &
        (~earnings_df['Revenue_L'].isna())
    ]

        if filtered_results.empty:
            print("No valid results to plot.")
            return

        all_G_values = np.concatenate([filtered_results['Revenue_G'].values,self.cm_data.net_earnings_no_contract_true_G.values])
        all_L_values = np.concatenate([filtered_results['Revenue_L'].values,self.cm_data.net_earnings_no_contract_true_L.values])


        # Create uniform bins based on global min and max
        bins = 20
        min_val_G = min(all_G_values)
        max_val_G = max(all_G_values)
        bin_edges_G = np.linspace(min_val_G, max_val_G, bins + 1)

        min_val_L = min(all_L_values)
        max_val_L = max(all_L_values)
        bin_edges_L = np.linspace(min_val_L, max_val_L, bins + 1)


        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        # Plot G Revenue Histogram
        ax_G = axes[0]
        ax_L = axes[1]

        # Get color cycle before the loops
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']

        # Plot G Revenue Histogram
        for idx, a_L in enumerate(A_L_to_plot):
            G_values = filtered_results[filtered_results['A_L'] == a_L]['Revenue_G'].values

            if G_values.size == 0:
                print(f"No G values for A_L={a_L}, skipping...")
                continue

            # Expected G Revenue
            G_6_expected = G_values.mean()
            # Calculate CVaR values
            cvar_G = calculate_cvar_left(G_values,self.cm_data.PROB, self.cm_data.alpha)
            utility_G = (1-fixed_A_G)*G_6_expected + fixed_A_G*cvar_G

            if len(G_values) > 0:
                current_color = colors[idx % len(colors)]  # Cycle through colors
                print(f"\nPlotting histogram for A_L={a_L}")
                print(f"Values range: {G_values.min() } to {G_values.max() }")
                ax_G.hist(
                    G_values ,
                    bins=bin_edges_G,
                    alpha=0.6,
                    label=f'A_L={a_L}',
                    color=current_color,
                    density=False
                )
                ax_G.axvline(G_6_expected, linestyle="--", color=current_color,
                              label=f"A_L={a_L} - Expected: {G_6_expected:.2f}")

            # Plot L Revenue Histogram with same color
            L_values = filtered_results[filtered_results['A_L'] == a_L]['Revenue_L'].values

            # Expected L Revenue
            L_expected = L_values.mean()
            # Calculate CVaR values

            cvar_L = calculate_cvar_left(L_values,self.cm_data.PROB, self.cm_data.alpha)
            utility_L = (1-a_L)*L_expected + a_L*cvar_L
            if len(L_values) > 0:
                ax_L.hist(
                    L_values ,
                    bins=bin_edges_L,
                    alpha=0.6,
                    label=f'A_L={a_L}',
                    color=current_color,
                    density=False
                )
                ax_L.axvline(L_expected, linestyle="--", color=current_color,
                              label=f"A_L={a_L} - Expected   : {L_expected:.2f}")

        ax_G.hist(self.cm_data.net_earnings_no_contract_true_G ,bins=bin_edges_G,alpha=0.4,label=f'No Contract',density=False,color ='black')
        ax_G.axvline(self.cm_data.net_earnings_no_contract_true_G.mean() , linestyle="--",color ='black', label=f"No Contract - Expected : {self.cm_data.net_earnings_no_contract_true_G.mean() :.2f}")
        ax_G.set_title(f'Generator (G) Revenue Distribution', fontsize=self.titlesize)
        ax_G.set_xlabel('Generator Revenue (Mio EUR)', fontsize=self.labelsize)
        ax_G.set_ylabel('Frequency', fontsize=self.labelsize)
        # Modify legend to have two columns with specific ordering
        handles, labels = ax_G.get_legend_handles_labels()
        hist_handles = handles[::2]  # Get histogram handles
        line_handles = handles[1::2]  # Get vertical line handles
        hist_labels = labels[::2]    # Get histogram labels
        line_labels = labels[1::2]   # Get vertical line labels
        ax_G.legend(hist_handles + line_handles, hist_labels + line_labels,
                    ncol=2, loc='upper right',
                    fontsize=10, bbox_to_anchor=(0.98, 0.98),
                    bbox_transform=ax_G.transAxes,
                    framealpha=0.8)
        ax_G.grid(True, axis='y', linestyle='--', alpha=0.7)

        ax_L.hist(self.cm_data.net_earnings_no_contract_true_L,bins=bin_edges_L,alpha=0.4,label=f'No Contract',density=False, color ='black')
        ax_L.axvline(self.cm_data.net_earnings_no_contract_true_L.mean() , linestyle="--",color ='black', label=f"No Contract - Average Earnings: {self.cm_data.net_earnings_no_contract_true_L.mean() :.2f}")
        ax_L.set_title(f'Load (L) Revenue Distribution', fontsize=self.titlesize)
        ax_L.set_xlabel('Load Revenue (Mio EUR)', fontsize=self.labelsize)
        ax_L.set_ylabel('Frequency', fontsize=self.labelsize)
        # Apply same legend formatting to L plot
        handles, labels = ax_L.get_legend_handles_labels()
        hist_handles = handles[::2]
        line_handles = handles[1::2]
        hist_labels = labels[::2]
        line_labels = labels[1::2]
        ax_L.legend(hist_handles + line_handles, hist_labels + line_labels,
                    ncol=2, loc='upper right',
                    fontsize=self.legendsize, bbox_to_anchor=(0.98, 0.98),
                    bbox_transform=ax_L.transAxes,
                    framealpha=0.8)
        ax_L.grid(True, axis='y', linestyle='--', alpha=0.7)

        #Add suptitle
        fig.suptitle(f'{self.cm_data.contract_type}: Expected Revenue ($A_G$ = {fixed_A_G})', fontsize=self.suptitlesize)

        plt.tight_layout()
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_earnings_histograms_alpha(self, filename=None):
            """
            Simplified: Plot earnings histograms for all unique alpha values in self.alpha_earnings_df.
            """
            df = self.alpha_earnings_df
            if df is None or df.empty:
                print("No alpha earnings results to plot.")
                return

            # Only keep rows with valid earnings
            df = df.dropna(subset=['Revenue_G', 'Revenue_L', 'alpha'])

            unique_alphas = sorted(df['alpha'].unique())
            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

            fig, (ax_g, ax_l) = plt.subplots(1, 2, figsize=(12, 6))

            # Collect all values for binning
            all_g = np.concatenate([df['Revenue_G'].values, self.cm_data.net_earnings_no_contract_true_G])
            all_l = np.concatenate([df['Revenue_L'].values, self.cm_data.net_earnings_no_contract_true_L])
            bins_g = np.linspace(all_g.min(), all_g.max(), 20)
            bins_l = np.linspace(all_l.min(), all_l.max(), 20)

            for idx, alpha in enumerate(unique_alphas):
                color = colors[idx % len(colors)]
                g_vals = df[df['alpha'] == alpha]['Revenue_G'].values
                l_vals = df[df['alpha'] == alpha]['Revenue_L'].values

                if len(g_vals) > 0:
                    ax_g.hist(g_vals, bins=bins_g, alpha=0.6, label=f'α={alpha}', color=color)
                    ax_g.axvline(g_vals.mean(), color=color, linestyle='--')
                if len(l_vals) > 0:
                    ax_l.hist(l_vals, bins=bins_l, alpha=0.6, label=f'α={alpha}', color=color)
                    ax_l.axvline(l_vals.mean(), color=color, linestyle='--')

            # No contract reference
            ax_g.hist(self.cm_data.net_earnings_no_contract_true_G, bins=bins_g, alpha=0.3, color='black', label='No Contract')
            ax_g.axvline(self.cm_data.net_earnings_no_contract_true_G.mean(), color='black', linestyle='--')
            ax_l.hist(self.cm_data.net_earnings_no_contract_true_L, bins=bins_l, alpha=0.3, color='black', label='No Contract')
            ax_l.axvline(self.cm_data.net_earnings_no_contract_true_L.mean(), color='black', linestyle='--')

            ax_g.set_title('Generator Revenue Distribution', fontsize=self.titlesize)
            ax_g.set_xlabel('Revenue (Mio EUR)', fontsize=self.labelsize)
            ax_g.set_ylabel('Frequency', fontsize=self.labelsize)
            ax_g.legend()
            ax_g.grid(True, axis='y', linestyle='--', alpha=0.7)

            ax_l.set_title('Load Revenue Distribution', fontsize=self.titlesize)
            ax_l.set_xlabel('Revenue (Mio EUR)', fontsize=self.labelsize)
            ax_l.set_ylabel('Frequency', fontsize=self.labelsize)
            ax_l.legend()
            ax_l.grid(True, axis='y', linestyle='--', alpha=0.7)

            fig.suptitle(f"{self.cm_data.contract_type}: Earnings Distribution by Alpha, $A_G$ = {self.cm_data.A_G}, $A_L$ = {self.cm_data.A_L}", fontsize=self.suptitlesize)
            plt.tight_layout()

            if filename:
                plt.savefig(os.path.join(self.plots_dir, filename), bbox_inches='tight', dpi=300)
                print(f"Plot saved to {filename}")
                plt.close(fig)
            else:
                plt.show()

    def _plot_expected_versus_threatpoint(self,fixed_A_G, A_L_to_plot, filename=None):

        """
        Plots histograms of G and L net earnings for different risk aversion levels.
        """
        earnings_risk_sensitivity_df = self.earnings_risk_sensitivity_df

        filtered_results = pd.concat([
            df[(df['A_G'] == fixed_A_G) & (df['A_L'].isin(A_L_to_plot)) &
               (~df['Revenue_G'].isna()) & (~df['Revenue_L'].isna())]
            for df in earnings_risk_sensitivity_df
            if isinstance(df, pd.DataFrame) and not df.empty
        ], ignore_index=True)

        if filtered_results.empty:
            print("No valid results to plot.")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        # Plot G Revenue Histogram
        ax_G = axes[0]
        ax_L = axes[1]

        # Get color cycle before the loops
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']

        zeta_L_values = []


        # Calculate CVaR values (constant for all risk aversion values)
        cvar_G_no_contract = calculate_cvar_left(self.cm_data.net_earnings_no_contract_G,self.cm_data.PROB, self.cm_data.alpha)
        cvar_L_no_contract = calculate_cvar_left(self.cm_data.net_earnings_no_contract_L,self.cm_data.PROB, self.cm_data.alpha)
        mean_G_contract = self.cm_data.net_earnings_no_contract_G.mean()
        mean_L_no_contract = self.cm_data.net_earnings_no_contract_L.mean()

        # Calculate threat points for different risk aversion values
        for A in A_L_to_plot:
            zeta_L = (1-A)*mean_L_no_contract + A*cvar_L_no_contract
            zeta_L_values.append(zeta_L)
        zeta_G = ((1-fixed_A_G)*mean_G_contract + fixed_A_G*cvar_G_no_contract)
        # Plot G Revenue Histogram
        for idx, a_L in enumerate(A_L_to_plot):
            G_values = filtered_results[filtered_results['A_L'] == a_L]['Revenue_G'].values
            current_color = colors[idx % len(colors)]  # Cycle through colors

            if len(G_values) > 0:
                expected_G = G_values.mean()
                cvar_G = calculate_cvar_left(G_values,self.cm_data.PROB, self.cm_data.alpha)
                utility_G = (1-fixed_A_G)*expected_G + fixed_A_G*cvar_G
                ax_G.axvline(utility_G/1e5, linestyle="-", color=current_color,
                              label=f"A_L={a_L} - Utility: {utility_G/1e5:.2f}")
            # Plot L Revenue Histogram with same color
            L_values = filtered_results[filtered_results['A_L'] == a_L]['Revenue_L'].values
            if len(L_values) > 0:
                expected_L = L_values.mean()
                cvar_L = calculate_cvar_left(L_values,self.cm_data.PROB, self.cm_data.alpha)
                utility_L = (1-a_L)*expected_L + a_L*cvar_L
                ax_L.axvline(utility_L/1e5, linestyle="-", color=current_color,
                              label=f"A_L={a_L} - Utility: {utility_L/1e5:.2f}")
                ax_L.axvline(zeta_L_values[idx]/1e5, linestyle="--", color=current_color, label=f"A_L={a_L:.2f} - Threat= {zeta_L_values[idx]/1e5:.2f} ")


        #G Subplot configuration
        ax_G.axvline(zeta_G/1e5, linestyle="--", color='black', label=f"Threat Point: {zeta_G/1e5:.2f}")
        ax_G.set_title(f'Generator (G) Threatpoint\n(A_G = {fixed_A_G}) vs. L Risk Aversion', fontsize=self.titlesize)
        ax_G.set_xlabel('Generator Revenue ($ x 10^5)', fontsize=self.labelsize)
        # Modify legend to have two columns with specific ordering
        handles, labels = ax_G.get_legend_handles_labels()
        hist_handles = handles[::2]  # Get histogram handles
        line_handles = handles[1::2]  # Get vertical line handles
        hist_labels = labels[::2]    # Get histogram labels
        line_labels = labels[1::2]   # Get vertical line labels
        ax_G.legend(hist_handles + line_handles, hist_labels + line_labels,
                    ncol=2, loc='upper right',
                    fontsize=10, bbox_to_anchor=(0.98, 0.98),
                    bbox_transform=ax_G.transAxes,
                    framealpha=0.8)
        ax_G.grid(True, axis='y', linestyle='--', alpha=0.7)

        #ax_L.axvline(self.cm_data.net_earnings_no_contract_L_df.sum().mean() / 1e5, linestyle="--",color ='black', label=f"No Contract - Average Earnings: {self.cm_data.net_earnings_no_contract_L_df.sum().mean() / 1e5:.2f}")
        #L Subplot configuration
        ax_L.set_title(f'Load (L) Threatpoints vs \n(A_G = {fixed_A_G})', fontsize=self.titlesize)
        ax_L.set_xlabel('Load Revenue ($ x 10^5)', fontsize=self.labelsize)
        # Apply same legend formatting to L plot
        handles, labels = ax_L.get_legend_handles_labels()
        hist_handles = handles[::2]
        line_handles = handles[1::2]
        hist_labels = labels[::2]
        line_labels = labels[1::2]
        ax_L.legend(hist_handles + line_handles, hist_labels + line_labels,
                    ncol=2, loc='upper right',
                    fontsize=10, bbox_to_anchor=(0.98, 0.98),
                    bbox_transform=ax_L.transAxes,
                    framealpha=0.8)
        ax_L.grid(True, axis='y', linestyle='--', alpha=0.7)

        plt.tight_layout()
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()
        print(f"Plot saved t bla bla")

    def _risk_plot_earnings_boxplot(self, fixed_A_G, A_L_to_plot, filename=None):



        """
        Plots boxplots of earnings for different risk aversion levels.

        Parameters:
        -----------
        fixed_A_G : float
            Fixed risk aversion level for the generator.
        A_L_to_plot : list
            List of risk aversion levels for the load to plot.
        filename : str, optional
            Path to save the plot. If None, the plot will be displayed.
        """

        earnings_df = self.earnings_risk_sensitivity_df
        filtered_results = earnings_df[
            (earnings_df['A_G'] == fixed_A_G) &
            (earnings_df['A_L'].isin(A_L_to_plot))
        ]

       # Prepare the no-contract data
        no_contract_g = self.cm_data.net_earnings_no_contract_true_G
        no_contract_l = self.cm_data.net_earnings_no_contract_true_L
        no_contract_df = pd.DataFrame({
            'Revenue_G': no_contract_g,
            'Revenue_L': no_contract_l,
            'A_L': 'No \n Contract'  # Assign a string label for the category
        })

        #Prepare Capture Price Data
        CP_df = pd.DataFrame({
            'Revenue_G': self.CP_earnings_df["Revenue_G_CP"],
            'Revenue_L': self.CP_earnings_df["Revenue_L_CP"],
            'A_L': 'Capture \n Price'  # Assign a string label for the category
        })


        # Combine the contract and no-contract data
        # Convert A_L to object type to allow mixing numbers and strings
        filtered_results['A_L'] = filtered_results['A_L'].astype(str)
        filtered_results = filtered_results.dropna()
        #plot_data = pd.concat([no_contract_df,CP_df,filtered_results], ignore_index=True)
        plot_data = pd.concat([no_contract_df,filtered_results], ignore_index=True)


        # Define the order for the x-axis categories
        A_L_to_plot = filtered_results['A_L'].unique()

        A_L_to_plot = sorted(A_L_to_plot)
        A_L_to_plot.insert(0, 'No Contract')  # Add 'No Contract' at the beginning
        plot_order = A_L_to_plot
        contract_mask = plot_data['A_L'] != 'No Contract'

        # Create figure with more space at the bottom for the table
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        ax_G = axes[0]
        ax_L = axes[1]

        # 1. Add violin plots behind boxplots for Generator Revenue
        sns.violinplot(
            data=plot_data,
            x='A_L',
            y='Revenue_G',
            order=plot_order,
            ax=ax_G,
            hue="A_L",
            hue_order=plot_order,
            legend=False,
            alpha=0.3,
            width=0.8,
            inner=None,
            palette="Set2"
        )

        # 2. Add boxplots on top for Generator Revenue
        box_G = sns.boxplot(
            data=plot_data,
            x='A_L',
            y='Revenue_G',
            order=plot_order,
            ax=ax_G,
            hue="A_L",
            hue_order=plot_order,
            legend=False,
            width=0.5,
            showfliers=True,
            palette="Set2"
        )
        ### add capture price
        """
        sns.violinplot(
            data=plot_data,
            x='A_L',
            y='CP_G_Revenue',
            order=plot_order,
            ax=ax_G,
            legend=False,
            alpha=0.3,
            width=0.8,
            inner=None,
            color= capture_color,
        )

        # 2. Add boxplots on top for Generator Revenue
        box_G = sns.boxplot(
            data=plot_data,
            x='A_L',
            y='CP_G_Revenue',
            order=plot_order,
            ax=ax_G,
            legend=False,
            width=0.3,
            showfliers=True,
            color = capture_color,
        )
        """



        #########

        # 3. Add violin plots behind boxplots for Load Revenue
        sns.violinplot(
            data=plot_data,
            x='A_L',
            y='Revenue_L',
            order=plot_order,
            ax=ax_L,
            hue = 'A_L',
            hue_order=plot_order,
            legend=False,
            alpha=0.3,
            width=0.5,
            cut=0,
            inner=None,
            palette="Set2"
        )

        # 4. Add boxplots on top for Load Revenue
        box_L = sns.boxplot(
            data=plot_data,
            x='A_L',
            y='Revenue_L',
            order=plot_order,
            ax=ax_L,
            hue= 'A_L',
            hue_order=plot_order,
            legend=False,
            width=0.3,
            showfliers=True,
            palette="Set2"
        )

        # Add Capture Price
        """
        sns.violinplot(
            data=plot_data[contract_mask],
            x='A_L',
            y='CP_L_Revenue',
            order=plot_order,
            ax=ax_L,
            legend=False,
            alpha=0.3,
            width=0.6,
            cut=0,
            inner=None,
            color = capture_color,
        )

        # 2. Add boxplots on top for Generator Revenue
        box_L_CP = sns.boxplot(
            data=plot_data[contract_mask],
            x='A_L',
            y='CP_L_Revenue',
            order=plot_order,
            ax=ax_L,
            legend=False,
            width=0.3,
            showfliers=True,
            color = capture_color,
        )
        """

        """
        # 6. Calculate and display percentage changes between risk aversion levels
        if len(A_L_to_plot) > 1:
            g_means = [filtered_results[filtered_results['A_L'] == a_l]['Revenue_G'].mean() for a_l in A_L_to_plot]
            l_means = [filtered_results[filtered_results['A_L'] == a_l]['Revenue_L'].mean() for a_l in A_L_to_plot]

            for i in range(len(A_L_to_plot) - 1):
                # Generator percentage change
                pct_change_g = ((g_means[i+1] - g_means[i]) / g_means[i]) * 100
                ax_G.annotate(f'Average Earnings Increase{pct_change_g:.1f}%',
                            xy=(i + 0.5, (g_means[i] + g_means[i+1])/2),
                            xytext=(0, 0),
                            textcoords='offset points',
                            ha='center',
                            va='center',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

                # Load percentage change
                pct_change_l = ((l_means[i+1] - l_means[i]) / l_means[i]) * 100
                ax_L.annotate(f'Average Earnings Decrease {-pct_change_l:.1f}%',
                            xy=(i + 0.5, (l_means[i] + l_means[i+1])/2),
                            xytext=(0, 0),
                            textcoords='offset points',
                            ha='center',
                            va='center',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
        """

        # Add threatpoint lins
        # Add Expectation of no contract earnings
        #ax_G.axhline(self.cm_data.net_earnings_no_contract_true_G.mean(), linestyle="--", color='grey', label=f"No Contract - Average Earnings: {self.cm_data.net_earnings_no_contract_true_G.mean() :.2f} ")
        #ax_L.axhline(self.cm_data.net_earnings_no_contract_true_L.mean(), linestyle="--", color='grey', label=f"No Contract - Average Earnings: {self.cm_data.net_earnings_no_contract_true_L.mean() :.2f} ")

        # Set titles and labels
        ax_G.set_title(f'Seller Revenue',fontsize=self.titlesize)
        ax_G.tick_params(axis='both', labelsize= self.legendsize)
        ax_G.set_xlabel('Risk Aversion $(A_B)$',fontsize=self.labelsize)
        ax_G.set_ylabel('Seller Revenue (Mio EUR)',fontsize=self.labelsize)
        ax_G.grid(True, linestyle='--', alpha=0.9, axis='y')

        ax_L.set_title(f'Buyer Revenue',fontsize=self.titlesize)
        ax_L.set_xlabel('Risk Aversion $(A_B)$', fontsize=self.labelsize)
        ax_L.set_ylabel('Buyer Revenue (Mio EUR)',fontsize=self.labelsize)
        ax_L.tick_params(axis='both', labelsize= self.legendsize)
        ax_L.grid(True, linestyle='--', alpha=0.9, axis='y')

        plt.suptitle(f"{self.cm_data.contract_type}: Earnings Distribution by Risk Aversion, $A_S$ = {fixed_A_G}", fontsize=self.suptitlesize)

        plt.tight_layout()

        # Save or show the figure
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _nego_plot_earnings_boxplot(self, filename=None):

        """
        Plots boxplots of earnings for different negotiation levels.

        Parameters:
        -----------
            filename : str, optional
            Path to save the plot. If None, the plot will be displayed.
        """
        earnings_df = self.negotiation_earnings_df
        earnings_df["tau_G"] = earnings_df["tau_G"].round(2)  # Round to 2 decimal places for better readability
        earnings_df["tau_L"] = earnings_df["tau_L"].round(2)  # Round to 2 decimal places for better readability
        unique_tau_g = earnings_df["tau_G"].unique()

        # Get three evenly spaced positions
       # positions = np.linspace(0, len(unique_tau_g)-1, 7, dtype=int)
        #selected_tau_g = np.round(unique_tau_g[positions], 2)

        # Filter the DataFrame for these tau_G values
        selected_tau_g = unique_tau_g,   # Round to 2 decimal places for better readability
        #df_filtered = earnings_df[earnings_df["tau_G"].isin(selected_tau_g)]
        df_filtered = earnings_df
        AL_used = df_filtered['A_L'].unique()[0]  # Assuming A_L is constant for the filtered data
        AG_used = df_filtered['A_G'].unique()[0]  # Assuming A_G is constant for the filtered data


       # Prepare the no-contract data
        no_contract_g = self.cm_data.net_earnings_no_contract_true_G
        no_contract_l = self.cm_data.net_earnings_no_contract_true_L
        no_contract_df = pd.DataFrame({
            'Revenue_G': no_contract_g,
            'Revenue_L': no_contract_l,
            'tau_G': 'No Contract'  # Assign a string label for the category
        })

        CP_df = pd.DataFrame({
            'Revenue_G': self.CP_earnings_df["Revenue_G_CP"],
            'Revenue_L': self.CP_earnings_df["Revenue_L_CP"],
            'tau_G': 'Capture \n Price'  # Assign a string label for the category
        })

        # Combine the contract and no-contract data
        # Convert A_L to object type to allow mixing numbers and strings
        df_filtered= df_filtered.astype(object)
        plot_data = pd.concat([no_contract_df,CP_df,df_filtered], ignore_index=True)

        # Define the order for the x-axis categories
        nego_to_plot = sorted(selected_tau_g)
        nego_to_plot.insert(0, 'No Contract')  # Add 'No Contract' at the beginning
        plot_order = nego_to_plot


        # Create figure with more space at the bottom for the table
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        ax_G = axes[0]
        ax_L = axes[1]

        # 1. Add violin plots behind boxplots for Generator Revenue
        sns.violinplot(
            data=plot_data,
            x='tau_G',
            y='Revenue_G',
            order=plot_order,
            ax=ax_G,
            hue="tau_G",
            hue_order=plot_order,
            legend=False,
            alpha=0.3,
            cut=0,
            inner=None,
            palette="Set2"
        )

        # 2. Add boxplots on top for Generator Revenue
        box_G = sns.boxplot(
            data=plot_data,
            x='tau_G',
            y='Revenue_G',
            order=plot_order,
            ax=ax_G,
            hue="tau_G",
            hue_order=plot_order,
            legend=False,
            width=0.5,
            showfliers=True,
            palette="Set2"
        )

        # 3. Add violin plots behind boxplots for Load Revenue
        sns.violinplot(
            data=plot_data,
            x='tau_G',
            y='Revenue_L',
            order=plot_order,
            ax=ax_L,
            hue = 'tau_G',
            hue_order=plot_order,
            legend=False,
            alpha=0.3,
            cut=0,
            inner=None,
            palette="Set2"
        )

        # 4. Add boxplots on top for Load Revenue
        box_L = sns.boxplot(
            data=plot_data,
            x='tau_G',
            y='Revenue_L',
            order=plot_order,
            ax=ax_L,
            hue= 'tau_G',
            hue_order=plot_order,
            legend=False,
            width=0.5,
            showfliers=True,
            palette="Set2"
        )

        """
        # 6. Calculate and display percentage changes between risk aversion levels
        if len(A_L_to_plot) > 1:
            g_means = [filtered_results[filtered_results['A_L'] == a_l]['Revenue_G'].mean() for a_l in A_L_to_plot]
            l_means = [filtered_results[filtered_results['A_L'] == a_l]['Revenue_L'].mean() for a_l in A_L_to_plot]

            for i in range(len(A_L_to_plot) - 1):
                # Generator percentage change
                pct_change_g = ((g_means[i+1] - g_means[i]) / g_means[i]) * 100
                ax_G.annotate(f'Average Earnings Increase{pct_change_g:.1f}%',
                            xy=(i + 0.5, (g_means[i] + g_means[i+1])/2),
                            xytext=(0, 0),
                            textcoords='offset points',
                            ha='center',
                            va='center',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

                # Load percentage change
                pct_change_l = ((l_means[i+1] - l_means[i]) / l_means[i]) * 100
                ax_L.annotate(f'Average Earnings Decrease {-pct_change_l:.1f}%',
                            xy=(i + 0.5, (l_means[i] + l_means[i+1])/2),
                            xytext=(0, 0),
                            textcoords='offset points',
                            ha='center',
                            va='center',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
        """
        # Set titles and labels
        ax_G.set_title(f'Generator Revenue',fontsize=self.titlesize)
        ax_G.set_xlabel('Negotiation Power $(\\tau_G)$',fontsize=self.labelsize)
        ax_G.set_ylabel('Generator Revenue (Mio EUR)',fontsize=self.labelsize)
        ax_G.tick_params(axis='both', labelsize= self.legendsize-1)
        ax_G.grid(True, linestyle='--', alpha=0.7, axis='y')

        ax_L.set_title(f'Load Revenue',fontsize=self.titlesize)
        ax_L.set_xlabel('Negotiation Power $(\\tau_L)$', fontsize=self.labelsize)
        ax_L.set_ylabel('Load Revenue (Mio EUR)',fontsize=self.labelsize)
        ax_L.tick_params(axis='both', labelsize= self.legendsize-1)
        ax_L.grid(True, linestyle='--', alpha=0.7, axis='y')

        plt.suptitle(f"{self.cm_data.contract_type}: Earnings Distribution by Negotiation Power with Risk Aversion $A_G$={AG_used}, $A_L$={AL_used}", fontsize=self.suptitlesize)

        plt.tight_layout()

        # Save or show the figure
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_nash_product_evolution(self, filename=None):
        """
        Plot how Nash Product changes across different sensitivity analyses.
        This is crucial for understanding the efficiency of negotiation outcomes.
        """
        fig, ax = plt.subplots(figsize=(7, 5))

        # 1. Risk Aversion Impact on Nash Product
        risk_df = self.risk_sensitivity_df.copy()
        #risk_df['Nash_Product'] = risk_df['Nash_Product']**2 # Since it is using the 0.5 utlity function from gurobi, manually would give the same results.

        # Create pivot table for heatmap
        pivot = risk_df.pivot_table(
            index='A_L',
            columns='A_G',
            values='Nash_Product',
            aggfunc='mean'
        )

        pivot = pivot.sort_index(ascending=False)

        sns.heatmap(
            pivot,
            ax=ax,
            cmap='RdYlGn',
            center=pivot.mean().mean(),
            annot=True,
            fmt='.1f',
            cbar_kws={'label': 'Nash Product'}
        )
        ax.set_title('Nash Product: Risk Aversion Impact', fontsize=self.titlesize)
        ax.set_xlabel('Generator Risk Aversion ($A_G$)', fontsize=self.labelsize)
        ax.set_ylabel('Load Risk Aversion ($A_L$)', fontsize=self.labelsize)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Nash Product evolution plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_disagreement_points(self,filename=None):

        """
        Plot the disagreement points for different risk aversion levels.
        This is crucial for understanding the negotiation dynamics and potential outcomes.
        """
        fig, ax = plt.subplots(figsize=(8, 6))

        A_values = np.linspace(0, 1, 100)
        d_G_vals = np.zeros(len(A_values))
        d_L_vals = np.zeros(len(A_values))

        for i, A in enumerate(A_values):
            d_G_vals[i] = ((1 - A) * (self.cm_data.PROB * self.cm_data.net_earnings_no_contract_priceG_G).sum() +
                        A * self.cm_data.CVaR_no_contract_priceG_G)
            d_L_vals[i] = ((1 - A) * (self.cm_data.PROB * self.cm_data.net_earnings_no_contract_priceL_L).sum() +
                        A * self.cm_data.CVaR_no_contract_priceL_L)
        ax2 = ax.twinx()  # Create a second y-axis for Load disagreement points

        # Plot disagreement points
        line2, = ax2.plot(A_values, d_L_vals, label='Load Disagreement Point', color='orange', linewidth=2,  marker='o', markevery=10)
        line1, = ax.plot(A_values, d_G_vals, label='Generator Disagreement Point', color='blue',  marker='o', markevery=5)


        # Add labels and title
        ax.set_xlabel('Risk Aversion', fontsize=self.labelsize)
        ax.set_ylabel('Generator Disagreement Point ($d_G$)', fontsize=self.labelsize)
        ax2.set_ylabel('Load Disagreement Point ($d_L$)', fontsize=self.labelsize)
        ax.set_title(f'{self.cm_data.contract_type}: Disagreement Points', fontsize=self.titlesize)

        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)

        # Combine legends from both axes
        lines = [line1, line2]
        labels = [line.get_label() for line in lines]
        ax.legend(lines, labels, loc='upper right', fontsize=self.legendsize)


        plt.tight_layout()
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Disagreement points plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()
