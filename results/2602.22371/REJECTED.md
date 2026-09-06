# Rejected: arXiv 2602.22371

Paper: Olivieri, Pogudin, Kramer, [*Quadratization of Autonomous Partial
Differential Equations: Theory and
Algorithms*](https://arxiv.org/abs/2602.22371) (cs.SC, cs.MS, math.DS, math.NA),
25 Feb 2026.

Candidate family: publish a polynomial PDE system
`d_t u_i = p_i(u, d_x u, ..., d_x^h u)` over **Q** together with a differential
order `k` and a bound `l`, and ask for a **monomial quadratization** of order at
most `l` — the set `W = {w_1..w_l}` of auxiliary monomials of Definition 1
(Section 2.2).

Module retained as `rejected_gen_2602_22371.py`; measurements in
`selftest_report.json`.

## Verdict

**G passes. V passes. H fails, on BOTH tracks. G4 fails independently.**

| | verdict | evidence |
|---|---|---|
| **G — generatable** | **passes, cleanly** | The closure conditions of Definition 1 are *linear* in the right-hand side, so for a chosen `W` the admissible right-hand sides form a rational subspace. `make_instance` samples `W` first and then draws `p` from an exact rational nullspace: 0.01–1.6 s per instance, no search for the answer anywhere. |
| **V — verifiable** | **passes, cleanly** | Proposition 2 (Section 3.1.2) turns the definition into a finite exact test: build `V^2`, row-reduce over **Q**, reduce every element of `P`. Measured at **658 exact rational operations** (520 to build the span, 138 to reduce). No float, no numerics, no PDE solving. |
| **H — hard** | **FAILS** | see the two numbers below |

## The two numbers

Shipping preset `n=1, k=3, h=2, l=3`, 8 seeds, same instances for both routes.

| route | what it is | cost |
|---|---|---|
| **mechanical** | QuPDE, the paper's own algorithm: Module 1 (decompositions, heuristic H3) + Module 2 (Proposition 2) + Module 3 (depth-first Branch-and-Bound with PR1, PR2 and the Section 3.1.3 subset-improvement step) | **solves 8/8**; median **1,277 nodes**, **1.79e5** exact rational operations, **4.36 s** |
| **compact** | the best in-context route: take the divisor pool the statement hands you (Section 3.1.1), order it by the degree-counting invariant `deg(w_max) >= deg(p)-1`, run the Proposition-2 test on `l`-subsets | **solves 8/8**; median **5.95e4** operations over **250** subset trials |

(`selftest_report.json`, `G5_density_and_cost`. An independent earlier sweep over
different seeds gave 2,889 nodes / 4.6e5 ops / 7.6 s mechanical against 6.0e4 ops
/ 146–283 trials compact — a 7.7x gap. Both sweeps agree on the conclusion.)

**Gap: 3.0x.** Not 1e3, not 1e6 — three. The two routes are the *same algorithm*:
enumerate candidate monomial subsets derived from the decompositions of the
nonquadratic monomials, and run the linear-algebra closure test on each. QuPDE
only orders and prunes that enumeration better. There is nothing to see, so the
question tests nothing — which is exactly the rejection criterion in
`prompts/codex_task.md` STEP 0.

And the compact route is **not executable in context either**: **59,538** exact
rational operations is **60x** the 1,000-operation cap of G9(c). So the family is
not a Track B family (no short route) and not a Track A family (the standard
algorithm succeeds). It is a raw search problem whose search is cheap for a
computer and impossible for a model, with no insight in between.

## Why: the paper's own Section 3.1.1 is the reason

Section 3.1.1 and equation (9) state it: every auxiliary monomial of a monomial
quadratization is one half of a decomposition of a nonquadratic monomial of the
system, and a monomial of total degree `d` has at most `2^(d-1)` decompositions.

**The published right-hand side names its own candidate set.** Measured across
every preset whose statement stays readable, that set has **14–32 monomials**.
There is no lever that grows it without growing the degree of `p`, which grows
the cost of *every* route superlinearly — so `escalate()` cannot separate the
haystack from the route. This is a property of the problem, not of my
construction.

## Quadratization multiplicity — measured, exhaustively

Number of *valid* quadratizations of size `<= l`, counted by exhaustive
enumeration.

| preset | candidate pool | subsets enumerated | **valid** | density |
|---|---|---|---|---|
| `n=1,k=3,l=3` (5 seeds) | 15–24 | 575–2,324 | **1, 1, 1, 2, 2** | 4.3e-4 … 1.7e-3 |
| `n=1,k=3,l=4` (5 seeds) | 14–26 | 1,470–17,901 | **1, 1, 1, 2, 13** | 5.6e-5 … 4.1e-3 |
| `n=2,k=2,l=3` (5 seeds) | 2–32 | 3–5,488 | **0, 1, 2, 3, 15** | 0 … 6.7e-1 |
| **full pool**, seed 100: all 121 monomials of degree 2–5 and order <= 3 | 121 | **295,361** | **2** | **6.8e-6** |

Two independent readings, both fatal:

1. **G4 fails by three orders of magnitude.** The gate is
   `P(random guess) < 1e-6`, measured structure-aware. The module's own selftest
   measures a structure-aware space of median **816** subsets with density
   **2.03e-3** — **2,000x over the bar**. Per-instance exact valid counts at the
   shipping preset over 8 seeds: **[2, 2, 3, 2, 1, 1, 5, 2]**, median **2**,
   against candidate pools of 12–22 monomials. Even the *naive* full-pool
   density, 6.8e-6, is above the bar.
2. **The answer is not forced.** QuPDE returns a quadratization *different from
   the plant* on **4/8** seeds at `l=3` and **8/8** at `l=4`. `verify` must
   accept any valid witness (and does), so the family grades a set that a solver
   can reach several ways.

## Attacks run, and what they did

Track A would need every entry to have `successes == 0`. All four succeed.

| attack | successes / attempts at the shipping preset |
|---|---|
| QuPDE Branch-and-Bound (the domain-standard algorithm, Section 3.1.3) | **8 / 8**, median 1,277 nodes / 1.79e5 ops / 4.36 s |
| compact divisor-pool enumeration (the in-context attack) | **8 / 8**, median 250 trials / 5.95e4 ops |
| greedy residual-shrink (add the divisor that shrinks the residual most) | **6 / 8** |
| random restart, 2,000 draws from the structure-aware pool | **8 / 8** |

All four succeed. The random-restart line is the one that should end the
discussion: uniform sampling from the pool the statement itself hands you finds a
valid quadratization within 2,000 draws on every instance, which is exactly what
a density of 2.0e-3 predicts.

## The QuPDE reimplementation is faithful

Validated against the paper's own benchmarks (Section 4.1, Table 1) before being
used as evidence:

| PDE | paper's quadratization (Table 1) | mine |
|---|---|---|
| Harry Dym, `u_t = u^3 u_xxx` (28) | `u^3`, `u_x^2 u` | `u^3`, `u u_x^2` ✔ |
| Allen–Cahn, `u_t = u_xx + u - u^3` (48) | `u^2` | `u^2` ✔ |
| modified KdV | `u^2` | `u^2` ✔ |
| Example 5/6, `u_t = u^2 u_xxx` (18) | `u^2`, `u_x^2` | `u^2`, `u_x^2` ✔ |
| nonlinear heat, `u_t = u_xx + u^6` (49) | `u^2, u^4, u^5` (order 3) | `u^2, u^3, u^5` (order 3) ✔ |

Node counts are in the paper's own range (Table 1 reports 1–2,107 nodes and
8.8 ms – 636 s over the fourteen benchmarks; mine reports 34 nodes on Dym against
the paper's 21, and 2–10 on the millisecond-scale examples). Where the Module 1
pseudocode is ambiguous — it decomposes "the lowest-degree nonquadratic
monomial" while Module 3 line 9 says "Module 1 of `R_nq`" — I implemented the
*wider*, strictly stronger reading and branch on every nonquadratic monomial, so
the mechanical cost reported here is an upper bound on the true one and the
rejection is conservative in the right direction.

## Presets and the escalation ladder (both measured)

| preset | `ell` | `k` | rhs terms / degree | answer chars | answer atoms | build |
|---|---|---|---|---|---|---|
| demo | 1 | 2 | 3 / 4 | 20 | 6 | 0.00 s |
| easy | 2 | 3 | 6 / 4 | 52 | 16 | 0.01 s |
| **medium (shipping)** | 3 | 3 | 7 / 5 | **78** | **24** | 0.04 s |
| hard | 4 | 3 | 9 / 5 | 104 | 32 | 0.68 s |

The `demo` rung really is hand-solvable: `d_t u = -2 u^2 u_x^2 + u - 1` with
answer `w = u^2 u_x`, checkable on paper in a minute.

`escalate()` moves three axes at fixed answer length — `aux_ord`, `aux_deg`,
`nterms` — and the escalated instance builds and verifies at the same 78
characters / 24 atoms. A later rung reaches `n=2, k=5, aux_deg=6, aux_ord=4` and
still verifies, but takes 103.7 s to generate and pushes the answer to 222
characters (the exponent-vector length is tied to the differential order). One
intermediate rung (`aux_deg=6, k=4`) fails to generate inside the 400-attempt
budget. So the ladder works, and it is not the reason the family fails.

## Gate results as measured (`selftest_report.json`)

| gate | number | verdict |
|---|---|---|
| G1 planted verifies | **42 / 42** across all four presets | pass |
| G2 rejects corruption | 7 distinct reasons | pass |
| G3 round-trip | parses model-style output, rejects junk | pass |
| G4 guess resistance | density **2.03e-3** vs required 1e-6 | **FAIL (2,000x)** |
| G5 density + cost | valid answers median **2**; mechanical 1.79e5 ops, compact 5.95e4 ops, gap **3.0x** | **FAIL** |
| G6 adversary panel | 8/8, 8/8, 6/8, 8/8 successes | **FAIL** |
| G7 scales | escalates on `aux_ord`, `aux_deg`, `nterms` at answer fixed to 78 chars / 24 elements | pass |
| G8 canonical_key | 24/24 distinct, 24/24 invariant under a common rescaling of the system | pass |
| G9 caps | answer **78 chars / 24 elements / ~19 tokens** (well inside 2,000 / 256); intended route **59,538 operations** vs cap 1,000 | **FAIL (60x on operations)** |

The answer size was never the problem: 78 characters and 24 atoms against caps of
2,000 and 256. The problem is that there is no route to it that a model can run.

## What I relied on, by number

- **Definition 1** (Section 2.2) — the definition of a quadratization of
  differential order `k`; fixed the semantics of `verify`.
- **Theorem 1** (Section 2.3) — every order-`h` polynomial PDE has a monomial
  quadratization of differential order `3h`; guarantees instances are always
  satisfiable, which is why generation never has to check for existence.
- **Proposition 1** (Section 2.3) — finding an *optimal* monomial quadratization
  is NP-hard, by reduction from the ODE case of reference [32]. This is
  **worst-case** hardness and, as `prompts/codex_task.md` warns, it does not
  transfer to the planted distribution: measured, it does not bite.
- **Proposition 2** (Section 3.1.2) — the exact verifier. This one is a genuine
  gift and is the reason G and V pass so cleanly.
- **Section 3.1.1, equation (9)** — the `2^(d-1)` bound on decompositions. This
  is the result that killed the family: it is what makes the candidate pool
  small and knowable from the published statement alone.
- **Section 3.1.3, Module 3** and **Table 1** (Section 4.2) — the algorithm and
  its measured cost on real PDEs.

## What would change the verdict

Nothing available inside this paper. To pass G4 the structure-aware pool would
have to reach ~90 monomials at `l=4` (for a space of ~2e6), which needs
right-hand sides of degree 8+ with many high-degree monomials; that inflates the
printed statement past readability *and* raises the compact route from 6.0e4 to
an estimated 1e7 operations, widening the very gap between "insight" and
"arithmetic" that G9 exists to close. The three other candidate families in the
paper are worse: producing the quadratic right-hand sides `g_1..g_{n+l}` given
`W` (Module 2's output) is a single linear solve and fails H outright; the
minimum differential order `k` is an integer with no witness for the negative
side; Module 4's polynomialization of rational PDEs (Section 3.1.4) has exactly
the same decomposition structure and the same small candidate pool.

A documented rejection, with both routes costed, rather than an "an algorithm
exists" dismissal.
