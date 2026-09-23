"""Compute and explain the PAP contract share gamma* (and the baseload volume M*).

Modes
-----
    uv run python analysis/compute_gamma.py toy         hand-checkable 5-scenario examples
    uv run python analysis/compute_gamma.py sweep       gamma sweep on the real scenario set
    uv run python analysis/compute_gamma.py foc         verify the break-even-crossing rule
    uv run python analysis/compute_gamma.py conditions  evaluate C1 / C2 numerically
    uv run python analysis/compute_gamma.py grid        gamma* over the A_G x A_L grid
    uv run python analysis/compute_gamma.py spread      buy-back-premium fix
    uv run python analysis/compute_gamma.py all

Extra Hydra overrides can be appended, e.g.

    uv run python analysis/compute_gamma.py sweep experiment.A_G=0.25 experiment.load_scale=1.0

Everything is solved in closed form (no Gurobi). The engine is verified against the
solver to 1e-6 in `gamma_engine`, so these numbers are the model's, not an approximation.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from ppa_symmetric_info.analysis.gamma_engine import (
    BaseloadNash,
    PapNash,
    load_data,
    tail_mean,
)  # noqa: E402


# ======================================================================================
# helpers
# ======================================================================================


def blend(m, X, tw, A):
    """The tail-adjusted expectation <X>_i = (1-A)E[X] + A E[X|tail_i]."""
    return (1 - A) * float((m.prob * X).sum()) + A * tail_mean(X, tw, m.alpha)


def breakevens(m, gamma, S):
    """Each party's break-even strike y_i/b_i in EUR/MWh, at the given contract point."""
    r = m.utilities(gamma, S)
    b_G = blend(m, m.B, r["tw_G"], m.A_G)
    b_L = blend(m, m.B_L, r["tw_L"], m.A_L)
    y_G = blend(m, m.Ync_G, r["tw_G"], m.A_G)
    y_L = blend(m, m.Y_L, r["tw_L"], m.A_L)
    return dict(
        b_G=b_G, b_L=b_L, y_G=y_G, y_L=y_L, SR_G=y_G / b_G * 1e3, SU_L=y_L / b_L * 1e3
    )


def toy_data(
    price,
    production,
    load,
    load_cr=1.0,
    A_G=0.5,
    A_L=0.5,
    alpha=0.8,
    tau_L=0.5,
    prob=None,
):
    """Build a minimal one-year toy dataset in the shape PapNash expects.

    price      EUR/MWh per scenario
    production GWh per scenario (the generator's output)
    load       GWh per scenario (the buyer's consumption)
    Earnings come out in MEUR:  GWh * EUR/MWh / 1000.
    """
    price = np.asarray(price, float)
    production = np.asarray(production, float)
    load = np.asarray(load, float) * np.ones_like(price)
    n = len(price)
    prob = np.full(n, 1.0 / n) if prob is None else np.asarray(prob, float)

    Y_G = production * price / 1e3  # merchant revenue, MEUR
    Y_L = -load * load_cr * price / 1e3  # merchant cost, MEUR (negative)

    return SimpleNamespace(
        prob=prob,
        earnings_nc_G=Y_G,
        earnings_nc_L=Y_L,
        pap_prod_disc_G=production,
        pap_prod_disc_L=production,
        pap_gamma_coeff_L=Y_G,  # symmetric information
        A_G=A_G,
        A_L=A_L,
        tau_L=tau_L,
        alpha=alpha,
        strikeprice_min=0.0,
        strikeprice_max=0.5,
    )


# ======================================================================================
# modes
# ======================================================================================


def mode_toy():
    print("=" * 96)
    print("TOY A — perfectly matched buyer, flat production: gamma* = 1 exactly")
    print("=" * 96)
    price = [40, 60, 70, 80, 120]
    prod = [100, 100, 100, 100, 100]
    print(
        "5 equiprobable scenarios, one year, alpha=0.8 so the tail is exactly the worst one."
    )
    print(f"  price  [EUR/MWh] : {price}")
    print(f"  output [GWh]     : {prod}   (flat)")
    print(f"  buyer  [GWh]     : {prod}   (consumes exactly what the plant makes)")
    print("  A_G = A_L = 0.5,  tau_L = 0.5")

    d = toy_data(price, prod, prod)
    m = PapNash(d)
    print(f"\n  merchant revenue Y_G  = {list(np.round(m.Ync_G, 2))} MEUR")
    print(f"  merchant cost    Y_L  = {list(np.round(m.Ync_L, 2))} MEUR")
    print(
        f"  E[Y_G] = {float((m.prob * m.Ync_G).sum()):.2f}, worst = {m.Ync_G.min():.2f}"
        f"  ->  d_G = 0.5*{float((m.prob * m.Ync_G).sum()):.2f} + 0.5*{m.Ync_G.min():.2f}"
        f" = {m.d_G:.2f} MEUR"
    )
    print(
        f"  E[Y_L] = {float((m.prob * m.Ync_L).sum()):.2f}, worst = {m.Ync_L.min():.2f}"
        f"  ->  d_L = {m.d_L:.2f} MEUR"
    )
    print(
        "\n  Note the tails are DISJOINT: the generator's worst case is the LOW price"
    )
    print(
        "  scenario, the buyer's worst case is the HIGH price scenario. That disjointness"
    )
    print(
        "  is the entire source of gains from trade -- the mean leg is exactly zero-sum."
    )

    print(
        f"\n{'gamma':>7} {'S*[E/MWh]':>10} {'delta_G':>9} {'delta_L':>9} {'Nash prod':>10}"
        f" {'G tail scen':>12} {'L tail scen':>12}"
    )
    print("-" * 96)
    for g in [0.0, 0.5, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5]:
        s, o = m.best_S(g)
        if not np.isfinite(o):
            print(f"{g:>7.2f} {'--':>10} {'no feasible contract':>44}")
            continue
        r = m.utilities(g, s)
        gt = int(np.argmax(r["tw_G"] > 0)) + 1
        lt = int(np.argmax(r["tw_L"] > 0)) + 1
        print(
            f"{g:>7.2f} {s * 1e3:>10.3f} {r['delta_G']:>9.4f} {r['delta_L']:>9.4f} "
            f"{r['delta_G'] * r['delta_L']:>10.4f} {gt:>12d} {lt:>12d}"
        )
    g, s, _ = m.argmax_gamma(0.0, 3.0, n=121, refine=40)
    print(f"\n  gamma* = {g:.4f}   S* = {s * 1e3:.3f} EUR/MWh")
    print(
        "  Hand check at gamma=1: pi_G = S*100/1000 in EVERY scenario -- the generator is"
    )
    print(
        "  perfectly hedged, payoff deterministic. u_G = 0.1*S, delta_G = 0.1*S - 5.70,"
    )
    print(
        "  delta_L = 9.70 - 0.1*S. Nash product (0.1S-5.7)(9.7-0.1S) peaks at 0.1S = 7.70,"
    )
    print(
        "  i.e. S = 77.00 EUR/MWh, giving 2.00 x 2.00 = 4.00. Matches the table above."
    )
    print(
        "  Watch the tail columns: G's tail is scenario 1 (low price) while gamma<1 and"
    )
    print("  jumps to scenario 5 (high price) once gamma>1. That flip is the brake.")

    print("\n" + "=" * 96)
    print("TOY B — perturbing the baseline one ingredient at a time")
    print("=" * 96)
    print(
        "gamma* = 1 in Toy A is a knife-edge: it holds because the buyer consumes exactly"
    )
    print("what the plant produces in every scenario, so gamma=1 makes BOTH payoffs")
    print(
        "deterministic. Perturb that and gamma* moves. What moves it, and which way:\n"
    )

    flat = [100.0] * 5
    cases = [
        ("baseline (buyer = plant output)", dict()),
        ("buyer 2x the plant", dict(load=[200.0] * 5)),
        ("buyer 0.2x the plant", dict(load=[20.0] * 5)),
        ("volume risk, mild (98-102 GWh)", dict(production=[102, 101, 100, 99, 98])),
        ("volume risk, strong (70-130 GWh)", dict(production=[130, 110, 100, 90, 70])),
        ("buyer peakier price shape (cr=1.2)", dict(load_cr=1.2)),
        ("generator less risk-averse A_G=0.2", dict(A_G=0.2)),
        ("generator more risk-averse A_G=0.8", dict(A_G=0.8)),
        ("buyer more risk-averse A_L=0.8", dict(A_L=0.8)),
        (
            "buyer 2x + mild volume risk",
            dict(load=[200.0] * 5, production=[102, 101, 100, 99, 98]),
        ),
        (
            "buyer 2x + mild vol + A_G=0.25",
            dict(load=[200.0] * 5, production=[102, 101, 100, 99, 98], A_G=0.25),
        ),
    ]
    print(f"{'perturbation':<38} {'gamma*':>9} {'S*[E/MWh]':>11}")
    print("-" * 62)
    for label, ov in cases:
        kw = dict(price=price, production=flat, load=flat, A_G=0.5, A_L=0.5, alpha=0.8)
        kw.update(ov)
        mm = PapNash(toy_data(**kw))
        gg, ss, _ = mm.argmax_gamma(0.0, 4.0, n=161, refine=40)
        print(f"{label:<38} {gg:>9.4f} {ss * 1e3:>11.3f}")

    print("\n  Read the table this way:")
    print(
        "  * BUYER SIZE is the dominant lever. gamma* tracks how much hedge the buyer"
    )
    print(
        "    wants relative to how much the plant can physically supply. A buyer twice"
    )
    print(
        "    the plant's size drives gamma* to ~1.86 -- it wants more MWh hedged than"
    )
    print("    the plant makes, and nothing in the model forbids selling them.")
    print(
        "  * VOLUME RISK pulls gamma* down: the more the plant's output varies, the less"
    )
    print("    a production-linked contract hedges, so less of it is written.")
    print("  * RISK AVERSION on its own does NOT move gamma* at all here (all exactly")
    print(
        "    1.0000) -- it only moves the STRIKE. Risk aversion re-prices the deal; it"
    )
    print("    does not resize it. It only starts to move gamma* once the buyer/plant")
    print("    symmetry is already broken (last two rows).")
    print("  This is the cleanest statement of the gamma>1 mechanism: it is a")
    print("  BUYER-DEMAND-EXCEEDS-PLANT-OUTPUT result, not a risk-appetite result.")


def mode_sweep(ov):
    d = load_data(["experiment=default_pap", "experiment.sim_name=analysis"] + ov)
    m = PapNash(d)
    print("=" * 104)
    print("GAMMA SWEEP — S re-optimised at every gamma, contract bounds ignored")
    print("=" * 104)
    print(
        f"A_G={m.A_G}  A_L={m.A_L}  tau_L={m.tau_L}  alpha={m.alpha}  "
        f"K_L_price={d.K_L_price}  load_scale={d.load_scale}"
    )
    Ecap = float((m.prob * m.Ync_G).sum()) / float((m.prob * m.B).sum()) * 1e3
    print(
        f"E[capture price] = {Ecap:.3f} EUR/MWh   d_G = {m.d_G:.3f}   d_L = {m.d_L:.3f}\n"
    )

    hdr = (
        f"{'gamma':>6} {'S*[E/MWh]':>10} {'NashProd':>10} | "
        f"{'dmean_G':>9} {'dcvar_G':>9} {'du_G':>9} | "
        f"{'dmean_L':>9} {'dcvar_L':>9} {'du_L':>9}"
    )
    print(hdr)
    print("-" * len(hdr))
    for g in np.round(np.arange(0.1, 2.01, 0.1), 3):
        s, o = m.best_S(g)
        if not np.isfinite(o):
            continue
        r = m.utilities(g, s)
        mg = m.marginals(g, s)
        print(
            f"{g:>6.2f} {s * 1e3:>10.3f} {r['delta_G'] * r['delta_L']:>10.3f} | "
            f"{mg.mean_G:>9.4f} {mg.cvar_G:>9.4f} {mg.du_G:>9.4f} | "
            f"{mg.mean_L:>9.4f} {mg.cvar_L:>9.4f} {mg.du_L:>9.4f}"
        )
    g, s, _ = m.argmax_gamma(0.0, 4.0)
    print(f"\ngamma* = {g:.4f}   S* = {s * 1e3:.3f} EUR/MWh")
    print(
        f"mean legs at the optimum: dmean_G + dmean_L = "
        f"{m.marginals(g, s).mean_G + m.marginals(g, s).mean_L:+.4e}"
        "   (exactly zero under symmetric information)"
    )

    print("\nTAIL COMPOSITION — the flip that stops gamma growing")
    print(f"{'gamma':>7} {'G-tail capture':>16} {'L-tail capture':>16}   (EUR/MWh)")
    print("-" * 60)
    for g_ in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
        s_, _ = m.best_S(g_)
        tp = m.tail_profile(g_, s_)
        print(
            f"{g_:>7.2f} {tp['G']['capture_price']:>16.3f} {tp['L']['capture_price']:>16.3f}"
        )
    print(f"{'  E[.]':>7} {Ecap:>16.3f} {Ecap:>16.3f}")


def mode_foc(ov):
    print("=" * 104)
    print("INTERIOR-OPTIMUM RULE — gamma* is where the two break-even strikes cross")
    print("=" * 104)
    print("Stationarity of the Nash program gives two conditions:")
    print(
        "   (i)  tau_G*b_G/delta_G = tau_L*b_L/delta_L      -> fixes S* (splits the surplus)"
    )
    print(
        "   (ii) y_G/b_G           = y_L/b_L                -> fixes gamma* (sizes the deal)"
    )
    print(
        "Condition (ii) says the viable strike band [S^R*, S^U*] collapses to a point.\n"
    )
    d = load_data(["experiment=default_pap", "experiment.sim_name=analysis"] + ov)
    m = PapNash(d)
    g, s, _ = m.argmax_gamma(0.0, 5.0, n=81, refine=30)
    print(f"{'gamma':>8} {'S*[E/MWh]':>10} {'S^R*_G':>10} {'S^U*_L':>10} {'gap':>10}")
    print("-" * 104)
    for gg in np.round(np.linspace(max(g - 0.6, 0.05), g + 0.6, 13), 4):
        ss, oo = m.best_S(gg)
        if not np.isfinite(oo):
            continue
        be = breakevens(m, gg, ss)
        star = "  <-- gamma*" if abs(gg - g) < 0.06 else ""
        print(
            f"{gg:>8.4f} {ss * 1e3:>10.3f} {be['SR_G']:>10.3f} {be['SU_L']:>10.3f} "
            f"{be['SR_G'] - be['SU_L']:>+10.4f}{star}"
        )
    print(f"\ngamma* = {g:.4f}  (gap crosses zero here)")


def mode_conditions(ov):
    print("=" * 104)
    print("C1 / C2 EVALUATED NUMERICALLY")
    print("=" * 104)
    print(
        "C1 : slope at the LOWER quantity bound  >  reference   -> a barter set exists"
    )
    print(
        "C2 : slope at the UPPER quantity bound  <  reference   -> optimum is interior"
    )
    print(
        "slope_i = (du_L/dx) / -(du_G/dx);  reference = b_L/b_G (PAP) or 1 (baseload)\n"
    )

    # ---- PAP ----
    d = load_data(["experiment=default_pap", "experiment.sim_name=analysis"] + ov)
    m = PapNash(d)
    S_R = d.strikeprice_min
    for label, x in (("gamma^R = 0", 1e-6), ("gamma^U = 1", 1.0), ("gamma = 1.5", 1.5)):
        be = breakevens(m, x, S_R)
        duG = S_R * be["b_G"] - be["y_G"]
        duL = be["y_L"] - S_R * be["b_L"]
        slope = duL / (-duG)
        ref = be["b_L"] / be["b_G"]
        which = "C1" if x < 0.5 else "C2"
        ok = (slope > ref) if which == "C1" else (slope < ref)
        print(
            f"PAP  {label:>12}: slope={slope:8.4f}  reference={ref:8.4f}  "
            f"{which} {'HOLDS' if ok else 'FAILS'}"
        )
    g, s, _ = m.argmax_gamma(0.0, 4.0)
    print(
        f"     -> unconstrained gamma* = {g:.4f}; the box cap is gamma^U = {d.gamma_max}"
    )
    print(
        f"     -> C2 is evaluated at the cap, so it FAILS whenever gamma* > cap: Case 3.\n"
    )

    # ---- Baseload ----
    db = load_data(["experiment=default_baseload", "experiment.sim_name=analysis"] + ov)
    b = BaseloadNash(db)
    S_Rb = db.strikeprice_min
    cap = db.contract_amount_max
    for label, x in ((f"M^R = 0", 1e-6), (f"M^U = {cap:.0f} GWh/y", cap)):
        r = b.utilities(x, S_Rb)
        phi_G = blend(b, b.Lam_G, r["tw_G"], b.A_G)
        phi_L = blend(b, b.Lam_L, r["tw_L"], b.A_L)
        duG = b.Dsum_G * S_Rb - phi_G
        duL = phi_L - b.Dsum_L * S_Rb
        slope = duL / (-duG)
        which = "C1" if x < 1.0 else "C2"
        ok = (slope > 1.0) if which == "C1" else (slope < 1.0)
        print(
            f"BL   {label:>18}: slope={slope:8.4f}  reference={1.0:8.4f}  "
            f"{which} {'HOLDS' if ok else 'FAILS'}"
        )
    best = (-np.inf, None, None)
    for M in np.linspace(0.0, 2.0 * cap, 100):
        ss, oo = b.best_S(M, n_grid=200, n_refine=25)
        if oo > best[0]:
            best = (oo, M, ss)
    print(
        f"     -> unconstrained M* = {best[1]:.2f} GWh/y = {best[1] / cap:.1%} of the cap: interior, Case 1."
    )


def mode_grid(ov):
    print("=" * 96)
    print("gamma* OVER THE RISK-AVERSION GRID (contract bounds ignored)")
    print("=" * 96)
    A = [0.0, 0.25, 0.5, 0.75, 1.0]
    print("rows = A_L (buyer), cols = A_G (generator)")
    print("       " + "".join(f"{a:>10.2f}" for a in A))
    for al in A:
        row = ""
        for ag in A:
            d = load_data(
                [
                    "experiment=default_pap",
                    "experiment.sim_name=analysis",
                    f"experiment.A_G={ag}",
                    f"experiment.A_L={al}",
                ]
                + ov
            )
            m = PapNash(d)
            g, _, _ = m.argmax_gamma(0.0, 8.0, n=49, refine=25)
            row += f"{g:>10.4f}" if np.isfinite(g) else f"{'--':>10}"
        print(f"A_L={al:<4.2f}" + row)


def mode_spread(ov):
    print("=" * 96)
    print(
        "BUY-BACK PREMIUM — an economically motivated way to make gamma* <= 1 endogenous"
    )
    print("=" * 96)
    print(
        "Covering a short position needs power bought back at spot PLUS an imbalance /"
    )
    print("liquidity premium phi. Applying phi to the (gamma-1) leg only:\n")
    d = load_data(["experiment=default_pap", "experiment.sim_name=analysis"] + ov)

    class PapWithSpread(PapNash):
        def __init__(self, data, phi, **kw):
            super().__init__(data, **kw)
            self.phi = phi

        def earnings(self, gamma, S):
            pi_G = (1 - gamma) * self.Ync_G + gamma * S * self.B
            pi_L = self.Ync_L + gamma * (self.Y_L - S * self.B_L)
            if gamma > 1.0:
                pi_G = pi_G - (gamma - 1.0) * self.phi * self.Ync_G
            return pi_G, pi_L

    print(f"{'phi':>8} {'gamma*':>9} {'S*[E/MWh]':>11}")
    print("-" * 32)
    for phi in [0.0, 0.02, 0.05, 0.10, 0.20]:
        mm = PapWithSpread(d, phi)
        g, s, _ = mm.argmax_gamma(0.0, 4.0, n=61, refine=25)
        print(f"{phi:>8.2f} {g:>9.4f} {s * 1e3:>11.3f}")


# ======================================================================================


def main():
    args = sys.argv[1:]
    mode = (
        args[0] if args and not args[0].startswith(("experiment", "+", "~")) else "all"
    )
    ov = [a for a in args if a.startswith(("experiment", "+", "~"))]

    if mode in ("toy", "all"):
        mode_toy()
        print()
    if mode in ("sweep", "all"):
        mode_sweep(ov)
        print()
    if mode in ("foc", "all"):
        mode_foc(ov)
        print()
    if mode in ("conditions", "all"):
        mode_conditions(ov)
        print()
    if mode in ("grid", "all"):
        mode_grid(ov)
        print()
    if mode in ("spread", "all"):
        mode_spread(ov)
    if mode not in ("toy", "sweep", "foc", "conditions", "grid", "spread", "all"):
        print(__doc__)


if __name__ == "__main__":
    main()
