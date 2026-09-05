# Oracle hardening blocked by exhausted OpenRouter key

The generator and local gates G1–G8 pass at the provisional shipping preset `easy = {"n": 36, "laps": 100003}`. G9(c) also passes. Final STEP 4/G9 oracle evidence cannot be completed with the supplied environment:

- `GET https://openrouter.ai/api/v1/key` reported `limit: 500`, `limit_remaining: 0`, and `usage: 501.232850938`.
- The final bare rerun obtained one completed (n=36) failure, followed by four HTTP 403 `Key limit exceeded (total limit)` redraws. The harness exited rather than scoring those errors as model failures.
- The earlier (n=18) rung held bare but failed G9(b), with the structural-hint arm solved by Grok 4.6. The one permitted upward move was therefore applied, and (n=36) replaced it in the ladder.
- Final (n=36) structural-hint and placebo arms have zero valid attempts.

This is an external-state blocker, not a rejection of arXiv:1404.4442 and not a passing hardness result. After quota is restored, rerun the bare harness in this directory, then run one-rung copies under `GV_HINT_MODE=structural` and `GV_HINT_MODE=placebo`, copy their transcripts back, update `G9_ORACLE_RESULTS`, rerun `selftest()`, and revise the oracle tables in `README.md`.
