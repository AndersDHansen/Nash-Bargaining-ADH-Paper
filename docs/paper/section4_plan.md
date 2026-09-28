# Section 4 (Numerical Results): storyline, runs, and config changes

Target: `Nash_Bargaining_Paper___Anders(4)/sections/04_results/`, which currently holds
Lesia's outline as `%` comments in `04_2_value_creation.tex` and `04_3_value_allocation.tex`,
plus drafted prose and real figures in `legacy/`.

---

## 1. The storyline in one paragraph

> Two parties with different attitudes to price risk can create value by trading it. The
> **size** of that value is set by how *different* they are, not by how risk-averse
> either one is in absolute terms. The **split** of that value is set by the strike price
> and by bargaining power. Volume and price therefore do two separate jobs: **volume sizes
> the pie, the strike slices it.** Baseload and pay-as-produced differ in how well volume
> can do its job: baseload's fixed volume carries a volumetric mismatch that naturally
> caps the efficient contract size, whereas pay-as-produced is a frictionless
> proportional hedge with no natural stopping point, so its optimal share runs to
> whatever bound the modeller imposes.

That last clause is the honest framing of the γ problem, and it makes the PAP result a
*finding* rather than an embarrassment. See §5.

**One structural result you should lead with, because it is counter-intuitive and you can
prove it:** risk aversion moves the **strike**, not the **volume**. In the symmetric toy
model, varying `A_G` from 0.2 to 0.8 and `A_L` up to 0.8 leaves γ\* at *exactly* 1.0000
while moving S\* from 71.9 to 83.9 €/MWh (`analysis/compute_gamma.py toy`). This directly
answers Lesia's own margin note in §4.2.3 ("*does it make sense to focus only on volume
… the strike price should only/mostly shift how the surplus is split?*"). She is right,
and it is a theorem, not an intuition. At fixed volume the strike-direction locus has
slope exactly −1 for baseload, a pure one for one transfer that creates nothing.

---

## 2. What each of Lesia's subsections asks for, and how to produce it

| § | Lesia asks for | Sweep to run | Metric / figure |
|---|---|---|---|
| **4.2.1 Joint surplus** | 2 heatmaps side by side, one per varying parameter (risk aversion, bias), showing total surplus | `risk_aversion` + `asymmetric_info`, **both contracts** | `δ_G + δ_L` from `grid_delta_G.csv` + `grid_delta_L.csv` |
| **4.2.2 Settlement type** | 2 heatmaps side by side, one per contract type, risk preferences only | `risk_aversion` for PAP and baseload | Panel (a) joint surplus BL, (b) joint surplus PAP; consider a third "which wins" panel |
| **4.2.3 Contracted volume** | heatmaps of contract terms | same `risk_aversion` sweep | `grid_M_MWh_h.csv` (BL), `grid_gamma.csv` (PAP), **this is where γ=1 shows up** |
| **4.3.1 Symmetric NBS** | strike + surplus allocation vs relative risk aversion, τ fixed | same `risk_aversion` sweep | `grid_S_EUR_MWh.csv`; add derived share `δ_G/(δ_G+δ_L)` |
| **4.3.2 Bargaining power** | strike + surplus allocation vs τ_L, repeated per risk-aversion level | `bargaining_power` (already has `A_L: [0.25,0.5,0.75]`) | `results_combined.csv`, which exactly matches her "2nd analysis" |
| **4.3.3 Incomplete information** | overlapping distributions of acceptable strike for buyer vs seller | `load_risk_aversion` (A_L~N(0.3,0.1), 500 draws) | KDEs of `S*`, `S_R*`, `S_U*`; notebook cell 25 already does this |

**Good news:** every sweep type she needs already exists in `config/sensitivity/`. The
plotting for most of it already exists in `results/plotting_notebook.ipynb`. The gap is
that nothing currently *runs the sweeps and then plots them* in one reproducible pass;
the notebook reads CSVs that are no longer on disk.

---

## 3. Config changes needed

### 3.1 Required

**Reduce the `asymmetric_info.yaml` grid.** Currently 101 × 101 =
10,201 solves ≈ 8.5 hours at ~3 s/solve. Also ±0.5 is an implausible bias (±50% price
belief error).

```yaml
K_G_price: {start: -0.15, end: 0.15, n: 13}
K_L_price: {start: -0.15, end: 0.15, n: 13}     # 169 points ≈ 8 min
```

**Decide `load_scale` and justify it in the text.** This parameter is doing far more work
than its name suggests. It silently sets the buyer's size relative to the plant (98.7
GWh/yr), and it is the dominant driver of γ\*:

| `load_scale` | buyer [GWh/yr] | buyer / plant | γ\* (as-is) | γ\* (with resale haircut) |
|---|---|---|---|---|
| 0.10 *(current)* | 14.6 | 0.148 | 0.4933 | 0.1505 |
| 0.30 | 43.9 | 0.444 | 0.8671 | 0.4506 |
| **0.54** | **79.0** | **0.800** | 1.0758 | **0.7990** |
| 1.00 | 146.2 | 1.482 | 1.2105 | 1.2034 |

**Recommendation:** set `load_scale = 0.54`, so the buyer consumes 80% of plant output,
and add the resale haircut described in §5. That combination yields γ\* = 0.799, matching
the 80% hedge ratio typical of real pay-as-produced deals, and it yields it *for the right
reason*: the contract then covers exactly the buyer's own consumption (contracted / buyer
need = 1.00x across the whole range). State the MWh figure explicitly in §4.1 and stop
treating `load_scale` as a tuning knob.

Note the trap in the "as-is" column. At `load_scale = 0.30` you also get γ\* ≈ 0.87, which
*looks* defensible, but the contract is then twice the buyer's consumption. The number
looks right for the wrong reason. Without the haircut, a sub-unity γ is not evidence of
sensible sizing.

**Fill in `04_1_case_study.tex`**. It is currently two lines. It needs: DK2 data
provenance, 20-year horizon, 2000 reduced scenarios, 30 MW plant / 98.7 GWh per year,
buyer size, α = 0.95, strike box [40, 200] €/MWh, and the resulting viable band
[62.6, 73.7] €/MWh.

### 3.2 Recommended

- Add `gamma_max: 1.0` **explicitly** to `default_pap.yaml` with a comment saying it is a
  *physical* cap, not an economic one (it is already 1.0; the comment is what's missing).
- For §4.3.3's second analysis (does incomplete information matter less to a very
  risk-averse or powerful player?), add discrete `A_G` and `tau_L` lists to
  `load_risk_aversion.yaml`.

---

## 4. Action list, in order

1. **Fix `load_scale`** and write §4.1 Case Study Setup around the chosen number.
2. **Shrink `asymmetric_info.yaml`** to 13 × 13.
3. **Run the sweeps** (≈40 min total on this machine at ~3 s/solve):
   ```bash
   for exp in default_baseload default_pap; do
     for s in risk_aversion bargaining_power contract_size load_risk_aversion asymmetric_info; do
       uv run python main.py experiment=$exp sensitivity=$s
     done
   done
   ```
4. **Write an orchestration script** (`analysis/run_all_results.py`) that does step 3 and
   then executes the notebook, so the whole results section is one command. This is the
   reproducibility ask.
5. **Add two derived metrics** to the postprocessor or notebook: joint surplus
   `δ_G + δ_L` and generator surplus share `δ_G/(δ_G + δ_L)`. Both §4.2.1 and §4.3.1 need
   them and neither is emitted today.
6. **Write §4.2 and §4.3** against the storyline in §1, pulling the drafted prose in
   `legacy/04_3_risk_aversion.tex` and `legacy/04_4_bargaining_power.tex`. Much of it is
   already written and just needs condensing into Lesia's structure. Note the red
   `\textcolor{red}{...}` spans in the legacy file are unverified numbers; re-extract them
   from the fresh sweeps rather than trusting them.
7. **Decide the PAP volume question** (§5 below) before writing §4.2.3.

---

## 5. The decision you have to make about §4.2.3

The PAP volume panel is currently degenerate: γ\* = 1 in essentially every cell, so the
heatmap is one flat colour. Three options:

**Option A. Report it as Case 3** (lowest effort, defensible).
Keep `gamma_max = 1`, state that condition C2 fails at the cap so the optimum is
boundary-constrained, and that the PAP negotiation therefore reduces to the strike alone.
Replace the flat γ heatmap with the *S* heatmap plus one sentence. This is already what
`03_2_barter_set.tex` claims, and it is true. Weakness: a reviewer may read "our model
always returns the bound" as a modelling failure rather than a result.

**Option B. Add a resale haircut, or a buy-back premium** (recommended).

The root defect is that Anders' buyer can resell contracted volume above its own
consumption at the full market price, with no penalty, so nothing ties contract size to
demand. Two ways to close it, addressing opposite sides of the trade:

*B1, resale haircut on the buyer (preferred).* Value consumed power at avoided cost but
resold surplus only at market, so surplus carries a haircut `h`. This is the asymmetry
Viktor's willingness-to-pay formulation creates, and it is the mechanism Anders' model is
missing. On the shipped default:

| `h` | 0.00 | 0.05 | 0.10 | 0.25 | 0.50 |
|---|---|---|---|---|---|
| γ\* | 1.0721 | 0.9595 | 0.7949 | 0.1499 | 0.1413 |
| contracted / buyer need | 7.24x | 6.48x | 5.37x | **1.01x** | 0.95x |

*B2, buy-back premium on the generator.* A premium φ on the `(γ−1)` leg, reflecting the
imbalance and liquidity cost of covering a short. This targets the generator's short
position rather than the buyer's over-purchase, and is the right tool when the buyer is
larger than the plant.
Covering a short needs power bought at spot *plus* an imbalance/liquidity premium φ on
the `(γ−1)` leg. Tested in `analysis/compute_gamma.py spread`:

| φ | 0.00 | 0.02 | 0.05 | **0.10** | 0.20 |
|---|---|---|---|---|---|
| γ\* | 1.2105 | 1.1268 | 1.0542 | **1.0000** | 1.0000 |

A 10% premium makes γ\* = 1 the **endogenous** optimum. This converts "our bound binds"
into "the economics select full coverage", gives you a real sensitivity axis (φ), and is
a ~15-line model change. It also pre-empts the reviewer question directly.

**Option C. Cut the PAP volume analysis**, keep PAP earnings.
Present baseload as the contract where volume is genuinely negotiated, and PAP only for
the earnings-distribution comparison (`legacy/04_3_risk_aversion.tex` §"Pay-as-Produced
earnings" is already drafted and makes a good point about asymmetric risk redistribution).
Weakness: loses half the two-contract comparison the paper promises.

**My recommendation: B, with A as the fallback** if there is no time for a model change.
Do **not** present γ = 1.12 as a headline contract term. It depends entirely on an
unenforced bound and will draw fire.

---

## 6. Things to flag to Anders

1. **Appendix D inequality chain is backwards.** It writes `S^{R*} ≤ S^R ≤ S ≤ S^U ≤ S^{U*}`,
   but the theorem requires `S^R < S^{R*}` and `S^U > S^{U*}` (box wider than the viable
   band). The theorem's version is correct and is what the code satisfies.
2. **Appendix D §"Derivation of C1", §"Derivation of C2", §"Interior optimum" are empty
   stubs.** The derivations are now written up in `docs/theory/barter_set_and_gamma.md`,
   including a result the paper does not currently state: at the optimum the two parties'
   break-even strikes coincide, `y_G/b_G = y_L/b_L`. That is the missing "Interior
   optimum" content, verified numerically to 5e-3.
3. **Main-body Eq. 4.3 vs Appendix F.3.** The contracted leg carries no capture rate in
   the main body and in the code, but does in Appendix F. Which is intended?
4. **`load_scale` needs a physical justification**, see §3.1.
