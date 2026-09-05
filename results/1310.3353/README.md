# arXiv 1310.3353 — verified weighted point-graph clustering

| Profile field | Value |
|---|---|
| Track | **B** — no-tool compression; an efficient exact algorithm exists |
| Native domain | optimization |
| Object regime | finite discrete (integer coordinates and weights) |
| Computational core | graph |
| Certificate | integer tuple of consecutive cut ranks |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This generator instantiates the weighted cluster-editing problem from Bellitto,
Marschall, Schönhuth, and Klau, [*Next Generation Cluster Editing*](https://arxiv.org/abs/1310.3353).
The solver receives a one-dimensional weighted point graph in an affine residue
representation.  After sorting the induced line coordinates, it must give cut ranks
whose consecutive clusters have total insertion/deletion cost no greater than the
displayed integer budget.

Generation is inverse, not solver-driven: `make_instance` first chooses symmetric
point bands and their cut ranks, computes that witness's exact cost, and then applies
an invertible affine residue encoding.  `verify` never reads `inst["answer"]`; it
decodes coordinates and recomputes the candidate's weighted edit cost using integers.
Any cut list meeting the budget is accepted.

## Why Track B

Section 2.2 fixes the weighted cost: same-cluster negative weight costs `-w`, while
different-cluster positive weight costs `w`.  Theorem 2 in Section 3.1 proves that a
one-dimensional weighted point graph has an optimal clustering of consecutive points,
and the following exact algorithm computes it in `O(n^2)`.  Section 3.1.2 explicitly
identifies the easy large-cluster regime: truncating the dynamic program gives the
paper's `O(nk)` heuristics.  Section 3.2.2 also says the exact recurrence optimizes
consecutive clusterings for any supplied order.  These results rule out Track A.

At the shipping preset, the exact reference algorithm succeeds 8/8, as it should.  It
performs 7,206 exact arithmetic operations per instance and averaged 0.000519 seconds in
CPython.  That is trivial with code but not a hand route.  The compact route is to
recognize the affine residue coordinate's symmetric bands, classify each point by its
band, and cumulatively count the band populations.  After that insight it takes 197
exact arithmetic operations (four per point plus five cumulative additions), within
the no-tool cap.  The deliberately remote same-band points make “take the largest
coordinate gaps” return the wrong cuts.

## Worked demo

For `make_instance(seed=23, **DIFFICULTY["demo"])`, the complete rendered data are:

```text
There are 12 points z:
5385 6517 6926 3266 3546 6680 2 5465 6354 608 5548 5711
p = 8191, A = 869, B = 702, L = 1968, budget = 5352.
x(z) = (869*z + 702) mod 8191 and w(u,v) = 1968 - |x(u)-x(v)|.
Return increasing cut ranks for consecutive clusters.
```

The answer is `<answer>4, 8</answer>`.  `verify(inst, [4, 8])` returns
`(True, "ok")`; dropping the second cut returns
`(False, "budget exceeded: cost 12264 > 5352")`.  Exhaustive enumeration finds
exactly one valid answer among all 2,048 cut subsets.  A person can solve this demo by
performing twelve small modular transformations and grouping the decoded coordinates.

## Difficulty presets

| Preset | n | constructed bands | modulus bits | reference operations | Ships? |
|---|---:|---:|---:|---:|---|
| demo | 12 | 3 | 13 | 144 | no; hand example |
| easy | 48 | 6 | 31 | 7,206 measured | **yes** |
| medium | 56 | 6 | 61 | `O(56^2)` | no |
| hard | 64 | 6 | 89 | `O(64^2)` | no |

An earlier `n=40, q=5` candidate was rejected despite a bare-oracle `hardened`
verdict: a construction-aware four-cut random restart succeeded on 1/8 panel seeds.
The ladder was shifted to the current fixed five-cut answer before the recorded bare
run.

## Gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified; all JSON round-trips passed |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | model-style prose/fence response parsed to the planted cuts |
| G4 | pass | 0/200,000 valid structure-aware random candidates; space `2^47` |
| G5 | pass | shipping density estimate 0/200,000; 32,768 targeted restarts in 0.101428 s |
| G6 | pass | all five attacks 0/8; reference DP 8/8 |
| G7 | pass | doubled instance, `n=96`, built and verified |
| G8 | pass | 80/80 symmetry checks and 80/80 carried witnesses; 20/20 unrelated keys distinct |
| G9 | pass | 20 chars, 5 atoms, about 5 tokens; intended route 197 operations |

The five failing G6 attacks are raw-coordinate outliers, transformed largest gaps,
4,096 targeted random restarts, positive-gain agglomeration, and equal-size blocks.

## Bare oracle loop

| Model | Seed | Result | Why |
|---|---:|---|---|
| Gemini 3.1 Pro Preview | 1610338114 | failed | parsed cuts cost 20,375,301,038 > 4,772,796,134 |
| Grok 4.6 | 845678568 | error, excluded | 900-second total deadline |
| Grok 4.6 redraw | 533030471 | failed | parsed cuts cost 12,719,765,658 > 4,531,135,570 |
| GPT-5.6-Terra | 1995748491 | failed | parsed cuts cost 21,798,554,425 > 4,410,305,288 |

The harness verdict is `hardened` at `easy`, with three distinct counted vendors.

## G9 arms

| Arm | Solved / attempts | Verdict or note |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; G9(b) passes |
| placebo hint | 0 / 3 | hardened diagnostic |

`hinted - placebo = 0.0`.  The structural sentence bought this oracle sample no
measurable success, so the run does not show positive sensitivity to the declared
change-of-variables intuition.  It does show that merely naming the invariant does not
dissolve the task.  One counted Claude call in each hint arm exhausted its 32,000-token
reasoning allowance and emitted no answer; the other counted failures supplied parsed,
over-budget cuts.  Each arm also contains one excluded 900-second Grok timeout.

## Use

From the repository root:

```python
import importlib.util

path = "results/1310.3353/gen_1310_3353.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

Emit instances with `bash scripts/emit.sh 1310.3353 20 easy`.

## Caveats

This is a no-tool benchmark, not a computational-hardness claim.  Giving a solver a
CAS, the decoded line coordinates, the band pitch, or the paper's dynamic program makes
it easy.  The 0/200,000 density estimate samples uniformly from **all** legal cut
subsets; it is not a proof of uniqueness and does not model every informed prior.  A
stronger targeted prior was tested by 32,768 five-cut restarts, also with zero success,
but that is still finite evidence.  The planted witness is not asserted optimal even
though the reference DP found a budget-feasible optimum on every tested seed.  No LP,
SDP, commercial ILP solver, or specialized pruned segmentation implementation was
tested; the exact paper DP is the relevant successful reference baseline.
