# Problem generator for arXiv:1910.04896

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple: one colour class |
| intended intuition | invariant: one binary coordinate changes across every edge |
| domain essentiality | native |
| reduction | paper-licensed by Section 4, Definition 4.1 and Theorem 4.8 |

## What the family asks

This module turns Guillermo Alesandroni's [*Monomial invariants applied to
graph coloring*](https://arxiv.org/abs/1910.04896) into an exact proper-colouring
task. The solver receives a finite simple graph on `2n` labelled vertices and a
displayed perfect matching. It must return the `n` vertices assigned colour 0;
the complement is colour 1. Checking the answer only requires confirming that
every graph edge has one endpoint in each class.

This is the paper's graph object and its paper-licensed combinatorial
representation of the algebraic invariant. Definition 2.5 fixes proper
`k`-colouring, Definition 4.1 constructs the chromatic monomial ideal, and
Theorem 4.8 proves `chi(G) = codim(S/M_G)`. Its proof carries colour-class
covers in both directions, so the graph representation is central rather than
a convenience discretisation. Generation is inverse: it chooses the two
classes first, samples every edge across them, and adds a connected scaffold.
The checker never reads the planted answer and accepts either valid class.

## Why this is Track B

This distribution is not Track A hard. Breadth-first bipartite colouring solves
it in `O(|V|+|E|)`. At the provisional hard preset, the final eight-instance
panel solved 8/8 with 85,864 primitive traversal operations (10,733 per
instance) in 0.263 seconds. The paper also explicitly constructs colourings in
Theorem 6.2 and, for odd clique size, Lemmas 6.3--6.4 and Theorem 6.6; claiming
structural hardness from those regimes would be false.

The no-tool route is shorter. Every displayed matching-pair XOR contains one
common power-of-two bit. Intersecting the `n` XORs reveals that bit; selecting
from each pair the endpoint on one fixed level gives a full colour class. This
costs at most `3n-1` exact bit operations—287 at `n=96`—instead of traversing a
dense graph. The hardening loop must still establish whether models can discover
and execute that route. It has **not** done so: OpenRouter rejected every redraw
with HTTP 403 `Key limit exceeded (total limit)`, so the current `hard` shipping
name is provisional and no cross-vendor hardness claim is made.

## Worked demo

This is `render(make_instance(n=4, seed=0, edge_percent=30))` with no hint:

```text
Proper two-colouring of a finite graph

A finite simple undirected graph has vertices 0 through 7. An edge u-v is
unordered. Submit exactly 4 distinct vertices as colour 0; all others are
colour 1, and every edge must cross the two colours.

MATCHING PAIRS:
  0: 0 6
  1: 2 5
  2: 3 7
  3: 1 4

ALL GRAPH EDGES:
  0-4 2-7 1-4 2-5 1-6 0-7 0-6 3-5 2-4 1-5 3-7 3-6 0-5

Give the answer as comma-separated decimal integers inside <answer></answer>.
```

The answer is `<answer>0, 1, 2, 3</answer>`, for which `verify` returns
`(True, "ok")`. Dropping the last vertex returns
`(False, "wrong class size: expected 4, got 3")`. A person can solve and check
this demo on paper: the matching XORs are `6, 7, 4, 5`, whose common changed
bit is `4`.

## Difficulty presets

| preset | matching pairs `n` | vertices | edge density parameter | candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 8 | 30% | `2^4` | hand example; harden skips it |
| easy | 32 | 64 | 35% | `2^32` | oracle run not completed |
| medium | 64 | 128 | 45% | `2^64` | reserve |
| hard | 96 | 192 | 55% | `2^96` | provisional shipping preset; local gates pass |

`escalate()` raises edge density at fixed answer length through 85%. It then
returns `cap_bound`, because raising `n` above 96 would push the intended route
past the 300-operation limit even though the answer still fits 256 atoms.

## Local gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified across all four presets |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged prose-and-fence response round-tripped exactly |
| G4 | 0/200,000 structure-aware guesses; language size `2^96` |
| G5 | exactly two shipping answers, density `2/2^96 = 2.5243548967e-29`; strongest failing attack used 196,608 steps |
| G6 | degree outlier, greedy independent set, 256 restarts, and parity ansatz each solved 0/8; BFS solved 8/8 as expected |
| G7 | all named rungs, doubled `n=192`, and denser fixed-length instances verify |
| G8 | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 422 serialized characters, 96 atoms, about 106 tokens, 287 intended operations |

The exact answer count follows from connectedness: a connected bipartite graph
has exactly two proper 2-colourings, exchanged by swapping the colour names.
`random_candidate` already incorporates the free matching constraint by choosing
one endpoint of every pair.

## Oracle loop and G9 arms

| run | preset | completed attempts | result |
|---|---|---:|---|
| bare | easy | 0/3 | four redraws returned HTTP 403 `Key limit exceeded`; harness aborted |
| structural hint | — | 0/3 | not run, because the same external limit remained |
| placebo hint | — | 0/3 | not run, because the same external limit remained |

There is no `hinted - placebo` estimate and no script-owned `hardened` verdict.
The error-only `llm_loop_transcript.jsonl` and `.meta.json` are retained as the
honest record. The required `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl` cannot be created until the OpenRouter budget is
restored; they have not been hand-written.

## Use

From this directory:

```python
import gen_1910_04896 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY["hard"])
question = g.render(inst)
wire = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

After a successful hardening rerun sets the true shipping preset, emit from the
repository root with:

```bash
bash scripts/emit.sh 1910.04896 20 hard
```

## Caveats

- This is deliberately not evidence of average-case or complexity-theoretic
  hardness. BFS solves the distribution quickly with tools; Track B measures
  whether a no-tool solver notices the shorter invariant.
- The 0/200,000 number only concerns uniform choices of one endpoint per
  displayed matching pair. It says nothing about bitwise, spectral, or BFS
  attacks. BFS is measured separately and always succeeds.
- The symmetric high-degree bait was added after the first generator version's
  degree-ordered greedy attack solved 5/8 instances. One bait lies on each true
  side, so it defeats that greedy route without indicating which side to choose.
- The common-bit construction is a deliberate global label invariant. A solver
  testing endpoint XORs can solve it; whether unaided models find it is exactly
  what the unavailable oracle run still needs to measure.
- Spectral clustering and general SAT/ILP solvers were not separately run:
  linear-time BFS is strictly more direct for a known bipartite graph and is the
  domain-standard reference algorithm here.
- `canonical_key` is invariant under tested vertex and input relabellings but
  uses colour refinement, not complete graph isomorphism; rare collisions can
  over-collapse unrelated marked graphs.
- Only the standard library is needed; `gvlib` is not imported.
