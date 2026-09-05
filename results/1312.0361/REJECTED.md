# Rejected at Step 0: arXiv 1312.0361

Paper: Louis-Hadrien Robert, [*On edge-colorings of planar bicubic
graphs*](https://arxiv.org/abs/1312.0361) (2013).

## Decision

No problem generator is shipped.  The proposed family—construct a properly
3-edge-colored web, erase the colors, and ask for a coloring—passes **G** by
inverse generation and **V** by a linear exact check, but fails **H on Track A**.
Every graph in the paper's native regime is cubic and bipartite, so a standard
bipartite perfect-matching algorithm constructs the requested certificate in
polynomial time on every generated instance, independently of how the coloring
was planted.

I also considered **Track B** before rejecting it.  At the largest natural
full-coloring size allowed by the 256-atom answer cap, the mechanical matching
route takes only about two thousand elementary edge inspections and the compact
route is no shorter in kind: it must recover the same perfect matching and emit
one color for almost every edge.  There is no million-operation-versus-dozens
compression gap, no hidden invariant that replaces the matching computation,
and a structured construction that did expose such an invariant would make the
answer an ordinary linear scan of that construction.  Failures at this scale
would primarily measure bookkeeping and transcription.

Because H fails analytically before Step 1, I did not create a module,
`selftest_report.json`, or oracle transcripts.  No generator reached the stage
at which the retention rule applies.

## What the paper actually studies

Section 1, Definition 1.1 defines a closed web as a plane-embedded, oriented,
3-regular multigraph (also allowing vertexless circles) in which every vertex is
a source or a sink.  Remark 1.2 says explicitly that the orientation condition
is equivalent to bipartiteness.  Section 1, Definition 1.9 defines a coloring as
a map from edges to the three colors such that adjacent edges have different
colors.

The first main result, Theorem 1.11, concerns the **colored Kuperberg bracket**:
the Laurent polynomial obtained by summing `q` to a degree over all colorings.
It gives circle, digon, and square relations.  Proposition 1.3 proves that every
closed web contains one of those three local configurations, so the relations
give an explicit recursive computation.

Section 2 defines a Kempe (`tau`) move by swapping two colors around a bicolored
cycle.  Theorem 2.14 proves, by induction using Proposition 1.3, that all
colorings of a closed web are Kempe-equivalent.  This is a connectivity theorem
about colorings already in hand; it is not an average-case hardness theorem for
recovering an erased coloring.

## The certificate-producing algorithm

For a cubic bipartite graph `G=(L,R,E)`, regularity and Hall's condition guarantee
a perfect matching `M`.  Find `M` with Hopcroft--Karp.  Removing `M` leaves a
2-regular bipartite graph, hence a disjoint union of even cycles.  Give every
edge of `M` the first color and alternate the other two colors around each
remaining cycle.  This outputs a proper 3-edge-coloring.

The mechanical complexity is

`O(|E| sqrt(|V|)) + O(|E|)`

and verification is `O(|E|+|V|)`: check that the submitted color of every edge
is in `{0,1,2}` and that the three incident edges at every vertex have distinct
colors.  Planarity and the paper's local reductions are not needed by this
algorithm; bipartiteness alone is enough.

## Required mechanical-cost / compact-route comparison

A full coloring uses one answer atom per edge.  Cubicity gives
`|E|=3|V|/2`, so the largest convenient instance below the 256-atom cap has 168
vertices and 252 edges.  I benchmarked 1,000 independently relabeled and
edge-order-shuffled copies of the planar bipartite prism `C_84 x K_2`.  A
standard-library Hopcroft--Karp implementation followed by even-cycle
alternation used:

| measurement | result |
|---|---:|
| vertices / edges | 168 / 252 |
| elementary edge inspections and color assignments | min 1,833; median **1,922**; max 2,486 |
| wall time per solve | min 0.000174 s; median **0.000193 s**; max 0.001207 s |
| successful solves | 1,000 / 1,000 |

The benchmark deliberately randomized labels and input order; it did not hand
the solver the planted colors.  The asymptotic guarantee, rather than this easy
prism distribution, is the decisive Track A obstruction.

For Track B, an arbitrary planted web has no construction-independent compact
route other than finding a perfect matching and alternating the residual
cycles—the mechanical algorithm above.  If the generator instead uses a
recognizable prism or face-expansion pattern, recognizing and traversing that
pattern is still linear in the displayed graph, and writing the required full
certificate alone takes **252 color assignments**.  Thus the comparison is
about 1,922 mechanical operations versus at least 252 output assignments plus a
linear structural scan, not a costly mechanical computation versus a short
by-hand invariant.  Both routes are the same order and both are bounded by the
small writable instance.  Encoding only one perfect matching would reduce the
answer to 84 edge indices, but Hopcroft--Karp directly produces exactly that
object; it does not create a new shortcut.

## Why obvious alternatives do not rescue the paper

| native candidate | gate that fails | reason |
|---|---|---|
| Find any proper 3-edge-coloring | **H, Tracks A and B** | Bipartite matching constructs it in polynomial time; the compact and mechanical routes are the same decomposition. |
| Find one color class / perfect matching | **H, Tracks A and B** | This is exactly the output of Hopcroft--Karp, not a route around it. |
| Compute the degree of a supplied coloring | **H, Tracks A and B** | Definitions 1.4--1.10 reduce it to finding bicolored cycles and summing their orientations, a linear traversal with no separate compressed insight. |
| Output the colored Kuperberg bracket | **V, or G9(c)** | A bare polynomial is not cheaply checkable without recomputing the coloring sum.  A complete local-reduction tree makes verification executable but may branch exponentially at squares and exceed the witness cap; restricting to short, planted reduction trees makes the instance mechanically easy. |
| Give a Kempe path between two supplied colorings | **H unsupported on Track A; no Track B gap** | Theorem 2.14 is constructive by circle/digon/square induction.  Inverse-planting a path proves G, not hardness of the resulting distribution, and the paper gives no hard parameter regime. |
| Ask for the number of colorings | **witness/verification mismatch** | Theorem 1.11 gives a recursive evaluation, but an asserted count or polynomial is not a locally inspectable certificate unless the reduction computation is included. |

The paper contains no NP-hardness, average-case hardness, FPT barrier, or hard
parameter regime.  Its two contributions are exact local identities and
connectivity of the coloring space.  Adding precolored-edge extension
constraints, SAT gadgets, or a non-bipartite surrogate could create a different
hard problem, but none is central to this paper and doing so would discard the
native web-coloring problem.

## Gate diagnosis

| requirement | result |
|---|---|
| G — certificate known by construction | **Passes in isolation:** sample a coloring first and build a plane cubic bipartite web around it. |
| V — exact witness verification | **Passes in isolation:** one linear incidence scan checks all three colors at every vertex. |
| H — Track A structural hardness | **Fails:** perfect matching plus cycle alternation solves every instance in `O(|E| sqrt(|V|))`. |
| H — Track B no-tool compression | **Fails:** 1,922 median mechanical operations versus a linear scan and at least 252 emitted colors at the largest writable natural size; there is no short distinct route. |
| Overall | **Rejected at Step 0.** |

This is not a `cap_bound` result: the answer fits at 252 atoms.  The cap merely
makes the Track B comparison especially clear.  Enlarging the graph while
compressing the answer would change the certificate language, but it would not
remove the polynomial matching algorithm or introduce a paper-backed compact
route.
