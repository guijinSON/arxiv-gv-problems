# Rejected: arXiv 2402.17528

Paper: Gary Greaves and Sho Suda, [*Constructions of t-designs from weighing matrices and association schemes*](https://arxiv.org/abs/2402.17528).

## Decision

No problem family in the paper meets gate **H (hard)**, and the paper's flagship
families also fail the structure-aware form of **G4 (guess resistance)**.  Per the
task instruction to stop when G, H, or V fails, no generator, self-test report, or
LLM-hardening transcript was produced.

## What was checked in the full paper

Section 1.4 defines

\[
\mathfrak B_A(v,k,a)=\{\alpha\in\tbinom{[v]}k:\det A[\alpha]=a\}.
\]

Theorem 2.2 proves that this explicitly defined block collection is a
`t`-design when the `k`-principal minors take two values and certain
characteristic-polynomial coefficients are constant.  The actual parameter
regimes used in Section 2 have fixed `k`: conference matrices use `k=4` or `5`,
while the equiangular-tight-frame, Hadamard, and doubly-regular-tournament
examples use `k=3` or `4`.  The association-scheme extensions in Theorems 3.1
and 3.8 and the signed-hypercube and balanced-generalised-weighing-matrix
constructions in Theorems 3.10 and 3.12 again use `k=4`.  Theorem 4.2 uses blocks
of sizes `3` and `4`.

Section 5 confirms that larger block size is not a proved hard regime: it asks
as an open question whether any example with `k >= 6` exists.  The paper
contains no complexity or hardness theorem, no NP-hard regime, and no search
problem with a hidden witness.

## Why the natural candidate is easy

Given `A`, `k`, and `a`, every block is obtained by enumerating the
`binom(v,k)` subsets and computing a constant-size determinant.  In every
proved infinite family above, `k <= 5`, so this takes polynomial time
(`O(v^5)` determinant tests, with constant matrix dimension).  Asking for one
block is no harder: the same enumeration finds one.  Asking for the complete
design is also direct enumeration of the definition.  This violates H's
requirement that there be no known polynomial-time or closed-form method.

Some families are easier still.  Lemma 3.9 identifies determinant-4 blocks of
the signed hypercube exactly with its induced 4-cycles, which can be generated
directly by choosing a vertex and two coordinate directions.  Theorems 2.2,
3.1, and 3.8 give closed formulas for the design/PBIBD incidence counts rather
than concealing a witness.

## Structure-aware guessing also fails on the flagship designs

For a `t-(v,k,lambda)` design, a uniformly random structurally valid candidate
(`k` distinct vertices) is a block with exact probability

\[
\frac{|\mathfrak B|}{\binom vk}
=\frac{\lambda}{\binom{v-t}{k-t}}.
\]

Applying the parameters stated in Examples 2.3 and 2.4 gives:

| construction and target minor | exact probability | limit |
|---|---:|---:|
| symmetric conference, `k=4`, `a=5` | `3n/(4n-1)` | `3/4` |
| symmetric conference, `k=4`, `a=-3` | `(n-1)/(4n-1)` | `1/4` |
| skew conference, `k=4`, `a=1` | `3(n-1)/(4n-3)` | `3/4` |
| skew conference, `k=4`, `a=9` | `n/(4n-3)` | `1/4` |
| skew conference shifted by `+/- I`, `k=5`, minor of magnitude `16` | `3(n-1)(n-2)/binom(4n-3,2)` | `3/8` |
| skew conference shifted by `+/- I`, `k=5`, minor of magnitude `32` | `5n(n-1)/binom(4n-3,2)` | `5/8` |

These are orders of magnitude above the required `10^-6` bound.  This is an
exact count, so a 200,000-sample experiment would add noise rather than useful
evidence.

## Why no alternative was manufactured

One could invent an inverse matrix-completion, design-reconstruction, or
arbitrary target-principal-minor puzzle inspired by the notation.  None is the
problem studied in this paper, and the paper supplies no hardness result or
hard parameter regime for it.  Claiming H for such a puzzle would therefore be
unsupported.  Asking the solver to construct the conference, Hadamard, or
weighing matrix does not help: the infinite orders usable by an unconditional
generator come from the same explicit Paley/Kronecker constructions available
to the solver, while the general existence questions are open.  The paper's
genuine open questions ask for existence, which would make a negative answer
an impermissible absence witness and positive witness generation dependent on
unresolved research.
