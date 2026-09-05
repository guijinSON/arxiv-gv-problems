# Rejected at Step 0: arXiv 1305.0539

Paper: Elizabeth S. Allman, John A. Rhodes, Bernd Sturmfels, and Piotr
Zwiernik, [*Tensors of Nonnegative Rank Two*](https://arxiv.org/abs/1305.0539)
(2013).

## Decision

No native family in this paper clears **G + H + V**. The prior-triage
rank-two decomposition proposal is generatable by inverse construction and its
factorization is an exact witness, but it fails **H on Track A** because the
paper gives a polynomial-time characterization and a constructive proof. It
also fails **H on Track B**: the same constant-size matrix-pencil/face-minor
calculation that mechanically produces the certificate is already the shortest
structural route. There is no meaningful compression gap.

Implementation therefore stopped before STEP 1, as STEP 0 requires. No
generator, self-test report, or oracle transcripts were created.

## What the paper actually proves

Section 1 defines a nonnegative-rank-at-most-two tensor as

`P = a_1 ⊗ ... ⊗ a_m + b_1 ⊗ ... ⊗ b_m`,

with every factor vector nonnegative. Theorem 1.1 says this is equivalent to
two executable conditions: all matrix flattenings have rank at most two, and
the entries are multiplicatively supermodular after independently ordering the
labels in every mode.

The proof is constructive, not merely existential:

- Proposition 2.2 reduces the `2 × 2 × 2` case to a real rank-two
  decomposition and checks nonnegativity through explicitly displayed
  determinants, marginals, and the hyperdeterminant.
- The proof of Theorem 1.1 in Section 3 obtains nonnegative bases from columns
  of the vector flattenings, reduces the tensor to a `2 × ... × 2`
  subtensor, decomposes that core, and lifts the factors by nonnegative matrix
  multiplication.
- Immediately after Theorem 1.2, Section 3 explicitly observes that model
  membership is polynomial-time: the supermodular cone has only polynomially
  many facet inequalities in the displayed tensor size, each involving four
  entries. For a binary `m`-mode tensor the paper counts
  `m(m-1)2^(m-3)` such faces.

Thus an inverse generator would know a decomposition by construction, and a
checker could multiply and compare exact rationals, but the solver can recover
the same witness by routine exact linear algebra.

## The certificate-producing algorithms and their costs

### Direct rank-two decomposition

For a generic three-mode rank-two tensor, the standard matrix-pencil route
uses two `2 × 2` slices of a nondegenerate `2 × 2 × 2` core. A
generalized `2 × 2` eigenproblem recovers the two component directions.
Every remaining coordinate of every factor is then recovered by an independent
`2 × 2` linear solve. This is `Theta(d)` exact arithmetic for a
`d × d × d` tensor once suitable anchor rows and columns are fixed;
the answer itself contains `6d` scalar coordinates.

Under the 256-atom answer cap, `d <= 42`. Even at that boundary the mechanical
route is only a constant-size pencil followed by 120 two-unknown extensions,
and the compact route must still recover and emit 252 factor coordinates. Both
routes are `Theta(d)` and differ only by a small constant. With unstructured
inverse-generated factors there is no shorter invariant to notice. Restricting
the factors to a low-parameter pattern merely makes that pattern itself the
equally short recovery algorithm.

### Toric-cell ordering witness

Lemma 2.1 makes the situation still more explicit. A `2 × 2` face minor
factors into one signed comparison determinant from each of the two varied
modes, times positive factors from the fixed modes. Fixing one nonzero reference
comparison therefore turns the other face minors into a comparison oracle for
the unknown label orders. Ordinary comparison sorting recovers all mode
permutations in `O(sum_i d_i log d_i)` face tests; each face test is exactly two
multiplications and one subtraction.

I measured this route in standard-library Python on 20 deterministic inverse-
generated instances with three unknown modes and one fixed reference mode:

| labels per unknown mode | mean / maximum comparisons | mean / maximum exact arithmetic | mean / maximum wall time |
|---:|---:|---:|---:|
| 8 | 49.15 / 53 | 147.45 / 159 | 0.0397 / 0.0448 ms |
| 12 | 90.8 / 95 | 272.4 / 285 | 0.0718 / 0.0748 ms |
| 42 | 518.15 / 527 | 1554.45 / 1581 | 0.4319 / 0.4501 ms |

All 60 trials recovered the planted orders exactly. At 12 labels, `(12!)^3`
already gives an enormous structure-aware answer space, but the complete
mechanical route costs at most 285 arithmetic operations and is the compact
route too. At 42 labels it exceeds the 300-operation no-tool cap, while the
compact route exceeds it by exactly the same amount. Increasing the size never
opens a Track B gap; it only lengthens the same comparison sort and eventually
violates G9(c).

These are the two numbers the Track B test asks to compare:

- **Mechanical cost at the plausible 12-label shipping size:** at most 285
  exact arithmetic operations, measured at no more than 0.0748 ms.
- **Compact route length:** the same at most 285 operations, because the
  face-minor invariant is the certificate-producing comparison algorithm.

The ratio is 1, not a hand-infeasible computation compressed by an insight.

## Why other results do not rescue a family

| Paper result | Candidate witness | Failing gate |
|---|---|---|
| Theorem 1.2, rank-two algebraic boundary | a rank-one slice or dependent double slice | **H**: the theorem identifies these by ordinary minor/rank checks; the component is not hidden behind a hard search. |
| Theorem 4.1, binary tree boundary | a pendant/internal edge and its rank-drop flattening | **H**: the proof again gives explicit flattening rank loci and matrix factorizations. |
| Example 5.1, `3 × 3 × 2` rank three | a nonnegative rank-three decomposition or boundary component | **H**: the paper says the identifiable decomposition is read from eigenvalues and eigenvectors of two displayed `3 × 3` matrices. |
| Example 5.2, `2 × 2 × 2 × 2` rank three | a boundary certificate | **G/V**: the model is non-identifiable and the paper only suspects candidate components; it does not supply a scalable exact characterization or theorem-backed certificate generator. |

The fixed higher-rank examples also do not provide an unlimited hard parameter
regime. Turning them into a scalable family would require adding mathematics or
a surrogate reduction not licensed by the paper.

## Gate diagnosis

| Requirement | Result |
|---|---|
| G — generatable | **Passes** for inverse-generated rank-two tensors: sample nonnegative factors first and form their two outer products. |
| V — exact witness verification | **Passes**: check nonnegativity and recompute every tensor entry with exact rational arithmetic. |
| H — Track A | **Fails**: Theorem 1.1 and its Section 3 discussion give polynomial-time membership, while the constructive proof and standard matrix-pencil method recover factors in polynomial time. No hard generated distribution or hard parameter regime is stated. |
| H — Track B | **Fails**: the measured mechanical and compact routes are the same face-minor comparison sort (285 versus 285 operations at the plausible shipping size). Direct decomposition is likewise linear in the certificate length. |
| Overall | **Rejected at STEP 0.** |

The rejection is not based merely on the existence of an efficient algorithm.
It is based on the absence of the mechanical/compact separation required for
Track B, after measuring the strongest native alternative exposed by the
paper's determinant identities.
