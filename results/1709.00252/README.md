# Verified edge-matching puzzle generator (arXiv:1709.00252)

Status: the module passes every local gate, and the required bare oracle loop held the first evaluated rung: 0 of 3 valid attempts solved independent 12×12 instances. The structural-hint arm also held 0/3. The placebo diagnostic was attempted separately, but OpenRouter exhausted the key's total limit before a valid placebo response; its four script-owned error records are preserved and are not counted as model failures.

| profile field | value |
|---|---|
| Track | A — structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple (one native oriented-tile assignment code per cell) |
| Intended intuition | constraint propagation |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

The family instantiates the feasibility form of Salassa et al., [“MILP and Max-Clique based heuristics for the Eternity II puzzle”](https://arxiv.org/abs/1709.00252), Section 2.1. A solver receives an unordered list of rotatable square tiles, each represented by its four integer edge colors, and must place every tile once on an `n × n` board. Touching colors must agree and color 0 must face exactly the outer frame. The witness is the row-major list of oriented tile codes `4*tile_id + clockwise_rotation`; verification is a permutation check plus exact integer edge comparisons.

Generation is inverse, never search-based. At the shipping settings the generator samples every internal grid edge independently, copies its color to the two incident planted tiles, puts gray only around the frame, then independently rotates and permutes the tiles. Thus the certificate is carried through known transformations. All internal edges come from one distribution; there is no separate planted-edge or decoy-edge population. If the named ladder is exhausted, the first further escalation keeps the 196-code 14×14 answer fixed and shuffles an exactly balanced color multiset, removing frequency outliers before any board-size increase.

## Why Track A is claimed

Section 1 cites [Demaine and Demaine's Theorem 3](https://erikdemaine.org/papers/Jigsaw_GC/paper.pdf): unsigned unit-square edge matching on a square board, using every tile, is NP-complete in the growing-palette regime. That worst-case theorem does **not** establish hardness of this generated distribution, so the Track-A claim also relies on the measured attack panel. At 12×12 with 10 non-gray colors, chronological CSP/DPLL-style search with unit domains and forward checking found no solution after 5,000,000 nodes on each of eight seeds (40,000,000 nodes total). On the final audit run the panel used 347.78 seconds in aggregate; the separately measured shipping instance used 5,000,000 nodes and 11.62 seconds.

The easy regimes were deliberately avoided. Section 2.3 reports both CPLEX and the max-clique heuristic solving the paper's instances through 6×6, while the larger 7×7 and 8×8 cases were not completed by the tested runs. Section 3 identifies easier decompositions: border optimization is one-dimensional and was always solved in preliminary tests, while non-adjacent tile reassignment is polynomial bipartite matching via the Hungarian algorithm. A calibration run also solved this generator's 7×7 instance in 37,259 DPLL nodes (0.17 seconds), so the evaluated ladder begins at 12×12.

## Worked demo

The complete `demo` instance (`n=2`, `seed=0`) is:

```text
EDGE-MATCHING PUZZLE

Arrange the 4 listed square tiles on a 2 by 2 board.
Each tile must be used exactly once and may be rotated, but not flipped.
A tile is listed as [top,right,bottom,left] in its stored orientation.
Rotation r=0,1,2,3 means r clockwise quarter-turns from that orientation.
Every pair of touching edges must have exactly the same integer color.
Color 0 is gray. An edge is 0 if and only if it faces outside the board:
all outer edges are 0 and no internal touching edge is 0.
Rows, columns, and tile IDs are 0-indexed.

Tiles:
0: [0,2,1,0]
1: [1,2,0,0]
2: [0,0,2,2]
3: [0,0,2,2]

Return one JSON list of exactly 4 integers in row-major cell order.
At each cell, integer code 4*t+r means tile ID t with rotation r.
Thus the first code is row 0, column 0; order matters and repeats are forbidden.
Give your final answer inside <answer></answer> tags, as that JSON list.
Format-only example: <answer>[13, 6, 8, 3]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[5,1,14,9]</answer>`. `verify(inst, answer)` returns `(True, "ok")`; replacing the second code by `5` returns `(False, "a tile ID is duplicated and another tile is missing")`. This demo is genuinely hand-solvable: orient the four gray corners and match the four internal colors. It has eight code-distinct solutions among 24 border-respecting candidates because two tile IDs happen to carry identical patterns.

## Difficulty presets

| preset | board | nonzero colors | color sampling | DPLL audit budget | status |
|---|---:|---:|---|---:|---|
| demo | 2×2 | 3 | iid | 2,000 | hand example; never shipped |
| easy | 12×12 | 10 | iid | 5,000,000 | **ships; held 0/3** |
| medium | 13×13 | 10 | iid | 5,000,000 | available escalation; not needed |
| hard | 14×14 | 11 | iid | 5,000,000 | available escalation; not needed |

The earlier 7×7 calibration was rejected by the standard-attack gate, not by an oracle. After `hard`, escalation first changes only color sampling from iid to balanced at 14×14, then raises the balanced board to 15×15 and 16×16. A larger board would exceed the 256-element answer cap, so `escalate` then returns `"cap_bound"`.

## Local gates

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | planted witness verified for 4 presets × 3 seeds |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0 / 200,000 structure-aware guesses; candidate space ≈10^267.47 |
| G5 | pass | shipping density sample 0 / 200,000; demo exact count 8 / 24; DPLL 5,000,000 nodes |
| G6 | pass | outlier, deterministic greedy, 256 edge-consistent random-greedy restarts, and DPLL all 0 / 8; DPLL exhausted 40,000,000 nodes |
| G7 | pass | 24×24 doubled instance built and planted witness verified |
| G8 | pass | 60 / 60 invariance and carried-witness checks, including global reflection; 20 / 20 unrelated keys distinct |
| G9(c) | pass | at most 550 characters, about 138 tokens, 144 atomic codes, 144 certificate-assembly placements |

The G4 implementation is an exact lazy sampler for the same distribution as `random_candidate`: it draws each category permutation uniformly without replacement, but stops drawing an irrelevant suffix as soon as a mismatched prefix proves failure.

## Oracle loop and G9 diagnostic

The script-owned bare run hardened immediately at `easy`; all replies parsed, and exact verification rejected each proposed board.

| preset | model | seed | solved | exact reason |
|---|---|---:|---:|---|
| easy | Gemini 3.8 Flash | 952204539 | no | gray-border rule fails at row 0, column 1 |
| easy | GPT-5.6 Terra | 2014520563 | no | horizontal mismatch after row 0, column 0 |
| easy | GPT-5.6 Terra | 481324658 | no | gray-border rule fails at row 0, column 0 |

| arm | solved / valid attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 0 (4 errors) | unavailable: OpenRouter HTTP 403 total-limit error |

Hinted minus placebo is undefined, not zero: error-only placebo calls supply no denominator. Bare and hinted both held, but without a valid placebo arm nothing can be concluded about the hint's structural benefit independent of prompt leakage. G9(c) measures 550 characters, about 138 tokens, 144 codes, and 144 placement operations after a complete compatible continuation has been identified.

## Use

```python
from gen_1709_00252 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit records after a valid hardening verdict with:

```bash
bash scripts/emit.sh 1709.00252 20 easy
```

The module is standard-library-only; `gvlib` is unnecessary for this finite integer witness.

## Caveats

- The Track-A evidence is empirical for this random-planted distribution. General NP-completeness is only a worst-case result and does not promote the distribution claim by itself.
- `P(guess)=0/200,000` is relative to the stated prior: it already knows corner/border/interior gray types, but it does not condition on matching the first edge. It is a density estimate, not a proof that smarter search is hard.
- The paper-specific CPLEX MILP, Grosso–Locatelli–Pullan max-clique heuristic, modern SAT/CP solvers, and broader restart portfolios were not run because the deliverable must remain standard-library-only. The implemented domain-standard attack is bounded CSP/DPLL with propagation; this is the largest unresolved attack caveat.
- Palette size has a non-monotone effect: too many colors make continuations nearly unique, while too few can create many solutions. The shipping palette is measured, not claimed optimal.
- The canonical key is invariant under tested tile reorderings, independent stored-orientation changes, global color relabeling, square-board reflection, and compositions. Its color-refinement normal form can over-collapse rare unresolved symmetric color classes; it is the strongest cheap invariant used here, not a complete isomorphism test.
- A model can fail because producing 144 codes is laborious even though it is under the explicit cap. The reported 144-operation intended route is certificate assembly after a compatible continuation is known; it does not claim that the failed combinatorial search itself takes 144 operations.
- The placebo arm is missing for an external quota reason. Consequently the structural hint's causal value is unknown even though both bare and hinted prompts held 0/3.
