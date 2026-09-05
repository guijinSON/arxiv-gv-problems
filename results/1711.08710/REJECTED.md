# Rejected at Step 0: the hardness reduction does not make inverse-planted instances hard

Paper: François Dross and Pascal Ochem, [*Vertex partitions of
$(C_3,C_4,C_6)$-free planar graphs*](https://arxiv.org/abs/1711.08710),
arXiv:1711.08710.

## Decision

No generator is shipped.  The proposed family—generate a graph together with a
planted valid vertex partition—passes **G** by inverse generation and **V** by
direct edge inspection, but it does not pass **H on Track A**.  The paper proves
worst-case NP-completeness by a reduction from another NP-complete graph class;
it makes no average-case claim about answer-first graphs.  The constructions for
which the certificate is available without solving (trees, bipartite graphs,
cacti, and relabelled copies of the displayed obstruction) all have an ordinary
linear-time or fixed-pattern recovery route.

They do not become a Track-B family either: for the positive constructions the
mechanical algorithm and the compact route are the same propagation, while for
the negative construction the four high-degree core vertices of a fixed gadget
are found by the same scan needed to read the instance.  There is no large
mechanical-versus-compact gap.

This is a Step-0 rejection.  In accordance with the task, there is intentionally
no `gen_1711_08710.py`, `selftest_report.json`, README, or oracle transcript.

## Exact problem and the easy regime

Section 1 defines a `(k1,k2)`-colouring as a partition of the graph's entire
vertex set into two induced subgraphs of maximum degrees at most `k1` and `k2`.
Therefore, in a `(0,k)`-colouring, the vertices coloured `0` must be an
independent set and every vertex coloured `k` may have at most `k` neighbours
also coloured `k`.  This is the native graph object; no SAT or finite-field
surrogate is needed to state or check it.

Theorem 1 is the result that makes the tempting positive family easy in the
decision sense: every planar graph with no cycles of lengths 3, 4, or 6 is
`(0,6)`-colourable.  Its Section 2 proof is a minimal-counterexample/discharging
argument.  It establishes existence; it does not output a colouring of an input
graph, and the recursive recolouring argument in Section 2 is not presented as
an efficient certificate-producing algorithm.  Consequently Theorem 1 by
itself is not a theorem-backed generator under G: the finite witness is still a
partition, and the proof does not hand the generator that partition.

Inverse generation can of course supply one, but then hardness must be shown
for the generated distribution.  The theorem does not do that.

## What the NP-completeness theorem actually supplies

Theorem 2 says that for fixed `k`, either every graph in this class is
`(0,k)`-colourable or deciding `(0,k)`-colourability in the class is
NP-complete.  Section 4 displays a graph that is not `(0,3)`-colourable, so the
following corollary gives NP-completeness for `k=3`.

The parameter regime is therefore exact and useful—`k=3`, planar, and no
`C3`, `C4`, or `C6`—but the proof of Theorem 2 matters.  Section 3 starts with
an arbitrary instance `G` of the NP-complete problem

> `(0,1)`-colourability of planar graphs of girth at least 9,

and attaches `k-1` copies of a forcing graph `H'_k` at every source vertex.  It
proves `G` is `(0,1)`-colourable exactly when the resulting `G'` is
`(0,k)`-colourable.  Thus the reduction preserves the difficulty of its source
instance; it does not generate that source instance, and it says nothing about
the distribution obtained by first choosing a source colouring and drawing a
graph around it.

This answers the Step-0 certificate question.  Given a source colouring, the
certificate for a yes-instance is produced by extending it through the fixed
attachments, with work linear in the expanded graph.  Without a source
colouring, the algorithm producing the certificate is precisely a solver for
the NP-complete source problem.  Sampling the source certificate first clears
G but leaves H unsupported.

There is also a practical obstacle to treating the reduction as an executable
generator from this paper alone.  `H'_k` is defined from a graph `H_k` chosen
minimal under the paper's partial order.  Section 4 draws a non-colourable graph
for `k=3`, but the paper neither lists a minimal subgraph nor gives a machine
readable adjacency table and extension colouring for the derived `H'_3`.
Those data could be obtained once by minimisation and then hard-coded as a
known base instance, but that would add an offline solve not supplied by the
paper.  More importantly, it would not fix the distributional-H problem below.

## Measured failure of the natural inverse construction

The simplest structure-preserving inverse generator uses a randomly relabelled
tree and takes its bipartition as the `(0,3)` certificate.  Trees are planar and
have no cycles at all, so they satisfy the paper's exact forbidden-cycle
condition.  This is not a deliberately weak verifier: any valid partition is
checked by testing every edge for two `0` endpoints and counting same-colour
degree at every `3` vertex.

I measured the obvious breadth-first bipartition attack on seeds 0 through 19
at each size.  For each seed, `random.Random(seed)` chose the parent of vertex
`v` uniformly from `0,...,v-1`, followed by an independent vertex relabelling.
The operation counter includes
building both adjacency directions, inspecting both directions during BFS,
and assigning each vertex once.

| vertices | attack successes | exact counted operations | median CPython time |
|---:|---:|---:|---:|
| 64 | 20/20 | 316 | 0.0000164 s |
| 128 | 20/20 | 636 | 0.0000346 s |
| 256 | 20/20 | 1,276 | 0.0000690 s |

The returned bipartition verifies as a `(0,3)`-colouring on every run.  The
same failure persists for the other immediately certifiable planar
constructions: a bipartite graph is solved by component propagation, and a
cactus or bounded-width assembly is solved by linear dynamic programming.
Random relabelling hides none of this structure.

A tiny probability for guessing a full 256-entry colour vector would not fix
the failure.  It would only show that uniform guessing is poor; it would not
contradict the measured linear recovery algorithm.

## Why the displayed negative certificate is not a hard family

Section 4 gives an exact, finite refutation of `(0,3)`-colourability.  Its
forcing graph `F_{x,y}` has the property that if every neighbour of `x` and `y`
is coloured `0`, then eight designated vertices are already coloured `3` and
have two `3`-neighbours each.  Nine adjacent pairs force one of those eight
vertices to receive two more `3`-neighbours, a pigeonhole contradiction.

The outer graph has two ordinary edges and seven copies of `F_{x,y}` between
each relevant pair of endpoints.  An endpoint of each ordinary edge is
coloured `3`; because each such endpoint has at most three `3`-neighbours, two
sets of at least four of the seven copies overlap, invoking the inner
contradiction.  This is a valid bounded refutation certificate.

It still fails H:

- The graph in Figure 3 is one fixed obstruction.  Relabelling it produces the
  same instance under `canonical_key`, so relabellings do not provide an
  unlimited diverse family.
- Adding trees or unrelated planar components preserves non-colourability, but
  the fixed obstruction remains a fixed-pattern subgraph.  Its four outer
  vertices are conspicuous degree outliers and the attached copies are
  connected fixed-size patterns.  A degree scan followed by fixed-pattern
  matching produces the certificate in `O(|V|+|E|)` on these decorated copies.
- Hiding one intact obstruction among many near-copies would make the solver
  scan the near-copies too.  It offers no compact route shorter than that scan,
  so it tests input inspection, not the paper's pigeonhole insight.  Encoding a
  checksum or secret permutation key to reveal the intact copy would test the
  added encoding rather than this paper.

## Track-B audit: mechanical cost versus compact route

The two plausible Track-B candidates have no useful compression gap.

| candidate | mechanical certificate algorithm | mechanical cost at 256 vertices | compact route |
|---|---|---:|---:|
| planted tree/bipartite yes-instance | BFS bipartition | 1,276 counted operations, 0.0000690 s median | the same parity propagation, plus writing 256 colour atoms |
| fixed Section-4 no-instance | degree scan and fixed-gadget recognition | linear in the displayed graph | the same scan to locate the four core vertices, followed by the constant pigeonhole argument |

For the first row, even a solver handed the bipartition rule must emit 256
colour atoms, so the compact route is not meaningfully shorter than the 1,276
operation mechanical route.  For the second, the logical contradiction is
short, but locating its core is already what the polynomial pattern recognizer
does; exposing the core makes the answer a lookup.  Neither is the million-to-a-
dozen compression required for a defensible no-tool benchmark.

The generic NP-complete regime does have expensive worst cases, but no efficient
algorithm is being concealed: the missing ingredient is a scalable,
certificate-known **distribution** in that regime.  The paper supplies a
hardness-preserving reduction, not such a distribution and not a compact
decoding invariant.

## Gate outcome

| requirement | outcome |
|---|---|
| G — inverse-planted positive partition | Passes. |
| V — positive partition | Passes in `O(|V|+|E|)` by exact adjacency and induced-degree checks. |
| G/V — displayed negative obstruction | Passes as a bounded counting refutation. |
| H — Track A | **Fails:** Corollary 3 is worst-case; it does not cover the answer-first distribution, and the natural certified distribution is solved 20/20 by BFS. |
| H — Track B | **Fails:** 1,276 mechanical operations versus at least 256 output steps for the positive route; fixed-pattern scan versus the same core recognition for the negative route. |
| Paper-licensed NP-hard reduction | Does not repair G+H together: it assumes a hard source instance, while inverse-planting a source witness loses the theorem's hardness guarantee. |
| Steps 1–4 | Not run, as required after the Step-0 H failure. |

The rejection is therefore about the proposed generator, not about witness
verification and not about the paper's worst-case theorem.  Shipping a planted
partition merely because the surrounding decision problem is NP-complete would
make exactly the distributional-hardness error the task warns against.
