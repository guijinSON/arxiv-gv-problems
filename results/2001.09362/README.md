# Verified problem generator for arXiv:2001.09362

## What the family is

This module generates an implicit graph and asks for an (S)-packing coloring. It uses the exact definition in Section 1 of Holub, Jakovac, and Klavžar, [“S-packing chromatic vertex-critical graphs”](https://arxiv.org/abs/2001.09362): vertices sharing color (i) must be at graph distance strictly greater than (s_i). Here (S=(1,ldots,1)), the ordinary proper-coloring specialization that Section 1 explicitly identifies.

For order (q), the graph has a (q)-vertex anchor clique and a (q\times q) grid of cell vertices. Every row and column is a clique. A clue joins its cell to every anchor except one. After normalizing the anchor colors, a valid graph coloring is exactly a completion of the displayed partial Latin square. The witness is the color of every anchor followed by every cell. Checking it requires only range, distinctness, row, column, and clue comparisons—no optimization or planted answer.

## Why it is hard, and which easy regimes were avoided

The source paper supplies the definition, not a new complexity theorem. Its Proposition 2.2 identifies the two-color/bipartite easy case, Theorems 3.1 and 4.1 classify low-color *critical graphs*, and Proposition 5.2 bounds the caterpillar regime. None is used. The paper cites the (S)-coloring complexity literature; Gastineau’s Theorem 2.2 records NP-completeness of the three-color (S=(1,1,1)) case. More specifically for this construction, Colbourn proved [partial Latin-square completion NP-complete](https://doi.org/10.1016/0166-218X(84)90075-1). The retained orders grow with `n`; this is not a fixed small-(q) lookup regime.

Generation samples a randomized full Latin square and a global color permutation **before** choosing clues. A random row/column/symbol relabeling and optional transpose erase construction order. At retained presets, clue sets are rejected if a public-data MRV search finishes within its node budget or if any panel attack succeeds. Clues are a uniformly sampled subset of the planted cells; there is no differently distributed decoy class.

## Worked demo (`demo`, seed 0)

The complete rendered instance is:

```text
S-packing coloring of a compactly defined graph

There are q = 5 available color labels: the integers 1 through 5.
Use the S-packing sequence S = (1, 1, 1, 1, 1).  An S-packing
coloring assigns one color label to every vertex, and two distinct vertices
with the same label must have graph distance strictly greater than 1.  Thus,
for this S, adjacent vertices must have different labels (ordinary proper
vertex coloring).

The undirected graph has these vertices:
  * anchors A[0], ..., A[4];
  * cells C[r,c] for 0 <= r < 5 and 0 <= c < 5.
All indices are 0-based.  Its edges are exactly the following; there are no
others:
  1. Every two distinct anchors are adjacent.
  2. Two distinct cells are adjacent exactly when they share a row or share a
     column: C[r,c]--C[r,d] for c != d, and C[r,c]--C[t,c] for r != t.
  3. For every clue (r,c)=s below, C[r,c] is adjacent to every anchor A[t]
     with t != s, and is not adjacent to A[s].

Clues (each s is an anchor INDEX, not an output color label):
  (0,0) = 3
  (0,1) = 2
  (0,2) = 1
  (0,3) = 0
  (1,1) = 3
  (1,2) = 2
  (1,4) = 0
  (2,3) = 2
  (2,4) = 3
  (3,2) = 4
  (3,3) = 3
  (4,0) = 0
  (4,2) = 3

Find any proper coloring of all vertices.  The anchor clique necessarily uses
all 5 output labels, and a clue (r,c)=s consequently forces C[r,c] to have
the same output label as A[s].  Output labels may be globally permuted; any
valid coloring is accepted.

Your answer must contain exactly 30 comma-separated base-10 integers, in
this order: A[0] through A[4], then all cells in row-major order
C[0,0], C[0,1], ..., C[4,4].  Order matters.  Every integer must
be in the inclusive range 1..5; repeats are allowed unless an edge forbids
them.

Give your final answer inside <answer></answer> tags, as one comma-separated
list.  Syntax example: <answer>1, 2, 3</answer> (your actual list must contain
exactly 30 integers).  Output nothing else inside the tags.
```

One answer is `2, 3, 5, 1, 4, 1, 5, 3, 2, 4, 4, 1, 5, 3, 2, 3, 4, 2, 5, 1, 5, 2, 4, 1, 3, 2, 3, 1, 4, 5`. `verify(inst, answer)` returns `(True, "ok")`. Swapping the first two cell colors returns `(False, "column 0 repeats color 5")`.

## Difficulty presets

| Preset | (q=n) | Implicit vertices | Clue density | MRV rejection budget | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 5 | 30 | 0.52 | 0 | Readable example; oracle solved it, so rejected for shipping |
| `medium` | 22 | 506 | 0.40 | 100,000 nodes | **Shipping; held against all three vendors** |
| `hard` | 26 | 702 | 0.40 | 150,000 nodes | Locally validated reserve; oracle did not need to reach it |

## Gate results at shipping difficulty

| Gate | Measurement | Result |
|---|---|---|
| G1 | 3 presets × 3 seeds; 9/9 plants verify | pass |
| G2 | drop, duplicate, empty, range, and swap rejected with 5 distinct reasons | pass |
| G3 | 506 integers recovered through prose and a Markdown fence; garbage → `None` | pass |
| G4 | 0/200,000 anchor-normalized, clue-respecting row-permutation guesses; reduced space has 222 decimal digits | pass |
| G5 | tiny (q=4): 24 valid labeled answers / (4^{20}) = (2.1828\times10^{-11}) | pass |
| G6 | positional 0/8; greedy 0/8; min-conflicts restart 0/8 | pass |
| G7 | (q=22\to44), vertices (506\to1980), reduced-space digits (222\to1200); doubled plant verifies | pass |
| G8 | 40/40 composed invariance checks and 40/40 carried witnesses; 20/20 unrelated keys distinct | pass |

## Multi-vendor oracle loop

The script-owned transcript used master seed `17936529707850234993`, medium reasoning effort, and schema version 2.

| Preset | Model | Seed | Solved? | Recorded reason |
|---|---|---:|---|---|
| demo | Gemini 3.1 Pro Preview | 1580406997 | yes | valid witness |
| demo | GPT-5.6 Terra | 1655720745 | yes | valid witness |
| demo | Grok 4.6 | 1625701289 | yes | valid witness |
| medium | Grok 4.6 | 1998954344 | no | 507 colors supplied; 506 required |
| medium | GPT-5.6 Terra | 1599619050 | no | 484 colors supplied; the 22 anchors were omitted |
| medium | Gemini 3.1 Pro Preview | 116305429 | no | parsed witness repeats color 1 in row 0 |

All six replies parsed; the held level is not a `parse_answer` false negative. Verdict: `hardened`, shipping preset `medium`.

## How to use it

```python
import random
import gen_2001_09362 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit fresh instances with:

```bash
bash scripts/emit.sh 2001.09362 20 medium
```

Run the complete local suite with `python3 results/2001.09362/gen_2001_09362.py`.

## Caveats

- NP-completeness is worst-case evidence, not a proof that this planted distribution is asymptotically hard. The 100,000-node filter uses one deterministic MRV/value ordering and can overfit that solver; SAT, exact-cover/DLX, constraint-programming, advanced Latin trades, and specialized algebraic attacks were not tested.
- G4 is an empirical result under a deliberately strong but specific prior: anchors are normalized, every clue is obeyed, and each row is already a permutation. It measures how often independently generated rows also satisfy all columns. It is not an estimate of success for search with propagation. Zero hits in 200,000 trials is reported as the measured rate, not a statistical proof of a universal probability bound.
- The easy failure modes are small (q), clue sets that make greedy propagation succeed, highly revealing clue density, or algebraic/cyclic construction. The generator randomizes via perfect matchings, filters greedy and cyclic attacks, and ships only (q=22), but other signatures may remain.
- `canonical_key` uses typed incidence-graph Weisfeiler–Lehman refinement. It is invariant under tested row, column, and symbol permutations, transpose, clue reordering, and their compositions, but it is not a complete partial-Latin-square isomorphism canonizer; rare collisions can over-collapse unrelated instances.
- The source paper calls (S=(1,1,ldots)) ordinary coloring and excludes that constant sequence from its later term “packing sequence” because ordinary coloring is already well studied. This generator uses the paper’s exact broader (S)-packing definition, not its vertex-critical classification as the search task.
