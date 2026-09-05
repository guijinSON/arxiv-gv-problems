# Rejection: arXiv:2511.22914

## Decision

The implemented modular-order path family is rejected because **H fails on both tracks**. G and V pass: generation samples the path before adding constraints, and the checker exactly replays any submitted path without consulting the planted answer. The failure is not the witness rule.

The source is Kei Kimura, “Towards an algebraic approach to the reconfiguration CSP,” arXiv:2511.22914v3. Definitions 2.8–2.9 define the solution graph and RCSP. Section 3.2, Lemma 3.7 and Theorem 3.8 are decisive: for a constraint language preserved by an ordered partial Maltsev operation, each component has a unique local minimum and RCSP is solvable in `O(n^2 m |D|^2)` time. Section 3.3, Lemma 3.13 puts min-closed relations in that class. The generated Boolean relation `LEQ = {(0,0),(0,1),(1,1)}` is min-closed.

## Certificate-cost test

Track A is unavailable. Besides Theorem 3.8’s polynomial greedy descent, this `LEQ` specialization reduces directly to precedence extraction followed by Kahn topological elimination in `O(n+m)` time.

At the shipping preset (`p=131`, 12 changing variables, 3,822 implications), the reference implementation used **4,051 counted operations** and an 11-run median of roughly **0.0001–0.0002 seconds**. The intended compact route inspects the endpoint-difference indices, recognizes their modular arithmetic progression, and orients it by the smaller positive residue; the audited implementation used at most **166 counted operations** over 64 seeds. The nominal compression is only about 24×, and—more importantly—the invariant is exposed directly by the endpoint-difference list. There is no difficult discovery step left.

Thus Track B also fails empirically. The script-owned bare hardening run produced valid solutions on:

| Level | Parameters | Solved / valid attempts |
|---|---|---:|
| easy | `n=37, k=10, decoys=18%` | 3/3 |
| medium | `n=73, k=12, decoys=24%` | 3/3 |
| hard | `n=131, k=12, decoys=32%` | 3/3 |
| escalation 1 | `n=263, k=12, decoys=35%` | 3/3 |
| escalation 2 | `n=541, k=12, decoys=38%` | 2/3 |

Overall, the two-vendor pool solved **14/15 valid attempts**. At the next level (`n=1087`) all four calls were provider/context errors; errors are redraws and provide no hardness evidence. Enlarging the implication haystack cannot repair the family because the 12-variable progression remains visible before any inequality is read. The run is preserved in `llm_loop_transcript.jsonl`.

## What was and was not rejected

This rejects the implemented family, not the paper’s mathematics. The Boolean dichotomy summarized in Section 2.3 also contains PSPACE-complete, non-safely-tight languages, but the paper does not provide a scalable certificate-carrying distribution for those cases, and this run did not establish one. Retuning the same visible progression after seeing the oracle results would violate the prescribed hardening protocol.

The locally passing implementation is retained as `rejected_gen_2511_22914.py`, as required. `selftest_report.json` records its G1–G9(c) measurements; those correctness checks do not override the failed hardness test.
