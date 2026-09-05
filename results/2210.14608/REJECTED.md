# Rejected: arXiv:2210.14608

## Decision

This paper clears **G** and **V**, but I could not obtain a family that clears
**H**.  The failure is specifically **H on Track A**: Theorem 1 is a worst-case
promise-problem result and does not establish hardness for a distribution from
which a Hamiltonian cycle, and hence the promised two-step path, can be sampled
with a held certificate.  I also considered **Track B** before rejecting it.  In
the faithful certificate-known specializations below, the mechanical route and
the compact route have the same linear size, so there is no no-tool compression
gap to test.

Paper: Jean Cardinal and Raphael Steiner, [*Inapproximability of shortest paths
on perfect matching polytopes*](https://arxiv.org/abs/2210.14608).

## Exact object and witness

Section 1.1 and Lemma 1 fix the native problem.  A vertex of the perfect matching
polytope of a bipartite graph is a perfect matching.  Two such vertices are
adjacent exactly when their symmetric difference is one cycle.  Theorem 1 asks,
for a maximum-degree-three bipartite graph and two perfect matchings promised to
be at distance at most two, for a path of at most a fixed `k >= 2` such flips.
The ETH statement allows
`k = floor((1/4-delta) log N / log log N)`.

G is available in Section 2.2.  Start with a Hamiltonian digraph `D` and a held
Hamiltonian cycle `H`.  The paper replaces every vertex by split incoming and
outgoing trees and a directed 4-cycle.  Its initial orientation is a perfect
matching `M1`; reversing every gadget 4-cycle gives `M2`.  The held cycle `H`
lifts to one directed cycle through the gadgets, and its reverse with the other
three sides of every gadget gives a second cycle.  Flipping those two cycles
carries `M1` to `M2`.  Thus this is theorem-backed generation when `H` is known
before the matching instance is assembled; it does not solve the completed
instance.

V is also straightforward and exact.  Replay each proposed flip, check that its
edge set is one alternating cycle, check that the resulting edge set is a
perfect matching, and compare the final matching with `M2`.  No numerical
approximation or oracle is involved.

## Why Track A is not supported

Theorem 1 derives hardness from Theorem 2's task of finding a long directed
cycle in an *arbitrary promised Hamiltonian digraph*.  The promise supplies
existence, not a samplable Hamiltonian-cycle certificate, and Section 2.2 gives
no distributional statement about planted Hamiltonian digraphs.  Sampling `H`
first and adding random arcs changes the distribution to one not covered by the
theorem.  Worst-case NP-hardness therefore cannot justify the required claim
that this generated distribution has no efficient general method.

The most literal certificate-known family is the cycle-ladder/transition
specialization illustrated by Figures 1 and 4: pair the occurrences of a held
cycle and allow the two transitions at each pair.  Its apparent exponential
set of transition choices is the line/transition representation of an Eulerian
multigraph.  Contracting the paired ports and running Hierholzer's algorithm
recovers a Hamiltonian source cycle, after which Section 2.2 writes the two
flips.  That is a linear-time domain attack, not a hard Track A distribution.
Random regular planted-cycle variants do not repair the logical gap: the paper
proves no average-case or planted-distribution theorem for them, and screening
until a bounded backtracker times out would establish only resistance to that
one cutoff.

## Track B cost comparison

I quantified the largest literal specialization that keeps the natural source
cycle within the 256-atom answer cap: 120 source vertices (and 960 vertices in
the degree-two specialization of the Section 2.2 gadget, eight gadget vertices
per source vertex).

| route | exact work at that size |
|---|---:|
| mechanical port contraction plus Hierholzer traversal | at most 240 transition-arc inspections plus 120 tour emissions |
| compact route after recognizing the transition representation | the same 120 tour emissions |
| expansion to the two matching-polytope flips | 14 source-gadget arc emissions, or 1,680 emissions, on either route |

Both routes are `O(n)` and both must write or expand the same `n`-vertex source
cycle.  The shortcut saves at most one small linear scan; it does not replace a
million-operation mechanical computation by a short invariant calculation.
Growing `n` enough to manufacture such a gap only lengthens the native cycle
witness beyond the 256-atom G9(c) cap.  A succinct algebraic program for a huge
cycle would avoid the cap, but succinct graph/cycle programs are not objects or
a reduction used in this paper; adding one would turn the result into a
benchmark-convenience analogue whose difficulty comes from the added encoding.

Consequently this is not merely “an efficient algorithm exists.”  The measured
mechanical cost and the compact route are comparable, so the natural family
also fails **H on Track B**.  There is no module to retain: the rejection was
made at Step 0, before implementing a generator.

## What would reopen the paper

A reviewable reopening would need either (1) a theorem-backed, samplable
distribution of Hamiltonian digraphs with a carried cycle and evidence that the
paper's standard search attacks fail on that distribution, or (2) a native
bounded symbolic encoding of the two flips, licensed by the paper, for which an
efficient mechanical algorithm has a genuinely large measured cost and a
sub-300-operation structural shortcut.  The paper supplies neither.
