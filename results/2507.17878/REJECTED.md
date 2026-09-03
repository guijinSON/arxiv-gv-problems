# Rejected on audit: broken by the domain-standard attack

Paper: [Strong Sparsification for 1-in-3-SAT via Polynomial Freiman-Ruzsa](https://arxiv.org/abs/2507.17878), arXiv:2507.17878.

**This family was shipped and has been withdrawn.** It passed all eight gates
(`G6.pass = True`) and the four-vendor oracle pool returned `hardened`. Both
signals were wrong.

## The break

- **Family:** planted monotone 1-in-3-SAT
- **Attack:** exactly-1-in-3 unit propagation with DPLL
- **Result: 8/8 shipping instances solved**, under 1 second each.

Graded by this module's own `verify()`. Reproduce with the harness in
[`audit/`](../../audit/README.md); see [`AUDIT.md`](../../AUDIT.md).

## Why the adversary panel missed it

Same mechanism as 1512.03127. Notably this module *did* anticipate the
GF(2) XOR relaxation -- it carries an `xor_echelon` and a `xor_free` set to
stop Gaussian elimination determining the assignment. That defence is real
but it is aimed at the wrong attack: 1-in-3 propagation is strictly
stronger than XOR reasoning here, because it also exploits the
at-most-one side of the constraint, which XOR discards.

Its G6 even included a `parity` probe, which is the XOR check. The
propagation attack was still absent.

## Disposition

The generator, self-test report, oracle transcript and README were removed, and
`artifacts/2507.17878.jsonl` was deleted, rather than leave an apparently validated but
easy family in the corpus. `codex_run.log` is kept for provenance.

G6 now requires the standard algorithm for the problem class (commit `606332e`),
and `submit.sh` refuses a panel of fewer than four attacks.
