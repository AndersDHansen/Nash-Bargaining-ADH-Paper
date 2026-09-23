"""Everything that decides how a figure looks.

Two rules keep the results section readable. A colour always means the same party,
and a line style always means the same settlement structure. Both live here, so a
change propagates to all six figures instead of being re-decided in each.
"""

from __future__ import annotations

import matplotlib as mpl

# ---------------------------------------------------------------------------
# Okabe-Ito, colourblind-safe and legible in greyscale print.
# ---------------------------------------------------------------------------
ORANGE = "#e69f00"
CYAN = "#56b4e9"
GREEN = "#009e73"
YELLOW = "#f0e442"
BLUE = "#0072b2"
RED = "#d55e00"
PINK = "#cc79a7"
GREY = "#4d4d4d"

# ---------------------------------------------------------------------------
# Semantic roles. Use these, never the raw colours, so the meaning is at the
# call site: colour=GENERATOR reads, colour=BLUE does not.
# ---------------------------------------------------------------------------
GENERATOR = BLUE
BUYER = ORANGE
NEUTRAL = GREY  # merchant baseline, caps, reference lines

# Settlement structure is carried by line style, so a figure can show both
# structures for both parties without needing four colours.
BASELOAD = {"linestyle": "-", "linewidth": 1.4}
PAP = {"linestyle": "--", "linewidth": 1.4}

# Risk-aversion slices, where three curves share one panel.
SLICE_COLOURS = [CYAN, BLUE, GREY]

CMAP_SEQUENTIAL = "viridis"
CMAP_DIVERGING = "RdBu_r"  # only with a centred norm, e.g. a surplus share around 0.5

BAND_ALPHA = {"inner": 0.35, "outer": 0.18}  # P10-P90 and P5-P95

# ---------------------------------------------------------------------------
# Geometry. The manuscript is IEEEtran today and elsarticle for EJOR, which have
# different column widths -- change these two numbers, not the figure methods.
# ---------------------------------------------------------------------------
SINGLE_COL_WIDTH = 3.5
FULL_WIDTH = 7.16
DPI = 300


def figsize(width: str = "full", ratio: float = 0.62) -> tuple[float, float]:
    """Figure size in inches. `width` is 'full' or 'single'; `ratio` is height/width."""
    w = FULL_WIDTH if width == "full" else SINGLE_COL_WIDTH
    return (w, w * ratio)


def apply_style() -> None:
    """Set the rcParams every figure in the paper shares. Idempotent."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "legend.frameon": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "lines.linewidth": 1.4,
            "figure.dpi": 110,
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,  # embed as TrueType, not Type 3: required by most journals
            "ps.fonttype": 42,
        }
    )
