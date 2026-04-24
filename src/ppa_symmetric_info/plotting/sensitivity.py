"""Sensitivity analysis plotting methods."""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from matplotlib.colors import to_rgb
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
from .base import cmap_red_green


class SensitivityPlotsMixin:
    """Mixin providing sensitivity analysis plotting methods."""

    def _plot_negotiation_vs_risk(self, metric='StrikePrice', filename=None):
        """
        Plot metric vs tau_L for multiple (A_G, A_L) pairs.

        - Color encodes the (A_G, A_L) pair using a palette.
        - Lines are drawn across tau_L; optional secondary axis for Gamma if PAP and metric is ContractAmount.
        """

        df = self.negotiation_vs_risk_df
        if df is None or df.empty:
            print("No data provided for negotiation vs risk plot.")
            return

        # Prepare data
        plot_df = df.copy()
        if 'tau_L' not in plot_df.columns:
            print("Dataframe missing tau_L; cannot plot.")
            return
        # Round contract amount to 4 decimals for readability
        if 'ContractAmount' in plot_df.columns:
            try:
                plot_df['ContractAmount'] = plot_df['ContractAmount'].astype(float).round(4)
            except Exception:
                pass

        # Unique pairs and grouped color mapping: similar colors per A_G, distinct per A_L
        pairs = plot_df[['A_G', 'A_L']].drop_duplicates().sort_values(['A_G', 'A_L']).values.tolist()
        unique_al = sorted(plot_df['A_L'].unique())
        color_map = {}
        base_palette = sns.color_palette('Set2', n_colors=max(3, len(unique_al)))
        for idx_ag, al in enumerate(unique_al):
            base = base_palette[idx_ag % len(base_palette)]
            ags = sorted(plot_df.loc[plot_df['A_L'] == al, 'A_G'].unique())
            # Generate base-to-darker shades so higher A_L lines are not too light
            base_rgb = to_rgb(base)
            dark_rgb = tuple(max(0.0, c * 0.55) for c in base_rgb)  # darker companion
            shades = sns.blend_palette([base_rgb, dark_rgb], n_colors=max(3, len(ags)))
            for j, ag in enumerate(ags):
                color_map[(ag, al)] = shades[j]

        # Sort by tau_L for nice lines
        plot_df = plot_df.sort_values('tau_L')

        is_pap = self.cm_data.contract_type == "PAP"
        has_gamma = 'Gamma' in plot_df.columns

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        metrics = ['StrikePrice', 'ContractAmount']
        titles = ['Strike Price', 'Contract Amount']

        for ax, m, title in zip(axes, metrics, titles):
            for pair in pairs:
                a_g, a_l = pair
                sub = plot_df[(plot_df['A_G'] == a_g) & (plot_df['A_L'] == a_l)]
                if sub.empty:
                    continue
                # Emphasize the symmetric mid-risk case (A_G = A_L = 0.5)
                is_mid = np.isclose(a_g, 0.5) and np.isclose(a_l, 0.5)
                lw = 3.0 if is_mid else 2.0
                ms = 8 if is_mid else 6
                z = 4 if is_mid else 2
                edge_color = 'black' if is_mid else 'none'
                marker = 'o' if is_mid else 'none'
                ax.plot(sub['tau_L'], sub[m], linewidth=lw, markersize=ms,
                        color=color_map[(a_g, a_l)], label=f"A_G={a_g}, A_L={a_l}", marker=marker, zorder=z, markeredgecolor=edge_color)

            # Reference lines
            if m == 'StrikePrice':
                ref = (self.cm_data.Capture_price_G_avg if is_pap else self.cm_data.expected_price) * 1e3
                ax.axhline(ref, color='black', linestyle='--', label='Reference price')
                ax.set_ylabel("Price (EUR/MWh)", fontsize=self.labelsize)
            elif m == 'ContractAmount' and not is_pap:
                ref = self.cm_data.expected_production / 8760 * 1000
                ax.axhline(ref, color='black', linestyle='--', label='Expected production (MWh)')
                ax.set_ylabel("Contract Amount (MWh)", fontsize=self.labelsize)

            # Secondary axis for Gamma in PAP on ContractAmount
            if m == 'ContractAmount' and is_pap and has_gamma:
                ax.set_ylabel("Contract Amount (MW)", fontsize=self.labelsize)
                ax2 = ax.twinx()
                for pair in pairs:
                    a_g, a_l = pair
                    sub = plot_df[(plot_df['A_G'] == a_g) & (plot_df['A_L'] == a_l)]
                    if sub.empty or 'Gamma' not in sub.columns:
                        continue
                    is_mid = np.isclose(a_g, 0.5) and np.isclose(a_l, 0.5)
                    lw = 2.0 if is_mid else 1.0
                    z = 4 if is_mid else 2
                    edge_color = 'black' if is_mid else 'none'
                    marker = 'o' if is_mid else 'none'
                    ax2.plot(sub['tau_L'], sub['Gamma'] * 100, linestyle='--', linewidth=lw,
                             color=color_map[(a_g, a_l)], alpha=0.6, zorder=z, markeredgecolor=edge_color, marker=marker)
                ax2.set_ylabel('$\\gamma$ share of production capacity', color='gray', fontsize=self.labelsize-2)
                ax2.tick_params(axis='y', labelcolor='gray')


            ax.set_xlabel('Load Negotiation Power $\\tau_L$', fontsize=self.labelsize)
            ax.set_title(title, fontsize=self.titlesize)
            ax.grid(True, alpha=0.3)

            # Avoid scientific notation/offset text and clamp y-limits for Gamma on Contract Amount (PAP only)
            if m == 'ContractAmount' and is_pap and has_gamma:
                ax2.set_ylim(99, 101)

        # Build a single legend from unique pairs
        handles = [mpatches.Patch(color=color_map[(pair[0], pair[1])], label=f"A_G={pair[0]}, A_L={pair[1]}") for pair in pairs]
        # Place legend below plots to avoid overlapping the title
        #fig.legend(handles=handles, loc='lower center', ncol=min(3, len(handles)), bbox_to_anchor=(0.5, -0.02))
        fig.legend(
            handles=handles,
            loc='upper center',
            ncol=3,                    # 3 columns
            bbox_to_anchor=(0.5, 0.02),
            frameon=False
        )
        fig.suptitle(f"{self.cm_data.contract_type}: Negotiation Power vs Risk Aversion", fontsize=self.suptitlesize)
        plt.tight_layout(rect=[0, 0.0, 1, 1])
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_3D_sensitivity_results(self, sensitivity_type, filename=None):

        """        Generalized function to plot 3D sensitivity analysis results."""

        """
        Generate individual 3D plots for each metric in sensitivity analysis.
        """

        if sensitivity_type == 'risk':
            df = self.risk_sensitivity_df
            x_col = 'A_L'
            y_col = 'A_G'
            xlabel = 'Risk Aversion $A_L$'
            ylabel = 'Risk Aversion $A_G$'
            title = 'Risk Aversion Sensitivity Analysis'
        else:
            return print(f"Unknown sensitivity type: {sensitivity_type}")

        # Determine metrics to plot
        is_pap = self.cm_data.contract_type == "PAP"
        if is_pap and 'Gamma' in df.columns:
            metrics = ['StrikePrice', 'Gamma','Nash_Product']
            z_labels = ['Strike Price (EUR/MWh)', 'Gamma (%)', 'Nash_Product']
        else:
            metrics = ['StrikePrice', 'ContractAmount', 'Nash_Product']
            z_labels = ['Strike Price (EUR/MWh)', 'Contract Amount (MWh)', 'Nash_Product']

        for i, (metric, z_label) in enumerate(zip(metrics, z_labels)):
            # Create individual figure for each metric
            fig = plt.figure(figsize=(12, 9))
            ax = fig.add_subplot(111, projection='3d')

            # Create pivot table without filling zeros
            pivot_table = df.pivot_table(
                index=x_col,
                columns=y_col,
                values=metric,
                aggfunc='mean'
            )

            # Interpolate missing values
            pivot_table = pivot_table.interpolate(method='linear', axis=0).interpolate(method='linear', axis=1)

            # Create meshgrid
            X, Y = np.meshgrid(pivot_table.columns, pivot_table.index)
            Z = pivot_table.values

            # Create surface plot
            surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)

            # Adjust z-limits to focus on meaningful values
            #z_min, z_max = Z.min(), Z.max()
            #z_range = z_max - z_min
            #ax.set_zlim(z_min - 0.1*z_range, z_max + 0.1*z_range)

            # Add scatter points for actual data
            mask = df[metric] > 0  # Only plot non-zero values
            ax.scatter(df.loc[mask, y_col], df.loc[mask, x_col], df.loc[mask, metric],
                    color='red', s=50, alpha=0.6)

            # Labels and title
            ax.set_xlabel(ylabel, fontsize=16, labelpad=12)
            ax.set_ylabel(xlabel, fontsize=16, labelpad=12)
            ax.set_zlabel(z_label, fontsize=16, labelpad=12)
            ax.set_title(f'{self.cm_data.contract_type}: {title}\n{metric}', fontsize=14)

            # Add colorbar
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=20)
            ax.view_init(elev=30, azim=0)  # adjust as needed

            #for azim in range(0, 360, 15):
            #    ax.view_init(elev=30, azim=azim)
            #    plt.savefig(f'plot_elev30_azim{azim}.png')



            plt.tight_layout()

            if filename:
                filename = f"{metric}_{filename}" if not filename else filename
                filepath = os.path.join(self.plots_dir, filename)
                plt.savefig(filepath, bbox_inches='tight', dpi=300)
                print(f"Plot saved to {filepath}")
                plt.close(fig)
            else:
                plt.show()

    def _plot_sensitivity_results_heatmap(self,sensitivity_type,filename=None):

        """
        Generalized function to plot sensitivity analysis results using heatmaps.

        Parameters:
        -----------
        sensitivity_type : str
            Type of sensitivity analysis ('risk', 'price_bias', 'production_bias')
        filename : str, optional
            Filename to save the plot
        """

        # Configuration dictionary for different sensitivity types
        config = {
            'risk': {
                'df': self.risk_sensitivity_df,
                'title': 'Risk Aversion Sensitivity on Strike Price and Contract Amount',
                'index_col': 'A_L',
                'columns_col': 'A_G',
                'xlabel': 'Risk Aversion $A_S$',
                'ylabel': 'Risk Aversion $A_B$'
            },
            'price_bias': {
                'df': self.price_bias_sensitivity_df,
                'title': 'Price Bias Sensitivity on Strike Price and Contract Amount',
                'index_col': 'KL_Factor',
                'columns_col': 'KG_Factor',
                'xlabel': 'Seller Bias Factor (%)',
                'ylabel': 'Buyer Bias Factor (%)'
            },
            'production_bias': {
                'df': self.production_bias_sensitivity_df,
                'title': 'Production Bias Sensitivity on Strike Price and Contract Amount',
                'index_col': 'KL_Factor',
                'columns_col': 'KG_Factor',
                'xlabel': 'Seller Bias Factor (%)',
                'ylabel': 'Buyer Bias Factor (%)'
            }
        }

        # Get configuration for the specified sensitivity type
        if sensitivity_type not in config:
            raise ValueError(f"Unknown sensitivity_type: {sensitivity_type}")

        cfg = config[sensitivity_type]
        results_df = cfg['df']


        # Prepare data
        results = results_df.copy()
        if sensitivity_type =="risk":
            results = results[results['A_L'].isin([0.1, 0.5, 0.9])]  # Add this line
            results = results[results['A_G'].isin([0.1, 0.5, 0.9])]  # Add this line

        if sensitivity_type == "price_bias" or sensitivity_type == "production_bias":
            results = results[results['KL_Factor'].isin([-0.05, 0.00, 0.05])]  # Add this line
            results = results[results['KG_Factor'].isin([-0.05, 0.00, 0.05])]  # Add this line

        results['ContractAmount'] = results['ContractAmount'].round(2)


        is_pap = self.cm_data.contract_type == "PAP"
        has_gamma = 'Gamma' in results.columns

        # Metrics to plot
        metrics = ['StrikePrice', 'ContractAmount']
        if is_pap and has_gamma:
            units = ['€/MWh', 'MW']
        else:
            units = ['€/MWh', 'MWh']
            #results['ContractAmount/year'] = results['ContractAmount'].round(2)  # Convert to MWh
        titles = ['Strike Price', 'Contract Amount']

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes = axes.flatten()
        if sensitivity_type == "bias":
            fig.suptitle(f'{cfg["title"]}, $A_S$={self.cm_data.A_G},$A_B$={self.cm_data.A_L}', fontsize=self.suptitlesize)
        else:
            fig.suptitle(f'{cfg["title"]}', fontsize=self.suptitlesize)

        for i, (metric, unit, title) in enumerate(zip(metrics, units, titles)):
            ax = axes[i]
            try:
                pivot_table = results.pivot(
                    index=cfg['index_col'],
                    columns=cfg['columns_col'],
                    values=metric
                )
                pivot_table = pivot_table.sort_index(ascending=False)

                sns.heatmap(
                    pivot_table,
                    ax=ax,
                    annot=True,
                    cmap="RdYlGn",
                    cbar=False,
                    linewidths=0.5,
                    fmt ='.2f',
                    linecolor='gray',
                    annot_kws={"size": 16}
                )
                """
                # Add custom annotations with units
                for i_idx, row_idx in enumerate(pivot_table.index):
                    for j_idx, col_idx in enumerate(pivot_table.columns):
                        val = pivot_table.iloc[i_idx, j_idx]
                        if not np.isnan(val):
                            # Get background color for text color determination
                            bg_color = plt.cm.get_cmap("cividis")(
                                plt.Normalize()(pivot_table.values) )[i_idx, j_idx, :3]

                            # Calculate luminance
                            luminance = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
                            text_color = 'white' if luminance < 0.5 else 'black'

                            # Add gamma annotation if applicable
                            if is_pap and has_gamma and metric == 'ContractAmount':
                                gamma_pivot = results.pivot(
                                    index=cfg['index_col'],
                                    columns=cfg['columns_col'],
                                    values='Gamma'
                                ).sort_index(ascending=False)

                                gamma_val = gamma_pivot.iloc[i_idx, j_idx]
                                ax.text(j_idx + 0.5, i_idx + 0.5,
                                    f"γ={gamma_val*100:.2f} %",
                                    ha='center', va='center', color=text_color, fontsize=7)

                                ax.text(j_idx + 0.5, i_idx + 0.63,
                                    f"{self.cm_data.generator_contract_capacity*gamma_val:.2f} MW",
                                    ha='center', va='center', color=text_color, fontsize=7)

                            else:

                                # Format the main value with units
                                if metric == 'ContractAmount':
                                    text = f"{val:.2f} {unit}"
                                else:
                                    text = f"{val:.2f}"

                                # Add the main value annotation
                                ax.text(j_idx + 0.5, i_idx + 0.5, text,
                                    ha='center', va='center', color=text_color, fontsize=7)

                                if metric == 'ContractAmount':
                                # Add the yearly contract value annotation just below the main value
                                    yearly_val = results.pivot(
                                        index=cfg['index_col'],
                                        columns=cfg['columns_col'],
                                        values='ContractAmount/year'
                                    ).sort_index(ascending=False).iloc[i_idx, j_idx]
                                    ax.text(j_idx + 0.5, i_idx + 0.63,
                                        f"{yearly_val:.2f} GWh/y",
                                        ha='center', va='center', color=text_color, fontsize=7)



                """
                ax.set_title(f"{title} ({unit})", fontsize=self.titlesize)
                ax.set_xlabel(cfg['xlabel'], fontsize=self.labelsize)
                ax.set_ylabel(cfg['ylabel'], fontsize=self.labelsize)

            except Exception as e:
                print(f"Could not plot heatmap for {metric}: {e}")
                ax.set_title(f'{metric} (Plotting Error)')

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_sensitivity_results_line(self, sensitivity_type, filename=None):
        """
        Generalized function to plot sensitivity analysis results for 1D parameter sweeps.
        For negotiation: uses tau_L as parameter.
        For alpha: uses 'alpha' as parameter (single value, not Alpha_L/Alpha_G).
        """
        # Configuration dictionary for different sensitivity types
        config = {
            'negotiation': {
                'df': self.negotiation_sensitivity_df,
                'param_col': 'tau_L',
                'xlabel': 'Load Negotiation Power $\\tau_L$',
                'title': 'Negotiation Power Sensitivity on Strike Price and Contract Amount'
            }
        }

        # Get configuration for the specified sensitivity type
        cfg = config[sensitivity_type]
        results_df = cfg['df'].copy()

        # Calculate reference values

        # Determine contract type and setup units/labels
        is_pap = self.cm_data.contract_type == "PAP"
        has_gamma = 'Gamma' in results_df.columns
        expected_production = self.cm_data.expected_production /8760*1000  # IN MW


        if is_pap and has_gamma:
            capture_price_pap = self.cm_data.Capture_price_G_avg*1e3  # Convert to EUR/MWh
            # PAP contract with Gamma
            units = ['€/MWh', 'MW']
            production_type = "MWh"

            # Convert contract amount to MW for PAP
            results_df['ContractAmount'] = results_df['ContractAmount']
        else:
            avg_price = self.cm_data.expected_price *1e3  # Convert to EUR/MWh
            # Non-PAP contract
            units = ['€/MWh', 'MWh']
            capture_price_type = r"\mathbb{E}(\lambda) (EUR/MWh)"
            production_type = "MWh"

            # Keep original contract amount and create yearly version
            #results_df['ContractAmount_yearly'] = results_df['ContractAmount'].round(2)
            results_df['ContractAmount'] = results_df['ContractAmount']

        # Sort results by parameter
        results_sorted = results_df.sort_values(cfg['param_col'])
        param_values = results_sorted[cfg['param_col']].values

        # Setup subplots
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        metrics = ['StrikePrice', 'ContractAmount']
        titles = ['Strike Price', 'Contract Amount']

        for i, (metric, unit, title) in enumerate(zip(metrics, units, titles)):
            ax = axes[i]

            # Plot reference lines
            if metric == 'StrikePrice' and is_pap:
                ax.axhline(capture_price_pap, color='black', linestyle='--',
                        label=f'Capture Price (G) ')
            elif metric == 'StrikePrice':
                ax.axhline(avg_price, color='black', linestyle='--',
                        label=f'Expected Price')
            elif metric == 'ContractAmount' and not (is_pap):
                # Plot expected production line for non-PAP contracts
                ax.axhline(expected_production, color='black', linestyle='--',
                        label=f'Expected Production {production_type}')

            # Plot main metric
            ax.plot(param_values, np.round(results_sorted[metric].values,4),marker='o', linewidth=2, markersize=8, label=f"({title})")
            """
            sns.lineplot(
                x=param_values,
                y=results_sorted[metric].values,
                marker='o',
                linewidth=2,
                markersize=8,
                ax=ax,
                label=f"Contract ({title})"
            )
            """
            # Handle secondary y-axis for Contract Amount subplot
            if metric == 'ContractAmount':
                if is_pap and has_gamma:
                    # Plot Gamma percentage for PAP contracts
                    ax2 = ax.twinx()

                    gamma_values = results_sorted['Gamma'].values * 100

                    ax2.plot(param_values, gamma_values, linestyle='--',color="red", linewidth=1, label='Gamma (%)')
                    """
                    sns.lineplot(
                        x=param_values,
                        y=gamma_values,
                        marker='s',
                        linewidth=1,
                        markersize=6,
                        color='red',
                        alpha=0.7,
                        linestyle='--',
                        ax=ax2,
                        label='Gamma (%)'
                    )
                    """
                    ax2.set_ylabel('Gamma (%)', color='red')
                    ax2.tick_params(axis='y', labelcolor='red')

                    # Special handling if Gamma values are all close to 100%
                    if np.allclose(gamma_values, 100, atol=1e-2):
                        ax2.set_ylim(99, 101)
                        #Set y-limits with some padding
                    #y_values = results_sorted[metric].values
                    #y_padding = 0.1 * (y_values.max() - y_values.min())
                    #ax.set_ylim(y_values.min() - y_padding, y_values.max() + y_padding)
                # Create combined legend for Contract Amount subplot only
                lines1, labels1 = ax.get_legend_handles_labels()
                if is_pap and has_gamma:
                    # Include Gamma line in the legend
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=self.legendsize)
                else:
                    ax.legend(lines1, labels1, loc="best", fontsize=self.legendsize)

            else:
                # Simple legend for Strike Price subplot

                ax.legend(loc="best", fontsize=self.legendsize)

            # Configure axes
            ax.set_xlabel(cfg['xlabel'], fontsize=self.labelsize)
            ax.set_ylabel(f'{title} ({unit})', fontsize=self.labelsize)
            ax.set_title(title, fontsize=self.titlesize)
            ax.grid(True, alpha=0.3)
            #



        # Add main title and layout
        fig.suptitle(f'{self.cm_data.contract_type}: {cfg["title"]}', fontsize=self.suptitlesize)
        plt.tight_layout()

        # Save or show plot
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()

    def _plot_sensitivity(self, x_column, sensitivity_name="Sensitivity", filename=None):
        """
        Generalized sensitivity plot for contract parameters.
        df: DataFrame with sensitivity results
        x_column: str, column name for x-axis (e.g. 'Production_Change', 'CaptureRate_Change', etc.)
        sensitivity_name: str, for plot titles (e.g. 'Production', 'Capture Rate', 'Price', etc.)
        filename: optional, for saving the plot
        """

        if sensitivity_name == "Production":
            df = self.production_sensitivity_mean_df

        elif sensitivity_name == "Capture Rate":
            df = self.gen_CR_sensitivity_results

        elif sensitivity_name == "Load Capture Rate":
            df = self.load_CR_sensitivity_df

        elif sensitivity_name == "Load":
            df = self.load_sensitivity_mean_df

        elif sensitivity_name == "Price":
            df = self.price_sensitivity_mean_df

        else:
            return print("No Sensitivity Dataframe Found")
        # Create figure with subplots - use a 2x3 grid for detailed analysis
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle(
            f'{self.cm_data.contract_type}: Contract Parameters Sensitivity to {sensitivity_name} $A_G$ = {self.cm_data.A_G}, $A_L$ = {self.cm_data.A_L}',
            fontsize=self.suptitlesize
        )
        axes = axes.flatten()

        # Plot Strike Price
        axes[0].plot(df[x_column], df['StrikePrice'], marker='o', linestyle='-')
        axes[0].set_xlabel(f'{x_column} (%)', fontsize=self.labelsize)
        axes[0].set_ylabel('Strike Price (EUR/MWh)', fontsize=self.labelsize)
        axes[0].set_title(f'Strike Price vs {sensitivity_name}', fontsize=self.titlesize)
        axes[0].grid(True)

        # Plot Contract Amount
        if self.cm_data.contract_type == "PAP":
            axes[1].set_ylim(25, 40)
        axes[1].plot(df[x_column], df['ContractAmount'], marker='o', linestyle='-')
        axes[1].set_xlabel(f'{x_column} (%)', fontsize=self.labelsize)
        axes[1].set_ylabel('Contract Amount (MWh)', fontsize=self.labelsize)
        axes[1].set_title(f'Contract Amount vs {sensitivity_name}', fontsize=self.titlesize)
        axes[1].yaxis.set_major_formatter(plt.FormatStrFormatter('%.1f'))
        axes[1].grid(True)

        # Plot Utility G
        axes[2].plot(df[x_column], df['Utility_G'], marker='o', linestyle='-', label='Utility Generator')
        axes[2].plot(df[x_column], df['ThreatPoint_G'], marker='o', linestyle='-', label='Threat Point Generator')
        axes[2].set_xlabel(f'{x_column} (%)', fontsize=self.labelsize)
        axes[2].set_ylabel('Utility Generator', fontsize=self.labelsize)
        axes[2].set_title(f'Generator Utility vs {sensitivity_name}', fontsize=self.titlesize)
        axes[2].grid(True)
        axes[2].legend()

        # Plot Utility L
        axes[3].plot(df[x_column], df['Utility_L'], marker='o', linestyle='-', label='Utility Load')
        axes[3].plot(df[x_column], df['ThreatPoint_L'], marker='o', linestyle='-', label='Threat Point Load')
        axes[3].set_xlabel(f'{x_column} (%)', fontsize=self.labelsize)
        axes[3].set_ylabel('Utility Load', fontsize=self.labelsize)
        axes[3].set_title(f'Load Utility & Threatpoint vs {sensitivity_name}', fontsize=self.titlesize)
        axes[3].grid(True)
        axes[3].legend()

        plt.tight_layout()
        plt.subplots_adjust(top=0.92)

        if filename:
            plt.savefig(os.path.join(self.plots_dir, filename), dpi=300, bbox_inches='tight')
            print(f"Saved {sensitivity_name.lower()} sensitivity plot to {filename}")
        else:
            plt.show()

    def _plot_parameter_sensitivity_spider(self, bias = False, filename=None):
        """
        Create a spider/radar plot showing how different parameters affect contract outcomes.
        Compares the sensitivity of contract parameters to different input variables.
        """
        plt.figure(figsize=(12, 10))



        # Define the metrics we want to compare
        if self.cm_data.contract_type == "PAP":
            metrics = ['StrikePrice', 'Gamma', 'Utility_G', 'Utility_L', 'ThreatPoint_G', 'ThreatPoint_L']
        else:
            metrics = ['StrikePrice', 'ContractAmount', 'Utility_G', 'Utility_L', 'ThreatPoint_G', 'ThreatPoint_L']


      # Prepare bias data as in spider plot
        price_bias_sensitivity_df = self.price_bias_sensitivity_df.copy()
        price_bias_sensitivity_df['KG_Factor'] = 1.0 + self.price_bias_sensitivity_df['KG_Factor']
        price_bias_sensitivity_df['KL_Factor'] = 1.0 + self.price_bias_sensitivity_df['KL_Factor']
        price_bias_KG = price_bias_sensitivity_df[price_bias_sensitivity_df['KL_Factor'] == 1.00]
        price_bias_KL = price_bias_sensitivity_df[price_bias_sensitivity_df['KG_Factor'] == 1.00]

        # Bias Production

        production_bias_sensitivity_df = self.production_bias_sensitivity_df.copy()
        production_bias_sensitivity_df['KG_Factor'] = 1.0 + self.production_bias_sensitivity_df['KG_Factor']
        production_bias_sensitivity_df['KL_Factor'] = 1.0 + self.production_bias_sensitivity_df['KL_Factor']
        production_bias_KG = production_bias_sensitivity_df[production_bias_sensitivity_df['KL_Factor'] == 1.00]
        production_bias_KL = production_bias_sensitivity_df[production_bias_sensitivity_df['KG_Factor'] == 1.00]
        # Define the sensitivity analyses to process

        elasticities = {}

        def _compute_local_elasticity(df_in: pd.DataFrame, factor_col: str, metric_cols: list[str], baseline: float) -> dict:
            """Compute local elasticities at baseline using central diff if possible, else local linear fit.
            E = (dY/dX) * (X0 / Y0). Handles NaNs by skipping invalid rows; returns NaN when insufficient data.
            """
            if df_in is None or df_in.empty:
                return {m: np.nan for m in metric_cols}

            df = df_in[[factor_col] + metric_cols].copy()
            # Keep rows where factor is finite
            df = df[np.isfinite(df[factor_col])]
            if df.empty:
                return {m: np.nan for m in metric_cols}

            # Sort by factor and drop duplicate X keeping closest to baseline
            df = df.sort_values(factor_col)
            # Identify indices around baseline
            x_vals = df[factor_col].values.astype(float)

            # Find bracket points around baseline
            left_mask = x_vals < baseline
            right_mask = x_vals > baseline

            result = {}
            for m in metric_cols:
                y_series = df[m].astype(float)
                # Valid rows for this metric
                valid = np.isfinite(y_series.values)
                if valid.sum() < 2:
                    result[m] = np.nan
                    continue

                x = x_vals[valid]
                y = y_series.values[valid]

                # Recompute masks on valid-only arrays
                left_idx = np.where(x < baseline)[0]
                right_idx = np.where(x > baseline)[0]

                slope = np.nan
                y0 = np.nan
                # Try exact baseline first
                exact_idx = np.where(np.isclose(x, baseline))[0]
                if exact_idx.size > 0:
                    y0 = y[exact_idx[0]]
                # Central difference if we have neighbors on both sides
                if left_idx.size > 0 and right_idx.size > 0:
                    iL = left_idx[-1]
                    iR = right_idx[0]
                    xL, yL = x[iL], y[iL]
                    xR, yR = x[iR], y[iR]
                    if np.isfinite(yL) and np.isfinite(yR) and xR != xL:
                        slope = (yR - yL) / (xR - xL)
                        if not np.isfinite(y0):
                            # Linear interpolate y0
                            y0 = yL + (baseline - xL) * slope
                # Fallback: local linear fit using up to 5 nearest points
                if not np.isfinite(slope):
                    if x.size >= 2:
                        # Select nearest k points
                        k = min(5, x.size)
                        order = np.argsort(np.abs(x - baseline))[:k]
                        x_fit = x[order]
                        y_fit = y[order]
                        if np.unique(x_fit).size >= 2:
                            coeffs = np.polyfit(x_fit, y_fit, deg=1)
                            slope = coeffs[0]
                            y0 = np.polyval(coeffs, baseline)
                # Compute elasticity
                if not np.isfinite(slope) or not np.isfinite(y0) or np.isclose(y0, 0.0):
                    result[m] = np.nan
                else:
                    result[m] = float(slope * (baseline / y0))
            return result
        if bias == False:
            sensitivity_analyses = [
                {
                'name': 'Production (Mean)',
                'df': self.production_sensitivity_mean_df,
                'factor_col': 'Production_Change',
            },
            {
                'name': 'Prod. Capture Rate (Mean)',
                'df': self.gen_CR_sensitivity_results,
                'factor_col': 'CaptureRate_Change',
            },
            {
                'name': 'Load. Capture Rate (Mean)',
                'df': self.load_CR_sensitivity_df,
                'factor_col': 'Load_CaptureRate_Change'
            },
            {
                'name': 'Load Sensitivity (Mean)',
                'df': self.load_sensitivity_mean_df,
                'factor_col': 'Load_Change',
            },

            {
                'name': 'Price Sensitivity (Mean)',
                'df': self.price_sensitivity_mean_df,
                'factor_col': 'Price_Change',

            },
            {
                'name': 'Price Sensitivity (Std)',
                'df': self.price_sensitivity_std_df,
                'factor_col': 'Price_Change',

            },
            {
                'name': 'Production (Std)',
                'df': self.production_sensitivity_std_df,
                'factor_col': 'Production_Change',

            },
            {
                'name': 'Load Sensitivity (Std)',
                'df': self.load_sensitivity_std_df,
                'factor_col': 'Load_Change',

            }

        ]
        else:
            sensitivity_analyses = [
             {
                'name': 'Price Bias (G)',
                    'df': price_bias_KG,
                'factor_col': 'KG_Factor',
            },
            {
                'name': 'Price Bias (L)',
                'df': price_bias_KL,
                'factor_col': 'KL_Factor',
            },
            {
                'name': 'Production Bias (G)',
                'df': production_bias_KG,
                'factor_col': 'KG_Factor'
            },
            {
                'name': 'Production Bias (L)',
                'df': production_bias_KL,
                'factor_col': 'KL_Factor',
            },
                  ]


        for analysis in sensitivity_analyses:
            df = analysis['df']
            factor_col = analysis['factor_col']
            # All sensitivity factors are modeled as multiplicative changes around 1.0
            baseline = 1.0
            vals = _compute_local_elasticity(df, factor_col=factor_col, metric_cols=metrics, baseline=baseline)
            elasticities[analysis['name']] = {k: (None if (v is None) else (np.nan if not np.isfinite(v) else round(v, 3))) for k, v in vals.items()}

        # You could add more parameter elasticities here (risk aversion, bias, etc.)

        # Create the spider plot
        # Set up the radar chart
        categories = metrics
        N = len(categories)

        # Create angles for each metric (evenly spaced around the circle)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Close the loop

        # Create subplot with polar projection (for radar chart)
        ax = plt.subplot(111, polar=True)

        # Set the first axis to be on top
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        # Add a bold circle at zero elasticity
        zero_circle = np.zeros(100)
        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(theta, zero_circle, 'k-', linewidth=2.5)  # Bold black line for zero


        # Draw one axis per variable and add labels
        plt.xticks(angles[:-1], [f"${cat}$" for cat in categories], size=self.labelsize)
        # Set y limits
        ax.set_ylim(-1, 1.25)

        # Add parameter elasticities

        for i, (param, values) in enumerate(elasticities.items()):
            values_ordered = [values[metric] for metric in categories]
            values_ordered += values_ordered[:1]  # Close the loop

            ax.plot(angles, values_ordered, linewidth=2, linestyle='solid',
                    label=f"${param}$")
            ax.fill(angles, values_ordered, alpha=0.1,)

        # Add legend
        plt.legend(loc='upper left')

        # Add title
        plt.title(f'{self.cm_data.contract_type}: Parameter Sensitivity Comparison Elaticities by Factor',
                size=self.titlesize, y=1.1)

        # Add reference circles and lines
        plt.grid(True)

        # Add annotations for key insights


        # Save or show the plot
        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Spider plot saved to {filepath}")
            plt.close()
        else:
            plt.show()

    def _plot_elasticity_tornado(self, bias = False, metrics='StrikePrice', filename=None):

        """
        Create a tornado plot showing the elasticity of a single metric
        with respect to different input factors.
        """

        if isinstance(metrics, str):
            metrics = [metrics]


        # Prepare the same elasticities as in the spider plot
        #if self.cm_data.contract_type == "PAP":
        #    metrics = ['StrikePrice', 'Gamma', 'Utility_G', 'Utility_L', 'ThreatPoint_G', 'ThreatPoint_L']
        #else:
        #    metrics = ['StrikePrice', 'ContractAmount', 'Utility_G', 'Utility_L', 'ThreatPoint_G', 'ThreatPoint_L']

        # Prepare bias data as in spider plot
        price_bias_sensitivity_df = self.price_bias_sensitivity_df.copy()
        price_bias_sensitivity_df['KG_Factor'] = 1.0 + self.price_bias_sensitivity_df['KG_Factor']
        price_bias_sensitivity_df['KL_Factor'] = 1.0 + self.price_bias_sensitivity_df['KL_Factor']
        price_bias_KG = price_bias_sensitivity_df[price_bias_sensitivity_df['KL_Factor'] == 1.00]
        price_bias_KL = price_bias_sensitivity_df[price_bias_sensitivity_df['KG_Factor'] == 1.00]

        # Bias Production

        production_bias_sensitivity_df = self.production_bias_sensitivity_df.copy()
        production_bias_sensitivity_df['KG_Factor'] = 1.0 + self.production_bias_sensitivity_df['KG_Factor']
        production_bias_sensitivity_df['KL_Factor'] = 1.0 + self.production_bias_sensitivity_df['KL_Factor']
        production_bias_KG = production_bias_sensitivity_df[production_bias_sensitivity_df['KL_Factor'] == 1.00]
        production_bias_KL = production_bias_sensitivity_df[production_bias_sensitivity_df['KG_Factor'] == 1.00]
        # Define the sensitivity analyses to process

        if bias == False:
            sensitivity_analyses = [
                {
                'name': 'Production (Mean)',
                'df': self.production_sensitivity_mean_df,
                'factor_col': 'Production_Change',
            },
            {
                'name': 'Prod. Capture Rate (Mean)',
                'df': self.gen_CR_sensitivity_results,
                'factor_col': 'CaptureRate_Change',
            },
            {
                'name': 'Load. Capture Rate (Mean)',
                'df': self.load_CR_sensitivity_df,
                'factor_col': 'Load_CaptureRate_Change'
            },
            {
                'name': 'Load Sensitivity (Mean)',
                'df': self.load_sensitivity_mean_df,
                'factor_col': 'Load_Change',
            },

            {
                'name': 'Price Sensitivity (Mean)',
                'df': self.price_sensitivity_mean_df,
                'factor_col': 'Price_Change',

            },
            {
                'name': 'Price Sensitivity (Std)',
                'df': self.price_sensitivity_std_df,
                'factor_col': 'Price_Change',

            },
            {
                'name': 'Production (Std)',
                'df': self.production_sensitivity_std_df,
                'factor_col': 'Production_Change',

            },
            {
                'name': 'Load Sensitivity (Std)',
                'df': self.load_sensitivity_std_df,
                'factor_col': 'Load_Change',

            }

        ]
        else:
            sensitivity_analyses = [
             {
                'name': 'Price Bias (G)',
                    'df': price_bias_KG,
                'factor_col': 'KG_Factor',
            },
            {
                'name': 'Price Bias (L)',
                'df': price_bias_KL,
                'factor_col': 'KL_Factor',
            },
            {
                'name': 'Production Bias (G)',
                'df': production_bias_KG,
                'factor_col': 'KG_Factor'
            },
            {
                'name': 'Production Bias (L)',
                'df': production_bias_KL,
                'factor_col': 'KL_Factor',
            },
                  ]

        n_metrics = len(metrics)
        ncols = int(np.ceil(np.sqrt(n_metrics)))
        nrows = int(np.ceil(n_metrics / ncols))

        fig, axes = plt.subplots(nrows, ncols, figsize=(8.5 * ncols, 6 * nrows))
        axes = axes.flatten()  # Flatten for easy indexing

        for idx, metric in enumerate(metrics):
            elasticities = {}
            for analysis in sensitivity_analyses:
                df = analysis['df']
                if df is None or df.empty:
                    print(f"Warning: DataFrame for {analysis['name']} is empty. Skipping.")
                    continue
                factor_col = analysis['factor_col']
                # All sensitivity factors are modeled as multiplicative changes around 1.0
                baseline = 1.0
                vals = self._safe_local_elasticity_single(df, factor_col=factor_col, metric_col=metric, baseline=baseline)
                if vals is not None and np.isfinite(vals):
                    # Keep full precision for plotting; format only in labels
                    elasticities[analysis['name']] = float(vals)
                else:
                    elasticities[analysis['name']] = np.nan

            # Prepare data for plotting
            factors = list(elasticities.keys())
            values = [elasticities[f] for f in factors]
            sorted_indices = np.argsort(np.abs(values))[::-1]
            sorted_factors = [factors[i] for i in sorted_indices]
            sorted_values = [values[i] for i in sorted_indices]

            tornado_df = pd.DataFrame({
                'Factor': sorted_factors,
                'Elasticity': sorted_values
            })

            ax = axes[idx]
            sns.barplot(
                data=tornado_df,
                y='Factor',
                x='Elasticity',
                orient='h',
                color='skyblue',
                ax=ax
            )
            ax.axvline(0, color='k', linewidth=1)
            ax.set_xlabel(f'Elasticity of ${metric}$',fontsize=self.labelsize)

            ax.set_title(f'Sensitivity of ${metric}$',fontsize=self.titlesize)
            ax.grid(axis='x', linestyle=':', alpha=0.7)


            for bar, value in zip(ax.patches, sorted_values):
                width = bar.get_width()
                y     = bar.get_y() + bar.get_height()/2

                offset = -15            # points   (change to taste)
                ha     = 'left'
                if width < 0:         # put the label on the other side of negative bars
                    offset = -3
                    ha     = 'right'

                txt = ax.annotate(f'{value:.3f}',
                                xy=(width, y),                 # end of the bar
                                xytext=(offset, 0),            # shift *offset* points
                                textcoords='offset points',
                                va='center',
                                ha=ha,
                                fontsize=self.legendsize,
                                zorder=3)


            xmin, xmax = ax.get_xlim()
            span = xmax - xmin
            ax.set_xlim(xmin - 0.05*span, xmax + 0.05*span)
        # Delete unused

    def _plot_elasticity_tornado_vs_risk(self,
                                     bias = False,
                                     fixed_A_G_values=None,
                                     fixed_A_L_values=None,
                                     metrics=['StrikePrice'],
                                     filename=None,
                                     fix: str = 'A_G'):
        """
        Plot grouped tornado bars (elasticities) for each metric across risk aversion combinations,
        computing elasticities with a log-log regression:

            log(metric) = a + b * log(factor)  ->  elasticity = b

        Parameters
        ----------
        bias : bool
            If True, analyzes bias factors (KG_Factor, KL_Factor) instead of production/price factors
        fixed_A_G_values : list[float] | None
            Values of A_G to fix when fix='A_G'
        fixed_A_L_values : list[float] | None
            Values of A_L to fix when fix='A_L'
        metrics : list[str]
            Metrics for which elasticities are plotted.
        filename : str | None
            If provided, each figure is saved as <filename>_<metric>.png
        fix : {'A_G','A_L'}
            Which party's risk aversion to hold fixed while grouping bars by the other party.
        """

        if bias == False:
            df = self.elasticity_vs_risk_df.copy()

            if df is None or df.empty:
                print("No data for elasticity_vs_risk plotting.")
                return

            # Map displayed factor label -> underlying factor change column
            factor_xcol = {
                'Production (Expected)': 'Production_Change',
                'Production (Std)': 'Production_Change',
                'Price Sensitivity (Expected)': 'Price_Change',
                'Price Sensitivity (Std)': 'Price_Change',
                'Load Sensitivity (Expected)': 'Load_Change',
                'Load Sensitivity (Std)': 'Load_Change',
                'Prod. Capture Rate (Expected)': 'CaptureRate_Change',
                'Load. Capture Rate (Expected)': 'Load_CaptureRate_Change',
            }

            factor_order = [
                'Prod. Capture Rate (Expected)',
                'Price Sensitivity (Expected)',
                'Production (Expected)',
                'Production (Std)',
                'Price Sensitivity (Std)',
                'Load Sensitivity (Expected)',
                'Load. Capture Rate (Expected)',
                'Load Sensitivity (Std)',
            ]

        else:  # bias == True
            df = self.bias_risk_elasticity_df.copy()

            if df is None or df.empty:
                print("No data for bias_risk_elasticity plotting.")
                return

            # Convert bias factors to multiplicative form (from additive)
            df['KG_Factor_mult'] = 1.0 + df['KG_Factor']
            df['KL_Factor_mult'] = 1.0 + df['KL_Factor']

            # Create separate datasets for each bias scenario
            scenarios = []

            # Scenario 1: KG_Factor = 0 (no bias for G), varying KL_Factor
            # This gives us elasticity w.r.t. L's bias
            kg_zero = df[df['KG_Factor'] == 0.0].copy()
            if not kg_zero.empty:
                # For Price Bias
                price_bias_kg_zero = kg_zero[kg_zero['Factor'] == 'Price Bias'].copy()
                price_bias_kg_zero['Factor'] = 'Price Bias (L)'
                price_bias_kg_zero['varying_factor'] = 'KL_Factor_mult'
                scenarios.append(price_bias_kg_zero)

                # For Production Bias
                prod_bias_kg_zero = kg_zero[kg_zero['Factor'] == 'Production Bias'].copy()
                prod_bias_kg_zero['Factor'] = 'Production Bias (L)'
                prod_bias_kg_zero['varying_factor'] = 'KL_Factor_mult'
                scenarios.append(prod_bias_kg_zero)

            # Scenario 2: KL_Factor = 0 (no bias for L), varying KG_Factor
            # This gives us elasticity w.r.t. G's bias
            kl_zero = df[df['KL_Factor'] == 0.0].copy()
            if not kl_zero.empty:
                # For Price Bias
                price_bias_kl_zero = kl_zero[kl_zero['Factor'] == 'Price Bias'].copy()
                price_bias_kl_zero['Factor'] = 'Price Bias (G)'
                price_bias_kl_zero['varying_factor'] = 'KG_Factor_mult'
                scenarios.append(price_bias_kl_zero)

                # For Production Bias
                prod_bias_kl_zero = kl_zero[kl_zero['Factor'] == 'Production Bias'].copy()
                prod_bias_kl_zero['Factor'] = 'Production Bias (G)'
                prod_bias_kl_zero['varying_factor'] = 'KG_Factor_mult'
                scenarios.append(prod_bias_kl_zero)

            # Combine all scenarios
            df = pd.concat(scenarios, ignore_index=True)

            if df.empty:
                print("No valid bias scenarios found (need KG_Factor=0 or KL_Factor=0 rows).")
                return

            # Factor mapping for bias analysis
            factor_xcol = {
                'Price Bias (G)': 'KG_Factor_mult',
                'Price Bias (L)': 'KL_Factor_mult',
                'Production Bias (G)': 'KG_Factor_mult',
                'Production Bias (L)': 'KL_Factor_mult',
            }

            factor_order = [
                'Price Bias (G)',
                'Price Bias (L)',
                'Production Bias (G)',
                'Production Bias (L)',
            ]

        def _loglog_elasticity(block: pd.DataFrame, factor_col: str, metric_col: str) -> float | None:
            """
            Return slope of log(metric) vs log(factor) for the block (elasticity).
            Requires >= 2 positive finite observations for both.
            """
            if block is None or block.empty or factor_col not in block.columns or metric_col not in block.columns:
                return np.nan
            x_raw = pd.to_numeric(block[factor_col], errors='coerce')
            y_raw = pd.to_numeric(block[metric_col], errors='coerce')
            mask = (x_raw > 0) & (y_raw > 0) & np.isfinite(x_raw) & np.isfinite(y_raw)
            if mask.sum() < 2:
                return np.nan
            lx = np.log(x_raw[mask].values)
            ly = np.log(y_raw[mask].values)
            # Guard against zero variance
            if np.allclose(lx, lx[0]) or np.allclose(ly, ly[0]):
                return np.nan
            slope = np.polyfit(lx, ly, 1)[0]
            # Clean near-zero numerical noise
            if np.isfinite(slope) and abs(slope) < 1e-9:
                slope = 0.0
            return float(slope) if np.isfinite(slope) else np.nan

        # Main plotting logic
        for metric in metrics:
            if fix == 'A_G':
                if not fixed_A_G_values:
                    print("No fixed_A_G_values provided for fix='A_G'.")
                    return
                for ag in fixed_A_G_values:
                    sub = df[df['A_G'].round(3) == round(ag, 3)].copy()
                    if sub.empty:
                        print(f"Warning: No rows for A_G={ag} in df.")
                        continue
                    var_values = sorted(sub['A_L'].dropna().unique().tolist())
                    present_factors = [f for f in factor_order if f in sub['Factor'].unique()]
                    if not present_factors:
                        print(f"No recognized factors for A_G={ag}")
                        continue

                    # rows = factors, cols = varying A_L
                    data = {al: [] for al in var_values}
                    for factor in present_factors:
                        fcol = factor_xcol.get(factor)
                        for al in var_values:
                            block = sub[(sub['Factor'] == factor) &
                                        (sub['A_L'].round(3) == round(al, 3))]
                            val = _loglog_elasticity(block, fcol, metric) if fcol else np.nan
                            data[al].append(val if np.isfinite(val) else np.nan)

                    plot_df = pd.DataFrame(data, index=present_factors)
                    valid_cols = [c for c in plot_df.columns if np.isfinite(plot_df[c].values).any()]
                    if not valid_cols:
                        print(f"No valid elasticities (log-log) for A_G={ag} across any A_L.")
                        continue
                    plot_df = plot_df[valid_cols]

                    # Plot
                    n_factors = len(present_factors)
                    n_groups = len(valid_cols)
                    bar_h = 0.8 / max(1, n_groups)
                    y_positions = np.arange(n_factors)

                    fig, ax = plt.subplots(figsize=(8.5, 0.5 * n_factors + 2))
                    for i, al in enumerate(valid_cols):
                        vals = plot_df[al].values
                        color = self._color_for_risk(al, kind='A_L')
                        ax.barh(y_positions + (i - (n_groups - 1)/2) * bar_h,
                                vals, height=bar_h, color=color, label=f"A_L={al}")

                    ax.axvline(0.0, color='k', linewidth=1)
                    ax.set_yticks(y_positions)
                    ax.set_yticklabels([f"{f}" for f in present_factors], fontsize=self.legendsize)
                    ax.set_xlabel(f"Elasticity of ${metric}$", fontsize=self.labelsize)

                    bias_suffix = " (Bias Analysis)" if bias else ""
                    ax.set_title(f"Parameter Sensitivity {self.cm_data.contract_type}, A_G={ag}{bias_suffix}",
                                fontsize=self.titlesize)
                    ax.grid(axis='x', linestyle=':', alpha=0.6)
                    ax.legend(fontsize=self.legendsize-1, title_fontsize=self.legendsize-1,loc="upper right",
                            ncol=min(3, n_groups))

                    plt.tight_layout()
                    if filename:
                        bias_suffix = "_bias" if bias else ""
                        fname = f"{filename}{bias_suffix}_{metric}_AG_{ag}.png"
                        plt.savefig(fname, bbox_inches='tight', dpi=300)
                        print(f"Saved log-log elasticity-vs-risk tornado: {fname}")
                        plt.close(fig)
                    else:
                        plt.show()

            elif fix == 'A_L':
                if not fixed_A_L_values:
                    print("No fixed_A_L_values provided for fix='A_L'.")
                    return
                for al in fixed_A_L_values:
                    sub = df[df['A_L'].round(3) == round(al, 3)].copy()
                    if sub.empty:
                        print(f"Warning: No rows for A_L={al} in df.")
                        continue
                    var_values = sorted(sub['A_G'].dropna().unique().tolist())
                    present_factors = [f for f in factor_order if f in sub['Factor'].unique()]
                    if not present_factors:
                        print(f"No recognized factors for A_L={al}")
                        continue

                    data = {ag: [] for ag in var_values}
                    for factor in present_factors:
                        fcol = factor_xcol.get(factor)
                        for ag in var_values:
                            block = sub[(sub['Factor'] == factor) &
                                        (sub['A_G'].round(3) == round(ag, 3))]
                            val = _loglog_elasticity(block, fcol, metric) if fcol else np.nan
                            data[ag].append(val if np.isfinite(val) else np.nan)

                    plot_df = pd.DataFrame(data, index=present_factors)
                    valid_cols = [c for c in plot_df.columns if np.isfinite(plot_df[c].values).any()]
                    if not valid_cols:
                        print(f"No valid elasticities (log-log) for A_L={al} across any A_G.")
                        continue
                    plot_df = plot_df[valid_cols]

                    n_factors = len(present_factors)
                    n_groups = len(valid_cols)
                    bar_h = 0.8 / max(1, n_groups)
                    y_positions = np.arange(n_factors)

                    fig, ax = plt.subplots(figsize=(8.5, 0.5 * n_factors + 2))
                    for i, ag in enumerate(valid_cols):
                        vals = plot_df[ag].values
                        color = self._color_for_risk(ag, kind='A_G')
                        ax.barh(y_positions + (i - (n_groups - 1)/2) * bar_h,
                                vals, height=bar_h, color=color, label=f"A_G={ag}")

                    ax.axvline(0.0, color='k', linewidth=1)
                    ax.set_yticks(y_positions)
                    ax.set_yticklabels([f"{f}" for f in present_factors], fontsize=self.legendsize)
                    ax.set_xlabel(f"Elasticity of ${metric}$", fontsize=self.labelsize)

                    bias_suffix = " (Bias Analysis)" if bias else ""
                    ax.set_title(f"Parameter Sensitivity {self.cm_data.contract_type}, A_L={al}{bias_suffix}",
                                fontsize=self.titlesize)
                    ax.grid(axis='x', linestyle=':', alpha=0.6)
                    ax.legend(fontsize=self.legendsize-1, title_fontsize=self.legendsize-1,loc="upper right",
                            ncol=min(3, n_groups))

                    plt.tight_layout()
                    if filename:
                        bias_suffix = "_bias" if bias else ""
                        fname = f"{filename}{bias_suffix}_{metric}_AL_{al}.png"
                        plt.savefig(fname, bbox_inches='tight', dpi=300)
                        print(f"Saved log-log elasticity-vs-risk tornado: {fname}")
                        plt.close(fig)
                    else:
                        plt.show()
            else:
                print("Invalid fix mode. Use fix='A_G' or fix='A_L'.")
