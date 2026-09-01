# Integer layered rectangle-contact witnesses

This generator turns Carolina Haase and Philipp Kindermann’s [*On Layered Area-Proportional Rectangle Contact Representations*](https://arxiv.org/abs/2311.15057) into a bounded `k`-**IntLayeredCrown** search problem. The solver receives fixed-order rows of unit-height rectangles, integer widths, a planar graph of permitted contacts, a canvas, and a target `k`. It returns every integer left x-coordinate. Verification is exact integer interval arithmetic: reject overlap and false adjacency, recompute contacts, and compare the count with `k`. Any qualifying layout is accepted; no optimality claim is checked.

## Why this is a credible hard family

Section 1’s “Problem statement” fixes the conventions that matter here: layer order is fixed, gaps are allowed, contacts have positive length, and nonedge contacts are forbidden. Section 2 proves `k`-IntLayeredCrown NP-complete even for internally triangulated graphs using widths 1, 2, and 3. Its combined construction uses a frame to force a designated bounding box; this module supplies that finite canvas directly. The generated planar graphs are not copies of the reduction gadgets, so the theorem is worst-case support for the containing problem—not an average-case proof for this distribution.

The easy regimes were decisive. The paper cites a linear algorithm for triangulated two-layer instances in Sections 1 and 3.1, while Section 3.2 gives an exact dynamic program taking `O(nW)^L`, XP in the layer count `L` when maximum width `W` is polynomial. Here `W <= 3`, but `L = ceil(layer_ratio*n)` grows with `n`; no preset fixes `L`. Section 3.3’s PTAS approximates the maximum and does not manufacture the required threshold witness.

Generation samples complete geometries first, retains the highest-contact one among a fixed number of independent samples, and only then derives `k` and the graph. Each vertical strip is completed to a random maximal noncrossing staircase containing the planted contacts, so decoys have the same strip, order, width environment, and local degree scale as plants. This preserves planarity and hides which permitted contacts were realized.

## Worked tiny example

For `make_instance(seed=7, **DIFFICULTY["tiny"])`, `render` returns the following complete problem:

```text
INTEGER LAYERED RECTANGLE CONTACT WITNESS

There are unit-height, axis-aligned rectangles on fixed horizontal layers.
Rectangle v(i,j) is on layer i at fixed left-to-right position j, has the
listed positive integer width, and must be assigned an integer left x-coordinate
x[i][j]. All indices are 0-based. Coordinates must satisfy 0 <= x[i][j] and
x[i][j] + width[i][j] <= B. On one layer, rectangles must occur in the
listed order and their interiors may not overlap: x[i][j]+width[i][j] <=
x[i][j+1]. Equality is allowed and is a horizontal contact. Gaps are allowed.

Rectangles on adjacent layers have a vertical contact exactly when their closed
x-intervals overlap in a segment of POSITIVE length. Endpoint-only intersection
has length zero and is not a contact. A horizontal contact exists exactly at
equality for consecutive rectangles on one layer. A contact is permitted only
when its pair appears in the corresponding edge list below; any other contact is
a forbidden false adjacency. Listed edges need not all be realized.

Find coordinates that form a valid representation with at least k realized
listed edges. Each contact counts once. The required answer is one JSON outer
array in layer order, containing exactly one inner array of exactly n integer
left coordinates per layer, in the fixed rectangle order. Repeats are not
allowed because widths are positive; the coordinate order is not permutable.

L = 3
n = 4
B = 8  (right boundary is inclusive for rectangle endpoints)
k = 13

WIDTHS
layer 0: 1 1 1 1
layer 1: 1 1 1 1
layer 2: 1 1 1 1

HORIZONTAL EDGES
layer 0: 0-1 1-2 2-3
layer 1: 1-2 2-3
layer 2: 1-2 2-3

VERTICAL EDGES
layers 0/1: 0-0 0-1 1-1 1-2 2-2 2-3 3-3
layers 1/2: 0-0 1-0 1-1 2-1 2-2 3-2 3-3

Give your final answer inside <answer></answer> tags, as the JSON array
specified above (with the actual L rows and n entries per row).
Example syntax only: <answer>[[0,2,5],[1,4,8]]</answer>
Output nothing else inside the tags.
```

The planted witness is `[[4,5,6,7],[2,4,5,6],[0,4,5,6]]`; `verify(inst, witness)` returns `(True, "ok")`. Removing its final layer-0 coordinate returns `(False, "layer 0 must contain exactly 4 coordinates")`.

## Difficulty presets

| Preset | `n` | `L` | widths | canvas `B` | plant trials | Status |
|---|---:|---:|---:|---:|---:|---|
| `tiny` | 4 | 3 | 1 | 8 | 64 | Readable; all three oracle attempts solved it |
| `standard` | 14 | 14 | 1–3 | 196 | 32 | **Ships; held against all three oracle vendors** |
| `hard` | 22 | 22 | 1–3 | 308 | 40 | Available; not reached because `standard` held |

`SHIPPING_DIFFICULTY = "standard"`. `escalate` multiplies `n` by 1.45, which also grows `L`; planting ensures this cannot make an instance unsatisfiable.

## Mandatory gates

| Gate | Measured result |
|---|---|
| G1 plant | 9/9 witnesses verified (3 presets × 3 seeds) |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 parse | Tagged fenced JSON round-tripped and verified |
| G4 guess | 0/200,000 structure-aware candidates; empirical probability 0 |
| G5 sparse | 69/343,000 exact tiny-case arrays = 0.000201166 |
| G6 attacks | degree-outlier 0/8; minimum-gap beam 0/8; random restart 0/8 |
| G7 scale | `(n,L)=(14,14)` to `(28,28)`; search-space bit length 953 to 3881; plant verified |
| G8 key | 80/80 invariant and carried-witness checks; 20/20 unrelated keys distinct |

## Oracle hardening loop

The script used four-vendor random selection at medium effort. Every reply containing a witness parsed successfully, so no failure below is a parser false negative.

| Preset | Model | Seed | Solved? | Verification result |
|---|---|---:|---|---|
| tiny | Gemini 3.1 Pro Preview | 158926665 | yes | `ok` |
| tiny | GPT-5.6 Terra | 1364974264 | yes | `ok` |
| tiny | Grok 4.6 | 1271319357 | yes | `ok` |
| standard | Claude Sonnet 5 | 847279453 | no | interior overlap at layer 13 positions 7/8 |
| standard | Gemini 3.1 Pro Preview | 1305098805 | no | false horizontal adjacency on layer 2 |
| standard | GPT-5.6 Terra | 1304580897 | no | false horizontal adjacency on layer 2 |

Harness verdict: `hardened`, one escalation, shipping preset `standard`. Full replies and timings are in `llm_loop_transcript.jsonl`; the script-owned master seed and pool are in `.meta.json`.

## Use

```python
from gen_2311_15057 import DIFFICULTY, SHIPPING_DIFFICULTY
from gen_2311_15057 import make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY[SHIPPING_DIFFICULTY])
question = render(inst)
candidate = parse_answer(model_reply)
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh distinct shipping instances with:

```bash
bash scripts/emit.sh 2311.15057 20 standard
```

## Caveats

The NP-completeness result is worst-case and does not prove this planted distribution hard; the oracle result covers only three standard seeds at medium effort. A fixed small `L`, especially two triangulated layers, invokes known easy behavior. A solver implementing the paper’s XP dynamic program, an ILP/SAT encoding, or a stronger global gap search may solve sizes that defeated the tested models.

The 0/200,000 number is not a uniform probability over all valid representations. Its prior uses random compact 0/1 gaps, already enforces bounds/order/nonoverlap and both false-adjacency rules, and does not target high contact count; it measures random guessing under that explicit prior only. The adversary panel did not try full dynamic programming, ILP, simulated annealing, genetic search, or learned attacks.

The canonical key exactly removes edge-list ordering and the ambient horizontal/vertical reflections. Vertex IDs are intrinsic `(layer, fixed-order position)` pairs, so arbitrary vertex-number permutations disappear before the key is formed. It does not attempt abstract planar-graph isomorphism that discards the fixed layer order, because that would identify problems outside this family’s definition.
