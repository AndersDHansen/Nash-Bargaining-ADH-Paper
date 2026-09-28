# What drives the PAP contract share γ*, and when is γ* = 1?

Companion note to Section III (PAP model) and Section IV (results). It records the
diagnosis of the "γ* = 1 always" problem: the economic mechanism, the first-order
condition behind it, the capture-rate bug that made it worse, and the role of price
beliefs. Every number below was produced with the repo's own model (Gurobi, 500
reduced scenarios) on branch `capture-rate-fix`; the scripts are `harness.py` and
`harness2.py` from the 2026-09-23 session.

The short version:

1. The buyer hedges in **value**, not volume. Its hedge demand is
   `value ratio = (CR_L x load volume) / (CR_G x production volume)`.
2. γ* = 1 whenever the value ratio is ≳ 1, i.e. whenever the buyer's cost exposure
   exceeds the plant's revenue. This threshold is almost independent of risk aversion.
3. The formal condition is that the two parties' risk-adjusted **break-even strikes**
   meet: interior γ* solves `y_G/b_G = y_L/b_L`. γ* = 1 means they have not met at the cap.
4. A capture-rate bug (now fixed) depressed the wind capture rate from 0.726 to 0.585,
   which inflated the value ratio by 24% and pushed borderline cases to the cap.
5. Price beliefs shift both valuations: an optimistic buyer raises γ*, an optimistic
   seller lowers it and can destroy the agreement entirely.

---

## 1. The mechanism: hedging is denominated in value

The buyer's exposure is its consumption cost, `CR_L x P^L x λ`. What a PAP contract
delivers is wind energy worth `CR_G x P^G x λ`. Because wind is cannibalised
(CR_G < 1) while an industrial load is not (CR_L ≈ 1), **one MWh of wind hedges less
than one MWh of consumption**:

| | volume | capture price | value |
| --- | --- | --- | --- |
| Plant output | 98.7 GWh/yr | 85.4 EUR/MWh | 8.4 MEUR/yr |
| Buyer (load_scale 0.6) | 87.7 GWh/yr | 121 EUR/MWh | 10.6 MEUR/yr |
| Ratio | 0.89 | | **1.27** |

So a buyer that looks smaller than the plant by volume is still *larger* by value, and
wants more wind than the plant can produce. The contracted share the buyer would choose
if unconstrained is approximately the value ratio, plus a small speculative add-on
(~10%) because at the Nash solution the strike sits just below the expected capture
price, making each extra unit profitable in expectation.

With the cap lifted to γ ≤ 3 (fixed capture rates, A_G = 0.5, A_L = 0.8):

| load_scale | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 | 0.60 | 0.80 | 1.00 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| value ratio | 0.32 | 0.42 | 0.63 | 0.84 | 1.06 | 1.27 | 1.69 | 2.11 |
| γ* | 0.36 | 0.47 | 0.69 | 0.89 | 1.02 | 1.13 | 1.36 | 1.70 |

## 2. Why γ* stops rising: the seller goes short

Above γ = 1 the generator sells more than it produces, so it is short its own output and
must buy back the difference at spot. A risk-averse generator resists, which is why the
unconstrained optimum saturates at 1.0–1.7 even when the buyer would want 2.6.

The two kinks therefore decide the regime:

- the **buyer's** marginal valuation collapses once the contract covers its value exposure,
  i.e. at γ = value ratio;
- the **seller's** marginal valuation rises steeply once γ exceeds 1.

Whichever kink comes first sets γ*. Neither kink depends on risk aversion, which is why
the γ* = 1 threshold is so robust.

## 3. The first-order condition (this is Appendix D's machinery)

Maximising `N = τ_G log w_G + τ_L log w_L` over (γ, S). Using the marginal utilities of
Appendix D, with `b_i = R_i^q[B]` the risk-adjusted contracted volume and
`y_G = R_G^q[Y_G]`, `y_L = R_L^q[V_L]` the two parties' risk-adjusted valuations of the
contracted wind energy:

    ∂N/∂S = 0   ⇒   τ_G b_G / w_G = τ_L b_L / w_L
    ∂N/∂γ = 0   ⇒   τ_G (S b_G − y_G)/w_G + τ_L (y_L − S b_L)/w_L = 0

Substituting the first into the second cancels every term in S and leaves

    y_G / b_G  =  y_L / b_L .

Both sides are **break-even strikes**: `s_G` is what the seller must receive to be
indifferent on the marginal MWh, `s_L` is what that MWh is worth to the buyer. Hence

- **interior γ***  ⟺  `s_G = s_L`;
- **γ* = 1**  ⟺  `s_L > s_G` still holds at full output.

Verified numerically: where γ* is interior the wedge `s_L − s_G` is within
0.15 EUR/MWh of zero; at the cap it is strictly positive and grows with buyer size
(+3.0 at load_scale 0.5, +8.7 at 0.6, +12.2 at 1.0).

The valuation curves at the solved strike (load_scale 0.3, S* = 86.1 EUR/MWh):

| γ | 0.20 | 0.50 | 0.65 | 0.80 | 0.95 | 1.10 |
| --- | --- | --- | --- | --- | --- | --- |
| s_G (seller) | 78.0 | 78.5 | 79.0 | 79.6 | 82.5 | 88.9 |
| s_L (buyer) | 97.1 | 93.0 | 82.2 | 75.5 | 74.4 | 73.7 |

They cross at γ = 0.70 against a solved γ* = 0.686. For load_scale 0.6 they cross at
1.15 against a solved 1.13. The crossing predicts the optimum, so this is a supply-and-
demand picture of the contracted share and the natural Section IV figure.

Note the degenerate case: with common beliefs and risk neutrality, `s_G = s_L` for every
γ (both equal the expected capture price), the surplus is zero and γ is indeterminate —
the Appendix C zero-sum result. The wedge that makes a PAP contract worth signing comes
from the tail weights (risk aversion) or from belief differences.

## 4. The capture-rate bug (fixed on branch `capture-rate-fix`)

`CaptureRateModel` / `LoadRateModel` build the capture rate from the identity

    CR = 1 + ρ · CV_price · CV_volume ,

which holds only when all three moments are measured over the same period. The code took
ρ per year but the means and standard deviations **pooled over 2020–2024**, a window
containing both 28 EUR/MWh (2020) and 210 EUR/MWh (2022). The pooled price CV is 1.058
against 0.707 within-year, so the capture rate was biased down.

| | before | after | empirical (DK2 hourly) |
| --- | --- | --- | --- |
| CR_G (wind) | 0.585 | 0.724 | 0.726 (yearly: 0.75, 0.80, 0.66, 0.70, 0.72) |
| CR_L (load) | 1.043 | 1.031 | 1.024 |
| CR_G spread (sd) | 0.098 | 0.065 | 0.055 across years |

The fix computes ρ, CV_price and CV_volume within each calendar year and averages across
years (`_within_year_moments`). Regenerating changes only the capture-rate scenarios;
price, production and load are untouched.

Consequences: the value ratio at load_scale 0.6 falls from 1.59 to 1.27 (still > 1, so
γ* = 1 there), the interior regime now starts below load_scale ≈ 0.5, and on the shipped
configuration the strike moves from 70.6 to 87.7 EUR/MWh with the joint surplus rising
from 28.0 to 34.2 MEUR. Every number in the paper shifts, and the generator's capture
level is the single largest driver of the results, so nothing should be written against
pre-fix numbers.

## 5. Where γ* = 1 begins, and how robust it is

Unconstrained γ* (cap 3), fixed capture rates:

| A_G, A_L | ls=0.3 | 0.4 | 0.5 | 0.6 | 0.8 |
| --- | --- | --- | --- | --- | --- |
| 0.2, 0.8 | 0.65 | 0.86 | 1.03 | 1.18 | 1.58 |
| 0.5, 0.5 | 0.79 | 0.91 | 1.03 | 1.10 | 1.19 |
| 0.5, 0.8 | 0.69 | 0.89 | 1.02 | 1.13 | 1.36 |
| 0.8, 0.2 | 0.99 | 0.99 | 1.02 | 1.03 | 1.05 |
| 0.8, 0.8 | 0.79 | 0.91 | 1.03 | 1.10 | 1.19 |

γ* crosses 1 at load_scale ≈ 0.5 (value ratio ≈ 1.05) for every risk-aversion pair.
Within a regime, risk aversion still moves γ*, and the direction follows one rule:
**γ* moves toward the value-hedge point as risk aversion rises.** Below that point (large
buyer) more risk aversion raises γ*; above it (small buyer, speculative add-on) it lowers
γ*. γ* also rises with the *seller's* risk aversion, because the seller accepts a lower
strike and volume becomes cheaper for the buyer. This is the concrete evidence that under
PAP the strike and the quantity are interdependent, unlike baseload.

## 6. Price beliefs (K_G, K_L)

Interior base (load_scale 0.3, A_G = 0.5, A_L = 0.8, cap 3). Cells are γ* / S* / J:

| K_G \ K_L | −0.05 | 0.00 | +0.05 |
| --- | --- | --- | --- |
| **−0.05** | 0.684 / 81.9 / 21.3 | 0.802 / 82.8 / 27.5 | 0.963 / 83.7 / 34.8 |
| **0.00** | 0.648 / 84.4 / 15.7 | 0.686 / 86.1 / 21.2 | 0.802 / 87.1 / 27.3 |
| **+0.05** | 0.602 / 86.9 / 10.5 | 0.644 / 88.6 / 15.6 | 0.689 / 90.3 / 21.0 |

- Only the **gap** matters: K_G = K_L = 0.05 reproduces the (0,0) surplus almost exactly.
  This is the Appendix C mechanism surviving in the risk-averse model.
- An optimistic buyer raises `s_L`, hence γ* and the surplus. An optimistic seller raises
  `s_G`, lowering γ* and the surplus while raising the strike.
- **Existence boundary.** With the seller increasingly optimistic (K_L = 0, load_scale 0.3)
  the surplus falls 21.2 → 15.6 → 10.3 → 5.5 → 1.4 and disappears at K_G ≈ 0.25–0.30.
  Risk aversion sustains a contract against moderate belief divergence, not beyond.
- Belief-driven surplus is speculative: both parties book a gain only because they value
  the same cash flows under different beliefs. If K enters the paper, the surplus should
  be decomposed into risk-transfer and belief components.

## 7. What this means for the paper

- γ* = 1 is a **regime, not an artefact**: the buyer is larger than the plant in value
  terms, so the whole output is contracted and only the strike is negotiated. Present it
  with the crossing-valuation figure, and it becomes a result.
- **Choose the buyer size deliberately** and state it in GWh. `load_scale` 0.3–0.4
  (44–59 GWh/yr against a 98.7 GWh plant) gives an interior γ* of 0.69–0.89 and lets the
  paper show both regimes.
- Report γ* against the value ratio, not the volume ratio. The one-line explanation:
  *because wind's capture price is well below the buyer's, one MWh of wind hedges only
  about 0.7 MWh of consumption, so the contracted share exceeds the volume share by the
  ratio of capture prices.*
- Two traps: `hedge_ratio_max` caps on volume, so it binds at 0.445 where the economics
  want 0.708 — define it in value terms if it is used at all; and the strike bounds can
  block agreement (a test with CR_G halved returned no contract with the strike pinned at
  the 40 EUR/MWh floor), which also violates the theorem's assumption that the box is
  wider than the viable band.
