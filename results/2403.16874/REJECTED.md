# REJECTED — arXiv:2403.16874

**Cohn, de Laat, Leijenhorst, *Optimality of spherical codes via exact semidefinite
programming bounds*** (math.MG; math.OC; cs.IT).

**Verdict: fails H, on BOTH tracks.** G and V both pass and are measured below;
the family is dead on hardness, and it is dead for a structural reason that no
choice of preset repairs.

Module retained as `rejected_gen_2403_16874.py`; every number below is
reproduced by `selftest()` in that file and recorded in `measurements.json`.

---

## The family that was built

The exact rational **dual certificate for the Delsarte two-point LP bound** on
spherical codes — the k=2 case of the k-point bounds described in **Section 1**,
written out in **Appendix A ("Two-point bounds")**, and the exact analogue at
k=2 of the three-point program in **Section 3, equation (3.1)**.

The solver is handed `n`, a rational `s = cos θ`, a degree cap `d` and a claimed
bound `B`, and must produce the Gegenbauer coefficients `(f_0=1, f_1, …, f_d)` of
a polynomial with `f_k ≥ 0`, `f ≤ 0` on all of `[-1, s]`, and `f(1) ≤ B`.

Certificate **planted first**, by inverse generation from complementary
slackness (**Section 3**, the paragraph following equation (3.2)):
`f(t) = (t+1)(t−s)·∏(t−a_i)²`, non-positive on `[-1,s]` by inspection, normalised
to `f_0 = 1`, kept when the Gegenbauer coefficients land non-negative. No LP, no
search, ever runs inside `make_instance`. Sanity check: fed the E8 inner
products `{−1, −1/2, 0, 1/2}` at `n=8`, the construction reproduces the classical
sharp certificate with bound exactly **240**.

---

## Why it fails H — the structural reason

> **The quantity the certificate bounds is the *optimum* of the program, and that
> optimum is a function of `(n, d, s)` alone. A generator can plant a *feasible*
> dual certificate; it cannot plant an *optimal* one.**

So the published bound `B` is always strictly slack, the accepted set is a
full-dimensional convex cone, and the problem degenerates from "find the
essentially unique optimal certificate" to "find any interior point of a cone".

Measured slack of the published bound against the value achieved by a
*hand-executable* certificate (20 seeds/preset):

| preset | B / achieved value, min | median | max |
|---|---|---|---|
| easy | 1.04× | 1.47× | 5.06× |
| medium | 1.15× | 2.01× | 16.17× |
| hard (shipping) | 1.13× | **3.67×** | 48.41× |

**Tightening to `f(1) == B` does not rescue it,** and this is verified
numerically, not asserted: if `f` is accepted with `f(1) = V`, then for
`λ = (B−1)/(V−1) ≥ 1` the certificate `λf + (1−λ)` is *also* accepted — every
`f_k` scales by `λ > 0`, and `λf(t) + (1−λ) ≤ 0` wherever `f(t) ≤ 0` — and it has
`f(1) = B` exactly. Cost: one division and `d` multiplications. Measured on a
shipping instance: `λ = 1.4503`, scaled certificate verifies `True`, `f(1) == B`
exactly.

Making the bound tight would require planting the LP optimum. That optimum is
given in closed form by Levenshtein's theory as an interpolation at roots of
adjacent Jacobi polynomials — **irrational**, so not plantable as a rational
certificate at all, and where it *is* rational the configurations are the finite
classified list the paper's own Table 1.1 enumerates. Either way the answer is a
lookup, not a family.

---

## The two required numbers

| | route | measured at the shipping preset (`dim=48`, `d=10`) |
|---|---|---|
| **mechanical** | exact rational **max-margin (Chebyshev-centre) LP over ℚ** — two-phase simplex, Bland's rule, cutting planes on the continuum constraint | **3.05 × 10⁵ exact operations, 0.51 s, solves 12/12** |
| **compact** | complementary slackness ⇒ `f = c(t+1)(t−s)∏(t−a_i)²`; expand, then one triangular Gegenbauer basis change | **280 exact operations** |

Gap: **1.1 × 10³**, and the mechanical route is half a second of ordinary
arithmetic. For comparison, the shipped Track B family `2302.03715` carries a gap
of **1.8 × 10⁸** with a mechanical route of 1.5 × 10⁶ seconds. A three-order-of
magnitude gap whose expensive side finishes in 0.51 s is not out of reach; it is
one page of tableau work.

*Method note, in the interest of not overstating the kill:* the naive variant of
the same attack — the simplex **minimising** `f(1)` rather than maximising the
slack — solves **0/12** at every preset (2.8–6.2 × 10⁶ ops, 2.4–5.4 s). That
failure is an artefact of the objective, not evidence of hardness: a minimiser
lands exactly on the boundary of the discretised cone and is therefore
generically infeasible between grid points. Reporting only that number would
have been a false negative of exactly the kind this project rejected a family
over. The max-margin objective is the correct standard method for a feasibility
problem, and it succeeds 36/36 across the three presets.

---

## The kill that does not even need a solver

Track B requires a fourth attack that a model could run **in context, without
tools**, and that **fails**. The obvious one succeeds:

> Assume the double roots coincide: `f = (t+1)(t−s)(t−a)^{2m}`, and sweep the
> single rational `a` over 11 grid values.

| preset | solves | median exact ops |
|---|---|---|
| easy | **16/20** | 470 |
| medium | **18/20** | 584 |
| hard (shipping) | **16/20** | 1,144 |

One rational parameter, a coarse sweep, roughly a compact-route budget of
arithmetic — and it produces a *verified* witness on 80–90% of instances. Per the
contract, that alone means "the family is guessable by hand and you should reject
it."

**G4 confirms it independently.** Structure-aware `random_candidate` — the same
ansatz with roots drawn from the instance's own grid — verifies at density

| preset | hits / trials | density |
|---|---|---|
| easy | 960 / 1800 | **0.533** |
| medium | 1009 / 1800 | **0.561** |
| hard (shipping) | 629 / 1800 | **0.349** |

against a G4 requirement of `P(guess) < 1e-6`: off by **5.5 orders of magnitude**.
(A naive uniform prior — random non-negative rationals of small height — scores
0/12000 at every preset. Reporting *that* number would have made a family guessed
one time in three look impossible. It is the structure-aware column that counts.)

Even a **foreign plant** transfers: the certificate from an unrelated instance of
the same preset verifies against 20.0% / 12.1% / 5.3% of other instances.

---

## What G and V did pass — so the decision is re-openable

| gate | measured |
|---|---|
| **G — planted verifies** | 24/24 seeds at each of the four presets, 96/96 total; certificate built, never searched |
| **V — exact** | `Fraction` end to end; no float anywhere in `verify()`. Gegenbauer recurrence over ℚ, sign comparison, Yun squarefree decomposition + Sturm root counting on the odd-multiplicity part (`gvlib.roots`), rational sample-point sign test |
| **V — corruption** | 8 corruption classes rejected, 8 distinct reasons |
| **answer cap (G9c)** | max **326 chars / 20 atoms** at the shipping preset (caps 2000 / 256) — comfortably inside |
| **escalate** | moves 3 axes at fixed answer length — `den_max` 14→20→26→32, `dim` 48→96→192→384, `height_bits` 160→320→640→1280 — with the answer pinned at **20 atoms** (254→258→323→446 chars) across the whole ladder, all rungs building and verifying |
| **valid certificates** | infinitely many: the accepted set is a full-dimensional cone section, so `enumerate_all()` returns `None` honestly and G5 carries the sampled density above |

The answer cap and the escalation ladder are the parts worth keeping: this
family is *not* `cap_bound`. It is genuinely easy.

---

## The three-point track, which is what the paper is actually about

Not built, and here is why, stated so it can be argued with rather than taken on
trust:

1. **Same structural failure.** The objective of **Section 3, equation (3.1)** is
   `1 + ⟨F_0, J⟩`, whose optimum is again a function of `(n, θ, d)` alone. A
   planted feasible `F` gives a strictly loose bound, and the accepted set is
   again full-dimensional. Nothing about moving from k=2 to k=3 changes the
   argument above.
2. **The certificate is, by the paper's own account, solver output.**
   **Section 2** is titled "Rounding procedure" and its entire content is
   converting the floating-point output of an interior-point SDP solver into an
   exact solution — RREF of a numerically computed kernel, Hermite normal form
   (equation (2.2)), LLL, then projection. **Section 2.1** assumes the optimal
   face's kernel "has a nice description over ℚ". This is precisely the
   "certificate is the output of a polynomial-time algorithm run on the instance"
   disqualifier.
3. **Planting one is not available either.** Feasibility needs `F ≤ 0` on the
   trivariate semialgebraic set `Δ`, `3F(u,u,1) ≤ −1` on `[-1, cos θ]`, and
   `F_k ⪰ 0` simultaneously; the SOS route (Section 3) lets you plant the first
   two by choosing the multipliers `q_0,…,q_4`, but then `F_k ⪰ 0` is not
   controllable, which is the same obstruction in a harder form.

**What I could not measure.** I did not obtain the paper's data files
\[CdLL24\] and so did not measure the serialised height of a real three-point
certificate against the 2000-character cap. My arithmetic count says the *shape*
fits at the paper's smallest sharp degree (`d=5`, `n=20`, the Gewirtz graph: the
blocks `F_0..F_5` are 21+15+10+6+3+1 = 56 rationals = 112 atoms, under the 256
cap), but the paper solves those programs to 40 digits before rounding
(**Table 3.1**), so the entries are very unlikely to fit 2000 characters. That is
a guess, and it is labelled as one. It does not affect the verdict, which rests
on point 1 and does not depend on the cap.

---

## Sections and results relied on, by number

- **Theorem 1.1** — the main theorem; the codes proved optimal are the finite
  list of Table 1.2, i.e. the sharp cases are a classification, not a family.
- **Table 1.1** — the previously known optimal codes: the classified list a
  rational sharp certificate would have to come from.
- **Section 2**, incl. **§2.1–§2.3** and equation **(2.2)** — the rounding
  procedure; establishes that the certificate is SDP-solver output plus
  rounding.
- **Section 3**, equations **(3.1)** and **(3.2)** — the Bachoc–Vallentin
  three-point bound and `|C| ≤ 1 + F(1,1,1)`; the paragraph after (3.2) is the
  complementary-slackness statement that supplies the plant.
- **Table 3.1** — solve/round/check timings and the 40–100 digit precision used.
- **Appendix A ("Two-point bounds")** — the k=2 specialisation the module
  implements.

## Files

- `rejected_gen_2403_16874.py` — the module, kept per the contract. Full
  interface (`TRACK`, `DIFFICULTY`, `make_instance`, `render`, `parse_answer`,
  `verify`, `random_candidate`, `search_space`, `enumerate_all`, `canonical_key`,
  `escalate`, `selftest`), plus `reference_algorithm`, `compact_route` and
  `in_context_sweep`. Needs `gvlib` on `sys.path`; set `GV_REPO_ROOT` when
  running it outside `results/<id>/`.
- `measurements.json` — every number above.
- `attacks.py`, `attacks2.py`, `lp2.py`, `slack.py`, `measure_all.py` — the
  attack harnesses that produced them.

No oracle loop was run: no `OPENROUTER_API_KEY` in this environment. The
rejection does not rest on an oracle result — an in-context sweep solving 16/20
and a structure-aware guess density of 0.35 settle it without one.
