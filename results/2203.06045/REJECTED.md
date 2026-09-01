# Rejected: no family simultaneously satisfies G, H, and V

Paper read in full: Alexander Walker, [*Integer Sets of Large Harmonic Sum Which Avoid Long Arithmetic Progressions*](https://arxiv.org/abs/2203.06045), arXiv:2203.06045v2 (Sections 1–6, including the September 2025 revision and its implementation discussion).

## Natural witness considered

The paper's finite object is a digit set `S` contained in `{0, ..., b-1}`. A solver could be asked to return `S` such that it is *k-free modulo b*: there must be no ordinary `k`-term arithmetic progression with nonzero common difference modulo `b` whose residues all lie in `S`. If `0` belongs to `S`, Theorem 1.2 proves that the associated Kempner set of nonnegative integers whose base-`b` digits all lie in `S` is also `k`-free.

Adding a lower bound on the harmonic sum of the shifted Kempner set `K(S,b)+1` is the only paper-specific condition that makes the author's search nontrivial.

## Gate analysis

| Criterion | Result | Reason |
|---|---|---|
| G — inverse-generatable | Only in easy regimes | Proposition 1.1 explicitly constructs modularly `k`-free digit sets from any finite `k`-free set by taking `b > 2 max(S)`. Theorem 1.2 then constructs the infinite `k`-free Kempner set. Sampling one of these easy witnesses first works, but exposes a direct construction to the solver. Sampling a *record-quality* digit set first is the same expensive search the generator is supposed to avoid. |
| H — hard witness search | **Fail** | The paper proves no computational-hardness result for finding a valid digit set. Section 3 says the longest progressions and harmonic sums of a fixed Kempner set are efficiently computable. Its thousands of core-hours are spent on branch-and-bound optimization over all digit subsets to improve a numerical record. The prompt forbids making optimality the witness claim. Without a demanding score threshold, explicit constructions solve the task; with a record-level threshold, the paper gives a handful of fixed answers rather than an unlimited answer-first generator. Affine relabellings of those answers are the same problem for canonicalization purposes. |
| V — cheap exact checking | Partial only | The modular `k`-free predicate is finite and can be checked exactly by enumerating modular progressions. The record condition is an inequality involving the harmonic sum of an infinite Kempner set. Section 3 uses an approximate score (Equation 3.1) for pruning and the Baillie–Schmelzer machinery for high-precision post-processing; the displayed record values are decimal approximations. That is not the required cheap exact “substitute, expand, recompute, compare” checker for arbitrary candidate outputs. A finite truncation would be exactly checkable, but would be a different and still explicitly constructible problem. |

## Easy regimes that prevent shipping

- Proposition 1.1: any finite `k`-free `S` becomes `k`-free modulo every `b > 2 max(S)`.
- Theorem 1.2: a modularly `k`-free digit set containing zero immediately yields an infinite `k`-free Kempner set.
- Theorem 2.1: shifted Kempner sets approximate the harmonic sum of any convergent `k`-free set, again through an explicit construction rather than a hard inversion problem.
- Section 4 and Remark 4.1 identify the greedy prime-`k` Kempner sets as dominant explicit constructions in the tested range.
- Remark 6.1 gives another efficient special-case test for a structured 10-free construction.

## Why no module or hardening transcript was produced

Any shipped module would have to choose between two invalid claims:

1. plant an explicitly generated progression-free digit set and call the resulting direct-construction task hard; or
2. ask for a record/highest-score set, making optimization (or an unverified infinite-series threshold) the substance of the answer.

Neither meets the requested witness contract. Consequently Step 0 requires stopping here. `gen_2203_06045.py`, `selftest_report.json`, and `llm_loop_transcript.jsonl` were intentionally not fabricated, and the LLM hardening loop was not run.
