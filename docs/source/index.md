# Nash Bargaining for PPAs

This project implements a Nash bargaining model for pricing Power Purchase Agreements (PPAs) between a renewable energy generator and a corporate electricity consumer.

## What it does

Given Monte Carlo scenarios of electricity prices, renewable production, and load consumption, the model finds the contract terms (strike price and volume) that maximize the asymmetric Nash product of both parties' utilities, subject to individual rationality constraints.

Both parties are modeled as risk-averse using a weighted combination of expected earnings and CVaR:

$$U_i = (1 - A_i)\,\mathbb{E}[r_i] + A_i\,\text{CVaR}_\alpha(r_i)$$

where $A_i \in [0, 1]$ controls risk aversion and $\alpha$ is the CVaR confidence level.

The Nash product is asymmetric, controlled by bargaining power weights $\tau_G$ and $\tau_L = 1 - \tau_G$:

$$\max \quad \tau_G \log(\delta_G) + \tau_L \log(\delta_L)$$

where $\delta_i = U_i - d_i$ is each party's surplus above its disagreement point $d_i$.

## Contract types

| Type | Contract volume | Decision variables |
| --- | --- | --- |
| Baseload | Fixed amount $M$ (GWh/year) each period | $S$, $M$ |
| Pay-As-Produced (PAP) | Fraction $\gamma$ of actual renewable production | $S$, $\gamma$ |

## Pipeline

```text
Raw data --> scenario generation --> scenario reduction --> Nash bargaining solve --> results
```

See [Quick Start](quickstart.md) to run the pipeline, [Model](model.md) for the mathematical formulation, and [Configuration](configuration.md) for all parameter options.
