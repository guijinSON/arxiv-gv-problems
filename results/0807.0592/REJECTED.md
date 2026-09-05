# Rejected: arXiv 0807.0592

This paper was read in full and a native finite-field generator was built, but the family is rejected by **G9(b) on Track B**.  The retained implementation is `rejected_gen_0807_0592.py`; it is not a shipping module.

## Decision

| item | result |
|---|---|
| G — generation | Pass. Multiplicities are sampled first and the exact count is composed as `k! * [z^k] product(1+m_i z)` before the vectors are assembled. |
| V — verification | Pass. The checker projectively normalizes every vector, checks all finite-field Gram relations exactly, and recomputes the coefficient without reading `inst["answer"]`. |
| H — Track A | Not claimed and unsupported. Theorem 1.1 is an asymptotic dense-set counting theorem, not a distributional search lower bound. |
| H — Track B | The mechanical/compressed gap exists, but the mandatory hinted-oracle gate fails, so the family is unsuitable for this no-tool benchmark. |
| failing mandatory gate | **G9(b): `hinted_still_hardened` is false.** |

Section 2 of [Iosevich–Senger, *Orthogonal systems in vector spaces over finite fields*](https://arxiv.org/abs/0807.0592) defines `D_k` and `lambda_k=|D_k|` as ordered mutually orthogonal tuples.  Theorem 1.1 assumes `binom(k,2)<d` and gives the asymptotic count for sufficiently dense `E`.  It supplies neither Track-A distributional hardness nor a certificate-finding lower bound.  Section 3 gives sharpness constructions, including large sets without orthogonal pairs; those do not change the search analysis for this positive count family.

## Mechanical cost versus compact route

The Track-B reference algorithm is projective normalization, an exact Gram check, and elementary-symmetric coefficient DP.  Its complexity is `O(|E|d + d^3 + dk)`.  At the final candidate preset `d=128`, `k=10`, `p=257`, multiplicities `1..5`, the final selftest measured an average of **2,165,594 field operations**, **1,319.125 Euclidean divisions**, and **0.0577 seconds** over eight seeds.

The compact route uses the scalar-layer histogram and Newton identities.  It needs **285 exact arithmetic operations** and emits a two-atom rational (30 serialized characters at the measured seed).  This is a real mechanical/compression gap; the rejection is not the invalid argument that “an efficient algorithm exists.”  It is rejected because a model executes the compact route once the invariant alone is named.

## Oracle evidence

The first bare candidate, `d=64,k=10`, hardened against all three bare vendors, but a structural-hint run produced a verified solution.  The one G9-permitted increase was therefore used.

At the final `d=128,k=10` preset, the authoritative bare run hardened 0/3 solved:

| model | seed | result | verifier reason |
|---|---:|---|---|
| x-ai/grok-4.6 | 821529393 | failed | incorrect exact orthogonal-system count |
| google/gemini-3.1-pro-preview | 1886838602 | failed | count is not divisible by `k!` |
| anthropic/claude-sonnet-5 | 239455941 | failed | incorrect exact orthogonal-system count |

The structural hint was exactly one invariant-only sentence:

> The canonical coordinate magnitudes are scalar layers on mutually orthogonal projective directions.

It contains no chained step, derived count, or algorithm.  With that hint, `openai/gpt-5.6-terra` solved seed **1597021224** in **67.4 seconds**, returning the exact verified answer `28487675698552991792793600/1`.  One verified solve is enough to fail G9(b), and this was already the one permitted higher rung.  Subsequent calls hit the OpenRouter account's total key limit; those rows are retained as errors and are not counted as model failures.  A placebo arm was not run after the decisive mandatory-gate failure, following the instruction to stop rather than spend more oracle budget.

## Retained evidence

- `llm_loop_transcript.jsonl`: authoritative final bare run, written by `scripts/harden.py`.
- `g9_hinted_transcript.jsonl`: final hinted run, including the verified solve and later service errors.
- `selftest_report.json`: G1–G8 pass; G9 records the verified hinted solve and fails honestly.
- `.meta.json`: bare run metadata and hardened shipping parameters.

The answer and operation caps were not the blocker, and this is not `cap_bound`.  No further manual escalation is permitted after the one G9 move, so the correct outcome is rejection rather than retuning.
