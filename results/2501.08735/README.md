# Maximum matching cuts from arXiv:2501.08735

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | exact cover |
| certificate form | integer tuple (selected graph-gadget IDs) |
| intuition | invariant: a cyclic tag difference is constant along a hidden cover layer |
| domain essentiality | licensed reduction |
| reduction | paper-licensed, Section 4, Theorem 23 |

## What the family is

Felicia Lucke's paper [*Matching Cut and Variants on Bipartite Graphs of Bounded Radius and Diameter*](https://arxiv.org/abs/2501.08735) defines a matching cut as all edges crossing a nontrivial vertex partition when those crossing edges form a matching. Theorem 23 converts Exact 3-Cover into a bipartite radius-3, diameter-4 graph: a complete bipartite core represents the universe and each triple becomes a labelled `K_(3,3)` gadget. Selecting an exact cover and colouring precisely its gadgets opposite the core produces a matching cut of size `6n`.

The solver receives that graph in the paper's compact construction notation, including every triple and the exact rule generating every vertex and edge. It returns `n` gadget IDs. `verify` reconstructs the complete graph, colours it, scans every crossing edge, and checks both the per-vertex matching condition and the target size. It never reads `inst["answer"]`. The complete core and gadget bicliques force every matching-cut colour class to be monochromatic within each block, so `6n` is the executable upper bound used by Theorem 23.

## Why Track B

Theorem 23 proves NP-hardness for bipartite graphs of radius 3 and diameter 4, but worst-case hardness is not a claim about this generated distribution. Every generated cover row belongs to a cyclic translation layer. The distribution therefore has an efficient `O(n*layers)` algorithm: bucket gadgets by `(tag(second)-tag(first)) mod n`. At shipping `n=35,layers=6`, that is 210 modular subtractions and averaged 0.000065 seconds once the invariant is noticed.

The graph/exact-cover mechanical reference is minimum-column Algorithm X, worst-case `O(layers^n)`. Across eight shipping seeds it succeeded as expected but averaged 82,276 recursive nodes, 26,936,781 exact incidence tests, and 2.90 seconds (maximum 11.61 seconds) on the final rerun. This gap—not a false Track A claim—is the benchmark: a no-tool solver has to discover the invariant and accurately extract 35 IDs. The paper's easy regimes are explicitly avoided: Theorem 12 makes bipartite diameter-at-most-3 instances polynomial and Theorem 15 does the same for radius at most 2. Our graphs use Theorem 23's radius-3/diameter-4 construction.

## Worked demo

For `make_instance(n=5, layers=2, seed=0)`, the self-contained data reduce to these tag tables and gadgets (the renderer also states the full graph rule):

```text
A 0:2 1:1 2:0 3:4 4:3
B 5:0 6:2 7:1 8:3 9:4
C 10:1 11:0 12:4 13:2 14:3

0: 4 5 12
1: 4 6 14
2: 1 8 13
3: 1 5 10
4: 2 9 11
5: 2 6 10
6: 0 7 13
7: 0 9 14
8: 3 7 11
9: 3 8 12
```

The answer is `<answer>[1, 3, 4, 6, 9]</answer>`. Exact checks return `verify(inst, inst["answer"]) == (True, "ok")`; deleting the last ID returns `(False, "expected exactly 5 gadget IDs")`. A person can solve this demo on paper: compute the second-minus-first tag difference modulo 5 and collect one five-gadget layer.

## Presets and gates

| preset | n | layers | candidates | status |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 32 | hand-solvable; 2 valid answers exactly |
| easy | 25 | 4 | `4^25` | local gates pass; oracle unavailable |
| medium | 31 | 5 | `5^31` | local gates pass; oracle not reached |
| hard | 35 | 6 | `6^35` (91 bits) | configured shipping preset; oracle unvalidated |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON-native |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | model-style fenced answer round-trips; garbage returns `None` |
| G4 | 0 hits / 200,000 structure-aware guesses (`P < 10^-6` observed) |
| G5 | shipping density 0/200,000; demo 2/32; shipping reference 2,190 nodes on the recorded seed |
| G6 | four attacks each 0/8; Algorithm X and cyclic reference each 8/8 |
| G7 | doubled `n=70` witness verifies; space grows from 91 to 181 bits |
| G8 | 60/60 composed relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | 126 characters, 35 atoms, about 32 tokens, 210 intended exact operations |

## Oracle loop and G9 diagnostics

The required harness was run, but OpenRouter returned HTTP 403 `Key limit exceeded` for every draw. The harness correctly recorded errors and refused to manufacture a hardness verdict. Consequently this directory is **not ready to submit or emit as a validated shipping family** until the three runs are repeated with a funded key.

| run | preset | seeds | scored attempts | outcome |
|---|---|---|---:|---|
| bare | easy | 821055208, 147027448, 2053731108, 471901831 | 0 | 4 provider errors; no verdict |
| structural hint | hard | 1660979503, 213540039, 1712826626, 631515366 | 0 | 4 provider errors; no verdict |
| placebo hint | hard | 672408895, 172016290, 1459192677, 620090847 | 0 | 4 provider errors; no verdict |

Thus bare/hinted/placebo are all `0 solved / 0 scored attempts`; `hinted - placebo` is undefined rather than evidence of no effect. The module records the neutral numeric placeholder `0.0` and `hinted_verdict="not_run"`. The structural-hint diagnostic must be rerun before drawing any conclusion about whether the claimed invariant helps.

## Use

From this directory:

```python
import gen_2501_08735 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY["hard"])
question = g.render(inst)
answer = g.parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

After a successful bare and G9 rerun, emit from the repository root with:

```bash
bash scripts/emit.sh 2501.08735 20 hard
```

## Caveats

The tags intentionally make this distribution polynomial-time solvable; deleting or ignoring them changes the benchmark, while exposing precomputed differences makes it trivial. The 0/200,000 guess estimate is relative to the stated structure-aware prior—one gadget per A element—not a uniform prior over arbitrary ID lists, and it cannot rule out a tiny nonzero density. Algorithm X showed wide seed-to-seed and machine-load variance, so the baseline is a measured distribution, not a per-instance lower bound: identical node and incidence counts averaged between 2.00 and 8.13 seconds in repeated runs, with maxima from 7.45 to 31.19 seconds. The four local attacks do not include a commercial CP-SAT/ILP solver or a dedicated exact-cover package; the in-module Algorithm X is the domain-standard substitute. `canonical_key` is exact for the generator's tested ID, gadget-order, affine-tag, and B/C-swap symmetries, but is not a complete general graph-isomorphism canonical form. Finally, all oracle conclusions remain blocked by the exhausted external key; the error transcripts are preserved verbatim.
