"""Single place where figure styling is decided.

Wraps `soft_style` so figures import from here and the underlying style module can
be replaced without touching every script.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from .soft_style import (  # noqa: F401
    BAR_PALETTE,
    CMAP_DIVERGING,
    CMAP_SEQUENTIAL,
    CMAP_SEQUENTIAL_BLUE,
    LINE_PALETTE,
    MULTILINE_PALETTE,
    NEUTRAL,
    configure_style,
    figure_title,
    panel_subtitle,
    save_figure,
)

# IEEEtran journal (see main.tex): single column ~3.5in, full double-column spread
# ~7.16in. Default to single-column width -- use FULL_WIDTH only when a figure
# genuinely needs multiple panels side by side to make its point (e.g. a direct
# baseload-vs-PAP comparison), not as a default layout.
SINGLE_COL_WIDTH = 3.5
FULL_WIDTH = 7.16

# Party colours, fixed across the whole paper: blue is the generator, coral the buyer.
COL_G = LINE_PALETTE["blue"]
COL_G_DARK = "#1A5B81"
COL_L = BAR_PALETTE["coral"]
COL_L_DARK = "#8B1515"
NEUTRAL_GREY = NEUTRAL if isinstance(NEUTRAL, str) else "#9A9A9A"

_configured = False


def use_paper_style() -> None:
    """Idempotent style setup. Every figure module calls this via the driver.

    `configure_style()` is the "nice-figures"/research-blog register: muted
    brownish-gray ink (`NEUTRAL["label"]` etc.), not black. Override that back to
    plain black ink and Arial-first fonts here, matching the paper's original
    plotting style (case_study.py, which never used soft_style, is black by
    matplotlib's own default) -- without touching soft_style.py itself, since it
    may still be used elsewhere for its original blog-style purpose.
    """
    global _configured
    if not _configured:
        configure_style()
        plt.rcParams.update(
            {
                "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
                "text.color": "black",
                "axes.titlecolor": "black",
                "axes.labelcolor": "black",
                "xtick.color": "black",
                "ytick.color": "black",
                "axes.edgecolor": "black",
                "legend.labelcolor": "black",
            }
        )
        _configured = True


def finalize(fig, *, tight: bool = True) -> None:
    """Last pass applied to every figure before saving."""
    if tight:
        fig.tight_layout()
