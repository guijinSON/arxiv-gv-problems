# Verified generator for arXiv:1704.08868

| Profile field | Value |
|---|---|
| Track | A — structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple |
| Intended intuition | reduction recognition: radius guards force one local choice per color and conflict gadgets forbid source edges |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 4, Lemmas 15–16 and Theorem 17 |

## What the family is

This module turns the weighted reduction in Katsikarelis, Lampis, and Paschos,
[“Structural Parameters, Tight Bounds, and Approximation for $(k,r)$-Center”](https://arxiv.org/abs/1704.08868),
into an inverse generator. It first chooses one hidden vertex in each of `k`
color classes. For every color pair it constructs a regular bipartite safe-pair
relation containing the planted pair, and regards every other pair as an edge
of a Multicolored Independent Set instance. It then exposes exactly the
weighted guard, hub, and conflict graph of Section 4 in a compact bit-matrix
encoding. The certificate was chosen before this public graph was built.

The solver returns `k` choice-vertex IDs, one per color. Verification decodes
their local indices and performs one exact bit lookup for each color pair. A 1
means the pair is nonadjacent in the source graph. This is also the exact
distance test in the reduced graph: a conflict vertex for the two selected
endpoints is at `r+1`, while changing either endpoint brings it within `r`.
The demo instances are additionally expanded to the full weighted graph and
checked independently with multi-source Dijkstra.

## Why Track A is the honest claim

Theorem 17 proves that weighted $(k,r)$-Center is W[1]-hard parameterized by
`vc+k` and, under ETH, has no `N^o(vc+k)` algorithm. Its construction has
`r=4s`, preserves `k`, and has a vertex cover of at most `4k`. This generator
uses that weighted, growing-`k`, unbounded-radius regime. It deliberately does
not use the easy regimes identified in the paper: Theorem 19 gives an
`O*(5^vc)` algorithm for the unweighted vertex-cover case, Theorem 21 gives an
`O*(2^O(td^2))` algorithm for unweighted bounded tree-depth, Theorem 14 gives
the fixed-radius clique-width DP, and Sections 5–6 give FPT approximation
schemes when radius relaxation is allowed.

Theorem 17 is a worst-case statement, not a proof about this distribution.
Distributional evidence comes from construction and measurement: every
safe-pair block is regular on both sides, plants and decoys have the same
degree, and the safe density is placed near the first-moment threshold for an
accidental transversal. At the shipping preset, a capped exact CSP solver with
MRV and forward checking failed after 1,000,008 visited nodes in 2.379 seconds.
Across eight seeds it failed after 8,000,053 total nodes and 18.108 seconds.
Degree, one-pass greedy, 256 randomized greedy restarts, min-conflicts repair,
and centered spectral rounding also solved 0/8 instances each.

## Worked demo

This is the complete `render(make_instance(seed=7, n=3, part_size=4,
safe_degree=1))` output (with no hint):

```text
Weighted (k,r)-Center with guard and conflict gadgets

For an undirected graph with positive integer edge weights, the distance from
v to u is the minimum total edge weight of any path from v to u. A center set
of budget k and radius r is a set of at most k graph vertices such that every
vertex not in the set is at distance at most r from at least one center.

This instance has k=3, r=16, and s=4 choices per color. All color and
local-choice indices are 0-based. The graph below is specified exactly; edges
not created by these rules do not exist.

Choice vertices are P(i,x), for 0<=i<3 and 0<=x<4. P(i,x) has integer ID
i*s+x. For each color i there are hubs A(i), B(i) and guards G(i,0), G(i,1).
For every x, add these undirected weighted edges:

  P(i,x)--G(i,0) weight 16; P(i,x)--G(i,1) weight 16
  P(i,x)--A(i) weight s+x+1; P(i,x)--B(i) weight 2*s-x

For each color pair i<j, one line below contains 4 fixed-width hexadecimal
bitmasks, in increasing x for color i. Bit y (least-significant bit is y=0) is
1 when choices P(i,x),P(j,y) are SAFE (nonadjacent in the source graph), and 0
when they conflict. Padding zeroes beyond bit 3 are ignored.

0,1: 8 4 2 1
0,2: 1 4 8 2
1,2: 2 8 1 4

For every 0 bit at pair (i,j), row x, bit y, create a conflict vertex U(i,x,j,y)
and exactly four incident edges:

  U--A(i) weight 3*s-x;     U--B(i) weight 2*s+x+1
  U--A(j) weight 3*s-y;     U--B(j) weight 2*s+y+1

There are 60 graph vertices, including 36 conflict vertices. The two guards
for each color force every radius-16 center set of size at most 3 to use
exactly one P(i,x) from every color. A conflict vertex U(i,x,j,y) is at
distance 17 from both P(i,x) and P(j,y), while a different choice in either
of those colors reaches it within radius. Thus the selected pair for every
color pair must be a displayed 1 bit.

Output the 3 selected choice-vertex IDs as a JSON array, one ID from each
color, in increasing color order. IDs must be distinct integers in 0,...,11;
the entry for color i must lie in i*s,...,(i+1)*s-1.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>[0, 4, 8]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[2, 5, 11]</answer>`.
`verify(inst, [2, 5, 11])` returns `(True, "ok")`. Replacing its first
entry gives `verify(inst, [0, 5, 11]) == (False, "conflict vertex
U(0,0,1,1) is at radius+1 from both selected choices")`. This 64-candidate
demo is genuinely hand-solvable by following the three displayed 1-bits.

## Difficulty presets

| Preset | `k` | choices/color | safe degree | radius | represented graph vertices | candidate space |
|---|---:|---:|---:|---:|---:|---:|
| demo | 3 | 4 | 1 | 16 | 60 | 64 |
| easy **(ships)** | 22 | 48 | 33 | 192 | 167,464 | `48^22` |
| medium | 24 | 56 | 39 | 224 | 264,192 | `56^24` |
| hard | 24 | 64 | 44 | 256 | 354,912 | `64^24` |

No named preset was rejected. The oracle held the first tested rung (`easy`),
so the hardening loop did not escalate. `escalate()` grows choices per color
while keeping the 22-element certificate length fixed.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; 3/3 independently expanded demo graphs |
| G2 | pass | empty, dropped, out-of-range, duplicate, and conflicting replacement all rejected with 5 distinct reasons |
| G3 | pass | tagged fenced JSON round-trips; malformed and absent tags return `None` |
| G4 | pass | 0 hits / 200,000 structure-aware guesses; candidate space `48^22` |
| G5 | pass | shipping sample density 0/200,000; exact demo count 1/64; capped exact baseline 1,000,008 nodes, 2.379 s |
| G6 | pass | all 6 attacks 0/8; exact baseline aggregate 8,000,053 nodes, 18.108 s |
| G7 | pass | named represented sizes strictly increase; doubled `k=44` instance has 365,552 vertices and verifies |
| G8 | pass | 60/60 relabelling invariance checks, 60/60 carried witnesses verify, 20/20 unrelated keys distinct |
| G9 | pass | 89 chars, about 23 tokens, 22 atoms; 253 exact decode/bit-check operations |

## Oracle loop

| Preset | Seed | Model | Solved | Grader result |
|---|---:|---|---|---|
| easy | 839002227 | `openai/gpt-5.6-terra` | no | first proposed pair conflict at `U(0,0,1,0)` |
| easy | 672192354 | `google/gemini-3.8-flash` | no | proposed pair conflict at `U(0,31,4,43)` |
| easy | 864963268 | `google/gemini-3.8-flash` | no | first proposed pair conflict at `U(0,0,4,0)` |

The script-owned verdict is `hardened` at `easy`, with no escalation.

## G9 diagnostic arms

| Arm | Solved/attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

The hinted-minus-placebo rate is `0.0`: naming what the guards enforce bought
the sampled oracle pool nothing. This says the remaining difficulty is the
compatible-transversal search, not merely recognition of the reduction. The
reported 253 operations are the exact certificate-decoding and pair-checking
work once a witness is in hand; Track A does not claim a compact solving
shortcut.

## How to use it

```python
from gen_1704_08868 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
prompt = render(inst)
candidate = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 1704.08868 20 easy
```

The module uses only the standard library. It probes for `gvlib` as required by
the repository convention, but this finite graph family does not need it and
degrades cleanly when it is absent.

## Caveats

The ETH/W[1] theorem does not prove average-case hardness for planted regular
instances. The 0/200,000 guess result is an observed rate under the explicit
prior “one uniform in-range choice per color”; it is not an exact solution
count or a statistical proof that the true density is below `1e-6`. The
canonical key is a strong cheap invariant (common-neighbor spectra plus color
incidence refinement), not a complete graph-isomorphism canonical form.

The panel did not run a production SAT/SMT/ILP package, belief propagation, or
a full SDP relaxation. Its exact DPLL probe was stopped at one million nodes
per seed, so completeness is conditional on removing that cap. The graph is
rendered by exact gadget rules and hexadecimal conflict matrices rather than
as hundreds of thousands of explicit edge lines. Lowering `k`, moving far
from the first-moment density, making the safe blocks irregular, or exposing
the per-block permutations could make the family easy.
