import logging
import numpy as np


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the package prefix stripped for cleaner output."""
    short_name = name.replace("ppa_symmetric_info.", "")
    return logging.getLogger(short_name)


def cvar_left(x: np.ndarray, prob: np.ndarray, alpha: float) -> float:
    """Expected value of x in the worst (1-alpha) probability mass (left-tail CVaR)."""
    tail = 1.0 - alpha
    order = np.argsort(x)
    x_s, p_s = x[order], prob[order]
    prev_cum = np.concatenate([[0.0], np.cumsum(p_s)[:-1]])
    weights = np.minimum(p_s, np.maximum(0.0, tail - prev_cum))
    return float((weights * x_s).sum() / tail)
