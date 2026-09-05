# Rejection: arXiv 1210.7684

Paper: Babak Farzad and Majid Karimi, [*Square-Root Finding Problem In
Graphs, A Complete Dichotomy Theorem*](https://arxiv.org/abs/1210.7684).

## Decision

No generator is shipped. The proposed families pass **G** (the root or truth
assignment is sampled first) and **V** (square the proposed root and compare
edge sets, or check every exact-one clause), but fail **H**. They fail Track A
empirically on the paper-licensed reduction distribution, and the alternatives
do not have the mechanical-versus-compact gap required for Track B.

The precise native problem is the one stated in Section 3: given a finite,
simple, undirected graph `G`, find a graph `H` on the same vertices such that
distinct vertices are adjacent in `G` exactly when their distance in `H` is one
or two, with `H` of girth at least five. Theorem 3 proves this recognition
problem NP-complete. Theorem 4 gives the girth dichotomy. The important easy
side is stated in the Introduction/Table 1 and discussed at the end of Section
2: roots of girth at least six can be reconstructed in
`O(|V| |E|)` time. Thus merely sampling a sparse random root is not covered by
the hard theorem; such samples often lie in, or remain locally close to, the
paper's reconstructible regime.

## Candidate 1: inverse-generate a root and square it

The prior-triage proposal sampled a hidden girth-five graph `H` and emitted
`G = H^2`. This is valid inverse generation, and verification is exact and
polynomial. It is not a Track A family: Theorem 3 is a worst-case result proved
through the special Section 3 gadgets, and says nothing about the distribution
of squares of random roots. Conditioning a random sparse graph to contain a
5-cycle does not put that distribution in the reduction's hard regime. The
paper itself explains why the known-neighbourhood reconstruction works at
girth six, so isolated planted 5-cycles are particularly weak evidence of
distributional hardness.

There is also no honest Track B claim here. For a genuinely random hidden root
there is no compact invariant supplied by the construction; the compact route
is just the general recovery search. Hence this candidate has neither a
distributional Track A basis nor a short Track B route.

## Candidate 2: use the Section 3 reduction

Section 3 reduces **Positive and Minimum Intersecting 1-in-3 SAT** (Theorem 2)
to girth-five square root (Lemma 3). I tested the natural scalable inverse
generator for that proof: choose a truth set first; construct a linear
3-uniform exact-one instance; make every variable have the same degree; and
randomize it by degree-preserving endpoint switches. The equal degrees remove
the construction's most obvious occurrence-count outlier, and the linearity
condition is exactly the paper's requirement that two clauses share at most
one variable.

This distribution fails the standard attack decisively. An exact-one DPLL
solver with unit propagation and a maximum-unresolved-occurrence branching
rule was run on 36 instances:

| variables | regular degrees tested | seeds per setting | solved |
|---:|---:|---:|---:|
| 45 | 3, 4, 5, 6 | 3 | 12/12 |
| 90 | 3, 4, 5, 6 | 3 | 12/12 |
| 135 | 3, 4, 5, 6 | 3 | 12/12 |
| **total** |  |  | **36/36** |

The maximum observed search was **64 branch nodes** and **0.102 seconds**.
This is the domain-standard algorithm required by G6, so a Track A adversary
panel would record successes rather than the required zero successes. Mapping
these formulas through Lemma 3 only wraps the same easy search in graph
gadgets; the lemma is an equivalence, not a distributional hardening theorem.

For Track B, the mechanical cost is therefore at most the measured 64 DPLL
nodes (under 0.102 seconds) on the largest tested instances. There is no
shorter hidden route after the endpoint switches: the planted assignment has
no retained symbolic description. In the unswitched algebraic seed, recovering
the three incidence classes is itself the direct solution and takes a linear
scan, comparable to DPLL. Thus the compact route is either absent or the same
order as the mechanical route; there is no million-operation versus dozen-step
compression to test.

## Candidate 3: compose the Section 2 twin-root gadgets

Section 2 and Observation 1 compose copies of the 16-vertex graphs
`G1`/`G2`, whose squares coincide. This is theorem-backed and has exact root
certificates. It is not hard:

- If the certificate records only the `G1`/`G2` choice in each exposed block,
  every choice is valid, so a structure-aware random candidate succeeds with
  probability 1.
- If the blocks are relabelled and the certificate must recover each block
  isomorphism, the square gadget is separated completely by one round of
  1-dimensional color refinement: starting from degree, the multiset of
  neighbour degrees gives **16 singleton color classes**. The measured
  mechanical cost is at most `16^2 = 256` neighbour-color inspections per
  block. The compact route is exactly those same signatures, also about 256
  inspections per block. One block is therefore comparable rather than
  compressed; composing blocks merely multiplies both costs and soon violates
  the 300-operation intended-route cap.

This rules out Track B for the explicit many-roots construction as well.

## Gate accounting

| gate | result | reason |
|---|---|---|
| G | pass in principle | inverse generation and Lemma 3 both carry a known witness |
| V | pass in principle | exact graph squaring/girth checking or exact-one clause evaluation |
| H, Track A | **fail** | domain-standard DPLL solved 36/36 planted reduction instances |
| H, Track B | **fail** | 64-node DPLL has no shorter retained route; the explicit gadget costs 256 inspections both mechanically and compactly |

No module was written, so there is no partially built generator to retain.
