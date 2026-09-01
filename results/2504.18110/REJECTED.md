# Rejected: arXiv:2504.18110

Paper: Hong-Jun Ge, Jack Koolen, and Akihiro Munemasa, [*A 2-distance set with 277 points in the Euclidean space of dimension 23*](https://arxiv.org/html/2504.18110v4) (v4).

## Decision

This paper does not supply a problem family satisfying **G (generatable), H (hard), and V (cheaply verifiable)**. No `gen_2504_18110.py` was produced, and the self-test and LLM hardening loop were intentionally not run. The task explicitly requires stopping when any of G/H/V fails.

## What the paper actually proves

[Section 2](https://arxiv.org/html/2504.18110v4#S2) defines one fixed construction. It takes

- `X = F_3 x {1,...,11}` (33 vertices),
- `Y = C^perp` for the ternary Golay code (243 vertices), and
- an explicitly defined graph on `X union Y`.

The matrix `A(Gamma) + 3I` is positive semidefinite of rank 24 and is used as a Gram matrix for 276 vectors. The switching root is given explicitly by

```text
r = x1 + x2 + x3 - (4/33) sum_{x in X} x + (1/81) sum_{y in Y} y,
```

and the extra point is then given explicitly by

```text
u = x1 + x2 + x3 - r.
```

Theorem 1 proves that the resulting 277 points lie in an affine copy of `R^23` and have squared pairwise distances exactly 4 and 6. Lemma 2 further proves that `u` is independent of which of the 11 three-point parts is used.

[Section 3](https://arxiv.org/html/2504.18110v4#S3) proves maximality. In the 23-dimensional affine hyperplane there is no extension. In `R^24`, Proposition 3 says that the only additional points are the two explicitly displayed multiples

```text
((1 + sqrt(3))/2) r  and  ((1 - sqrt(3))/2) r.
```

The appendix supplies Magma code implementing the construction and the exhaustive maximality check. It reports 16,689,170 short nonzero dual-lattice vectors and a run time of 788.6 seconds with 4.58 GB of memory.

## Why candidate problem formulations fail

| Candidate witness task | G | H | V | Disqualifier |
|---|---:|---:|---:|---|
| Construct the 277-point two-distance set | only at one fixed size | **fail** | pass with an exact Gram representation | Section 2 is a direct, explicit construction; there is no growing parameter regime. |
| Add the 277th point to the 276-point set | pass | **fail** | pass | Theorem 1 gives `u` by a short linear formula, and Lemma 2 gives 11 immediately recognizable ways to compute the same point. |
| Extend `Z` inside its `R^23` affine hull | **fail** | not applicable | fail for the required witness model | Proposition 3 says no extension exists; an absence is expressly forbidden as an answer. |
| Extend `Z` in `R^24` | pass | **fail** | pass | Proposition 3 completely classifies the answer as two explicit multiples of `r`; this is a lookup/closed-form task. |
| Decide whether 325 points exist in `R^24` | **fail** | unknown | fail for the required witness model | The paper calls this an open existence question and supplies no witness from which an instance can be inversely generated. |
| Recover coordinates from the supplied Gram matrix | pass | **fail** | pass | Positive-semidefinite Gram factorization is direct linear algebra, and the appendix performs it explicitly. |

The paper contains no complexity-hardness theorem, NP-hard parameter regime, FPT boundary, or scalable parameterized construction. Its only nontrivial regime is the fixed pair `(dimension, size) = (23, 277)`. Permuting vertices, changing coordinates by an isometry, or changing the seed would merely relabel the same problem and therefore must collapse under `canonical_key`; those operations cannot provide an unlimited supply of structurally distinct instances.

The standard general-dimensional construction mentioned in the introduction (midpoints of the edges of a regular simplex) also cannot rescue the family: it is itself a closed-form construction and therefore fails H.

## Gate status

| Gate | Status | Reason |
|---|---|---|
| G1--G8 | not run | No admissible family exists to implement or test. |
| LLM hardening loop | not run | `scripts/harden.py` requires a qualifying generator; running it on a knowingly closed-form or fixed-instance task would not establish H. |

The decisive failure is **H**, with additional **G/scaling** failures for the fixed construction and the open problem. Although pairwise distances or an integer Gram matrix could be checked cheaply and exactly, V alone is insufficient.
