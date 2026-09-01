# Rejected: arXiv:1601.07131

Paper: Ferran Cedó, Tatiana Gateva-Ivanova, and Agata Smoktunowicz,
[*On the Yang-Baxter equation and left nilpotent left braces*](https://arxiv.org/abs/1601.07131).

## Verdict

This paper does not support a problem family satisfying the required hardness
gate **H**, so no generator module is shipped. The full LaTeX source, not only
the abstract, was reviewed.

## What the paper actually establishes

- Section 1 defines a left brace, its operation `a*b = a·b-a-b`, the socle,
  and a non-degenerate involutive set-theoretic Yang--Baxter solution.
- Section 2 proves structural restrictions. In particular, Theorem 2 says that
  a finite solution whose structure group is Engel is the trivial solution.
  This is not a computational-hardness result or a hard parameter regime.
- Section 3, Proposition 5, identifies the multipermutation level of the
  solution associated with a nonzero brace with termination of the radical
  chain `B^(n+1) = B^(n)*B`. For an explicitly tabulated finite brace, both the
  associated solution and this chain are obtained by direct finite-table
  computation.
- Section 4, Proposition 6, proves that every finite solution embeds in a finite
  left brace. Its proof is an explicit quotient construction from the structure
  group; it is an existence/embedding theorem, not an intractability theorem.

The paper contains no reduction, complexity classification, FPT boundary, or
parameter regime in which finding any of these algebraic objects is shown (or
argued) to be computationally hard.

## Why the apparent generator ideas fail

| Candidate task | Gate failure |
|---|---|
| Given a set, output a Yang--Baxter solution | **H:** the flip `r(x,y)=(y,x)` is a closed-form non-degenerate involutive solution for every size. |
| Given a finite brace, output its associated solution | **H:** Section 3 gives the formula `r(a,b)=(L_a(b), L^(-1)_(L_a(b))(a))`; this is direct table lookup/inversion. |
| Given operation tables, certify that they form a brace or that `r` satisfies YBE | Not a witness-search problem: substitution already decides the supplied object. Asking for the full table would again admit trivial closed-form braces/solutions unless extra constraints external to the paper were imposed. |
| Compute multipermutation level/right nilpotence | **H:** on finite tables, retraction/partition refinement or repeated set closure computes it directly; Proposition 5 is a characterization, not a hard search problem. |
| Embed a finite solution into a finite brace | **H/G/V not established together:** Proposition 6 supplies a general construction, while its brace can have order `n^m` (notation of its proof). The paper supplies neither a polynomially bounded witness regime nor hardness of finding an embedding. |
| Complete a partially hidden operation or Yang--Baxter table | **H unsupported:** this would be a new constraint-satisfaction problem and planted distribution not studied in the paper. Planting a completion would give G and substitution would give V, but the required claim that no polynomial-time/closed-form attack exists would be speculation. |
| Recover an isomorphism after relabelling a brace | **H unsupported and not the paper's problem:** no isomorphism-complexity result appears in the paper; using this would also make the required canonicalization depend on the unproved hard problem. |

## Gate status

| Gate | Status |
|---|---|
| G (inverse-generatable) | Possible for several artificial completion/isomorphism variants, but not sufficient. |
| H (hard) | **Failed.** Natural tasks are explicitly constructible or direct finite-table computations; modified tasks have no hardness support in the paper. |
| V (cheap exact verification) | Possible by substitution for tables, but not sufficient. |

Per the task instruction to stop when any of G/H/V fails, `gen_1601_07131.py`,
`selftest_report.json`, and oracle-loop artifacts were not fabricated, and the
hardening harness was not run.
