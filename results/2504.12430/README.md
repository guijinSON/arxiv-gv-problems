# Verified generator for arXiv:2504.12430

## What the problem is

This module turns Akhmejanova and Longbrake's [*Fractional hypergraph coloring*](https://arxiv.org/abs/2504.12430) into a witness-search problem.  The input is an ordinary graph, equivalently a 2-uniform hypergraph.  A solver must give every vertex exactly two distinct colors from `{0,1,2,3,4,5}`, with disjoint color pairs at the ends of every edge.  A witness is a JSON list of `[vertex,color1,color2]` records.  Checking it is an exact linear scan of the records and edges.

Generation is inverse: all fifteen 2-subsets are planted equally often before any edge is drawn.  Five stubs per vertex are then paired only between disjoint planted subsets.  The result is a connected simple 5-regular graph; labels and edge order are randomized.  Thus every generated instance is satisfiable, every public vertex has the same degree, and there is no differently distributed class of “decoy” edges.

## Why it is hard, and whether to trust it

Section 1 of the paper supplies the exact definition and states that 2-element hyperedges recover ordinary `(a:b)` graph multicoloring.  A `(6:2)` coloring is a graph homomorphism to the Kneser graph `KG(6,2)`: its fifteen target vertices are the 2-subsets of six colors, adjacent exactly when disjoint.  `KG(6,2)` contains triangles and is non-bipartite.  The [Hell–Nešetřil H-coloring dichotomy](https://doi.org/10.1016/0095-8956(90)90132-J) therefore makes the unrestricted decision/search family NP-complete (unless P=NP).

The paper itself does **not** claim computational hardness.  Its Theorem 1 is a sufficient sparse-edge colorability result for large uniformity, and its proof gives a randomized recoloring construction; Theorem 3 gives a reserve-color construction when `a/b` grows.  Those are easy-looking regimes to avoid.  Here uniformity is 2 and `a=6`, so their hypotheses do not apply.  The nearby `(4:2)` graph problem is also avoided: `KG(4,2)` is three disjoint edges, reducing feasibility to bipartiteness.

Worst-case NP-completeness is not an average-case proof for this planted distribution.  Evidence specific to the generator is: all local gates pass, four generator-aware attacks fail on eight shipping seeds each, and the required fresh-vendor oracle pool returned `hardened` at the first named preset.  A preliminary cubic version was rejected after generic CSP search solved 180 vertices in 0.05 seconds.  Degree 4 was likewise easy in a density sweep, degree 6 began propagating the plant, and a degree-5 `n=12` draft was removed when bounded exact search solved 1/8 seeds.  The shipped degree-5, `n=18` window survived that probe.

## Worked example

The named presets are intentionally too large for a readable worked listing.  This is the same family's exact enumerable fixture, produced by `make_instance(n=1, degree=6, seed=2026)`; it is a relabeled `KG(6,2)` and exercises the identical statement, parser, and verifier.

```text
Proper (6:2)-fractional coloring of a graph

A graph is a set of vertices together with undirected edges.  Here it
is also viewed as a 2-uniform hypergraph: every edge has exactly two
distinct endpoints.  There are no loops and no repeated edges.

Assign every vertex exactly two DISTINCT colors chosen from
{0,1,2,3,4,5}.  An edge is properly fractionally colored exactly when
no color is assigned to both endpoints.  Equivalently, the two
2-element color sets at the endpoints must be disjoint.  Every listed
edge must satisfy this rule.

Vertices are the integers 0 through 14, inclusive
(0-indexed).  Every vertex must appear exactly once in the answer.
The order of vertex records and the order of the two colors within a
record do not matter.  Different vertices may receive the same pair.
Only the edges listed below impose constraints; nonedges impose none.

Edges (45 total), one pair of endpoints per line:
1 8
0 9
4 8
0 11
2 6
4 13
0 4
3 11
5 11
10 12
2 9
11 13
6 14
1 5
7 9
8 13
2 12
1 6
4 10
2 10
2 3
3 8
1 12
5 7
8 12
9 14
4 6
0 10
0 3
5 10
3 7
7 14
0 1
11 12
2 13
7 10
11 14
5 13
5 6
9 13
7 8
3 6
12 14
4 14
1 9

Give your final answer inside <answer></answer> tags as one JSON array.
It must contain exactly one [vertex,color1,color2] record per vertex.
Both colors in a record must be integers in 0..5 and must be distinct.
Example format: <answer>[[0,0,1],[1,2,3]]</answer>
Output nothing else inside the tags.
```

One answer is:

```text
<answer>[[0,0,1],[1,2,3],[2,0,3],[3,2,5],[4,3,5],[5,0,5],[6,1,4],[7,1,3],[8,0,4],[9,4,5],[10,2,4],[11,3,4],[12,1,5],[13,1,2],[14,0,2]]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Changing the first color `0` to `6` returns `(False, "color out of range: 6 is not in 0..5")`.

## Difficulty presets

| preset | `n` per target color | vertices | edges | degree | status |
|---|---:|---:|---:|---:|---|
| `standard` | 18 | 270 | 675 | 5 | **shipping; hardened** |
| `hard` | 24 | 360 | 900 | 5 | G1 passed; available escalation |
| `extreme` | 30 | 450 | 1125 | 5 | G1 passed; available escalation |

Rejected drafts were not left in `DIFFICULTY`: cubic instances failed the stronger exact-search audit; degree 4 was similarly easy; degree-5 `n=12` was solved on 1/8 bounded-search seeds.  Increasing `n` at fixed degree 5 grows the fixed-target CSP without crossing into the propagation-heavy denser regime.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 12/12 across every preset; 12/12 deterministic rebuilds |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | 270 records recovered through prose + Markdown; 4/4 garbage cases rejected |
| G4 structured guess | 0/200,000; candidates already have all vertices and valid 2-subsets |
| G5 sparse | exactly 720 valid of `15^15`; ratio `1.6442339475752403e-15` on 3/3 tiny instances |
| G6 adversaries | outlier 0/8; left-to-right greedy 0/8; 512-restart forward greedy 0/8; capped AC-3/MRV 0/8 |
| G7 scaling | doubled to 540 vertices and 1,350 edges; planted witness still verifies |
| G8 canonical key | 60/60 relabel/reorder checks; 80/80 carried witnesses; 20/20 unrelated keys distinct |

The complete machine-readable measurements are in `selftest_report.json`.

## Oracle loop

All calls used reasoning effort `medium`, distinct random seeds, and the script-owned four-vendor pool.  The shipping level held without escalation.

| preset | model | seed | solved | why |
|---|---|---:|---|---|
| standard | `openai/gpt-5.6-terra` | 1203815856 | no | parsed witness; shared colors `0,1` on edge 1 |
| standard | `anthropic/claude-sonnet-5` | 1296269060 | no | used the 32,000-token budget and emitted no witness (`finish_reason=length`) |
| standard | `google/gemini-3.1-pro-preview` | 247354392 | no | parsed witness; shared colors `4,5` on edge 52 |

See `llm_loop_transcript.jsonl` and `.meta.json` for the full replies, timings, master seed, pool, and `hardened` verdict.

## How to use it

```python
import gen_2504_12430 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit verified samples with:

```bash
bash scripts/emit.sh 2504.12430 20
```

Run the local gates with `python3 results/2504.12430/gen_2504_12430.py`.

## Caveats

- The hardness theorem is worst-case.  It does not prove this balanced planted distribution is average-case hard; the attack panel and three-vendor hold are empirical evidence only.
- `0/200,000` is the observed rate under independent uniform choices among all fifteen legal 2-subsets at each vertex.  It does not mean the true probability is zero, and it does not model a solver that conditions deeply on edges.  The exact tiny count partly complements that limitation.
- Balance and equal aggregate traffic on target edges are generator facts, not stated constraints.  A sophisticated spectral, belief-propagation, or unrestricted SAT/CSP solver was not exhaustively tested.  Only a 2,000-node AC-3/MRV probe was included in G6.
- One oracle failure was length-limited rather than an explicit wrong answer; the other two produced parseable, exactly rejected witnesses.
- `canonical_key` is a strong polynomial-time invariant (sorted rooted BFS layer/edge profiles), not an exact graph-isomorphism canonical form.  Non-isomorphic collisions are possible even though all tested relabelings were invariant and all 20 unrelated shipping graphs were distinct.
- Constant degree keeps larger `n` from merely revealing the plant through density, but individual random seeds can still vary in practical difficulty.
