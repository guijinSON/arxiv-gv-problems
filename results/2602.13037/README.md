# arXiv 2602.13037 — recursive-cube mixed coloring

**Status:** locally verified Track-B candidate, **not hardness-certified for shipping**. The required bare, structural-hint, and placebo runs were invoked through `scripts/harden.py`, but OpenRouter returned HTTP 403 “total key limit exceeded” before any scored attempt. The transcripts preserve those infrastructure failures; they are not evidence that a model failed.

| profile field | value |
|---|---|
| track | B — no-tool compression |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple (ordered port pairs) |
| intended intuition | decomposition |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The family uses the native `(1^1,2^3)`-coloring problem from Section 2.2 of [*Between proper and square coloring of planar graphs, hardness and extremal graphs*](https://arxiv.org/abs/2602.13037). Such a coloring has one color that cannot repeat across an edge and three colors that cannot repeat between vertices at graph distance one or two.

The displayed graph is the full subdivision of a cubic bipartite planar core. The core starts as the cube `Q_3`; each construction step replaces one edge by a fresh cube with one edge removed. The answer lists only the two boundary ports of each eight-vertex patch, in leaf-to-root peeling order. Generation samples and carries those ports through a random relabeling, so it never solves its output. Given a port pair, the checker tries the `3 × 3` possible external incident-edge pairs, recovers and validates the eight-vertex patch, collapses it, explicitly reconstructs a three-edge-coloring, converts that into a mixed vertex coloring, and scans every edge and length-two path. It never reads `inst["answer"]`.

## Why Track B

Theorem 6 proves NP-completeness for `(1^1,2^3)`-coloring on bipartite planar graphs of maximum degree 4 and any prescribed fixed girth. That theorem does **not** imply average-case hardness for this maximum-degree-3, short-cycle distribution. The paper also identifies polynomial boundary cases in Section 2: `(1^1,2^1)` graphs are star forests, while `(1^0,2^3)` graphs are disjoint unions of paths and cycles. This family claims neither of those easy regimes nor Track A.

The disclosed reference algorithm repeatedly deletes one core edge, runs bridge DFS to expose every two-edge cut, recognizes an eight-vertex cube side, and collapses it. Its complexity is `O(r*m*(n+m))` for `r` patches. At the configured hard preset, the saved selftest measured 146,400 counted graph operations and 0.056 seconds for one instance; the eight-seed reference panel used 1,171,200 operations and 0.480 seconds, solving 8/8 as expected. Once the recursive two-pole decomposition is seen, the intended route uses at most 264 local adjacency operations. This mechanical-versus-structured gap is the Track-B claim; graph tooling makes the family easy.

## Worked demo

`make_instance(n=0, seed=0)` renders the complete hand-scale instance below.

```text
Mixed distance-(1,2) coloring certificate

The undirected simple graph below has vertices 0 through 19.
An edge u-v is unordered.  There are 24 edges:
  0-8 3-18 2-13 14-15 7-18 6-16 3-10 5-10
  1-11 7-14 4-18 0-1 13-17 2-12 0-5 6-11
  14-19 11-12 8-17 2-15 16-19 9-10 9-16 4-17

A (1^1,2^3)-coloring uses one distance-1 color and three distance-2
colors.  Two adjacent vertices may not share the distance-1 color.  Two
distinct vertices at graph distance 1 or 2 may not share a distance-2 color.

Your task is to give a compact peeling certificate for such a coloring.
First form the degree-three core H: every degree-two vertex of the displayed
graph has two degree-three neighbors; suppress it and put one core edge
between those two neighbors.

The certificate has exactly 0 ordered rows.  Each row is a
sorted pair [p,q] of distinct current vertices of H, and no vertex ID may be
repeated between rows.  The pair must be the two boundary ports of an exposed
eight-vertex patch: p and q are not adjacent, and it must be possible to
remove one incident edge at p and one incident edge at q so that their
component has exactly eight vertices, meets the rest of H only in those two
removed edges, and becomes Q_3 after adding the missing edge p-q.  Here Q_3
is the graph on the eight binary triples, with two triples adjacent exactly
when they differ in one coordinate.  Since H is cubic, the checker examines
only 3 x 3 possible pairs of incident edges to recover and check the patch.
If a port pair recovers more than one such component, the lexicographically
smallest sorted vertex set is used.

Peel a row by deleting its eight vertices and adding an edge between its two
outside neighbors.  After all rows, the remaining eight core vertices must
induce Q_3.  This certificate is executable: the checker colors the three
coordinate-direction edge classes of the final cube, reverses every peel,
colors core vertices with the distance-1 color, colors each suppressed
vertex by its core edge's direction, and directly checks every required
distance.

All IDs are decimal integers in 0..19.  Order within a pair is not
mathematical, but each pair must be written in increasing order to give one
unambiguous representation.  Repetitions are forbidden.

Give your final answer inside <answer></answer> tags as one JSON object with
the single key "patches".  Its value must be the ordered list of rows.
Syntax example only (not a proposed certificate):
<answer>{"patches": [[0,1],[2,3]]}</answer>
Output nothing else inside the tags.
```

The demo answer is `<answer>{"patches":[]}</answer>`. Suppressing its twelve degree-two vertices exposes `Q_3`, so a person can check it on paper. `verify(inst, {"patches": []})` returns `(True, "ok")`; `verify(inst, {})` returns `(False, "answer_shape: expected one JSON key named patches")`.

## Difficulty and gates

| preset | patches `n` | displayed vertices | answer atoms | configured to ship? |
|---|---:|---:|---:|---|
| demo | 0 | 20 | 0 | no; hand example |
| easy | 4 | 100 | 8 | no |
| medium | 7 | 160 | 14 | no |
| hard | 10 | 220 | 20 | yes, pending oracle evidence |

| gate | measured result |
|---|---|
| G1 planted verifies | pass, 12/12 over all presets |
| G2 corruption | pass, five corruptions rejected with five distinct reason codes |
| G3 round trip | pass, tagged JSON recovered from prose and a Markdown fence |
| G4 structured guessing | pass, 0/200,000; candidate space `73037418105512652388311807892800000` |
| G5 density and baseline | pass, hard estimate 0/200,000; demo exact count 1; decoder 146,400 operations |
| G6 adversaries | pass, four attacks 0/8 each; reference decoder 8/8 |
| G7 scaling | pass, reference work rises `0 → 15,936 → 59,136 → 146,400`; `n=20` also builds and verifies (420 vertices) |
| G8 canonical key | pass, 20/20 relabelings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) caps | pass, 106 characters, 27 estimated tokens, 20 atoms, 264 intended operations |

The four failing attacks are degree-core plus low IDs, nearest-core greedy pairing, 256 structured random restarts, and a one-pass static cube scan. The last is the in-context Track-B attack: it can identify an initially exposed end but does not rebuild the reduced graph after every collapse.

## Oracle loop and G9 diagnostics

| arm | preset reached | scored attempts | recorded calls | result |
|---|---|---:|---:|---|
| bare | easy | 0 | 4 | all HTTP 403 key-limit errors |
| structural hint | hard | 0 | 4 | all HTTP 403 key-limit errors |
| placebo hint | hard | 0 | 4 | all HTTP 403 key-limit errors |

There is no oracle verdict and therefore no empirical hinted-minus-placebo conclusion. The selftest records `0.0` only as a placeholder for two empty rates; G9(a) and the retired G9(b) are diagnostic, while G9(c) passes. The structural hint names only the invariant: “The degree-three core retains a recursive cube-minus-edge two-pole structure under edge subdivision.”

## Use

```python
import gen_2602_13037 as g

inst = g.make_instance(n=10, seed=7)
statement = g.render(inst)
answer = g.parse_answer('<answer>{"patches": []}</answer>')
ok, reason = g.verify(inst, answer)          # False: hard needs ten rows
ok, reason = g.verify(inst, inst["answer"]) # True, "ok"
```

From the repository root, rerun hardening once the OpenRouter quota is available, then emit only if the verdict is `hardened`:

```bash
cd results/2602.13037
python3 ../../scripts/harden.py gen_2602_13037.py
cd ../..
scripts/emit.sh results/2602.13037/gen_2602_13037.py
```

## Caveats

This family is deliberately easy with graph tooling, and the paper’s worst-case theorem does not establish hardness for its generated distribution. The `0/200,000` estimate is relative to uniform ordered, disjoint, unordered pairs of core vertices after enforcing type, count, order, range, degree-three membership, and non-reuse; it is not a bound against topology-aware search. The measured reference decoder is intentionally simple; no linear-time two-edge-cut implementation, SAT/SMT colorer, tree-decomposition dynamic program, or general graph-isomorphism package was run. The canonical key is a strong all-pairs distance-profile invariant, not a complete isomorphism invariant, although an additional 200-seed audit had no collision. Difficulty currently grows the number of certificate rows as well as the graph; no honest fixed-answer-length decoy axis was found, so further escalation is limited by the 300-operation route cap. Finally, the archived `rejected_gen_2602_13037.py` is an earlier affine prototype that failed structure-aware G4 and G6 and is retained only as audit evidence.
