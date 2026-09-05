# Verified SOJA elimination-sequence generator (arXiv:2506.17521)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate form | integer tuple (a total elimination order) |
| Intended intuition | reduction recognition |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed: Section 1's linearized computational graph and Section 3, Theorem 1 |

## What the problem is and why it is trustworthy

This module instantiates **Structural Optimal Jacobian Accumulation** from Bentert, Crane, Drange, Mizutani, and Sullivan, [“Structural Optimal Jacobian Accumulation and Minimum Edge Count are NP-Complete Under Vertex Elimination”](https://arxiv.org/abs/2506.17521). The solver receives a directed acyclic linearized computational graph, its internal/terminal partition, an integer budget, and presentation-only coordinate labels. It must order every internal vertex exactly once. Eliminating a vertex costs its current in-degree times its current out-degree and creates every predecessor-to-successor fill arc.

The generator knows a witness without solving the generated instance. It samples a regular bipartite graph as a union of exchangeable perfect matchings. One matching is an independent set in its line graph, so the complement is a vertex cover. It then applies the paper's Section 3 reduction and the proof's four-block order

`cover-role-2, matching-role-3, matching-role-2, cover-role-3`.

Theorem 1 gives its budget exactly. A random relabelling is applied only after the witness exists. `verify` accepts any valid total order, not just the planted one: it checks syntax, applies a safe necessary condition from the reverse direction of Theorem 1, then exactly replays all eliminations with integer bit sets and compares the accumulated cost. It never reads `inst["answer"]`.

## Why this is Track B

This is not an average-case NP-hardness claim. Section 3 proves worst-case NP-completeness via a linear reduction from Vertex Cover, but does not prove this generated distribution hard; claiming Track A would therefore be wrong. Proposition 4 in Section 5 gives the general exact subset dynamic program in `O(2^r r^4)` time. The shipping graph has `r=110` internal vertices, so its subset lattice alone has `2^110` states before polynomial work.

An efficient distribution-aware algorithm openly exists. The reference algorithm enumerates point-pair slopes, buckets labels by affine intercept, and applies the Section 3 construction. Its complexity is `O(N^2 + A)`; across eight shipping instances it used 63,712 counted high-level exact operations (at most 7,964 on one instance), took 0.032 seconds total, and solved 8/8. That successful algorithm is reported separately from the failing attacks, as Track B requires. The compact no-tool route notices that two coordinate columns are translates, identifies one exchangeable matching class, and places both roles of every paired gadget in 187 elementary comparisons/arithmetic operations. The benchmark tests seeing that compression and carrying it through a 110-entry exact order, not computational intractability.

The explicit easy structures in the paper are also accounted for. Proposition 2 allows internal false twins to be eliminated consecutively; this family creates no internal false-twin blocks. Section 5's exponential DP remains available. The coordinate invariant deliberately makes this special distribution polynomial-time solvable and is stated in both `hardness_basis` and the reference result.

## Worked demo (`seed=7`)

This is the complete output of `render(make_instance(seed=7, **DIFFICULTY["demo"]))` (with the illustrative format example retained):

```text
STRUCTURAL OPTIMAL JACOBIAN ACCUMULATION BY VERTEX ELIMINATION

You are given a directed acyclic graph.  Its vertices are partitioned into
internal vertices and terminals.  To eliminate an internal vertex v:
(1) let P be its current in-neighbors and Q its current out-neighbors;
(2) pay the Markowitz cost |P|*|Q|;
(3) delete v and all incident arcs; and
(4) add every missing directed arc p->q with p in P and q in Q.
A total elimination sequence contains every internal vertex exactly once.
Find a total sequence whose summed cost is at most 63.
All identifiers are 0-based nonnegative integers; order matters and repeats
are forbidden.  Coordinate labels are annotations on paired internal
vertices: each row x:y[:decoys] -> a,b assigns the same label to internal
vertices a and b.  Labels do not change elimination or verification.
All arithmetic, including coordinate residues, is modulo 3.

Internal vertices:
22, 15, 3, 25, 8, 28, 21, 29, 16, 1, 17, 13

Terminal vertices:
23, 19, 26, 12, 18, 6, 11, 2, 9, 4, 14, 20, 10, 7, 0, 27, 24, 5

Coordinate-label classes (x:y followed by any decoy residues -> paired internal IDs):
0:2 -> 28,29
1:2 -> 16,1
2:1 -> 22,13
1:1 -> 3,15
0:0 -> 21,17
2:0 -> 8,25

Directed arcs u->v (one per line; this is the complete arc set):
21->29
28->19
22->13
22->27
21->17
8->14
22->2
4->28
17->20
8->13
25->14
8->25
8->1
23->25
13->27
28->13
28->5
24->29
13->2
29->19
15->26
28->29
16->25
12->1
29->5
3->15
22->25
12->13
25->0
24->21
21->7
3->17
16->15
1->11
3->9
28->17
16->11
10->17
1->18
21->20
6->15
3->26
3->1
15->9
23->29
4->17
16->1
17->7
24->15
12->8
8->0
22->29
4->13
10->1
16->18
21->15
6->25
23->22
6->16
10->3

Give your final answer inside <answer></answer> tags as one comma-separated
list of all internal vertex IDs in elimination order.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

The planted response is `<answer>8, 3, 28, 17, 1, 13, 21, 16, 22, 25, 15, 29</answer>`. Its exact replay costs 63, equal to the budget, and `verify` returns `(True, "ok")`. Dropping the final `29` returns `(False, "sequence length must be 12")`. A person can solve this demo on paper: the six labels modulo 3 split into two parallel matching classes, and the two gadget roles are distinguished by their directed neighborhoods. It is intentionally an illustration, not a hard rung.

## Difficulty presets

| preset | `n` | degree | label decoys | vertices | internal / answer atoms | arcs | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 2 | 0 | 30 | 12 | 60 | hand-scale illustration; skipped by hardening |
| easy | 11 | 5 | 0 | 275 | 110 | 1,210 | **ships; bare and hinted oracle pools held** |
| medium | 17 | 5 | 1 | 425 | 170 | 1,870 | not needed after easy held |
| hard | 23 | 5 | 2 | 575 | 230 | 2,530 | not needed after easy held |

No preset was rejected by a local attack. `escalate` first adds fixed-answer-length label decoys; only after that does it increase `n`, returning `"cap_bound"` before 256 answer atoms would be exceeded.

## Mandatory gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 planted instances verified across all presets; every answer JSON-round-tripped |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions all rejected with five distinct reasons |
| G3 | pass | fenced, prose-surrounded response recovered exactly; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 uniform total permutations; declared space is `110!` (592-bit cardinality) |
| G5 | pass | shipping sampled fraction 0/200,000; strongest failing panel used 2,072 trials in 0.163 s |
| G6 | pass | static Markowitz 0/8, dynamic greedy 0/8, random restart 0/8, diagonal ansatz 0/8; reference solved 8/8 in 63,712 operations / 0.032 s |
| G7 | pass | doubling test grew 20 internal vertices to 44 and strictly enlarged the search space; both witnesses verified |
| G8 | pass | 40/40 ID/order/affine/composed invariance checks, 40/40 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle 0/3; 511 characters, 110 atoms, about 128 tokens, 187 intended operations |

Times are machine-dependent and are preserved exactly in `selftest_report.json`.

## Bare oracle hardening loop

| preset | model | seed | solved | exact verifier reason |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 1473423709 | no | theorem-derived cover exceeded budget slack |
| easy | Grok 4.6 | 1120555698 | no | theorem-derived cover exceeded budget slack |
| easy | GPT-5.6-Terra | 140230906 | no | theorem-derived cover exceeded budget slack |

All replies parsed as concrete sequences. Thus none of the failures is a parser artifact. The script-owned verdict is `hardened`, with zero escalations and `easy` as the held/shipping preset.

## G9 three-arm diagnostic

| arm | solved / attempts | verdict or interpretation |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; G9(b) passes |
| placebo hint | 0 / 3 | hardened |

`hinted - placebo = 0.0`. The one-sentence invariant bought the sampled oracle pool nothing. This may mean the models did not operationalize the affine-class observation, or that reliably translating it into the long exact elimination order remained the limiting step; the diagnostic alone cannot separate those explanations. The hint names only the invariant and does not state the matching choice or the four-block algorithm.

## How to use it

From this directory:

```python
import math
import random
import gen_2506_17521 as gen

inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer("<answer>" + ",".join(map(str, inst["answer"])) + "</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.search_space(inst) == math.factorial(110)
```

To emit 20 fresh, diversity-checked shipping instances from the repository root:

```bash
bash scripts/emit.sh 2506.17521 20 easy
```

## Caveats

- The coordinate annotations are not part of the paper's bare decision-problem input; they are presentation clues added for the Track-B compression. They do not participate in verification. The DAG, elimination operation, Markowitz cost, and certificate are nevertheless exactly the paper's objects, and the construction itself is the paper's central Section 3 reduction.
- The generator samples a very special polynomial-time-solvable subdistribution. It provides no average-case hardness evidence and must never be relabelled Track A. Removing the coordinate clue leaves the paper's generic exponential method, while exposing the affine relation to code makes the reference solve inexpensive.
- The `0/200,000` guess rate is only for a uniform random total permutation after enforcing all obvious shape constraints. It does not estimate a solver using reduction recognition, affine labels, local search, or learned priors.
- The adversary panel did not run a general ILP/SAT encoding, an optimized implementation of the paper's subset DP, beam search over partial orders, or commercial Jacobian-accumulation software. It did run the construction-aware polynomial reference algorithm, which succeeded as expected and is reported separately.
- `canonical_key` uses strong distance-profile and common-neighbor invariants of the recovered base graph, not complete graph-isomorphism canonization. Non-isomorphic graphs can theoretically collide. Arbitrary vertex relabellings, input reorderings, independent coordinate affine maps, compositions, carried answers, and 20 unrelated seeds were tested.
- There can be many correct orders because every affine matching class is exchangeable and within-block orders can vary. `verify` checks any candidate by exact replay and does not compare it to the planted answer.
