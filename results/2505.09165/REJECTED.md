# Rejected: arXiv 2505.09165

## Decision

This attempted family is rejected on **H for Track B**, specifically mandatory gate
**G9(b)**.  Generatability (G) and exact witness verification (V) pass: the generator
samples the path partition first, constructs path lengths around it, and `verify`
checks a submitted partition by exact integer sums plus compressed replay of the
paper's BusOut transitions.  This is not a Track A rejection and no distributional
hardness claim is made.

The source basis is Section 2's transition definition and Section 3, Theorem 2 of
[Ishibashi, Yoshinaka, and Shinohara, *BusOut is NP-complete*](https://arxiv.org/abs/2505.09165).
Theorem 2 supplies the native one-spot, two-colour, unit-capacity, disjoint-directed-
path regime.  Theorem 1 (one colour), Theorem 6 (edgeless graphs with all relevant
parameters fixed), and Theorem 7 (at least as many spots as colours in the edgeless
case) are the easy regimes that the construction avoided.

## Costs and the failed hint gate

At the final shipping candidate (`n=82`, 246 paths), the successful mechanical
algorithm builds 30,135 pair sums, makes 20,172 target/path probes, and uses **100,860
exact arithmetic/lookup operations** in total.  It is
`O(m^2 + bm + z)` and took under 0.02 seconds locally.  The intended compact route is
**246 exact remainder operations**: reduce every displayed path length modulo
500000003 and group equal residues.  The answer is 246 atoms / 1,039 characters, so
neither answer length nor the 300-operation cap caused the rejection.

The bare harness first held `n=56` at 0/3.  The structural hint then produced a
verified solution, so the protocol's single upward move was used.  In the final bare
rerun, `n=80` was solved by one oracle and the harness itself escalated to `n=82`,
where bare held **0/3**.  The one-sentence hint at that exact held rung was:

> Modulo 500000003, the three path lengths assigned to one passenger block share a residue.

It names only the invariant and contains no procedure or derived answer.  With it,
the pool solved **2/3** instances.  Therefore the family fails the polarity-flipped
G9(b) gate after its one allowed higher-level rerun: the compact route is executable
in context once the claimed insight is named.  A placebo arm was not run after this
decisive gated failure.

## Retained evidence

- `rejected_gen_2505_09165.py`: complete deterministic generator and local gates.
- `llm_loop_transcript.jsonl` and `.meta.json`: harness-owned final bare run.
- `g9_hinted_transcript.jsonl`: three shipping-level hinted calls (2/3 solved).

The family should not be reopened merely by increasing `n`: 84 groups already use
252 of the 256 allowed answer atoms.  A viable new attempt would need a different,
fixed-length native dispatch certificate or a different structural compression, not
another transcription-heavy escalation.
