# Rejected at Step 0: arXiv:2105.11317

Paper: Pamela E. Harris, Peter Hollander, and Erik Insko,
[*On $(t,r)$ broadcast domination of directed graphs*](https://arxiv.org/abs/2105.11317).

## Decision

No generator is shipped. The paper supplies native objects with cheap exact
verification, and several of its constructions supply certificates, so **G and V
are available**. However, every theorem-backed certificate family in the paper
fails **H on Track A**, and none has the distinct short structural route needed for
**Track B**.

The best fixed-answer-length candidate is the oriented-star construction from
Proposition 3.14. For `t=3`, `r=1`, and 16 source leaves, the unique minimum
broadcast dominating set is exactly those 16 leaves, independently of how many
sink leaves are added. It is obtained by scanning the arcs and collecting the
leaves whose arc points toward the center. Thus the very theorem that certifies
the answer also gives a linear-time algorithm for recovering it on every generated
instance.

| Gate | Result | Reason |
|---|---|---|
| G — generatable | available | Proposition 3.14 certifies the source-leaf set on an oriented star; the grid constructions in Observations 3.8–3.9 and Proposition 4.6 also explicitly provide their tower sets. |
| H — Track A | **fails** | The star witness is recovered by one arc scan; the finite-grid witness of Proposition 4.6 is recovered by one indegree scan. The paper contains no NP-hardness, average-case hardness, FPT barrier, or hard generated distribution for the arbitrary-graph definition. |
| H — Track B | **fails** | In the scalable star candidate the mechanical algorithm and the shortest public compact route are the same scan. For the grid constructions, the scan and the certificate output are both linear in the displayed grid. There is no million-operation-versus-dozens compression gap. |
| V — verifiable | available | Definition 2.8 can be checked exactly using bounded directed shortest paths and integer reception sums; for `(2,2)`, only immediate out-neighbors are needed. |

This is a failure of H, not of the witness rule. It also is not `cap_bound`: the
16-vertex star answer is well below the answer cap and can be made arbitrarily
large in ambient graph size.

## What the paper actually establishes

Definitions 2.6–2.8 define directed distance, signal `t-d(u,v)`, cumulative
reception, and a directed `(t,r)` broadcast dominating set. A submitted finite
set of towers is therefore an executable witness: compute directed distances less
than `t`, sum integer signals, and compare every reception with `r`.

The main arbitrary-graph result does not give a hard certificate generator.
Lemma 3.1 proves that reversing one arc changes `gamma_{t,1}` by at most one.
Theorem 3.2 (and its `(2,2)` analogue, Theorem 3.3) then proves interval fullness
by starting with orientations already known to attain the two extreme domination
numbers and walking between them by arc flips. The proof does **not** find those
extreme orientations or identify the first intermediate orientation having a
requested exact domination number without evaluating domination numbers. An
orientation alone is also not a witness for the claim that its domination number
is exactly `b`; a feasible tower set supplies only the upper bound.

The paper's concrete finite families are deliberately explicit:

- Theorem 3.7 quotes closed formulas for undirected grids of fixed widths 3–5.
  Observations 3.8 and 3.9 explain how to orient the grid around those already
  known patterns. Section 3.2 also points to Sage code using dynamic programming.
- Proposition 3.10 gives contained intervals for small-width grids from displayed
  orientations. These witnesses grow linearly with grid length.
- Propositions 3.12–3.14 completely classify stars by the number of source
  leaves, and Theorem 3.15 obtains fullness by exhaustion of that one integer.
- Theorem 4.2 gives three explicit periodic infinite-grid patterns, of densities
  `1/3`, `1/2`, and `2/3`. Proposition 4.6 cuts them into finite grids and proves
  optimality because the towers are exactly the vertices of indegree at most one.

These are existence, classification, and explicit-construction results. None is a
hardness theorem for finding a broadcast set from a generated distribution.

## Certificate-producing algorithm and measured cost

The most favorable natural candidate for Track B uses Proposition 3.14 with
`t=3`, `r=1`, a star on `n=4096` vertices, and exactly `s=16` arcs directed from
leaves to the center. Vertex labels and arc order were independently shuffled for
each seed. Every source leaf has indegree zero and is therefore forced into every
dominating set. The 16 source leaves together dominate the center and every sink
leaf, so they are the unique optimum.

The standard algorithm is:

1. accumulate undirected degrees to identify the unique center;
2. scan the arcs once and output the tails of arcs entering that center.

I benchmarked this exact algorithm on 1,000 seeds using standard-library Python.

| Measurement at `n=4096, s=16` | Result |
|---|---:|
| successful recoveries | 1,000 / 1,000 |
| arcs | 4,095 |
| degree endpoint updates | 8,190 |
| direction inspections | 4,095 |
| center-selection comparisons | 4,096 |
| answer atoms | 16 |
| median wall clock | 0.003191 s |
| minimum / maximum wall clock | 0.001182 / 0.059753 s |

The asymptotic mechanical cost is `Theta(n)` time and `Theta(n)` input reads. The
**compact route is no shorter**: after arbitrary relabelling and arc-order
shuffling, each uninspected leaf arc can independently be one of the 16 reversed
arcs, so recovering the exact set requires all 4,095 direction inspections. The
mechanical/compact ratio for the decisive work is therefore **4,095:4,095 = 1**.
The theorem reduces the mathematical characterization to this scan; it does not
leave a hidden invariant that skips it. Marking the source leaves or encoding them
in their labels would merely leak the answer.

The finite-grid route is similarly small at the output cap. On a `3 x 126` grid,
there are 378 vertices and 627 edges, while the upper-density construction of
Proposition 4.6 has 252 towers. Its proof says that the minimum set is precisely
the vertices of indegree at most one. Recovery costs 627 indegree increments, 378
threshold tests, and 252 output writes: about **1,257 elementary operations**.
The compact route performs the identical scan and must still emit 252 atoms.

## Why other native formulations do not repair H

| Candidate problem | Why it is not acceptable |
|---|---|
| Find the minimum set on the paper's oriented stars | Linear source-leaf scan; Track A is false and Track B has a 1:1 route. |
| Find the minimum set in Proposition 4.6's oriented grids | The proof itself identifies all and only indegree-`0/1` vertices; one linear scan outputs the answer. |
| Reproduce a Theorem 3.7 grid pattern | The certificate has linear length, and the quoted formulas/patterns are explicit. At writable size, execution and output are the same linear work. |
| Find an orientation with domination number `b` via Theorem 3.2/3.3 | The theorem assumes extremal orientations and uses unknown intermediate domination numbers. Exact optimality is not locally certified by an orientation or a feasible tower set. Supplying all optimum checks would reintroduce the search. |
| Return one of Theorem 4.2's infinite periodic patterns | The paper displays only three classified constructions, so this is lookup. Allowing an unrestricted infinite orientation destroys finite exact verification. |
| Plant towers in an arbitrary oriented graph and ask for a set of that size | G and V can pass, but inverse planting alone supplies no distributional hardness. The paper gives no parameter regime or attack analysis supporting Track A. The private planted set is not a solver-visible Track B shortcut. |
| Encode SAT/set cover as `(2,1)` domination | Such a reduction is not in the paper. It would be a convenience reduction that compiles away the paper's interval, grid, and orientation mathematics, so it cannot provide native coverage. |

For the arbitrary-graph option, asking only for *some* dominating set without a
cardinality bound is trivial because all vertices work. Adding a size bound turns
it into a genuine search problem, but the paper provides neither a hard generated
distribution nor a theorem-backed way to certify exact optimality beyond the easy
special families above. A novel planted-distribution study could conceivably make
a different benchmark; it would not justify a Track A claim from this paper.

## Final gate diagnosis

| Requirement | Result |
|---|---|
| G — certificate known without solving the generated instance | **Passes in isolation** for stars and the displayed grid constructions. |
| V — exact, cheap witness checking | **Passes in isolation** by directed-distance reception sums. |
| H — Track A structural hardness | **Fails:** the theorem-backed distributions are linearly solvable, while the general planted proposal has no distributional hardness basis. |
| H — Track B no-tool compression | **Fails:** 4,095 mechanical direction inspections versus the same 4,095-inspection public route on the best fixed-answer candidate; grid recovery is about 1,257 linear operations with 252 compulsory output atoms. |
| Overall | **Rejected at Step 0.** |

Because Step 0 fails before module construction, there is no generator,
`selftest_report.json`, or oracle transcript to retain.
