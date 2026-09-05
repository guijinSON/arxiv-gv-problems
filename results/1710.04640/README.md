# L-tromino tilings with arbitrary defects (arXiv:1710.04640)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | integer lattice |
| Computational core | exact cover |
| Certificate | integer tuple: L-tromino placement triples |
| Intended intuition | decomposition: a dominant anchor-parity grid plus a small fringe |
| Domain essentiality | native |
| Reduction | paper-licensed, Section 3.2, Theorem 13 |

## Problem and trust model

This generator is based on Akagi, Gaona, Mendoza, Saikia, and Villagra, [*Hard and Easy Instances of L-Tromino Tilings*](https://arxiv.org/abs/1710.04640). The solver receives an Aztec diamond whose nondefective lattice cells are listed explicitly; every other diamond cell is a defect. It must give `n` triples `[x,y,m]`, each describing the three occupied corners of a 2-by-2 square. The checker uses integer coordinates only: it expands every triple, rejects defective cells and overlaps, and compares the exact union with the listed free cells. It never reads the planted answer.

Generation is by composition, not solution. The generator first lays down disjoint L-trominoes, with most anchors on one parity grid and a fixed-size phase-breaking fringe, then applies a random square-lattice symmetry and translation. Theorem 13 licenses embedding such a defective region in an Aztec diamond. The recorded tiling is carried through the transformation.

## Why this is Track B

Theorem 13 proves NP-completeness for Aztec diamonds with an unbounded number of defects, but that worst-case statement does **not** establish average-case hardness for this planted distribution. An efficient generic method exists here: enumerate every legal L placement and run minimum-column Algorithm X. Across eight shipping instances it solved 8/8 in 0.265692 seconds total, using 213,057 placement checks and 1,113 search nodes (about 26,632 checks and 139 nodes per instance). Its worst-case search is exponential, but at this preset it is easy for a computer and infeasible to execute manually from 144 shuffled coordinates.

The compact route is to recognize that almost all tile anchors lie in one residue class modulo 2, recover the corresponding 2-by-2 block decomposition, and solve only the small fringe. The automated four-phase probe used 986–1,180 counted operations because it also discovers the phase mechanically. Once the phase is seen—the intended insight—the route needs at most 228 exact grouping, emission, and fringe comparisons.

The easy regimes in the paper are deliberately excluded: defect-free Aztec rectangles have an `O(b^2)` construction (Theorems 3 and 8), the one-defect case has another `O(b^2)` construction (Theorem 10), forbidden-polyomino-free 180° instances are polynomial through claw-free maximum independent set (Theorem 19), and scaled regions `R^boxplus` have a constructive efficient tiling (Theorem 23).

## Worked demo

For `make_instance(seed=123, **DIFFICULTY["demo"])`, the order-33 diamond has these 18 nondefective cells (all other cells are defects):

```text
(-3,23) (-1,23) (-3,25) (-2,22) (-4,23) (-4,24)
(-5,23) (-2,24) (-2,21) (0,20)  (-3,24) (-1,20)
(-2,23) (-1,21) (-3,26) (-5,24) (0,21)  (-4,25)
```

One answer is:

```json
[[-2,21,3],[-1,20,2],[-4,25,2],[-4,23,0],[-2,23,3],[-5,23,3]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last tile returns `(False, "wrong tile count: expected 6, got 5")`. This demo is genuinely hand-scale: a person can draw the 18 cells and cover them with six L shapes; exhaustive enumeration finds two tilings.

## Difficulty ladder

| preset | tiles `n` | free cells | legal placements (seed 2) | candidate-space bits | status |
|---|---:|---:|---:|---:|---|
| demo | 6 | 18 | 23 | 17 | illustration; skipped by hardener |
| easy | 36 | 108 | 190 | 130 | one oracle solved; rejected as shipping level |
| **medium** | **48** | **144** | **244** | **171** | **ships; held 3/3** |
| hard | 60 | 180 | 314 | 217 | available, not needed |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verify across all presets |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | fenced JSON with surrounding prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware random candidates; shipping space `1.1526440724303576e51` |
| G5 | pass | shipping density sample 0/200,000; demo has exactly 2 tilings; strongest failed attack cost 8.401245 s total |
| G6 | pass | four attacks at 0/8; reference Algorithm X at 8/8 |
| G7 | pass | doubled instance has 96 tiles, verifies, and raises search-space bits from 170 to 343 |
| G8 | pass | 40 symmetry/translation invariance checks, 40 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 475 characters, 119 estimated tokens, 144 atoms, 228 intended operations |

The four failing G6 attacks are low-cell-frequency boundary selection, lexicographic greedy, 48 randomized most-constrained restarts, and the natural bounding-box parity guess. The successful domain-standard Algorithm X is intentionally reported under `reference_algorithm`, not mislabelled as a failed attack.

## Bare oracle loop

| preset | model | seed | solved | outcome |
|---|---|---:|---|---|
| easy | OpenAI gpt-5.6-terra | 42148202 | no | incorrectly claimed 107 cells and gave no answer |
| easy | Google gemini-3.8-flash | 1499137749 | no | analysis ended without a tagged answer |
| easy | Google gemini-3.8-flash | 1401424229 | yes | verified tiling; escalation triggered |
| medium | Google gemini-3.8-flash | 1095242278 | no | returned 53 tiles instead of 48 |
| medium | OpenAI gpt-5.6-terra | 1874779161 | no | placement 4 covered a defect |
| medium | OpenAI gpt-5.6-terra | 1134108350 | no | tagged answer was empty |

The script-owned verdict is `hardened` at `medium` after one escalation. The unparsed responses were inspected; none contained a complete answer that `parse_answer` missed.

## G9 hint diagnostic

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened at shipping preset |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. On these small samples, naming the dominant parity invariant did not help the pool. That weakens evidence that model failures specifically measure discovery of the declared decomposition; they may also reflect the bookkeeping needed to emit 48 exact triples. The answer still fits the formal cap (475 characters / 144 atoms), and the intended post-insight route is 228 operations.

## Use

From the repository root:

```python
import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "g", "results/1710.04640/gen_1710_04640.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit dataset records with:

```bash
bash scripts/emit.sh 1710.04640 20 medium
```

## Caveats

- This is not a Track A distributional-hardness claim. A computer solves the shipping instances quickly with exact cover, and Theorem 13 supplies only worst-case NP-completeness.
- The 0/200,000 guess rate is relative to uniform `n`-subsets of all legal in-region L placements. It enforces shape, count, containment, and distinctness, but not nonoverlap or coverage—the two constraints being solved. It is not a posterior model of an expert solver.
- The parity signature is intentionally planted. A solver that recognizes and executes it should succeed; the benchmark measures the gap between that route and coordinate-level exact cover.
- SAT/ILP/CP encodings, DLX implementation variants, transfer-matrix methods, and learned geometric heuristics were not tested. The required generic Algorithm X baseline was tested and succeeds.
- `canonical_key` is complete only for input reordering, translations, and the eight square-lattice dihedral symmetries. It is not a general polyomino-isomorphism solver.
- The generator screens against named heuristics. This is deterministic and does not produce the witness—the witness exists before screening—but it can bias the generated promise away from instances those specific heuristics solve.
