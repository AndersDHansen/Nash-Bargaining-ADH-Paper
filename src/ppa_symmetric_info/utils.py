import logging
import numpy as np


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the package prefix stripped for cleaner output."""
    short_name = name.replace("ppa_symmetric_info.", "")
    return logging.getLogger(short_name)


def cvar_left(x: np.ndarray, prob: np.ndarray, alpha: float) -> float:
    """Expected value of x in the worst (1-alpha) probability mass (left-tail CVaR)."""
    return _tail_avg(x, x, prob, alpha)


def _tail_avg(value: np.ndarray, order_by: np.ndarray, prob: np.ndarray, alpha: float) -> float:
    """Prob-weighted mean of `value` over the worst (1-alpha) mass ranked by `order_by`.

    Generalises cvar_left: when value is order_by it IS the left-tail CVaR. Used for
    reservation strikes, where the tail is selected by a party's no-contract earnings
    but the averaged quantity is the discounted price sum.
    """
    tail = 1.0 - alpha
    order = np.argsort(order_by)
    v_s, p_s = value[order], prob[order]
    prev_cum = np.concatenate([[0.0], np.cumsum(p_s)[:-1]])
    weights = np.minimum(p_s, np.maximum(0.0, tail - prev_cum))
    return float((weights * v_s).sum() / tail)
