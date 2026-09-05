# arXiv 1111.0934 — hidden equal-load SALBP-2 schedules

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | optimization |
| Object regime | finite discrete |
| Computational core | subset sum |
| Certificate form | integer tuple (the paper's task-to-station assignment) |
| Intended intuition | decomposition by a concealed residue invariant |
| Domain essentiality | native |
| Reduction | none |

This module turns Ritt and Costa's [*Improved integer programming models for
simple assembly line balancing and related problems*](https://arxiv.org/abs/1111.0934)
into a two-station SALBP-2 feasibility problem. The solver receives positive
integral task times, an empty precedence order, and a cycle time, and must assign
every task to station 0 or 1. Verification sums the two loads exactly and checks
the capacity and cardinality conditions; it never reads the planted answer.

## Why the construction is valid, and what “hard” means

Section 1 defines SALBP and SALBP-2 and says its decision version is NP-complete
even without precedences, where it is identical-parallel-machine makespan
scheduling. That is the exact native regime used here, but it is not a Track-A
claim about this distribution. The same section names strong constructive,
heuristic, and exact methods, while Section 5 uses CPLEX branch-and-cut and a
600-second limit. Those facts rule out treating worst-case NP-completeness as
distributional evidence.

Generation is by composition of identities, not solution search. Each hidden
four-task group has quotients satisfying `q0+q3=q1+q2`; all four task times have
the same residue modulo 997. One equal pair is independently assigned to each
station, the task order is shuffled, and a common offset forces every feasible
schedule to use exactly half the tasks at each station.

This is honestly Track B. The domain-standard Horowitz–Sahni exact
meet-in-the-middle algorithm is `O(2^(n/2))`; on eight shipping instances it
solved 8/8 using 8,534,741 exact add/subtract steps (1,066,842 average) and
4.735684 seconds total. A faster algorithm specialized to this generated
distribution hashes all pair sums in `O(n^2)`: it solved 8/8 with 780 additions
per instance and 0.007473 seconds total. The compact route reduces times modulo
997 and tests six pair sums in each four-task bucket: 40 reductions plus 60
additions. Thus an efficient tool route exists and is disclosed; the benchmark
tests whether a no-tool solver discovers the 100-operation decomposition.

## Worked demo (`seed=0`)

The complete rendered instance is:

```text
Two-station simple assembly-line balancing (SALBP-2)

There are 8 indivisible tasks, numbered 0 through 7, and two stations,
labelled 0 and 1. Task i has the positive integral execution time shown below.
Every task must be assigned to exactly one station. There are no precedence
relations in this instance. The load of a station is the sum of the execution
times assigned to it, and its load must be at most the common cycle time
353023271.

Task data are written as task:time:
  0:86621749   1:88557923   2:86974160   3:90302673
  4:89124689   5:88710934   6:88366499   7:87387915

The sum of all task times is exactly twice the cycle time. The displayed range
of task times also forces every feasible assignment to put exactly 4 tasks at
each station. Thus both station loads must equal the cycle time.

Output a JSON list of exactly 8 integers. Entry i is the station label for task
i, so every entry must be 0 or 1; exactly 4 entries must be 0 and exactly 4 must
be 1. Task order is fixed by its 0-based index. The two station labels may be
globally swapped, but entries may not be omitted or repeated.

Give your final answer inside <answer></answer> tags as the JSON list.
Example format: <answer>[0,1,1,0]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[1,0,1,1,1,0,0,0]</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting its last entry
returns `(False, "too few entries: expected 8, got 7")`. The demo has only 70
balanced candidates and exactly four valid assignments, so a person can solve
it by enumerating pairs on paper.

## Presets

| Preset | Tasks | Quotient range | Balanced candidate space | Compact ops | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 10,000 | 70 | 20 | hand example; hardening skips it |
| easy | 40 | 1,000,000,000 | 137,846,528,820 | 100 | **ships; bare oracle hardened** |
| medium | 64 | 1,000,000,000 | 1,832,624,140,942,590,534 | 160 | local gates only |
| hard | 96 | 1,000,000,000 | 6,435,067,013,866,298,908,421,603,100 | 240 | local gates only |

The first evaluated rung already held, so `SHIPPING_DIFFICULTY="easy"`. No
preset was rejected; the larger rungs were unnecessary.

## Gate results

| Gate | Result | Measurement |
|---|---:|---|
| G1 | pass | 16/16 planted witnesses and 16/16 independent residue reconstructions |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON inside prose and a Markdown fence round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; space 137,846,528,820 |
| G5 | pass | demo exact count 4/70; shipping sampled density 0/200,000; both reference costs measured above |
| G6 | pass | five attacks at 0/8; MITM and pair-collision references both 8/8 |
| G7 | pass | every named candidate space grows; doubled `n=80` builds and verifies |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 81 chars, about 21 tokens, 40 atoms, 100 intended operations |

The failing panel comprises smallest-half outliers, largest-processing-time
greedy balancing, sorted alternation, an extreme-pair ansatz, and 256 balanced
random restarts per seed.

## Bare oracle loop

| Model | Preset | Seed | Solved | Recorded reason |
|---|---|---:|---:|---|
| Gemini 3.8 Flash | easy | 278820587 | no | exhausted 32k reasoning budget and emitted no answer |
| GPT-5.6 Terra | easy | 1236336497 | no | parsed assignment overloaded station 0 by 93,059,675,457 |
| Gemini 3.8 Flash | easy | 1906357537 | no | parsed assignment overloaded station 1 by 1,505,080,874,720 |

The script-owned verdict is `hardened` with zero escalations at `easy`.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | held at shipping |
| structural | 3/3 | modulo-997 invariant makes the compact route discoverable |
| placebo | 0/3 | an extra sentence alone did not help |

`hinted − placebo = 1.0`. The hint dissolving the problem is positive evidence
that the difficulty is finding the claimed decomposition, rather than carrying
out arithmetic after it is known. The hinted result is diagnostic, not a gate.
The answer is 81 characters / 40 atoms and the intended route uses 100 exact
operations, all within G9(c).

## Use

```python
import json
import gen_1111_0934 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
prompt = g.render(inst)
candidate = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1111.0934
```

## Caveats

- This is not computational hardness. The `O(n^2)` distribution-specific
  algorithm finishes in well under a millisecond per typical instance; Track A
  would be false.
- The 0/200,000 density is an observed fraction under uniform balanced binary
  assignments. It does not prove the exact shipping density and does not model
  a solver already conditioned on the residue invariant. The construction
  guarantees at least `2^10` valid orientations; unrelated equal partitions may
  also exist.
- One of the three bare failures emitted nothing after exhausting its reasoning
  budget. The other two are substantive invalid witnesses, and the placebo arm
  independently failed 0/3.
- No external ILP/CP-SAT package or CPLEX was run. The exact MITM solver is the
  domain-standard baseline, and the pair-collision solver is stronger on this
  distribution. LLL and Karmarkar–Karp were not separately tested.
- The fourth quotient in a group is derived rather than independent, but the
  station side is randomly complemented per group, so that marginal cannot
  reveal a task's planted station label. The tested outlier and greedy attacks
  found no complete witness on eight seeds.
- `canonical_key` is complete for task renumbering and uniform positive time
  scaling. It does not claim to decide every possible numerical equivalence of
  two scheduling instances.
