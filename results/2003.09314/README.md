# Compressed path-forest burning certificates (arXiv:2003.09314) — parked

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | subset sum / fixed-bin exact partition |
| Certificate | exact symbolic: a radius-to-component partition expanded into a burning sequence |
| Intended intuition | decomposition: congruence classes modulo `t+4` collapse the radius partition to small singleton/pair matching |
| Domain essentiality | native; no reduction |

This module turns Farokh et al., [“New heuristics for burning graphs”](https://arxiv.org/abs/2003.09314), into a generator over the paper’s native graph-burning objects. The instance is a path forest, represented by its component orders. The solver partitions the radius indices `0,...,k-1` among those components. The checker expands that finite symbolic object into concrete source vertices and rounds, verifies that every source was unburned when selected, and replays exact interval coverage. No floating point, oracle, or planted answer is used by `verify`.

## Trust and hardness

Generation is a composition of identities, not a solve. The `k` fire balls have odd capacities

```text
1, 3, 5, ..., 2k-1,
```

whose sum is `k^2`. Before the instance exists, the generator groups radii by residue modulo `q=t+4`, randomly pairs four pairs of residue classes, and leaves the other `t-4` classes single. It sums the odd capacities in each bundle, creates a path of that exact order, and shuffles the paths while carrying the certificate through the isomorphism. Filtering only selects already-certified instances on which the named attacks fail and whose reference cost lies in the declared window.

This is intentionally Track B. Section 1 of the source paper states both sides of the boundary: Graph Burning is NP-complete even for path forests, but path forests with a fixed number of components are polynomial-time solvable. The cited result is Algorithm 15 of Bessy et al., [“Burning a Graph is Hard”](https://arxiv.org/abs/1511.06774), with bound `O(t*m^t)` for fixed component count `t` and maximum component order `m`. This generator fixes `t=8` outside the demo, so it makes no Track-A claim.

The executable memoized fixed-bin dynamic program solves 8/8 provisional `easy` instances. It used a median 54,107 nodes, 331,076 counted branch operations, and 0.104 seconds; the eight instances totaled 2,363,676 operations in 0.752 seconds. That is easy with code but not a plausible hand calculation. Recognizing the residue-class invariant reduces the same instance to 231 exact operations: compute 12 class totals, index singleton and pair sums, and match those totals to the eight paths.

The local correctness and adversary gates pass, but the family is **not released**. The script-owned hardening loop obtained verified answers on all 21/21 calls across the three presets and four escalations, ending at `k=53`, `t=11`. It returned `budget_bound` because one more valid conditioned level remained after its six-escalation budget. The following size increase would cost at least 320 compact-route operations, so `escalate()` now returns `cap_bound` before it violates G9. Per the harness verdict this paper is parked, not rejected; `easy` remains only the module’s provisional target.

## Worked demo

This is the complete statement from `make_instance(seed=123, **DIFFICULTY["demo"])`:

```text
Find a compressed burning certificate for the path forest below.

Definitions.
A path of order L has vertices 0,1,...,L-1 and edges between consecutive vertices.
A path forest is the disjoint union of its displayed path components; vertices in different components have infinite distance.
There are k=9 rounds. In round i (1-indexed), choose one vertex that was not burned in an earlier round; by the end, its fire covers every vertex at distance at most k-i.
Equivalently, radius r=k-i belongs to round i and its fire ball has at most 2r+1 vertices on a path.

Compressed certificate.
Partition every radius index 0,1,...,8 among the t=4 displayed components.
For each component, the checker reads its radii in the required increasing order and lays their intervals left-to-right: radius r occupies the next 2r+1 vertices and its source is the middle vertex of that interval.
The checker expands these sources into rounds i=k-r, verifies that every source was unburned when selected, and verifies that the fire balls cover every vertex exactly.
Thus your assignment is valid precisely when the odd sizes assigned to every component sum to that component's displayed order; the checker still performs the full interval replay independently.

Total graph order = 81 = k^2.
Component orders (0-based component index: order):
0: 18
1: 18
2: 25
3: 20

Give your final answer inside <answer></answer> tags as a JSON array of exactly 4 nonempty arrays.
Array c lists, in strictly increasing order, the distinct radius indices assigned to component c; together the arrays must contain each radius 0 through k-1 exactly once.
Example syntax only: <answer>[[0],[1],[2],[3,4,5,6,7,8]]</answer>
Output nothing else inside the tags.
```

The hand-solvable answer is `<answer>[[2,6],[1,7],[0,3,8],[4,5]]</answer>`. The capacities are `5+13=18`, `3+15=18`, `1+7+17=25`, and `9+11=20`; `verify` returns `(True, "ok")`. Dropping radius `6` produces `[[2],[1,7],[0,3,8],[4,5]]` and returns `(False, "incomplete: radius 6 is missing")`.

## Difficulty presets

| preset | rounds `k` | components | reference-node window | random-greedy restarts | status |
|---|---:|---:|---:|---:|---|
| demo | 9 | 4 | none | 4 | hand example; hardener skips it |
| easy | 37 | 8 | 5,000–250,000 | 32 | solved by 3/3 bare oracles; provisional target only |
| medium | 45 | 8 | 15,000–500,000 | 64 | solved by 3/3 bare oracles |
| hard | 53 | 8 | 40,000–800,000 | 128 | solved by 3/3 bare oracles |

`escalate` first increases the number of components at fixed `k`, enlarging the assignment haystack without lengthening the certificate. It next strengthens attack conditioning. A subsequent increase from `k=53` to `k=59` at `t=11` would cross the 300-operation intended-route cap, so the generator reports `cap_bound` instead.

## Gate results

| gate | measured result at `easy`, unless noted |
|---|---|
| G1 | 12/12 planted witnesses verified across four presets and three seeds; all answers JSON-round-trip |
| G2 | 8/8 corruption classes rejected with eight distinct diagnostics |
| G3 | tagged, fenced, prose-surrounded answer round-tripped; garbage returned `None` |
| G4 | 0/200,000 valid structure-aware guesses from 2,449,380,252,051,393,086,407,492,937,986,560 onto assignments |
| G5 | shipping density 0/200,000; demo exact count 12/186,480; reference total 408,638 nodes and 2,363,676 operations in 0.752 s |
| G6 | length-rank, tightest-residual, largest-residual, random-greedy, and affine-modulo attacks each solved 0/8; Track-B reference solved 8/8 |
| G7 | `k=74` size-doubled instance built and verified; next escalation raises components from 8 to 9 at fixed answer length |
| G8 | 40/40 component-permutation invariance checks and 40/40 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | 118 characters, about 30 tokens, 37 atoms, and 231 intended-route operations; cap gate passes |

## Oracle loop

The bare run used the repository’s configured Gemini 3.8 Flash / GPT-5.6 Terra pool. Every reply parsed and independently verified. The table groups the three seeds at each level; “3/3 solved” means three valid witnesses, not merely plausible text.

| round | preset / parameters | seeds | result | why |
|---:|---|---|---:|---|
| 0 | easy: `k=37,t=8,min=5,000` | 1372683617, 1865880256, 2025939008 | 3/3 solved | all witnesses verified |
| 1 | medium: `k=45,t=8,min=15,000` | 1681803361, 695006671, 853837756 | 3/3 solved | all witnesses verified |
| 2 | hard: `k=53,t=8,min=40,000` | 1317078567, 1387726442, 2100883112 | 3/3 solved | all witnesses verified |
| 3 | escalated: `k=53,t=9,min=40,000` | 758362860, 87672596, 285787122 | 3/3 solved | all witnesses verified |
| 4 | escalated: `k=53,t=10,min=40,000` | 1423906561, 1992053188, 905148001 | 3/3 solved | all witnesses verified |
| 5 | escalated: `k=53,t=11,min=40,000` | 1472754262, 2132872906, 60579558 | 3/3 solved | all witnesses verified |
| 6 | escalated: `k=53,t=11,min=80,000` | 930151371, 871234602, 1718672772 | 3/3 solved | all witnesses verified |

The terminal verdict in `.meta.json` is `budget_bound`, not `hardened`: the loop exhausted its six escalation rounds while `k=53,t=11,min=100,000` was still available. This result does not support shipping the provisional preset.

## G9 diagnostic arms

| arm | usable solved/attempts | outcome |
|---|---:|---|
| bare | 3/3 | all three provisional `easy` instances solved and verified |
| structural hint | 3/3 | all three isolated `easy` instances solved and verified |
| placebo hint | 3/3 | all three isolated `easy` instances solved and verified |

Hinted minus placebo is `1.0 - 1.0 = 0.0`. The structural hint names one invariant—residue classes modulo `t+4` stay intact—and gives no chained procedure, but it bought no measured improvement because the rung was already solved at ceiling rate. These arms are diagnostic and non-gating. G9(c), the actual cap gate, passes with 118 characters, 37 atoms, and 231 intended-route operations.

## Use

```python
import json
from gen_2003_09314 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
prompt = render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

From the repository root, the normal emission command is:

```bash
bash scripts/emit.sh 2003.09314
```

The current `budget_bound` metadata intentionally prevents treating this as a hardened release; retain the command for a future rerun after the parked family is redesigned or the hardening budget is explicitly extended.

## Caveats

The `0/200,000` density estimate is for a uniform onto assignment of labeled radii to labeled nonempty components. It does not model a solver that uses component sums, subset-sum propagation, or the planted residue invariant, and it is not an exact solution count at shipping size. The family is deliberately easy for the exact reference program and for anyone who notices that congruence classes stay intact; that is the Track-B claim.

The answer is a compressed burning schedule rather than a literal list of `k` vertex pairs. This is not a weaker witness: the checker deterministically expands it and checks every source-separation and interval-coverage condition. The path forest itself is represented only by component orders, the representation used in the cited path-forest algorithm; expanding all `k^2` path vertices would add transcription without changing the problem.

The panel did not run industrial ILP, CP-SAT, SAT, generating-function, or meet-in-the-middle solvers. Filtering is conditioned on the five reported attacks and on a bounded reference-cost window, so its measured density is a property of that conditioned distribution. The canonical key is exact for path forests because their isomorphism type is precisely the multiset of component orders.

Most importantly, the cross-vendor result is negative for release: 21/21 bare oracle attempts succeeded, and all six G9 comparison attempts succeeded. The generator’s obvious modular structure is likely easier for language models to recognize than the local attacks suggested. The family is parked rather than rejected only because the harness reached its escalation budget one valid conditioned level before the compact-route cap; no claim is made that this remaining level would hold.
