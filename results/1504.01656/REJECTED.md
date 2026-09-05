# Rejected: the available short-certificate family fails H on Track B

The attempted family clears G and V but fails H on `TRACK = "B"`.  It is
retained as `rejected_gen_1504_01656.py`, together with its gate report and the
script-owned oracle transcript.

## Paper triage

Lauria and Nordström define SOS refutations in Definition 2.2 and state just
before Section 1.1 that a degree-`d` certificate can be found by coefficient
matching plus semidefinite programming in `n^{O(d)}` time.  Their genuinely
hard objects do not yield a shippable witness family here:

- Theorem 3.6 gives the needed 3-XOR properties only with high probability.
  In the proof of Theorem 3.9 the authors choose and fix an unspecified good
  formula from that distribution; this is an existence argument, not a
  deterministic per-instance construction carrying a certificate.
- Theorem 4.12 then proves that the relativized 4-CNF formulas require SOS
  refutations of size `m^{Omega(k)}` in the stated regime.  The very property
  that makes these formulas hard makes an explicit SOS witness exceed the
  benchmark's 2,000-character/256-atom answer cap.  A resolution refutation
  supplied through Lemma 2.6 is also exponentially large in the relevant
  parameter.

The retained prototype therefore used the exact SOS object from Definition
2.2 but only its degree-one equational special case.  It inverse-generated
linear polynomial equations around a known constant-multiplier identity.  No
instance was solved during generation, and verification is exact coefficient
comparison.

## Why H fails

Track A would be false: the certificate is produced by modular Gaussian
elimination with exact rational validation.  Its complexity is
`O(n*m^2 + m^3)` for `m` equations and `n` coefficient columns.  At the
declared hard preset (`m=31`, `n=640`), the measured mechanical cost averaged
**671,237 field operations and 0.029 seconds per instance** (5,369,902
operations over eight instances in the latest self-test record).

The proposed Track B compact route was a 32-point Walsh-Hadamard transform and
Gray-code sign generation: **222 exact operations**.  This is a real
mechanical/compact gap, but it does not make a hard no-tool distribution: the
row labels expose the Walsh domain clearly enough that the oracle models
recovered the route unaided.

The repository-owned hardening run measured:

| level | completed non-error attempts | solved |
|---|---:|---:|
| easy: `n=96` | 3 | 2 |
| medium: `n=256` | 3 | 1 |
| hard: `n=640` | 3 | 3 |
| escalated: `n=1280` | 2 | 1 |

Any one success defeats a level.  Thus all four levels through the task's
third escalation were defeated, and in particular the named shipping
candidate was solved 3/3.  The final slot at `n=1280` could not complete
because the OpenRouter key reached its total limit; four 403 records are kept
in `llm_loop_transcript.jsonl` and are not counted as failures.  They do not
change the rejection: that level had already been solved by a completed
attempt.

Increasing `n` further only appends coefficient columns.  Every individual
column has the same missing Walsh frequency, so the 222-operation route is
independent of `n`; more columns do not create a new structural obstacle.
There is therefore no honest fixed-answer-length escalation left for this
prototype.  The four local attacks in G6 all failed 0/8, but the no-tool oracle
successes are direct contrary evidence and take precedence.

In short: **G passes, V passes, H fails on Track B; Track A is explicitly not
claimed.**  The main Theorem 4.12 family cannot replace the prototype without
violating the explicit-witness cap, and the short native SOS special case was
too easy once its invariant was visible.
