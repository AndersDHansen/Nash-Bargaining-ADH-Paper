# Roadmap to EJOR submission

Living checklist for the base paper. Latest status: section 0c (2026-10-02); the sections
below it are older and kept as a record. Day-to-day state: `notes/session_handoff.md`.
Companion notes: `docs/theory/gamma_drivers.md` (γ diagnosis), `docs/theory/axiom_choice.md`
(why the NBS), `docs/paper/section4_plan.md` (earlier sweep-level plan, partly superseded).

**Two releases.** The base paper is submission-ready *without* beliefs and private
information, provided the research question and gaps no longer promise them. Everything
about incomplete information moves to a second release.

---

## 0c. Status 2026-10-02: Lesia's meeting feedback, re-examination, plan for Section 4

**State.** Overleaf b5a8cb2 compiles to 22 pages; Sections 1-5 and the appendices are written. The
user moved the earnings subsection ahead of risk preferences (order now: case, barter set, earnings,
risk preferences, bargaining power, Buyer size, beliefs). All Section 4 numbers were recomputed from
the runs (`notes/analysis/sec4_large_buyer_numbers.py`) and match the text. Nothing new has to be run:
every item below comes from the existing sweeps and the scenario files
(`notes/analysis/lesia_meeting_checks.py`).

**Re-examination (whole paper).** The argument holds and the sections connect: exposure and
preferred volume (1.1) -> earnings, utility, surplus (2) -> conditions (C1)/(C2) and two theorems (3)
-> cases and numbers (4) -> conclusion (5). Still wrong or broken:
- 4.1 table: "Buyer consumption (expected) 58.5 GWh/yr" (must be 146.2), duplicate row, P95 155.0 (154.9).
- 4.2: placeholder figure (two legacy images, caption "Caption"); title says "Bargaining set".
- 2.1: "with divergent beliefs, each party also expects to gain from the price difference itself" is
  false when the Generator is the more optimistic party, and contradicts 4.7.
- 3.3 / 3.4: bounds M^R, gamma^R, gamma^U are not defined (Section 2 uses 0 and 1); the settlement is
  printed with the yearly price and no sum over hours, unlike (pi_G_BL); the solver is not named.
- Undefined: `Boyd2004Convex`, `Shapiro2009Lectures`, `TODO`, `TODO_cost_of_capital`, `tab:summary_stats`.
- Wording: 2.1 utility sentence and "Here they are defined here"; 1.1 "reducing the risks of ...
  cannibalisation" (baseload does not); "reservation price" (Section 1) against "reservation strike"
  (Sections 3-4); abstract "joint gain" and "only of the strike" (abstract is edited last).
- 4.4 ends with the risk-removed sentence (29 % / 74 %, 81 % / 46 %), which now repeats the earnings
  subsection in another measure.

**Lesia's feedback (meeting of 2026-10-02) and verdict.** She saw the paper and the seven figures in
`lesia_figures/`.

| # | Her point | Verdict | What it becomes |
| --- | --- | --- | --- |
| 1 | Structure works | - | keep |
| 2 | Volume heat maps: show the Buyer's P50 consumption | applicable | mark the two preferred volumes and the expected consumption on the colour bar and in the caption |
| 3 | Belief surplus is virtual | applicable, strong | add the surplus valued at the scenario prices to the belief figure; fix the 2.1 sentence |
| 4 | How much is a contract worth: Nash product, individual or joint surplus? | individual surplus w_i (per party) and joint surplus W (total); not the Nash product | state that w_i is the sure amount a party would pay for the contract; give W per contracted MWh |
| 5 | Surplus = money part + CVaR part; visualise | applicable | new small bar figure at the base case |
| 6 | Earnings before sizes, maybe also surpluses | applicable (earnings already moved) | value block in 4.2, then earnings, then terms |
| 7 | A surplus comparison | applicable per party | the bar figure of point 5 compares both structures per party |
| 8 | Buyer-size figure: P50 load line | applicable for baseload; for PAP the line must be in value | reference lines in `buyer_size` |
| 9 | One bargaining-power figure | applicable | keep `strike_vs_size`, drop `bargaining_power` |
| 10 | Layout of the barter-set figure | applicable (assumed: the 4.2 figure) | build the real two-panel figure |
| 11 | Surplus heat map and the split between parties | W heat map yes; split heat map no | W heat maps replace the PAP strike heat map |

**Verified numbers behind the verdicts.**
- Expected consumption 16.69 / 7.91 / 4.17 MW (large / similar / small Buyer); the Buyer's preferred
  baseload volume is 4 % above it (17.39 / 8.24 / 4.35 MW). Generator: expected output 11.26 MW,
  preferred volume 7.82 MW. In energy the three Buyers are 1.48 / 0.70 / 0.37 of the plant, in value
  2.11 / 1.00 / 0.53; the preferred PAP shares follow the value figure (cap / 0.97 / 0.51).
- Each surplus = expected payment received + own risk aversion x risk removed (exact to 1e-12).
  Base case, baseload: Generator +9.51 + 4.41 = 13.92; Buyer -9.51 + 23.43 = 13.92 MEUR.
  PAP: Generator +1.03 + 12.26 = 13.29; Buyer -1.03 + 14.54 = 13.52 MEUR.
- W per contracted MWh: 11.89 EUR/MWh (baseload, equal to the gap between the reservation strikes)
  and 13.59 EUR/MWh (PAP). The surplus is 8.3 % of the Generator's expected merchant revenue and
  3.9 % of the Buyer's expected cost.
- Split of W at equal bargaining power: Generator share 0.500-0.501 (baseload), 0.491-0.500 (PAP)
  over the whole risk grid, so a heat map of the split would show one colour.
- Beliefs, surplus valued at the scenario prices (no shift): baseload 27.8 MEUR at gap 0, 24.7 at
  +0.10, 19.2 at +0.15 and -16.4 from +0.20 (30 MW), against 108 to 294 MEUR perceived; PAP stays at
  26.8 for every gap from -0.05 to +0.50 against up to 111 MEUR perceived. At +0.20 the party whose
  belief is wrong loses 70.2 MEUR under baseload and 3.3 MEUR under PAP.
- Structures compared per party over the risk grid (120 cells): both parties gain more under
  baseload in 65 (A_L/A_G >= 1), both under PAP in 49 (A_L/A_G <= 0.8), 6 split or tied. Not in the
  paper; needs a yes.

**Plan (nothing to run).**
1. Quick text fixes: 4.1 table, 4.2 title, the 2.1 belief sentence.
2. Decisions by the user (below), then figures as `Plotter` methods, one per figure, proposed first:
   real barter-set figure (4.2); `surplus_parts` (new); colour-bar marks on `risk_preferences`
   baseload; W heat maps in place of `risk_preferences_pap`; reference lines in `buyer_size`; second
   curve in `price_beliefs`; `bargaining_power.pdf` dropped. Figure count stays at ten.
3. Short text blocks and captions for 4.2, 4.4, 4.5, 4.6, 4.7 (Section 4 must not grow: each addition
   replaces something, e.g. the risk-removed sentence and the PAP plane formula).
4. Then the Sections 1-3 leftovers listed above and in `notes/session_handoff.md`.

**Decisions needed.** (a) w_i and W as the value measures, with W per contracted MWh; (b) the
money / risk bar figure; (c) the belief figure with the surplus at scenario prices, and the wording
("perceived" against "valued at the scenario prices"); (d) reference lines: expected consumption for
baseload, consumption relative to output in value for PAP, and whether to show the Generator's
expected output; (e) which bargaining-power figure stays; (f) W heat maps instead of the PAP strike
heat map; (g) whether the per-party structure comparison enters 4.4 as one sentence; (h) confirm that
"barter set figure 4" means the 4.2 figure.

## 0b. Status 2026-09-28: Buyer size, manuscript review, Lesia's revisions next

**Supersedes the load_scale decision in 0a.** Lesia objected that our baseload volume
heatmap (load_scale 0.4) reverses Anders' trend. Diagnosis (verified 2026-09-25/27):

- Plots are correct (grid rows = A_G, cols = A_L on both branches); results are correct
  (1-D reconstruction matches both solvers to 0.02 MW; PAP brute force matches exactly).
- Cause = Buyer size, not the capture-rate fix and not load stochasticity. Making the load
  and its capture rate deterministic moves the Buyer's preferred volume by < 1%
  (consumption CV 0.8% vs price 8.5% over 20 years).
- Mechanism: baseload M* is a risk-weighted compromise between two **preferred volumes**
  (each party's optimum when only it is risk averse), each ~ its value-weighted volume
  (CR x mean volume). Generator 7.82 MW (fixed); Buyer grows linearly with its size.
- **Value ratio** VR = E[sum CR_L lam P_L] / E[sum CR_G lam P_G] = 2.1108 x load_scale.
  One threshold (VR ~ 1) flips the baseload trend AND caps the PAP share:
  1. VR < 1 (small Buyer, ls 0.4, VR 0.84): risk-averse Buyer shrinks M; M nearly flat
     (7.0-7.8 MW); PAP gamma interior (0.82-1.0). Our old results.
  2. VR ~ 1 (ls 0.474): preferred volumes coincide; risk sets price, not size; PAP gamma
     reaches 1 (0.989 at VR 1, 1.000 at ls 0.5).
  3. VR > 1 (large Buyer, ls 1.0, VR 2.11, Anders' size): intuitive trend, M 7.8-17.4 MW;
     PAP gamma = 1 at every risk preference; only the strike is negotiated.
  Consumption = production in MWh at ls 0.68, but the balance in value is at ls 0.47,
  because one MWh of wind hedges only ~0.7 MWh of consumption (CR_G 0.72 vs CR_L 1.03).
- At ls 1.0 the baseload joint gain DEcreases with A_G in part of the grid (25/90 steps
  on 10x10): the contract is sized for the Buyer, so the Generator is over-hedged.
  "Risk aversion enlarges the gains" (C4, abstract) holds only for the Buyer there.
- Side observation, not yet agreed as a claim: PAP gives a slightly larger joint gain for
  small Buyers (ls <= 0.6), baseload for large ones (ls >= 0.8); differences <= ~5%.

Proposal sent to Lesia: base case = large Buyer (ls 1.0), plus a Buyer-size subsection with
one figure (baseload M* with the two preferred volumes, PAP gamma*, vs value ratio; the
three regimes marked). Awaiting her revisions. "Preferred volume" and "value ratio" still
need final agreement before entering the paper.

**Baseload needs no solver for M (keep for Section 3.3 and as a check).** The strike is a
pure transfer, so the joint gain Delta(M) = A_G R_G(M) + A_L R_L(M), R_i = CVaR_i - E_i
(measured from M = 0), does not depend on S or tau: M* = argmax Delta (1-D search;
Lemma C2 / Theorem DE_main in Appendices D-E). The NBS then sets the price:
S* = S_Gen + (1 - tau_L)(S_Buyer - S_Gen), where S_Gen, S_Buyer are the reservation
strikes at M*. Verified: ls 0.4 window 109.82-126.84 EUR/MWh; tau 0/0.5/1 -> 126.84 /
118.33 / 109.82 vs solver 126.85 / 118.33 / 109.81. This is why the strike is linear in
tau. PAP does not separate (strike multiplies stochastic output) and needs the full model.
Script: notes/analysis/baseload_volume_1d.py.

**Runs available (all verified).**
- load_scale 1.0: `baseload_loadscale_1`, `pap_loadscale_1` x {risk_aversion (BL 10x10,
  PAP 16x16), bargaining_power, contract_size (BL via contract_size_wide, 0.5-30 MW),
  asymmetric_info 21x21}. The 4 NaN cells in BL asymmetric_info and the 9 in BL
  contract_size are no-deal cells.
- Buyer size: `results/single_run/buyer_size_{baseload,pap,baseload_genpref,
  baseload_buyerpref}_{0p2,...,1p2}` (10 load scales incl. 0.474 = VR 1; genpref A_L = 0,
  buyerpref A_G = 0).
- Configs added: `config/experiment/{baseload,pap}_loadscale_1.yaml`,
  `config/sensitivity/contract_size_wide.yaml`; `risk_aversion.yaml` now n = 10.
- Plotter still hard-codes `default_baseload` / `default_pap` (lines 193, 256-257, 311,
  378-379, 489, 575-576); needs the new names, plus a `buyer_size` method (user builds).

**Manuscript review 2026-09-25 (full list given in chat; fixes drafted for Sec 1-3).**
- 45 pages in EJOR format (11 pt, 1.5 spacing; limit 30): appendices to online
  supplement, main text to trim ~6 pp (merge 3.3/3.4, cut App C to 0.5 pp, App A, repeated
  utility equations in Sec 2, lit-review class 1).
- Blunders: convexity (z = xS lifting makes the NBS a concave program; paper says
  non-convex); 3.2 says PAP gamma* = 1 and "curved" frontier; abstract/C4 "compresses the
  barter set"; bankability vs merchant disagreement point; main Theorem 1 differs from the
  appendix theorem; months vs years; units of M; C3 "U is not convex" unverified;
  "bargaining set" is the wrong term (use barter set); tau endpoints; Kalai citation wrong
  in 1.3 (ProportionalComparisons -> Kalai1977Nonsymmetric); Figure 6 caption says three
  A_L but draws two.
- Section 1 edits applied by the user in part (C4, coupling sentence); remaining drafts
  are in the chat history of 2026-09-25/28.

Next: Lesia's revisions -> sharpen the Section 1 storyline; rework Section 4 around the
large-Buyer base case with the Buyer-size subsection; decide D1 (4.6).

## 0a. Status 2026-09-25: finish the paper as it stands

Decision: finish the base paper at load_scale 0.4. A subsection on Buyer size (volume
split and earnings "funnel", as in Anders' load_scale 1.0 results; load_scale 0.2 gives a
similar spread with PAP gamma likely interior) is a candidate for later, not now.
Handoff: `notes/session_handoff.md`. Drafts: `notes/section4_drafts.md` (both private).

Section 4 figures (single column, 8 pt, in `Plotter`; each skips with the `uv run`
command when its sweep is missing; include at natural size):

| Sec | Figure (method) | Sweeps needed | State |
| --- | --- | --- | --- |
| 4.1 | `case_study_summary` + parameter table | scenarios | figure done; text + table drafted |
| 4.2 | `bargaining_set` | risk_aversion + scenarios | user rebuilding in Anders' notebook style |
| 4.3 | `risk_preferences` -> baseload and PAP figures | risk_aversion | done, drafted |
| 4.4 | `bargaining_power` (strike vs tau_L) | bargaining_power | done, drafted |
| 4.4 | `strike_vs_size` | contract_size, bargaining_power | done, drafted |
| 4.5 | `earnings` (2x2) | risk_aversion | done, drafted |
| 4.6 | `price_beliefs` | asymmetric_info (21x21, run) | done, drafted (if D1) |

- [x] 4.1, 4.3, 4.4, 4.5, 4.6 drafted (notes/section4_drafts.md)
- [ ] 4.2 figure (user) and text
- [ ] D1 decision; optional true-price paragraph in 4.6
- [ ] Align A_L sets in 4.4; PAP risk grid 31x31 (run in progress 2026-09-25)
- [ ] Appendix F fixes (list at the end of the drafts file)
- [ ] Section 5

Out of the base paper: KDE-overlap figure (release 2, as an acceptance-probability
curve), joint-gain heatmap (replaced by r_G/r_L in the 4.3 text), risk premium S - S0
(dropped), CVaR line plots, full-range bargaining-set view. Terminology: "divergent
(heterogeneous) price beliefs" for K, "private (incomplete) information" for unknown
types; never "asymmetric information" for K.

## 0. Where we are  (status 2026-09-23, end of day)

Done:

- [x] Section 1 rewritten and source-verified; three gaps; contributions aligned.
- [x] Deep review of the manuscript against model, code and data.
- [x] gamma* diagnosis complete, with a first-order condition matching the solver.
- [x] Capture-rate fix **committed** (`f63c637`) and scenarios regenerated: the 500 and
      2000 reduced sets both carry CR_G = 0.724 and CR_L = 1.031.
- [x] Section 4 structure agreed; six subsection files exist and are wired into main.tex.
- [x] Repo cleaned: `Code/`, dockerfiles, superpowers scaffolding, stale plots and solar
      data removed; `analysis/` and `plotting/` moved under `src/`; notes and sources
      moved to a git-ignored `notes/`; config trimmed 427 -> 274 lines; README rewritten.
- [x] Plotting rebuilt as `Plotter` + `plotter_config`, wired into `Runner`. Data layer,
      MissingResults reporting and probability-weighted statistics in place and verified.
- [x] Pipeline runs end to end (`main.py ... scenario_gen=100_scenarios` verified).

Not done:

- [ ] **No sweep has been run.** `results/sensitivity/` is empty; only one single run
      exists, and it is at the old base case (`load_scale 0.6`, `A_L 0.8`, gamma* = 1).
- [ ] **All six figure bodies are stubs** (`raise NotImplementedError`).
- [ ] Section 4 prose: 0 words. Section 5: 0 words.
- [ ] No tests anywhere.
- [ ] Mechanical manuscript defects from the September review are all still open.
- [ ] Still IEEEtran with numeric citations; EJOR needs elsarticle and author-year.

## 1. Decisions to take first

| # | Decision | Recommendation | Blocks |
| --- | --- | --- | --- |
| D0 | Section 4 structure | **Agreed**: five subsections, §2 | — |
| D1 | Price bias K in the base paper? | Yes, minimally: in the formulation, K = 0 for headline results, one existence figure | Sec 2, 4.6, RQ |
| D2 | Buyer size (`load_scale`) | **0.40** (58.5 GWh/yr, 59% hedge ratio): γ* runs 0.86–0.99 over the risk grid, so the γ panels carry information. At 0.60 they are dead panels. | WP1, all results |
| D3 | γ cap handling for PAP | Report both regimes; γ*=1 ⟺ consumption ≥ CR_G/CR_L ≈ 70% of production makes it a result | Sec 4.2, 4.3 |
| D4 | Convex reformulation | Adopt: rewrite C4 and Sec 3.3–3.4 around the lifting z = x·S | Sec 3, abstract |
| D5 | Commit the capture-rate fix and regenerate `data/processed` | Do it before WP1 | WP1 |

---

## 2. Section 4 structure: agreed

Five subsections plus an optional sixth. Baseload and pay-as-produced are separated by
run-in `\paragraph` headings inside each subsection, never by `\subsubsection`, so the
two structures read as two readings of one figure rather than as parallel studies.

Full skeletons, the figure map for Anders' existing plots and the verified numbers are in
`docs/paper/section4_skeleton.md`.

```
4.1  Case study and data
4.2  The bargaining set and the baseline contract      [gamma mechanism lives here]
4.3  Impact of risk preferences                        [gamma regime lives here]
4.4  Impact of bargaining power
4.5  Risk transfer and contracted earnings
4.6  Divergent price beliefs                           [only if D1 = yes]
```

The section opens with a framing paragraph stating the organising result:

> Under a baseload contract the two questions separate exactly: the contracted volume
> fixes the joint gain and the strike divides it, so risk preferences determine how much
> value the contract creates while bargaining power determines only how it is shared.
> Under pay-as-produced the separation fails -- the strike both creates and divides value,
> and the contracted share responds to the division as well.

This keeps Lesia's value-creation / value-allocation logic as the reading rhythm inside
each subsection without forcing it to be the skeleton, and keeps Anders' one-sweep-per-
subsection organisation. Comparisons of *responses* between structures are made
throughout; comparisons of *levels* are made only in 4.5, in earnings, because the joint
gain is risk-adjusted through party-specific A_i and is not comparable across structures.

**Verified 2026-09-23** (branch `capture-rate-fix`, corrected capture rates, 2000 scenarios):

- Baseload separates exactly: J = 28.0987 MEUR and M* = 12.6594 MW at every tau, to four
  decimals; the frontier has slope exactly -1.
- The PAP frontier is **straight but tilted**, not curved: departure from the chord is
  0.03% of the joint gain, but the slope is about -1.017 (measured on the 303-point sweep), so the joint gain rises 1.4%
  and gamma* drifts 0.6% as power moves to the buyer. Do not write "curved".
- gamma* crosses 1 at a value ratio of 1.003, i.e. at consumption = CR_G/CR_L = 70% of
  production (predicted 0.7022, observed 0.7036). Nearly invariant to risk aversion:
  the crossing value ratio stays within 0.90-1.02 over (A_G, A_L) in {0.2, 0.5, 0.8}^2.
- The current barter-set figure *assumes* a straight frontier through two points rather
  than tracing it. Trace it when the figure is redone.

**Terminology, per Anders.** *Asymmetric information* is the belief bias K on the mean of
price or production, which is in the base paper if D1 says yes. *Incomplete information*
is not knowing the counterparty's risk aversion or bargaining weight, which is release 2
-- this is what `load_risk_aversion.yaml` and the strike/volume KDE figures actually are.
Section 1 and Section 5 must use the two terms in exactly this sense.
---

## 3. Work packages

### WP0 — Decisions and freeze (0.5 d)
- [ ] D0–D5 agreed with co-authors
- [ ] Figure list frozen (6 figures + 2 tables, see §4)
- [ ] Case parameters frozen and written into `04_1`

### WP1 — Results pipeline (1 d)
- [ ] Commit the capture-rate fix; regenerate `data/processed` (both 500 and 2000)
- [ ] Shrink `config/sensitivity/asymmetric_info.yaml` to ~13 x 13
- [ ] Set `load_scale` per D2 in both experiment configs
- [ ] Run every sweep for both contracts; delete stale CSVs (the PAP
      `load_risk_aversion` results predate the current `load_scale`)
- [ ] `analysis/run_all_results.py`: one command from sweeps to figures
- [ ] Emit joint surplus and generator surplus share as derived metrics

### WP2 — Theory verification (1 d)
- [x] Baseload frontier has slope exactly −1: J and M* invariant to τ to four decimals
- [ ] Barter set convex while the utility image is not (plot both, both structures)
- [ ] Retrace the barter-set figure instead of assuming a straight frontier through two points
- [ ] Conditions C1/C2 predict the case across a risk-aversion grid
- [x] PAP cap criterion: γ*=1 ⟺ value ratio ≥ 1.00 ⟺ consumption ≥ CR_G/CR_L of production
- [ ] Is the maximiser a single point or a flat interval? (C3 claims uniqueness of terms)
- [ ] Utility-space figure for the barter set (also a Section 3 figure)
- [x] Interior PAP first-order condition `y_G/b_G = y_L/b_L` verified numerically

### WP3 — Write Section 4 (1.5 d)
- [x] Skeletons written: `docs/paper/section4_skeleton.md`
- [ ] 4.1 case study and data
- [ ] 4.2 the bargaining set and the baseline contract
- [ ] 4.3 impact of risk preferences
- [ ] 4.4 impact of bargaining power
- [ ] 4.5 risk transfer and contracted earnings
- [ ] 4.6 divergent price beliefs (if D1)

### WP4 — Write Section 5 (0.5 d)
- [ ] Discussion, limitations (iid annual volumes, synthetic capture rates, complete
      information), future work (beliefs, private information, iterative negotiation)
- [ ] Conclusions

### WP5 — Consistency pass (1 d)
- [ ] Claims ledger: every claim in the abstract, Section 1 and Section 3 mapped to a
      figure, table or theorem; unsupported claims cut or softened
- [ ] Fix the claims we know are wrong:
      - [ ] "risk aversion compresses the barter set" (C4 and abstract) — it expands it
      - [ ] abstract says NBS models omit bargaining power — Kandpal and Chen have it
      - [ ] weights mean patience or breakdown risk, not "access to alternatives" (context L46)
      - [ ] bankability opening vs the merchant disagreement point
      - [ ] research question still promises private information
- [ ] Abstract (<= 250 words) and highlights (3–5 bullets, <= 85 characters)

### WP6 — EJOR submission form (1 d)
- [ ] Convert IEEEtran -> elsarticle (two-column floats will need attention)
- [ ] Numeric citations -> APA author–year (natbib `\citet`/`\citep`)
- [ ] Keywords: first from the official EJOR list (recommend **Game theory**, which routes
      to Borgonovo; **OR in energy** routes to Rebennack), then 2–4 more
- [ ] Title page, corresponding author, CRediT statement
- [ ] Declarations: competing interests (Ramboll affiliation), funding, data availability
- [ ] **Generative AI declaration** (required; new section before the references)
- [ ] Fix the mechanical defects found in review:
      - [ ] undefined citation keys `Kalai1977Nonsymmetric`, `Roth1979Axiomatic`
      - [ ] duplicate label `fig:barter_conditions` (Sec 3.2 and Sec 4.1)
      - [ ] Appendix F commented out, so `app:data` is undefined
      - [ ] Appendix F says annual periods, Section 2 says monthly
      - [ ] S^{R*}/S^{U*} defined as min/max in Sec 3.2 but party-specific in Appendix D
      - [ ] three `\cite{TODO}` placeholders
      - [ ] RE-Source figures (1.2 -> 59.7 GW) unverified

---

## 4. Frozen figure list

| # | Subsec | Content | Panels |
| --- | --- | --- | --- |
| 1 | 4.1 | Production, consumption, price and capture-rate scenario bands | 4 |
| 2 | 4.2 | Bargaining set BL and PAP (traced), plus contracted quantity against buyer size | 3 |
| 3 | 4.3 | Strike and joint gain over (A_G, A_L), both structures | 2x2 |
| 4 | 4.4 | Strike, generator share and quantity against tau_L, both structures | 3 |
| 5 | 4.5 | Earnings bands, generator and buyer, both structures | 2x2 |
| 6 | 4.6 | Existence and joint gain over the belief gap (if D1) | 2 |

Neither quantity belongs on the risk-aversion grid: at the base case M* moves by a factor
1.15 and gamma* by 1.21, so the panels would be dead. Both ranges go in the text, and the
quantity gets its own panel against buyer size in Figure 2(c).

About 1.7 pages of floats, which suits a 5-6 page results section.

Tables: case parameters and scenario summary statistics; modelling ablation (what each
ingredient is worth).

To the appendix: the slice plots that accompany the Figure 3 heatmaps, the contract-size
sweeps (S against a fixed M or gamma at three tau), and the full-range barter-set views.

Dropped: the CVaR line plots (redundant with the bands; the number belongs in a table)
and `cmap_preview.png`.

Release 2, not this paper: `*_load_risk_aversion/strike_volume*.png`. These sweep an
unknown counterparty risk aversion, which is incomplete information, and the overlap
shading does not measure a zone of agreement.

---

## 5. Suggested 7-day schedule

| Day | Work |
| --- | --- |
| 1 | WP0 decisions; commit fix and regenerate data; start sweeps; mechanical Sec 1–3 fixes while they run |
| 2 | WP1 finishes; WP2 verification and the utility-space figure |
| 3 | WP3: 4.1 and 4.2 |
| 4 | WP3: 4.3, 4.4 and 4.5 (+ 4.6 if D1) |
| 5 | WP4 Section 5; abstract and highlights |
| 6 | WP5 claims ledger and top-to-bottom pass |
| 7 | WP6 formatting, references, declarations; buffer |

Internal co-author review starts on day 7; expect submission a few days later.

---

## 6. Release 2: beliefs and private information

1. Two-sided priors over the counterparty's type (risk aversion, possibly bargaining weight)
2. Propagate each prior through the (convex, fast) solve
3. Report each party's predicted-strike distribution; their overlap is the zone of likely
   agreement; add the probability that a given offer is accepted
4. Replace the KDE-overlap plot, which does not measure what its caption claims
5. Frame as decision support, not an incomplete-information equilibrium (Harsanyi–Selten
   and Anderson & Philpott are the equilibrium alternatives)

---

## 7. Deferred repo chores (not now)

- [ ] Trim the repo: drop dead files, keep the pipeline that reproduces the paper
- [ ] Move `Code/` and other legacy material to a `legacy` branch
- [ ] Push a clean `main`
- [ ] Data and code availability statement pointing at the cleaned repo
