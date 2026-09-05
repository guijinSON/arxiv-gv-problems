# Weight-six total Roman strategies for a direct graph product

| profile field | value |
|---|---|
| paper | [Dominating the direct product of two graphs through total Roman strategies](https://arxiv.org/abs/2005.13608) |
| `TRACK` | B |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple (three product vertices, six integers) |
| intended intuition | invariant: an anchored complement-neighbourhood overlap identifies a central triangle |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The solver receives one regular graph `G` in an exact compact representation and
must give three vertices of the direct square `G x G`.  Those vertices receive
label 2 and every other product vertex receives label 0.  The checker reconstructs
factor adjacency from the displayed hexadecimal non-neighbour masks, checks that
the three product vertices form a triangle, and directly verifies that every
product vertex sees at least one submitted label-2 vertex.  It never reads the
planted answer.  Thus the submitted object is a locally checkable weight-six total
Roman dominating function; the question does not ask the solver to certify
optimality.

The generator is inverse.  In the bipartite complement of `G`, it chooses three
left rows whose equal-size neighbour sets partition the right side.  These become
a central triangle in `G`.  It adds an anchored near-row, mixes every other row by
degree-preserving two-switches, and independently relabels both sides.  The planted
triangle is carried through those transformations.  All factor vertices have the
same degree and all complement rows have the same weight.

## Why Track B, not Track A

Section 1 supplies the exact definitions of total Roman domination and the direct
product.  Section 3, Theorem 10(iii) proves that central triangles in both factors
give a weight-six total Roman function, supported with label 2 on three paired
vertices.  Its converse proof also turns a weight-six all-2 support into central
factor triangles.  That is both the construction theorem and an efficient
mechanical route: enumerate all `N choose 3` factor triples and test each one in
`O(N)` scalar adjacency checks, or use bit masks for an `O(N^3)` word-operation
implementation.  Track A would therefore be false.

At the shipping preset (`N=144` factor vertices), the successful bit-parallel
reference scan took 4,651,332 counted word operations over eight instances,
at most 1,273,144 on one instance, and 0.319 seconds total in the recorded local
run.  The compact route uses the anchor: its unique maximum-overlap left row has
exactly two disjoint left partners.  Two scans of 71 masks cost 284 exact
AND/popcount word operations.  Corollary 11 and Section 4 identify still easier
closed-form families (complete, complete-bipartite, wheel/fan, cycle and regular
efficient-open-domination products); this generator does not claim hardness from
those regimes.

## Worked demo (`seed=7`)

This is the complete rendered demo instance:

```text
Find a weight-6 total Roman strategy on a direct product.

Define a simple factor graph G on 42 vertices numbered 0 through 41.
Its left side is L_i=i for 0<=i<21; its right side is R_j=21+j for 0<=j<21.
There are no loops. Every two distinct left vertices are adjacent, and
every two distinct right vertices are adjacent. Across the sides, L_i
and R_j are adjacent exactly when bit j of row M_i below is 0.
Hexadecimal bit 0 is the least-significant (rightmost) bit; leading zeroes
are included only for readability. Thus a 1 records a cross-side NON-edge.
Every M_i has exactly 7 one-bits.

One annotated left vertex is the anchor: L_19.
The annotation is part of the instance but does not change adjacency.
The non-neighbour rows are presented in arbitrary order:
M_9 = 0x1089a8
M_1 = 0x147018
M_0 = 0x048744
M_6 = 0x032846
M_18 = 0x08223c
M_8 = 0x114581
M_14 = 0x0a700a
M_11 = 0x0e00d1
M_17 = 0x066904
M_15 = 0x0055b0
M_10 = 0x0b4111
M_2 = 0x11d600
M_5 = 0x168a02
M_20 = 0x143086
M_3 = 0x090174
M_12 = 0x008e68
M_13 = 0x0b0289
M_7 = 0x081a92
M_16 = 0x142047
M_19 = 0x008c69
M_4 = 0x019423

The direct product P=G x G has vertices (u,v), with 0<=u,v<42. Distinct product vertices (u,v) and (u',v') are
adjacent in P exactly when uu' is an edge of G AND vv' is an edge of G.

A total Roman dominating function assigns each product vertex a label in
{0,1,2}. Every label-0 vertex must have a label-2 neighbour, and the
subgraph induced by all positive-label vertices must have minimum degree
at least 1. Its weight is the sum of all labels. This instance is promised
to admit a total Roman dominating function of weight exactly 6.

Submit exactly three distinct product vertices. They will receive label 2;
every other product vertex receives label 0. The three submitted vertices
must induce a triangle in P and be in strict lexicographic order, with no
repetitions. Coordinates and
all indexing are zero-based; interval bounds above are inclusive at 0 and
exclusive at the upper endpoint.

Give your final answer inside <answer></answer> tags as one JSON list of
three pairs [[u1,v1],[u2,v2],[u3,v3]].
Example: <answer>[[0,1],[2,3],[4,5]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[10,10],[12,12],[20,20]]</answer>` and `verify` returns
`(True, "ok")`.  Swapping its first two entries returns
`(False, "product vertices must be in strict lexicographic order")`.  A person
can solve this smallest setting on paper by converting 21 short masks to sets,
comparing them with the anchor, and checking the two disjoint partners, although
the hexadecimal bookkeeping is intentionally the laborious part of the demo.

## Difficulty presets

| preset | side size `n` | factor order | product order | guide gap | mix rounds | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 21 | 42 | 1,764 | 1 | 16 | hand-scale illustration |
| easy | 24 | 48 | 2,304 | 1 | 16 | rejected: bare oracle solved 3/3 |
| medium | 48 | 96 | 9,216 | 2 | 24 | rejected: bare oracle solved 2/3 |
| hard | 72 | 144 | 20,736 | 4 | 32 | configured shipping preset; local gates pass, oracle run quota-blocked |

`SHIPPING_DIFFICULTY` is currently `hard`.  The answer length stays fixed while
the factor, direct-product haystack, mixing, and guide gap grow.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verify; JSON round-trip holds |
| G2 | empty, dropped, duplicate, out-of-range and reordered corruptions all rejected with distinct reasons |
| G3 | realistic prose/fence/tag response round-trips |
| G4 | 0/200,000 structure-aware legal product triangles succeeded |
| G5 | exact shipping density `56,454 / 476,169,905,664 = 1.1856e-7`; reference total 0.319 s and 4,651,332 word ops over 8 |
| G6 | five attacks, each 0/8; reference central-triangle scan 8/8 as Track B requires |
| G7 | factor order 288 builds and verifies with the same six answer atoms |
| G8 | 40 relabelling/order invariance checks, 20 carried-witness checks, 20/20 unrelated keys distinct |
| G9(c) | 25 characters, conservative 25-token bound, 6 atoms, 284 intended-route word operations |

## Oracle loop and G9 diagnostics

The required bare `scripts/harden.py` run scored both lower rungs: all three
`easy` calls solved, and two of three `medium` calls solved.  When it reached
`hard`, OpenRouter returned HTTP 403 `Key limit exceeded (total limit)` on all
four permitted tries before a single hard response could be scored.  The harness
correctly treated these as infrastructure errors rather than mathematical
failures.  Consequently there is no bare hardness verdict yet, and the partial
transcript must not be cited as evidence that `hard` held.

| bare preset | model | seed | result |
|---|---|---:|---|
| easy | Gemini 3.8 Flash | 1298812119 | solved |
| easy | GPT-5.6 Terra | 781995784 | solved |
| easy | GPT-5.6 Terra | 1044808128 | solved |
| medium | Gemini 3.8 Flash | 1055739303 | solved |
| medium | GPT-5.6 Terra | 1647397037 | failed: invalid certificate |
| medium | GPT-5.6 Terra | 356679699 | solved |
| hard | pool retries | four distinct seeds | infrastructure errors; not scored |

| arm | solved / scored attempts | status |
|---|---:|---|
| bare | 0 / 0 | hard-preset arm blocked by OpenRouter key limit |
| structural hint | 1 / 3 | one valid certificate; diagnostic verdict `too_easy` |
| placebo hint | 1 / 3 | one valid certificate |

`hinted - placebo` is `0.0`.  On this small sample the structural sentence bought
no measurable improvement over a register-matched placebo, so the claimed
invariant has not yet received positive causal support from G9.  Both completed
arms were produced by isolated runs of the official harness; the copies include
only script-produced records.  Re-run the bare hard level after restoring
OpenRouter capacity.

## Use

```python
import gen_2005_13608 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
instance = g.make_instance(seed=123, **params)
answer = g.parse_answer("<answer>" + __import__("json").dumps(instance["answer"]) + "</answer>")
assert g.verify(instance, answer) == (True, "ok")
```

From the repository root, emit only after the oracle evidence is complete:

```bash
bash scripts/emit.sh 2005.13608 20
```

## Caveats

This is Track B: ordinary software solves it quickly, and the measured 0.319
seconds must not be presented as computational hardness.  The benchmark tests
whether a no-tool solver notices the anchored overlap invariant rather than
enumerating hundreds of thousands of triples.  The exact guess density applies
to the declared prior—uniform product-graph triangles—not to a solver using the
anchor.  The panel does not include ILP/SAT encodings or a learned set-packing
heuristic; the relevant domain-standard exact scan is included and succeeds.
The canonical key uses anchor-aware colour refinement of row-intersection sizes,
not complete bipartite-graph isomorphism, so rare nonisomorphic collisions are
possible.  The shortcut costs `4n-4` word operations, so increasing `n` beyond
the shipping rung would exceed the 300-operation no-tool cap even though the
answer remains short; escalation therefore weakens the guide and increases
mixing at fixed `n` before it exhausts the admissible axes.  Most importantly,
the four-vendor and G9 evidence is presently absent
because the supplied OpenRouter key hit its total limit; this directory is not
submission-ready until those script-owned runs succeed.
