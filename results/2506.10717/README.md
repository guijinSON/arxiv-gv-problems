# Canonical 1-planar region layouts (arXiv:2506.10717)

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (a partition into triples) |
| Intuition | invariant — repeated residues reveal the three paths in each region |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 3.2, Theorem 9 |

This generator instantiates the central Unary Bin Packing reduction in Gima,
Kobayashi, and Okada, [*Structural Parameterizations of k-Planarity*](https://arxiv.org/abs/2506.10717).
The solver receives the paper's graph as an exact succinct specification: a cycle,
two hubs, item paths, and the two spoke bundles. It must return a region assignment
for the item paths. Each region load is checked with integer arithmetic. The assignment
then deterministically expands to the proof's canonical topological drawing and its
crossing ledger, in which every edge has zero or one crossings.

This is not arbitrary 1-planarity recognition and is not claimed as Track A. Theorem 9
is W[1]-hard when parameterized by distance to path forest, and its construction has
distance at most `b+2`; here `b` grows. But this generated distribution deliberately
has a shortcut. Pair-sum indexing finds every capacity triple in `O(m^2)` time and the
resulting exact cover is forced. At the shipping preset it solved 8/8, using 14,028
pair probes, 28,224 counted operations, and median 0.00094 s. The compact route notices
a hidden common modulus, reduces 168 values, and matches each repeated residue to its
double-complement: 280 exact arithmetic operations. The gap between those routes—not
asymptotic intractability—is the Track B claim.

The positive results matter too. Theorem 14 gives FPT for feedback-edge-set number;
Theorem 16 gives FPT for `treedepth+k`; Corollary 18 covers induced-path-free classes
parameterized by `t+k`; Theorem 23 and Corollary 25 give polynomial kernels for vertex
cover and neighborhood diversity together with `k`. This generator does not claim
hardness inside any of those bounded-parameter regimes. The final fixed-length
hardening step raises the modulus from 14 to 31 bits while leaving the 168-atom answer
unchanged.

## Worked demo

The full rendered `demo` instance for seed 11 is:

```text
CANONICAL 1-PLANAR REGION LAYOUT

A topological drawing maps vertices to distinct points in the plane and edges
to non-self-intersecting curves between their endpoints. An edge crossing is an
intersection of two edges away from their endpoints. Edges may not pass through
other vertices, and no three edges may meet at one crossing. A drawing is
1-planar when every edge has at most one crossing.

The following finite simple graph G is specified by named vertex and edge families;
the compressed notation defines every vertex and edge, even though G is very large.
Let b=3 and B=320288. There are hubs u1,u2 and cycle markers
v_0,...,v_(b-1). For every r, a cycle path of exactly B edges joins v_r
to v_((r+1) mod b); these internally disjoint paths form one cycle C.
For item i of size x_i, add a path P_i on exactly x_i vertices and join
each vertex of P_i to both u1 and u2.
Before spokes this graph has m=3843447 edges. For every marker v_r,
add 3843448 internally vertex-disjoint u1-v_r paths of length 2,
and 15373792 internally vertex-disjoint u2-v_r paths of length 2.
All internal vertices named by different paths are distinct, and there are no other edges.
Thus G has 59573450 vertices and 119146887 edges.

There are 9 items, numbered 0 through 8.
Item-path sizes x_i (item_id:size):
  0:128769  1:92777  2:95466  3:98742  4:111544  5:99329  6:107209  7:125493
  8:101535

Your certificate is a region layout for the canonical drawing used in Theorem 9.
Partition all item IDs into exactly b=3 unordered triples, one per
spoke-bounded region, so the three sizes in every triple sum exactly to B=320288.
The decoder sorts IDs inside each triple, concatenates their path vertices, and
routes the resulting B u1-to-u2 two-edge strands across the B distinct edges of
that region's cycle segment in order. Item-path edges and all spokes are routed
locally without crossings. Therefore the certificate explicitly determines a
crossing ledger: each cycle-segment edge and each routed strand is crossed once,
and every other edge zero times. The checker reconstructs and checks this ledger.

Every item ID must occur exactly once. IDs are zero-based; repetitions are forbidden.
The order of triples and the order of IDs within a triple do not affect validity.

Give your final answer inside <answer></answer> tags, as a JSON array of
exactly 3 arrays, each containing exactly three integer item IDs.
Syntax example for a hypothetical six-item instance:
<answer>[[0,2,4],[1,3,5]]</answer>
Output nothing else inside the tags.
```

The demo is hand-solvable: there are only 280 structure-aware partitions. Its answer
is `[[0,1,3],[2,5,7],[4,6,8]]`; `verify` returns `(True, "ok")`. Swapping item 0
with item 2 gives `[[2,1,3],[0,5,7],[4,6,8]]` and returns
`(False, "region_load_not_B")`.

## Difficulty and gates

| preset | regions `n` | item paths | modulus bits | log2 candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 9 | 14 | 8.13 | hand example |
| easy | 38 | 114 | 14 | 372.45 | solved by 3/3 oracles |
| medium | 56 | 168 | 14 | 611.15 | solved by 2/3 oracles |
| **hard** | **56** | **168** | **31** | **611.15** | **ships; 0/3 solved** |

| gate | measured result |
|---|---|
| G1 | 20/20 planted/determinism/JSON checks passed |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged prose-and-fence round trip passed; garbage returned `None` |
| G4 | 0/200,000 valid structure-aware random partitions |
| G5 | shipping density 0/200,000; demo has exactly 1/280 valid layouts; baseline 28,224 ops, 0.00094 s median |
| G6 | five attacks × 8 seeds, 0 successes; disclosed reference solved 8/8 |
| G7 | doubled `n=112` built and verified; ladder sizes/heights increase |
| G8 | 100 relabelling/carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 675 chars, 169 estimated tokens, 168 atoms, 280 intended arithmetic operations; hinted verdict `hardened` |

## Oracle loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | Terra | 1789006871 | solved | verified |
| easy | Gemini | 546349963 | solved | verified |
| easy | Grok | 947407287 | solved | verified |
| medium | Grok | 355745161 | solved | verified |
| medium | Gemini | 1529665768 | failed | parsed layout had a wrong region load |
| medium | Claude | 2048503717 | solved | verified |
| hard | Claude | 211002095 | failed | exhausted the 32k response budget without a witness |
| hard | Gemini | 880600113 | failed | parsed layout had a wrong region load |
| hard | Terra | 744657127 | failed | parsed layout had a wrong region load |

## G9 arms

| arm | solved / attempts at shipping | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping run held |
| structural hint | 0 / 3 | G9(b) held; all three parsed answers failed exact loads |
| placebo | 1 / 3 | one verified solution after a timed-out call was redrawn |

`hinted - placebo = -1/3`. With only three calls per arm, this does not show that the
hint hurts; it does show no evidence that naming the invariant dissolves the problem.
The answer-size and intended-route figures are 675 characters, 168 atoms, and 280 exact
arithmetic operations. The placebo transcript also retains `harden.py`'s automatic
higher-modulus round after the shipping success; the table and G9 statistic use only
round 0's three completed, non-error attempts. That later scratch round ended in API-key
errors and is not used as evidence for any claim.

## Use

```python
import gen_2506_10717 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + g._format_answer(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 2506.10717 20
```

## Caveats

The witness covers the paper's canonical Theorem-9 drawing template, not every possible
topological drawing of the graph. The graph is represented succinctly because explicitly
listing its enormous spoke bundles would be a transcription benchmark; this changes the
input representation from the ordinary explicit-graph model. Knowing the hidden modulus
makes reconstruction essentially linear, and the quadratic pair-sum algorithm already
makes the generated distribution computationally easy—hence Track B.

The 0/200,000 guess result applies only to the uniform prior over unlabeled partitions
into triples. It says nothing about informed arithmetic strategies. The tested failures
were display order, central-magnitude outliers, sorted adjacency, balanced rank zipping,
and 256 structure-aware random restarts. The successful pair-sum reference dominates
DLX/CP on this specially forced distribution, so separate commercial ILP, general
1-planarity, spectral, and SDP implementations were not run. Canonicalization proves
invariance under item relabelling and region order, but it is not a general graph-
isomorphism solver. Finally, one bare hard failure was response-budget exhaustion; the
other two bare failures and all three hinted failures were parsed, exact load failures.
