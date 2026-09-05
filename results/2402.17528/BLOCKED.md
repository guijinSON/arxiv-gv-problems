# External hardening blocker

The Track-B generator is implemented and its local G1–G9(c) gates pass. It is
neither shipped nor rejected because the mandatory script-owned oracle evidence
could not finish.

On 2026-09-05, `scripts/harden.py` completed two countable `easy` attempts:

- `openai/gpt-5.6-terra`, seed `1939039951`: parsed answer, rejected because the
  `x^(v-3)` coefficient was wrong;
- `google/gemini-3.8-flash`, seed `566635636`: parsed answer, rejected for the
  same exact reason.

Before the third required attempt, OpenRouter returned HTTP 403 “Key limit
exceeded (total limit)” on four consecutive redraws. The harness correctly
stopped with “oracle pool is unreachable” and did not write a
`harden_verdict`. Those errors are not model failures, so 0/2 cannot support a
hardness claim.

`llm_loop_transcript.jsonl` and `.meta.json` are the untouched script outputs.
The structural-hint and placebo runs were not started, and their transcript
files are absent rather than fabricated.

Resume after configuring a funded `OPENROUTER_API_KEY`:

```bash
cd results/2402.17528
python3 ../../scripts/harden.py gen_2402_17528.py
```

If the bare run hardens, set `SHIPPING_DIFFICULTY` to the held rung, run the two
G9 arms in separate scratch directories, copy their script-owned transcripts
back, update `G9_RESULTS`, regenerate `selftest_report.json`, and update the
oracle tables in `README.md`.
