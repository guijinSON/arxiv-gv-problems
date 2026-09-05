# Rejected Track B family for arXiv:1301.4884

This directory does **not** contain a shippable problem generator.  The native
Hopf-fibre construction passes all local generation and exact-verification
checks, but the official bare hardening loop solved every tested instance and
returned `too_easy`.  The full, reviewable decision is in
[`REJECTED.md`](REJECTED.md).

| item | result |
|---|---|
| attempted track | B, no-tool compression |
| native objects | rational points on `S^3` and Hopf-fibre quarter-turn orbits |
| construction | common-phase identity after Equation (7) |
| certificate | 6-by-4 rational matrix |
| local G/V gates | pass |
| random guessing | 0/200,000 at `n=16` |
| reference method | exact compatibility CSP, 64,876 median operations |
| compact method | phase normalization, 192 operations at `n=16` |
| bare oracle loop | 12/12 solved through escalated `n=21` |
| final verdict | rejected: H-B fails |

The built module is retained as `rejected_gen_1301_4884.py`; the script-owned
oracle evidence is `llm_loop_transcript.jsonl` with metadata in `.meta.json`.
The paper itself is [Delimiting Maximal Kissing Configurations in Four
Dimensions](https://arxiv.org/abs/1301.4884).
