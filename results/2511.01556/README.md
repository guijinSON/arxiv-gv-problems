# Affine `K4`-cover certificates for removable edge sets

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | matrix certificate |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

This generator turns Davide Mattiolo's [*On removable edge subsets in graphs
with a nowhere-zero 4-flow*](https://arxiv.org/abs/2511.01556) into a search for
an affine cover projection from a cubic graph to `K4`.  The solver receives the
graph and a distinct binary coordinate on every vertex, and returns a rank-two
binary matrix plus a two-bit offset.  The matrix must map every closed
neighbourhood bijectively onto the four vertices of `K4`.

The certificate is native to Section 2's flow-continuous-map machinery.  It
induces an edge map to `K4`; the verifier deletes the fibre of edge `{0,1}` and
explicitly pulls back the fixed flow
`f02=1, f03=-1, f12=1, f13=-1, f23=2`.  It checks the cover locally, counts the
six fibres, and recomputes integer conservation at every vertex.  It never
reads the planted answer or invokes a solver.

## Why Track B

This is not a Track A claim.  Section 1 of the paper gives a linear construction
for cubic graphs once a proper 3-edge-colouring is known, and Section 3 is
linear once a flow-continuous map is supplied.  Theorem 2.2 identifies the
existence of such a map with a nowhere-zero 4-flow; Lemma 2.1 and the proof of
Theorem 1.2 license the deletion-and-pullback certificate used here.

The domain-standard reference route computes the exact `-1` eigenspace of the
`768 x 768` adjacency matrix by modular Gaussian elimination, quotients an
occasional one-dimensional accidental eigenspace, groups the four fibre-constant
row signatures, and fits the affine matrix.  It is polynomial, `O(n^3)`,
succeeds 8/8 as expected, and used 121,489,118 modular field operations in
8.4607 seconds across eight shipping instances (at most 16,283,642 operations
for one).  The compact route notices that, at a vertex, XORing the three
endpoint differences yields a vector annihilated by both hidden matrix rows.
The first `d+2=18` such signatures already have rank `d-2=14` by construction;
their nullspace recovers a valid matrix in at most 213 packed XOR/parity
operations.  That is the measured compression gap.  A provisional 96-vertex
rung was not shipped because the exact eigenspace reference decoder was not
reliable across the mandated eight-seed G6 panel.

## Worked demo

Here is `render(make_instance(n=8, coordinate_bits=4, seed=0))` in full.

```text
Affine K4-cover certificate for a removable edge set

The undirected graph below has 8 vertices, indexed 0 through 7, and 12 edges,
indexed 0 through 11. It is simple, connected, and cubic: every vertex has
degree three. Each vertex v also carries a distinct vector x(v) in GF(2)^4.
In a displayed bit string, the leftmost character is coordinate 3 and the
rightmost is coordinate 0.

Find a two-row binary matrix A and a two-bit offset b. For a vertex v define

  c(v) = A x(v) + b  in GF(2)^2,

where all sums and products are modulo 2. Interpret [q0,q1] as the K4 vertex
q0 + 2*q1 in {0,1,2,3}. Your map must be a K4-cover projection: for every
vertex v, the four values consisting of c(v) and the values on its three
neighbours must be exactly {0,1,2,3}.

Why this certifies the paper's removable-set claim is checked explicitly.
Every graph edge maps to the K4 edge joining its endpoint classes. The checker
deletes all edges mapping to {0,1} and pulls back this fixed integer 3-flow on
K4-{0,1}, with each base edge oriented from its smaller to its larger endpoint:

  f(0,2)=1, f(0,3)=-1, f(1,2)=1, f(1,3)=-1, f(2,3)=2.

It then checks that the deleted fibre has at most one sixth of all edges, every
retained value is nonzero with absolute value at most 2, and the exact incoming
and outgoing sums agree at every source vertex. Thus the answer is a compact
formula for a concrete removable set and a concrete nowhere-zero 3-flow, not an
existence assertion.

Vertex coordinates x(v):

0: 0001
1: 1111
2: 1100
3: 1001
4: 1011
5: 0011
6: 0110
7: 1000

Edges (edge_index: endpoint endpoint):
0: 2 5
1: 3 6
2: 7 4
3: 2 6
4: 1 7
5: 3 5
6: 1 4
7: 5 6
8: 0 7
9: 1 2
10: 3 0
11: 0 4

Return one JSON object with exactly these fields:
  "matrix": two rows, each a JSON array of exactly 4 integer bits in
            coordinate order [0,1,2,3];
  "offset": exactly two integer bits [b0,b1].
Rows must be distinct and nonzero (equivalently, full row rank over GF(2)).
Every bit must be the integer 0 or 1; booleans are not accepted.

Give your final answer inside <answer></answer> tags, as that one JSON object.
Syntax-only example for d=4:
<answer>{"matrix":[[1,0,1,0],[0,1,1,0]],"offset":[0,1]}</answer>
Output nothing else inside the tags.
```

A valid answer is:

```json
{"matrix":[[0,1,1,1],[1,1,1,0]],"offset":[1,1]}
```

`verify` returns `(True, "ok")`.  Replacing the second row by a copy of the
first returns `(False, "the two matrix rows must be nonzero and linearly
independent")`.  This demo is genuinely hand-scale: one can tabulate the four
class values for eight vertices and check all twelve edges.

## Difficulty presets

| Preset | Vertices | Edges | Coordinate bits | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 12 | 4 | 10 | hand example; skipped by hardener |
| easy | 192 | 288 | 16 | 34 | not shipped: G9 structural hint solved |
| medium | 384 | 576 | 16 | 34 | not shipped: bare Grok solved |
| hard | 768 | 1152 | 16 | 34 | **ships**; all final arms hardened |

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted certificates verified |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | tagged prose/JSON round-trip; answer is JSON-native |
| G4 | pass | 0 hits / 200,000 structure-aware guesses; language size 17,179,082,760 |
| G5 | pass | shipping density 0/200,000; demo exactly 24/840; reference cost above |
| G6 | pass | four attacks each 0/8; reference eigenspace algorithm 8/8 |
| G7 | pass | 768 to 1536 vertices, 1152 to 2304 edges; answer remains 34 atoms |
| G8 | pass | 140 invariance and 160 witness-transport checks; 20/20 distinct seeds |
| G9 | pass | 95 chars, about 24 tokens, 34 atoms; compact route at most 213 operations |

The four failing G6 attacks were the best individual-coordinate pair, greedy
no-backtracking `K4`-cover colouring followed by affine fitting, 256 random
full-rank matrix restarts, and the two-low-bits hand ansatz.  The successful
spectral algorithm is reported separately, as Track B requires.

## Bare oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| medium | 1183618295 | Gemini 3.1 Pro | failed | unequal affine fibres |
| medium | 789755146 | GPT-5.6 Terra | failed | unequal affine fibres |
| medium | 517475618 | Grok 4.6 | **solved** | verified `ok`; escalated |
| hard | 216623359 | Gemini 3.1 Pro | failed | unequal affine fibres |
| hard | 1273226062 | Claude Sonnet 5 | failed | response exhausted its 32k completion budget |
| hard | 141439176 | GPT-5.6 Terra | failed | unequal affine fibres |

The empty Claude response is a caveat: the harness deliberately counts a
completed, length-limited empty response as unsolved.  The other two deciding
hard-rung vendors returned parsed but invalid matrices.  In the transcript this
final rung is named `escalated`; after it held, it was promoted to the module's
named `hard` preset as required by the ladder contract.

## G9 arms

| Arm | Solved / completed attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`.  The hint named the correct XOR invariant but
did not measurably improve this oracle pool: executing the remaining exact
reduction still mattered.  The structural and placebo arms each include one
completed Claude response that exhausted its 32k completion budget; all other
final-arm vendors returned parsed but invalid matrices.  The serialized answer
is 95 characters, about 24 tokens and 34 atomic bits; the intended route uses
at most 213 packed exact operations.

## Use

```python
from gen_2511_01556 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit fresh shipping instances with:

```bash
bash scripts/emit.sh 2511.01556 20 hard
```

## Caveats

The family becomes easy if the affine matrix, the four vertex fibres, a
3-edge-colouring, or the flow-continuous edge map is supplied; those are
exactly the easy regimes identified above.  The 0/200,000 guess result is only
for uniform ordered full-rank matrices with uniform offsets.  It is not a
lower bound against correlated algebraic guesses; indeed the XOR-nullspace
decoder always succeeds.

The panel did not run an SDP or a general-purpose graph-cover package.  It did
run the relevant exact spectral method to completion.  Its strengthened
decoder handles a one-dimensional accidental `-1` eigenspace, as observed in
testing, but not higher accidental nullity; this did not occur on the shipping
panel.  The modular
eigenspace route is unusually fast in wall-clock time in Python despite its
operation count, so this benchmark claims no computational resource hardness.
It claims a no-tool compression gap.  Finally, `canonical_key` uses sorted
all-vertex distance histograms.  This is invariant under vertex renumbering and
all affine coordinate changes tested, but it is not a complete cubic-graph
isomorphism canonizer; rare non-isomorphic collisions can therefore be
over-collapsed, never spuriously counted as diverse.
