# arXiv 2601.04295 — rejected after Track B hardening

This directory contains a preserved, locally verified prototype for Gomes,
[“An explicit family of 30 blocks meeting every 6-set of [60] in at least two
points”](https://arxiv.org/abs/2601.04295), but it is **not a shippable problem
family**. Read [REJECTED.md](REJECTED.md) for the full quantitative decision.

The paper's Section 2 object is native and retained: each 12-point component is
split into four triples and carries all six unions of two triples. The prototype
composes these components, inverse-plants a unique pair-and-block witness, and
carries it through an exact modular relabeling. Every local correctness,
guess-resistance, adversary, scaling, canonicalization, and output-cap gate
passes.

The family nevertheless fails H. Track A is unavailable because Theorem 1's
proof is itself a short witness algorithm and the paper proves no hard regime.
For Track B, the reference incidence scan is `O(6m)` and used a measured mean of
5,849 tests at `easy` and 17,295 at `hard`; the modular/decomposition shortcut
uses at most 295 exact operations. The mandatory no-tool pool found that
shortcut and solved 9/9 calls—3/3 at each of `easy`, `medium`, and `hard`.
`.meta.json` records the resulting `too_easy` verdict.

The `prior_g9_*_quota_blocked` files are retained only as an audit of an older
prototype whose G9 calls received HTTP 403. No final G9 arms were run: the bare
STEP 4 loop had already rejected the family, so hinted/placebo diagnostics could
not rescue it and would only spend oracle calls.

The attempted module is preserved as `rejected_gen_2601_04295.py`, as required
for audit and possible future analysis. It may be run directly to reproduce the
local self-test, but it must not be emitted as a dataset family:

```bash
python3 rejected_gen_2601_04295.py
```
