# Quadratic correspondence colouring on paper-defined covers

**Status: parked, not shippable yet.** The module passes every local gate, but
OpenRouter returned HTTP 403 “Key limit exceeded” on every redraw in the
required bare, structural-hint, and placebo runs. Those harness-owned error
transcripts are retained; they are not evidence that any model failed.

| profile field | value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | polynomial: two exact quadratic Boolean polynomials |
| Intended intuition | invariant: the matching shifts are a quadratic edge coboundary |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust boundary

Section 2.1 of Davies, Kang, Pirot, and Sereni, [*Graph structure via local
occupancy*](https://arxiv.org/abs/2003.14361), defines a correspondence cover
`H=(L,H)` and an `H`-colouring as an independent transversal of its local
lists. An instance here gives a dense regular bipartite base graph and a
2-fold cover. A bit `s` on base edge `Li-Rj` matches local colour `z` at `Li`
to the conflicting colour `z XOR s` at `Rj`.

The witness is a compact `H`-colouring: one squarefree degree-two Boolean
polynomial of the public vertex code on each side. Generation samples the two
polynomials first and writes every edge shift as
`f_L(x) XOR f_R(y) XOR 1`; the sampled colours therefore never meet a matching
edge. Verification independently expands any submitted polynomials and checks
every displayed matching. It never reads `inst["answer"]`.

Theorem 12 is the paper's broad existence theorem for correspondence colourings
from strong local occupancy. This generator does not claim that theorem covers
arbitrary 2-fold covers: its list-size hypotheses are not the regime used here.
Existence is instead known by inverse generation, using exactly the paper's
cover and independent-transversal objects.

## Why Track B

This is not a Track A claim. For a satisfiable 2-fold cover, avoiding each
matching is an XOR equality. Signed-graph breadth-first propagation solves the
cover in `O(|V|+|E|)` after it is read; the displayed dense table makes the
measured implementation `O(n^2+|E|)`. At `hard` it solved 8/8 instances in
61,866 counted scans/XORs, with a 0.048558 s mean in the G6 audit.

The compact route notices the edge-coboundary invariant. Values at code `0`,
each unit code, and each pair of unit codes determine every coefficient by
finite differences. At dimension 9 that takes
`2d + 6*C(d,2) + 1 = 235` XORs, without propagating through the remaining
20,448 cover edges. Section 8.4 supplies the paper's algorithmic warning:
local-occupancy hypotheses do not automatically give polynomial algorithms for
correspondence colouring, although the companion results do for certain list
colourings. Our much narrower 2-fold promise is explicitly easier, hence Track
B and the successful reference algorithm.

## Worked demo

`make_instance(seed=0, n=8, dimension=3, degree=7)` renders:

```text
Quadratic 2-fold correspondence colouring over F_2.

The base graph is bipartite with left vertices L0,...,L7 and
right vertices R0,...,R7.  Each vertex has degree 7.
Every vertex v has a two-element local list {(v,0),(v,1)}.
The two elements inside one local list conflict with each other.

For every base edge Li-Rj, the table entry s in {0,1} specifies the
perfect matching of conflicts between their lists: (Li,z) conflicts
with (Rj,z XOR s) for both z=0 and z=1.  A dot means Li-Rj is not
a base edge and creates no cross-list conflict.  XOR is addition mod 2.

An H-colouring chooses exactly one local-list element at every base
vertex and contains no conflicting pair.  You must give such a colouring
in the promised quadratic form below; at least one is guaranteed.

Each vertex carries a public code x=(x0,...,x2) in F_2^3;
write d=3 for this code dimension.
A coefficient list first gives the constant c, then the linear
coefficients a0,...,a_(d-1), then one quadratic coefficient b_ij
for every pair 0 <= i < j < d in lexicographic (i,j) order:
  c XOR XOR_i(ai AND xi) XOR XOR_(i<j)(b_ij AND xi AND xj).
Give one coefficient list for all left codes and one for all right codes.
All coefficients must be literal integers 0 or 1 and may repeat.
Vertex order is fixed by the indices below.

Left codes (the first displayed bit is x0):
L0: 100
L1: 011
L2: 101
L3: 000
L4: 010
L5: 001
L6: 110
L7: 111

Right codes (the first displayed bit is x0):
R0: 010
R1: 001
R2: 100
R3: 110
R4: 000
R5: 111
R6: 101
R7: 011

Matching-shift table: row i is Li; character j is the entry for Rj.
Columns are 0-indexed from left to right, with exactly n characters per row.
L0: 01.10010
L1: 011100.0
L2: 1000110.
L3: 01110.10
L4: 0.110010
L5: .0001101
L6: 100.1101
L7: 1000.101

Output one JSON object with exactly the keys left and right.  Each value
must be a list of exactly 7 bits: constant; x0,...,x2;
then x0*x1,x0*x2,...,x0*x_(d-1),x1*x2,... in lexicographic pair order.
Give your final answer inside <answer></answer> tags, as that exact JSON object.
Example of the required syntax and shape: <answer>{"left":[0,0,0,0,0,0,0],"right":[0,0,0,0,0,0,0]}</answer>
Output nothing else inside the tags.
```

The answer is
`{"left":[0,0,0,1,1,0,1],"right":[1,1,0,1,0,1,1]}`.
`verify(inst, answer)` returns `(True, "ok")`; deleting the last left
coefficient returns `(False, "left quadratic rule is too short: expected 7
coefficients")`. A person can solve this demo on paper by reading the 0, unit,
and pair-unit anchor entries.

## Difficulty and gates

| preset | vertices/side | dimension | degree | rendered chars (seed 0) | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 3 | 7 | 2,193 | hand-solvable; hardener skips it |
| easy | 64 | 7 | 62 | 8,167 | local gates pass; oracle blocked before scoring |
| medium | 96 | 8 | 94 | 14,535 | local gates pass; oracle not reached |
| hard | 144 | 9 | 142 | 28,146 | provisional shipping preset; local gates pass |

`SHIPPING_DIFFICULTY` is provisionally `hard`; there is no shipping hardness
claim until the bare harness returns `hardened`. A prior affine version was
discarded after a live oracle solved its easy rung. During construction, the
row/column-bias attack then solved 5/8 quadratic instances; balancing every
non-demo row and column reduced that attack to 0/8 before the final audit.

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed witnesses verify; 12/12 JSON round trips |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged fenced/prose response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 shaped guesses; exact fraction `2/2^92 = 4.039e-28` |
| G5 | pass | exactly 2 shipping witnesses; BFS 61,866 operations, 0.047045 s mean |
| G6 | pass | six attacks each 0/8; reference BFS 8/8 as expected |
| G7 | pass | `n=288` builds/verifies with the answer fixed at 92 atoms |
| G8 | pass | 140/140 invariance/witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 204 chars, 51 estimated tokens, 92 atoms, 235 intended XORs |

The six G6 attacks are constant, left-first greedy, row/column marginal bias,
single-monomial, affine-only, and 256 random restarts. Regularity removes degree
outliers; balanced row and column labels defeat marginal bias; dense linear and
quadratic supports defeat the simple ansatzes.

## Oracle and G9 diagnostics

The bare harness stopped before its first scored slot. Its four records are:

| preset | seed | model | result |
|---|---:|---|---|
| easy | 1,756,352,294 | GPT-5.6 Terra | HTTP 403 key total limit |
| easy | 819,454,938 | Gemini 3.8 Flash | HTTP 403 key total limit |
| easy | 1,581,763,008 | GPT-5.6 Terra | HTTP 403 key total limit |
| easy | 1,193,581,359 | GPT-5.6 Terra | HTTP 403 key total limit |

| G9 arm | solved/completed attempts | harness records | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 errors | blocked before scoring |
| structural hint | 0/0 | 4 errors | blocked before scoring |
| placebo hint | 0/0 | 4 errors | blocked before scoring |

Hinted minus placebo is undefined, so nothing can yet be concluded about the
claimed invariant intuition. This is an external block, not a failed gate and
not a reason to reject the paper.

## Use

```python
from gen_2003_14361 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
```

After OpenRouter quota is restored, rerun the bare hardener here and both G9
arms in separate scratch directories, update `G9_RESULTS`, rerun `selftest()`,
and then emit from the repository root:

```bash
python3 scripts/harden.py results/2003.14361/gen_2003_14361.py
bash scripts/emit.sh 2003.14361 20 hard
```

## Caveats

This is a narrow promise subclass: 2-fold, satisfiable, bipartite, dense,
regular, and promised to have quadratic rules on public Boolean codes. A
tool-enabled solver should use signed BFS and will solve it quickly—that is the
Track B premise. The exact `2/2^92` guess rate is for uniform correctly shaped
quadratic coefficient lists; it does not model an informed solver who detects
the coboundary or exploits correlations in the balanced code sets. The graph
distribution is conditioned on balanced planted colours and protected anchor
edges, not uniform over regular bipartite graphs.

No SAT, ILP, or spectral package was benchmarked because exact signed
propagation strictly dominates them on this 2-fold subclass. The canonical key
uses affine difference multiplicities and deterministic colour refinement; it
is invariant under all audited affine relabellings but can still collide on
nonisomorphic coded covers. Finally, the multi-vendor no-tool evidence required
for release is absent until the external OpenRouter limit is repaired.
