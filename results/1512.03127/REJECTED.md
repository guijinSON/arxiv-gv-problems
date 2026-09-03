# Rejected on audit: broken by the domain-standard attack

Paper: [Flexible constraint satisfiability and a problem in semigroup theory](https://arxiv.org/abs/1512.03127), arXiv:1512.03127.

**This family was shipped and has been withdrawn.** It passed all eight gates
(`G6.pass = True`) and the four-vendor oracle pool returned `hardened`. Both
signals were wrong.

## The break

- **Family:** positive/monotone 1-in-3-SAT over a line-graph construction
- **Attack:** exactly-1-in-3 unit propagation with DPLL
- **Result: 8/8 shipping instances solved**, under 0.1 seconds each.

Graded by this module's own `verify()`. Reproduce with the harness in
[`audit/`](../../audit/README.md); see [`AUDIT.md`](../../AUDIT.md).

## Why the adversary panel missed it

Exactly-1-in-3 propagates extremely hard: one true literal forces its two
clause mates false, and two false literals force the third true. With 900
variables over 900 clauses the propagation closure alone very nearly
decides the instance -- no search was needed on any seed.

G6 ran degree-frequency outlier, left-to-right greedy and min-conflicts
random restart. None of them propagate, so none of them saw this.

## Disposition

The generator, self-test report, oracle transcript and README were removed, and
`artifacts/1512.03127.jsonl` was deleted, rather than leave an apparently validated but
easy family in the corpus. `codex_run.log` is kept for provenance.

G6 now requires the standard algorithm for the problem class (commit `606332e`),
and `submit.sh` refuses a panel of fewer than four attacks.
