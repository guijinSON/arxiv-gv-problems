# Rejected: arXiv 2409.17832

Paper: [Scott Neville, *Mutation-acyclic quivers are totally proper*](https://arxiv.org/abs/2409.17832), version 2.

## Decision

The constructed native family passes G and V but fails H for the allowed Track B
benchmark, specifically the polarity-flipped G9(b) gate.  It must not ship.

The family asks for the exact Markov invariant of an acyclic integer-weighted
cycle quiver.  The multiplicities are a shuffled complete arithmetic progression,
and at least two edges point each way around the cycle.  The answer is known by
composition of identities before the quiver is emitted.  Exact verification uses
the paper's executable edge-square/cycle formula and does not read the planted
answer.  G1--G8 passed; the retained `selftest_report.json` records the numbers.

This is not a Track A family.  Definition 3.20 defines the Markov invariant,
Proposition 3.21 gives an exact combinatorial computation, and Example 6.4 states
that in the generated parameter regime the answer is the sum of the squared arrow
multiplicities.  Thus a polynomial-time O(n) algorithm exists for every generated
instance.  Theorem 1.1 supplies the mutation-acyclic/totally-proper setting but is
not a hardness theorem.

## Mechanical cost and compact route

At the original shipping candidate, n=472 with 40-bit multiplicities, the
paper-standard mechanical algorithm performs 472 integer squares and 471 additions:
943 exact arithmetic operations.  Selftest measured 0.0001575 seconds for eight
instances, or 0.000019688 seconds per instance in this Python process.  At the one
permitted higher rung, n=629 with 44-bit multiplicities, that same algorithm costs
1,257 exact operations.

The compact route is genuinely shorter: identify the minimum and maximum of the
complete progression, recover its common difference, and evaluate

```text
n*a^2 + a*d*n*(n-1) + d^2*n*(n-1)*(2*n-1)/6.
```

The module conservatively counts this as 18 exact arithmetic operations after the
structural observation.  Therefore this rejection is **not** based merely on an
efficient method existing, nor on a claim that the 943-versus-18 gap is too small.
It is based on the required live G9(b) result: the compact structure becomes usable
to the evaluated solvers when it is named.

## Oracle evidence

The bare hardening run at n=472 returned `hardened`: Claude Sonnet 5 emitted no
answer within its 32,000-token completion budget, while Grok 4.6 and GPT-5.6 Terra
returned parsed but incorrect rationals.

The valid one-sentence structural hint was:

> The relevant structure is the edge-square/cycle decomposition and the arithmetic-progression multiset of arrow multiplicities.

It names the relevant structures but gives no procedure, no vanished-cycle
conclusion, and no closed-form formula.  With that hint at n=472, Grok 4.6 and
GPT-5.6 Terra both produced exact verified answers (2/3 solved).  Following G9(b),
the family was moved up exactly once.  At n=629, Gemini failed but Grok 4.6 again
produced an exact verified answer (1/2 completed attempts).  That single verified
solve is decisive: the hint still breaks the family at the one allowed higher rung.

The external OpenRouter key then reached its total limit during the third n=629
attempt.  Those 403 records are retained and are not counted as failures.  They do
not alter the decision because G9(b) is already disproved by the verified Grok
answer.  The placebo arm was not run after this decisive second failure; the task
requires rejection and stopping at that point, and a placebo result cannot rescue
the gated hinted arm.

## Prior-triage correction and retained artifacts

The suggested inverse-generated mutation-sequence family was also unsuitable for
Track A: mutation involutivity gives G and replay gives V, but this paper proves no
distributional hardness for recovering an acyclic representative.  Treating the
size of the mutation-word space as hardness would have been unsupported.  The
weighted-cycle family above was the stronger honest Track B alternative, and it is
the family actually tested.

The implementation is retained as `rejected_gen_2409_17832.py`, as required.
`llm_loop_transcript.jsonl` is the successful bare hardening run;
`g9_hinted_transcript.jsonl` contains both hinted rungs and the subsequent quota
errors.  `calibration_budget_bound_transcript.jsonl` records the initial ladder
calibration.  `selftest_report.json` honestly has G9 false and `all_passed` false.
