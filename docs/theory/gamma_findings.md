# Why γ Goes Above 1, What Controls It, and How to Fix It

Everything in this note is reproducible with `analysis/compute_gamma.py`. The closed-form
engine in `analysis/gamma_engine.py` matches Gurobi to 1e-6 on every quantity (`δ_G`,
`δ_L`, `u_G`, `u_L`, `CVaR_G`, `CVaR_L`) and returns the same γ\* = 1.0721 the solver
gives when `gamma_max = 3.0`. So these are the model's own numbers.

---

## 1. First, a correction: γ = 0.99 versus γ = 0.49

You ran `uv run main.py` with `load_scale = 0.1` and got γ ≈ 0.99. That is correct, and
my earlier summary was misleading. I reported 0.4933 in a table headed "load_scale",
which implied load scale alone produced it. It did not. That figure needed three changes
from the shipped default, not one.

Here is the honest ladder:

| configuration | γ\* unbounded | γ\* with cap at 1 | S\* [EUR/MWh] |
|---|---|---|---|
| `default_pap` exactly as shipped | 1.0721 | **1.0000** | 67.655 |
| plus `K_L_price = 0` | 0.9636 | 0.9636 | 65.859 |
| plus `K_L_price = 0`, `A_L = 0.5` | **0.4933** | 0.4933 | 65.699 |
| plus `K_L_price = 0`, `A_L = 0.5`, `load_scale = 1.0` | 1.2105 | 1.0000 | 69.268 |

The shipped default is `A_G = 0.5, A_L = 0.1, K_L_price = 0.05, load_scale = 0.1,
gamma_max = 1.0`. With the cap at 1.0 the solver returns 0.9999..., which is your 0.99.
The 0.4933 required symmetric information **and** `A_L = 0.5` **and** `load_scale = 0.1`
together. Reproduce it with:

```bash
uv run python analysis/compute_gamma.py foc \
    experiment.K_L_price=0.0 experiment.A_L=0.5 experiment.load_scale=0.1
```

---

## 2. What drives what

This is the part worth internalising, because two of these are counter to intuition.

### Buyer size drives the VOLUME

γ\* tracks how much hedge the buyer wants relative to how much the plant can physically
make. This is by far the strongest lever. In the toy model (`compute_gamma.py toy`),
starting from a perfectly matched pair where the buyer consumes exactly what the plant
produces:

| perturbation | γ\* |
|---|---|
| buyer = plant output | 1.0000 |
| buyer 2x the plant | 1.8632 |
| buyer 0.2x the plant | 0.7191 |

### Risk aversion drives the PRICE, not the volume

This is the surprise. In the same symmetric toy, moving risk aversion over its whole
useful range leaves γ\* at *exactly* 1.0000 and moves only the strike:

| perturbation | γ\* | S\* [EUR/MWh] |
|---|---|---|
| baseline | 1.0000 | 77.000 |
| generator less risk averse, `A_G = 0.2` | 1.0000 | 82.100 |
| generator more risk averse, `A_G = 0.8` | 1.0000 | 71.900 |
| buyer more risk averse, `A_L = 0.8` | 1.0000 | 83.900 |

Risk aversion **re-prices** the deal. It does not **resize** it. It only begins to move
γ\* once the buyer/plant symmetry is already broken. For baseload this is a theorem, not
an observation: at fixed volume the strike direction locus has slope exactly minus one,
so the strike is a pure one for one transfer that moves the split and never the size of
the pie.

### Generation variability pulls the volume DOWN

The more the plant's output swings, the worse a production linked contract works as a
hedge, so less of it gets written:

| perturbation | γ\* |
|---|---|
| flat output | 1.0000 |
| mild volume risk (98 to 102 GWh) | 0.9842 |
| strong volume risk (70 to 130 GWh) | 0.8692 |

### CVaR has three separate jobs

Keeping these apart resolves most of the confusion.

**Job 1: CVaR is the only reason any contract exists at all.** Under symmetric
information the mean legs cancel to machine precision (`dmean_G + dmean_L = 2.2e-16`).
In expectation, raising γ is a pure zero sum transfer that creates nothing. All gains
from trade come from the two parties' tail sets being **disjoint**. In the toy the
generator's worst case is the low price scenario and the buyer's worst case is the high
price scenario. Trade swaps tail risk that each side values differently.

**Job 2: CVaR is the brake on γ, through a tail flip.** Look at the merchant coefficient
`(1 - γ)` in `π_G = (1 - γ)·Y_G + γ·S·B`:

| regime | coefficient on `Y_G` | generator's worst case is |
|---|---|---|
| γ < 1 | positive | low revenue, meaning low price, scenarios |
| γ = 1 | zero | pure volume risk, price risk fully removed |
| γ > 1 | **negative** | high revenue, meaning high price, scenarios |

The generator's tail changes identity as γ crosses 1. Measured on the real data as the
tail average capture price in EUR/MWh:

| γ | 0.25 | 0.50 | 0.75 | 1.00 | 1.25 | 1.50 |
|---|---|---|---|---|---|---|
| generator tail | 56.41 | 56.75 | 58.70 | **68.61** | 80.51 | 82.13 |
| buyer tail | 66.71 | 56.89 | 56.34 | 56.20 | 56.19 | 56.17 |

The unconditional mean is 68.99. The generator's tail migrates from the cheap scenarios
to the expensive ones and passes through the unconditional mean at exactly γ = 1, the
point where its payoff `S·B` carries no price risk whatsoever. Past that the generator is
short, and its CVaR leg turns hard negative: `dcvar_G` runs `+22.7` to `-1.8` to `-21.5`
across γ = 0.25, 1.0, 1.2.

**Job 3: CVaR is the only thing bounding γ at all.** Remove the generator's risk aversion
and γ diverges:

| `A_G` | 0.00 | 0.10 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---|---|---|---|---|---|
| γ\* | above 12, unbounded | above 12, unbounded | 1.14 | 1.07 | 1.04 | 1.04 |

The paper already states this result for the risk neutral belief asymmetry case, in
Appendix C: *"risk aversion is what would make the objective concave in M and yield a
genuine interior optimum. Absent it, the model has no internal check on over contracting,
and M must be capped externally."* My finding extends exactly that statement to the risk
averse pay as produced case.

---

## 3. Why it happened in Anders' case, specifically

There are two distinct routes to γ > 1 in this model, and the shipped config uses the
second one.

### Route A: the buyer is bigger than the plant

The `load` array is scaled at read time, so the raw magnitude is easy to miss. At
`load_scale = 1.0` the buyer consumes 146.2 GWh per year against the plant's 98.68, so
the buyer is **1.48 times the plant**. Its hedging demand simply exceeds what one plant
can supply, and γ > 1 is the model satisfying that demand by over selling the generator.
Note the buyer is not over hedged here: at γ\* = 1.21 the contract covers 119 GWh against
a 146 GWh need, so the buyer still buys 27 GWh at market. The generator is short, not the
buyer long.

### Route B: the belief wedge, which is what the shipped default actually uses

`default_pap` sets `K_L_price = 0.05`, meaning the buyer believes prices will be 5 percent
higher than they are. That breaks the exact mean cancellation and manufactures phantom
surplus that both sides think they are capturing:

| `K_L_price` | 0.000 | 0.010 | 0.020 | 0.030 | 0.050 | 0.080 |
|---|---|---|---|---|---|---|
| γ\* | 0.9636 | 0.9830 | 1.0070 | 1.0315 | 1.0721 | 1.1379 |
| mean legs sum | 0.0000 | 1.36 | 2.72 | 4.09 | 6.81 | 10.89 |

γ crosses 1 at about `K_L_price = 0.019`. This is the same mechanism Appendix C already
proves for baseload, now showing up in pay as produced.

### The structural gap underneath both routes

Here is the root cause, and it is a genuine modelling omission rather than a parameter
choice. In Anders' formulation the buyer's cost is

```
π_L = -CR_L·λ·L  +  γ·P·(CR_G·λ - S)
```

Both legs are valued at *a market price*: the buyer avoids cost at `CR_L·λ` and is paid
`CR_G·λ` on the contracted volume. Nothing marks the point where the contract stops
hedging and starts speculating. Rearranged for the case `CR_L = CR_G = CR`, this reads
`-CR·λ·(L - γ·P) - γ·P·S`, which makes the issue visible: when `γ·P > L` the bracket goes
negative and the buyer simply **resells the surplus at the full market price with no
penalty at all**. It is exactly indifferent between consuming a MWh and reselling it.

(The two capture rates are not in fact equal here, `CR_G ≈ 0.585` against
`CR_L ≈ 1.043`, so the buyer is already paid less per contracted MWh than it saves per
consumed MWh. That 44% wedge discourages contracting uniformly but has no kink at
`γ·P = L`, which is why it lowers γ\* without capping it. See section 5b.)

Nothing in the model ties the contract size to the
buyer's own consumption, so nothing stops the buyer contracting far more than it uses.

On the shipped default the buyer contracts **7.24 times its own consumption** at γ\* and
suffers nothing for it. That is the real defect.

---

## 3b. Who actually wants γ > 1? Not the producer

This is the single most useful diagnostic, and it corrects a natural misreading. At the
negotiated strike S\*, compute each party's *individually* optimal γ, the one that
maximises its own utility alone, and compare with the Nash outcome:

| `load_scale` | buyer / plant | generator's own best γ | buyer's own best γ | Nash γ\* |
|---|---|---|---|---|
| 0.10 | 0.148 | 0.8907 | 0.2852 | 0.4933 |
| 0.30 | 0.444 | 0.9608 | 0.7556 | 0.8671 |
| 0.54 | 0.800 | 1.0058 | 1.2611 | 1.0758 |
| 1.00 | 1.482 | 1.0359 | **2.1918** | 1.2105 |

Two things fall out.

**The producer never wants γ much above 1.** Its own optimum sits between 0.89 and 1.04
across the whole range, always hugging 1. That is exactly what the theory predicts: at
γ = 1 its payoff is `S·B`, carrying no price risk at all. The producer is behaving
perfectly rationally, and its rational point *is* full coverage of its own output.

**It is the buyer that pulls γ past 1.** At `load_scale = 1.0` the buyer would like
γ = 2.19, because its consumption is 1.48x the plant and it wants its whole exposure
hedged. γ\* = 1.21 is the compromise.

So the answer to "why would the producer settle for more than the rational?" is: it does
not do so on its own account. It concedes volume it does not want in exchange for a
strike it does want. The Nash product rewards trading own-utility for joint surplus, and
S\* rises to compensate (69.06 at `load_scale = 0.54`, 69.96 at 1.0). The producer is
paid to over-sell.

---

## 4. How to get γ inside 1, and make it mean something

### Correcting yesterday's framing

I proposed a "resale haircut" and justified it as a physical loss on resold surplus. **You
were right to push back on that.** This is a financial CfD: nothing is physically
delivered, and the buyer does resell at the market price with no haircut. There is no
physical penalty, and inventing one would be a fudge.

The real constraint is institutional, not physical:

> **A corporate treasury may not hold a hedge larger than the exposure it hedges.**

Under IFRS 9 / ASC 815 hedge accounting, a derivative can only be designated as a hedge
against an existing exposure. Volume beyond that is not a hedge, it is a speculative
position: it goes to mark-to-market through P&L, and essentially every corporate treasury
mandate forbids it. A buyer signing a PPA for more MWh than it consumes has stopped
hedging and become an energy trader, which is outside its business.

That gives a clean, defensible cap: `γ·P ≤ L`, i.e. **γ ≤ L/P**.

### The two caps, and what each one is

| cap | value | what kind of constraint |
|---|---|---|
| `γ ≤ 1` | 1.000 | **Physical.** A plant cannot sell what it does not generate. |
| `γ ≤ L/P` | `load_over_prod` | **Institutional.** A buyer may not hedge beyond its exposure. |

The admissible share is `γ ≤ min(1, L/P)`, and which one binds depends on the relative
size of the two parties. Implemented as `hedge_ratio_max` in `default_pap.yaml`:

| `load_scale` | L/P | unconstrained γ\* | cap = min(1, L/P) | γ\* capped | resulting hedge ratio |
|---|---|---|---|---|---|
| 0.10 | 0.148 | 0.4933 | 0.148 | 0.1482 | 100.0% |
| 0.30 | 0.444 | 0.8671 | 0.444 | 0.4445 | 100.0% |
| 0.40 | 0.593 | 0.9815 | 0.593 | 0.5926 | 100.0% |
| **0.54** | **0.800** | 1.0758 | **0.800** | **0.8000** | **100.0%** |
| 0.70 | 1.037 | 1.1324 | 1.000 | 1.0000 | 96.4% |
| 1.00 | 1.482 | 1.2105 | 1.000 | 1.0000 | 67.5% |

Verified against Gurobi, not just the closed-form engine:

```bash
uv run python main.py experiment=default_pap experiment.sim_name=hedged \
    experiment.load_scale=0.54 experiment.hedge_ratio_max=1.0 \
    experiment.gamma_max=3.0 experiment.K_L_price=0.0 experiment.A_L=0.5
# -> gamma = 0.7997, S = 68.80 EUR/MWh
```

### Fix 2: size the buyer deliberately

With the haircut in place, γ\* tracks buyer size almost perfectly, capped by plant output:

| `load_scale` | buyer GWh/yr | buyer / plant | γ\* (h = 0) | γ\* (h = 0.25) | contracted / buyer |
|---|---|---|---|---|---|
| 0.10 | 14.6 | 0.148 | 0.4933 | 0.1505 | 1.02x |
| 0.20 | 29.2 | 0.296 | 0.7187 | 0.3008 | 1.02x |
| 0.30 | 43.9 | 0.444 | 0.8671 | 0.4506 | 1.01x |
| 0.40 | 58.5 | 0.593 | 0.9815 | 0.5994 | 1.01x |
| 0.50 | 73.1 | 0.741 | 1.0543 | 0.7425 | 1.00x |
| **0.54** | **79.0** | **0.800** | 1.0758 | **0.7990** | **1.00x** |
| 0.56 | 81.9 | 0.830 | 1.0843 | 0.8256 | 1.00x |
| 0.70 | 102.3 | 1.037 | 1.1324 | 0.9903 | 0.95x |
| 1.00 | 146.2 | 1.482 | 1.2105 | 1.2034 | 0.81x |

**To get the γ ≈ 0.8 you described as typical for real pay as produced deals: set
`load_scale ≈ 0.54`, so the buyer consumes about 80 percent of plant output, and apply
the resale haircut.** Then γ\* ≈ 0.8 has a clean meaning: the buyer hedges its full
consumption, which happens to be 80 percent of what the plant makes.

Note the contrast in the two γ\* columns at `load_scale = 0.30`. Without the haircut you
also get roughly 0.87, which looks fine, but the contract is then twice the buyer's
consumption. The number looks right for the wrong reason. **The haircut is what makes a
sub unity γ mean something rather than just look reasonable.**

### Fix 3 as a fallback: a buy back premium on the generator side

If you would rather target the generator's short position than the buyer's over purchase,
a premium `φ` on the `(γ - 1)` leg also works, and at `φ = 0.10` it makes γ\* = 1 the
endogenous optimum rather than a box constraint:

| `φ` | 0.00 | 0.02 | 0.05 | **0.10** | 0.20 |
|---|---|---|---|---|---|
| γ\* | 1.2105 | 1.1268 | 1.0542 | **1.0000** | 1.0000 |

This is the right fix for Route A, where the generator is short. Fix 1 is the right fix
for Route B, where the buyer is over purchasing. The shipped default suffers from Route
B, so Fix 1 is the one you need.

---

## 5. Is Viktor's model useful? Does deriving it differently cause problems?

### Short answer

Yes, one specific mechanism in it is useful, and it is precisely the thing Anders' model
is missing. No, deriving it differently is not in itself a problem. But there is one
piece of Viktor's formulation you should **not** copy.

### Why Viktor got an interior γ and we did not

The two buyer formulations differ in exactly one respect, and it is decisive.

**Anders' buyer** pays `CR_L·λ` for its consumption and receives `CR_G·λ` per contracted
MWh. Both legs are valued at *the market price*. The buyer is therefore indifferent
between consuming a MWh and reselling it, so contracted volume beyond its consumption
costs nothing. There is no kink at `γ·P = L`, and nothing ties contract size to demand.

**Viktor's buyer** has the term `(L_t - γ·P_fore)·(WTP - λ)`. Consumption is worth `WTP`
to it, and `WTP > λ` in normal hours. When `γ·P > L` that bracket goes negative while
`(WTP - λ)` stays positive, so every surplus MWh costs the buyer `(WTP - λ)` of forgone
consumer surplus. The penalty starts exactly at `γ·P = L`.

So: **Viktor's buyer has a finite consumption need with value above market; Anders' buyer
is effectively a financial trader that values energy at exactly market price.** A trader
has no natural hedge ceiling, and that is the whole difference. Viktor's `WTP` term is a
soft version of the hedge-ratio constraint in section 4; the `hedge_ratio_max` cap is the
hard version of the same economics.

Viktor's curtailment mechanism is a second, independent channel, but it is not what
produces his sensible hedge ratios in the normal case.

### What not to borrow

Viktor pays the generator on curtailed delivery `P_DA = P_fore · 1{λ ≥ 0}` but nets the
buyer's baseline against the **uncurtailed** forecast `P_fore`. The two sides settle
against different quantities for the same nominal γ. That looks like an inconsistency
rather than a design feature: a real pay as produced contract settles on metered output,
so if the generator curtails, the buyer should receive less. This matters because it is
what drives his γ toward zero when negative price hours are present. I would not import
that part, and I would treat his γ values as indicative rather than as a target to
reproduce.

Related and worth knowing: his synthetic data generator in
`enlight_PPA/src/enlight_PPA/utils/nbs_utils.py` has the two negative price hours sign
flipped to positive, with the original values still visible in a commented out block
directly above. Restoring them collapses γ to about 0.0002 across his whole grid. So his
demonstration data is currently not exercising the very mechanism that distinguishes his
model.

### Are we biasing our results?

Yes, in one specific and correctable direction. By omitting any penalty on resold surplus
volume, Anders' model **systematically overstates the optimal contract size**. That is
the bias, and γ > 1 is its most visible symptom. Everything else in the model is sound:
the barter set theory, the CVaR machinery, the baseload results, and the strike price
results are all unaffected, because the strike is determined by a separate condition
(see section 4.1 of `barter_set_and_gamma.md`).

### Is the different derivation a problem for the paper?

No. They are two models of the same contract at different resolutions, and that is a
legitimate thing to have. What you should not do is present Viktor's γ ≈ 0.8 as
independent validation of a corrected Anders model, because the two numbers come from
different mechanisms. Cite his work for the structural insight that consumption netting
matters, implement it in your own formulation, and report your own γ.

---

## 5b. Is the capture rate to blame? And would hourly resolution fix it?

Short answer to both: no.

### Ablating the capture rate

Set `CR_G = CR_L = 1` everywhere, so the settlement is against the flat average price and
cannibalisation disappears:

| `load_scale` | L/P | γ\* with capture rates | S\* | γ\* with CR = 1 | S\* |
|---|---|---|---|---|---|
| 0.10 | 0.148 | 0.4933 | 65.70 | 0.2238 | 114.79 |
| 0.54 | 0.800 | 1.0758 | 69.06 | 0.8544 | 117.70 |
| 1.00 | 1.482 | 1.2105 | 69.96 | **1.2643** | 120.29 |

The strike moves a lot, from about 69 to about 118 EUR/MWh, which is expected: without
cannibalisation the plant captures the full time-average price instead of 58.5% of it. But
γ\* moves by roughly 0.2 in either direction, and at `load_scale = 1.0` removing the
capture rate makes the overshoot slightly **worse**, not better. The capture rate is a
level effect on the price, not the thing generating γ > 1.

Worth knowing, though: a 44% asymmetry is **already** in the model. The buyer receives
`CR_G ≈ 0.585` per contracted MWh but avoids cost at `CR_L ≈ 1.043` on its own
consumption. So the buyer is already paid at the generation-weighted price while saving at
the consumption-weighted one. This penalises contracting in general, but uniformly, with
no kink at `γ·P = L`, which is why it shifts γ\* without capping it.

### Would hourly resolution with no capture rate be different?

Not for this problem. The γ = 1 knife-edge comes from the merchant coefficient `(1 - γ)`
changing sign, and that is true at any time resolution. Hourly, the settlement would be
`Σ_t γ·P_t·(λ_t - S)`, and at γ = 1 the generator's payoff is `S·Σ_t P_t`, still free of
price risk. Same structure, same knife-edge.

What hourly resolution genuinely adds is two things the yearly capture rate cannot
represent:

1. **Curtailment at negative prices**, which needs an hour-specific gate `1{λ_t ≥ 0}`.
   This is Viktor's second mechanism.
2. **Hour-by-hour interaction between the generation profile and the consumption
   profile**, which matters if you want the hedge ratio to respond to shape mismatch
   rather than just to annual volumes.

Neither is required to fix γ > 1. Both would make the model richer, and both are
substantial changes. Given the paper is about bargaining rather than dispatch, the yearly
capture-rate reduction is a defensible modelling choice, and I would keep it and state the
limitation rather than rebuild at hourly resolution.

---

## 6. Summary card

| question | answer |
|---|---|
| Why did I get 0.99? | That is the shipped default with the cap at 1 binding. My 0.49 needed three config changes, not one. |
| What drives volume? | Buyer size relative to plant output. Dominant lever. |
| What drives the strike? | Risk aversion and bargaining power. These barely touch volume. |
| What does generation variability do? | Pulls volume down. More output swing means a worse hedge. |
| What does CVaR do? | Creates the deal, brakes γ via the tail flip at 1, and is the only thing bounding γ at all. |
| Why γ > 1 in Anders? | The buyer values energy at market price on both legs, so contracting beyond its consumption is free. The 5 percent price bias then tips it over 1. |
| Who wants γ > 1? | Not the producer. Its own optimum is 0.89 to 1.04 always. The buyer wants 2.19 at load_scale 1.0 and drags γ up through bargaining. |
| How do I get γ ≈ 0.8? | `load_scale=0.54` plus `hedge_ratio_max=1.0`. Gives γ* = 0.7997 against Gurobi. |
| Is the capture rate to blame? | No. Ablating it moves γ* by ~0.2 and at load_scale 1.0 makes it worse. |
| Would hourly fix it? | No. The γ=1 knife-edge is resolution-independent. Hourly adds curtailment and shape matching, which are separate gains. |
| Is Viktor useful? | Yes for the WTP consumption-netting mechanism, which is why he gets an interior γ. No for the curtailment mismatch. |
