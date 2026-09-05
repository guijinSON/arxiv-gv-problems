# Acyclic orientations with degree constraints — rejected prototype

| Field | Value |
|---|---|
| Attempted track | A — structural hardness |
| Domain / regime | logic; finite discrete |
| Core / certificate | NAE-3-SAT; signed Boolean tuple encoding an order |
| Paper reduction | Section 3.1, Theorem 10 |
| Outcome | **Rejected: G5 and G6 fail** |

This directory contains the audit of an attempted generator for Király and
Pálvölgyi, [*Acyclic orientations with degree
constraints*](https://arxiv.org/abs/1806.03426). The prototype uses the paper's
Theorem 10 reduction from NAE-3-SAT to an acyclic orientation with two earlier
and two later incident edges at every nonterminal vertex. It samples the
assignment first, builds a balanced regular NAE formula around it, and uses the
proof to expand that assignment into a topological order. Exact verification is
sound and never consults the stored answer.

It must not ship. A corrected break-count WalkSAT attack solves 8/8 instances
at the shipping preset and 8/8 at both tighter named presets, in milliseconds.
The earlier report used random flips while calling the probe WalkSAT, so its
zero-success result was not evidence against standard local search. See
[`REJECTED.md`](REJECTED.md) for the theorem-level decision, both-track audit,
and measured mechanical/compact-route costs.

## Reproducing the failed gate

```bash
python3 rejected_gen_1806_03426.py > selftest_report.json
```

The report should have `G1`, `G2`, `G3`, `G4`, `G7`, `G8`, and the G9 size caps
passing, while `G5_density_and_baseline.pass` and
`G6_adversary_panel.pass` are false. The decisive G6 entry is
`walksat_breakcount_32x100n`, with 8 successes in 8 attempts.

The old bare oracle transcript is retained because it is valid evidence about
those three no-tool calls, but it does not override a successful executable
domain attack. The hinted and placebo transcripts contain only HTTP 403
key-limit errors and support no diagnostic conclusion.

## Files

| File | Purpose |
|---|---|
| `rejected_gen_1806_03426.py` | retained, executable failed prototype |
| `selftest_report.json` | corrected gates showing the attack success |
| `llm_loop_transcript.jsonl` | historical bare no-tool run |
| `g9_*_transcript.jsonl` | historical auxiliary-arm errors |
| `REJECTED.md` | reviewable rejection rationale |

No `gen_1806_03426.py` is present, preventing this failed distribution from
being mistaken for a shippable family.
