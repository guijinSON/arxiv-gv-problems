# Distance-two coloring generator for arXiv:2403.12302

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | vertex-color array (`integer_tuple`) |
| Intended intuition | invariant: a collision-free mod-7 functional on triangular-lattice directions |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The solver receives a simple planar graph of maximum degree 6, an exact
integer straight-line embedding, and the palette `1..19`.  It must color every
vertex so that vertices joined by a path of one or two edges have different
colors.  The answer is the color array in vertex-ID order.  `verify` checks the
array shape and palette and scans every distance-one and distance-two pair; it
accepts any valid coloring and never reads the planted answer.

This is the native problem of Deniz, [*A 2-distance
$(2\Delta+7)$-coloring of planar graphs*](https://arxiv.org/abs/2403.12302).
Section 1 gives the exact definition and Theorem 1.2 proves the bound for every
simple planar graph.  The start of Section 2 says earlier results cover
`Delta <= 5` and `Delta >= 9`; the paper's new work is therefore the
`Delta in {6,7,8}` regime.  These instances use `Delta=6`, hence 19 colors.
Remark 2.1 supplies the deletion-and-extension principle, Lemma 2.2 bounds a
two-neighborhood, and Sections 2.1--2.3 finish the three remaining degree
cases with reducible configurations and discharging.

Generation does not solve an emitted graph.  Begin with a connected irregular
induced patch of the triangular lattice.  For its three edge directions
`(1,0)`, `(0,1)`, `(1,-1)`, the value `x+3y mod 7` is nonzero on every one of
the 18 nonzero displacements possible in at most two steps.  It is therefore a
seven-color certificate.  The generator carries it through a random lattice
symmetry, large unimodular shears, vertex relabeling, and edge reordering.

## Why Track B

The paper proves existence, not average-case or distributional hardness, so a
Track A claim would be unsupported.  An efficient algorithm is explicitly
disclosed here: construct the square graph and apply first-fit coloring.  A
triangular-lattice vertex has at most 18 vertices within two steps, so 19
colors guarantee success in every public vertex order.  The implementation is
`O(n*Delta^2+n*q)`; on eight hard instances it averaged **8,792 counted
set/color operations**.  The latest builder run measured 0.004574 s mean and
0.010892 s maximum; the stable operation count is the
hardware-independent Track B cost signal.

The compact route notices the three opposite edge-displacement pairs, gives a
lattice basis mod-7 increments 1 and 3, and carries the resulting increment
along a spanning tree.  At the hard preset that costs 119 modular updates plus
19 setup/direction checks, **138 exact operations**.  The benchmark asks a
no-tool model to find that compression in a shuffled 120-vertex instance; it
does not pretend graph-square greedy coloring is hard with software.

## Worked demo

The complete `demo`, seed 0, is genuinely hand-solvable.  Vertex 6 is adjacent
to the other six and those six form a cycle, so every pair of vertices is at
distance at most two; any seven distinct colors work.

```text
Distance-two coloring of a planar graph

The graph is finite, simple, and undirected.  Its vertices are the integers
0 through 6; vertex numbering is 0-based.  An edge u-v is unordered.
The graph distance between two vertices is the minimum number of edges in a
path joining them.  A distance-two coloring assigns a color to every vertex
so that any two distinct vertices at graph distance 1 or 2 have different
colors.  Equivalently, adjacent vertices and vertices sharing a common
neighbor must receive different colors.

This planar graph has maximum degree Delta=6.  You may use the 2*Delta+7=19
colors numbered 1 through 19, both endpoints included.  Colors may be reused,
not every color has to be used, and color names have no meaning beyond their
integers.

The following integer coordinates give a straight-line planar embedding.
Graph distance is determined only by the edge list, not by Euclidean distance.
Coordinates are listed as vertex:(x,y):
  0:(589544,866976)   1:(589544,866977)   2:(589546,866975)   3:(589545,866975)
  4:(589546,866976)   5:(589545,866977)   6:(589545,866976)

There are 12 edges:
  2-3 4-6 2-6 1-6 5-6 4-5 0-3 1-5 2-4 0-6
  0-1 3-6

Return exactly 7 integers [c_0,...,c_6] in vertex-ID order, where c_v
is the color of vertex v.  Order matters, repetitions are allowed, and no
vertex may be omitted.

Give your final answer inside <answer></answer> tags as one JSON array of
integers.  Example format only: <answer>[1,2,3]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>[6,5,4,2,3,7,1]</answer>`.
`verify(inst, [6,5,4,2,3,7,1])` returns `(True, "ok")`; deleting the last
entry returns `(False, "too few colors: expected 7, got 6")`.

## Difficulty presets

| preset | vertices | shear steps | growth bias | status |
|---|---:|---:|---:|---|
| demo | 7 | 0 | 1 | hand example; skipped by hardening |
| easy | 48 | 2 | 1 | first oracle rung |
| medium | 84 | 4 | 2 | local gates pass |
| hard | 120 | 6 | 3 | shipping preset; local gates pass, full oracle verdict blocked |

`escalate()` first raises coordinate camouflage and constraint crowding at a
fixed 120-entry answer.  Only after those axes are exhausted does it lengthen
the patch, up to 240 vertices; a further increase returns `cap_bound` because
the 256-atom answer limit becomes binding.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses, deterministic rebuilds, paper-regime checks, and exact planar embeddings pass |
| G2 | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | prose/fence/JSON round-trip passes, garbage is rejected, answer is JSON-native |
| G4 | 0 hits in 200,000 structure-aware samples; space size `P(19,7)*19^113` |
| G5 | hard density 0/200,000; reference 8,891 operations and 0.012303 s on the reporting seed |
| G6 | five attacks at 0/8 each; reference greedy algorithm 8/8 as expected |
| G7 | 240-vertex instance builds and verifies; search-space bits grow 508 to 1018 |
| G8 | 140/140 invariance checks, 140/140 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 360 characters, about 90 tokens, 120 atoms, 138 intended operations |

## Oracle loop and G9 arms

The required bare, structural-hint, and placebo harnesses were invoked in
separate directories against the current module.  The latest bare run obtained
one genuine Gemini response at `easy`; its parsed coloring failed verification.
The key then reached its OpenRouter total limit, and four Terra redraws returned
HTTP 403.  Earlier hinted and placebo runs encountered the same quota before a
scored response.  The harness correctly classified quota failures as errors,
not model failures, and refused to issue a hardness verdict.  The three
script-owned transcripts are retained, but a funded key must rerun all arms
before this family can be submitted.

| bare preset | seed | result | reason |
|---|---:|---|---|
| easy | 851153711 | failed | Gemini returned 48 colors; vertices 1 and 42 conflicted at distance at most two |
| easy | 1120679642 | error | OpenRouter HTTP 403 quota limit |
| easy | 1572813868 | error | OpenRouter HTTP 403 quota limit |
| easy | 73622205 | error | OpenRouter HTTP 403 quota limit |
| easy | 54541720 | error | OpenRouter HTTP 403 quota limit |

| arm / preset | scored solved / attempts | unscored errors | conclusion |
|---|---:|---:|---|
| bare / easy | 0/1 | 4 | one genuine failure; insufficient for a hardening verdict |
| structural hint / hard | 0/0 | 4 | diagnostic unavailable |
| placebo / hard | 0/0 | 4 | diagnostic unavailable |

Because both diagnostic denominators are zero, hinted-minus-placebo is
undefined.  No claim about the usefulness of the invariant hint is made.

## Use

The module is standard-library-only; its discrete coloring witness does not
need the optional `gvlib` exact-algebra helpers.

```python
from gen_2403_12302 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

After a successful bare oracle run and both G9 reruns, emit from the repository
root with:

```bash
bash scripts/emit.sh 2403.12302 20 hard
```

## Caveats

This generated distribution is easy for any implementation of square-graph
greedy coloring; that is the declared Track B reference route.  It tests
recognition and no-tool execution of a lattice invariant, not the difficult
case analysis in the paper's general planar-graph proof and not average-case
graph-coloring hardness.

The 0/200,000 guess result is not based on naive independent noise: each sample
already gives seven distinct uniform colors to the smallest-ID degree-6 vertex
and its six neighbors, a clique in the square graph, and samples the remaining
slots uniformly.  It says that guesses from that explicit prior are sparse;
it says nothing about a model prior biased toward lattice formulas.  The panel
checks a degree outlier, edge-only greedy, public-index periodic, a portfolio
of `x`, `y`, `x+y`, and `x-y` modulo both 7 and 19, and 256 random restarts.  It
does not test every affine formula; finding the correct affine invariant is
the intended solution.

The canonical key is exact for vertex relabeling, edge order/reversal,
translation, unimodular coordinate changes, and their tested compositions,
but it is not a complete graph-isomorphism canonical form for arbitrary
planar graphs.  Most importantly, only one bare attempt from the currently
configured multi-vendor pool was scored; the credential expired before the
remaining calls.  The local gates are trustworthy, but the required external
hardness claim remains pending.
