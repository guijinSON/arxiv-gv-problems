# Rejection — arXiv:2105.01787

Paper: Sepehr Hajebi, Yanjia Li, and Sophie Spirkl, [“Complexity dichotomy for List-5-Coloring with a forbidden induced subgraph”](https://arxiv.org/abs/2105.01787), version 3.

## Decision

No module is shipped. The proposed family clears G and V but fails H on Track A, and it has no compact route that would make it a Track B family. This decision is based on the full paper and its LaTeX source, especially Theorems 24–26 and Section 6, not on the abstract.

| gate | result |
|---|---|
| G — generatable | Pass for the Section 6 reduction: sample a satisfying assignment first, sample monotone NAE clauses that cross its two color classes, and carry the assignment through the displayed graph construction. |
| V — verifiable | Pass: check every NAE clause and execute the proof's explicit extension to a 5-coloring; all checks are finite integer comparisons. |
| H — Track A | Fail for the generated distribution: the theorem is worst-case NP-completeness, while ordinary inverse-planted monotone NAE instances are easy for the tested standard algorithms. |
| H — Track B | Fail: the tested family has no shorter invariant/symmetry route. Its only evident route is the same clause repair or propagation performed by the mechanical solver. |

## Exact paper regimes

The paper defines List-5-Coloring as a graph plus lists contained in `{1,2,3,4,5}`, with a witness assigning one listed color to every vertex and unequal colors to adjacent vertices.

Theorem 24 proves that List-5-Coloring on `rP3`-free graphs is polynomial-time for every fixed `r`. Its proof constructs polynomially many refinements, reduces them to list size at most two, and invokes the 2-SAT algorithm of Theorem 23. Consequently, a Track A generator in the title regime would contradict the paper's own main algorithmic result unless it supplied independent distributional evidence; the proposed planting gives none.

The hard regime is different. Section 6, Theorem 26 reduces monotone NAE-3-SAT to ordinary 5-coloring. For a source instance with `n` variables and `m` clauses, it creates the clique `C`, the variable set `X`, two vertices per clause in `Y`, and six vertices per clause in `U`, for `5 + n + 8m` vertices. Statements (30) and (32) prove respectively that the graph is 5-colorable exactly when the source is NAE-satisfiable and that every resulting graph is `2P4`-free. This is the only construction in the paper that simultaneously preserves a hard forbidden-induced-subgraph regime and carries a finite coloring witness.

The prior proposal — plant a proper list coloring and add arbitrary edges only between different colors — does not preserve `rP3`-freeness or `2P4`-freeness. It therefore produces generic planted coloring instances, not instances in either dichotomy regime of this paper.

## Track A failure: measured standard attacks

I tested the direct inverse version of Theorem 26: choose a balanced Boolean assignment, then sample distinct 3-variable clauses uniformly subject to being NAE under that assignment. A pilot sweep used all 30 combinations

`n in {64,96,128,160,200}` and `m/n in {4,6,8,10,12,16}`

with a fixed independent seed at each combination. A DPLL solver with unit propagation and a maximum-occurrence branching rule solved 30/30. A min-conflicts/random-walk NAE repair solver also solved 30/30, always from its first restart.

At the largest and sparsest tested point, `n=200, m=800`, DPLL found a witness in 0.657 seconds using 528 search nodes and 11,722 propagated assignments. The local repair solver found one in 206 flips. Denser instances were easier rather than harder: at `m/n=16`, DPLL needed only 10 nodes and local repair 169 flips in the recorded `n=200` run. These algorithms return a valid source assignment, which Section 6 then extends mechanically to a graph coloring. Thus the certificate is simply the output of a fast standard solver on this distribution.

Theorem 26 establishes worst-case NP-completeness for `k=5, r=2`; it does not establish hardness of this planted distribution. Reporting that theorem as the distributional hardness basis would conflate the two claims prohibited by Track A.

## Why this is not rescued by Track B

There are two possible answer formats, and neither gives the required mechanical-versus-compact gap.

1. A full 5-coloring at `n=200, m=800` has `5+n+8m = 6,605` atomic entries, far above G9(c)'s 256-element cap.
2. A reduced 200-bit source assignment can be checked and extended by the Section 6 proof, but its known route is the local-repair/propagation computation just measured. The mechanical route is 206 flips plus clause bookkeeping (or 528 DPLL nodes and 11,722 propagations). The putative compact route is not shorter: no invariant in the planted construction recovers the 200 bits, so an unaided solver must perform the same repairs/propagations and then write all 200 bits. Even the unrealistically favorable count of one initial inspection per clause plus one operation per recorded flip is `800 + 206 = 1,006` operations, versus the mechanical solver's same 1,006-step lower bound; real bookkeeping is higher. Both are well beyond G9(c)'s 300-operation intended-route cap.

In other words, the mechanical and unaided routes are the same algorithm, up to implementation detail. There is no change of variables, symmetry, invariant, or decomposition to notice. Scaling until the local solver becomes costly would only lengthen the assignment past the 256-atom cap; it would grow the needle rather than the haystack.

I also checked the obvious alternative of using the polynomial `rP3`-free side as Track B. Theorem 24 supplies a general algorithm, but a planted coloring by itself supplies no compact recovery route. Special subclasses that make the witness compact (cluster graphs, two-element lists, or visibly repeated gadgets) are solved directly by matching, 2-SAT, or componentwise propagation; their compact and mechanical routes again coincide. The existence of a very high-degree general theorem is not by itself a Track B puzzle.

## What could reopen this paper

A future construction could qualify if it supplied one of the following without leaving the paper's objects:

- a theorem-backed distribution of satisfiable monotone NAE-3-SAT instances on which DPLL, local search, and the relevant spectral/relaxation attacks all fail, together with a certificate of at most 256 atoms and a sub-300-operation structural route; or
- an `rP3`-free list-coloring construction whose paper algorithm has a measured large mechanical cost but whose coloring follows from a genuinely shorter invariant.

Neither is present in the paper, and the tested inverse planting has the opposite empirical behavior. Building a module around it would turn a worst-case theorem into a false distributional Track A claim.
