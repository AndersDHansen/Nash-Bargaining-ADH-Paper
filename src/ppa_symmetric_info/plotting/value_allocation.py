"""Section 4.3, value allocation: how is the surplus split, and on what terms?

  symmetric NBS:    strike and surplus share against relative risk aversion
  bargaining power: the same against tau_L

The recurring message is that the strike is the splitting device while the quantity
sizes the pie, so these panels pair the strike with the surplus SHARE rather than
with the surplus level.

Write the figures into figures/value_allocation/:
    uv run python -m ppa_symmetric_info.plotting.value_allocation
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .io import PAPER_FIGURES, MissingResults, load_combined, load_grid, surplus_share_G
from .panels import heatmap, slices
from .style import COL_G, COL_G_DARK, COL_L, finalize, use_paper_style

_AL_SLICES = [0.25, 0.50, 0.75]
_TAUS = [0.0, 0.5, 1.0]


def build_symmetric_nbs(experiment: str = "default_pap"):
    """4.3.1 strike and surplus split across the risk-aversion grid, tau_L fixed."""
    S = load_grid(experiment, "risk_aversion", "S_EUR_MWh")
    share = surplus_share_G(experiment, "risk_aversion")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    heatmap(
        axes[0, 0],
        S,
        label="Strike $S^*$ [EUR/MWh]",
        title="(a)  Negotiated strike",
        xlabel="Buyer risk aversion $A_L$",
        ylabel="Generator risk aversion $A_G$",
    )
    slices(
        axes[0, 1],
        S,
        at_columns=_AL_SLICES,
        label_fmt="$A_L$ = {:.2f}",
        xlabel="Generator risk aversion $A_G$",
        ylabel="Strike $S^*$ [EUR/MWh]",
        title="(b)  Strike slices",
    )

    heatmap(
        axes[1, 0],
        share,
        label="Generator share of joint surplus [-]",
        center=0.5,
        title="(c)  Surplus allocation",
        xlabel="Buyer risk aversion $A_L$",
        ylabel="Generator risk aversion $A_G$",
    )
    slices(
        axes[1, 1],
        share,
        at_columns=_AL_SLICES,
        label_fmt="$A_L$ = {:.2f}",
        xlabel="Generator risk aversion $A_G$",
        ylabel="Generator share of surplus [-]",
        title="(d)  Allocation slices",
    )
    axes[1, 1].axhline(0.5, color="k", linestyle=":", linewidth=0.9, alpha=0.6)

    finalize(fig)
    return fig


def build_bargaining_power(experiment: str = "default_pap"):
    """4.3.2 strike and surplus split against tau_L, one line per A_L."""
    df = load_combined(experiment, "bargaining_power")
    qty = "gamma" if experiment.endswith("pap") else "M_MWh_h"
    qty_label = (
        "Contract share $\\gamma$ [-]" if qty == "gamma" else "Contract volume $M$ [MW]"
    )

    df = df.copy()
    df["share_G"] = df["delta_G"] / (df["delta_G"] + df["delta_L"])

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    colours = [COL_G, COL_G_DARK, COL_L]

    for k, al in enumerate(_AL_SLICES):
        sub = df[np.isclose(df["A_L"], al)].sort_values("tau_L")
        if sub.empty:
            continue
        axes[0].plot(
            sub["tau_L"], sub["S_EUR_MWh"], color=colours[k], label=f"$A_L$ = {al:.2f}"
        )
        axes[1].plot(
            sub["tau_L"], sub["share_G"], color=colours[k], label=f"$A_L$ = {al:.2f}"
        )
        if qty in sub:
            axes[2].plot(
                sub["tau_L"], sub[qty], color=colours[k], label=f"$A_L$ = {al:.2f}"
            )

    for ax, ylab, ttl in (
        (axes[0], "Strike $S^*$ [EUR/MWh]", "(a)  Strike moves with power"),
        (axes[1], "Generator share of surplus [-]", "(b)  So does the split"),
        (axes[2], qty_label, "(c)  Quantity barely moves"),
    ):
        ax.set_xlabel("Buyer bargaining power $\\tau_L$")
        ax.set_ylabel(ylab)
        ax.set_title(ttl)
        ax.axvline(0.5, color="k", linestyle=":", linewidth=0.9, alpha=0.6)
        ax.legend(frameon=False, fontsize=8)

    finalize(fig)
    return fig


def main() -> None:
    use_paper_style()
    outdir = PAPER_FIGURES / "value_allocation"
    outdir.mkdir(parents=True, exist_ok=True)

    builders = {
        "symmetric_nbs": build_symmetric_nbs,
        "bargaining_power": build_bargaining_power,
    }
    for name, builder in builders.items():
        try:
            fig = builder()
        except MissingResults as e:
            print(f"  skipped  {name}: {e}")
            continue
        fig.savefig(outdir / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(outdir / f"{name}.png", dpi=300, bbox_inches="tight")
        print(f"  wrote    {outdir / name}.pdf")


if __name__ == "__main__":
    main()
