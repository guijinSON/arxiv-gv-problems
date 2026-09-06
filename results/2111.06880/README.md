# arXiv:2111.06880 — robust eigenvectors of a symmetric tensor over Q

Paper: **Tommi Muller, Elina Robeva, Konstantin Usevich, "Robust Eigenvectors of
Symmetric Tensors"**, arXiv:2111.06880v3 (math.NA, math.AG, math.SP, cs.NA),
SIAM J. Matrix Anal. Appl., doi:10.1137/21M1462052 —
<https://arxiv.org/abs/2111.06880>.

| field | value |
|---|---|
| `TRACK` | **B** — an efficient algorithm exists and is named below |
| `native_domain` | algebra |
| `object_regime` | `rational_exact` |
| `computational_core` | `polynomial_identity` |
| `certificate_form` | `rational` (a rational unit vector) |
| `intuition_type` | `invariant` |
| `domain_essentiality` | `native` — `reduction_kind: none` |
| shipping preset | `hard`: n=5, d=6, denominator band [20, 80], 45 decoy generators, decoy weights ±[8, 200] |

## What the family is

An instance publishes the **210 integer coefficients of a degree-6 form F in 5
variables**. F is the polynomial form of a symmetric tensor T of order 6 in
dimension 5: `F(x) = T·x^6`, so `grad F(x) = 6·(T·x^5)`.

The solver must return a **rational unit vector x** that is a *robust
eigenvector* of T, in the paper's own sense (Section 2):

1. `<x,x> = 1` exactly, common denominator in the published band, first nonzero
   coordinate positive (so the answer is unique up to nothing at all);
2. `grad F(x) = 6·mu·x` with `mu = F(x) ≠ 0` — x is an eigenvector (`T·x^{d-1} = mu x`);
3. `rho(J) < 1` for `J = H(x)/(6·mu) − 5·x·xᵀ`, H the Hessian of F —
   the paper's **Lemma 4** Jacobian of the tensor power method at x, and
   **Lemma 3**'s sufficient condition for x to be an *attracting* fixed point.

**Checking an answer is cheap and completely exact.** Write `x = a/q` with a an
integer vector. Then `grad F(a)` is an integer vector, and "x is an eigenvector"
is the integer identity `grad F(a)_i · a_j = grad F(a)_j · a_i`. J is a rational
matrix, and for a symmetric J, `rho(J) < 1` iff `I − J` and `I + J` are both
positive definite, which an exact LDLᵀ over Q decides outright
(`gvlib.exact_matrices.is_positive_definite`). `verify()` contains **no floating
point at all** — an AST audit of every function on the verification path is run
by `selftest()` and recorded as `exactness_audit` (0 violations; the in-module
LDL fallback agrees with gvlib on 400/400 random symmetric matrices).

**How instances are built (answer first, no search).** Sample a primitive integer
vector `a` with `|a|² = q²` — the Householder parametrisation of the rational
points of the sphere — so `v = a/q` is a rational unit vector. Sample decoy
integer vectors `w_k` **orthogonal to a**. Publish

    F(x) = A·<a,x>^6  +  sum_k g_k·<w_k,x>^6 ,   A = ±1,  g_k = ±[8, 200].

Because every `<w_k, v> = 0`, the paper's computation (3.3) collapses to
`T·v^5 = A q^6 v` and `T·v^4 = A q^6 v vᵀ`, hence `mu = A q^6` and **J(v) = 0**:
v is an eigenvector and it is robust for every d ≥ 3. This is Theorem 2's
hypothesis in its exactly-certifiable corner — a generator of the symmetric
decomposition that happens to be an eigenvector — and the certificate is what
Lemmas 3–4 produce.

## Why it is hard — Track B, stated honestly

**The efficient algorithm, named:** because every decoy is orthogonal to `a`,
*every* second-order contraction of T has v as an eigenvector. In particular
`Hess F(e_1)` and `Hess F(e_2)` — each read off n(n+1)/2 = 15 published
coefficients — commute on that direction, so **v spans the kernel of their
commutator**. Two 15-entry reads, two 5×5 products, one nullspace:

| route | operations | seconds | solves |
|---|---|---|---|
| **compact: commutator of two Hessians, then its kernel** | **659 exact** | 5.7e-4 | 8/8 |
| unfolding (HOSVD) Gram, *smallest* eigenvector | 1.3e4 exact | 0.01 | 6/8 |
| tensor power method, random restarts (the paper's algorithm) | 1.8e8 float measured / **7.7e8 extrapolated** | 13.6 (512 restarts) | 1/8 at 512 restarts |
| Newton on `grad F(x) = lam·x, <x,x> = 1`, random starts | 5.0e7 float (mean) | 37.6 | 2/8 within 200 starts |
| brute force over the certificate language | **1.05e11 exact** | 3.1e4 extrapolated | — |

The gap the family tests is between the top row and the bottom three:
**659 operations with the invariant, 7.7e8 without it** (a factor of 1.2e6), or
1.05e11 if the solver has no idea at all. 659 exact operations on 13–17 digit
integers is heavy but writable in context; 7.7e8 floating-point operations with
random restarts is not, and neither is a 5×5 Newton solve repeated a hundred
times. That is the entire Track B claim, and the numbers above are measured, not
asserted (`selftest_report.json`, `G5_density_and_cost` and
`G6_adversary_panel`).

**What makes the power method weak here, and why it is not a trick.** The paper's
Theorem 2 is a statement about the *local* Jacobian: `rho(J(v)) < 1` makes v
attracting. It says nothing about the *size* of the region of convergence — the
paper studies those separately (Section 4.4, Theorem 11 and Figure 2, where the
regions for a Mercedes–Benz simplex tensor are sectors for even d and *fractal*
for odd d). Here v is as attracting as a fixed point can be (`rho(J(v)) = 0`,
quadratic convergence) and yet its region of convergence is measured at a cap of
**half-angle 0.208 rad, i.e. 3.2e-4 of the 4-sphere**, because the plant weight
A = ±1 is small next to the decoy weights. Robust does not mean findable. That
decoupling is the honest mathematical content of the instance.

**Eigenvector census at the shipping preset** (the thing that decides whether
"find an eigenvector" is too easy):

| quantity | value |
|---|---|
| eigenvectors of a generic order-6 tensor in 5 variables, `((d−1)^n − 1)/(d−2)` | **781** |
| robust eigenvectors found by 300 random power-method restarts | **4** (basins 192 / 50 / 38 / 20) |
| of those, rational and in the certificate language | **0** — all four are irrational limits |
| valid answers known to exist | **1** (the plant, verified exactly) |
| exact count at the `demo` preset, by exhausting the language | **1 valid out of 192** |

So the robustness requirement is doing exactly the job the paper suggests: it cuts
781 eigenvectors down to a handful, and exactness cuts that handful to one.

## Worked example (the `demo` preset, seed 5)

    +94 x3^4 +1632 x2*x3^3 -864 x2^2*x3^2 +1968 x2^3*x3 -431 x2^4 +648 x1*x3^3
    -2592 x1*x2*x3^2 +3456 x1*x2^2*x3 -1536 x1*x2^3 +1404 x1^2*x3^2 -3744 x1^2*x2*x3
    +2496 x1^2*x2^2 +504 x1^3*x3 -672 x1^3*x2 +387 x1^4

denominator band [5, 15], d = 4, n = 3.

    answer            <answer>0, 3/5, 4/5</answer>
    verify            (True, 'ok')
    corrupt one num   [[1,1],[3,5],[4,5]]  -> (False, 'not a unit vector: <x,x> != 1')
    a wrong rotation  [[3,5],[4,5],[0,1]]  -> (False, 'grad F(x) is not parallel to x:
                                                      x is not an eigenvector')
    compact route     162 exact operations
    whole language    192 candidates, exactly 1 of them valid

**Can a person do this by hand?** At `demo`, yes: `Hess F(e_1)` and `Hess F(e_2)`
are 3×3 integer matrices read off six coefficients each, their commutator is a
3×3 skew matrix of rank 2, and its kernel is one line — about 160 exact
operations, half an hour with a pen. At the shipping preset the same route is
659 operations on 13–17 digit integers: writable, but only if you know which 30
of the 210 coefficients matter.

## Difficulty presets

| preset | n | d | denominator band | decoys m | decoy weights | coefficients published | answer chars | route ops |
|---|---|---|---|---|---|---|---|---|
| demo | 3 | 4 | [5, 15] | 6 | ±[1,3] | 15 | 18 | 162 |
| easy | 5 | 5 | [15, 60] | 25 | ±[1,9] | 126 | 34 | 659 |
| medium | 5 | 6 | [20, 80] | 35 | ±[1,40] | 210 | 33 | 659 |
| **hard (ships)** | 5 | 6 | [20, 80] | 45 | ±[8,200] | 210 | 35 | 659 |

`n` never moves above 5, so **the answer is always 5 rationals — 10 atoms, ≤ 48
characters — all the way up the ladder**. `escalate()` moves five axes at that
fixed answer length: decoy weight range (shrinks the region of convergence),
number of decoys, denominator band (raises the answer's height without
lengthening it) and, on alternate rounds, the tensor order d. Three escalation
rounds measured:

| round | d | m | weights | band | coefficients | answer chars | atoms | verifies |
|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 60 | ±[40,1000] | [40,160] | 210 | 46 | 10 | yes |
| 2 | 7 | 75 | ±[200,5000] | [40,160] | 330 | 47 | 10 | yes |
| 3 | 7 | 90 | ±[1000,25000] | [80,320] | 330 | 48 | 10 | yes |

`n = 3` at `demo` is the only rung that would fail G4 (only ~2.8e3 rational unit
vectors of denominator ≤ 60 exist in Q³, against 5.0e7 in Q⁵) — that is why the
ladder jumps to n = 5 at `easy` and why `demo` is an illustration, not a
difficulty level.

## Gate results

| gate | result |
|---|---|
| **G1** planted verifies | **32/32** — 4 presets × 8 seeds |
| **G2** rejects corruption | **10/10** corruptions rejected, **6 distinct reasons**; the robustness clause is exercised separately on `F = x³ + 3xy²` at (1,0) — an exact eigenvector with ρ(J) = 2 — which is rejected, while the control `F = x³ + xy²` (ρ(J) = 2/3) is accepted |
| **G3** round trip | parses a prose+markdown model reply, rejects junk and `None` |
| **G4** guess resistance | **0 hits / 200,000** structure-aware samples; language size **49,778,760**; analytic P(guess) = **2.0e-8** |
| **G5** density + cost | density **2.0e-8**; valid answers **1**; strongest attack (power method, 512 restarts) **1.27e8 ops, 6.9 s, does not solve** at the G5 seed (1/8 across the G6 seeds); compact route **659 ops, 5.7e-4 s** |
| **G6** adversary panel | **5 attacks, 0/8 successes each** (below) |
| **G7** scales | size-doubled and escalated instances build and verify; 5 axes move at fixed answer length |
| **G8** canonical_key | **140/140** invariance under variable permutations, sign flips and rescaling of F; **20/20** distinct keys; **140/140** transformed instances verify against the transformed answer |
| **G9** caps | answer **35 chars / 10 atoms / ~9 tokens** (caps 2000 / 256); intended route **659 operations** (cap 1000) |

### G6 attack panel (all failing, 8 seeds each)

| attack | successes |
|---|---|
| `best_rank_one_dominant_eigenvector` — power iteration kept at the largest \|F\| limit | 0/8 |
| `coefficient_outlier` — directions read off the largest/smallest coefficients, the pure powers x_i^d, coordinate vectors | 0/8 |
| `low_height_sweep_in_context` — enumerate the lowest-denominator rational unit vectors, 1200 of them, the ones a solver can write down | 0/8 |
| `random_candidate_2000` — sampling from the certificate language | 0/8 |
| `hosvd_dominant_singular_vector` — unfold the tensor, take the dominant left singular vector (the standard first move in tensor decomposition) | 0/8 |

Reference routes that **do** solve it are reported separately, as Track B
requires, under `G6_adversary_panel.reference_algorithm` and
`additional_reference_routes`: the commutator route (8/8, 659 ops), the tensor
power method (1/8 within 512 restarts, 1.8e8 ops, 13.6 s per instance), Newton on
the eigen-system (2/8 within 200 starts, 5.0e7 ops, 37.6 s) and the HOSVD Gram's
*smallest* eigenvector (6/8, 1.3e4 ops).  The 0.064 s wall clock recorded for the
reference algorithm in G6 includes building the instance; the route itself is
5.7e-4 s (G5 `compact_seconds_shipping`).

## The G9 arms

Not run: this build has no `OPENROUTER_API_KEY`, so the bare / hinted / placebo
diagnostic and the STEP 4 hardening loop were not executed here. The gate's
*gated* part — the size and effort caps — is measured and passes: 35 characters,
10 atoms, 659 route operations. `render()` appends a hint only when
`GV_HINT_MODE` is set, and the selftest asserts the default render contains
neither hint nor any coordinate of the answer.

`STRUCTURAL_HINT` names the invariant and stops: *"The matrix of second partial
derivatives of F, at every point where you evaluate it, has the vector you are
looking for as an eigenvector."* It does not say to take a commutator, does not
chain a second step and states no derived quantity.

## How to use it

```python
import gen_2111_06880 as G
inst = G.make_instance(seed=7, **G.DIFFICULTY[G.SHIPPING_DIFFICULTY])
print(G.render(inst))                     # the whole problem statement
print(G.verify(inst, inst["answer"]))     # (True, 'ok')
print(G.compact_route(inst))              # the intended solution + its op count
```

    python3 gen_2111_06880.py --demo            # render the hand-scale instance
    python3 gen_2111_06880.py --out selftest_report.json
    bash scripts/emit.sh 2111.06880

## Caveats — read these

* **The plant is the quiet direction, and that is disclosed rather than hidden.**
  The decoy weights are 8–200× the plant weight, which is what shrinks the power
  method's region of convergence. The same choice makes the plant the *smallest*
  eigenvector of any second-order contraction, so `probe_hosvd_bottom_singular_vector`
  solves 6/8 at 1.3e4 operations. That probe is deliberately **not** in the attack
  panel: it is the compact route entered from the other end of the spectrum, and
  it needs exactly the insight the family tests (that the answer is an exact
  eigenvector of a second-order contraction). A solver who computes *any* Hessian
  and tests all 5 of its eigenvectors wins. Setting the weights equal instead
  would not make that route harder — it would only hand the tensor power method
  a basin of order 1/80 and make the family easy for a machine.
* **ρ(J(v)) = 0 at every shipping instance.** The planted eigenvector is
  orthogonal to every other generator, which is exactly the condition that forces
  J = 0 (a generator that is a common eigenvector of all the Hessians *must* be
  orthogonal to the others, and conversely). So the robustness clause never
  rejects the *plant*; it is verified, not assumed, and it does reject other
  candidates — but the only demonstration of that in this family is the
  purpose-built `F = x³ + 3xy²` member in G2. A version with `ρ(J)` strictly
  between 0 and 1 would need a generator that is *not* orthogonal to the others
  (the paper's Theorem 6 kernel condition), which kills the compact route and
  makes the coefficients explode by ~q^{d−1}; that regime was rejected, see below.
* **The paper's own new classes are not what this generates.** Section 4's
  equiangular-set and ETF-decomposable tensors (Theorems 6, 8, 10) are the
  paper's contribution, and they are *not* rationally realisable: an equiangular
  set needs |⟨v_i,v_j⟩| equal for all pairs, and already the Mercedes–Benz frame
  of Appendix A needs √3/2. Worse for us, for an ES-decomposable tensor the
  Hessians do **not** share an eigenvector, so the compact route disappears and
  the only remaining routes are the power method and polynomial-system solving —
  no gap, nothing to test, and it would have been a rejection. This family uses
  Section 2's definitions, Lemmas 3–4 and the hypothesis of Theorem 2, which is
  the part of the paper that survives exact rationality.
* **P(guess) = 2.0e-8 is the probability of hitting the *one known* valid answer**
  under a sampler drawn from the same distribution as the plant. Other valid
  answers would have to be rational robust eigenvectors of the decoy part; a
  300-restart numerical census found four robust eigenvectors and none of them
  rational, and 200,000 sampled candidates produced zero hits, but this is
  evidence, not a proof of uniqueness.
* **`canonical_key` is an invariant, not an isomorphism test.** It is invariant
  under variable permutations, sign flips and rescaling of F — the relabellings a
  solver could apply — but two instances related by a general rational orthogonal
  change of coordinates would get different keys. Deciding that equivalence is
  the tensor-isomorphism problem and is not attempted.
* **Attacks not tried.** No Gröbner/resultant elimination of the eigen-system was
  run (781 solutions of a degree-5 square system in 5 unknowns; the Newton
  sampling above is the practical stand-in), no polyhedral homotopy solver, no
  LLL against the coefficient lattice, and no attempt to recover the decoy
  subspace via the apolar ideal. On that last one: the middle catalecticant of
  the shipping form is 35×35 with 46 generators in the decomposition, so it has
  full rank and no kernel for a Sylvester-style method to use — which is also why
  this family is *not* a Waring-decomposition problem.
* **Relation to the already-shipped `2302.03715`.** That family is Waring
  decomposition of a cubic form recovered by Sylvester/Prony: the answer is n+2
  pairs (μ_i, t_i) and the insight is a change of variables collapsing the form to
  a binary one. Here the answer is a *single rational unit vector*, the object is
  an *eigen*-problem rather than a decomposition, the certificate includes an
  exact positive-definiteness test (LDLᵀ over Q) that has no counterpart there,
  and the insight is an invariant of the second-order contractions rather than a
  substitution. The two share only the ambient notion of a symmetric tensor.
