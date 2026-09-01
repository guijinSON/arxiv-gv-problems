# Rejected: arXiv 2211.12582

Paper: Iliyas Noman and Yuan Yao, [*Spectral conditions for spherical two-distance sets*](https://arxiv.org/abs/2211.12582) (v2, 3 February 2026).

## Decision

This paper does not provide a problem family satisfying **G, H, and V** simultaneously. The suggested family—construct or recognize points on a sphere having exactly two pairwise distances—can be generated and checked, but it fails **H (hardness)** in the parameter regime studied by the paper. The paper's main contribution is a necessary-and-sufficient spectral characterization, and its other main result reads the minimum representation dimension directly from an eigenvalue multiplicity. I therefore stopped at Step 0, before creating a generator, claiming gate measurements, or running the LLM hardening loop.

## What the paper actually studies

Definition 2.1 calls a finite set in `R^d` a two-distance set when the distances between distinct points take exactly two values. Definition 2.2 encodes it by a graph: an edge represents the longer of the two distances. Definition 2.4 calls the set spherical when all points lie on a `(d-1)`-sphere in `R^d` (scaling can make this the unit sphere).

The paper focuses on the "small" regime of a graph with exactly `d+2` vertices represented in `R^d`. It supplies progressively simpler exact characterizations:

- Theorem 2.1 (Einhorn--Schoenberg) says that a graph on `d+2` vertices is not representable precisely in the complete-multipartite exception; otherwise it has a unique admissible distance ratio.
- Lemma 2.2 (Schoenberg) reduces realization of a prescribed distance matrix to positive semidefiniteness and a rank bound, and states that the configuration is unique up to congruence.
- Sections 3--5 rewrite spherical representability as positive-semidefinite, nullspace, and eigenvalue conditions.
- Theorem 1.1, proved in Section 6, says that spherical representability is determined by the second eigenvalue of the adjacency matrix and the spectrum of its projection onto the all-ones vector's orthogonal complement.
- Proposition 1.2, also proved in Section 6, gives the lowest representation dimension directly from the multiplicity of the second adjacency eigenvalue.
- The final corollary makes an especially broad regime immediate: every regular graph on `d+2` vertices that is not complete multipartite has a spherical representation in `R^d`.

These are finite-dimensional linear-algebra computations, not a hard witness-search regime. The paper contains no NP-hardness result, no planted average-case hardness claim, and no parameter range in which finding a representation is asserted to be hard.

## Why the proposed generator fails

### Recognize a spherical two-distance graph

Given the adjacency matrix, Theorem 1.1 is an explicit decision procedure: compute the spectra of `A` and `P A P`, compare the relevant eigenvalue and multiplicities. Exact versions can use characteristic-polynomial and rational/algebraic linear algebra. This is polynomial-time linear algebra, so **H fails**. Asking for the minimum dimension is even more directly defeated by Proposition 1.2.

### Construct a spherical two-distance realization

Sampling a graph first would satisfy inverse generation, and a submitted exact Gram/distance matrix could be checked by substitution, rank, and positive-semidefiniteness. But Theorem 2.1, Lemma 2.2, and Section 4's formula

```text
k = sqrt(1/lambda_2 + 1)
```

give the distance ratio and a standard spectral/Gram-matrix reconstruction route. A solver need not recover a hidden plant. For regular non-complete-multipartite graphs the paper's final corollary even decides existence immediately. Thus **H fails** again.

There is a second contract problem if ordinary coordinates are requested: the natural coordinates and distance ratio can be irrational algebraic numbers. A floating-point answer is not an exact witness, while an exact algebraic-number representation and checker would require machinery beyond the requested standard-library substitution-style interface. Restricting the generator to rational constructions would improve V but would not repair H.

### Recover information from already supplied points

If the points are supplied and the witness is their two distances, the associated graph, or confirmation that the points are spherical, the solver only computes norms and all pairwise distances. That costs polynomial time and is exactly the proposed verifier, so it also supplies the solving algorithm. Returning the two distances would additionally make the answer a real-valued object, which the witness contract forbids.

### Nearby formulations do not rescue the family

- A yes/no existence answer is not a witness, and Theorem 1.1 makes it a spectral lookup anyway.
- An eigenvector, null vector, Gram factor, or multiplicity certificate is found by standard linear algebra; changing the output from a decision to a certificate does not create hardness.
- Asking for an optimal or maximum-cardinality two-distance set would make optimality the claim and violate the witness requirement; the paper also does not give an answer-first generator for such optima.
- Hiding a vertex permutation and asking the solver to recover it would append a graph-isomorphism puzzle not studied or shown hard in this paper. Its difficulty would come from the added encoding, not from the spherical two-distance results, so it would not be an honest use of the paper's regime.
- Moving to arbitrary numbers of vertices abandons the paper's `d+2` characterization regime. The paper proves no computational-hardness theorem or inverse-generation distribution there.

## Gate outcome

| requirement | result |
|---|---|
| G -- sample the answer first | Possible for explicit point/Gram constructions |
| H -- no known polynomial-time or closed-form method | **Fail: Theorem 1.1, Proposition 1.2, and Lemma 2.2 reduce the natural tasks to spectral and PSD/rank computations** |
| V -- cheap exact witness checking | Possible for exact distance/Gram data; problematic for unrestricted irrational coordinates |

No `gen_2211_12582.py`, `selftest_report.json`, `README.md`, or `llm_loop_transcript.jsonl` was created. Running `scripts/harden.py` after this analytical H rejection would contradict the instruction to stop as soon as a family fails G, H, or V.
