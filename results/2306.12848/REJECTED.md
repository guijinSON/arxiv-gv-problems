# Rejected at Step 0: no qualifying hard witness-search family

Paper: Kishan Chand Gupta, Sumit Kumar Pandey, and Susanta Samanta,
[*On the Direct Construction of MDS and Near-MDS Matrices*](https://arxiv.org/abs/2306.12848),
arXiv:2306.12848v4 (9 April 2026).

## Decision

This paper does not support a problem family satisfying **G**, **H**, and **V**
simultaneously. In particular, **H fails** for the paper's matrix-construction
problems. No generator module, self-test report, or oracle-hardening transcript was
created: the task explicitly requires stopping after this Step 0 conclusion.

## What the paper actually defines

Section 2, Definition 5 says that an order-`n` matrix `A` is MDS (respectively
NMDS) exactly when `[I | A]` generates a `[2n,n]` MDS (respectively NMDS) code.
For NMDS codes, Lemma 4 turns the definition into three column-rank conditions:
every `n-1` columns are independent, some `n` columns are dependent, and every
`n+1` columns have full rank. MDS is the stronger condition that every `n`
columns are independent.

Section 3 treats recursive matrices `C_g^m`. Theorems 8 and 9 translate the MDS
and NMDS properties into column independence/rank conditions on an explicit
generalized Vandermonde generator matrix. The section then constructs suitable
polynomials and companion matrices directly:

- Theorem 10 constructs recursive NMDS matrices from a prescribed root pattern
  and an explicit zero-sum condition.
- Lemma 10 gives a scaling closure that immediately creates further examples.
- Theorem 11 directly constructs recursive MDS matrices from another prescribed
  root pattern and explicit nonvanishing conditions.
- The paragraph before Theorem 8 gives an easy/impossible regime: for `n >= 3`
  and `m < n`, `C_g^m` cannot be MDS or NMDS because its first row is a unit
  vector.

Section 4 gives direct nonrecursive constructions. Theorems 12, 13, 15, 16, and
17 form two generalized Vandermonde matrices and output `V1^-1 V2` (or its
inverse), with explicit distinctness and subset-sum conditions guaranteeing MDS
or NMDS. Theorem 14 and Corollaries 7 and 8 impose `y_i = l + x_i` to obtain
involutory constructions. Thus the paper's main contribution is precisely a
closed algebraic route around matrix search.

The full text contains no NP-hardness result, parameterized-hardness result,
search lower bound, or hard parameter regime. It contains no FPT algorithm
either; its relevant easy cases are stronger than that—explicit constructions.

## Why the plausible formulations fail

| Proposed solver task | G | H | V | Reason for rejection |
|---|---:|---:|---:|---|
| Output an MDS/NMDS matrix for supplied field parameters | yes | **no** | problematic | Sections 3–4 give direct formulas. Checking the bare matrix definition also requires universal rank/minor conditions over exponentially many column subsets. |
| Output generalized-Vandermonde/companion construction parameters | yes | **no** | yes for sufficient conditions | Theorems 10–17 prescribe the parameter patterns and algebraic tests; reproducing them is not hard witness search. |
| Find a dependent `n`-column set in a promised NMDS generator matrix | potentially | unsubstantiated | yes | A dependency is cheaply checked, but the paper proves no hardness for finding one in its highly structured constructed codes. Claiming general minimum-codeword hardness would not establish hardness for this restricted family. |
| Find the zero-sum `n`-subset occurring in Theorems 10 or 13 | potentially | unsubstantiated | yes | Planting could manufacture such an instance, but this would turn an explicit sufficient condition into a separate subset-sum puzzle. The paper gives no hardness result for its structured instances, so it cannot support H honestly. |
| Find a lowest-hardware-cost MDS/NMDS matrix | possibly | possibly | **no** | The introduction says low-cost examples are often found by search, but the answer would be an optimum. The task forbids optimality claims, and optimality is not cheaply verified by a witness. |

## Gate outcome

| Requirement | Outcome |
|---|---|
| G — inverse-generatable with a known witness | Available for direct constructions or a planted dependency |
| H — no known polynomial/closed-form method in the supported regime | **FAIL** for construction; unsupported for the derived dependency/subset tasks |
| V — cheap exact verification of any witness | Possible for a supplied dependency, but not enough to repair H; verifying the full MDS/NMDS property from a bare matrix is combinatorial |

Because no candidate clears all three requirements, running `selftest()` or
`scripts/harden.py` would test an inadmissible family and would not cure the
missing hardness foundation.
