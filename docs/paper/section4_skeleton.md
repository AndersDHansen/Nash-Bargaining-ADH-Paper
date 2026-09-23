# Section 4 — skeleton, figure map and verified numbers

Structure agreed 2026-09-23. Five subsections plus an optional sixth. Baseload and
pay-as-produced are separated by run-in `\paragraph` headings, never by `\subsubsection`,
so the two structures read as two readings of one figure rather than as parallel studies.

Numbers below were produced on branch `capture-rate-fix` with the corrected capture rates
(CR_G = 0.724, CR_L = 1.031) on the 2000-scenario set. They are the ones to write against.

---

## 1. What the WP1 checks returned

### 1.1 Does the contracted quantity respond to bargaining power?

Frontier traced by sweeping tau_L over 17 points at A_G = A_L = 0.5.

| Structure | joint gain along the frontier | quantity along the frontier | departure from a straight chord |
| --- | --- | --- | --- |
| Baseload, load_scale 1.0 | 28.0987 MEUR at every tau (spread 0.000%) | M* = 12.6594 MW at every tau (0.000%) | 0.0000 MEUR |
| PAP, load_scale 0.40 (interior gamma) | 21.564 – 21.869 MEUR (spread 1.404%) | gamma* 0.9059 – 0.9110 (0.555%) | 0.0061 MEUR = 0.028% of J |
| PAP, load_scale 0.60 (gamma capped) | 25.923 – 26.286 MEUR (spread 1.389%) | gamma* = 1 throughout | 0.0014 MEUR = 0.005% of J |

Two conclusions, and the second corrects what we had assumed:

1. **Baseload separates exactly.** The volume and the joint gain are invariant to tau to
   four decimals, and the strike is exactly linear in tau. Utility transfers one-for-one:
   the frontier has slope exactly -1. This is Theorem 1 shown numerically.
2. **The PAP frontier is not curved — it is straight but tilted.** Departure from the
   chord is 0.03% of the joint gain, i.e. visually and numerically linear, but its slope
   is about -0.986 rather than -1. One unit of generator surplus surrendered buys about
   1.014 units of buyer surplus, so the joint gain rises 1.4% as power moves to the buyer
   and gamma* drifts by 0.6%.

   **Do not write "the PAP frontier is curved".** Write that the separation between
   creating and dividing value fails under PAP, and that the failure is second-order:
   1.4% in the joint gain, 0.6% in the contracted share.

Side effect worth acting on: at tau_L = 1 the three A_L curves for PAP meet at a single
strike (78.99 EUR/MWh), because a buyer with all the power pays the generator's
reservation strike, which does not depend on A_L. Visible in Anders' figure; worth a
sentence.

### 1.2 Where is the gamma* = 1 threshold?

Cap released to gamma_max = 3 so the true optimum is visible; K = 0, tau_L = 0.5.

| load_scale | buyer GWh/yr | load/production | value ratio | gamma* | s_G | s_L |
| --- | --- | --- | --- | --- | --- | --- |
| 0.10 | 14.6 | 0.148 | 0.211 | 0.3513 | 78.14 | 78.13 |
| 0.20 | 29.2 | 0.296 | 0.422 | 0.6030 | 78.56 | 78.55 |
| 0.30 | 43.9 | 0.444 | 0.633 | 0.7856 | 79.47 | 79.43 |
| 0.35 | 51.2 | 0.519 | 0.739 | 0.8572 | 80.67 | 80.60 |
| 0.40 | 58.5 | 0.593 | 0.844 | 0.9068 | 81.66 | 81.61 |
| 0.45 | 65.8 | 0.667 | 0.950 | 0.9739 | 83.39 | 83.37 |
| 0.50 | 73.1 | 0.741 | 1.055 | 1.0257 | 85.79 | 85.72 |
| 0.60 | 87.7 | 0.889 | 1.267 | 1.1009 | 88.90 | 88.95 |
| 0.80 | 117.0 | 1.185 | 1.689 | 1.1865 | 91.39 | 91.38 |
| 1.00 | 146.2 | 1.481 | 2.111 | 1.2384 | 92.10 | 92.08 |

**The threshold has a closed form.** gamma* crosses 1 at a value ratio of 1.003, i.e. at
load/production = 0.7036 — against CR_G / CR_L = 0.724 / 1.031 = 0.7022, a 0.2% match.
So:

> The buyer contracts the plant's entire output whenever its consumption exceeds
> CR_G / CR_L of the plant's production — about 70% on this case study. Below that it
> contracts a strict fraction.

The break-even strikes s_G and s_L agree to within 0.07 EUR/MWh at every interior point,
confirming the first-order condition across the whole grid, not just at one point.

**The threshold barely moves with risk aversion.** Crossing value ratio over a 3x3 grid of
(A_G, A_L) in {0.2, 0.5, 0.8}: 0.899 to 1.018, mean 0.99. The spread is driven by A_G
(a more risk-averse seller lowers the threshold slightly); A_L hardly matters.

| A_G \ A_L | 0.2 | 0.5 | 0.8 |
| --- | --- | --- | --- |
| 0.2 | 1.003 | 1.014 | 1.018 |
| 0.5 | 0.967 | 1.003 | 1.013 |
| 0.8 | 0.899 | 0.984 | 1.001 |

### 1.3 Consequence for D2 (buyer size)

At the shipped `load_scale = 0.6` the PAP share is pinned at 1 everywhere, and Anders'
gamma panels are literally a solid colour block and a flat line — two dead panels.
At `load_scale = 0.40` (buyer 58.5 GWh/yr against a plant producing 98.7 GWh/yr, a 59%
hedge ratio, entirely realistic) gamma* runs from 0.856 to 0.992 across the risk-aversion
grid and the panel carries information. **Adopt load_scale = 0.40 as the base case** and
show the capped regime as the sensitivity, not the other way round.

### 1.4 A defect in the current barter-set figure

The notebook builds the frontier as a straight line through two computed points
(the two extreme-strike points), so the shape is assumed rather than traced. For baseload
that assumption is exactly right. For PAP it hides the 1.4% tilt that is the whole
structural result. When the figure is redone, trace the frontier by sweeping tau and
plotting the solved (w_G, w_L) pairs.

Also: the baseload legend reads `M* = 12.70 [MWh]`; the unit is MW.

---

## 2. Where Anders' existing figures go

All will be regenerated at the corrected capture rates; this is the placement and the
space estimate.

| Existing file | Destination | Action |
| --- | --- | --- |
| `barter_set/barter_set_baseload.png`, `..._pap.png` | **4.2, Fig. 2(a)(b)** | trace the frontier instead of assuming it; fix the MW label |
| `barter_set/*_full.png` | appendix or drop | the zoomed view carries the argument |
| `contract_params_sensitivity/*.png` | **4.3, Fig. 3(a)(b)** | heatmaps to the main text, slice plots to the appendix |
| `pap_contract_params_sensitivity/*.png` | **4.3, Fig. 3(c)(d)** | rerun at load_scale 0.40 or the gamma panel is dead |
| `baseload_bargaining_power_contract_params.png` | **4.4, Fig. 4(a)(b)** | keep the flat M panel — the flat line is the result |
| `pap_bargaining_power_contract_params.png` | **4.4, Fig. 4(c)(d)** | rerun at load_scale 0.40 |
| `baseload_earnings/*_stacked_bands.png` | **4.5, Fig. 5 top row** | keep the percentile bands |
| `pap_earnings/*_stacked_bands.png` | **4.5, Fig. 5 bottom row** | keep |
| `*_earnings/*_cvar5_lineplot*.png` | drop | redundant with the bands; the CVaR number belongs in a table |
| `baseload_contract_size/*.png`, `pap_contract_size/*.png` | appendix | supporting evidence that M* maximises the gain |
| `*_load_risk_aversion/strike_volume*.png` | **release 2** | incomplete information, not the belief bias; the overlap shading also does not measure a zone of agreement |
| `cmap_preview.png` | drop | development artefact |

Space, assuming a two-column elsarticle layout and full-width floats:

| Figure | Panels | Aspect | Page share |
| --- | --- | --- | --- |
| 1 Scenario bands | 2 | wide | 0.25 |
| 2 Bargaining set + marginal valuations | 3 | 3:1 | 0.20 |
| 3 Terms over (A_G, A_L) | 2x2 heatmaps | 1.3:1 | 0.45 |
| 4 Bargaining power | 4 in a row | 4:1 | 0.18 |
| 5 Earnings bands | 2x2 | 1.3:1 | 0.40 |
| 6 Belief divergence | 2 | wide | 0.25 |

About 1.7 pages of figures, which suits a 5–6 page results section.

---

## 3. LaTeX skeletons

Paste into `sections/04_results/`. Every `%>` line is a note to the writer, to be deleted.

### 4.1

```latex
\subsection{Case study and data}
\label{sec:res_case}

%> The asset, the buyer, the tenor. 30 MW onshore wind in DK2, 98.7 GWh/yr;
%> buyer consumption 58.5 GWh/yr (load_scale 0.40), i.e. a 59% hedge ratio; 20 annual
%> periods; alpha = 0.95; strike box [40, 200] EUR/MWh.

%> Scenarios. Source data 2020-2024, generation and reduction to 2000 scenarios,
%> probabilities. Refer to Appendix F.

%> Capture rates and why they differ. CR_G = 0.724, CR_L = 1.031. Wind is cannibalised,
%> an industrial profile is not. Define the value ratio here as a property of the data:
%> (CR_L x consumption) / (CR_G x production) = 0.844 in the base case.
%> State plainly that the generator's capture level is the single strongest driver of
%> every number in this section (ablation: 73% against at most 9% for the volumes).

%> Parameters held fixed unless swept: A_G = A_L = 0.5, tau_L = 0.5, K = 0.

\begin{figure}[tb] \centering
  % Figure 1: price and production scenario bands
  \caption{...}\label{fig:scenarios}
\end{figure}

\begin{table}[tb] \centering
  % Table 1: case parameters and scenario summary statistics
  \caption{...}\label{tab:case}
\end{table}
```

### 4.2

```latex
\subsection{The bargaining set and the baseline contract}
\label{sec:res_baseline}

%> What the bargaining set is and how it is traced: solve the weighted NBS over
%> tau in (0,1) and plot the attained (w_G, w_L). Individual rationality bounds the set
%> below and to the left; the disagreement point is the merchant position.

\paragraph{Baseload.}
%> Agreed terms: S* = 121.9 EUR/MWh, M* = 12.66 MW, w_G = w_L = 14.05 MEUR.
%> The frontier has slope exactly -1: the strike transfers utility one-for-one, so the
%> joint gain is fixed by M alone. Verified: J = 28.0987 MEUR at every tau, M* identical
%> to four decimals. This is Theorem 1.

\paragraph{Pay-as-produced.}
%> Agreed terms at the base case: gamma* = 0.91, S* = 84.7 EUR/MWh. State it flatly.
%> The frontier is still straight to within 0.03% of the joint gain, but its slope is
%> about -0.986, not -1: the strike is not a pure transfer, so moving power to the buyer
%> raises the joint gain by 1.4% and moves gamma* by 0.6%. The separation between
%> creating and dividing value fails, and the failure is second-order.

\paragraph{Why the contracted share is what it is.}
%> The buyer hedges value, not volume. Because wind is cannibalised, one MWh of
%> production hedges only CR_G/CR_L = 0.70 MWh of consumption, so the buyer's demand for
%> the plant's output is the value ratio, not the volume ratio. The interior optimum
%> equalises the two parties' risk-adjusted break-even strikes, s_G = y_G/b_G and
%> s_L = y_L/b_L (Appendix X); at the base case they meet at 81.6 EUR/MWh. gamma* = 1
%> means they have not met before the cap.

\begin{figure*}[tb] \centering
  % Figure 2: (a) bargaining set, baseload  (b) bargaining set, PAP
  %           (c) the two break-even strikes against gamma, and where they cross
  \caption{...}\label{fig:barter}
\end{figure*}
```

### 4.3

```latex
\subsection{Impact of risk preferences}
\label{sec:res_risk}

%> The sweep: A_G x A_L on [0,1]^2, 11 x 11, tau_L = 0.5. Report the strike and the
%> contracted quantity for both structures.

\paragraph{Baseload.}
%> The strike rises with the buyer's risk aversion and falls with the seller's:
%> 112 to 129 EUR/MWh across the grid. The volume responds to *relative* risk aversion
%> while the strike responds to *absolute* levels (keep Anders' wording).
%> The joint gain RISES with risk aversion on both sides, because risk aversion lowers
%> each party's disagreement utility. This contradicts contribution C4 and the abstract
%> as currently written -- fix both (WP5).

\paragraph{Pay-as-produced.}
%> The strike responds the same way and is close to linear in A_L. The contracted share
%> moves very little: gamma* runs only from 0.86 to 0.99 over the whole grid, against a
%> volume that roughly triples under baseload. The quantity is set by the value ratio,
%> not by risk preferences; risk preferences re-price the deal without resizing it.

\paragraph{When the buyer contracts the full output.}
%> gamma* reaches the cap once the value ratio passes 1.00, i.e. once consumption exceeds
%> CR_G/CR_L = 70% of production. The threshold is nearly invariant to risk preferences:
%> over (A_G, A_L) in {0.2,0.5,0.8}^2 the crossing value ratio stays within 0.90-1.02.
%> gamma* = 1 is therefore a regime of the case, not an artefact of the model.

\begin{figure*}[tb] \centering
  % Figure 3: (a) S*, baseload  (b) M*, baseload  (c) S*, PAP  (d) gamma*, PAP
  %           heatmaps over (A_G, A_L); slice plots in the appendix
  \caption{...}\label{fig:risk}
\end{figure*}
```

### 4.4

```latex
\subsection{Impact of bargaining power}
\label{sec:res_power}

%> The sweep: tau_L from 0 to 1 at A_L in {0.25, 0.5, 0.75}, A_G = 0.5.

\paragraph{Baseload.}
%> The strike sweeps linearly from the buyer's reservation strike to the generator's,
%> and the volume does not move at all. The joint gain is constant to four decimals.
%> Panel (b) being a horizontal line is the result, not an empty plot: bargaining power
%> is a pure transfer, and creation and allocation separate exactly.

\paragraph{Pay-as-produced.}
%> The strike again falls linearly in tau_L, and the three risk-aversion curves converge
%> at tau_L = 1, where the buyer takes the whole gain and pays the generator's
%> reservation strike, which does not depend on A_L. The contracted share drifts by 0.6%
%> and the joint gain by 1.4% across the sweep: small, but not zero, so the separation
%> that holds exactly for baseload holds only approximately here.

%> One closing sentence: under baseload a negotiator's power decides only the price;
%> under pay-as-produced it also, marginally, decides the size of the deal.

\begin{figure*}[tb] \centering
  % Figure 4: (a) S vs tau, baseload  (b) M vs tau, baseload
  %           (c) S vs tau, PAP       (d) gamma vs tau, PAP
  \caption{...}\label{fig:power}
\end{figure*}
```

### 4.5

```latex
\subsection{Risk transfer and contracted earnings}
\label{sec:res_earnings}

%> Framing. Same parties, same scenarios, same merchant baseline; earnings in MEUR over
%> the tenor. State explicitly that this is the one place where the two structures can be
%> compared like for like, and that the joint gain cannot be, because it is risk-adjusted
%> through party-specific A_i.

\paragraph{Baseload.}
%> As the buyer becomes more risk averse it buys certainty and pays for it: its earnings
%> band narrows sharply while its expected cost rises. The generator's band widens by the
%> same mechanism and its expected earnings rise. Risk moves from the buyer to the seller,
%> and the strike is the price of that transfer.

\paragraph{Pay-as-produced.}
%> The mirror image. The generator's band is narrow and stays narrow across the whole
%> sweep, while the buyer's band barely contracts. Pay-as-produced stabilises the seller;
%> baseload stabilises the buyer. The two structures redistribute risk in opposite
%> directions (keep Anders' sentence).

\paragraph{Is a deal between a cautious and a tolerant party a good deal?}
%> Answer in euros: how much expected earnings each party gives up for how much tail
%> protection, at the four corners of the risk-aversion grid.

\begin{figure*}[tb] \centering
  % Figure 5: earnings percentile bands vs A_L
  %           rows: generator / load;  columns: baseload / PAP
  \caption{...}\label{fig:earnings}
\end{figure*}
```

### 4.6 (only if D1 says yes)

```latex
\subsection{Divergent price beliefs}
\label{sec:res_beliefs}

%> The bias K on the believed price mean, and the result that only the GAP between the
%> two parties' beliefs matters, not its level.

%> Existence. Agreement fails once the generator's optimism passes K_G ~ 0.25-0.30.

%> Interpretation, and this is the honest part: gain created by disagreement is
%> speculative, not hedging value. Neither party earns it. Report it separately from the
%> risk-transfer gain and never add the two together.

\begin{figure}[tb] \centering
  % Figure 6: existence boundary and joint gain over the belief gap
  \caption{...}\label{fig:beliefs}
\end{figure}
```

---

## 4. Terminology, fixed

- **Asymmetric information** = the belief bias K on the mean of price or production.
  Both parties know the model and disagree about the forecast. Base paper, Section 4.6.
- **Incomplete information** = not knowing the counterparty's risk aversion or bargaining
  weight. `config/sensitivity/load_risk_aversion.yaml` and the strike/volume KDE figures.
  Release 2.

Section 1 and Section 5 must use the two terms in exactly this sense.

---

## 5. Full risk-aversion grid at the base case (2026-09-23, later run)

11 x 11 over (A_G, A_L), load_scale 0.40, tau_L 0.5, K = 0, fixed capture rates.
120 of 121 cells create value; the cell where both parties are risk neutral does not.

| | baseload | pay-as-produced |
| --- | --- | --- |
| strike S* | 110.4 – 127.1 EUR/MWh (x1.15) | 78.9 – 91.5 EUR/MWh (x1.16) |
| quantity | M* 6.95 – 7.97 MW (x1.15) | gamma* 0.824 – 1.000 (x1.21) |
| joint gain J | 0 – 42.7 MEUR | 0 – 43.5 MEUR |
| at the cap | n/a | 17 of 120 cells |

**This corrects two things I had written above.**

1. The quantity is **not** much more responsive under baseload than under PAP. At this
   buyer size it barely moves in either: a factor 1.15 against 1.21. The earlier
   impression came from Anders' figure, which was run at `load_scale = 1.0`, where the
   buyer is large and M is free to range 6–17 MW. **The quantity's sensitivity to risk
   preferences is a function of buyer size, not of contract structure.** At a buyer
   consuming 59% of plant output, both instruments sit close to the buyer's own exposure.
2. Consequently **neither** quantity panel over the risk grid is worth a figure. Report
   the two ranges in the text and give the quantity its own panel against **buyer size**
   in Figure 2(c), where it genuinely varies and where the gamma = 1 threshold lives.

**New result worth leading with.** When both parties are risk neutral the joint gain is
exactly zero in both structures: under symmetric beliefs the contract is a pure transfer
in expectation, so every gain from trade comes from the two parties' loss tails containing
different scenarios. This is the justification for the mean-CVaR formulation and it should
be stated in 4.3. The joint gain is monotone increasing in both A_G and A_L, which settles
the C4 correction in both structures.

## 6. Revised figure list

| # | Subsec | Panels | Built from |
| --- | --- | --- | --- |
| 1 | 4.1 | production, consumption, price, capture rates | `figures/case_study/scenario_overview_bands.pdf`, regenerated |
| 2 | 4.2 | (a) bargaining set BL (b) bargaining set PAP (c) quantity vs buyer size, both | `results/plots/barter_set/*`, retraced; (c) is new |
| 3 | 4.3 | (a) S* BL (b) S* PAP (c) J BL (d) J PAP, all over (A_G, A_L) | `contract_params_sensitivity/*` + `value_creation/joint_surplus_risk.png` |
| 4 | 4.4 | (a) strike (b) generator share (c) quantity, all vs tau_L, both structures | `figures/value_allocation/bargaining_power.png` layout, both structures overlaid |
| 5 | 4.5 | generator/buyer x baseload/PAP earnings bands | `results/plots/*_earnings/*_stacked_bands.png` |
| 6 | 4.6 | (a) existence over the belief plane (b) joint gain vs belief gap | `figures/value_creation/joint_surplus_bias.png`, extended |

## 7. Defects found in the current `figures/*` set

- `value_allocation/symmetric_nbs.png` panel (c) is broken: the colour bar runs to
  +/-200000 while the quantity plotted is a share in [0, 1]. Panel (d) shows why --- the
  generator's share is 0.493 to 0.500 everywhere, i.e. flat, but the axis is stretched so
  a 0.7% variation looks dramatic. Both panels mislead; the honest statement is that at
  tau_L = 0.5 the split is even regardless of risk preferences.
- `value_creation/settlement_type.png` has colliding tick labels and axis titles, and its
  panel (c), "which settlement wins", is exactly the baseload-versus-PAP level comparison
  the section is built to avoid.
- The new figures use x = A_L with A_G as the series; Anders' use x = A_L with A_G as the
  series in the heatmaps but A_G on the x-axis in the slices. Pick one convention.
- `figures/value_allocation/bargaining_power.png` reports gamma* of 0.31, 0.59 and 0.91
  for A_L of 0.75, 0.50 and 0.25. Those levels are not reproducible under any current
  config, so the underlying CSVs are stale and must be regenerated before anything is
  written against them. The qualitative directions do survive.
- `figures/case_study/scenario_overview_bands.pdf` shows the seller capture rate at 0.58,
  the pre-fix value, and the buyer load at `load_scale = 0.6`. Regenerate.
