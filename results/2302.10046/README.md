# Orthogonal drawing extension generator (arXiv:2302.10046)

**Trust status:** complete. All local gates pass, and the script-owned bare
oracle loop hardened at `medium`: `easy` was solved on two of three attempts,
then all three `medium` attempts failed.

| Profile field | Value |
|---|---|
| Track | **B** — an efficient reference algorithm exists and is disclosed |
| Native domain | geometry |
| Object regime | integer lattice, exact throughout |
| Computational core | graph path search in an orthogonal face |
| Certificate form | exact symbolic orthogonal polyline |
| Intended intuition | decomposition by nested one-gap separators |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 5.1, Definition 12 and Section 5.2, Corollary 16 license the sector-adjacency graph and finite grid representation |

## Problem and construction

The source is Bhore, Ganian, Khazaliya, Montecchiani, and Nöllenburg,
[“Extending Orthogonal Planar Graph Drawings is Fixed-Parameter
Tractable”](https://arxiv.org/abs/2302.10046). Section 2 defines
Bend-Minimal Orthogonal Extension (BMOE): a connected maximum-degree-four
planar graph `G`, a connected subgraph `H` with a fixed planar orthogonal
drawing `Gamma(H)`, and a total bend budget. Here `Gamma(H)` is the exact wall
drawing of a perfect rectilinear maze and `G` adds one missing edge `ST`. The
solver returns an integer-coordinate orthogonal polyline for that edge. The
checker uses exact endpoint, bend, frame, segment-intersection, and
self-intersection tests; it accepts any valid extension and never reads the
planted answer.

Generation is a composition of certified objects, not a solve. Recursive
division produces two cell trees, connects them through one sampled gap, and
composes their already-held endpoint paths through that gap. Extra blocks are
built by the same law and attached through one gap, so they are branches that
cannot change the unique `S`-to-`T` cell route. Route and decoy gaps use the
same distribution. Section 5.1, Definition 12 explicitly turns geometric
sector adjacency into a graph, and Section 5.2, Lemma 15 and Corollary 16 show
that exact finite feature-point sets suffice. This paper-central representation
licenses the cell-complex search. The solver is still handed the native wall
drawing, returns a native polyline, and is graded by geometric operations.

## Why this is Track B

Track A would be false. The Introduction records a linear algorithm for
extension existence without bend minimization, a polynomial flow algorithm
for fixed-embedding bend minimization, and a linear algorithm at maximum
degree three. Section 6, Lemma 23 and Corollary 24 solve BMOE in
`2^(kappa^O(1)) * N` time. This specialization has one missing edge, so
`kappa=1`; the paper's general NP-hardness statement is not a claim about this
generated distribution.

The executable reference algorithm expands the **public wall list**, builds
all cell adjacencies, and runs BFS in `O(R*C + |walls|)`. At shipping seed
271828 it processes 1,872 cells in 7,967 charged exact operations and 0.002809
seconds; across eight attack seeds it succeeds 8/8 with 65,300 operations in
0.019845 seconds. The compact route notices that blocks joined through a sole
gate and containing neither endpoint are irrelevant, then searches only the
12-by-12 endpoint block shown in ASCII. It takes 120 charged cell decisions and
coordinate writes at seed 271828 and at most 178 across the eight seeds. Thus
tools solve the family efficiently, while the intended no-tool task is to find
the decomposition that compresses thousands of mechanical checks below the
300-operation cap.

## Worked demo

This is the complete no-hint rendering of
`make_instance(seed=0, **DIFFICULTY["demo"])`:

```text
BEND-BOUNDED ORTHOGONAL DRAWING EXTENSION

A fixed planar orthogonal drawing Gamma(H) is given by the closed wall
segments listed below. Every segment is horizontal or vertical. Segment
endpoints, every meeting point, and the marked points S and T are vertices
of H; S and T subdivide their incident wall segments. Touching listed
segments share a vertex rather than crossing. H is connected.
The closed frame is [0,W] x [0,H].

The graph G adds exactly one missing edge from the marked vertex S to the
marked vertex T. Draw that edge as one simple orthogonal polyline. Its
interior may not meet or overlap any listed wall, and may not touch any
vertex or edge of Gamma(H). The polyline may meet Gamma(H) only at S and T.
It must stay in the closed frame and have at most beta bends. A bend is an
internal point where a horizontal segment and a vertical segment meet.

W=6  H=6  beta=4
S=[0,1]
T=[6,5]

For exact visual tracing, the square 0<=x<=W, 0<=y<=W containing S and
T is also shown as an ASCII lattice below. Character column x is the
integer x-coordinate and each row is labelled by its integer y-coordinate;
'-' and '|' are wall points, '+' is their meeting, and blanks are free.
This is a redundant view of the wall list, not additional geometry.
ENDPOINT_BLOCK_ASCII
y=06 +-----+
y=05 |     T
y=04 +-- --+
y=03 |     |
y=02 | | | |
y=01 S | | |
y=00 +-+-+-+
END_ENDPOINT_BLOCK_ASCII

WALLS=8
0: 0 0 6 0
1: 2 0 2 2
2: 4 0 4 2
3: 0 4 2 4
4: 4 4 6 4
5: 0 0 0 6
6: 6 0 6 6
7: 0 6 6 6

Output a JSON list of points [[x0,y0],[x1,y1],...,[xm,ym]] in order
from S to T. Coordinates must be integers. Include S, T, and every bend
point, but no other collinear intermediate points. Consecutive points
must be distinct and share exactly one coordinate. Indices are zero-based;
all bounds are inclusive; repeated points and self-intersections are forbidden.

Give your final answer inside <answer></answer> tags, as the JSON point list.
Format-only example: <answer>[[0,1],[1,1],[1,3],[3,3]]</answer>
Output nothing else inside the tags.
```

The answer is `[[0,1],[1,1],[1,3],[3,3],[3,5],[6,5]]`; `verify` returns
`(True, "ok")`. Dropping its first bend is rejected with
`axis: segment 0 is not horizontal or vertical`. A person can solve this demo
by tracing the seven-row maze. Its bounded certificate language has 160
candidates and exactly one valid answer.

## Presets and gates

| Preset | `n` | Decoy blocks | Minimum route cells | Answer-atom cap | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 0 | 2 | 80 | hand-solvable example |
| easy | 8 | 4 | 16 | 180 | oracle solved 2/3; rejected as shipping level |
| **medium** | **12** | **12** | **36** | **220** | **ships; oracle solved 0/3** |
| hard | 16 | 40 | 48 | 256 | local gates pass; not reached because medium held |

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses plus construction invariants and JSON checks |
| G2 | pass | five corruptions rejected by five distinct reason classes |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structured guesses; 158-bit sampled language at seed 271828 |
| G5 | pass | shipping density 0/200,000; demo exact count 1/160; reference 7,967 operations |
| G6 | pass | four attacks 0/8 each; reference BFS and compact solver both 8/8 |
| G7 | pass | 1,872 to 6,400 cells; planted answer 52 to 60 atoms in the scaling check |
| G8 | pass | 320/320 real isometry/order/endpoint-swap checks; 20/20 unrelated keys distinct |
| G9(c) | pass | measured 202 chars, 56 atoms, about 51 tokens, 120 operations; worst bounds 991/220/248/300 |

## Oracle loop

| Preset | Seed | Model | Solved? | Checker result |
|---|---:|---|---|---|
| easy | 1524301503 | OpenAI GPT-5.6 Terra | no | wall intersection |
| easy | 1809978070 | Google Gemini 3.8 Flash | yes | verified |
| easy | 22810020 | Google Gemini 3.8 Flash | yes | verified |
| medium | 363228882 | Google Gemini 3.8 Flash | no | empty length-limited response |
| medium | 2049158509 | OpenAI GPT-5.6 Terra | no | bend budget exceeded |
| medium | 1440480894 | OpenAI GPT-5.6 Terra | no | claimed no valid drawing; no parseable witness |

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 2/3 | naming the one-gap separator often unlocks the route |
| placebo | 1/3 | some lift comes from prompt variation alone |

`hinted - placebo = 1/3`. The positive difference supports the declared
`decomposition` intuition, while the placebo success and one hinted failure
show that three trials are only a diagnostic. The hint makes the shipping
level too easy in the harness sense; this is non-gating and is evidence that
the difficulty lies partly in discovering the structure. The measured answer
is 202 characters/56 atoms and the compact route takes 120 operations.

## Use

```python
from gen_2302_10046 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2302.10046 20 medium
```

## Caveats

This family is deliberately easy with tools: exact BFS is the disclosed Track
B reference. The 0/200,000 figure samples endpoint- and port-correct,
alternating, nonzero, up-to-budget lattice polylines, but does not condition on
wall avoidance or global self-avoidance; it may understate the success of a
stronger geometric proposal distribution. Generation also conditions on the
four declared cheap attacks failing, so the distribution is adversarially
filtered rather than an unconditioned random-maze distribution.

The panel does not implement a visibility-graph solver, SAT/SMT encoding, or
the paper's full sector-treewidth dynamic program. One of the three bare
medium failures exhausted its reasoning-token allowance, so the hardening
evidence contains two substantive wrong answers and one resource failure. A
medium rendering is about 18,000 characters; prompt length may contribute to
difficulty, although the exact 12-by-12 endpoint view keeps the intended route
within the no-tool effort cap. No claim of Track A or average-case
complexity-theoretic hardness is made.
