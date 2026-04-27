# Nash Bargaining for PPAs

This project implements a Nash bargaining optimization framework for pricing Power Purchase Agreements (PPAs) between a renewable energy generator and a corporate electricity consumer.

## What it does

Given Monte Carlo scenarios of electricity prices, renewable production, and load consumption, the framework finds the contract terms (strike price and volume) that maximize the Nash product of both parties' utilities, subject to CVaR-based individual rationality constraints.

Both parties are modeled as risk-averse using a weighted combination of expected earnings and CVaR:

$$U_i = (1 - A_i)\,\mathbb{E}[r_i] + A_i\,\text{CVaR}_\alpha(r_i)$$

where $A_i \in [0, 1]$ controls risk aversion and $\alpha$ is the CVaR confidence level.

## Contract types

| Type | Volume |
| --- | --- |
| Baseload | Fixed amount $M$ each period |
| Pay-As-Produced (PAP) | Share $\gamma$ of actual renewable production |

## Workflow

```
data/  -->  generate_scenarios  -->  scenario_reduction  -->  main.py  -->  outputs/
```

See [Quick Start](quickstart.md) to run the full pipeline.