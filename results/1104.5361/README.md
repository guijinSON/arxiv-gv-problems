# arXiv 1104.5361 — exact X–Y vertex separators

**Status: parked, not shipped.** The local G1–G9(c) checks pass, but the required
bare oracle loop returned `budget_bound`: every tested level was solved. There is
therefore no honest shipping preset and no G9 hinted/placebo experiment.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (the paper's vertex-set object) |
| Intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## Problem and provenance

The module uses the native objects of Igor Razgon's [*Large Isolating Cuts
Shrink the Multiway Cut*](https://arxiv.org/abs/1104.5361). A solver receives an
implicitly specified undirected graph, terminal sets `X,Y`, and a marked
nonterminal, and must give an exact-size `X`–`Y` vertex separator containing the
mark. Verification checks label syntax, membership, size, and exact reachability;
it does not compare with the planted answer.

Section 2 defines `X`–`Y` separators and important separators. Its lower-bound
construction (Theorem 4 in the rendered paper) joins `r` complete binary-tree
roots to one terminal and all leaves to the other. Its proof constructs a
separator containing a depth-`i` vertex by replacing every marked-path ancestor
with the off-path sibling. This module carries that certificate through an
affine relabelling and random edge subdivisions. `X` contains the strict marked
ancestors, which protects them from deletion and makes the prescribed frontier
size `r+depth`.

## Hardness claim and why this run is parked

This can only be Track B. The Introduction cites an `O*(4^k)` FPT algorithm for
Multiway Cut, and Theorem 3 explicitly enumerates principal important separators.
For this promised family an even simpler standard method exists: delete the
mandatory marked vertex, assign unit vertex capacities to allowed vertices and
infinite capacity to `X∪Y`, split every vertex, and run max flow. The implemented
Dinic reference solver succeeds 8/8. At the provisional hard preset it averaged
2,350,226 edge scans and 0.357 seconds (maximum 2,892,248 scans), while undoing
the affine labelling and writing the sibling frontier takes at most 96 exact
operations.

That mechanical/compact gap justified testing Track B, but it did not survive
STEP 4. Both oracle vendors repeatedly found the compact route. All seven levels,
through `n=14,q=9`, had at least one verified solve; 18 of 21 individual calls
returned verified answers. The harness stopped only at its six-escalation budget
and explicitly ordered the result parked rather than rejected. Increasing the
ambient forest further barely changes the compact calculation, so the current
evidence does not justify calling any preset hard.

## Worked demo (seed 0)

This is the complete output of `render(make_instance(seed=0, **DIFFICULTY["demo"]))`:

```text
Exact X-Y vertex separator in an implicitly specified graph

An X-Y vertex separator in an undirected graph is a set K of vertices outside
X union Y such that, after deleting K and all incident edges, no vertex of X is
connected by a path to any vertex of Y.

This graph has terminals s and t and the following integer-labelled nonterminals.
All arithmetic below is exact integer arithmetic.

Parameters:
  h = 2                 (binary-tree height; roots have depth 0)
  r = 2                 (number of trees)
  q = 2
  C = 14
  m = 7         (base vertices per tree)
  a = 9, b = 6
  A = 26, B = 26, M = 29

Logical base indices are j=0,...,C-1.  Tree z uses j=z*m+u, where
z=0,...,r-1 and u=0,...,m-1 is the usual breadth-first binary-heap index:
u=0 is its root; children of u are 2u+1 and 2u+2 when those indices are <m.
Define E(j)=(a*j+b) mod C.  The branch vertex for j has visible label q*E(j).

For every non-root base index j, define
  L(j) = 1 + (((A*j+B) mod M) mod q).
The edge from j's logical parent to j is replaced by the path whose visible
labels are
  q*E(parent), q*E(j)+L(j)-1, ..., q*E(j)+1, q*E(j).
When L(j)=1 this is just the edge q*E(parent)--q*E(j).  Terminal s is adjacent
to every tree root q*E(z*m).  Terminal t is adjacent to every branch vertex at
depth h.  These and only these are the graph edges and vertices.

The terminal sets are
  X = {s, 6, 26}
  Y = {t}
The required separator must contain marked vertex 22.

Find exactly k=4 DISTINCT integer-labelled nonterminals
that form an X-Y separator and contain 22.  The order of labels is
irrelevant, repetitions are forbidden, and neither -1 nor -2 may be output.

Give your final answer inside <answer></answer> tags as comma-separated integers.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

The answer is `<answer>4, 12, 16, 22</answer>`.
`verify(inst, [4,12,16,22])` returns `(True, "ok")`; deleting the last label
returns `(False, "wrong number of labels: expected 4")`. A person can solve this
demo on paper: `9^{-1}=11 (mod 14)`, after which the marked heap path and its two
siblings are visible.

## Presets and local gates

| Preset | `h,r,depth,q` | Nonterminals (seed 0) | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 2,2,2,2 | 19 | 4 | hand-solvable; not hardened |
| easy | 6,3,4,3 | 755 | 7 | oracle solved 3/3 |
| medium | 8,4,6,4 | 5,105 | 10 | oracle solved 2/3 |
| hard (provisional) | 10,4,6,5 | 24,566 | 10 | oracle solved 2/3; **not shipped** |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verify |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged prose round-trip succeeds |
| G4 | 0/200,000 structured guesses; space 8.89e33 |
| G5 | exactly 300 valid provisional-hard answers; density 3.37e-32; max flow 2.35M scans mean |
| G6 | five attacks, each 0/8; reference max flow 8/8 as expected |
| G7 | next level has 2.335x as many vertices with the same 10-atom answer |
| G8 | 140/140 invariance/witness checks; 20/20 unrelated keys distinct |
| G9(c) | 70 characters, 18 estimated tokens, 10 atoms, 96 operations |

## Oracle loop

| Level | Seeds | Verified solves | Why failures failed |
|---|---|---:|---|
| easy | 1027346452, 203808083, 1688726254 | 3/3 | — |
| medium | 961255171, 782239768, 804850752 | 2/3 | one empty length-limited response |
| hard | 246333125, 521413235, 1860540796 | 2/3 | one proposed set left an X–Y path |
| n=11,q=6 | 418659524, 1567236174, 1367597096 | 3/3 | — |
| n=12,q=7 | 1682012548, 1469320935, 1226715783 | 3/3 | — |
| n=13,q=8 | 741711027, 1327492252, 2098243007 | 2/3 | one reply claimed no solution and supplied no answer |
| n=14,q=9 | 319398617, 1616230834, 400684853 | 3/3 | — |

## G9 diagnostic arms

| Arm | Solved / attempts | Result |
|---|---:|---|
| bare | not separately run | STEP 4 already solved every candidate shipping level |
| structural hint | not run | no shipping preset exists |
| placebo hint | not run | no shipping preset exists |

Consequently `hinted − placebo` is not estimated. Running those paid diagnostics
without a defensible shipping level would not answer the experiment's question.

## Use

```python
from gen_1104_5361 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

After (and only after) a future `harden.py` run returns `hardened`, emission would
use `bash scripts/emit.sh 1104.5361 20 <held-preset>`.

## Caveats

The strongest caveat is decisive: current no-tool oracles solve the family, so it
is not release-ready. The G4 prior is uniform over exact-size, distinct, allowed
sets that contain the mark; it already incorporates every syntactic constraint,
but it is not a model of a solver that notices the affine heap structure. That is
why the tiny density did not predict STEP 4. Edge subdivisions create several
valid frontiers (300 for the measured seed), so the witness is not unique.

The panel did not implement the paper's full principal-important-separator
enumerator, an ILP formulation, or a general-purpose graph-isomorphism package.
Those omissions cannot rescue the hardness claim because the cheaper max-flow
reference already solves 8/8 and the external pool found the compact route. The
canonical key is an exact colored-tree canonicalization followed by SHA-256; its
invariance was tested under arbitrary vertex relabelling, edge order, X–Y swap,
and compositions, but—as with any digest—collision freedom is computational,
not mathematical.
