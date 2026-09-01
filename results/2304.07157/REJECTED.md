# Rejected: arXiv 2304.07157

Paper: Aleksandr D. Krotov and Denis S. Krotov, [*Do K33-Free Latin
Squares Exist?*](https://arxiv.org/abs/2304.07157), arXiv:2304.07157.

## Decision

This paper does not yield a problem family satisfying G, H, and V. In
particular, the suggested switched-combination family fails **H**, and the
paper's existence problem fails scalable **G**. Per Step 0 of the task, no
generator, self-test report, or oracle transcript was fabricated after this
failure was established.

## Exact definition checked

Section 1 defines a Latin rectangle as a set of triples `(row, column, letter)`
with no two triples differing in exactly one coordinate. Proposition 1 proves
that an induced `K_3,3` is exactly the stated six-cell pattern on three distinct
rows, columns, and letters. Thus checking a supplied Latin square and scanning
for the forbidden pattern is exact and polynomial-time; **V** itself is not the
problem.

## Why the suggested family fails H

Section 4 defines a switched combination of two order-`n` Latin squares using
an `n x n` binary switching matrix. The two input squares must be orthogonal.
The second lemma in that section proves that a forbidden pattern occupying six
blocks survives precisely for switching matrices with even parity on those six
positions. The authors then give the complete search method (immediately after
that lemma): find every forbidden pattern in the zero-combination and add the
equation

```text
s[i,j''] + s[i',j''] + s[i,j] + s[i',j'] + s[i'',j] + s[i'',j'] = 1
```

over `GF(2)` for each pattern. Any solution of this linear system produces a
`K_3,3`-free switched combination. Gaussian elimination therefore finds a
switching witness in polynomial time. H explicitly disallows a known
polynomial-time method, so neither the switching matrix nor the resulting
combined Latin square can be shipped as a hard witness task.

The reported order-16 construction reinforces the issue rather than avoiding
it: only one of the 11,887 equivalence classes of order-8 orthogonal pairs gives
a solvable system, and that system has `2^15` solutions obtained by row/column
changes. This is a finite classified construction, not an unlimited hard
family.

## Why the other paper-native choices also fail

| Candidate witness task | Failed requirement | Paper evidence |
|---|---:|---|
| Construct a `K_3,3`-free Latin square of growing order | G | Sections 1 and 4 give examples only at orders 8 and 16. The conclusion says generalization to higher orders remains open; for orders above 11 other than 16, existence is open. Isotopes of the fixed squares are relabellings and must collapse under `canonical_key`, so they cannot satisfy G7/G8 diversity. |
| Find a forbidden `K_3,3` pattern in a supplied Latin square | H | Proposition 1 reduces the witness to six cells. Exhaustive enumeration of a fixed-size pattern is polynomial in the square order. |
| Classify or prove absence of such squares/rectangles | witness rule, G | Section 3 is an exhaustive finite classification through the reported small orders. Classification or nonexistence is not a witness of the required kind. |
| Find a `K_4,4` pattern in a linear orthogonal pair | H | Theorem 1 in Section 5 gives an if-and-only-if classification by field parity and `kappa`, and its proof gives explicit witnesses. This is a lookup/closed-form regime plus fixed-size pattern detection. |
| Use transversals, trades, or minimum-support eigenfunctions | G/H as a paper-derived family | Section 2 discusses these only as motivation. It supplies no scalable inverse generator or hardness regime. Importing a separate generic Latin-square completion or transversal problem would no longer be a family justified by this paper, and a planted subfamily would still need an independent hardness argument. |

## Gate outcome

| Gate | Result |
|---|---|
| G (generatable at unbounded growing sizes) | **Fail** for the paper's central existence family |
| H (no known polynomial-time or closed-form method) | **Fail** for switching, forbidden-pattern search, and the Section 5 linear family |
| V (cheap exact witness checking) | Passes for several candidates, but cannot rescue failures of G/H |

The rejection occurs before Step 3 and Step 4. Running the LLM hardening loop on
a task already proved polynomial-time would not establish H and would waste the
oracle budget.
