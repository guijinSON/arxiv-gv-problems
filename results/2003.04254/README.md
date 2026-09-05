# Affine fall-coloring generator for arXiv:2003.04254

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph (solved through an exact GF(2) invariant) |
| certificate form | matrix certificate |
| intuition | invariant: closed-neighborhood coordinate XORs are annihilated by the coloring map |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

This module instantiates the fall-coloring problem treated in Section 3.6 of [*b-Coloring Parameterized by Clique-Width*](https://arxiv.org/abs/2003.04254). A fall coloring is a proper coloring in which every vertex has a neighbor in every other color, so every vertex is a `b`-vertex. The solver receives a finite simple 7-regular graph, distinct GF(2) coordinates on its vertices, and an affine coordinate frame. It must return a full-rank three-row binary matrix and three-bit offset whose eight induced colors form a fall coloring. The controlled-vocabulary core is `graph` because validity is the paper's fall-coloring predicate; the compact solution route uses exact GF(2) linear algebra. `verify` expands the affine map, checks every edge, and checks every closed neighborhood exactly; it never reads the planted answer.

Generation is inverse. The module samples the affine certificate first, draws equally many coordinates in its eight fibers, and connects every pair of fibers by an independently shuffled perfect matching. Every closed neighborhood therefore contains exactly one vertex of every color. Rejection sampling enforces connectivity and the promised presentation properties, but it never obtains the returned certificate by solving the generated instance.

## Why Track B

This is not a Track A claim. Theorem 3.20 gives an `n^(2^O(w))` fall-coloring algorithm when a module-width-`w` branch decomposition is supplied, and Proposition 3.21 gives a matching worst-case parameterized lower bound; neither proves hardness for this generated distribution. For `b`-coloring, Corollary 2.10 is FPT in vertex-cover number and Corollary 2.11 is FPT on chordal graphs parameterized by the number of colors. The paper also records polynomial fall-coloring cases for strongly chordal, threshold, and split graphs. The generator claims none of those regimes.

For this distribution, a construction-specific polynomial decoder exists and is disclosed: take the nullspace of adjacency-plus-identity over GF(2), recover the eight cover fibers, and fit an affine projection. Packed exact Gaussian elimination costs `O(n^3/word_size)`. On eight shipping instances it solved 8/8 in 1.108 seconds total and 1,023,502 packed exact operations, with at most 129,261 operations for one instance. That is easy for software but out of reach by hand. The compact route notices that each closed-neighborhood coordinate XOR lies in the kernel of the coloring map; exact elimination on a few such signatures used at most 262 packed operations. The benchmark tests whether a no-tool solver finds this compression, not whether the instances defeat software.

## Worked demo

The `demo` preset with seed 3 is hand-scale. Here is the complete output of `render`:

```text
Affine certificate for an eight-color fall coloring

The undirected graph below has 16 vertices numbered 0 through 15.
It is finite and simple. Each vertex also has a distinct coordinate
x(v) in GF(2)^5. In a displayed bit string the leftmost character
is coordinate 4 and the rightmost is coordinate 0.

A proper coloring assigns different colors to the endpoints of every
edge. A b-vertex has a neighbor in every color other than its own. A
fall coloring is a proper coloring in which every vertex is a b-vertex.
Thus every color must occur, and a fall coloring is in particular a
b-coloring in the sense of the paper.

Find a full-row-rank three-row binary matrix A and a three-bit offset b.
For every vertex v define c(v) = A*x(v) + b in GF(2)^3, with all
arithmetic modulo 2. Interpret [q0,q1,q2] as color q0+2*q1+4*q2 in
{0,1,...,7}. The induced map c must be a fall coloring with exactly
eight colors. Row and offset arrays use coordinate order 0,1,...,d-1
and bit order 0,1,2 respectively. Rows may be in any order; any valid
affine fall-coloring certificate is accepted.

The displayed coordinate frame records the affine presentation. Its
origin and ordered direction vectors are data, not an extra condition
on A. All integers below are binary vectors rendered most-significant
bit first.

Frame origin: 01001
Frame directions (direction_index: vector):
0: 11011
1: 10010
2: 10000
3: 01101
4: 10101

Vertex coordinates (vertex: vector):
0: 01010
1: 11011
2: 11111
3: 01011
4: 01001
5: 10110
6: 00110
7: 10101
8: 00111
9: 11001
10: 00100
11: 11100
12: 00101
13: 10010
14: 01000
15: 10001

Adjacency lists (vertex: its seven neighbors, in increasing order):
0: 5 8 9 11 12 13 14
1: 3 5 6 9 12 13 14
2: 3 4 5 7 8 11 12
3: 1 2 4 6 7 10 15
4: 2 3 6 10 11 13 15
5: 0 1 2 8 10 13 14
6: 1 3 4 7 9 10 15
7: 2 3 6 10 11 14 15
8: 0 2 5 11 12 13 14
9: 0 1 6 10 13 14 15
10: 3 4 5 6 7 9 11
11: 0 2 4 7 8 10 15
12: 0 1 2 8 13 14 15
13: 0 1 4 5 8 9 12
14: 0 1 5 7 8 9 12
15: 3 4 6 7 9 11 12

Return one JSON object with exactly these fields:
  "matrix": three JSON arrays, each containing exactly 5 integer bits;
  "offset": exactly three integer bits [b0,b1,b2].
Every bit must be the integer 0 or 1; booleans are not accepted.

Give your final answer inside <answer></answer> tags, as that JSON object.
Syntax-only example for d=5:
<answer>{"matrix":[[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]],"offset":[0,0,0]}</answer>
Output nothing else inside the tags.
```

One accepted response is:

```text
<answer>{"matrix":[[0,1,1,1,1],[0,1,1,0,1],[0,0,0,1,1]],"offset":[0,1,0]}</answer>
```

`verify(inst, answer)` returns `(True, "ok")`. Replacing the second matrix row by a copy of the first returns `(False, "the three matrix rows must be linearly independent")`. A person can solve this preset on paper by XORing four five-bit closed neighborhoods and row-reducing the resulting small binary matrix.

## Difficulty and gates

| preset | vertices | coordinate bits | edges | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 16 | 5 | 56 | 18 | hand-scale illustration |
| easy | 256 | 16 | 896 | 51 | **shipping; oracle held** |
| medium | 512 | 16 | 1,792 | 51 | locally verified; not needed by oracle ladder |
| hard | 1,024 | 16 | 3,584 | 51 | locally verified; not needed by oracle ladder |

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified across all presets |
| G2 | 7 corruption classes rejected with 7 distinct reasons |
| G3 | tagged prose round-trip succeeded; answer is JSON-native |
| G4 | 0 hits / 200,000 full-rank affine candidates; bounded space 2,251,559,302,856,640 |
| G5 | shipping density sample 0/200,000; demo has exactly 1,344 valid answers among 208,320; reference cost above |
| G6 | coordinate outlier, greedy, 256-restart, and low-frame-bit attacks each 0/8; reference decoder 8/8 as expected |
| G7 | 512-vertex doubled instance verified; answer length unchanged |
| G8 | 100 relabeling invariance checks, 120 witness transports, and 20/20 distinct unrelated keys |
| G9(c) | 131 characters, about 33 tokens, 51 atoms, 262 intended exact operations |

## Oracle loop and G9 diagnostics

The current harness-owned pool contains two vendors and makes three calls per level, repeating one vendor on a fresh seed. All three bare calls failed at `easy`, so the official verdict is `hardened` with zero escalations. This successful run was made in an isolated scratch directory during the quota check and copied back byte-for-byte after confirming that its three generated instances and bare prompts were identical under the final module; an immediate in-place rerun then hit the total quota. The recorded escalation cap of zero cannot affect a verdict reached on the first rung.

| preset | seed | model | solved | result |
|---|---:|---|---|---|
| easy | 830591202 | `openai/gpt-5.6-terra` | no | parsed matrix rejected: edge 0 had equal endpoint colors |
| easy | 887572467 | `google/gemini-3.8-flash` | no | response budget exhausted without emitting an answer |
| easy | 482021116 | `openai/gpt-5.6-terra` | no | parsed matrix rejected: edge 9 had equal endpoint colors |

| G9 arm | solved / completed attempts | result |
|---|---:|---|
| bare | 0 / 3 | hardened at `easy` |
| structural hint | 0 / 0 | OpenRouter total quota exhausted before inference |
| placebo hint | 0 / 0 | OpenRouter total quota exhausted before inference |

Because both diagnostic denominators are zero, hinted minus placebo is not estimable. `selftest_report.json` stores `0.0` only as the module's zero-denominator convention; it is not evidence about the invariant. This diagnostic is not a gate. The gated G9(c) measurements are 131 characters, approximately 33 tokens, 51 atomic elements, and 262 intended exact operations.

## Use

```python
import gen_2003_04254 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=3, **params)
candidate = g.parse_answer("<answer>" + g._answer_text(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
print(g.render(inst))
```

From the repository root:

```bash
scripts/emit.sh 2003.04254 20 easy
```

The module uses only the Python standard library and performs no file or network I/O.

## Caveats

The family is easy with exact GF(2) elimination, and the displayed coordinates deliberately create the compact invariant; this is the Track B premise, not hidden structural hardness. The 0/200,000 guess result estimates only the declared prior of ordered full-rank affine maps with uniform offsets. It is not a proof of solution density and says nothing about informed candidates. The adversary panel did not test general-purpose SAT/SMT, integer programming, Weisfeiler-Leman refinement, or every spectral clustering variant. The reference nullspace decoder is construction-specific and succeeds. Canonicalization is exact for vertex renumbering, edge reordering, coherent affine coordinate changes, and their tested compositions, but it is not a complete graph-isomorphism canonical form. Finally, the structural-hint and placebo diagnostics remain unavailable because the shared API key reached its total spending limit after the successful bare run.
