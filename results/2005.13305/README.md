# Affine Seidel recovery for arXiv:2005.13305

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | matrix certificate (two affine parameters per permutation matrix) |
| Intended intuition | invariant: a switched lattice cross has an affine-invariant packed-label XOR |
| Domain essentiality | native |
| Reduction | none |

This generator is based on Kabanov, Konstantinova, and Shalaginov, [“Generalised dual Seidel switching and Deza graphs with strongly regular children”](https://arxiv.org/abs/2005.13305). It hands the solver adjacency lists of graphs with adjacency matrix `N=P(M+I)`, where `M` is a hidden affine copy of a lattice graph and `P` is a fixed-point-free Seidel involution. The requested witness gives the packed binary vectors `u,b` in `P(x)=x XOR ([parity(v AND x)]u) XOR b`; `v` is part of the instance. The verifier reconstructs `M`, checks the matrix identity, the involution and automorphism conditions, and all strongly regular common-neighbour counts using exact integers and sets.

## Why this is Track B

Section 1 fixes the exact definitions of Deza graphs, children, and Seidel automorphisms. Section 3, Theorem 9 proves `(P(M+I))^2=(M+I)^2` and identifies the strongly regular children; Example 7 supplies the lattice-graph regime. Those same results make a Track A claim impossible: if `M` is recovered, row matching recovers `P` in polynomial time, and if the hidden lattice coordinates are supplied the construction is explicit.

The reference algorithm computes all row intersections of `N^2`, recovers the child `M` from the two common-neighbour values, and matches rows of `N` against closed neighbourhoods of `M`. Its complexity is `O(L*v^3)` with ordinary adjacency comparisons. At shipping size (`L=3`, `v=64`) it succeeds 8/8, averages **0.001237 s** using Python bitsets, and represents **6,048 bitset intersections / 387,072 elementary adjacency comparisons**. This is easy with tools and infeasible as unaided exact bookkeeping.

The compact route notices that a closed `L_2(8)` neighbourhood is a 15-point row-column cross. Its packed labels XOR to its centre, and an affine relabelling preserves the equality because 15 is odd. For each layer, XORing the neighbourhood at `0` gives `b`; XORing the neighbourhood at the least basis bit selected by the displayed `v` then gives `u`. The shipping route costs **90 exact XOR operations**. The paper proves the graph identity; the generator samples `P` and the affine relabelling first and carries the witness through, never solving its output.

## Worked demo (`seed=7`)

This is the complete rendered demo. A person can solve it on paper: XOR the seven neighbours of vertex `0` to obtain `b=13`; the demo requires `u=0`.

```text
Recover Seidel involutions from switched lattice graphs.

A simple graph is strongly regular with parameters (v,k,lambda,mu) if
it has v vertices, every vertex has k neighbors, adjacent vertex pairs
have lambda common neighbors, and distinct nonadjacent pairs have mu.
A Seidel involution P is a graph automorphism with P(P(x))=x that maps
every vertex to a distinct nonneighbor.

Each layer below is a complete undirected adjacency list on vertices
0,...,2^d-1. Vertex labels denote d-bit vectors: addition is bitwise XOR
and e_i is the integer 2^i. List order carries no information.

For each layer there is an unknown strongly regular graph M and an
unknown fixed-point-free Seidel involution P of M. The displayed
adjacency matrix is exactly N=P(M+I), where I is the identity matrix.
For d=2s, M is an affinely relabelled lattice graph L_2(2^s). It has
vertices (r,c), joining two distinct vertices exactly when they share r
or c, and strongly regular parameters (2^(2s),2(2^s-1),2^s-2,2).
Different layers use independent hidden affine
lattice coordinates on the same public vector space.

Certificate language. For each layer output the two packed d-bit integers
u and b. The integer v is displayed with that layer and the map is exactly
P(x)=x XOR (u if parity(v AND x)=1 else 0) XOR b.
For d=4, v=u=0 and b is nonzero. For d>=6, u and v are nonzero,
parity(u AND v)=parity(v AND b)=0, and b is neither 0 nor u.

LAYER 0: d=4, vertices 0..15, v=0
0: 10,15,13,4,12,3,14
1: 13,5,14,15,2,11,12
2: 14,6,1,12,8,13,15
3: 12,9,13,0,14,7,15
4: 10,11,7,14,9,0,8
5: 1,9,8,15,6,11,10
6: 5,12,2,8,11,9,10
7: 3,11,13,8,10,9,4
8: 6,11,5,2,7,12,4
9: 7,10,3,13,4,6,5
10: 9,7,6,5,14,0,4
11: 1,6,8,15,4,7,5
12: 3,1,15,2,0,6,8
13: 0,2,7,3,9,1,14
14: 0,3,2,10,4,1,13
15: 3,11,2,12,1,0,5

Give your final answer inside <answer></answer> tags as one JSON object
with exactly this shape: {"maps":[{"u":...,"b":...}, ...]}
Use the displayed layer order and exactly one u,b object per layer.
Example for one d=4 translation:
<answer>{"maps":[{"u":0,"b":1}]}</answer>
Output nothing else inside the tags.
```

Answer: `<answer>{"maps":[{"u":0,"b":13}]}</answer>`.

`verify(inst, inst["answer"])` returns `(True, "ok")`. Changing `b` to zero returns `(False, "layer 0 translation b must be nonzero")`.

## Difficulty presets

| Preset | Layers | Lattice side | Vertices/layer | Search space | Compact operations | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 1 | 4 | 16 | 15 | 6 | hand-solvable illustration |
| easy | 3 | 8 | 64 | 804,357,000 | 90 | **ships; bare pool held** |
| medium | 3 | 16 | 256 | 4,097,536,192,008 | 186 | available, not reached |
| hard | 4 | 16 | 256 | 65,568,774,144,512,016 | 248 | available, not reached |

The ladder enlarges the lattice before adding a fourth certificate, so the medium step grows the mechanical haystack while keeping the answer at six integers. `n` can be doubled and still builds and verifies; the named hard preset remains below the 300-operation cap.

## Gate results

| Gate | Result |
|---|---|
| G1 | pass: 20/20 planted witnesses, all JSON-native |
| G2 | pass: drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass: tagged and untagged fenced JSON round-trip; malformed text returns `None` |
| G4 | pass: 0/200,000 valid structure-aware random candidates; bounded language size 804,357,000 |
| G5 | pass: shipping density sample 0/200,000; demo has exactly 1 valid answer among 15; reference cost 387,072 comparisons and 0.001237 s average |
| G6 | pass: five attacks, each 0/8; reference reconstruction solves 8/8 as Track B expects |
| G7 | pass: six-layer size-doubled instance builds and its planted witness verifies |
| G8 | pass: 20/20 common-affine/layer/list-order invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass: 58 characters, 15 estimated tokens, 6 atomic elements, 90 intended operations |

## Oracle loop

| Preset | Model | Seed | Solved | Recorded reason |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 89,160,478 | no | asserted underdetermination and supplied no full certificate |
| easy | Google Gemini 3.8 Flash | 584,082,727 | no | parsed witness failed a child common-neighbour check |
| easy | Google Gemini 3.8 Flash | 566,436,241 | no | empty length-limited response at the harness token budget |

The harness verdict is `hardened` at `easy`, with three distinct seeds and two vendors. The empty third response is recorded explicitly rather than disguised as a mathematical error; the other two are substantive failures.

## G9 diagnostic arms

| Arm | Solved/attempts |
|---|---:|
| bare | 0/3 |
| structural hint | 2/3 |
| placebo hint | 1/3 |

The hinted-minus-placebo rate is **1/3**. Naming the XOR invariant materially helps, although one placebo prompt also solved; this supports, but does not by itself prove, that the task measures discovery of the claimed invariant. The hinted arm is recorded as `too_easy` in the module’s diagnostic field because at least one model solved it; under the current protocol this is not a shipping gate.

## Use

From this directory:

```python
import json
import random
import gen_2005_13305 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
raw = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(raw)
assert g.verify(inst, answer) == (True, "ok")
candidate = g.random_candidate(inst, random.Random(9))
```

From the repository root, emit fresh verified records with:

```bash
bash scripts/emit.sh 2005.13305 20 easy
```

## Caveats

This is a Track B benchmark, not a claim of computational hardness: a few milliseconds of bitset code solve it. Seeing the XOR invariant also makes it short by hand, as the hinted arm demonstrates. The 0/200,000 guess result is only an empirical density under the exact bounded prior stated to the solver—uniform legal `(u,b)` pairs for each displayed `v`; it is neither an exact shipping solution count nor evidence about other priors. The adversary panel did not test a full automorphism-group package, canonical labelling package, or a learned graph model. The canonical key is a strong multiplex invariant, not a complete graph-isomorphism canonical form, so rare collisions are possible. Finally, the shipping prompt is about 10.8k characters, while medium and hard are much larger; only `easy` has oracle evidence and is emitted.
