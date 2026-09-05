# Blocked: external oracle quota

The module and all local gates pass, but STEP 4 and both G9 diagnostic arms could not obtain a single valid oracle attempt on 2026-09-05.

`scripts/harden.py` returned HTTP 403 `Key limit exceeded (total limit)` from every selected OpenRouter vendor. In accordance with the harness contract, these are recorded as `solved: "error"` and are not counted as oracle failures. The script-owned error transcripts are retained in `llm_loop_transcript.jsonl`, `g9_hinted_transcript.jsonl`, and `g9_placebo_transcript.jsonl`.

This is neither a rejection nor a hardness verdict. Re-run all three arms with a funded `OPENROUTER_API_KEY`, copy the G9 transcripts back, update `G9_ORACLE_RESULTS`, regenerate `selftest_report.json`, and revise the README tables before submission.
