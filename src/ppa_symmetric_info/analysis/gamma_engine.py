"""Closed-form (Gurobi-free) replica of the PAP / baseload Nash bargaining utilities.

Why this exists
---------------
The Gurobi model returns *a* solution but not *why*. This module rebuilds the same
objective analytically so every term can be inspected: the mean leg, the CVaR leg,
which scenarios sit in each party's tail, and how each of those responds to the
contract quantity. That decomposition is what explains the gamma corner and the
gamma > 1 overshoot.

Everything here is exact, not an approximation: the earnings are affine in the
contract quantity and in the strike, and the CVaR is the Rockafellar-Uryasev
lower-tail average, evaluated by sorting rather than by an LP. Solving the inner
maximisation over zeta analytically is what removes the need for a solver.

Units: strike S is carried in model units throughout (EUR/GWh * 1e-3); multiply by
1e3 for EUR/MWh. Production is GWh, earnings are MEUR.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))


# --------------------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------------------


def load_data(overrides=None):
    """Compose the Hydra config outside a @hydra.main entry point and build a DataLoader."""
    from hydra import compose, initialize_config_dir
    from ppa_symmetric_info.data_ops import DataLoader

    overrides = list(overrides or [])
    # paths.root normally resolves via ${hydra:runtime.cwd}, which only exists inside
    # a hydra run; pin it explicitly so the loader works from a plain script.
    overrides.append(f"++paths.root={REPO}")
    with initialize_config_dir(config_dir=str(REPO / "config"), version_base=None):
        cfg = compose(config_name="config", overrides=overrides)
    return DataLoader(cfg)


# --------------------------------------------------------------------------------------
# CVaR
# --------------------------------------------------------------------------------------


def cvar_lower(values: np.ndarray, prob: np.ndarray, alpha: float):
    """Lower-tail CVaR of `values` at confidence `alpha`, plus the tail weights.

    Returns (cvar, tail_weight) where tail_weight is a probability-like vector over the
    *original* scenario ordering, summing to (1 - alpha). It is the exact set of
    Lagrange weights the LP formulation would put on the binding CVaR constraints, so
    tail expectations built from it give exact directional derivatives of the CVaR
    (Rockafellar-Uryasev envelope theorem).
    """
    tail_mass = 1.0 - alpha
    order = np.argsort(values, kind="stable")
    v = values[order]
    p = prob[order]
    cum = np.cumsum(p)

    k = int(np.searchsorted(cum, tail_mass, side="left"))
    k = min(k, len(v) - 1)

    w_sorted = np.zeros_like(p)
    used = cum[k - 1] if k > 0 else 0.0
    if k > 0:
        w_sorted[:k] = p[:k]
    w_sorted[k] = max(tail_mass - used, 0.0)

    cvar = float((w_sorted * v).sum() / tail_mass)

    tail_weight = np.zeros_like(prob)
    tail_weight[order] = w_sorted
    return cvar, tail_weight


def tail_mean(x: np.ndarray, tail_weight: np.ndarray, alpha: float) -> float:
    """E[x | tail] using the weights returned by cvar_lower."""
    return float((tail_weight * x).sum() / (1.0 - alpha))


# --------------------------------------------------------------------------------------
# The model
# --------------------------------------------------------------------------------------


@dataclass
class Marginals:
    """Decomposition of du_i/d(quantity) into its mean and CVaR legs."""

    mean_G: float
    cvar_G: float
    du_G: float
    mean_L: float
    cvar_L: float
    du_L: float


class PapNash:
    """Pay-as-Produced Nash bargaining, evaluated in closed form.

    Per-scenario earnings (matching model.py `_build_pap_cons` exactly):

        pi_G(s) = (1 - g) * Ync_G[s]  +  g * S * B[s]
        pi_L(s) =            Ync_L[s] +  g * (Y_L[s] - S * B[s])

    where
        Ync_G[s] : generator merchant earnings, no contract
        Ync_L[s] : load merchant cost (negative), no contract
        B[s]     : discounted contracted production (the random volume S multiplies)
        Y_L[s]   : the load's belief of the captured revenue on that same volume
    """

    def __init__(self, data, A_G=None, A_L=None, tau_L=None, alpha=None):
        self.prob = np.asarray(data.prob, dtype=float)
        self.prob = self.prob / self.prob.sum()

        self.Ync_G = np.asarray(data.earnings_nc_G, dtype=float)
        self.Ync_L = np.asarray(data.earnings_nc_L, dtype=float)
        self.B = np.asarray(data.pap_prod_disc_G, dtype=float)
        self.B_L = np.asarray(data.pap_prod_disc_L, dtype=float)
        self.Y_L = np.asarray(data.pap_gamma_coeff_L, dtype=float)

        self.A_G = data.A_G if A_G is None else A_G
        self.A_L = data.A_L if A_L is None else A_L
        self.tau_L = data.tau_L if tau_L is None else tau_L
        self.tau_G = 1.0 - self.tau_L
        self.alpha = data.alpha if alpha is None else alpha

        self.S_lo = data.strikeprice_min
        self.S_hi = data.strikeprice_max

        # Disagreement points are the utilities at gamma = 0, recomputed here so that
        # A_G / A_L can be swept without reloading data.
        self.d_G = self._utility(self.Ync_G, self.A_G)[0]
        self.d_L = self._utility(self.Ync_L, self.A_L)[0]

    # -- primitives ---------------------------------------------------------------

    def _utility(self, pi: np.ndarray, A: float):
        mean = float((self.prob * pi).sum())
        cvar, tw = cvar_lower(pi, self.prob, self.alpha)
        return (1 - A) * mean + A * cvar, mean, cvar, tw

    def earnings(self, gamma: float, S: float):
        pi_G = (1 - gamma) * self.Ync_G + gamma * S * self.B
        pi_L = self.Ync_L + gamma * (self.Y_L - S * self.B_L)
        return pi_G, pi_L

    def utilities(self, gamma: float, S: float):
        pi_G, pi_L = self.earnings(gamma, S)
        u_G, mean_G, cvar_G, tw_G = self._utility(pi_G, self.A_G)
        u_L, mean_L, cvar_L, tw_L = self._utility(pi_L, self.A_L)
        return dict(
            u_G=u_G,
            u_L=u_L,
            mean_G=mean_G,
            mean_L=mean_L,
            cvar_G=cvar_G,
            cvar_L=cvar_L,
            tw_G=tw_G,
            tw_L=tw_L,
            delta_G=u_G - self.d_G,
            delta_L=u_L - self.d_L,
        )

    def nash(self, gamma: float, S: float) -> float:
        """Asymmetric Nash objective tau_G*ln(delta_G) + tau_L*ln(delta_L)."""
        r = self.utilities(gamma, S)
        if r["delta_G"] <= 1e-12 or r["delta_L"] <= 1e-12:
            return -np.inf
        return self.tau_G * np.log(r["delta_G"]) + self.tau_L * np.log(r["delta_L"])

    # -- marginals ----------------------------------------------------------------

    def marginals(self, gamma: float, S: float) -> Marginals:
        """Exact d u_i / d gamma, split into the mean leg and the CVaR leg.

        d pi_G / d gamma = S*B - Ync_G      (per scenario)
        d pi_L / d gamma = Y_L - S*B_L      (per scenario)

        The mean leg is the probability-weighted average of those; the CVaR leg is the
        same quantity averaged over that party's tail only.
        """
        r = self.utilities(gamma, S)
        gG = S * self.B - self.Ync_G
        gL = self.Y_L - S * self.B_L

        mean_G = float((self.prob * gG).sum())
        mean_L = float((self.prob * gL).sum())
        cv_G = tail_mean(gG, r["tw_G"], self.alpha)
        cv_L = tail_mean(gL, r["tw_L"], self.alpha)

        return Marginals(
            mean_G=mean_G,
            cvar_G=cv_G,
            du_G=(1 - self.A_G) * mean_G + self.A_G * cv_G,
            mean_L=mean_L,
            cvar_L=cv_L,
            du_L=(1 - self.A_L) * mean_L + self.A_L * cv_L,
        )

    # -- optimisation --------------------------------------------------------------

    def best_S(self, gamma: float, n_grid: int = 600, n_refine: int = 60):
        """Maximise the Nash objective over S at fixed gamma (grid + golden refine)."""
        grid = np.linspace(self.S_lo, self.S_hi, n_grid)
        vals = np.array([self.nash(gamma, s) for s in grid])
        if not np.isfinite(vals).any():
            return np.nan, -np.inf
        i = int(np.nanargmax(vals))
        lo = grid[max(i - 1, 0)]
        hi = grid[min(i + 1, n_grid - 1)]
        # golden-section refine on the bracketing interval
        phi = (np.sqrt(5) - 1) / 2
        a, b = lo, hi
        c, d_ = b - phi * (b - a), a + phi * (b - a)
        fc, fd = self.nash(gamma, c), self.nash(gamma, d_)
        for _ in range(n_refine):
            if fc > fd:
                b, d_, fd = d_, c, fc
                c = b - phi * (b - a)
                fc = self.nash(gamma, c)
            else:
                a, c, fc = c, d_, fd
                d_ = a + phi * (b - a)
                fd = self.nash(gamma, d_)
        s_star = (a + b) / 2
        return s_star, self.nash(gamma, s_star)

    def sweep_gamma(self, gammas):
        """For each gamma, re-optimise S and report the full decomposition."""
        rows = []
        for g in gammas:
            s, obj = self.best_S(g)
            if not np.isfinite(obj):
                rows.append(
                    dict(
                        gamma=g,
                        S=np.nan,
                        S_EUR_MWh=np.nan,
                        nash_obj=-np.inf,
                        delta_G=np.nan,
                        delta_L=np.nan,
                        nash_product=np.nan,
                        u_G=np.nan,
                        u_L=np.nan,
                        mean_G=np.nan,
                        cvar_G=np.nan,
                        mean_L=np.nan,
                        cvar_L=np.nan,
                        dmean_G=np.nan,
                        dcvar_G=np.nan,
                        du_G=np.nan,
                        dmean_L=np.nan,
                        dcvar_L=np.nan,
                        du_L=np.nan,
                    )
                )
                continue
            r = self.utilities(g, s)
            m = self.marginals(g, s)
            rows.append(
                dict(
                    gamma=g,
                    S=s,
                    S_EUR_MWh=s * 1e3,
                    nash_obj=obj,
                    delta_G=r["delta_G"],
                    delta_L=r["delta_L"],
                    nash_product=r["delta_G"] * r["delta_L"],
                    u_G=r["u_G"],
                    u_L=r["u_L"],
                    mean_G=r["mean_G"],
                    cvar_G=r["cvar_G"],
                    mean_L=r["mean_L"],
                    cvar_L=r["cvar_L"],
                    dmean_G=m.mean_G,
                    dcvar_G=m.cvar_G,
                    du_G=m.du_G,
                    dmean_L=m.mean_L,
                    dcvar_L=m.cvar_L,
                    du_L=m.du_L,
                )
            )
        return rows

    def argmax_gamma(self, lo=0.0, hi=3.0, n=121, refine=40):
        """Locate gamma* by coarse scan then golden-section refine."""
        grid = np.linspace(lo, hi, n)
        vals = np.array([self.best_S(g)[1] for g in grid])
        if not np.isfinite(vals).any():
            return np.nan, np.nan, -np.inf
        i = int(np.nanargmax(vals))
        a = grid[max(i - 1, 0)]
        b = grid[min(i + 1, n - 1)]
        phi = (np.sqrt(5) - 1) / 2
        c, d_ = b - phi * (b - a), a + phi * (b - a)
        fc, fd = self.best_S(c)[1], self.best_S(d_)[1]
        for _ in range(refine):
            if fc > fd:
                b, d_, fd = d_, c, fc
                c = b - phi * (b - a)
                fc = self.best_S(c)[1]
            else:
                a, c, fc = c, d_, fd
                d_ = a + phi * (b - a)
                fd = self.best_S(d_)[1]
        g_star = (a + b) / 2
        s_star, obj = self.best_S(g_star)
        return g_star, s_star, obj

    # -- diagnostics ----------------------------------------------------------------

    def tail_profile(self, gamma: float, S: float):
        """Which scenarios sit in each party's tail, and what they look like.

        The identity of the tail set is the whole story behind the gamma corner: the
        generator's tail flips from low-revenue scenarios to high-revenue scenarios as
        gamma crosses 1, because the merchant coefficient (1 - gamma) changes sign.
        """
        r = self.utilities(gamma, S)
        capture = self.Ync_G / self.B * 1e3  # EUR/MWh realised capture price
        out = {}
        for who, tw in (("G", r["tw_G"]), ("L", r["tw_L"])):
            m = tw > 0
            out[who] = dict(
                n_tail=int(m.sum()),
                capture_price=tail_mean(capture, tw, self.alpha),
                production=tail_mean(self.B, tw, self.alpha),
                merchant=tail_mean(self.Ync_G, tw, self.alpha),
            )
        out["E_capture_price"] = float((self.prob * capture).sum())
        out["E_capture_ratio"] = (
            float((self.prob * self.Ync_G).sum() / (self.prob * self.B).sum()) * 1e3
        )
        return out


class BaseloadNash(PapNash):
    """Baseload contract: a fixed volume M replaces the stochastic share gamma.

        pi_G(s) = Ync_G[s] + (Dsum*S - Lam_G[s]) * M
        pi_L(s) = Ync_L[s] + (Lam_L[s] - Dsum*S) * M

    The strike multiplies a deterministic M, so the strike-direction loci in utility
    space are straight with slope -1 -- the structural difference from PAP.
    """

    def __init__(self, data, A_G=None, A_L=None, tau_L=None, alpha=None):
        super().__init__(data, A_G=A_G, A_L=A_L, tau_L=tau_L, alpha=alpha)
        self.Lam_G = np.asarray(data.lambda_disc_G, dtype=float)
        self.Lam_L = np.asarray(data.lambda_disc_L, dtype=float)
        self.Dsum_G = float(data.disc_G_sum)
        self.Dsum_L = float(data.disc_L_sum)
        self.M_lo = data.contract_amount_min
        self.M_hi = data.contract_amount_max

    def earnings(self, M: float, S: float):
        pi_G = self.Ync_G + (self.Dsum_G * S - self.Lam_G) * M
        pi_L = self.Ync_L + (self.Lam_L - self.Dsum_L * S) * M
        return pi_G, pi_L

    def marginals(self, M: float, S: float) -> Marginals:
        r = self.utilities(M, S)
        gG = self.Dsum_G * S - self.Lam_G
        gL = self.Lam_L - self.Dsum_L * S
        mean_G = float((self.prob * gG).sum())
        mean_L = float((self.prob * gL).sum())
        cv_G = tail_mean(gG, r["tw_G"], self.alpha)
        cv_L = tail_mean(gL, r["tw_L"], self.alpha)
        return Marginals(
            mean_G=mean_G,
            cvar_G=cv_G,
            du_G=(1 - self.A_G) * mean_G + self.A_G * cv_G,
            mean_L=mean_L,
            cvar_L=cv_L,
            du_L=(1 - self.A_L) * mean_L + self.A_L * cv_L,
        )
