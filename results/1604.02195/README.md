# arXiv:1604.02195 — a not-necessarily-symmetric matrix with a given spectrum and a given graph

Keivan Hassani Monfared, *Existence of a Not Necessarily Symmetric Matrix with Given
Distinct Eigenvalues and Graph*, Linear Algebra Appl. **527** (2017) 1–11
([abs](https://arxiv.org/abs/1604.02195), math.SP / math.CO / math.DS).

## Profile

| field | value |
|---|---|
| `TRACK` | **B** — an efficient algorithm exists and is named below |
| `native_domain` | algebra |
| `object_regime` | rational_exact |
| `computational_core` | linear_algebra |
| `certificate_form` | matrix_certificate |
| `intuition_type` | decomposition (the three-term recursion / continued fraction) |
| `domain_essentiality` | **native** — `reduction_kind = none` |
| shipping preset | `hard` — n = 8, num_max = 9, den_max = 2, b_num_max = 4, scrambled labels |

The solver is handed a graph, a matrix over ℚ with holes in it, and two characteristic
polynomials over ℚ, and must return matrix entries. Nothing is compiled into a graph
surrogate: the graph *is* the paper's object (Section 1 defines the graph of a matrix),
and `verify()` operates on the matrix itself.

## What the family is

The paper's main theorem (Section 3) says: for `k` distinct conjugate pairs
λ_j ± μ_j i, `l` distinct reals γ_j, and **any** loopless graph `G` on `n = 2k+l`
vertices with a matching of size ≥ k, some real matrix has exactly that spectrum and
exactly that graph. The proof is non-constructive — it perturbs the block-diagonal
matrix of Example 2.4 and applies the Implicit Function Theorem to the Jacobian of
Corollary 2.8 — so it certifies existence and hands you no formula. The corollary that
closes Section 3 is the case used here: *a real matrix has distinct eigenvalues iff it
is similar to a real irreducible tridiagonal matrix*, i.e. `G` may be taken to be the
path `P_n` (matching number ⌊n/2⌋ ≥ k for every admissible split).

An instance publishes

* the path `G` as an **edge list on scrambled vertex labels** (so the matrix is not
  visibly tridiagonal);
* **one** entry per edge — at a randomly chosen one of the two directions;
* `p(x) = det(xI − A)` and `q(x) = det(xI − Â)`, where `Â` deletes the row *and* the
  column of one endpoint `v0` of the path;
* the split of the spectrum into `l` real roots and `k` conjugate pairs, certified at
  generation time by a Sturm chain (`gvlib.roots`), never by a root-finder.

and asks for the `2n−1` missing entries: the `n` diagonal entries and, for each edge,
the direction that was not published.

**Checking is cheap and exact.** `verify()` assembles the matrix, checks that every
off-diagonal entry at an edge is nonzero (that is the definition of "the graph of A is
G"), computes `det(xI − A)` by fraction-free **Bareiss** determinants at `n+1` rational
nodes plus exact Lagrange interpolation, and compares coefficient by coefficient with
`p`; then the same for `Â` against `q`. No eigenvalues are ever computed and no root is
ever isolated inside `verify`. No float is created anywhere in the generation or
verification path — the only floats in the file are `escalate()`'s growth multipliers
(immediately truncated to ints) and the p-values, rates and timings in the report.

**The realisation is unique — exactly one matrix, not one orbit.** `p` and `q` are
monic of consecutive degree, so the Euclidean division `p = (x − d₁)q − e₁r` has a monic
linear quotient (forcing `d₁`), a remainder of degree exactly `n−2` (forcing the edge
product `e₁` from its leading coefficient and `r` from the rest), and `(q, r)` is the
same problem one vertex shorter. Induction gives one `(d, e)`, and one published entry
per edge turns each product `e_i` into one entry. Over ℚ **and** over ℂ the count is 1.
That is why one entry per edge is published: without it the diagonal similarity
`A ↦ DAD⁻¹` fixes both the spectrum and the graph and leaves a continuum of realisations.

## Why it is hard — Track B

**The algorithm that exists**, named as Track B requires: the root-free form of the
**de Boor–Golub inverse Jacobi reconstruction** — the continued-fraction expansion of
`q/p`, i.e. `n−1` Euclidean divisions of monic polynomials of consecutive degree.
Complexity `O(n²)` exact rational operations; **measured at 147 operations and
3.7e-4 s** at the shipping preset (`selftest_report.json`, `G6.reference_algorithm`),
solving 8/8.

**The mechanical route** — what is left to a solver who does not see the recursion — is
`2n−1 = 15` unknown entries against 15 polynomial coefficient equations of degree up to
⌊n/2⌋ = 4, i.e. enumerate the certificate language and recompute both characteristic
polynomials per candidate: **2.9e17 candidates, 2.3e19 operations, 1.5e14 s
extrapolated** at the measured rate, and that is *after* the two entries that leak for
free are fixed. The gap is 1.6e17×.

Neither number is executable in context: the mechanical route is out of reach for any
machine, and the compact route is 147 exact rational operations on 5–7 digit numerators
— reachable by a careful solver with no tools, and only if the recursion is seen.

### The spectral shortcut, measured (this is the attack that decides the family)

Newton's identities turn `p` into the power sums `tr(A^k)` with no root-finding, so the
right question is whether `tr(A^k)` leaks the entries. Measured by building the
symbolic power sums of the path matrix, linearising (every monomial in the entries an
independent unknown) and asking which entry variables the linear system pins:

| data used | equations | monomials | entries determined |
|---|---|---|---|
| power sums of `p` alone | 8 | 856 | **0 of 15** |
| power sums of `p` and `q` | 15 | 856 | **1 of 15** (`d₁ = tr A − tr Â`) |
| coefficients of `p` and `q` | 15 | 984 | **1 of 15** |

One further *nonlinear* substitution (squaring the recovered `d₁` inside
`tr A² − tr Â² = d₁² + 2e₁`) yields a second entry. The remaining 13 need the peel
itself. So the trace/Newton route does **not** break the family: it is an alternative
*entrance* to the same recursion — which on Track B is expected, since the recursion is
the declared efficient algorithm — and not a one-shot read-off. `random_candidate`
hands the guesser both leaked entries for free, so `P(guess)` is not measured against a
prior a solver can beat.

## Worked example (`demo`, seed 1) — solvable on paper

```
E = {{0,1}, {1,2}, {2,3}};   A[0][1] = -1,  A[2][1] = 1,  A[2][3] = 1
p(x) = x^4 + 4x^3 + 6x^2 + 5x + 8          q(x) = x^3 + 3x^2 - 7   (delete vertex 0)
ask: (0,0), (1,0), (1,1), (1,2), (2,2), (3,2), (3,3)
```
By hand: `p ÷ q` has quotient `x + 1`, so `d₁ = A[0][0] = −1`; the remainder is
`3x² + 12x + 15`, so `e₁ = −3` and `r = x² + 4x + 5`; with `A[0][1] = −1` published,
`A[1][0] = 3`. Repeat on `(q, r)`. Answer: `-1, 3, 1, 1, -2, -1, -2`, and
`verify` returns `(True, 'ok')`. Corrupt one diagonal entry and it returns
`(False, 'det(xI-A) differs from p at the coefficient of x^0 (got 15, want 8)')`;
zero an off-diagonal entry and it returns
`(False, 'A[1][2] = 0 at the edge {1,2}: the graph of A is not G')`. The demo is 39
operations and genuinely hand-scale; the shipping preset is the same route at 147
operations with 5–7 digit rationals.

## Difficulty presets

| preset | n | num_max | den_max | b_num_max | scrambled | answer atoms | answer chars | route ops |
|---|---|---|---|---|---|---|---|---|
| demo | 4 | 3 | 1 | 1 | no | 7 | 22 | 39 |
| easy | 6 | 6 | 1 | 2 | yes | 11 | 34 | 85 |
| medium | 7 | 8 | 2 | 3 | yes | 13 | 56 | 114 |
| **hard (ships)** | 8 | 9 | 2 | 4 | yes | 15 | 59 | 147 |

No preset was rejected by a gate. `demo` is an illustration, not a rung: it is
hand-solvable by design and `harden.py` skips it.

## Gate results

| gate | measured |
|---|---|
| G1 planted verifies | 32/32 (4 presets × 8 seeds) |
| G2 rejects corruption | 13 corruptions, 8 distinct reasons, 0 accepted — including a **different matrix with the same `p`** rejected on `q` |
| G3 round-trip | parses a prose-wrapped reply, an untagged comma list and a fenced JSON list; rejects junk |
| G4 guess resistance | 0/200 000 structure-aware samples, 0/2 000 full verifies; analytic P = 3.5e-18 (naive 1.5e-22) |
| G5 density + cost | valid answers at shipping = **1** (theorem + 0/20 000 sampled); exhaustive count over the whole demo grid = **1 of 518 616**; strongest attack 2.9e17 candidates / 2.3e19 ops / 1.5e14 s (1 950 candidates/s measured); compact route 147 ops / 3.7e-4 s |
| G6 adversary panel | 5 attacks, 0/8 each; `reference_algorithm` (the peel) 8/8 as Track B requires |
| G7 scales | escalation moves `num_max`, `den_max`, `b_num_max` with n and the answer length fixed at 15 atoms; n = 16 builds and verifies at 555 ops |
| G8 canonical key | 120/120 invariant under relabelling, transposition and their compositions; 120/120 transformed instances verify against the carried answer; 24/24 distinct keys |
| G9 caps | 59 chars, 15 elements, 147 route operations at seed 23; worst case over 150 shipping seeds 71 chars / 57 tokens / 15 elements / 147 ops (the op count depends only on n) against caps 2000 chars / 256 elements / 1000 ops |

`attacks`, all failing at 8 seeds: `linearised_coefficient_solve` (elimination after
linearising — 15 equations against 984 monomials, nullity 969),
`newton_power_sums_p_only` (the spectral shortcut above),
`greedy_coefficient_hill_climb` (the in-context attack: start from the freely deducible
entries and change one entry at a time keeping any improvement in matched coefficients),
`random_restart_structure_aware` (20 000 structure-aware samples per seed),
`symmetric_or_antisymmetric_ansatz` (the first thing a solver tries by hand: make `A`
symmetric or skew, fit the diagonal by the trace).

## The oracle loop and the G9 arms

**Not run in this build**: no `OPENROUTER_API_KEY` was available in the environment, so
`llm_loop_transcript.jsonl`, `.meta.json` and the three G9 arms (bare / hinted /
placebo) are owed by whoever runs STEP 4. `G9.arms` is recorded as 0/0 with that note,
and it is a diagnostic, never a gate. The escalation ladder is already measured for
that run and is in `G7.ladder`:

| escalation | n | num_max | den_max | b_num_max | answer atoms | route ops |
|---|---|---|---|---|---|---|
| 1 | 8 | 18 | 3 | 8 | 15 | 147 |
| 2 | 8 | 30 | 4 | 12 | 15 | 147 |
| 3 | 9 | 42 | 4 | 18 | 17 | 184 |
| 4 | 9 | 84 | 5 | 36 | 17 | 184 |
| 5 | 9 | 142 | 6 | 54 | 17 | 184 |
| 6 | 10 | 198 | 6 | 81 | 19 | 225 |

Two of every three escalations hold `n` and the answer length fixed and buy difficulty
from entry height, denominator range and the height of the published entries — the
haystack grows, the needle does not. `escalate()` returns `"cap_bound"` only if the
answer would pass 2 000 chars / 256 atoms or the route would pass 1 000 operations.
Measured: the binding cap is the route, at **n = 22 (1 029 operations)**; the answer is
still only 43 atoms / 184 chars there, so the height axes remain open indefinitely below
n = 22 and there is a lot of ladder left above the shipping preset.

## How to use it

```python
import gen_1604_02195 as G
inst = G.make_instance(seed=23, **G.DIFFICULTY[G.SHIPPING_DIFFICULTY])
print(G.render(inst))                     # the whole problem statement
ans  = G.parse_answer(model_reply)        # tolerant of prose and fences
print(G.verify(inst, ans))                # (True, 'ok') or (False, reason)
```

```bash
scripts/emit.sh 1604.02195                # writes artifacts/1604.02195.jsonl
python3 results/1604.02195/gen_1604_02195.py   # runs selftest(), ~9 minutes
```

`gvlib` is used for the Bareiss determinant, the exact rank/solve in the attack panel
and the Sturm chain that splits the spectrum. The module also carries self-contained
fallbacks for all three, so it runs standalone: with `gvlib` unimportable it produces
**identical instances** (checked: same `k`/`l` split, same canonical key, same 147-op
route at seed 23), and the only thing it loses is the `linearised_coefficient_solve`
attack, which needs an exact linear solver. The fallback Sturm counter was checked
against `gvlib.roots` on 300 random polynomials with 0 mismatches, and `_charpoly` was
checked against the Leibniz permutation expansion of `det(xI − A)` on random dense
rational matrices.

## Caveats — read these

1. **The compact route is a textbook algorithm.** Continued fractions of `q/p`, the
   root-free de Boor–Golub reconstruction: a model that recognises "two nested
   characteristic polynomials of a tridiagonal matrix" has the whole method. This is
   declared, not hidden — it is what `TRACK = "B"` means. The family's difficulty is
   (a) recognising the recursion behind a scrambled edge list and a published entry on
   a random side of each edge, and (b) executing 147 exact rational operations on 5–7
   digit numbers without a calculator. If the oracle pool solves the shipping preset,
   the honest move is to escalate the height axes (which make the arithmetic heavier
   without lengthening the answer), not to reject the paper.
2. **Attacks not run.** No Gröbner basis, no resultant elimination, and no
   floating-point Newton with rational reconstruction — the module is standard-library
   plus `gvlib`, which deliberately carries no Gröbner engine. All three are *expected
   to succeed* given a computer algebra system, exactly as the declared reference
   algorithm does; on Track B that is the premise, not a hole. What matters is that
   each costs ≳1e5 operations (a 15×15 Jacobian solve per Newton step) and none is
   executable in context. A Track A claim here would be false, and is not made.
3. **What `P(guess) = 3.5e-18` means.** It is measured against a prior that already
   knows the entry heights, that every off-diagonal entry is nonzero, the trace, and
   the two entries that leak from the power sums. It does *not* model a solver who has
   started the peel — after `t` peel steps the residual space is the same problem at
   `n − t`, and after `n − 1` steps it is a single point. The number bounds guessing,
   not partial insight.
4. **The answer is unique, so there is no partial credit.** One wrong entry fails the
   coefficient comparison. That is a property of the design (it is what makes the
   realisation count 1) and it makes the family unforgiving: a solver who peels four of
   seven steps correctly scores zero.
5. **What would make this family easy.** Publishing `p` alone (the realisation set
   becomes (n−1)-dimensional *and* constructively easy: pick any monic `q` coprime to
   `p` and expand). Using a star or any graph with small matching number instead of the
   path (the coefficient system becomes linear in the edge products — a single Lagrange
   interpolation). Publishing both directions of some edge (that edge's step collapses).
   All three are recorded in `NOTES`; none is in the shipped generator.
6. **`verify` does not enforce the height bounds** of `CERTIFICATE_LANGUAGE`; it accepts
   any rational witness. Uniqueness makes that safe — there is no second rational
   solution to accept — and it keeps the checker from rejecting a correct answer for
   being outside a bound the solver was never given.
7. **Coverage bucket, stated plainly.** This is `native_domain = algebra` with
   `computational_core = linear_algebra`: it counts toward the corpus's
   *geometry / linear-algebraic* quota and toward the symbolic-certificate quota, and it
   does **not** count toward the *dynamics / optimization / analytic* quota. The paper
   is cross-listed math.DS, but nothing a solver does here is dynamics, and labelling it
   `analysis` to fill that quota would be the exact failure `corpus_report.py` exists to
   catch.
