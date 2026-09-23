"""Joint surplus over risk preferences and over belief bias.

Grid convention from the sensitivity runner: rows are A_G (generator), columns are
A_L (buyer). For the bias sweep, rows are K_G_price and columns K_L_price.

Write the figures into figures/value_creation/:
    uv run python -m ppa_symmetric_info.plotting.value_creation
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from .io import PAPER_FIGURES, MissingResults, joint_surplus
from .panels import heatmap
from .style import SINGLE_COL_WIDTH, finalize, use_paper_style

NAME = "value_creation/joint_surplus"

_AL_SLICES = [0.25, 0.50, 0.75]


def build_joint_surplus_risk():
    """4.2.1a joint surplus over risk preferences. Single column: stands alone."""
    fig, ax = plt.subplots(figsize=(SINGLE_COL_WIDTH, SINGLE_COL_WIDTH * 0.85))
    w_risk = joint_surplus("default_pap", "risk_aversion")
    heatmap(
        ax,
        w_risk,
        label="Joint surplus  $\\delta_G+\\delta_L$  [MEUR]",
        xlabel="Buyer risk aversion $A_L$",
        ylabel="Generator risk aversion $A_G$",
    )
    finalize(fig)
    return fig


def build_joint_surplus_bias():
    """4.2.1b joint surplus over belief bias. Single column: stands alone."""
    fig, ax = plt.subplots(figsize=(SINGLE_COL_WIDTH, SINGLE_COL_WIDTH * 0.85))
    w_bias = joint_surplus("default_pap", "asymmetric_info")
    heatmap(
        ax,
        w_bias,
        label="Joint surplus  $\\delta_G+\\delta_L$  [MEUR]",
        xlabel="Buyer price bias $K^L_{price}$",
        ylabel="Generator price bias $K^G_{price}$",
    )
    finalize(fig)
    return fig


def main() -> None:
    use_paper_style()
    outdir = PAPER_FIGURES / "value_creation"
    outdir.mkdir(parents=True, exist_ok=True)

    builders = {
        "joint_surplus_risk": build_joint_surplus_risk,
        "joint_surplus_bias": build_joint_surplus_bias,
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
