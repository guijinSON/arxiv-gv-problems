# Rejected: the coordinate-swap family fails Track B hardness

This candidate family for [*Matrices of nonnegative integer rank two*](https://arxiv.org/abs/2602.05957) is rejected.  It passes generation and exact verification, but fails **H on Track B**: no-tool models reliably discover and execute its compact symmetry route.  It is not a Track A family; the paper gives a general algorithm, and it proves no distributional hardness result for these planted instances.

## STEP 0 result

Problem 2.2 in Section 2.1 is the exact native formulation used here: given a pointed rational cone in a rank-two integer lattice and finitely many lattice points in it, find two lattice points whose nonnegative integer span contains every displayed point.  Proposition 2.8 carries this cone object back to nonnegative-integer rank two.  The candidate was inverse-generated from a unimodular pair of lattice generators, so its certificate was known without solving the instance.  Verification uses only integer determinants, gcds, divisibility, and sign comparisons.

The paper also identifies the easy mechanism.  Section 3 and Algorithm 1 enumerate possible splits of the minimum-slope point in the bounded triangle
`Delta = K_- intersect (u - K_+)`, primitive-normalize both rays, and test exact coordinates.  The paper states that this costs polynomial time in `||u||`, hence pseudo-polynomial time in the coordinate bitlength, and Section 3.2 reports very fast behavior on ordinary random inputs (0.00812 seconds on average in its second experiment).  Theorem 2.10's polynomial-time reduction to a 3-by-3 representative is another reason no Track A claim is justified.

The mechanical and compact costs are not comparable, so the mere existence of Algorithm 1 is **not** the rejection reason:

| Route at the named `hard` preset | Measured cost |
|---|---:|
| Algorithm 1 bounded-triangle scan, eight seeds | 7,079,480 candidate splits and 142,152,081 counted exact operations on average |
| Same reference scan, wall clock | 4.01 s mean, 7.97 s maximum |
| Compact coordinate-swap route | 135 counted exact operations |

That gap initially made Track B plausible.  Each generated pair has the form `alpha*a + beta*b` and `beta*a + alpha*b`, with a pair-specific center so that raw coordinate extrema are not mates.  Nevertheless, the unique oriented-slope extremes are a swapped pair.  Primitive-normalizing their sum and difference gives `a+b` and `b-a`, hence the two generators.  The planted split then follows by one exact determinant coordinate.  The oracle models found this route repeatedly.

## Hardening evidence

The script-owned transcript contains the following valid calls.  A rung is defeated when any call solves it; therefore every completed rung below is too easy.

| Rung | Parameters | Verified solves |
|---|---|---:|
| easy | `n=60, pairs=5, fib_index=7` | 2/3 |
| medium | `n=300, pairs=7, fib_index=8` | 3/3 |
| hard | `n=1000, pairs=8, fib_index=9` | 3/3 |
| escalation 1 | `n=2000, pairs=8, fib_index=10` | 2/3 |
| escalation 2 | `n=4000, pairs=8, fib_index=11` | 3/3 |
| escalation 3 | `n=8000, pairs=8, fib_index=12` | 3/3 |
| escalation 4, partial | `n=16000, pairs=8, fib_index=12` | 1/1 valid call |

Overall, 17 of 19 valid calls returned witnesses accepted by `verify`.  The configured OpenRouter allowance was exhausted during the final rung, after its first verified solve; four retries then returned HTTP 403.  Those errors are preserved in `llm_loop_transcript.jsonl` and are not counted as model failures.  The environment's `ORACLE_POOL` override exposed two models rather than the documented four-vendor default, so the interrupted run cannot certify a hardened family.  That limitation does not rescue this candidate: a missing vendor cannot reverse a verified solve, and the family was already defeated through the three post-`hard` escalations specified by the task.

## Local gates and disposition

The last full selftest passed G1--G9(c): 0/200,000 structure-aware random candidates verified; six cheap attacks each scored 0/8; Algorithm 1 solved 8/8 as expected; 420 composed point-permutation and `GL(2,Z)` invariance checks passed; the answer had six atomic elements and the intended route used 135 operations.  These results establish G and V, but cardinality and failed cheap heuristics do not establish H in the face of actual verified oracle solutions.

The implementation is retained as `rejected_gen_2602_05957.py`, as required.  The rejection applies to this planted coordinate-swap distribution.  It does not prove that no other benchmark family can be extracted from the paper; it records that this family exhausted the prescribed hardening escalations and must not ship.
