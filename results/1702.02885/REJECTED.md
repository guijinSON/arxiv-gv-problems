# Rejected: no verified hard generator for arXiv:1702.02885

Paper: Ali Çivril, [*Sparse Approximation is Provably Hard under Coherent
Dictionaries*](https://arxiv.org/abs/1702.02885).

## Decision

This paper does **not** yield an acceptable generator under the required gates.
The attempted native rational sparse-approximation family passed the local
correctness, guessing, attack, scaling, and canonicalization checks, but failed
the mandatory multi-vendor hardening loop.  The harness verdict was
`too_easy`, so no family is shipped and the G9 hinted/placebo arms were not run.

## STEP 0 findings

Section 1 and equation (1) define the native problem: for a normalized
dictionary whose columns span the ambient real vector space, find at most `k`
nonzero coefficients minimizing the Euclidean residual.  The finite witness for
an exact YES instance is a sparse coefficient vector; exact substitution is a
cheap checker.

The hardness theorems do not justify the prior-triage proposal “sample sparse
coefficients and compute the target” as Track A:

- Theorem 1.7 is worst-case inapproximability for dictionaries produced by the
  multilayered Smooth Label Cover reduction, at any fixed positive coherence.
- Theorem 1.8 uses multilayered Unique Label Cover and the assumption that
  Unique Games is not in P to reach coherence `k^(-1+epsilon)` for constant
  factor approximation.
- Neither theorem is an average-case result for independently planted sparse
  vectors.  The construction in Sections 2--4 is highly special and starts from
  hard Label Cover instances; sampling a satisfying labeling first does not
  inherit its soundness distribution.
- Theorems 1.2--1.6 explicitly list polynomial OMP/OLS guarantees in several
  low-coherence regimes.  Those results are another reason random incoherent
  planting cannot be called Track A merely from the paper's title.

The discriminating certificate question therefore has a clear answer.  In the
attempted square-dictionary construction, exact Gauss-Jordan elimination
produces the unique certificate in `O(n^3)`.  The tensor structure gives an even
shorter exact inverse.  The only honest option was Track B.

## Attempted Track B family

`gen_1702_02885.py` is retained as an audit artifact, not as a shipping module.
It plants a bounded sparse rational vector first and multiplies it by a shuffled
tensor product of rational unit-column matrices.  At the largest admissible
dimension `n=27`, the dictionary coherence is exactly `8/9`, the answer has nine
nonzero rational terms, dense Gauss-Jordan elimination took about 18--20 thousand
instrumented exact arithmetic operations, and the tensor inverse took 189.

Local evidence before the oracle run:

| gate | result |
|---|---|
| G1 | 20/20 plants verified; the independently implemented tensor inverse also recovered 20/20 |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 2/2 model-style answers round-tripped |
| G4 | 0/200,000 structure-aware guesses; language size `16,747,540,997,771,810,944,924,195,907,174,400` |
| G5 | demo has exactly one valid answer; shipping density estimate 0/200,000; OMP used 34,327 operations on the measured seed |
| G6 | correlation 0/8, exact-refit OMP 0/8, 256 random restarts 0/8, one-axis shortcut 0/8; disclosed Gauss-Jordan reference solved 8/8 |
| G7 | doubled `n=54` instance built and verified |
| G8 | 60/60 reorder invariance checks, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 120 answer characters, 27 atomic integers, 189 intended-route operations |

These local gates were not enough.  The domain-standard exact solver was already
known to succeed by design, and the oracle pool found the compact route.

## Mandatory hardening evidence

The transcript was produced by `scripts/harden.py` with medium reasoning effort
and is preserved in `llm_loop_transcript.jsonl`; `.meta.json` records the master
seed and `too_easy` verdict.

| rung | model | seed | outcome |
|---|---|---:|---|
| easy | Gemini 3.1 Pro Preview | 1207446792 | solved, exact witness verified |
| easy | GPT-5.6 Terra | 140602158 | solved, exact witness verified |
| easy | Claude Sonnet 5 | 1702013689 | solved, exact witness verified |
| medium | Grok 4.6 | 1584772402 | solved, exact witness verified |
| medium | GPT-5.6 Terra | 990476638 | solved, exact witness verified |
| medium | Gemini 3.1 Pro Preview | 1402320197 | solved, exact witness verified |
| hard | GPT-5.6 Terra | 310643332 | failed exact row 0 |
| hard | Grok 4.6 | 1503058253 | solved, exact witness verified |
| hard | Claude Sonnet 5 | 2122791056 | solved, exact witness verified |

The next supported size is `n=54`.  Its mixed-radix inverse needs approximately
594 exact arithmetic operations, already above G9(c)'s limit of 300, and would
turn the benchmark into an arithmetic/transcription test.  Accordingly
`escalate()` returns `None`; increasing coefficient bounds further after the
official capped verdict would be prohibited hand-tuning.

## Conclusion

Inverse planting clears G and V but has no Track A distributional hardness
basis in this paper.  The honest Track B realization is solvable by the oracle
pool even at its largest no-tool-suitable rung.  Therefore the family fails
STEP 4 (and cannot reach G9(b)), and arXiv:1702.02885 is rejected for this task.
