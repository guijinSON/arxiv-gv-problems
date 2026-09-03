# Rejected on audit: broken by the domain-standard attack

Paper: [Orientable quadratic equations in wreath products](https://arxiv.org/abs/2503.01929), arXiv:2503.01929.

**This family was shipped and has been withdrawn.** It passed all eight gates
(`G6.pass = True`) and the four-vendor oracle pool returned `hardened`. Both
signals were wrong.

## The break

- **Family:** exact tiling of blocks by sum-T triples (3-PARTITION)
- **Attack:** Algorithm X / DLX exact cover with fewest-options-first (MRV)
- **Result: 8/8 shipping instances solved**, under 5 seconds each (four instances under 0.2 s).

Graded by this module's own `verify()`. Reproduce with the harness in
[`audit/`](../../audit/README.md); see [`AUDIT.md`](../../AUDIT.md).

## Why the adversary panel missed it

The generator is *correct*: every length lies strictly inside the
3-PARTITION band `T/4 < a < T/2` (verified 3840/3840), so exactly three
items fill each block and the family sits in the genuinely strongly
NP-hard regime. That is worst-case hardness, and it does not transfer to
this distribution. A shipping instance offers ~300 sum-T triples over 96
items; MRV backtracking closes that search almost immediately.

The panel that passed -- per-item degree outlier, largest-first greedy,
256 random restarts -- probes whether the *planting* left a signature. It
did not: plants and decoys share one sampler and labels are shuffled. The
family is symmetric and still trivial, because symmetry was never what
made it hard.

## Disposition

The generator, self-test report, oracle transcript and README were removed, and
`artifacts/2503.01929.jsonl` was deleted, rather than leave an apparently validated but
easy family in the corpus. `codex_run.log` is kept for provenance.

G6 now requires the standard algorithm for the problem class (commit `606332e`),
and `submit.sh` refuses a panel of fewer than four attacks.
