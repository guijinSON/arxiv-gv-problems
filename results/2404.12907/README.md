# Dynamic FAST progression-cancellation generator

| Profile | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core / certificate | graph / integer tuple (eight directed arcs) |
| Native objects | transitive tournament in an affine order, arc-reversal streams, final feedback arc set |
| Intended intuition | invariant: arc-reversal parity cancels overlapping progressions |
| Domain essentiality / reduction | native / none |

This is a generator for Feedback Arc Set in Tournaments (FAST) from
[Zych-Pawlewicz and Żochowski, *Dynamic Parameterized Feedback Problems in
Tournaments*](https://arxiv.org/abs/2404.12907). The solver receives a
transitive tournament and a sequence of the paper's arc-reversal updates,
written succinctly as arithmetic-progression batches. It must return exactly
`K` final directed arcs whose deletion makes the tournament acyclic.

The construction is certified without solving. It samples `K` answer residues
first. One primitive is a progression paired with the same progression minus
its first term, so common reversals cancel and only one boundary survives.
Target boundaries occur once; decoy boundaries occur twice. Deleting the odd
boundaries leaves a subgraph of the original transitive tournament. `verify`
reconstructs parity from public data, checks each final arc, and checks exact
acyclicity using the displayed topological order; it never reads
`inst["answer"]`. A separate general Kahn topological-sort checker agreed on
all 432 legal demo candidates across 12 seeds.

## Why Track B

Track A would be false. Section 3, Algorithm 1 branches on a directed triangle.
Theorems 3.1 and 3.2 (Appendix Theorems 0.B.1 and 0.B.2) give query bounds
`O(3^K K sqrt(K))` in the promise model and `O(3^K K log^2 n)` in the full
model, after `O(n^2)` initialization. The Introduction also cites a static
`2^O(sqrt(K)) n^O(1)` algorithm. Thus small `K` is explicitly FPT; it is not an
average-case hardness claim.

The measured mechanical reference removes complete modulo-`n` turns and
replays every residual term. At the shipping preset it is `O(Bn)`, solves 8/8,
and averages 4,676,082 exact operations and 0.096987 seconds; the seed-3 stream
contains 172,068,764 literal reversals. The compact route groups normalized
batches by absolute step and right endpoint, keeps each unmatched left
boundary, and cancels equal residues. It takes 240 counted operations. The
benchmark tests whether a no-tool solver finds this compression.

## Worked demo (`seed=0`)

The smallest supported instance is genuinely hand-solvable: match the eight
batch endpoints, cancel their interiors, and reduce the four remaining
boundaries modulo 9.

```text
Dynamic feedback arc set in a tournament

A tournament is a directed graph with exactly one directed arc between
each pair of distinct vertices.  A feedback arc set is a set of directed
arcs whose deletion leaves an acyclic directed graph (one with no directed
cycle).

There are n=9 vertices, labelled 0 through 8.
The initial tournament is transitive in a left-to-right order whose
vertex at 0-indexed position p is (7*p+6) mod n.
The multiplier is coprime to n, so this lists every vertex exactly once.
For positions p<q, the initial arc points from the vertex at position p
to the vertex at position q.

The tournament is updated by all batches below, in the listed order.
The fixed position gap is g=2.  A batch [first,last,step]
means: start with x=first, repeatedly use x:=x+step, and include both
endpoints through x=last.  For every such x, let r=x mod n, using the
residue in {0,...,n-1}, and reverse
the arc between the vertices at positions r and (r+g) mod n.
Each displayed step is nonzero and coprime to n.  Reversing an arc twice
restores its old direction.

Batches (8 total):
  [162525,162545,5]
  [160286,160306,5]
  [162520,162545,5]
  [164761,164751,-2]
  [167024,166992,-8]
  [164761,164749,-2]
  [167024,166984,-8]
  [160281,160306,5]

Find exactly K=2 distinct directed arcs present in the FINAL
tournament such that deleting those arcs makes the resulting digraph
acyclic.  Every listed arc must be one of the fixed-gap chords: its endpoint
positions differ by g modulo n in one direction.  Write it as [tail,head],
use vertex labels (not positions), do not repeat an arc, and sort the list
lexicographically.  Order inside an arc matters; all bounds above are
inclusive/exclusive exactly as stated.

Give your final answer inside <answer></answer> tags as one JSON list of
K two-integer lists.  Example syntax: <answer>[[3,17],[8,2]]</answer>
(the example illustrates syntax only; your list must contain exactly K arcs).
Output nothing else inside the tags.
```

Answer: `<answer>[[2,6],[3,7]]</answer>`. It verifies as `(True, "ok")`;
dropping `[3,7]` gives `(False, "expected exactly 2 arcs")`.

## Difficulty and verification

The hardening loop solved every earlier rung. The final ladder therefore keeps
the last two defeated fixed-witness levels beneath the level that held.
Counts below use seed 0; the G5 reference number is the eight-seed mean.

| Preset | n | K | Decoys | Batches | Literal updates | Compact ops | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 9 | 2 | 1 | 8 | 46 | 46 | hand example |
| easy | 16,381 | 8 | 8 | 48 | 42,649,046 | 240 | oracle solved 1/3 |
| medium | 32,761 | 8 | 8 | 48 | 85,298,094 | 240 | oracle solved 2/3 |
| **hard (ships)** | **65,521** | **8** | **8** | **48** | **170,596,186** | **240** | **oracle solved 0/3** |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verify |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose/fence round-trip succeeds; answers are JSON-native |
| G4 | 0/200,000 structure-aware guesses; space `C(65521,8)=8420502582834386732485679968862490` |
| G5 | shipping density 0/200,000; demo exact answer count 1; baseline 4,676,082 ops / 0.096987 s |
| G6 | five attacks each 0/8; mechanical and compact references each 8/8 |
| G7 | doubled `n=131,041` verifies with the same eight-arc answer |
| G8 | 100/100 invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 113 chars, 65 conservative tokens, 16 atoms, 240 intended operations |

G6 tests batch-length outliers, first-update frequency, endpoint frequency,
indegree-score ordering, and 256 structure-aware random restarts per instance.
The paper's Algorithm 1 is separately recorded with its `3^K=6,561`
branching-node upper bound.

## Oracle loop and G9 diagnostics

Every row below is script-owned evidence at reasoning effort `medium`. “Wrong”
means a parsed but invalid witness; “no tags” means a response from which the
required answer could not be parsed; “length” means the provider used its
response budget without returning content.

| Run level (n) | Seeds | Valid solves | Other outcomes |
|---|---|---:|---|
| original easy (257) | 1204649161, 603749161, 1067786551 | 2/3 | 1 wrong arc |
| original medium (2,047) | 1405878575, 524901210, 158327464 | 3/3 | — |
| original hard (8,191) | 1998845119, 506874201, 1183088071 | 1/3 | 1 no tags, 1 wrong arc |
| escalated (16,381) | 1534843913, 1761806182, 581661747 | 1/3 | 2 no tags |
| escalated (32,761) | 145043278, 2076993310, 1986229500 | 2/3 | 1 no tags |
| escalated (65,521) | 379393604, 370678020, 1481504918 | **0/3** | 1 no tags, 1 length, 1 wrong arc |

The separate shipping-preset G9 arms are diagnostic, not gates.

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. On this sample, naming parity helped no more than an
equal-length, equally styled non-structural sentence. The hint names only the
invariant, not the endpoint-pairing procedure. G9(c) passes with the sizes above.

## Use

```python
import json
import gen_2404_12907 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
candidate = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2404.12907 20 hard
```

## Caveats

This family is deliberately easy with tools and makes no Track-A or
average-case claim. The paper does not analyze arithmetic-progression batch
encoding; the batches succinctly represent its native individual reversal
operation, and the returned witness is still a feedback arc set in the final
tournament. The family becomes easy once endpoint cancellation is recognized.

The G4 prior enforces exact size, distinctness, sorting, chord shape, and final
arc direction, but is uniform over legal chord subsets; it does not model a
learned prior that notices parity. No SAT/ILP encoding, optimized implementation
of the paper's data structure, or external tournament solver was run. The
shipping verdict includes one length-exhausted oracle response; the other two
independent attempts returned substantive but invalid outputs.
