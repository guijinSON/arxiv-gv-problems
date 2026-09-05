# External hardening blocker

On 2026-09-05 the final module passed every local gate, including the current
G9(c) size/effort gate. The required script-owned oracle evidence could not be
completed because the configured OpenRouter key exhausted its total quota.

The bare run produced five genuine scored calls before the failure:

| preset | scored results |
|---|---|
| `easy`, `n=8` | 3/3 solved across Google and OpenAI |
| `medium`, `n=16` | 2/2 solved across Google and OpenAI |
| `hard`, `n=24` | not reached |

The third medium attempt was redrawn four times; every redraw returned HTTP 403
`Key limit exceeded (total limit)`, so `harden.py` correctly aborted without a
terminal verdict. The isolated structural-hint and placebo runs likewise contain
only HTTP 403 records and no scored attempts.

The partial bare transcript and error-only G9 transcripts are retained exactly
as produced by `harden.py`. They are not evidence that the provisional shipping
preset is hard. The family is therefore blocked, not rejected: restore OpenRouter
quota, rerun the bare ladder, run the two G9 arms in isolated directories, update
`G9_RESULTS`, rerun `selftest()`, and only then consider emission or submission.
