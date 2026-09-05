# External hardening blocker

The repaired Track-B generator passes all local gates: its rooted-codegree route recovers the candidate shipping answer in 236 exact operations, and G9(c) is within every cap. The required external loop remains incomplete on 2026-09-05.

The refreshed bare run produced real, unfavorable evidence before the external failure: `easy`, `medium`, `hard`, and `n=2400` were solved 3/3, and `n=3600` was solved 2/3. Because one success defeats a level, the harness escalated each time. At `n=5400`, four redraws received HTTP 403 `Key limit exceeded (total limit)`, so `harden.py` correctly aborted without manufacturing a verdict. The older structural-hint and placebo transcripts likewise contain only quota errors.

Accordingly:

- `.meta.json` has no `harden_verdict`;
- `llm_loop_transcript.jsonl` preserves 15 scored calls and four later API errors;
- `G9_ORACLE_RESULTS` records the named `hard` bare result as 3/3 solved, with hinted/placebo still unscored;
- `selftest_report.json` passes G9 only on the current G9(c) caps, while marking the diagnostic evidence incomplete;
- no `REJECTED.md` exists, because the harness neither returned `too_easy` nor exhausted the generator's fixed-answer-length escalation axis.

After replenishing the OpenRouter key, rerun the bare harness from this directory (the script will overwrite the partial transcript):

```bash
python3 ../../scripts/harden.py gen_2004_11315.py
```

If a level holds, slide the four-name ladder as specified, re-run local gates, and only then refresh each isolated G9 copy at the held preset. Run those copies with `GV_HINT_MODE=structural` and `GV_HINT_MODE=placebo`, copy back the transcripts, update `G9_ORACLE_RESULTS`, regenerate `selftest_report.json`, and update the oracle tables in `README.md`.
