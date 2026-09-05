# Target-set token-jump generator — arXiv:2107.09885

| profile | value |
|---|---|
| Track | **B** — an efficient algorithm exists and is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | exact symbolic word of token jumps |
| Intended intuition | change of variables |
| Domain essentiality | licensed reduction (paper-central, representational coverage) |
| Reduction | Section 4.2, Theorem 4.4 and Lemma 4.5 |

## What the family is

[Ohsaka, *On Reconfigurability of Target Sets*](https://arxiv.org/abs/2107.09885)
defines irreversible threshold activation and asks whether one target set can be
changed into another by swapping one seed at a time while every intermediate set
remains a target set. This generator hands the solver the paper's native split
graph, written exactly with compressed classes of independent twin vertices, its
integer thresholds, and two equal-size target sets. The answer is a chronological
list of `[remove, add]` token jumps. `verify` replays the jumps and the graph's
activation process using integer comparisons only.

The graph is the paper-licensed Hitting Set Reconfiguration construction from
Section 4.2. A random matching and total precedence order are sampled first.
Two-neighbour classes enforce the matching and every forward implication; every
prefix of the sampled order is therefore a target set. Decoy classes touch the
one fixed common seed, so they preserve the planted certificate by construction.

## Why Track B is honest

Theorem 4.4 proves PSPACE-completeness on split graphs, but that is a worst-case
result and does **not** prove this inverse-generated distribution hard. This
distribution has a polynomial reference algorithm: extract repeated
two-neighbour classes, interpret singleton two-neighbour classes as precedence
arcs, and run Kahn topological sorting. Its complexity is `O(c+n²)` for `c`
compressed classes. At the shipping preset it succeeds 8/8, scans 1,553 classes,
uses 4,690 counted primitive operations, and averages 0.000240 s.

The shorter route is to remove the public `k+1` offset from each moving clique
threshold and inspect residues under the size-derived period. Matching quotients
pair the remove/add vertices and complementary remainders give their ranks. That
route takes `6n = 192` exact arithmetic operations. Without recognizing this
change of variables, a no-tool solver must work through the shuffled constraint
listing. The easy regimes avoided are threshold-1 graphs (Observation 3.1),
maximum-degree-two graphs (Theorem 3.2), and trees (Theorem 4.1), all of which the
paper solves in polynomial time.

## Worked demo (`seed=0`)

This is the complete `demo` rendering (the final two-pair example is format-only):

```text
Target-set token-jump certificate on a split graph

The graph below is specified exactly, with large groups of twin vertices written
compactly. It is a simple undirected graph after expansion.

Element vertices are the integer IDs 0 through 8.
There is one special vertex x with ID 9. These
10 vertices form a clique: every two distinct vertices
among them are adjacent.

Each constraint row "r: M: v1 v2 ..." creates M distinct independent vertices
W(r,1),...,W(r,M). A W vertex is adjacent exactly to x and to the listed element
vertices. There are no edges between W vertices. Every W vertex has threshold 1.
The listed M is a positive integer multiplicity, not a parallel edge.

An irreversible activation process starts with exactly the vertices of a seed
set active. At each synchronous round, every inactive vertex having at least its
threshold number of active neighbours becomes active. Active vertices never
deactivate. A seed set is a target set when this process eventually activates
the whole expanded graph.

Thresholds of element vertices (vertex: threshold):
  0: 144
  1: 69
  2: 151
  3: 126
  4: 98
  5: 224
  6: 331
  7: 25
  8: 51
The threshold of x=9 is 426.

Constraint twin classes (row: multiplicity: element neighbours):
  0: 1 : 6
  1: 108 : 0 5 6
  2: 36 : 1 6 8
  3: 18 : 7 4
  4: 27 : 1 0
  5: 1 : 7 0
  6: 72 : 4 5 6
  7: 1 : 5 4
  8: 1 : 3 4
  9: 9 : 3 8
  10: 1 : 3 2
  11: 108 : 2 3 6
  12: 1 : 3 0
  13: 1 : 5 0
  14: 36 : 5 2

The start target set X is:
  1 3 5 6 7
The end target set Y is:
  0 2 4 6 8
Both contain exactly k=5 vertices.

A token jump simultaneously removes one currently active seed vertex and adds
one vertex not currently in the seed set, preserving the seed-set size. Find a
sequence of exactly n=4 token jumps that changes X into Y and for which X and
every set after a jump is a target set. Because the sequence has exactly n
jumps, every vertex in X\Y must be removed exactly once, every vertex in Y\X
must be added exactly once, the sole vertex in X intersection Y is never moved,
and no other vertex may occur in a jump.

Give your final answer inside <answer></answer> tags as a JSON array of exactly
4 ordered integer pairs [remove, add], in chronological order. Vertex IDs are
0-based; order matters; repeats are forbidden.
Example format only: <answer>[[3,7],[1,5]]</answer>
Output nothing else inside the tags.
```

The answer is `[[1,0],[7,4],[5,2],[3,8]]`; `verify` returns `(True, "ok")`.
Swapping its first two moves returns
`(False, "jump 1 violates a precedence twin class")`. A person can solve this
small case on paper: the four two-neighbour rows of multiplicity greater than one
identify the pairs, and the multiplicity-one rows order them.

## Difficulty and gates

| preset | `n` jumps | decoy classes | decoy width | status |
|---|---:|---:|---:|---|
| demo | 4 | 4 | 2 | hand-scale illustration |
| easy | 20 | 256 | 4 | oracle solved 1/3; not shipped |
| medium | 32 | 1,024 | 4 | **ships; hardened 0/3** |
| hard | 48 | 4,096 | 4 | available, not needed by ladder |

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verified; every answer JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose plus fenced JSON parsed and verified |
| G4 | 0/200,000 structure-aware guesses; language size `(32!)²` |
| G5 | exactly 1 valid word; density `1.4442969889585408e-71`; demo brute force found 1 |
| G6 | five attacks, each 0/8; reference decoder 8/8 at 4,690 operations |
| G7 | doubled `n=64` and fixed-length decoy escalation both built and verified |
| G8 | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 311 chars, 78 estimated tokens, 64 atoms, 192 intended-route operations |

## Oracle hardening loop

| preset | model | seed | solved | reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 881402009 | no | parsed word failed at jump 16 |
| easy | GPT-5.6 Terra | 1980005074 | no | parsed word failed at jump 1 |
| easy | Gemini 3.8 Flash | 694885663 | yes | verified |
| medium | GPT-5.6 Terra | 317877681 | no | parsed word failed at jump 1 |
| medium | Gemini 3.8 Flash | 1142650649 | no | empty, length-limited response |
| medium | GPT-5.6 Terra | 812274576 | no | parsed word failed at jump 1 |

The script-owned verdict is `hardened` at `medium`. The one empty shipping reply
is retained as such in the transcript; the other two shipping replies were
parseable and wrong.

## G9 diagnostic arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. The hint bought no measured improvement, but all
three arms are at the zero floor, so this run cannot distinguish an ineffective
hint from an insight that the models still could not execute. One placebo reply
was also empty and length-limited; the other five hint/placebo replies were
parseable invalid words.

## Use

```python
import random
import gen_2107_09885 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
text = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
assert g.search_space(inst) == __import__("math").factorial(32) ** 2
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2107.09885 20
```

## Caveats

- This is Track B. Knowing either the modular invariant or the constraint-to-DAG
  decoder makes the family easy; no distributional Track A claim is made.
- Twin classes are a succinct exact specification. The shipping graph expands to
  4,278,083 vertices, whereas the paper's complexity theorem uses ordinary
  explicit graph input. The theorem is cited to license the construction, not to
  transfer PSPACE-hardness to this compressed distribution.
- The `1/(32!)²` guess probability is uniform over candidates that already obey
  both endpoint permutations. It is not a claim about a language model's prior.
- The panel did not run a generic PSPACE state-space search, SAT/SMT, or ILP.
  It did run the stronger distribution-specific polynomial decoder and reports
  its 8/8 success separately, as Track B requires.
- The verifier uses threshold-derived necessary checks to reject malformed words
  cheaply, then performs full exact activation replay on every surviving word.
  General alternative-length sequences are outside the declared certificate
  language.
