# External hardening incomplete

The local generator and gates are complete.  The required command

```bash
python3 ../../scripts/harden.py gen_1606_06566.py
```

completed 11 valid oracle attempts, then every redraw returned HTTP 403 with
`Key limit exceeded (total limit)`.  The harness exited without writing a
`harden_verdict`, as it should: API errors are not solver failures.

Do not submit or reject this result in its current state.  After increasing the
OpenRouter key limit, rerun the bare loop from this directory.  That command
will overwrite the partial transcript by design.  If and only if it returns a
complete hardened verdict, update the named difficulty ladder as instructed,
rerun `selftest()`, and run the structural and placebo G9 arms in separate
scratch directories.
