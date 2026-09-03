# Directed Token Sliding witness generator

| axis | declaration |
|---|---|
| native domain | combinatorics |
| computational core | graph |
| intended intuition | phase invariants expose a hidden Boolean consistency constraint |

This directory turns Banerjee, Engels, and Hoang’s [*Directed Token Sliding* (arXiv:2411.16149v2)](https://arxiv.org/abs/2411.16149) into a deterministic inverse generator. A solver receives an oriented graph, an initial independent token set, a target independent token set, and an exact move count. It must return the ordered directed slides. `verify` replays every move, checking the arc direction, occupancy, independence in the underlying undirected graph, exact length, and final configuration. This accepts any valid path, not just the planted one.

## Why this is a hard regime

Section 2 supplies the precise rule used here. Section 3 proves PSPACE-completeness on oriented split graphs (Theorem 1), oriented bipartite graphs (Theorem 2), and a constant-treewidth oriented class (Corollary 1); the introduction recalls PSPACE-completeness for general oriented graphs. Section 4 identifies the regimes to avoid: oriented cycles are polynomial-time (Theorem 3), cographs are linear-time (Theorem 4), and the cited earlier work makes oriented trees polynomial-time. Version 2 also removes the version-1 planar claim, so this generator makes no planarity claim.

The generated graphs are general oriented incidence-gadget graphs, not trees, cycles, or cographs. To obtain a bounded witness rather than an exponentially long PSPACE certificate, the module compiles regular NAE-3-SAT into token sliding. It first samples a Boolean assignment, then makes a connected degree-regular formula in which every variable has balanced polarity and every clause is NAE-satisfied. A variable token chooses a value; two clause-token gadgets require respectively a true and a false literal; a control token forces the phases. A successful path has the minimum possible `2n + 4m + 2` moves and exists exactly when those choices form an NAE assignment. This bounded search subclass is NP-hard in the worst case; no polynomial-time or closed-form solver is known.

## Difficulty presets

| preset | variables `n` | NAE clauses `m` | vertices | arcs | moves | status |
|---|---:|---:|---:|---:|---:|---|
| easy | 144 | 384 | 4,419 | 10,994 | 1,826 | **ships; oracle held** |
| medium | 168 | 448 | 5,155 | 12,826 | 2,130 | available, not needed by hardening |
| hard | 192 | 512 | 5,891 | 14,658 | 2,434 | available, not needed by hardening |

“Easy” is only relative to the ladder; the earlier 48-variable prototype was rejected by G6 because DPLL solved 8/8 and WalkSAT plus signed spectral repair each solved 5/8. The ladder was moved above that broken regime before hardening.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 12/12: 4 seeds at each of 3 presets |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round trip | fenced, prose-surrounded JSON recovered all 1,826 moves |
| G4 structured guess | 0/200,000; empirical rate 0; threshold `< 1e-6` |
| G5 shipping difficulty | at shipping `easy` (`n=144, degree=8`), 0/200,000 verifier-checked `random_candidate` samples were valid in the exact `2^144` declared language; NAE DPLL exhausted its 10,000-node budget after 10,001 node calls in 2.830645 wall-clock seconds without solving |
| G6 attacks | each 0/8: outlier, greedy, 256-restart WalkSAT, 10k-node DPLL, signed spectral+repair, 20k-state configuration BFS |
| G7 scaling | doubled `n=288`: 8,835 vertices and 3,650 moves; plant verifies |
| G8 canonical key | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |

## Oracle loop

The harness held the shipping preset without escalation. No reply visibly contained a full answer that the parser missed.

| preset | model | seed | parsed | solved | reason |
|---|---|---:|---|---|---|
| easy | `anthropic/claude-sonnet-5` | 298157493 | yes | no | returned an empty tagged list |
| easy | `openai/gpt-5.6-terra` | 607694045 | no | no | explicitly declined; no answer block |
| easy | `x-ai/grok-4.6` | 1973541191 | yes | no | returned 2 moves instead of 1,826 |

## Worked example

This is `make_instance(n=3, degree=2, seed=1)` rendered in full:

```text
DIRECTED TOKEN SLIDING — EXACT-LENGTH SEARCH

Definitions and rules:
- The graph has vertices 0 through 34.
- Each ordered pair u v listed below is a directed arc u -> v. No reverse arc is implied.
- A configuration is a set of occupied vertices, with at most one token per vertex.
- A configuration is independent when no two occupied vertices are adjacent after arc directions are ignored; in other words, for no listed arc u -> v may both u and v be occupied.
- One legal slide chooses an occupied source u and an unoccupied destination v, requires the listed arc u -> v, moves that token from u to v, and leaves an independent configuration.
- Tokens are indistinguishable. Vertex numbers are 0-indexed. Reusing a directed arc at different times is allowed if the move is legal each time.

Start configuration (8 occupied vertices):
0 6 11 17 20 28 31 33

Target configuration (8 occupied vertices):
4 12 13 23 25 27 29 32

Find exactly 16 legal slides that transform the start configuration into the target configuration.
Order matters and every move is applied to the configuration produced by the preceding move.

Directed arcs (75 total), one `u v` pair per line:
30 29
28 34
28 9
6 19
26 30
17 24
3 0
31 1
26 4
31 7
7 23
34 4
6 18
26 0
8 27
20 2
19 15
2 25
27 20
5 25
24 0
15 29
16 1
28 26
1 23
24 32
8 23
24 10
27 28
22 13
8 11
0 23
18 13
0 8
9 4
21 0
11 30
19 0
27 6
5 0
11 15
34 0
14 12
9 0
8 29
6 22
8 31
3 30
16 32
16 0
8 33
5 14
22 0
27 17
33 14
0 29
34 7
33 10
20 5
18 1
21 32
3 25
18 0
17 16
17 21
20 3
8 12
9 14
2 7
10 12
21 15
2 0
22 10
0 12
19 13

Give your final answer inside <answer></answer> tags, as a JSON list of exactly the required number of [source,destination] integer pairs.
Example: <answer>[[3,17],[8,42]]</answer>
Output nothing else inside the tags.
```

One answer is:

```json
[[31,7],[11,15],[33,10],[0,8],[6,18],[18,13],[17,16],[16,32],[20,5],[5,25],[28,9],[9,4],[8,27],[15,29],[7,23],[10,12]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Reversing the first move returns `(False, "move 0: source 7 is unoccupied")`.

## Use

```python
import gen_2411_16149 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=2026, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_output)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit 20 fresh recorded instances with:

```bash
bash scripts/emit.sh 2411.16149 20 easy
```

## Caveats

- The paper proves decision hardness for graph classes, not average-case hardness of this planted distribution. The NAE compiler gives a worst-case NP-hard bounded-witness subclass, while the empirical tests only cover the sampled distribution and stated budgets.
- `CERTIFICATE_LANGUAGE` is the normal-form space containing one fixed-phase move list per Boolean assignment. `random_candidate` samples assignments uniformly and uses deterministic lowest-index gate tie-breaking, so its support and `search_space(inst) == 2 ** inst["n"]` agree exactly. The earlier arc-sequence superset was replaced, and gate tie-breaking was made deterministic. At the small labelled reference (`n=9, degree=4`), exact enumeration found 14 valid candidates in 512 (fraction 0.02734375). That reduced fixture is dense and is not evidence for shipping difficulty.
- The shipping density measurement observed 0/200,000 valid samples; it is an empirical observation, not an exact zero or a bound against clause learning or message passing. The strongest systematic panel baseline also failed at its cap, but 2.830645 seconds and 10,001 node calls are a modest bounded cost. That failure alone does not establish that solving the instance is intrinsically expensive.
- The panel did **not** run an industrial SAT/SMT solver, SDP, non-backtracking spectral method, or large-memory bidirectional/A* search. It did run NAE unit-propagating DPLL, signed power iteration plus repair, WalkSAT, and explicit configuration BFS.
- The oracle failures were refusals or drastically short witnesses. They demonstrate failure under the mandated interface and token budget, but are weaker evidence of computational hardness than a serious programmatic solve attempt.
- `canonical_key` is invariant under all tested relabellings and value-coordinate flips, but uses closed-walk traces rather than complete graph canonization. Rare non-isomorphic cospectral formulas could collide and be conservatively treated as duplicates.
- Exact length is essential: it makes the witness polynomial and excludes detours through deliberately harmless blocker arcs. Removing the length bound changes both the certificate size and the problem being generated.
