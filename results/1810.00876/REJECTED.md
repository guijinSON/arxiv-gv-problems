# Rejected: arXiv:1810.00876

Paper: M. Delacorte, [*Graph Isomorphism by Conversion to Chordal (6, 3) Graphs*](https://arxiv.org/abs/1810.00876).

## Decision

This paper does not yield a family that clears **H**, on either track. The proposed
inverse generator (sample a graph, relabel it by a sampled permutation, and retain
that permutation) clears G, and exact adjacency comparison clears V. The failure is
hardness of the generated distribution, not witness validity or answer-space size.

- **Track A fails.** The paper proves no distributional-hardness result. Its Section
  2 construction is a reversible representation change: subdivide every source edge
  and make all original vertices a clique (Booth's reduction), then add and mark
  edges in forbidden six-vertex configurations. Section 3 explicitly proposes a
  direct isomorphism procedure after that conversion. Worst-case equivalence to
  Graph Isomorphism does not make the natural planted distribution hard.
- **Track B also fails.** For the natural scalable distribution suggested by the
  triage, dense `G(n,1/2)` graphs followed by a secret relabelling, ordinary joint
  color refinement produces the certificate. The only by-hand route is the same
  computation: compare degrees, then compare multisets of neighbor degrees. There
  is no shorter invariant, symmetry, or change of variables left for a solver to
  notice.

## STEP 0 findings from the full paper

The exact native object is a finite simple graph. Section 1 defines chordal graphs,
`(q,t)` graphs, simplicial/regular partitions, stars, and thin- and thick-leg
spiders. The relevant easy case is stated immediately after Lemmas 1.1--1.3: for
the extended chordal `(6,3)` class, the coarsest regular simplicial partition is the
automorphism partition. Section 3 says to convert both graphs and then test them by
that partition method (or align corresponding partition cells and compare the
remembered original edges). Thus the paper's own contribution is a mechanical
route to the isomorphism, not a source of hard instances or a compact alternative
to that route.

There is no numbered main theorem, complexity analysis, hard parameter regime,
average-case statement, or planted-distribution statement in the paper. The only
numbered results are the three structural lemmas in Section 1. The termination
argument in Section 2 merely observes that at most `n(n-1)/2` edges can be added.

## Measured certificate cost

I tested the exact prior-triage proposal before rejecting it. For each `n` and seed,
I sampled every possible edge independently with probability `1/2`, sampled a
uniform permutation using a seed-local PRNG, formed the relabelled copy, and ran
joint 1-dimensional Weisfeiler--Leman refinement. A run was counted as solved only
when every final color occurred exactly twice, once in each graph, so the colors
themselves gave a verified bijection.

| source vertices | solved | refinement rounds | median neighbor-incidence operations | median wall time |
|---:|---:|---:|---:|---:|
| 64 | 20/20 | 2 | 7,964 | 0.000890 s |
| 128 | 20/20 | 2 | 32,436 | 0.007328 s |
| 256 | 20/20 | 2 | 130,152 | 0.029009 s |

Seeds were `0..19`. The operation count includes both input graphs and both
refinement rounds. At `n=256` the ordinary permutation witness already reaches the
256-atom G9 cap.

These are the two required STEP 0 numbers at the largest shippable setting:

- **Mechanical cost:** 130,152 neighbor-incidence inspections, two refinement
  rounds, and 0.029009 seconds median. It succeeds on 20/20 instances.
- **Compact route:** no shorter route exists in this construction; the apparent
  shortcut is precisely “degree, then neighbor-degree multiset,” which performs the
  same 130,152 inspections, plus writing the 256 vertex images. The compact and
  mechanical routes therefore have the same asymptotic and measured length.

Applying the Section 2 split-graph conversion does not repair H. It is reversible,
so a solver can recognize the clique/edge-subdivision sides and run the same
refinement on the source graph; conversely, including all subdivision vertices in
the witness only exhausts the answer cap sooner. Choosing an externally engineered
hard Graph Isomorphism benchmark would import the hardness and intuition from that
external construction, while this paper would contribute only a reversible wrapper.
That would not be an honest family *from this paper*.

No generator module was built, so there is no module to retain or hardening evidence
to run. This is a STEP 0 rejection, not a `cap_bound` outcome and not a G9 rejection.
