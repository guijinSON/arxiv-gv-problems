# Rejected: arXiv 2101.03643

**Disposition:** the candidate family fails **H on Track B**.  G and V pass.
This is not a Track-A claim: the paper itself gives an algorithm for producing
the certificate.

## Step-0 paper audit

The full v3 paper was read, not only the abstract.  Definition 3.2 is the exact
definition of a differential primary decomposition: the differential conditions
must recover each localization along an associated prime.  Theorem 3.6 proves
existence and says that the minimum number of operators is the arithmetic
multiplicity.  Section 5 specializes this to polynomial rings over a
characteristic-zero field; Theorem 5.3 gives the minimal representation in the
Weyl algebra.

The easy regime is explicit in the Introduction: when the associated primes are
rational maximal ideals, finding the operators is the standard inverse-system
case.  Algorithm 5.4 is the general mechanical route.  Its steps (2.5)-(2.7)
compute the Weyl-Noether spaces E and H, find a complementary vector space G,
take a basis, and lift it to differential operators.  The authors implemented
that algorithm in Macaulay2.  Therefore declaring Track A would be false.

Paper: [Primary Decomposition with Differential Operators](https://arxiv.org/abs/2101.03643).

## Family that was tested

The retained module inverse-generates an m-primary ideal

`I = <q_1,...,q_(M-1)> + m^3` in `Q[x_1,...,x_n]`,

where the independent quadrics span a hyperplane in the M-dimensional space of
quadrics, `M=n(n+1)/2`.  It samples the normal vector first.  That vector is the
coefficient matrix of the unique normalized second-order Noetherian operator;
only afterward does generation build the annihilated quadratic hyperplane.
Thus G uses inverse generation and never solves its own instance.

Verification is exact integer coefficient pairing.  If `X` is the submitted
symmetric matrix, the checker evaluates `D_X(q_k)(0)` as a dot product for every
quadratic generator.  Together with `1` and the first derivatives, the accepted
operator characterizes the ideal because all degree-three terms lie in `m^3`.
The checker never reads the planted answer.  The local selftest passed G1-G9(c),
including 0 hits in 200,000 structure-aware guesses, five attacks at 0/8, 80/80
canonical-key invariance checks, and 20/20 unrelated keys distinct.

## Why Track B fails

The dense quadratic coefficient matrix was made as
`(I + u v^T) [I | -z]`.  This was intended to create a large generic nullspace
calculation while leaving a short rank-one route.  It instead prints the entire
shortcut in a form the oracle pool recognizes reliably: subtracting the identity
from the leading block exposes rank one, and one Sherman-Morrison scalar recovers
the operator.

At the largest admissible attempted setting, `n=9`, `M=45`, coefficient bound
255:

| route | measured cost |
|---|---:|
| Exact rational Gaussian elimination (Algorithm 5.4's linear-algebra core) | average 89,927 exact arithmetic operations and 0.0249 s over 8 seeds |
| Compact rank-one route | 264 exact arithmetic operations |
| Answer | at most 317 serialized characters, 81 atomic entries |

The numerical gap is real, so this was a plausible Track-B candidate.  The
conceptual gap is not: the invariant is directly visible in the displayed block,
and the evaluated models repeatedly found and executed it.  Increasing to
`n=10` would raise the compact route to 324 operations, violating G9(c)'s
300-operation cap; it is not an answer-size `cap_bound`, so `escalate()` correctly
returns `None`.

The script-owned bare hardening run recorded:

| rung | solved / attempts |
|---|---:|
| easy (`n=6`) | 2 / 3 |
| medium (`n=7`) | 3 / 3 |
| hard (`n=8`) | 3 / 3 |
| escalated (`n=9`) | 1 / 3 |

Because any verified solve defeats a rung, every rung was defeated.  The final
script verdict is `too_easy` after three escalations.  No hinted/placebo arms
were run after that terminal failure.

The implementation is retained as `rejected_gen_2101_03643.py`, together with
the unedited `llm_loop_transcript.jsonl` and `.meta.json`, so this decision can be
replayed or revisited.
