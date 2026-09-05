# arXiv 2506.10471 — induced octahedron packing

Trust status: the generator and all local G1–G9(c) checks pass, but the required
multi-vendor oracle run is **not yet evidence of hardness**.  OpenRouter returned
HTTP 403 `Key limit exceeded (total limit)` on every redraw, so there were zero
scored oracle attempts.  The script-owned error transcripts are retained and the
module must be rerun with funded OpenRouter access before submission.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (a set partition into six-vertex blocks) |
| Intended intuition | decomposition: recognize the overlap tree and its private leaf vertices |
| Domain essentiality | native |
| Reduction | none |

## Problem and provenance

The solver receives a plane triangulation as an undirected edge list and must
find a prescribed number of pairwise vertex-disjoint induced octahedra.  A
six-set is an octahedron exactly when every one of its vertices has induced
degree four, so verification is just range/disjointness checks and exact edge
lookups.  This uses the paper's own graph objects, not a surrogate.

The source is Enami, Matsumoto, and Yashima,
[“Contributions to conjectures on planar graphs: Induced Subgraphs, Treewidth,
and Dominating Sets”](https://arxiv.org/abs/2506.10471), version 4.  Section 2
fixes the graph terminology.  Section 8 constructs `G_k` and `G'_k` by inserting
octahedral triangulations into triangular faces; Observation 17 decomposes the
result into vertex-disjoint octahedra.  This generator first samples a finite
pruning of that insertion tree, then applies a random vertex relabelling.  It
also adds distractor units in distinct remaining faces: a first stacked vertex
is raised to degree four by stacking a degree-three satellite into one of its
new faces.  Face stacking preserves planarity and triangulation.  The
degree-four center cannot lie in an octahedron because all four of its neighbors
would have to be present, including its degree-three satellite.  The planted
core blocks are therefore known before the public graph is built.

## Why Track B

This paper does not prove search hardness for its decomposition, so Track A
would be unjustified.  An efficient distribution-specific method exists: for
each nonedge, intersect the endpoint neighborhoods, test four-subsets, and pass
the resulting six-sets to minimum-column Algorithm X.  Candidate enumeration is
`O(N^2 Delta^4)`; on this generated overlap tree the exact-cover search is
forced and linear after enumeration.  At the hard shipping preset it took
0.038 seconds, 73,536 vertex-pair checks, 72,390 common-neighborhood
intersections, 237 four-set tests, and 41 search nodes (146,204 counted
operations), and solved an independent 8/8 audit.

The compact route is different in scale: the candidate octahedra consist of
disjoint core blocks and interfaces overlapping adjacent cores.  Private
vertices at leaves force the core choice recursively.  At hard this is at most
`2b-1 = 79` block eliminations, compared with 146,204 mechanical operations.
The construction's easy regime is precisely when the insertion order, core
blocks, or candidate-overlap tree is exposed; the module hides all three by
relabeling and supplies only the graph.  Theorem 9's unique coloring of
`k`-trees was considered and rejected as a family because ordinary greedy
coloring would be both the mechanical and compact route.

## Worked demo

With `make_instance(n=2, decoys=0, seed=0)`, the full rendered data are:

```text
N = 12, b = 2
Edges (30):
0-2 0-3 0-6 0-8 1-4 1-5 1-10 1-11 2-3 2-5 2-6 2-7 2-9
3-5 3-8 3-9 3-11 4-7 4-10 4-11 5-7 5-10 5-11 6-8 6-9
7-9 7-10 7-11 8-9 9-11
```

The answer is
`[[0,2,3,6,8,9],[1,4,5,7,10,11]]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the last
entry of the first block returns `(False, "block_size")`.  A person can solve
this demo on paper by testing the three octahedron candidates and taking the
two disjoint ones (there are 462 shape-valid two-block partitions in total).

## Difficulty presets

| Preset | Core blocks `b` | Distractor units | Vertices | Edges | Answer atoms | Ships? |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 0 | 12 | 30 | 12 | no; hand example |
| easy | 30 | 60 | 300 | 894 | 180 | oracle not scored |
| medium | 35 | 100 | 410 | 1,224 | 210 | not reached |
| hard | 40 | 144 | 528 | 1,578 | 240 | configured shipping preset |

No preset was rejected by a local gate.  `escalate()` first adds facial decoys
at fixed answer length; only after that axis is exhausted may it raise `b` to
42 (252 answer atoms), after which it returns `cap_bound`.

## Gate results

| Gate | Result at hard |
|---|---|
| G1 | 12/12 preset-seed constructions verify; answers JSON-round-trip |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | prose + fenced tagged answer round-trips |
| G4 | 0/200,000 guesses over 384 degree-eligible vertices; candidate space about `10^415` |
| G5 | exactly 1 valid semantic answer at demo and hard; reference 146,204 ops / 0.038 s |
| G6 | degree grouping, two greedy packers, and 256 random restarts: all 0/8; reference 8/8 |
| G7 | doubled build has 1,056 vertices and verifies |
| G8 | relabel/reorder invariance 20/20, carried witnesses 20/20, unrelated keys 20/20 distinct |
| G9(c) | 996 chars, 249 estimated tokens, 240 atoms, 79 intended operations |

## Oracle and G9 diagnostics

| Arm | Scored solved/attempts | Script calls | Outcome |
|---|---:|---:|---|
| bare | 0/0 | 4 | every call HTTP 403 key-limit error at easy |
| structural hint | 0/0 | 4 | every call HTTP 403 key-limit error at hard |
| placebo hint | 0/0 | 4 | every call HTTP 403 key-limit error at hard |

Thus `hinted - placebo` is unavailable, not evidence of a zero effect.  The
structural hint names only the private-leaf invariant and does not give the
propagation procedure.  The G9 size and intended-route caps pass.  Once quota
is restored, rerun all three arms; the bare verdict must determine the actual
shipping rung, and this table plus `G9_ORACLE_RESULTS` must be updated.

## Use

```python
import random
import gen_2506_10471 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) > 10**6
```

From the repository root, emit only after a successful oracle rerun:

```bash
bash scripts/emit.sh 2506.10471 20
```

## Caveats

- The external H evidence is presently missing; the retained error transcripts
  must not be read as model failures.
- The G4 prior is uniform over all disjoint unordered six-set packings.  It
  measures blind guessing after enforcing shape and disjointness, not a solver
  that enumerates induced octahedra.  The reference algorithm shows that the
  latter prior collapses the task quickly with tools.
- Degree-three satellites are freely discardable, so `random_candidate` does
  discard them.  It retains their degree-four centers, which share the obvious
  degree eligibility of many planted vertices but fail the local octahedron
  test.  A specialist's candidate enumeration still removes them quickly; the
  meaningful insight is the overlap-tree decomposition, not the noise.
- The four recorded attacks do not include ILP/CP-SAT implementations or a
  planar-embedding canonicalizer.  Algorithm X is the relevant standard exact
  cover attack and succeeds as expected for Track B.
- `canonical_key` combines the exact quotient-tree code with a 1-WL graph
  fingerprint.  It passed all required relabellings and 20 unrelated instances,
  but 1-WL is not a complete graph-isomorphism test and could over-collapse a
  rare pair.  It never uses the seed, rendering, or planted answer.
