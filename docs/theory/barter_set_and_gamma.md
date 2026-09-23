# The Barter Set, the Boundary Conditions, and Why γ Exceeds 1

*A step-by-step derivation of `S^{R*}`, `S^{U*}`, `M*`, `γ*`, `C1` and `C2` for both
contract types, with worked numbers throughout.*

Everything numerical in this note is reproducible with:

```bash
uv run python analysis/compute_gamma.py all
```

The closed-form engine (`analysis/gamma_engine.py`) reproduces Gurobi to 1e-6 on every
quantity (`δ_G`, `δ_L`, `u_G`, `u_L`, `CVaR_G`, `CVaR_L`), and finds the same γ\* = 1.0721
that the solver returns when `gamma_max = 3.0`. So the numbers below are the model's
own, not an approximation of it.

---

## Part 0: Notation

| symbol | meaning | code |
|---|---|---|
| ω ∈ Ω | scenario, probability `p_ω` | `prob` |
| t = 1…T | year | 20 years |
| `Y_G,ω` | generator merchant revenue, no contract (MEUR) | `earnings_nc_G` |
| `Y_L,ω` | buyer merchant cost, no contract (negative, MEUR) | `earnings_nc_L` |
| `B_ω` | discounted contracted production, Σ_t δ_t P^G_{t,ω} (GWh) | `pap_prod_disc_G` |
| `Λ_i,ω` | discounted price sum, Σ_t δ_t λ^i_{t,ω} | `lambda_disc_G/L` |
| `D_i` | discount factor sum Σ_t δ_t (= T with no discounting) | `disc_G_sum` |
| `A_i` | risk aversion weight ∈ [0,1] | `A_G`, `A_L` |
| `α` | CVaR confidence (0.95 → worst 5%) | `alpha` |
| `τ_i` | bargaining power, τ_G + τ_L = 1 | `tau_G`, `tau_L` |
| `d_i` | disagreement utility (= utility at zero volume) | `d_G`, `d_L` |
| `δ_i` | Nash surplus u_i − d_i | `delta_G`, `delta_L` |

**Units.** Strike `S` is carried internally in EUR/GWh × 1e-3; multiply by 1000 for
EUR/MWh. Production is GWh, earnings MEUR. All EUR/MWh figures below are already
converted.

---

## Part 1: The three building blocks

### 1.1 Earnings are affine in the contract quantity

This is the single most important structural fact, and it is true for both contracts.

**Baseload.** The contract is a fixed volume `M` (GWh/year) settled against spot:

```
π_G(M,S; ω) = Y_G,ω + (D_G·S − Λ_G,ω)·M
π_L(M,S; ω) = Y_L,ω + (Λ_L,ω − D_L·S)·M
```

**Pay-as-produced.** The contract is a share `γ` of whatever the plant actually makes:

```
π_G(γ,S; ω) = (1−γ)·Y_G,ω + γ·S·B_ω   =   Y_G,ω + γ·(S·B_ω − Y_G,ω)
π_L(γ,S; ω) =      Y_L,ω             + γ·(Y_G,ω − S·B_ω)
```

(the second line uses symmetric information; with a belief wedge the buyer's `Y_G,ω`
is replaced by its own valuation `Y^L_{G,ω}` = `pap_gamma_coeff_L`.)

Write `x` for the contract quantity (`M` or `γ`). In both cases:

> **π_i is affine in x at fixed S, and affine in S at fixed x.**

No squared terms anywhere. The only non-linearity in the whole program is the product
`x·S`, which is why Gurobi needs `NonConvex=2`.

### 1.2 CVaR, and the one derivative rule you need

Utility blends the mean with the lower-tail CVaR:

```
u_i = (1 − A_i)·E[π_i] + A_i·CVaR_α(π_i)
```

CVaR in Rockafellar–Uryasev form is itself a maximisation:

```
CVaR_α(π) = max_ζ { ζ − (1/(1−α))·E[(ζ − π)^+] }
```

which is exactly the `ζ`/`η` machinery in the Gurobi model. The optimal `ζ` is the VaR,
and the expression collapses to *the average of the worst (1−α) fraction of scenarios*.

**The rule that unlocks everything (envelope / Danskin):**

```
d/dx CVaR_α(π(x))  =  E[ ∂π/∂x  |  ω ∈ tail_i ]
```

You differentiate *inside* the tail and hold the tail set fixed. This is legitimate
because the tail set only changes at ties, which are measure-zero. It means CVaR
derivatives are just tail averages, so no LP is needed.

### 1.3 The tail-adjusted expectation operator

Define, for party *i*:

```
⟨X⟩_i  :=  (1 − A_i)·E[X]  +  A_i·E[X | tail_i]
```

Then **the entire theory compresses to one line**:

```
du_i/dx  =  ⟨ ∂π_i/∂x ⟩_i
```

This `⟨·⟩_i` is precisely the paper's `φ_i` (eq. `phi_main`) generalised. Note that
`⟨·⟩_G` and `⟨·⟩_L` use **different tail sets**: the generator's worst scenarios are not
the buyer's worst scenarios. *That disjointness is the whole source of gains from trade.*

### 1.4 The Nash program

```
max_{x,S}   τ_G·ln(u_G − d_G)  +  τ_L·ln(u_L − d_L)
```

with `d_i` = the utility at `x = 0`. So by construction `δ_i = 0` at zero volume: a
contract must earn its way above the merchant baseline.

---

## Part 2: Baseload, the closed-form case

### 2.1 Marginal utility of volume

`∂π_G/∂M = D_G·S − Λ_G,ω`. The strike term `D_G·S` is **deterministic**, so it passes
through `⟨·⟩_G` unchanged:

```
du_G/dM = D_G·S − φ_G      where  φ_G := ⟨Λ_G⟩_G
du_L/dM = φ_L − D_L·S      where  φ_L := ⟨Λ_L⟩_L
```

With no discounting `D_i = T`, giving exactly the paper's

```
du_G/dM = T·S − φ_G ,   du_L/dM = φ_L − T·S
```

### 2.2 `S^{R*}` and `S^{U*}`: the viable strike band

Each party has a **break-even strike** where its marginal utility of volume vanishes:

```
generator:  T·S − φ_G = 0   →   S_G = φ_G / T
buyer:      φ_L − T·S = 0   →   S_L = φ_L / T
```

Below its break-even the generator wants *less* volume; above it, *more*. The buyer is
the mirror. Define

```
S^{R*} = min(φ_G, φ_L)/T        S^{U*} = max(φ_G, φ_L)/T
```

**What these are, plainly.** They are *not* the box you type into the config. There are
three distinct strike concepts and the paper conflates them in places:

| concept | symbol | value in this repo | what it is |
|---|---|---|---|
| box bounds | `S^R`, `S^U` | 40, 200 EUR/MWh | what the modeller allows the solver to try |
| viable band | `S^{R*}`, `S^{U*}` | 62.62, 73.71 EUR/MWh | where a mutually beneficial strike can exist |
| the solution | `S*` | 67.66 EUR/MWh | what the two parties actually negotiate |

The theorem's hypothesis is `S^R < S^{R*}` and `S^U > S^{U*}`, meaning **the box must be wider
than the viable band**, so the bound never binds and the geometry is data-driven. That
holds here (40 < 62.62, 200 > 73.71).

> ⚠️ **Inconsistency to fix in the paper.** Appendix D writes
> `S^{R*} ≤ S^R ≤ S ≤ S^U ≤ S^{U*}`, which is the *opposite* of the theorem's hypothesis
> `S^R < S^{R*}`, `S^U > S^{U*}`. The theorem's version is the correct one, and it is what
> the monotonicity lemma needs and what the code satisfies. Appendix D's inequality
> chain has its inequalities flipped.

### 2.3 Why the strike-direction locus has slope −1

Fix `M`, vary `S`. Then `∂π_G/∂S = D_G·M`, deterministic, so:

```
du_G/dS = D_G·M ,     du_L/dS = −D_L·M
⇒  du_L/du_G = −D_L/D_G = −1     (equal discounting)
```

**Economically:** at fixed volume, the strike is a *pure transfer instrument*. One euro
of utility the generator gains is exactly one euro the buyer loses. It moves the split,
never the size of the pie. (This is exactly Lesia's intuition in her §4.2.3 note, and
it is a theorem, not a guess.)

### 2.4 C1 and C2, derived

Along the boundary curve at `S = S^R`, the slope in utility space is

```
du_L/du_G = (du_L/dM) / (du_G/dM)
```

With `du_G/dM < 0` and `du_L/dM > 0` this is negative; take its magnitude:

```
slope  =  (φ_L − T·S^R) / (φ_G − T·S^R)
```

Now compare against the **reference rate 1** from §2.3. That comparison *is* C1/C2:

```
C1 (at M = M^R):   slope > 1     →  a barter set exists
C2 (at M = M^U):   slope < 1     →  the optimum is interior
```

**The economics in one sentence:** *adding volume is worth doing only while it moves
utility at a better-than-1:1 rate, because 1:1 is already available for free by moving
the strike.*

- **C1 fails** → the very first MWh already trades worse than 1:1 → no deal (Case 2).
- **C1 holds, C2 holds** → the rate starts above 1 and has fallen below 1 by the cap →
  it crossed 1 somewhere inside → interior `M*` (Case 1).
- **C1 holds, C2 fails** → still above 1 at the cap → the solver runs into the wall →
  `M* = M^U` (Case 3).

Because `φ_i` depends on the tail set, which depends on `M`, `φ_i` is *piecewise constant
in M*, so evaluate at `M^R` for C1 and at `M^U` for C2. That volume-dependence is the origin
of the two-regime split in Yu (2012).

### 2.5 Baseload, real numbers

```
                      slope     reference    verdict
M^R = 0             1.2829        1.0000     C1 HOLDS
M^U = 263 GWh/y     0.7705        1.0000     C2 HOLDS
→ unconstrained M* = 111.49 GWh/y = 42.4% of the cap, interior, Case 1 ✓
```

Baseload is **healthy**. Across every risk-aversion pair tested, `M*/cap` lands between
0.23 and 0.57, never at the boundary.

---

## Part 3: Pay-as-produced, what changes

### 3.1 The strike now multiplies a *random* volume

`∂π_G/∂S = γ·B_ω` is **stochastic**. It does *not* pass through `⟨·⟩` unchanged:

```
du_G/dS = γ·b_G       b_G := ⟨B⟩_G
du_L/dS = −γ·b_L      b_L := ⟨B⟩_L
⇒  du_L/du_G = − b_L / b_G      ← not −1, and it varies with (γ,S)
```

**This one line is the entire PAP extension of Yu (2012).** The reference rate is no
longer the constant 1; the loci curve. Note `b_G ≠ b_L` even under symmetric information,
because the two tail-adjusted averages are taken over *different tail sets*.

### 3.2 Break-even strikes become a ratio

```
∂π_G/∂γ = S·B_ω − Y_G,ω        ⇒  du_G/dγ = S·b_G − y_G ,   y_G := ⟨Y_G⟩_G
∂π_L/∂γ = Y_G,ω − S·B_ω        ⇒  du_L/dγ = y_L − S·b_L ,   y_L := ⟨Y_L^G⟩_L
```

Setting each to zero:

```
S^{R*} = min_i ( y_i / b_i )        S^{U*} = max_i ( y_i / b_i )
```

The threshold has changed character: from *a mean price* (`φ_i/T`) to *captured revenue
per unit of contracted volume* (`y_i/b_i`). Because `S` sits inside the tail set that
defines `⟨·⟩`, this is **implicit** and must be solved numerically, which is why the
paper says PAP is evaluated numerically while baseload is closed-form.

### 3.3 C1 and C2 for PAP

Identical logic, new reference rate:

```
C1 (at γ = γ^R):   (y_L − S^R·b_L) / (y_G − S^R·b_G)  >  b_L / b_G
C2 (at γ = γ^U):   (y_L − S^R·b_L) / (y_G − S^R·b_G)  <  b_L / b_G
```

Real numbers from this repo (`compute_gamma.py conditions`, default PAP config):

```
                      slope     reference    verdict
γ^R = 0             1.4939        1.0021      C1 HOLDS
γ^U = 1             1.1001        1.0169      C2 FAILS   ← still above the reference at the cap
γ   = 1.5           0.8702        1.0007      C2 would hold here
→ unconstrained γ* = 1.0721 > cap 1.0  ⇒ Case 3, boundary-constrained
```

Note how close the PAP reference rate `b_L/b_G` sits to 1 (1.002–1.017): the two
tail-adjusted production averages nearly coincide, so PAP's curved loci are only mildly
curved here. The curvature is real but small: the corner is driven by the *slope*, not
by the curvature.

So the paper's claim is exactly right *as a description*: **C2 fails at γ^U = 1, therefore
γ* = γ^U = 1.** The corner is not a bug. But note what C2 failing at the cap actually
means, which Part 5 takes up.

---

## Part 4: Where γ\* actually sits (filling the empty stub)

Appendix D currently has an empty subsection headed *"Interior optimum"*. Here is the
result that belongs there.

### 4.1 Derivation

Stationarity of `τ_G ln δ_G + τ_L ln δ_L` in both variables:

```
∂/∂S :   τ_G·(γ b_G)/δ_G  −  τ_L·(γ b_L)/δ_L  =  0
∂/∂γ :   τ_G·(S b_G − y_G)/δ_G  +  τ_L·(y_L − S b_L)/δ_L  =  0
```

The first gives, for γ ≠ 0:

```
(i)      τ_G·b_G/δ_G  =  τ_L·b_L/δ_L                    ← fixes S*
```

Substitute (i) into the second. Using `τ_L/δ_L = τ_G b_G /(δ_G b_L)`:

```
(S b_G − y_G) + (b_G/b_L)·(y_L − S b_L) = 0
S b_G − y_G + b_G y_L / b_L − S b_G     = 0
```

The `S b_G` terms cancel, leaving

```
(ii)     y_G / b_G  =  y_L / b_L                        ← fixes γ*
```

### 4.2 What (ii) says

`y_G/b_G` is the generator's break-even strike and `y_L/b_L` is the buyer's. So:

> **At the optimum, the two parties' break-even strikes coincide. Equivalently: γ\* is the
> volume at which the viable band `[S^{R*}, S^{U*}]` collapses to a single point.**

Any remaining gap between the two break-evens means there is still volume-surplus on the
table. C2 failing at the cap is exactly the statement *"the band had not yet collapsed
when we hit the wall."*

### 4.3 Numerical verification

`compute_gamma.py foc`, symmetric info, load_scale = 1.0:

| γ | S\* [€/MWh] | generator break-even | buyer break-even | gap |
|---|---|---|---|---|
| 0.81 | 69.005 | 64.453 | 74.778 | −10.325 |
| 1.01 | 69.293 | 69.185 | 74.414 | −5.228 |
| **1.21** | **69.958** | **74.182** | **74.187** | **−0.005** ← γ\* |
| 1.41 | 70.605 | 75.323 | 73.760 | +1.563 |
| 1.61 | 71.086 | 75.636 | 72.971 | +2.665 |

The gap crosses zero exactly at γ\*, and does so monotonically, so γ\* is unique. Verified
on four independent parameter settings.

---

## Part 5: Why γ\* > 1

### 5.1 First, kill the wrong explanation

Under symmetric information and equal discounting the **mean legs cancel exactly**:

```
∂E[π_G]/∂γ = S·E[B] − E[Y_G]  =  −( E[Y_G] − S·E[B] ) = −∂E[π_L]/∂γ
```

Verified numerically to machine precision: `dmean_G + dmean_L = 2.2e-16`. So in
expectation, raising γ is a *pure zero-sum transfer* that creates nothing. **γ\* > 1
cannot be the generator "chasing profit".** Something else must be going on.

Confirming this: at γ\* = 1.21, `S* = 69.96` vs `E[capture] = 69.00` €/MWh, a margin of
under 1.4%. The generator is not being handed a fat spread.

### 5.2 The real driver: the buyer wants a bigger hedge than the plant can supply

The toy model isolates this cleanly (`compute_gamma.py toy`). Start from a perfectly
matched pair, where the buyer consumes exactly what the plant produces, every scenario:

| perturbation | γ\* | S\* [€/MWh] |
|---|---|---|
| baseline (buyer = plant output) | **1.0000** | 77.000 |
| buyer **2×** the plant | **1.8632** | 86.266 |
| buyer **0.2×** the plant | **0.7191** | 62.563 |
| volume risk, mild (98–102 GWh) | 0.9842 | 76.881 |
| volume risk, strong (70–130 GWh) | 0.8692 | 79.054 |
| generator less risk-averse `A_G=0.2` | 1.0000 | 82.100 |
| generator more risk-averse `A_G=0.8` | 1.0000 | 71.900 |
| buyer more risk-averse `A_L=0.8` | 1.0000 | 83.900 |
| buyer 2× + mild volume risk | 1.3352 | 82.061 |

Read the three groups:

1. **Buyer size is the dominant lever.** γ\* tracks the buyer's hedging demand relative
   to the plant's physical output. Double the buyer and γ\* nearly doubles.
2. **Volume risk pulls γ\* down.** The more the plant's output varies, the worse a
   production-linked contract hedges, so less of it gets written.
3. **Risk aversion alone does not move γ\* at all** (three rows, all exactly 1.0000): it
   only moves the *strike*. Risk aversion **re-prices** the deal; it does not **resize**
   it. It only starts to affect γ\* once the buyer/plant symmetry is already broken.

Point 3 is worth pausing on: it means the γ heatmaps and the S heatmaps are answering
*different questions*, and the intuition "a risk-averse buyer hedges more" is **false** in
this model. A risk-averse buyer *pays more*, it does not *buy more*.

### 5.3 This is exactly what the real data shows

`load_scale` in the config controls buyer size. The plant produces 98.68 GWh/yr:

| `load_scale` | buyer [GWh/yr] | buyer / plant | γ\* |
|---|---|---|---|
| 0.1 | 14.62 | 0.148 | **0.4933** |
| 0.5 | 73.1 | 0.741 | 1.0543 |
| 1.0 | 146.2 | **1.482** | **1.2105** |
| 6.75 | 987 | 10.0 | 1.3627 |

**At `load_scale = 1.0` the buyer consumes 1.48× what the plant produces.** Of course the
unconstrained optimum wants γ > 1: the buyer's hedging demand simply exceeds this plant's
output, and nothing in the formulation forbids over-subscribing it.

> **The answer to give a reviewer.** γ > 1 is not "the generator sells power it does not
> have in order to profit". It is the model reporting that *the buyer's hedging demand
> exceeds this single plant's production*. In reality that buyer would contract with
> several generators; here there is only one, and no constraint says a plant may not be
> over-subscribed. γ > 1 is a **missing-constraint artefact**, and the missing constraint
> is a physical/credit one, not an economic one.

### 5.4 What CVaR is doing (and what it is not)

CVaR plays three distinct roles. Keeping them separate resolves most of the confusion.

**Role 1: CVaR is the *only* reason any contract exists.** The mean leg is exactly
zero-sum (§5.1). If both parties were risk-neutral there would be nothing to bargain
over. Gains from trade come entirely from the fact that the two parties' tail sets are
**disjoint**: in Toy A the generator's worst case is the low-price scenario (ω=1) and the
buyer's is the high-price scenario (ω=5). Trade swaps tail risk that each values
differently.

**Role 2: CVaR sets the *brake* on γ, through a tail flip.** Look at the merchant
coefficient `(1−γ)` in `π_G = (1−γ)·Y_G + γ·S·B`:

| regime | coefficient on `Y_G` | generator's worst case is… |
|---|---|---|
| γ < 1 | positive | **low**-revenue (low-price) scenarios |
| γ = 1 | zero | pure volume risk; price risk fully removed |
| γ > 1 | **negative** | **high**-revenue (high-price) scenarios |

The generator's tail *flips identity* as γ crosses 1. Measured on the real data (tail
average capture price, €/MWh):

| γ | 0.25 | 0.50 | 0.75 | 1.00 | 1.25 | 1.50 |
|---|---|---|---|---|---|---|
| G-tail capture | 56.41 | 56.75 | 58.70 | **68.61** | 80.51 | 82.13 |
| L-tail capture | 66.71 | 56.89 | 56.34 | 56.20 | 56.19 | 56.17 |

(unconditional mean = 68.99). The generator's tail migrates from the cheap scenarios to
the expensive ones, passing through the unconditional mean at exactly γ = 1, the point
where its payoff `S·B` carries no price risk at all. Past that it is **short**, and the
CVaR leg turns hard negative: `dcvar_G` goes `+22.7 → −1.8 → −21.5` across γ = 0.25 → 1.0
→ 1.2. That sign flip is what stops γ growing.

(The table above is the *default* config, which carries a 5% buyer price bias
`K_L_price=0.05`; there the mean legs do **not** cancel, since `dmean_G + dmean_L = +6.81`,
because the belief wedge manufactures phantom surplus. Set `K_L_price=0` to recover the
exact cancellation of §5.1. The tail-flip mechanism is identical either way.)

Connecting to §4.2: this tail migration is precisely *why* the generator's break-even
strike `y_G/b_G` rises with γ (64.5 → 69.2 → 74.2). γ\* is where it catches the buyer's.

**Role 3: CVaR is the only thing bounding γ at all.** Remove the generator's risk
aversion and γ\* diverges:

| `A_G` | 0.00 | 0.10 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---|---|---|---|---|---|
| γ\* | >12 (unbounded) | >12 (unbounded) | 1.14 | 1.07 | 1.04 | 1.04 |

With `A_G = 0` and any mean wedge at all, the problem has **no interior optimum**: γ runs
away. The generator's own tail aversion is the sole brake.

### 5.5 Why baseload is immune

Under baseload the contracted volume `M` is **decoupled from realised production**. Raising
`M` therefore adds *volumetric mismatch risk*, since the generator owes `M` MWh whether or not
the wind blew, and that penalty grows without bound in the tail. There is a natural
interior brake, so C2 holds and `M*` lands at ~42% of the cap.

Under PAP the contracted volume *is* `γ ×` realised production, so for γ ≤ 1 there is no
mismatch at all: the hedge is perfect and free of volume basis. Nothing brakes it until
γ passes 1 and the merchant leg changes sign. **PAP's very strength as a hedge, its perfect
proportionality, is what removes its natural stopping point.**

That is a clean, publishable structural statement, and it is the honest reading of the
paper's own Theorem 1.

---

## Part 6: Ways to make γ ≤ 1 endogenous

Four options, in increasing order of structural change:

1. **Keep the cap, report it honestly.** γ\* = γ^U is Case 3 of your own theorem. State
   that C2 fails and the negotiation reduces to the strike alone. Costs nothing, but the
   γ heatmap stays degenerate.
2. **Buy-back premium (recommended).** Covering a short position needs power bought at
   spot *plus* an imbalance/liquidity premium `φ`, applied to the `(γ−1)` leg only.
   Tested (`compute_gamma.py spread`):

   | φ | 0.00 | 0.02 | 0.05 | **0.10** | 0.20 |
   |---|---|---|---|---|---|
   | γ\* | 1.2105 | 1.1268 | 1.0542 | **1.0000** | 1.0000 |

   A 10% premium makes γ\* = 1 the **endogenous** optimum rather than a box constraint.
   Cheap to implement, physically defensible, and it converts an artefact into a result.
3. **Size the buyer to the plant.** Much of the effect is that the buyer is 1.48× the
   plant. Justifying `load_scale` explicitly (or setting buyer ≈ plant) is the
   lowest-effort fix, but note `load_scale = 0.1` gives γ\* = 0.49, which is *also* hard
   to defend as it implies a buyer one-seventh the plant's size.
4. **Capture rate on the contracted leg** (Appendix F.3 vs main-body Eq. 4.3) or Viktor's
   curtailment/delivery mismatch. Bigger structural changes; see the separate
   `gamma_corner_note`.

---

## Part 7: Summary card

| question | answer |
|---|---|
| What is `S^{R*}`/`S^{U*}`? | Each party's break-even strike, min/max. The band where a mutually beneficial deal exists. Not the config box. |
| What is `M*`/`γ*`? | The negotiated quantity. Located where the two break-even strikes coincide. |
| What are C1/C2? | Slope tests at the lower/upper quantity bound against the reference transfer rate (1 for baseload, `b_L/b_G` for PAP). |
| Why does C2 fail for PAP? | Because unconstrained γ\* = 1.07–1.21 exceeds the cap of 1. C2 is evaluated *at the cap*. |
| Why is γ\* > 1? | The buyer's hedging demand (1.48× the plant) exceeds the plant's output, and no constraint forbids over-subscription. |
| Is it a risk-appetite effect? | **No.** Risk aversion moves the *strike*, not the *volume* (proven in the toy). |
| What bounds γ at all? | The generator's own CVaR, via the tail flip at γ = 1. With `A_G = 0`, γ diverges. |
| Why is baseload fine? | `M` is decoupled from production, so volume mismatch provides a natural interior brake. |
