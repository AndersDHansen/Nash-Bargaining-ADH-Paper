# Why the NBS: the axiom choice for the PPA bargaining problem

Companion note to Section I.B and Appendix A of the manuscript. It sets out, as a
sequence of statements with proofs, why the asymmetric Nash bargaining solution is
the rule adopted here, which axioms actually do the work, and exactly where the
alternatives would and would not give a different answer.

The short version is in three lines:

1. **Scale invariance** is forced by the fact that the two parties have no common
   numeraire. It eliminates the egalitarian and utilitarian rules.
2. **IIA** is a choice, not a necessity. It is what separates the NBS from
   Kalai-Smorodinsky (KS), and the reason to prefer it is specific to this model.
3. For the **baseload** contract the choice does not matter at all: NBS, KS and
   egalitarian give the identical answer. It matters only for **pay-as-produced**.

Point 3 is not in the manuscript yet and is the most useful thing in this note.

---

## 0. Setup and notation

A two-player bargaining problem is a pair $(\mathbf{B}, \mathbf{d})$ with
$\mathbf{B} \subset \mathbb{R}^2$ compact and convex and $\mathbf{d} \in \mathbf{B}$.
A bargaining rule $f$ maps each problem to a single point $f(\mathbf{B},\mathbf{d}) \in \mathbf{B}$.

In this paper:

| Object | Meaning |
| --- | --- |
| $i \in \{G, L\}$ | generator, load |
| $\pi_i(\omega)$ | net earnings of party $i$ in scenario $\omega$, in EUR |
| $u_i = (1-A_i)\,\mathbb{E}[\pi_i] + A_i\,\mathrm{CVaR}_\alpha(\pi_i)$ | risk-adjusted utility |
| $d_i$ | the same functional applied to the merchant earnings $\pi_i^0$ |
| $w_i = u_i - d_i$ | surplus of party $i$ |
| $\mathbf{B}$ | barter set, the individually rational part of the utility image of the contract box |
| $x$ | contracted quantity, $M$ for baseload and $\gamma$ for PAP |
| $S$ | strike price |
| $\tau_i$ | bargaining weight, $\tau_G + \tau_L = 1$ |

Write $\mathbf{a} = (a_G, a_L)$ for the **aspiration point**, where
$a_i = \max\{u_i : \mathbf{u} \in \mathbf{B},\ u_j \ge d_j\}$: the best party $i$ could
hope for while leaving the other party willing to sign.

---

## 1. The property of our utility that makes the axioms bite

Everything below depends on one fact about the CVaR-weighted utility, so it is worth
isolating first.

**Lemma 1 (positive affine equivariance).** For any $a > 0$ and $b \in \mathbb{R}$,

$$u_i(a\,\pi_i + b) = a\,u_i(\pi_i) + b .$$

*Proof.* $\mathbb{E}$ is linear, so $\mathbb{E}[a\pi + b] = a\mathbb{E}[\pi] + b$.
$\mathrm{CVaR}_\alpha$ is positively homogeneous and translation equivariant, so
$\mathrm{CVaR}_\alpha(a\pi + b) = a\,\mathrm{CVaR}_\alpha(\pi) + b$ (Appendix D of the
manuscript cites Rockafellar and Uryasev, and Shapiro et al., for both properties).
Taking the convex combination with weights $(1-A_i, A_i)$ preserves the relation.
$\square$

**Why this matters.** A change of currency, of accounting units, or the addition of a
fixed sunk cost to one party's books, is exactly a map $\pi_i \mapsto a\pi_i + b$ with
$a > 0$. By Lemma 1 it induces exactly the same map on $u_i$. Such a change carries no
economic content, so the prescribed contract $(x^\ast, S^\ast)$ must not move. That
requirement is the scale invariance axiom, stated in the utility space.

Note also what is **not** true: there is no map relating $u_G$ to $u_L$. The generator
is typically a project SPV whose risk appetite $A_G$ is set by its lenders; the load is
an industrial firm whose $A_L$ reflects a procurement mandate. Their risk-adjusted euro
figures live on unrelated scales. Nothing in the model licenses adding them or equating
them.

---

## 2. Scale invariance eliminates two rules, and the elimination is constructive

**Claim.** The utilitarian and egalitarian rules are not scale invariant, and the
failure is not a technicality: it changes the prescribed contract.

**Utilitarian.** $f^U = \arg\max_{\mathbf{u} \in \mathbf{B}} (u_G + u_L)$.
Rescale the generator's utility by $a > 0$, which by Lemma 1 is what happens if the
generator restates its accounts in a different unit. The objective becomes
$a\,u_G + u_L$, whose maximiser over $\mathbf{B}$ is in general a different point of the
frontier. As $a \to \infty$ the rule allocates everything to $G$; as $a \to 0$,
everything to $L$. The prescription is therefore a function of the reporting
convention, which is not a property a negotiation reference point can have.

**Egalitarian.** $f^E = \arg\max_{\mathbf{u} \in \mathbf{B}} \min_i (u_i - d_i)$,
which selects $w_G = w_L$. Rescale $w_G \mapsto a\,w_G$. The selected point now
satisfies $a\,w_G = w_L$, a different contract for every $a$. Same defect.

**Nash.** $f^{NBS}_\tau = \arg\max\ w_G^{\tau_G} w_L^{\tau_L}$. Under
$w_G \mapsto a\,w_G$ the objective becomes $a^{\tau_G} w_G^{\tau_G} w_L^{\tau_L}$, and
$a^{\tau_G} > 0$ is a constant multiplier. The argmax is unchanged. Invariant.

**KS.** $f^{KS}$ solves $\dfrac{w_G}{a_G - d_G} = \dfrac{w_L}{a_L - d_L}$ on the
frontier. Under $w_G \mapsto a\,w_G$ the aspiration gap scales identically,
$a_G - d_G \mapsto a\,(a_G - d_G)$, so the ratio is unchanged. Invariant.

**Conclusion of Section 2.** Scale invariance is a genuine requirement of this model,
and it narrows the field to $\{$NBS, KS$\}$. It does **not** select the NBS.

---

## 3. What separates NBS from KS, and what does not

A correction to the manuscript as it previously stood, and the source of the confusion
this note was written to resolve.

| Axiom | NBS | KS | Separates them? |
| --- | --- | --- | --- |
| Pareto efficiency | yes | yes (for $n=2$) | no |
| Symmetry | yes | yes | no |
| **Scale invariance** | **yes** | **yes** | **no** |
| IIA | yes | no | **yes** |
| Individual monotonicity | no | yes | **yes** |

Scale invariance does not distinguish NBS from KS. Only the IIA / monotonicity pair
does. Any argument for the NBS over KS must therefore be an argument about IIA, and
nothing else.

Two further corrections worth recording:

- The **egalitarian rule satisfies IIA**. $f^E(\mathbf{B},\mathbf{d})$ is the maximal
  point of $\mathbf{B}$ on the ray $\mathbf{d} + t(1,1)$. If
  $\mathbf{B}' \subseteq \mathbf{B}$ and $f^E(\mathbf{B},\mathbf{d}) \in \mathbf{B}'$,
  then $t^\ast(\mathbf{B}') \ge t^\ast(\mathbf{B})$ because that point is still
  available, and $t^\ast(\mathbf{B}') \le t^\ast(\mathbf{B})$ because
  $\mathbf{B}' \subseteq \mathbf{B}$. Hence equality. So it is scale invariance, not
  IIA, that rules the egalitarian rule out.
- KS and the egalitarian rule satisfy **different** monotonicity axioms: individual
  monotonicity (defined relative to the aspiration point) and strong monotonicity
  (aspiration-free) respectively. Collapsing them into one column obscures that no
  scale invariant rule satisfies the strong version.

---

## 4. The case for IIA in this specific model

Two arguments, one general and one specific to the formulation. The specific one is
narrower than the manuscript previously claimed, and the honest version is given here.

### 4.1 The general argument: stability of the prescription under refinement

IIA says: if the feasible set shrinks but the prescribed contract remains feasible,
the prescription does not move.

In a PPA negotiation the feasible set is refined repeatedly and late. A lender imposes
a floor strike. A credit limit caps the contracted volume. An internal mandate rules out
tenors below some threshold. A revised LCOE lifts $S^R$. Each of these removes a region
of the contract box.

Under IIA, if the prescribed $(x^\ast, S^\ast)$ survives the refinement, it remains the
prescription and the parties do not reopen the negotiation. Under individual
monotonicity it does not: removing a region that neither party would have chosen still
moves the prescribed strike, because it moved someone's ceiling. For a framework whose
stated purpose is to be a reference point that shortens negotiations, a prescription
that moves for reasons unrelated to either party's valuation of the contract on the
table is a defect.

### 4.2 The specific argument: where the aspiration point comes from in this model

KS is anchored to $\mathbf{a}$, so it is only as well founded as $\mathbf{a}$ is.
Theorem 1 tells us exactly what $\mathbf{a}$ is here. For baseload,

$$\mathbf{B} = \{\mathbf{d} + \mathbf{w} : \mathbf{w} \ge 0,\ w_G + w_L \le D^\ast\},
\qquad D^\ast = \max_{M \in [0, M^U]} \Delta(M),$$

so $a_G = d_G + D^\ast$ and $a_L = d_L + D^\ast$. The aspiration point is governed
entirely by $D^\ast$, and there are two cases:

- **Condition C2 holds.** The maximiser of $\Delta$ is interior, $D^\ast$ is fixed by
  where the parties' marginal tail-adjusted valuations cross, and $\mathbf{a}$ is fully
  endogenous. **KS is perfectly well founded in this case.** The manuscript should not
  claim otherwise.
- **Condition C2 fails.** $D^\ast = \Delta(M^U)$, pinned at the volume cap. The cap is
  a modelling choice (installed capacity, in our case study). KS would then prescribe
  $w_i$ proportional to a number the modeller selected, and doubling the assumed cap
  would move the prescribed strike with no change in anyone's preferences.

For PAP, Section III reports that the DK2 optimum lands in the boundary case with
$\gamma^\ast = 1$. Here the honest qualification is that $\gamma^U = 1$ is a *physical*
bound, not an arbitrary one, so the objection is weaker than in the baseload boundary
case. What remains true is that the aspiration point is determined by a constraint
rather than by the parties' valuations, and that KS therefore inherits whatever the
modeller assumes about the maximum contractible share.

**Summary of 4.2.** The aspiration-point objection to KS is real but conditional: it
bites in the boundary cases and not in the interior ones. State it that way.

### 4.3 The Nash program: the argument that does not depend on axioms at all

This is the strongest reason and it should lead, not trail.

Rubinstein (1982) models negotiation as an alternating-offer game with discounting and
obtains a unique subgame-perfect equilibrium. Binmore, Rubinstein and Wolinsky (1986)
show that as the delay between offers vanishes, that equilibrium converges to the NBS,
with the asymmetric weights $\tau_i$ picking up relative patience and outside options.

The NBS is therefore not only a fairness postulate but a **prediction** of what two
rational counterparties running an offer-and-counteroffer process would converge to.
KS has no comparably standard non-cooperative implementation. Since the paper's stated
aim is to prescribe terms that the parties are *likely to accept*, a rule backed by a
strategic foundation is doing something the axioms alone cannot.

---

## 5. The result that reframes the whole question: for baseload, the rules coincide

**Proposition.** Under the hypotheses of Theorem 1 (baseload, condition C1), the
symmetric NBS, the KS solution and the egalitarian solution select the **same** point of
$\mathbf{B}$, namely $\mathbf{w} = (D^\ast/2,\ D^\ast/2)$. The utilitarian rule attains
the same joint surplus $D^\ast$ but does not pin the split.

*Proof.* By Theorem 1, $\mathbf{B} = \{\mathbf{d} + \mathbf{w} : \mathbf{w} \ge 0,\ w_G + w_L \le D^\ast\}$,
a right triangle whose efficient frontier is the segment
$\mathcal{F} = \{\mathbf{w} \ge 0 : w_G + w_L = D^\ast\}$, of slope $-1$.

*Aspiration point.* Setting $w_L = 0$ gives $a_G = d_G + D^\ast$, and symmetrically
$a_L = d_L + D^\ast$.

*KS.* The rule requires $w_G/(a_G - d_G) = w_L/(a_L - d_L)$, that is
$w_G/D^\ast = w_L/D^\ast$, so $w_G = w_L$. Combined with efficiency,
$w_G + w_L = D^\ast$, this gives $\mathbf{w} = (D^\ast/2, D^\ast/2)$.

*Symmetric NBS.* Maximise $w_G w_L$ subject to $w_G + w_L = D^\ast$. By AM-GM the
maximum is at $w_G = w_L = D^\ast/2$.

*Egalitarian.* Maximise $\min(w_G, w_L)$ over $\mathcal{F}$; the maximum is at
$w_G = w_L = D^\ast/2$.

*Utilitarian.* $w_G + w_L = D^\ast$ for every point of $\mathcal{F}$, so every point is
a maximiser and the rule is not single-valued without a tie-break. $\square$

**Corollary.** The asymmetric NBS gives $w_i^\ast = \tau_i D^\ast$, and the implementing
quantities are exactly the surplus-maximising set $\mathcal{M}^\ast$, independently of
$\tau$ (Theorem 1). So for baseload, bargaining power redistributes the surplus and
never changes its size.

**What this means for the paper.** For the baseload contract, the axiom debate is
*moot*. Any of the three rules gives the same prescribed strike. Spending a table, a
paragraph and an appendix subsection defending a choice that makes no difference for
half the paper is an exposed flank. The better move is to say so, and to report the KS
point alongside the NBS point in Section IV. For baseload the agreement is exact and
provable; for PAP the two differ, and that difference is itself a result.

---

## 6. Where the rules do separate: pay-as-produced

The baseload coincidence is a consequence of the frontier having slope $-1$, which in
turn is a consequence of a single fact:

**Lemma 2 (baseload strike transfers are exact).** For baseload, changing the strike
by $\delta$ at fixed $M$ changes $\pi_G$ by $+\delta M T$ and $\pi_L$ by $-\delta M T$
in *every* scenario. The shift is deterministic, so by translation equivariance of
$\mathrm{CVaR}$ (Lemma 1 with $a=1$), $u_G$ moves by exactly $+\delta M T$ and $u_L$ by
exactly $-\delta M T$. The tail weights do not move at all.

*Consequence.* $\Delta(M) = w_G + w_L$ is **independent of the strike**. Volume sizes
the pie; the strike slices it. Exactly, not approximately. This is what Appendix D
records as "translation equivariance makes the joint surplus independent of strike".

**For PAP this fails.** The contracted payment is $\gamma S \sum_t P^G_{t,\omega}$,
which is *stochastic* because it rides on production. Changing $S$ shifts $\pi_G$ by a
scenario-dependent amount. Translation equivariance does not apply, the tail weights
move, and Appendix D states the consequence directly: under PAP, joint utility
generally depends on the strike. Therefore:

- the constant-$\gamma$ loci are curved rather than of slope $-1$;
- the efficient frontier $F(a)$ is concave and strictly decreasing but not a single
  line of slope $-1$;
- the NBS maximises $\tau_G \ln(a - d_G) + \tau_L \ln(F(a) - d_L)$, whereas KS selects
  the point where the two normalised gains are equal, and these coincide only if $F$ is
  affine of slope $-1$;
- the negotiated share $\gamma^\ast$ can depend on the bargaining weights, so creation
  and allocation are no longer separable.

**The one-sentence version.** In baseload, the strike only splits. In PAP, the strike
also creates. That is why the axiom choice is invisible in one structure and visible in
the other.

---

## 7. Where Garcia et al. (2020) sits

`sources/Raiffa-Kalai-Smorodinsky Bargaining Solution for Bilateral Contracts in
Electricity Markets.pdf`, cited in the manuscript as
`Garcia2020Raiffa-Kalai-SmorodinskyMarkets`.

It applies the Raiffa-KS rule to bilateral electricity contracts and reports that RKS
beats the NBS. It is not a counterexample to this paper, for four reasons, and the
manuscript's previous characterisation of it was inaccurate.

1. **Different negotiated object.** They bargain over the *delivery schedule*
   $\{x_t\}$, with the contract price $J$ and the total volume $V$ exogenous; $V$ is
   swept as a scenario (145, 165 MWh and so on). This paper negotiates price and
   quantity jointly. Their problem does not have the structure of ours.
2. **Risk-neutral parties.** They maximise expected profit with no risk measure
   anywhere. There is no risk premium and no CVaR, so the entire value-creation
   mechanism of this paper is absent from theirs. By Appendix C, with risk neutrality
   and common beliefs the joint surplus is identically zero in our model.
3. **The comparison is circular.** They rank the two rules by *relative concession*,
   meaning the fraction of its maximum possible profit each party gives up, and find
   55.01 percent for RKS against 56.08 percent for the NBS. But minimising relative
   concession from the aspiration point is precisely what the KS rule is constructed
   to do. Two rules were compared using the objective that one of them optimises by
   definition. This is the decisive point and it is checkable in one paragraph of
   their Section 4.
4. **Their aspiration point is well founded.** It is each party's own unconstrained
   profit-maximising schedule, not a modelling bound. The manuscript previously wrote
   that "its aspiration point is fixed by the bounds imposed on price and quantity",
   which is false about their model. That objection applies to *our* formulation in the
   boundary case (Section 4.2 above), and should be stated as such.

---

## 8. Summary

| Question | Answer |
| --- | --- |
| Do PPAs *require* IIA and scale invariance? | No. There is no such theorem. Axioms are chosen, not derived from the application. |
| Is scale invariance required here? | Yes, and constructively so: without it the prescription depends on the reporting currency (Section 2). |
| Does scale invariance rule out KS? | **No.** KS is scale invariant. Only IIA separates the two. |
| Is the table wrong? | One cell was: egalitarian satisfies IIA. Also, "monotonicity" covered two different axioms. Both now fixed. |
| Is Garcia et al. a problem for us? | No. Different object, risk-neutral parties, circular evaluation metric. But our stated criticism of them was inaccurate and has been rewritten. |
| Are we unsound? | No. The argument was overstated and partly misdirected, not wrong. |
| Does the choice change our baseload answer? | **No. NBS, KS and egalitarian coincide exactly.** |
| Does it change our PAP answer? | Yes, and that is worth reporting as a result. |

## 9. Follow-ups this note implies for the manuscript

- [x] Correct the egalitarian / IIA cell in Table I.
- [x] Split the monotonicity column into individual and strong.
- [x] Remove the claim that utilities may be rescaled "negatively".
- [x] Rewrite the "why NBS" paragraph so that IIA, not scale invariance, carries the
      argument against KS.
- [x] Restate the Garcia et al. criticism accurately.
- [ ] Add the baseload coincidence result (Section 5 above) to Section III.B. It is a
      two-line corollary of Theorem 1 and pre-empts the obvious referee objection.
- [ ] Report the KS point alongside the NBS point in Section IV, for PAP.
- [ ] Promote Lemma 2 (volume sizes the pie, the strike slices it) out of Appendix D
      and into the abstract. It is the sharpest economic statement in the paper.
