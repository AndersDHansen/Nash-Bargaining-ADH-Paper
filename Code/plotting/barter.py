"""Barter set and utility space plotting methods."""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os


class BarterPlotsMixin:
    """Mixin providing barter set and utility space plotting methods."""

    def _plot_utility_space(self, filename=None):
        """
        Plot the utility space showing feasible region, threat points, and Nash bargaining solution.
        This is fundamental for understanding the negotiation dynamics.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

        # 1. Utility Space with Different Risk Scenarios
        risk_df = self.risk_sensitivity_df.copy()

        # Plot threat points and contract utilities for different scenarios
        scenarios = [
            {'A_G': 0, 'A_L': 0, 'label': 'Risk Neutral', 'color': 'green', 'marker': 'o'},
            {'A_G': 0.5, 'A_L': 0.5, 'label': 'Moderate Risk', 'color': 'orange', 'marker': 's'},
            {'A_G': 1, 'A_L': 1, 'label': 'High Risk', 'color': 'red', 'marker': '^'},
            {'A_G': 0, 'A_L': 1, 'label': 'Asymmetric (G:0, L:1)', 'color': 'purple', 'marker': 'D'},
            {'A_G': 1, 'A_L': 0, 'label': 'Asymmetric (G:1, L:0)', 'color': 'blue', 'marker': 'v'}
        ]

        for scenario in scenarios:
            row = risk_df[(risk_df['A_G'] == scenario['A_G']) & (risk_df['A_L'] == scenario['A_L'])]
            if not row.empty:
                # Plot threat point
                ax1.scatter(row['ThreatPoint_G'], row['ThreatPoint_L'],
                        color=scenario['color'], marker=scenario['marker'],
                        s=200, alpha=0.5, edgecolor='black', linewidth=2,
                        label=f"{scenario['label']} (Threat)")

                # Plot contract utility
                ax1.scatter(row['Utility_G'], row['Utility_L'],
                        color=scenario['color'], marker=scenario['marker'],
                        s=200, alpha=1.0, edgecolor='black', linewidth=2)

                # Draw line from threat point to contract
                ax1.plot([row['ThreatPoint_G'].iloc[0], row['Utility_G'].iloc[0]],
                        [row['ThreatPoint_L'].iloc[0], row['Utility_L'].iloc[0]],
                        color=scenario['color'], linestyle='--', alpha=0.5, linewidth=2)

        # Add Nash bargaining curve (approximate)
        # This would be the Pareto frontier in the utility space
        utility_g_range = np.linspace(risk_df['ThreatPoint_G'].min(), risk_df['Utility_G'].max(), 100)

        ax1.set_xlabel('Generator Utility', fontsize=self.labelsize)
        ax1.set_ylabel('Load Utility', fontsize=self.labelsize)
        ax1.set_title('Utility Space: Contract vs Threat Points', fontsize=self.titlesize)
        ax1.grid(True, alpha=0.3)
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Add annotations
        ax1.annotate('Feasible Region', xy=(risk_df['Utility_G'].mean(), risk_df['Utility_L'].mean()),
                    xytext=(risk_df['Utility_G'].mean() + 20, risk_df['Utility_L'].mean() + 20),
                    fontsize=12, ha='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.3))

        # 2. Nash Product Contours
        # Create a grid for contour plot
        util_g_min = min(risk_df['ThreatPoint_G'].min(), risk_df['Utility_G'].min()) - 10
        util_g_max = max(risk_df['ThreatPoint_G'].max(), risk_df['Utility_G'].max()) + 10
        util_l_min = min(risk_df['ThreatPoint_L'].min(), risk_df['Utility_L'].min()) - 10
        util_l_max = max(risk_df['ThreatPoint_L'].max(), risk_df['Utility_L'].max()) + 10

        g_range = np.linspace(util_g_min, util_g_max, 100)
        l_range = np.linspace(util_l_min, util_l_max, 100)
        G, L = np.meshgrid(g_range, l_range)

        # Calculate Nash product for each point (using average threat points)
        threat_g_avg = risk_df['ThreatPoint_G'].mean()
        threat_l_avg = risk_df['ThreatPoint_L'].mean()

        # Nash product = (U_G - T_G) * (U_L - T_L)
        nash_product = np.maximum(G - threat_g_avg, 0) * np.maximum(L - threat_l_avg, 0)

        # Plot contours
        contour = ax2.contour(G, L, nash_product, levels=20, cmap='viridis', alpha=0.6)
        ax2.clabel(contour, inline=True, fontsize=10)

        # Overlay actual points
        scatter = ax2.scatter(risk_df['Utility_G'], risk_df['Utility_L'],
                            c=risk_df['Nash_Product'], s=200, cmap='viridis',
                            edgecolor='black', linewidth=2)

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('Nash Product', fontsize=self.legendsize)

        ax2.set_xlabel('Generator Utility', fontsize=self.labelsize)
        ax2.set_ylabel('Load Utility', fontsize=self.labelsize)
        ax2.set_title('Nash Product Contours in Utility Space', fontsize=self.titlesize)
        ax2.grid(True, alpha=0.3)

        # Overall title
        fig.suptitle(f'{self.cm_data.contract_type}: Utility Space Analysis', fontsize=self.suptitlesize)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath, bbox_inches='tight', dpi=300)
            print(f"Utility space plot saved to {filepath}")
            plt.close(fig)
        else:
            plt.show()
