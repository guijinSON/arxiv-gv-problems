# Rejected on audit: broken by the domain-standard attack

Paper: [Nuclear norm minimization for the planted clique and biclique problems](https://arxiv.org/abs/0901.3348), arXiv:0901.3348.

**This family was shipped and has been withdrawn.** It passed all eight gates
(`G6.pass = True`) and the four-vendor oracle pool returned `hardened`. Both
signals were wrong.

## The break

- **Family:** planted k-clique
- **Attack:** spectral seeding + randomized greedy with local search
- **Result: 5/8 shipping instances solved**, within a 45 s budget.

Graded by this module's own `verify()`. Reproduce with the harness in
[`audit/`](../../audit/README.md); see [`AUDIT.md`](../../AUDIT.md).

## Why the adversary panel missed it

The parameter choice was thoughtful and still wrong. k=16 sits *below* the
spectral threshold sqrt(512)~22.6, which correctly defeats the textbook
Alon-Krivelevich-Sudakov eigenvector attack -- and the README documented
that reasoning. What it missed is that at n=512 the planted clique is close
to the natural maximum clique of G(512,1/2) (~2*log2(512)=18), which puts it
within reach of randomized greedy with local search. Defeating the named
spectral algorithm is not the same as defeating the problem.

The break is unambiguous: expected random 16-cliques in G(512,1/2) is about
4e-7, so the only 16-clique is the planted one and the attack recovered it.
As with 1008.2814, the paper presents an algorithm that solves the planted
problem, which should have forced this attack first.

## Disposition

The generator, self-test report, oracle transcript and README were removed, and
`artifacts/0901.3348.jsonl` was deleted, rather than leave an apparently validated but
easy family in the corpus. `codex_run.log` is kept for provenance.

G6 now requires the standard algorithm for the problem class (commit `606332e`),
and `submit.sh` refuses a panel of fewer than four attacks.
