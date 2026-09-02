# Rejected at Step 0: no qualifying hard witness family

Paper: Vedrana Mikulić Crnković and Ivona Traunkar, [*Self-orthogonal codes constructed from weakly self-orthogonal designs invariant under an action of M11*](https://arxiv.org/abs/1910.13133), arXiv:1910.13133v5.

## Verdict

This paper does not support a problem family satisfying **G + H + V**. The natural family suggested by the paper—construct a self-orthogonal code from a weakly self-orthogonal design—is generatable and exactly verifiable, but it fails **H (hardness)**: the paper's main results give the witness by an explicit, direct matrix formula.

No generator module, self-test report, or oracle transcript was created. Running the hardening loop on a family already known to have a polynomial-time construction would manufacture misleading evidence rather than test a defensible hardness claim.

## What the paper actually defines

Section 1 defines a weakly self-orthogonal design as a design whose pairwise block-intersection numbers all have the same parity. It is self-orthogonal when those intersections and the block size are even. Its incidence matrix has one binary row per block, and the associated code is the row span over the chosen finite field.

Sections 2 and 3 then construct self-orthogonal codes from incidence matrices and orbit matrices. These are sufficient conditions accompanied by explicit formulas, not search problems.

## Why the proposed witness is easy

For a binary incidence matrix `M` with `b` rows, Theorem 1 gives the output immediately in all four parity cases:

| Design case | Explicit generator matrix |
|---|---|
| even block size, even intersections | `M` |
| even block size, odd intersections | `[I_b | M | 1]` |
| odd block size, even intersections | `[I_b | M]` |
| odd block size, odd intersections | `[M | 1]` |

Theorem 2 gives the analogous formulas over arbitrary finite fields. Theorems 6–21 do the same for orbit matrices and their fixed-point/fixed-block submatrices, with the applicable formula selected by simple divisibility and congruence tests. Constructing these matrices and checking their Gram matrix are polynomial-time operations in the displayed matrix size. Increasing `n` only enlarges the same deterministic concatenation; it does not create a hard search task.

Thus the prior-triage proposal fails **H** even though it satisfies **G** and **V**. A solver does not have to guess or search for the planted witness: it can reproduce the theorem's construction directly from the public instance.

## Why the results section does not rescue the family

Section 4, Theorem 22 constructs a 1-design by taking the orbit of a selected union of point-stabilizer orbits under a finite transitive permutation group. The authors use the fixed finite group `M11` to list 178 pairwise non-isomorphic weakly self-orthogonal designs on 22, 55, 66, 110, 132, 144, and 165 points, then tabulate the resulting codes. This is a finite catalog, not an unlimited scalable hard regime.

The paper mentions that some minimum distances and automorphism groups were not computed because of computational limitations, but it states no complexity or hardness theorem for those tasks and supplies no inverse generator for a hard distribution. Turning minimum distance into the requested answer would either ask for an optimum (forbidden by the task) or require inventing a separate planted low-weight-codeword problem whose hardness is not established by this paper. Likewise, asking for an automorphism admits the identity unless extra conditions are added, while certifying the full automorphism group is not a bounded witness with cheap completeness verification.

## Gate status

| Criterion | Status | Reason |
|---|---|---|
| G — generatable | Would pass | Theorems 1–21 explicitly construct a code generator matrix. |
| H — hard | **Fails** | The same theorems are a closed-form polynomial-time solution. No hard parameter regime is stated. |
| V — verifiable | Would pass | Pairwise row inner products can be recomputed exactly. |
| Unlimited scaling | **Fails for the paper's M11 catalog** | Section 4 reports only 178 designs at seven fixed point counts. |

Because **H** is mandatory, implementation stopped before Steps 1–4, as required by the task's Step-0 rejection rule.
