# Model

## Problem setup

Two parties negotiate a power purchase agreement over a contract horizon of $T$ years. The generator (G) sells renewable electricity; the load (L) buys it. Uncertainty is represented by a finite set of $\Omega$ scenarios, each with probability $p_\omega$.

Both parties are risk-averse. The utility of party $i$ is a weighted combination of expected earnings and left-tail CVaR:

$$U_i = (1 - A_i)\,\mathbb{E}[r_i] + A_i\,\text{CVaR}_\alpha(r_i)$$

where $A_i \in [0, 1]$ is the risk-aversion weight and $\alpha$ is the confidence level (e.g. 0.95 means the worst 5% of scenarios determine the tail).

CVaR is computed using the Rockafellar-Uryasev formulation:

$$\text{CVaR}_\alpha(r_i) = \zeta_i - \frac{1}{1-\alpha}\,\mathbb{E}\bigl[\max(0,\,\zeta_i - r_i)\bigr]$$

where $\zeta_i$ is an auxiliary variable (the Value-at-Risk threshold).

## Disagreement points

If no contract is signed, each party trades on the spot market. Their no-contract earnings per scenario are:

- Generator: $r^\text{nc}_{G,\omega} = \sum_t \delta^G_t \cdot \text{CR}^G_{t,\omega} \cdot \lambda^G_{t,\omega} \cdot P^G_{t,\omega}$
- Load: $r^\text{nc}_{L,\omega} = -\sum_t \delta^L_t \cdot \text{CR}^L_{t,\omega} \cdot \lambda^L_{t,\omega} \cdot Q_{t,\omega}$

where $\delta^i_t = (1 + D_i)^{-t}$ are discount factors, $\text{CR}$ is the capture rate, $\lambda^i$ is the party's biased price belief, $P^G$ is renewable production, and $Q$ is load consumption.

The disagreement point for each party is their utility under no-contract:

$$d_i = U_i(r^\text{nc}_i)$$

A contract is individually rational only if it gives each party at least $d_i$.

## Nash bargaining problem

The asymmetric Nash bargaining solution maximizes the weighted Nash product of surpluses:

$$\max_{S,\,\text{volume}} \quad \delta_G^{\tau_G} \cdot \delta_L^{\tau_L}$$

subject to:

$$\delta_i = U_i - d_i \geq 0 \quad \forall\, i$$

where $\tau_G + \tau_L = 1$ are the bargaining power weights and $\delta_i$ is the surplus of party $i$ above its disagreement point.

Taking logarithms, the objective becomes:

$$\max \quad \tau_G \log \delta_G + \tau_L \log \delta_L$$

which is linear in the log variables. Gurobi handles this via `addGenConstrLog`.

## Contract types

### Baseload

The generator delivers a fixed volume $M$ (GWh/year) at strike price $S$ (EUR/GWh) each period. Settlement is against the spot price:

$$r_{G,\omega} = r^\text{nc}_{G,\omega} + \sum_t \delta^G_t \cdot M \cdot (S - \lambda^G_{t,\omega})$$

$$r_{L,\omega} = r^\text{nc}_{L,\omega} + \sum_t \delta^L_t \cdot M \cdot (\lambda^L_{t,\omega} - S)$$

Decision variables: $S$ (strike price) and $M$ (contract volume). The product $S \times M$ is bilinear; Gurobi resolves it with `NonConvex=2`.

### Pay-As-Produced (PAP)

The generator sells a fraction $\gamma \in [0, \gamma_\text{max}]$ of its actual production at strike price $S$:

$$r_{G,\omega} = r^\text{nc}_{G,\omega} + \gamma \sum_t \delta^G_t \cdot P^G_{t,\omega} \cdot (S - \text{CR}^G_{t,\omega} \cdot \lambda^G_{t,\omega})$$

$$r_{L,\omega} = r^\text{nc}_{L,\omega} + \gamma \sum_t \delta^L_t \cdot P^G_{t,\omega} \cdot (\text{CR}^G_{t,\omega} \cdot \lambda^L_{t,\omega} - S)$$

Decision variables: $S$ and $\gamma$. The product $\gamma \times S$ is bilinear.

## Asymmetric information

Each party holds biased beliefs about prices and production. The bias parameters $K^i_\text{price}$ and $K^i_\text{prod}$ shift the scenario distribution relative to the true one:

$$\lambda^i_{t,\omega} = \lambda_{t,\omega} + K^i_\text{price} \cdot \mathbb{E}[\lambda_t]$$

$$P^i_{t,\omega} = P_{t,\omega} + K^i_\text{prod} \cdot \mathbb{E}[P_t]$$

Setting all $K = 0$ gives the symmetric information case.

## Gurobi implementation

| Feature | Gurobi mechanism |
| --- | --- |
| Log objective | `addGenConstrLog` on $\delta_G$, $\delta_L$ |
| Bilinear terms ($S \times M$, $\gamma \times S$) | `Params.NonConvex = 2` |
| CVaR shortfall variables | `addMVar` with $\text{lb}=0$ |
| Time limit | 420 seconds |

The model is written to `model.lp` and `model.mps` after each solve for inspection.
