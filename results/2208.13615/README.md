# arXiv 2208.13615 — verified fixed-spine two-page embeddings

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a canonical edge partition) |
| Native objects | DAG, fixed topological spine order, directed edge intervals |
| Intended intuition | invariant: compress away isolated spine vertices and inspect edge-span parity |
| Domain essentiality | native |
| Reduction | paper-licensed fixed-spine specialization (Section 2 and Theorem 9) |

## What the family asks

[Bekos et al., *Recognizing DAGs with Page-Number 2 is NP-complete*](https://arxiv.org/abs/2208.13615) defines a two-page book embedding as a topological vertex order plus a partition of the directed edges into two pages, with no alternating-endpoint pair on one page. This family supplies the topological order and asks for the paper's native second object: a page partition of every edge ID. Verification checks the partition and every declared same-page crossing using exact integer positions.

Generation never solves its output. On a compressed spine, all adjacent forward edges are placed on page 1. Extra chords are sampled one at a time; their page is their span parity, and a chord is retained only when it crosses no chord already on that page. Each new chord is also required to cross the opposite page, so the chord crossing graph is connected. Isolated vertices are inserted, all vertices are randomly renamed, and edge rows are shuffled. These transformations carry the known partition unchanged.

## Why Track B, not Track A

Theorem 9 states the full recognition problem is NP-complete even for st-planar DAGs, but this generator deliberately fixes the spine order. Its certificate-producing reference algorithm is therefore easy with tools: construct the edge-crossing graph in `O(m²)` and bipartite-colour it by BFS. At shipping size it tests exactly 6,216 edge pairs, takes about 0.0005 seconds here, and succeeds 8/8. Claiming Track A would be false.

The no-tool gap is between those 6,216 mechanical comparisons and at most 292 exact operations after noticing the invariant: mark incident vertices, compress the spine, and colour each edge by compressed-span parity. The Introduction's other easy boundaries also matter: page-number 1 is linear-time recognizable, and the cited algorithms are FPT by vertex-cover number for every page count and by treewidth for two-page st-graphs. This benchmark does not claim hardness against any of them.

## Worked demo (`seed=0`)

This smallest rung intentionally discloses its page split, so a person can solve and check it on paper.

```text
Two-page embedding of a fixed-order DAG

Spine order (left to right):
1322 1171 1432 1097 1124 1008 1374 1138 1059 1361

Directed edges (0-indexed edge IDs):
0: 1008 -> 1138
1: 1432 -> 1124
2: 1322 -> 1124
3: 1374 -> 1138
4: 1124 -> 1008
5: 1432 -> 1138
6: 1171 -> 1432
7: 1097 -> 1374
8: 1322 -> 1171
9: 1097 -> 1124
10: 1008 -> 1374
11: 1432 -> 1097

Training-rung disclosure: edge IDs 0 through 2 form page 0, and IDs
3 through 11 form page 1.
```

Answer:

```text
<answer>[0, 1, 2, -1, 3, 4, 5, 6, 7, 8, 9, 10, 11]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last ID returns `(False, "expected exactly 13 list entries")`.

## Difficulty presets

| preset | active spine vertices | isolated decoys | edges / answer bits | disclosed clue | result |
|---|---:|---:|---:|---|---|
| demo | 8 | 2 | 12 | exact page split | hand-scale illustration |
| easy | 18 | 4 | 29 | exact page split | oracle solved 3/3 |
| medium | 34 | 8 | 63 | compressed-span rule | oracle solved 3/3 |
| hard | 52 | 16 | 112 | none | **ships; bare oracle failed 3/3** |

The ladder grows the graph and removes redundant clues. No preset was rejected by a local gate. If more difficulty is requested, `escalate()` first adds eight isolated decoys at fixed certificate length; after that the 300-operation compact-route cap is binding.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 planted verifies | pass | 20/20 across all presets |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round trip | pass | tagged JSON recovered through prose/fences |
| G4 random guess | pass | 0/200,000; exact fraction `2^-60 = 8.67e-19` |
| G5 density/baseline | pass | `2^52` valid of `2^112`; 6,216 pair tests, ~0.0005 s |
| G6 adversaries | pass | five attacks, each 0/8; reference 8/8 as expected |
| G7 scaling | pass | doubled instance: 104 active vertices, 225 edges, planted verifies |
| G8 canonical key | pass | 20 relabels, 20 composed transforms, 20/20 unrelated keys distinct |
| G9 caps | pass | 454 chars, 114 estimated tokens, 113 atoms, 292 operations |

The failing G6 attacks were short-versus-long outliers, online first-fit, 256 uniform restarts, raw displayed-spine parity, and alternating input rows. The successful crossing-graph BFS is correctly separated as Track B's reference algorithm.

## Bare oracle hardening loop

| preset | model | seed | solved | result |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1301056794 | yes | verified |
| easy | Gemini 3.8 Flash | 593865504 | yes | verified |
| easy | GPT-5.6 Terra | 1846588834 | yes | verified |
| medium | GPT-5.6 Terra | 1004841606 | yes | verified |
| medium | Gemini 3.8 Flash | 1376641386 | yes | verified |
| medium | Gemini 3.8 Flash | 542237294 | yes | verified |
| hard | Gemini 3.8 Flash | 2061081124 | no | same-page crossing, edges 11/63 |
| hard | GPT-5.6 Terra | 2410870 | no | same-page crossing, edges 1/51 |
| hard | GPT-5.6 Terra | 1571828733 | no | same-page crossing, edges 1/27 |

Every hard reply parsed as a complete canonical partition. Thus the hardened verdict is not a parser failure.

## G9 diagnostic arms

| arm | solved / attempts | interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 2/3 | often exposed the intended route |
| placebo hint | 3/3 | adding a generic sentence also changed outcomes |

Hinted minus placebo is `-1/3`. With only three attempts per arm, this provides no evidence that the structural wording helped beyond prompt/stochastic effects; indeed it underperformed the placebo in this run. The defensible finding is narrower: bare held 0/3, while either added sentence made the task less robust. These arms are diagnostic and do not gate shipment.

## Use

```python
from gen_2208_13615 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2208.13615 20 hard
```

## Caveats

- This is the fixed-spine colouring subproblem, not the paper's NP-hard search over topological orders. It is intentionally Track B and is trivial for the included sub-millisecond reference program.
- The `2^-60` figure is exact for uniform page partitions because the 61-chord crossing graph is connected and the 51 adjacent edges are isolated in it. It does not model a solver with interval-layout priors.
- Conditioning edge-row shuffles on four cheap heuristics failing may itself create learnable distributional artifacts. The panel did not test SAT/ILP encodings, optimized circle-graph recognition, or trained invariant detectors; the successful BFS already establishes tool-based easiness.
- `canonical_key` removes arbitrary vertex names and edge-row order, but does not quotient every possible order-preserving graph automorphism beyond those transformations.
- The compact route is close to the 300-operation cap (292), so larger native instances would become calculator/bookkeeping tests before they became better no-tool tests.
