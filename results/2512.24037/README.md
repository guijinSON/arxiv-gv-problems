# Perfect directed-triangle kidney exchange

| Axis | Declaration |
|---|---|
| Native domain | Combinatorics |
| Computational core | Exact cover |
| Intended intuition | Recognize perfect directed-triangle packing as exact cover |

`reduction` is `None`: the solver receives the paper's own directed compatibility-graph object, not a discretization of a continuous problem.

This generator turns [*Kidney Exchange: Faster Parameterized Algorithms and Tighter Lower Bounds*](https://arxiv.org/html/2512.24037v1) into a search task.  The solver receives a directed compatibility graph whose vertices are patient–donor pairs.  There are no altruists or chains; it must partition every vertex into directed 3-cycles.  A witness is a sorted JSON list of vertex triples.  Checking it is linear in the witness size after building the edge set: verify the shape, disjoint full coverage, and the three directed arcs of every cycle.

## Why this is a hard regime

Definition 1 in Section 2 fixes the exact graph, length, disjointness, altruist, and patient-target conventions.  Section 1.2 records NP-hardness even for short cycles or chains, while Section 5 proves hardness without altruistic donors.  This family takes their intersection in the standard cycle-only kidney-exchange setting: `B = {}`, `lp = 0`, `lc = 3`, and `t = |V|`.  The exact cap-3 result is background hardness cited by Section 1.2 rather than a new theorem proved in this paper; Section 5's own construction uses longer cycles.

The easy regimes matter.  Section 3 gives a deterministic `O*((4e)^t)` FPT algorithm, so the shipping target grows as `t = 3n`.  The combined treewidth-and-length result discussed in Sections 1.1 and 5 is avoided by letting the random graph's structural width grow.  A cap of 2 would reduce cycle packing to matching, so the generator uses cap 3.  Approximation algorithms mentioned in Section 1.2 do not certify the required perfect cover.

The answer is sampled first as a uniform random partition and cyclic orientation.  Random 3-cycles drawn from the same triple/orientation distribution are then added at the empirically difficult exact-cover density.  Every vertex is planted exactly once, so there is no planted-vertex class for a degree test to isolate.  Reverse arcs are rejected uniformly to keep the graph oriented.  Shipping draws are resampled if minimum-column Algorithm X finds a cover within 50,000 nodes.

The bounded certificate language consists of canonical JSON partitions of vertices `0` through `3n-1` into exactly `n` unlabeled triples.  Each triple has three distinct, increasing integers; triples are lexicographically sorted; and every vertex occurs once.  `random_candidate` samples uniformly from exactly these partitions, and `search_space` counts the same language as `(3n)! / ((3!)^n n!)`; neither function needed to change.

## Worked example

This is the complete `example` preset at seed 7:

```text
Kidney exchange — perfect directed 3-cycle packing

There are 9 patient-donor pairs, numbered 0 through 8.
There are no altruistic donors, so paths/chains are not allowed.  A directed edge
u -> v means that u's donor is compatible with v's patient.  The graph has no
self-loops and never contains both u -> v and v -> u.

A legal exchange is a directed cycle with at most 3 edges.  Because this graph is
oriented as stated above, it has no 1- or 2-edge cycles; every legal exchange is
therefore a directed 3-cycle on three distinct vertices.  For a sorted triple
[a,b,c], it is a directed 3-cycle exactly when either the edges a->b, b->c, c->a
all exist or the edges a->c, c->b, b->a all exist.

Find exactly 3 pairwise vertex-disjoint directed 3-cycles.  They must
cover all 9 vertices, so every patient receives a kidney.  A vertex
may appear in exactly one triple.  Vertex numbering is 0-based.  Within each
triple list the three vertex numbers in strictly increasing order; sort the list
of triples lexicographically.  No repeats are allowed, and order otherwise has
no meaning.

The adjacency list below gives every directed edge.  A dash means no outgoing
edges.  No edges other than those listed exist.

0: 8
1: 6
2: 5
3: 2
4: 0
5: 3
6: 7
7: 1
8: 4

Give your final answer inside <answer></answer> tags, as one JSON array containing
exactly 3 three-integer arrays in the canonical sorted order just
specified.
Example format: <answer>[[0, 1, 2], [3, 4, 5]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[0, 4, 8], [1, 6, 7], [2, 3, 5]]</answer>`, and `verify` returns `(True, "ok")`.  Dropping vertex 8 gives `[[0, 4], [1, 6, 7], [2, 3, 5]]`; verification returns `(False, "cycle 0 has 2 vertices; expected 3")`.

## Difficulty presets

| Preset | Planted cycles | Vertices | Deliberate decoys | Exact-cover screen | Status |
|---|---:|---:|---:|---:|---|
| `example` | 3 | 9 | 0 | none | Illustrative only; Algorithm X solves it immediately |
| `hard` | 60 | 180 | 360 | 50,000 nodes | **Shipping; oracle-hardened** |

`escalate()` preserves the decoy density and raises `n` by 20 up to 120.  At fixed density this enlarges the critical planted exact-cover core; the doubled `n=120` instance built and verified in G7.

## Local gate results

| Gate | Measurement | Result |
|---|---|---|
| G1 | 2 presets × 4 seeds; 8/8 plants verified | pass |
| G2 | drop, swap, duplicate, empty, out-of-range; 5/5 rejected for 5 distinct reasons | pass |
| G3 | tagged JSON recovered through prose/fence; garbage returned `None` | pass |
| G4 | structure-aware uniform triple partitions: 0 hits / 200,000 | pass |
| G5 | Shipping `hard`, seed 2024: 0/200,000 sampled certificates valid; Algorithm X stopped at 50,001 nodes in 2.582303597126156 s without a witness. Additional exact `n=5` count: 39/1,401,400 | pass |
| G6 | degree outlier, greedy, 256 restarts, Algorithm X: each 0/8 | pass |
| G7 | `n=120`: 360 vertices, 2,461 arcs, planted witness verifies | pass |
| G8 | 80/80 invariance + carried-witness checks; 20/20 unrelated keys distinct | pass |

The full machine-readable measurements are in `selftest_report.json`.

## Oracle loop

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| `example` | 1796983193 | GPT-5.6 Terra | yes | witness parsed and verified |
| `example` | 282140383 | Grok 4.6 | yes | witness parsed and verified |
| `example` | 125494308 | Gemini 3.1 Pro Preview | yes | witness parsed and verified |
| `hard` | 692572285 | Claude Sonnet 5 | no | no final content; 32,000 completion tokens, `finish_reason=length` |
| `hard` | 84405690 | Gemini 3.1 Pro Preview | no | parsed; cycle 0 was not a directed cycle |
| `hard` | 1044253582 | Grok 4.6 | no | no final content after 22,021 completion tokens |

The harness verdict is `hardened`, with master seed `12875438686292856258`, medium reasoning effort, one escalation from `example` to the named `hard` preset, and no hand-tuned post-ladder parameters.  The full replies and required metadata are in `llm_loop_transcript.jsonl` and `.meta.json`.

## Use

```python
from gen_2512_24037 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, after a hardened verdict:

```bash
python3 results/2512.24037/gen_2512_24037.py
python3 scripts/harden.py results/2512.24037/gen_2512_24037.py
bash scripts/emit.sh 2512.24037 20 hard
```

## Caveats

G4 and the shipping-preset G5 density measurement sample uniformly from all partitions into unlabeled triples.  This already grants a guesser the required arity, disjointness, full coverage, and canonical order, but it does not condition every sampled triple on being a graph cycle—doing that for a complete partition is the exact problem being measured.  Zero hits in 200,000 samples is an observed fraction, not an exact density or a distribution-free upper confidence bound.  The exact `n=5` count is included only as an additional small-instance measurement, never as a substitute for shipping `n=60`.

On the measured shipping instance, the strongest G6 baseline—minimum-column Algorithm X—used 50,001 search calls and 2.582303597126156 local wall-clock seconds before its 50,000-node budget cut it off.  That is a modest measured cost, not evidence that unrestricted exact search is expensive; it also did not exhaust the tree, so failure alone says little.  Larger exact search, branch-and-price, a commercial ILP/CP-SAT solver, or a better randomized row ordering may succeed.  No LP relaxation, SAT encoding, or commercial optimizer was run.  The family is a planted distribution inside an NP-hard problem class; worst-case NP-hardness alone does not prove average-case hardness.  Generation explicitly conditions on failure of the stated Algorithm X screen and may therefore bias the distribution.  In the hard oracle round, two of three decisive vendors emitted no final answer; only Gemini emitted a parsed, incorrect witness.  Thus the oracle evidence is valid under the fixed 32,000-token harness policy but is weaker than three independently wrong completed witnesses, and a higher-token rerun could change the result.

`canonical_key` uses directed 1-dimensional Weisfeiler–Leman refinement and normalizes global arc reversal.  It is invariant under arbitrary vertex renumbering and input edge order in the tests, but it is not a complete directed-graph isomorphism algorithm and can theoretically collide on non-isomorphic regular graphs.  Finally, Section 6 of the paper appears inconsistent with Definition 1 about whether altruists count toward `t` and whether path length counts edges; its fixed-target hardness wording is also suspect.  None of those Section 6 claims are used by this generator.
