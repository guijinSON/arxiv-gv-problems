# arXiv 1608.06944 — rejected zero-sum-flow candidate

Status: **rejected because H fails on the generated distribution**. Generation and exact verification are sound, but a construction-aware attack solves every tested instance, including the largest instance writable under the 256-atom answer cap. The retained module is an audit artifact, not a shippable family.

| Profile field | Value |
|---|---|
| Track evaluated | A — structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer edge-flow tuple |
| Native objects | all-negative signed simple `(3,4)`-semiregular graph and a zero-sum 3-flow |
| Intended intuition | joint propagation of sign type and magnitude-two choices |
| Domain essentiality | native; no reduction |

## Problem and provenance

The candidate comes from Kaiser, Lukot'ka and Rollová, [*Nowhere-zero flows in signed graphs: A survey*](https://arxiv.org/abs/1608.06944). Section 2.7 defines a zero-sum `k`-flow as a nonzero integer edge labelling whose incident values sum to zero at every vertex, and identifies it with a nowhere-zero flow of the all-negative signed graph. Theorem 27(ii) reports NP-completeness of deciding whether a `(3,4)`-semiregular graph has a zero-sum 3-flow. The same section records the easy `(2,4)` regime with only `O(log n)` degree-4 vertices.

The draft inverse-generates a certificate: it samples local patterns `(1,1,-2)` and `(-1,-1,2)` at degree-3 vertices, compatible zero-sum patterns at degree-4 vertices, matches equal-valued half-edges, then relabels vertices and edges. `verify` checks only the candidate vector and instance, with exact integer sums; it never reads the planted answer. Thus G and V pass.

## Why H fails

The original attack panel stopped after a greedy second stage. The missing completion is exact and simple. Once a sign type is fixed at every degree-3 vertex, each degree-4 vertex has two neighbours of each type. Selecting the unique magnitude-two edge at every degree-3 vertex is equivalent to a bipartite perfect matching between the two type classes: two vertices are adjacent in the matching graph when they share a degree-4 neighbour. A matched pair selects that common neighbour. Hopcroft–Karp then completes a valid flow.

The retained `_type_then_matching_attack` uses the draft's planted-blind exact-2-in-4 propagation for sign types and Hopcroft–Karp for completion. It solved 8/8 seeds at all tested writable sizes:

| `n` | vertices | edges / answer atoms | solved | mean wall time | maximum |
|---:|---:|---:|---:|---:|---:|
| 18 | 126 | 216 | 8/8 | 0.0093 s | 0.0156 s |
| 20 | 140 | 240 | 8/8 | 0.0129 s | 0.0200 s |
| 21 | 147 | 252 | 8/8 | 0.0249 s | 0.0666 s |

Times are single-process Python measurements from the rejection audit and vary with host load. At `n=21`, matching took two breadth-first phases and about 482–500 edge scans per seed. The exact sign-type phase remains exponential in the worst case, so this does not contradict Theorem 27; it shows that this planted distribution is easy.

Track B does not rescue the candidate. The mechanical route at the largest writable instance already takes under 0.07 seconds. The compact route is the same type-propagation-plus-matching decomposition, not a shorter invariant or change of variables. There is no meaningful no-tool compression gap to benchmark.

## Worked demo

For `make_instance(n=1, seed=1)`, the edge list is:

```text
0:1-3  1:1-6  2:0-6  3:4-5  4:0-3  5:2-6
6:2-4  7:2-3  8:5-6  9:3-5  10:1-4  11:0-4
```

One valid answer is `[-1,2,-2,-2,1,-1,2,-1,1,1,-1,1]`. It gives `(True, "ok")`; changing the first entry to zero gives `(False, "edge 0 value 0 is outside {-2,-1,1,2}")`. The demo is hand-solvable, but it is illustrative only.

## Gate audit

| Gate | Result |
|---|---|
| G1 | planted flows verify across every preset and seed tested |
| G2 | five corruptions are rejected with distinct reasons |
| G3 | tagged, fenced JSON round-trips |
| G4 | 0/200,000 structure-aware random candidates verified at `n=18` |
| G5 | **fails hardness**: the strongest construction-aware attack returns a witness in milliseconds |
| G6 | **fails**: exact type-then-matching succeeds 8/8 |
| G7 | doubled instances build and verify |
| G8 | tested vertex/edge relabellings preserve the structural key |
| G9(c) | the nominal `n=18` answer fits, but this cannot repair H |

The earlier oracle transcripts contain only HTTP 403 service errors and make no hardness claim. No further oracle calls were warranted after the local attack broke G6.

## Reproduce the decisive check

```python
import importlib.util, random

spec = importlib.util.spec_from_file_location(
    "g", "results/1608.06944/rejected_gen_1608_06944.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(n=21, seed=0)
answer, stats = g._type_then_matching_attack(inst, random.Random(2500))
assert g.verify(inst, answer) == (True, "ok")
print(stats)
```

## Caveats

- The rejection is of this inverse-generated distribution, not of the paper's worst-case problem or every possible generator based on it.
- Zero random hits estimate solution density under the declared degree-3-aware prior; they never established computational hardness.
- A different theorem-backed gadget distribution based directly on the Monotone NAE-3-SAT reduction behind Theorem 27 might still be viable, but it is not what this draft generated.
- The canonical key is a strong color-refinement/BFS invariant, not a complete graph-isomorphism canonical form.
- The external four-vendor loop was unavailable because its OpenRouter key had exceeded its limit; this is immaterial to the rejection because G6 already fails locally.
