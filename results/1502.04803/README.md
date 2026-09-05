# Succinct sparse independent-set reconfiguration

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | combinatorics / finite discrete |
| Core / certificate | graph / integer tuple (a signed TAR move sequence) |
| Native objects | exact sparse graph, source and target independent sets, reconfiguration sequence |
| Intuition | invariant: edge toggles cancel modulo two, exposing a forced dependency chain |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

This generator instantiates Independent Set Reconfiguration (ISR) from
[Lokshtanov et al., *Reconfiguration on sparse graphs*](https://arxiv.org/abs/1502.04803).
The solver receives an ordinary simple graph, specified exactly by succinct
batches of edge toggles, and two independent sets of size `k`.  It must give an
explicit token-addition/removal (TAR) sequence: each step touches one vertex,
every intermediate set is independent, and its size stays in `[k-1,k]`.
`verify` computes exact toggle parity for the relevant edges and replays the
submitted sequence; it never reads the planted answer.

Generation is inverse, not search.  The generator samples ordered pairs
`(s_i,t_i)` and adds the mandatory edges `t_i--s_i` and
`t_i--s_(i-1)`, plus seed-dependent edges from `t_i` to still earlier source
vertices.  Initially only `t_0` can be added after one deletion.  Inductively,
after ranks below `i` have moved, `t_i` has the sole remaining blocker `s_i`,
while every later target retains two mandatory blockers.  Thus the planted
shortest sequence is forced.  Each final edge is then encoded as one inclusive
arithmetic progression and the same progression without its first term; all
shared toggles cancel.  Decoy boundaries are emitted twice and cancel as well.
Plants and decoys use the same distribution of spans, steps, orientations and
offsets.

## Why Track B

Track A would be false.  Sections 1–2 give the exact ISR/TAR definition and
note its equivalence to token jumping.  In Section 3.1, Lemma 1 deletes
irrelevant low-degree vertices using a sunflower, and Theorem 2 proves ISR is
FPT in `k+d` on `d`-degenerate graphs by kernelization followed by exhaustive
enumeration.  These generated graphs have only `O(k)` final edges and degeneracy
at most `k`, so that easy-regime result applies.  The paper also records
PSPACE-completeness on bounded-bandwidth graphs and W[1]-hardness on general
graphs, but neither worst-case statement is claimed for this distribution.

The measured successful reference algorithm performs exact modular membership
tests for every pair of endpoint vertices and then breadth-first search in the
bounded TAR state graph.  Its complexity is
`O(B k^2 log n + explored transitions)`; at shipping it solved 8/8 instances,
averaging **98,418 counted exact operations, 66 states, 642 transitions and
about **0.002 s**.  Literal expansion of the reported shipping instance would
perform **95,305,568 toggles**.  The compact route instead pairs equal batch
tails, cancels parity, and propagates the forced chain in **244 exact
operations**.  This benchmark tests whether a no-tool solver notices that
invariant; it does not claim the problem is hard for a computer.

## Worked demo (`seed=0`)

This smallest instance is hand-solvable: pair batches with equal absolute step
and common numerical endpoint, retain each unmatched first update modulo 121,
then follow the forced blockers.

```text
Independent-set reconfiguration in a succinct sparse graph

A simple undirected graph has vertices labelled 1 through n=11.  A set is independent when no graph edge has both endpoints in the set.

The graph starts empty.  Apply every edge-toggle update in every batch below.  Toggling an absent edge inserts it; toggling a present edge deletes it.  Thus two toggles of the same edge cancel.

For an integer x, set q = x mod n^2 = x mod 121, using the residue in {0,...,n^2-1}.  Write q=a*n+b with 0<=a,b<n.  If a=b, the update does nothing.  Otherwise it toggles the undirected edge {a+1,b+1}; the two orders name the same edge.

A batch [first,last,step] is the inclusive integer progression first, first+step, ... , last.  Its nonzero step has the sign needed to reach last, and both endpoints are included.

Batches (16 total, in arbitrary order):
  [1185500743,1185501191,64]
  [416309141,416308677,-58]
  [186382499,186382352,-21]
  [509748627,509748767,20]
  [661388945,661389215,45]
  [661388900,661389215,45]
  [1185500679,1185501191,64]
  [416309141,416308735,-58]
  [671525305,671524633,-96]
  [186382331,186382499,21]
  [190555975,190556035,10]
  [222602773,222602297,-68]
  [222602773,222602229,-68]
  [671524729,671525305,96]
  [190556035,190555965,-10]
  [509748767,509748647,-20]

Source independent set I_s (size k=3): 1, 7, 11
Target independent set I_t (also size k): 4, 5, 8

Give a reconfiguration sequence of exactly 6 single-vertex operations.  Start at I_s and finish at I_t.  After every operation the current set must be independent and have size k or k-1. Consequently operations alternate removal and addition, beginning with a removal.  Vertex labels are 1-indexed; repetitions are forbidden.

Encode a removal of vertex v as the negative integer -v and an addition as the positive integer v.  Give your final answer inside <answer></answer> tags as one JSON list of signed integers.
Example syntax: <answer>[-3,17,-8,2]</answer>
Output nothing else inside the tags.
```

Answer: `<answer>[-7,5,-11,8,-1,4]</answer>`.  `verify` returns
`(True, "ok")`; dropping the last operation returns
`(False, "expected exactly 6 operations")`.

## Difficulty and validation

The final ladder was slid upward after the first hardening run.  Counts below
use seed 0; the 16-operation answer stays fixed while the ambient modulus and
mechanical replay grow.  The clean final oracle run solved `easy` and held
`medium`; `hard` is retained as the next rung but was not reached in that run.

| Preset | n | k | Decoys | Batch span | Batches | Literal toggles | Compact ops | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| demo | 11 | 3 | 1 | 7 | 16 | 128 | 71 | hand example |
| easy | 1,007 | 8 | 4 | 400,000 | 56 | 23,961,992 | 244 | oracle solved 1/3 |
| **medium** | **2,015** | **8** | **4** | **1,600,000** | **56** | **96,754,620** | **244** | **ships; oracle 0/3** |
| hard | 4,031 | 8 | 4 | 6,400,000 | 56 | 383,391,896 | 244 | reserve, not reached |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verify across all presets |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose/fence round-trip succeeds; answer is JSON-native; garbage returns `None` |
| G4 | 0/200,000 structure-aware guesses; bounded space `(8!)^2 = 1,625,702,400` |
| G5 | shipping density 0/200,000; demo exact count 1; reference 98,418 ops / about 0.002 s |
| G6 | five attacks each 0/8; reference and compact algorithms each 8/8 |
| G7 | doubled `n=4,031` instance builds/verifies with the same 16-operation answer |
| G8 | 100/100 invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | worst case 84 chars, 53 conservative tokens, 16 atoms, 244 operations |

G6 covers longest-batch endpoint outliers, ascending and descending label
greedies, the visible unpaired-first-endpoint ansatz, and 256 structure-aware
random restarts per seed.  The successful modular-membership/BFS algorithm is
reported separately, as Track B requires.

## Oracle loop and G9 diagnostics

The clean bare transcript contains only the following six script-owned calls.
The two `parse_answer`/empty cases ended without a final answer; inspection
confirmed there was no answer hidden in prose, so they are not parser bugs.

| Preset | Seed | Model | Solved | Result |
|---|---:|---|---:|---|
| easy | 642274238 | Gemini 3.8 Flash | yes | verified `ok` |
| easy | 692400629 | GPT-5.6 Terra | no | operation 13 creates an edge |
| easy | 720374134 | Gemini 3.8 Flash | no | length-limited empty response |
| medium | 1992636460 | GPT-5.6 Terra | no | operation 3 creates an edge |
| medium | 1867796197 | Gemini 3.8 Flash | no | length-limited reasoning, no answer tags |
| medium | 895799263 | GPT-5.6 Terra | no | operation 1 creates an edge |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened at shipping |
| structural hint | 0/3 | hardened |
| placebo hint | 1/3 | solved once |

`hinted - placebo = -1/3`.  The parity hint bought no measurable help and the
placebo did better, so the three samples support no positive causal claim about
the declared invariant; sampling variance or a generic prompt effect is the
safer interpretation.  Answer size is 84 characters / 53 conservative tokens /
16 atoms, and the intended route is 244 operations.

## Use

```python
import json
import gen_1502_04803 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
raw = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(raw)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1502.04803 20 medium
```

## Caveats

The paper studies explicit graphs, not this succinct edge-toggle encoding, and
does not impose the benchmark's exact shortest-length output request.  The
encoding nevertheless defines an ordinary graph exactly; no graph/SAT or
finite-field surrogate replaces the paper's native object.  With tools the
family is intentionally easy, as the roughly 0.002-second reference demonstrates.

G4 samples uniformly from the strongest freely deducible prior: independent
permutations of all source removals and target additions with the required sign
pattern.  It does not model a solver that recognizes batch cancellation, so
0/200,000 is guess resistance, not a complexity claim.  No external SAT/SMT
solver, optimized implementation of the paper's full kernelization, or general
succinct-graph package was run.

Most importantly, the displayed batch count and 244-operation compact route do
not grow between non-demo presets; only numeric/modular workload grows.  An
earlier exploratory master seed intermittently solved medium and hard and held
only a later escalation, whereas the final isolated run held medium.  The
shipping result is therefore a sampled Track-B no-tool threshold, not robust
average-case evidence.  The G9 placebo success reinforces that warning.
