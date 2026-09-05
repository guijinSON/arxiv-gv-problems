# Rejected RCSP modular-order generator (arXiv:2511.22914)

This directory contains an archived, locally correct generator that **does not meet the hardness requirement**. The complete decision and measured costs are in [REJECTED.md](REJECTED.md).

The family uses the paper’s native Boolean reconfiguration-CSP objects: pins, constraints `x_u <= x_v`, and two satisfying assignments. A witness is an ordered list of single-variable changes. Generation plants that list first and adds only constraints that preserve it; verification replays the changes exactly. These facts establish G and V.

They do not establish H. The family is in the tractable ordered-partial-Maltsev regime of Section 3.2 (Theorem 3.8), and the specialization has an `O(n+m)` topological algorithm. The hoped-for Track B challenge was to recognize a modular progression among the endpoint-difference variables instead of scanning thousands of inequalities. In the fresh script-owned hardening run, however, the oracle pool returned valid witnesses on 14 of 15 non-error calls, including 3/3 at the configured hard preset and 3/3 after doubling the ambient size. A later oversized prompt caused provider errors, not model failures.

The implementation is retained as [rejected_gen_2511_22914.py](rejected_gen_2511_22914.py). It can still be inspected locally:

```bash
python3 rejected_gen_2511_22914.py
```

Its `selftest_report.json` is evidence of construction, parsing, verification, adversary, scaling, canonicalization, and size-cap behavior only. It must not be interpreted as a passing hardness report. The bare oracle evidence is in `llm_loop_transcript.jsonl`; the two `g9_*` files are older infrastructure-error diagnostics and were not used in this rejection.
