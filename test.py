import gurobipy as gp
import numpy as np


prices = np.array([50.0, 55.0, 45.0, 60.0, 52.0])
P_G    = np.array([100.0,  80.0, 120.0,  90.0, 110.0])
P_L    = np.array([150.0, 160.0, 140.0, 170.0, 155.0])
CR_G   = np.array([0.85, 0.88, 0.57, 0.80, 0.84])
CR_L   = np.array([1.05, 1.04, 1.06, 1.03, 1.05])

tau_G, tau_L = 0.5, 0.5
S_min, S_max = 30.0, 80.0
A_G,   A_L   = 0.5, 0.5
# A_G,   A_L   = 0, 0
alpha        = 0.95
#alpha        = 0

def cvar_left(x, p, a):
    zeta = float(np.quantile(x, 1 - a))
    return zeta - (1 / (1 - a)) * float((p * np.maximum(zeta - x, 0.0)).sum())


def deterministic_pap():
    d_G = float((CR_G * prices * P_G).sum())
    d_L = float(-(CR_L * prices * P_L).sum())

    m = gp.Model()
    m.Params.NonConvex = 2
    m.Params.OutputFlag = 0

    S     = m.addVar(lb=S_min, ub=S_max, name="S")
    gamma = m.addVar(lb=0.0,   ub=1.0,   name="gamma")

    u_G         = m.addVar(lb=-gp.GRB.INFINITY, name="u_G")
    u_L         = m.addVar(lb=-gp.GRB.INFINITY, name="u_L")
    delta_G     = m.addVar(lb=1e-8,              name="delta_G")
    delta_L     = m.addVar(lb=1e-8,              name="delta_L")
    log_delta_G = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_G")
    log_delta_L = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_L")

    m.addConstr(u_G == (1 - gamma) * d_G + gamma * S * float(P_G.sum()), name="u_G_pap")
    m.addConstr(u_L == d_L + gamma * (float((CR_G * prices * P_G).sum()) - S * float(P_G.sum())), name="u_L_pap")
    m.addConstr(delta_G == u_G - d_G, name="surplus_G")
    m.addConstr(delta_L == u_L - d_L, name="surplus_L")
    m.addGenConstrLog(delta_G, log_delta_G, name="log_G")
    m.addGenConstrLog(delta_L, log_delta_L, name="log_L")

    m.setObjective(tau_G * log_delta_G + tau_L * log_delta_L, gp.GRB.MAXIMIZE)
    m.optimize()

    print("deterministic")
    if m.Status == gp.GRB.OPTIMAL:
        print(f"S={S.X:.4f}  gamma={gamma.X:.4f}  d_G={d_G:.2f}  delta_G={delta_G.X:.6f}  d_L={d_L:.2f}  delta_L={delta_L.X:.6f}")
    else:
        print(f"status: {m.Status}")




# Stochastic data: shape (S_scen, T) — rows are scenarios, columns are timesteps
# 5 scenarios x 5 timesteps
prices_sto = np.array([[50.0, 55.0, 45.0, 60.0, 52.0],
                       [40.0, 42.0, 38.0, 44.0, 41.0],
                       [65.0, 68.0, 60.0, 70.0, 66.0],
                       [30.0, 32.0, 28.0, 35.0, 31.0],
                       [75.0, 78.0, 70.0, 80.0, 76.0]])
P_G_sto    = np.array([[100.0,  80.0, 120.0,  90.0, 110.0],
                       [110.0,  85.0, 115.0,  95.0, 105.0],
                       [ 90.0,  75.0, 110.0,  85.0, 100.0],
                       [120.0,  90.0, 130.0, 100.0, 115.0],
                       [ 80.0,  70.0, 100.0,  75.0,  95.0]])
P_L_sto    = np.array([[150.0, 160.0, 140.0, 170.0, 155.0],
                       [155.0, 162.0, 145.0, 168.0, 158.0],
                       [148.0, 158.0, 138.0, 165.0, 152.0],
                       [160.0, 165.0, 150.0, 175.0, 160.0],
                       [145.0, 155.0, 135.0, 162.0, 150.0]])
CR_G_sto   = np.array([[0.85, 0.88, 0.57, 0.80, 0.84],
                       [0.87, 0.90, 0.60, 0.82, 0.86],
                       [0.80, 0.83, 0.52, 0.76, 0.80],
                       [0.90, 0.92, 0.65, 0.85, 0.88],
                       [0.75, 0.78, 0.48, 0.72, 0.76]])
CR_L_sto   = np.array([[1.05, 1.04, 1.06, 1.03, 1.05],
                       [1.04, 1.03, 1.05, 1.02, 1.04],
                       [1.06, 1.05, 1.07, 1.04, 1.06],
                       [1.03, 1.02, 1.04, 1.01, 1.03],
                       [1.07, 1.06, 1.08, 1.05, 1.07]])
prob_sto   = np.full(5, 1.0 / 5)



def stochastic_pap():
    earnings_nc_G = (CR_G_sto * prices_sto * P_G_sto).sum(axis=1)   # (S_scen,)
    earnings_nc_L = -(CR_L_sto * prices_sto * P_L_sto).sum(axis=1)  # (S_scen,)
    prod_disc_G   = P_G_sto.sum(axis=1)                               # (S_scen,)
    gamma_coeff_L = (CR_G_sto * prices_sto * P_G_sto).sum(axis=1)    # (S_scen,)

    d_G = float((prob_sto * earnings_nc_G).sum())
    d_L = float((prob_sto * earnings_nc_L).sum())

    m = gp.Model()
    m.Params.NonConvex = 2
    m.Params.OutputFlag = 0

    S     = m.addVar(lb=S_min, ub=S_max, name="S")
    gamma = m.addVar(lb=0.0,   ub=1.0,   name="gamma")

    u_G         = m.addVar(lb=-gp.GRB.INFINITY, name="u_G")
    u_L         = m.addVar(lb=-gp.GRB.INFINITY, name="u_L")
    delta_G     = m.addVar(lb=1e-8,              name="delta_G")
    delta_L     = m.addVar(lb=1e-8,              name="delta_L")
    log_delta_G = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_G")
    log_delta_L = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_L")

    m.addConstr(u_G == (1 - gamma) * d_G + gamma * S * float((prob_sto * prod_disc_G).sum()), name="u_G_pap")
    m.addConstr(u_L == d_L + gamma * (float((prob_sto * gamma_coeff_L).sum()) - S * float((prob_sto * prod_disc_G).sum())), name="u_L_pap")
    m.addConstr(delta_G == u_G - d_G, name="surplus_G")
    m.addConstr(delta_L == u_L - d_L, name="surplus_L")
    m.addGenConstrLog(delta_G, log_delta_G, name="log_G")
    m.addGenConstrLog(delta_L, log_delta_L, name="log_L")

    m.setObjective(tau_G * log_delta_G + tau_L * log_delta_L, gp.GRB.MAXIMIZE)
    m.optimize()

    print("stochastic (no CVaR)")
    if m.Status == gp.GRB.OPTIMAL:
        print(f"S={S.X:.4f}  gamma={gamma.X:.4f}  d_G={d_G:.2f}  delta_G={delta_G.X:.6f}  d_L={d_L:.2f}  delta_L={delta_L.X:.6f}")
    else:
        print(f"status: {m.Status}")


def cvar_pap():
    S_scen = prices_sto.shape[0]
    earnings_nc_G = (CR_G_sto * prices_sto * P_G_sto).sum(axis=1)   # (S_scen,)
    earnings_nc_L = -(CR_L_sto * prices_sto * P_L_sto).sum(axis=1)  # (S_scen,)

    d_G = (1 - A_G) * float((prob_sto * earnings_nc_G).sum()) + A_G * cvar_left(earnings_nc_G, prob_sto, alpha)
    d_L = (1 - A_L) * float((prob_sto * earnings_nc_L).sum()) + A_L * cvar_left(earnings_nc_L, prob_sto, alpha)

    m = gp.Model()
    m.Params.NonConvex = 2
    m.Params.OutputFlag = 0

    S     = m.addVar(lb=S_min, ub=S_max, name="S")
    gamma = m.addVar(lb=0.0,   ub=1.0,   name="gamma")

    u_G         = m.addVar(lb=-gp.GRB.INFINITY, name="u_G")
    u_L         = m.addVar(lb=-gp.GRB.INFINITY, name="u_L")
    delta_G     = m.addVar(lb=1e-8,              name="delta_G")
    delta_L     = m.addVar(lb=1e-8,              name="delta_L")
    log_delta_G = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_G")
    log_delta_L = m.addVar(lb=-gp.GRB.INFINITY, name="log_delta_L")
    zeta_G      = m.addVar(lb=-gp.GRB.INFINITY, name="zeta_G")
    zeta_L      = m.addVar(lb=-gp.GRB.INFINITY, name="zeta_L")
    eta_G       = m.addMVar(shape=S_scen, lb=0.0, name="eta_G")
    eta_L       = m.addMVar(shape=S_scen, lb=0.0, name="eta_L")

    prod_disc_G   = P_G_sto.sum(axis=1)                             # (S_scen,)
    gamma_coeff_L = (CR_G_sto * prices_sto * P_G_sto).sum(axis=1)  # (S_scen,)
    E_prod_disc_G   = float((prob_sto * prod_disc_G).sum())
    E_gamma_coeff_L = float((prob_sto * gamma_coeff_L).sum())

    m.addConstr(
        u_G == (1 - A_G) * ((1 - gamma) * float((prob_sto * earnings_nc_G).sum()) + gamma * S * E_prod_disc_G)
             + A_G * (zeta_G - (1 / (1 - alpha)) * prob_sto[0] * eta_G.sum()),
        name="u_G_pap"
    )
    m.addConstr(
        u_L == (1 - A_L) * (float((prob_sto * earnings_nc_L).sum()) + gamma * (E_gamma_coeff_L - S * E_prod_disc_G))
             + A_L * (zeta_L - (1 / (1 - alpha)) * prob_sto[0] * eta_L.sum()),
        name="u_L_pap"
    )
    for s in range(S_scen):
        m.addConstr(eta_G[s] >= zeta_G - earnings_nc_G[s] - gamma * (S * prod_disc_G[s] - earnings_nc_G[s]), name=f"eta_G_{s}")
        m.addConstr(eta_L[s] >= zeta_L - earnings_nc_L[s] - gamma * (gamma_coeff_L[s] - S * prod_disc_G[s]), name=f"eta_L_{s}")

    m.addConstr(delta_G == u_G - d_G, name="surplus_G")
    m.addConstr(delta_L == u_L - d_L, name="surplus_L")
    m.addGenConstrLog(delta_G, log_delta_G, name="log_G")
    m.addGenConstrLog(delta_L, log_delta_L, name="log_L")

    m.setObjective(tau_G * log_delta_G + tau_L * log_delta_L, gp.GRB.MAXIMIZE)
    m.optimize()

    print(f"CVaR (A={A_G}, alpha={alpha})")
    if m.Status == gp.GRB.OPTIMAL:
        print(f"S={S.X:.4f}  gamma={gamma.X:.4f}  d_G={d_G:.2f}  delta_G={delta_G.X:.6f}  d_L={d_L:.2f}  delta_L={delta_L.X:.6f}")
    else:
        print(f"status: {m.Status}")


deterministic_pap()
stochastic_pap()
cvar_pap()