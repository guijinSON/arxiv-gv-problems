# Rejected on audit: broken by the domain-standard attack

Paper: [Convex optimization for the planted k-disjoint-clique problem](https://arxiv.org/abs/1008.2814), arXiv:1008.2814.

**This family was shipped and has been withdrawn.** It passed all eight gates
(`G6.pass = True`) and the four-vendor oracle pool returned `hardened`. Both
signals were wrong.

## The break

- **Family:** planted k disjoint cliques
- **Attack:** spectral seeding + randomized greedy with local search, per clique
- **Result: 8/8 shipping instances solved**, well under the 60 s budget.

Graded by this module's own `verify()`. Reproduce with the harness in
[`audit/`](../../audit/README.md); see [`AUDIT.md`](../../AUDIT.md).

## Why the adversary panel missed it

The deeper problem is not the search but the *specification*. The shipping
preset plants 3 cliques of size 10 in n=144 at p=1/2, where roughly 36
10-cliques already exist by chance, and `verify` accepts ANY three disjoint
10-cliques. The planted answer is therefore never needed -- the attack
never looked for it, it just harvested three cheap cliques.

This is the 'huge space, worthless problem' failure in a new guise: the
space is astronomically large and the solution set is dense enough that
finding *a* witness is easy. Note also that the paper itself gives a convex
relaxation that recovers planted disjoint cliques, which should have made
the domain attack the first thing tried.

## Disposition

The generator, self-test report, oracle transcript and README were removed, and
`artifacts/1008.2814.jsonl` was deleted, rather than leave an apparently validated but
easy family in the corpus. `codex_run.log` is kept for provenance.

G6 now requires the standard algorithm for the problem class (commit `606332e`),
and `submit.sh` refuses a panel of fewer than four attacks.
