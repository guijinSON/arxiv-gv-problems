# Planar L1 Freeze-Tag schedule generator (arXiv:2509.14357)

This module generates witness-search instances from de Oliveira Silva and Pedrosa, [“Freeze-Tag is Strongly NP-hard in 2D with Lp Distances”](https://arxiv.org/abs/2509.14357) (v4). A solver receives labeled robots at integer plane coordinates and an inclusive deadline. It must assign every `A_i` to a distinct `B_j`, then send the two robots available there to the two robots in a distinct `C_k` pair. The certificate is two permutations. `verify` replays both terminal routes with exact Manhattan distances, so checking costs polynomial time and no floating-point arithmetic.

## Why this is the paper’s hard regime

Section 2 defines a Freeze-Tag schedule as a rooted wake-up tree and its makespan as the longest root-to-leaf path. Theorem 3.1 proves strong NP-completeness for planar L1 instances with integer coordinates and an integer deadline. More specifically, Section 3.3 reduces distinct-input Numerical 3-Dimensional Matching (N3DM) to the exact coordinate pattern used here. Lemma 3.6 forces every feasible schedule into the `A -> B -> two C terminals` normal form; Lemma 3.7 and Section 3.3.4 prove that its two permutations are exactly an N3DM witness. The “Additional consequences” paragraph also transfers strong ASP-hardness to rational schedules.

The easy results do not cover this regime. Section 1 reports polynomial solvability on unweighted stars and a PTAS in fixed-dimensional Lp space; these instances are planar geometric instances rather than unweighted stars, and the task is exact feasibility at the reduction’s tight deadline rather than approximation. The paper gives no FPT algorithm for this parameterization. The module stays at `p=1`, where every comparison is integral; it does not use the `1<p<infinity` regime whose exact-distance membership in NP is deliberately left open.

Generation is genuinely inverse: both answer permutations are shuffled before any numerical value is chosen. Every planted triple is then made from three distinct deviations summing to zero, randomly permuted among the U, V, and W roles, with global collisions rejected. Plants therefore do not occupy a special value range or input position. The paper’s Section 3.3 formulas turn those values into robot locations, and the public robot lines are shuffled independently.

## Worked example

For readability this uses the smallest supported construction, `make_instance(n=3, band=2, seed=0)`, below the shipping preset. Its complete rendering is:

```text
Planar L1 Freeze-Tag: find a deadline-feasible normal-form schedule

There are 14 labeled robots at integer points in the plane.  Distance
between (x1,y1) and (x2,y2) is the Manhattan distance
|x1-x2|+|y1-y2|.  Robot O is active at time 0; every other robot is frozen.
An active robot moves at speed at most 1.  When it reaches a frozen robot, that
robot activates immediately, and the arriving robot and the newly active robot
may move independently.  Waiting is allowed.  All robots must be active by the
inclusive deadline L=168750.

For this instance, construct the following normal-form schedule.  Robot O moves
along the straight segment from O to Z, activating every A robot on that segment
in increasing distance from O.  On reaching A_i, one available robot goes by a shortest
L1 path directly to one B_j.  The two robots then available at B_j go by shortest
L1 paths, one directly to C_k.1 and one directly to C_k.2.  Choose exactly one
B_j and one paired C_k for each A_i, using every B index j=0,...,2 exactly
once and every C-pair index k=0,...,2 exactly once.  Routes may cross and
robots may wait; there are no collision, congestion, or capacity constraints.

Robot data are shuffled.  Each line is: label x y.  Labels and indices are
literal and 0-based; C_k.1 and C_k.2 are two distinct robots in pair k.
C1.2 95040 71348
C0.2 47520 118862
O 0 0
A0 65 0
C2.1 118800 47594
C2.2 142560 23834
A2 63 0
A1 69 0
C1.1 71280 95108
B1 -540 -581
B0 -270 -843
Z 168750 0
C0.1 23760 142622
B2 -810 -302

Output a JSON array of exactly 3 two-integer rows.  Row i (rows are ordered
i=0,...,2) must be [j,k], meaning A_i activates B_j and B_j activates both
C_k.1 and C_k.2.  Both columns must be permutations of 0,...,2; order
inside [j,k] matters, and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example: <answer>[[2,0],[0,1],[1,2]]</answer>
Output nothing else inside the tags.
```

One answer is `[[0,2],[2,1],[1,0]]`; `verify(inst, answer)` returns `(True, "ok")`. Dropping its last row gives `[[0,2],[2,1]]` and returns `(False, "wrong row count: expected 3, got 2")`.

## Difficulty presets

| Preset | `n` | Robots | Naive `(n!)^2` digits | Status |
|---|---:|---:|---:|---|
| discarded draft | 40 | 162 | 96 | rejected by G6: capped exact MRV solved 3/3 sampled instances in at most 1.9 seconds |
| `standard` | 125 | 502 | 419 | **ships; five attacks and the three-vendor panel held** |
| `hard` | 170 | 682 | 614 | available; not reached |
| `extreme` | 225 | 902 | 867 | available; not reached |

`escalate` grows `n` by roughly one third while keeping `band=2`. Larger `n` strictly increases the witness length and search space, while inverse planting preserves satisfiability. `band=2` deliberately crowds the compatibility relation; widening the band can expose low-degree forced choices and is not treated as a safe hardening direction.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 9/9 plants verified: three seeds for every preset |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | All 125 rows recovered from tagged JSON surrounded by prose and a Markdown fence |
| G4 | **0/200,000** valid guesses; each guess first makes random locally compatible A-B choices, then repairs B and C to permutations |
| G5 | At `n=7`, seeds 5, 6, and 7 each had exactly 1 answer out of 25,401,600 (`3.94e-8`) |
| G6 | Index alignment, degree/outlier, left-to-right nearest, 64-restart randomized MRV, and exact MRV capped at 100,000 nodes each solved **0/8** shipping instances; exact MRV exhausted all 100,000 nodes on every seed |
| G7 | Doubling to `n=250` built 1,002 robots and the plant still verified |
| G8 | 160/160 composed invariance checks, 160/160 carried-answer checks, and 20/20 unrelated keys distinct |

The exact corruption reasons, counts, prior description, and canonical transformations are in `selftest_report.json`.

## Required oracle loop

`scripts/harden.py` stopped at round 0 with `verdict: hardened` and shipping parameters `{"n":125,"band":2}`. Both visible answers parsed correctly; there is no parser-induced false negative.

| Preset | Seed | Model | Outcome | Recorded reason |
|---|---:|---|---|---|
| `standard` | 1914865257 | Gemini 3.1 Pro Preview | Failed | Parsed permutations; route `A1->B1->C123.1` was 82 time units late |
| `standard` | 1009308615 | Claude Sonnet 5 | Failed | Empty response after all 32,000 completion tokens were consumed (`finish_reason=length`) |
| `standard` | 1820044077 | GPT-5.6 Terra | Failed | Parsed identity permutations; route `A2->B2->C2.1` was 786 time units late |

The three deciding failures came from three distinct vendors as required. Full replies, timings, statuses, and the master seed are script-owned in `llm_loop_transcript.jsonl` and `.meta.json`.

## Use

```python
import gen_2509_14357 as freeze_tag

params = freeze_tag.DIFFICULTY[freeze_tag.SHIPPING_DIFFICULTY]
inst = freeze_tag.make_instance(seed=42, **params)
question = freeze_tag.render(inst)
candidate = freeze_tag.parse_answer(model_output)
ok, reason = freeze_tag.verify(inst, candidate)
```

From the repository root:

```bash
python3 results/2509.14357/gen_2509_14357.py
bash scripts/emit.sh 2509.14357 20 standard
```

## Caveats

- The theorem is worst-case hardness for the full integer-coordinate planar L1 family, not an average-case theorem for this planted distribution. The role-symmetric value sampler and four attacks remove obvious planting signatures, but do not prove distributional hardness.
- G4 is not uniform sampling from the naive `(n!)^2` space. It is deliberately stronger: rows are visited randomly, locally deadline-compatible unused B choices are preferred, then dead ends and duplicate C values are repaired so both output columns remain permutations. That sampler is not uniform. `0/200,000` is empirical evidence on one shipping instance, not a confidence-free proof for all seeds or all solver priors.
- The panel did run a simple exact MRV depth-first search, but only to a fixed 100,000-node budget. It did not run a full SAT/SMT/ILP solver, uncapped exhaustive rainbow-matching search, augmenting-cycle local search, or a learned detector for the planted matching. Models in the required oracle loop had no external solver tools.
- Small `n`, a loose deadline, a revealed matching, or a band so wide that compatible triples have conspicuously low degree can make instances easy. Approximate FTP solutions are also easier, but do not satisfy this exact witness checker.
- Claude’s deciding result was a length-budget failure, weaker evidence than an incorrect parsed witness. Gemini and Terra did emit parseable but invalid witnesses.
- `canonical_key` exactly removes label/order changes, C-copy swaps, translation, and the eight signed-axis L1 symmetries. It does not solve for accidental non-geometric isometries of a finite point set; the role-tagged geometric representation is the family’s declared equivalence.
