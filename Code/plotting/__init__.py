"""Plotting package for power system contract negotiation results.

Assembles the full Plotting_Class from domain-specific mixins.
"""
from .base import PlottingBase, cmap_red_green
from .sensitivity import SensitivityPlotsMixin
from .earnings import EarningsPlotsMixin
from .boundary import BoundaryPlotsMixin
from .barter import BarterPlotsMixin


class Plotting_Class(
    PlottingBase,
    SensitivityPlotsMixin,
    EarningsPlotsMixin,
    BoundaryPlotsMixin,
    BarterPlotsMixin,
):
    """Handles plotting of results from the power system contract negotiation simulation."""
    pass
