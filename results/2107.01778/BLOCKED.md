# Oracle hardening incomplete: OpenRouter total limit reached

The native Track B generator is implemented and every local gate G1--G9(c)
passes at the provisional `hard` preset. The mandatory STEP 4 and G9 oracle
evidence cannot be completed with the supplied credential.

On 2026-09-05, `python3 ../../scripts/harden.py gen_2107_01778.py` completed
three valid attempts at `easy` (3/3 solved), three at `medium` (3/3 solved), and
two at `hard` (0/2 solved). Before the third `hard` attempt, four redraws
returned HTTP 403 `Key limit exceeded (total limit)`, so the harness correctly
aborted without a verdict. No second OpenRouter credential is configured.

One-rung copies were then run in isolated scratch directories for
`GV_HINT_MODE=structural` and `GV_HINT_MODE=placebo`. Both received four HTTP
403 responses and zero completed attempts. Their script-owned transcripts were
copied back as required. Nothing in the error-only arms is counted as model
failure or hardness evidence.

After quota is restored, rerun:

```bash
python3 ../../scripts/harden.py gen_2107_01778.py
```

Because that command overwrites the transcript, it will repeat the full ladder.
Use its returned `shipping_params` to confirm or slide the four-rung ladder,
rerun `selftest()`, and then rerun the structural and placebo one-rung copies in
separate scratch directories. Update `G9_ARMS`, `selftest_report.json`, and the
oracle tables in `README.md` from those script-owned outputs.
