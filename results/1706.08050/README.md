# Verified generator for arXiv:1706.08050

> **Blocked, not rejected or shipped.** The final module passes local gates
> G1–G9(c). In the required bare hardening run, both configured vendors solved
> all three `easy` instances and the first two `medium` instances; the shared
> OpenRouter key then hit HTTP 403 `Key limit exceeded` before the third medium
> attempt or any `hard` attempt. The G9 hint arms likewise have no scored calls.
> API errors are not model failures, so the shipping hardness claim remains
> unmeasured.

| profile field | value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: a source-vertex set |
| Intended intuition | constraint propagation |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 2, Theorem 4 at `p=3` |

The solver is still handed a graph and returns the paper's own connected
odd-cycle-transversal object. The search is carried by a visible parity-gadget
surrogate, so this is representational coverage (`licensed_reduction`), not a
claim that arbitrary instances from the paper have this extra structure.

## Problem and provenance

This family comes from Chiarelli, Hartinger, Johnson, Milanič, and Paulusma,
[“Minimum Connected Transversals in Graphs”](https://arxiv.org/abs/1706.08050).
Section 1 defines an odd-cycle transversal as a vertex set whose deletion leaves
a bipartite graph, and calls it connected when the chosen vertices induce a
connected subgraph. Section 2, Theorem 4 retains every edge of a Connected
Vertex Cover instance and adds an even parallel path. At `p=3` the path has two
edges, so every source edge becomes the base of a triangle.

The source graph here contains variable edges, clause triangles, their incidence
edges, and a universal connector. It encodes a sparse nonsingular parity system.
The generator samples the assignment first, builds a nonsingular matrix from a
four-variable `J-I` core plus triangular extensions, constructs the corresponding
connected vertex cover, and then applies Theorem 4. No generated instance is
solved to learn its answer. Verification checks the exact gadget quotas and the
only potentially uncovered incidence edge in each clause. Those checks prove
that every source edge is covered; the connector proves connectivity; after
triangle expansion, the unselected graph is a forest of stars and is bipartite.

## Why Track B

This distribution is **not** claimed hard in the Track-A sense. An efficient
algorithm exists and is exposed honestly: decode each group of four 3-clauses as
one GF(2) parity equation and apply Gaussian elimination. At shipping `n=24`,
the measured median is 2,678 scalar XORs and 0.000298 s (`O(n^3)`). A plain DPLL
implementation with unit propagation also solves 8/8, with medians of 6 search
nodes, 2,225 literal checks, and 0.000508 s.

The compact no-tool route recognizes that the equation-incidence hypergraph can
be peeled to a four-variable all-but-one core. The core has the identity
`x_i = xor(all four right-hand sides) xor b_i`; reversing the peel determines
the remaining variables. The measured compact route uses 119 exact XORs. That
is within the no-tool cap, but finding and carrying it out across 96 shuffled
clause triangles plus writing 217 labels is materially different from invoking
Gaussian elimination or a SAT solver.

The paper's easy regimes were also checked. The Introduction notes FPT results
for Connected Feedback Vertex Set parameterized by solution size, so this
family lets the requested set grow. Section 3, Theorems 10, 12, and 14 give
polynomial algorithms on fixed-`s` `sP2`-free graphs. Here the subgraph induced
by all variable vertices is `nP2`, so no fixed `s` contains the growing family.

## Worked demo

Below is `render(make_instance(n=4, seed=7))` in full.

```text
Connected odd-cycle transversal in a triangle-expanded graph

All graphs here are finite, simple, and undirected. A vertex set T is an
odd-cycle transversal if deleting T leaves a bipartite graph (equivalently, no
odd cycle). It is connected if the subgraph induced by T is connected.

The source graph H has the designated connector vertex C=32,
4 variable-pair gadgets, and 16 clause-triangle gadgets.
Each integer names one source vertex. Variable labels recur as attachment
targets; all variable and clause vertices themselves are pairwise distinct.

Variable pairs (the parenthetical order only defines the 0/1 convention):
  x0: (12, 29)  [first means 0; second means 1]
  x1: (10, 30)  [first means 0; second means 1]
  x2: (1, 49)  [first means 0; second means 1]
  x3: (24, 22)  [first means 0; second means 1]

Clause triangles are grouped into four-triangle blocks. A record a->b means
that a is a vertex of that triangle and {a,b} is an attachment edge:
  block 0:
    triangle 0: 36->1, 3->24, 52->30
    triangle 1: 35->1, 53->10, 15->22
    triangle 2: 4->49, 26->24, 27->10
    triangle 3: 5->30, 2->22, 13->49
  block 1:
    triangle 0: 8->24, 54->29, 42->1
    triangle 1: 38->49, 25->29, 44->22
    triangle 2: 45->49, 37->24, 41->12
    triangle 3: 40->1, 14->22, 7->12
  block 2:
    triangle 0: 19->30, 56->12, 43->49
    triangle 1: 16->29, 34->10, 0->49
    triangle 2: 39->1, 33->10, 23->12
    triangle 3: 11->1, 6->29, 20->30
  block 3:
    triangle 0: 51->10, 46->24, 48->12
    triangle 1: 21->30, 28->12, 9->22
    triangle 2: 31->30, 47->29, 17->24
    triangle 3: 50->10, 55->29, 18->22

These tables define every source edge of H, as follows and with no others:
1. the edge joining the two vertices in each variable pair;
2. all three edges inside each listed clause triangle;
3. every listed attachment edge a->b; and
4. an edge from C to every other source vertex.

Construct G from H by retaining every source edge {u,v} and, for each such
edge, adding one fresh vertex q_{u,v} and the two edges {u,q_{u,v}} and
{q_{u,v},v}. All q vertices are distinct and there are no other vertices
or edges. Thus every source edge is the base of exactly one triangle in G.

Find exactly 37 SOURCE vertices that form a connected odd-cycle
transversal of G. The set must contain C, exactly one vertex from each variable
pair, and exactly two vertices from each clause triangle. Do not output any q
vertex. Output the 37 distinct base-10 integer labels in strictly
increasing order; order otherwise has no meaning, and repetitions are forbidden.

Give your final answer inside <answer></answer> tags, as comma-separated base-10
integers. Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

The planted answer is:

```text
<answer>0, 1, 2, 3, 4, 6, 7, 8, 9, 13, 14, 15, 17, 18, 20, 23, 24, 27, 28, 29, 30, 32, 33, 34, 38, 41, 42, 43, 44, 45, 47, 48, 50, 51, 52, 53, 56</answer>
```

`verify` returns `(True, "ok")`. Dropping the last label returns
`(False, "wrong_length_expected_37")`. A person can solve the demo on paper by
decoding four parity equations, using the four-variable identity, and filling
the clause triangles; the 37-label output is tedious but still hand-scale.

## Presets and gate results

| preset | `n` | source vertices | expanded vertices | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 57 | 213 | 37 | hand-solvable illustration |
| easy | 8 | 113 | 425 | 73 | solved by all 3 scored oracle attempts |
| medium | 16 | 225 | 849 | 145 | first 2 scored attempts solved; quota then exhausted |
| hard | 24 | 337 | 1,273 | 217 | provisional shipping preset; not reached by oracle |

| gate | measured result |
|---|---|
| G1 | 20/20 planted witnesses verified and JSON-round-tripped |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence response round-tripped; garbage rejected |
| G4 | 0/200,000 structure-aware guesses from `2^24 3^96` candidates |
| G5 | exactly `3^24` valid lists, density `2.65e-42`; Gaussian baseline 3,466 XORs on the fixed reporting seed |
| G6 | degree, greedy, 256-restart, and one-pass parity-repair attacks each 0/8; Gaussian, DPLL, and compact references each 8/8 |
| G7 | `n=48` builds and verifies; search entropy grows from 176 to 352 bits (output then exceeds the shipping cap) |
| G8 | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 1,002 chars (1,085 worst-case), 251 estimated tokens (272 worst-case), 217 atoms, 119 exact operations |
| G9 arms | diagnostic pending because the oracle account returned HTTP 403 |

The structure-aware grammar contains one choice from each variable pair and one
omitted vertex from each clause triangle, so its size is `2^24 3^96`. The
nonsingular parity system has one variable assignment. For that assignment,
each four-clause block has completion multiplicity three, producing exactly
`3^24` accepted lists and exact density
`1/(2^24 3^72) = 2.6457558450387274e-42`. The G4 sampler draws uniformly from
this full shape-constrained grammar; it is not padded with malformed lists.

## Oracle loop and G9 arms

| run | preset | completed attempts | outcome |
|---|---|---:|---|
| bare | easy (`n=8`) | 3 | 3/3 solved across both configured vendors |
| bare | medium (`n=16`) | 2 | 2/2 solved; four redraws for attempt 3 returned HTTP 403 |
| bare | hard (`n=24`) | 0 | not reached |
| structural hint | hard (`n=24`) | 0 | four redraws, all HTTP 403 quota errors |
| placebo hint | hard (`n=24`) | 0 | four redraws, all HTTP 403 quota errors |

No shipping-preset bare rate or hinted-minus-placebo difference exists yet.
The error records are retained as infrastructure diagnostics, not hardness
evidence. The hinted arm is diagnostic rather than gated under the current
contract; the missing bare shipping verdict still prevents release.

## Use

```python
import gen_1706_08050 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
print(g.render(inst))
text = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = g.parse_answer(text)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emission is `bash scripts/emit.sh 1706.08050`—but do
not emit this result until OpenRouter quota is restored, the bare hardening run
reaches a terminal verdict, both diagnostic arms complete, and `G9_RESULTS` is
updated.

## Caveats

- A tool-enabled solver makes this family easy: Gaussian elimination and DPLL
  both finish in well under a millisecond locally. This is exactly why it is
  Track B, not Track A.
- The G4 prior is uniform over every answer satisfying the explicit pair and
  triangle quotas. It measures blind guessing within that declared grammar,
  not a solver that notices parity or performs propagation.
- No external SAT/ILP package was used because the module must remain standard-
  library-only; the panel includes an implemented DPLL solver and the stronger
  parity-specific Gaussian algorithm.
- `canonical_key` uses a colored 1-WL quotient. It is invariant under all tested
  source relabellings and input reorderings, but 1-WL can theoretically collide
  on non-isomorphic graphs; it is not a complete graph canonizer.
- The witness grows as `9n+1`. After `n=28` the 256-atom cap, not the mathematics,
  binds, so `escalate()` returns `cap_bound`. The `n=48` G7 build is deliberately
  not a shipping candidate.
- Most importantly, the required shipping-preset multi-vendor evidence is
  absent. The five scored lower-rung solves are real evidence that `easy` and
  probably `medium` are too easy; none of the HTTP errors is a model failure.
