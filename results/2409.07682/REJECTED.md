# Rejection: sparse Walsh spectracone certificates

This paper was tested on **Track B (no-tool compression)**.  The proposed family
passes G and V, but fails H on Track B.  It also cannot make a Track A claim.

## Decision

- **G passes.**  The generator samples seven distinct Walsh rows and seven positive
  integer coefficients first, then expands their conical combination.  Theorem 4.29
  guarantees that the Walsh spectracone equals its row cone, so the planted sparse
  row-cone decomposition is a certificate by construction.
- **V passes.**  The verifier checks the bounded rational syntax and expands the
  claimed rows at every spectral coordinate using exact integer parity and equality.
  It does not read the planted answer.
- **H fails on Track B.**  The script-owned hardening loop's recorded pool contained
  two available models; they solved `easy` 3/3, `medium` 1/3, and the final admissible
  `hard` preset 2/3.  Thus no rung held.  The last rung has `n=4096`, seven answer
  terms, two relabelling rounds, and 48-bit weights.  A further doubling makes the
  intended route exceed G9(c)'s 300-operation cap, so `escalate()` returned `None`.

The relevant paper results are Definition 4.17 (row cone), Definition 4.18
(ideal Perron similarity), Theorem 4.29 (Walsh matrices are ideal), equation (4.7)
(the realizing Klein matrices), and Theorem 4.10 (row/column permutation
equivalences).  The explicit Fourier feasibility result in Theorem 7.4 is the
paper's clearest warning that an analogous Track A claim would be false.

## Required algorithm-cost comparison

This rejection is **not** based merely on the existence of an efficient algorithm.
The reference algorithm is exact affine reindexing followed by the fast
Walsh--Hadamard transform.  At the final `hard` preset it costs 73,735 counted exact
operations and has complexity `O(n(log n + rounds))`.  The compact route undoes the
two affine relabellings, reads the twelve binary unit characters, and decodes the seven
row labels from the supplied signed-sum table; its conservative bound is 294 exact
operations.

That operation gap was large enough to justify testing the family as Track B, but it
did not survive the required empirical test: the oracle replies visibly executed the
compact route and returned verified witnesses.  Because the next fixed-answer-length
rung would cross the no-tool effort cap, there is no compliant escalation left.

## Evidence retained

- `rejected_gen_2409_07682.py`: complete generator and all local gates.
- `selftest_report.json`: local gate measurements for the original provisional
  `easy` shipping preset.
- `llm_loop_transcript.jsonl` and `.meta.json`: the unedited script-owned hardening
  run whose verdict is `too_easy`.
- `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl`: earlier attempted
  diagnostics; every call was an HTTP 403 and none counts as a solver attempt.

No module is being shipped from this directory.
