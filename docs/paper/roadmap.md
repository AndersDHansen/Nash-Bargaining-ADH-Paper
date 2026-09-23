# Roadmap to EJOR submission

Living checklist for the base paper. Updated 2026-09-23 (Section 4 structure agreed).
Companion notes: `docs/theory/gamma_drivers.md` (γ diagnosis), `docs/theory/axiom_choice.md`
(why the NBS), `docs/paper/section4_plan.md` (earlier sweep-level plan, partly superseded).

**Two releases.** The base paper is submission-ready *without* beliefs and private
information, provided the research question and gaps no longer promise them. Everything
about incomplete information moves to a second release.

---

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
  0.03% of the joint gain, but the slope is about -0.986, so the joint gain rises 1.4%
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
