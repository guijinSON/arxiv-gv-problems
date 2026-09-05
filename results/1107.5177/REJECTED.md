# Rejected at Step 0: dense random planting makes the witness abundant

Paper: Alex Scott and Matthew White,
[*Monochromatic cycles and the monochromatic circumference in 2-coloured
graphs*](https://arxiv.org/abs/1107.5177), arXiv:1107.5177.

## Decision

No generator is shipped. The prior-triage proposal—plant a monochromatic cycle
inside a random dense 2-coloured graph—passes **G (inverse generation)** and
**V (exact cycle checking)**, but fails **H** under both tracks. The paper proves
an extremal existence theorem, not hardness of recovering a cycle from the
inverse-planted distribution. On the natural complete-graph realization, a
minimal random-restart greedy attack found an unrelated valid cycle on **20/20**
instances.

This is a Step-0 rejection, so there is intentionally no `gen_1107_5177.py`,
`selftest_report.json`, README, or oracle transcript. The task requires stopping
before the builder and oracle runs once G, H, or V fails.

## What the paper actually defines

Section 1 defines a 2-edge colouring of a finite graph `G` as a partition of its
edges into spanning red and blue subgraphs `R` and `B`. A monochromatic cycle is
a simple cycle lying wholly in one of those subgraphs. The monochromatic
circumference is the maximum length of such a cycle.

Theorem 1.6 (labelled “main result” in the arXiv source) says that, for
sufficiently large `n`, every 2-coloured `n`-vertex graph with minimum degree at
least `3n/4` has a monochromatic cycle of every length from `4` through
`ceil(n/2)`, with one exact exception: when `n=4p`, the graph is
`K_{p,p,p,p}`, and both colour graphs are bipartite. The strict-degree
conjecture proved by this theorem therefore has no exception when the minimum
degree is greater than `3n/4`.

Theorem 1.8 (labelled “circumference”) gives the other main regime. For
`0 < delta <= 1/180` and sufficiently large `n`, minimum degree at least
`3n/4` forces either a monochromatic cycle of length at least
`(2/3+delta/2)n`, or cycles of every length through `(2/3-delta)n` in one
colour. Section 4 proves this with the Regularity Lemma, a reduced graph,
matchings, the Embedding Lemma, and the Blow-up Lemma. It is an existence proof;
it makes no average-case or planted-distribution complexity claim.

The precise exceptional construction in Section 1 matters. Its four independent
sets can be labelled `U_ij`, for `i,j in {1,2}`. Red has bipartition by the first
coordinate and blue by the second. Edges between two opposite pairs of classes
may be coloured arbitrarily. Consequently every monochromatic graph is
bipartite and has no odd cycle. Section 1 also defines `F_{s,t}`: a complete
graph with a set `A` of size `s`, blue edges exactly across the cut at `A`, and
all other edges red. Its monochromatic circumference is the displayed formula
`max(s,2t)`.

## Certificate-production test

For the triaged task, the certificate is `(colour, v_0, ..., v_{ell-1})`.
Sampling distinct vertices first and forcing their consecutive edges to have
the chosen colour produces it in `O(ell)` operations. Verification checks the
length and distinctness of the list and looks up its `ell` cyclic edges, also in
`O(ell)`. Thus G and V are uncomplicated.

The algorithm producing the certificate for the *solver*, however, need not
recover the planted cycle. In a random red/blue complete graph there are many
other witnesses. Planting only makes this easier and the theorem's minimum-degree
promise is automatic because the underlying graph is complete.

I tested the natural proposed distribution at a representative no-tool-sized
setting:

- `n = 256` vertices and requested length `ell = 64`, within the theorem's
  interval;
- choose 64 distinct planted vertices, force their cyclic edges red, and colour
  every other complete-graph edge independently and uniformly red or blue;
- start at a random vertex, repeatedly take the first unused red neighbour in a
  shuffled candidate order, and restart if the length-64 path does not close;
- allow at most 32 restarts and count every inspected adjacency as one edge
  probe.

The attack returned a valid red 64-cycle on **20/20 independent seeds**. It
returned the planted cyclic ordering on **0/20**, confirming that it exploited
witness abundance rather than the plant. Its edge-probe count had
minimum/median/maximum **111 / 133 / 723**, with restart counts
**1 / 1 / 6**. Median attack time was **0.0015 seconds** in CPython; all graph
generation plus attacks took **0.173 seconds**.

These measurements also answer the required Track-B question. The mechanical
route costs only 133 edge probes at the median shipping-sized example. A
hypothetical compact route that is handed the hidden planted order still has to
emit 64 vertex labels and check its 64 cycle edges: approximately **64 atomic
output steps plus 64 edge checks**. The measured route and the putative shortcut
are therefore the same hand-scale order (indeed, their counted work differs by
only about a factor of two), not a million-operation mechanical route compressed
to a dozen insightful operations. Without exposing the plant there is no compact
route at all; exposing it merely makes the question direct transcription.

## Why Track A fails

Track A requires evidence about the generated distribution. The paper supplies
none. Its degree threshold guarantees existence in every graph in a broad
worst-case class, while the proposed generator samples a much narrower random
complete-graph distribution. The measured greedy solve rate is 20/20 on that
distribution. A very small probability that a uniformly guessed 64-tuple is
monochromatic would not repair this: random-answer density and algorithmic
search cost are separate quantities, and here the greedy search is cheap.

Making the host graph sparse down to the theorem's `3n/4` degree boundary, or
adding more planted decoys, would define a new distribution whose hardness is
neither proved nor suggested by the paper. Worst-case difficulty of long-cycle
problems cannot be transferred to such an inverse-planted distribution.

## Why Track B also fails

The random family has no useful mechanical-versus-compact gap, as quantified
above. The paper's two explicit extremal constructions do not furnish a better
one:

| native candidate | certificate | ordinary route | compact route |
|---|---|---|---|
| exceptional `K_{p,p,p,p}` colouring | bipartitions of `R` and `B`, proving no monochromatic odd cycle | breadth-first bipartite colouring, `O(n+m)` | the same propagation; no shorter invariant avoids reading the graph |
| `F_{s,t}` circumference optimum | a longest cycle plus the cut `A` giving the upper bound | group vertices by blue degree/neighbourhood, then traverse a clique or complete bipartite graph | the same grouping; if `A` is displayed, the answer is immediate |
| prescribed cycle in a generic theorem-regime graph | colour and cyclic vertex list | search the supplied graph | the paper gives no concise decoding invariant |

For the exceptional family, the four independent classes are exactly the
non-neighbourhood equivalence classes, and the two colour bipartitions then
follow by ordinary component/bipartite propagation. With arbitrary vertex
labels, finding those classes requires scanning the supplied adjacency data;
there is no sublinear by-hand shortcut. With classes rendered compactly, the
certificate is already exposed. The `F_{s,t}` partition is still more visible:
its two sides have different blue degrees when `s=2t`, the sharp example used
in the paper. These are valid exact witnesses, but not hard families.

The Section 4 proof also cannot be repackaged honestly as Track B. Applying a
regularity partition, finding a reduced-graph matching, and invoking a blow-up
embedding is a long mechanical existence route, but the paper does not encode a
short solver-visible invariant selecting the actual vertices of the promised
cycle. Planting such an invariant would be an extra puzzle construction, not a
consequence of this paper, and the measured random construction already shows
that an arbitrary cycle can be found without it.

## Gate outcome

| requirement | result |
|---|---|
| G — generatable | Passes for the proposal: sample a cyclic vertex list first and force its edges monochromatic. |
| H — Track A | **Fails:** no hardness theorem covers the generated distribution, and greedy random restart solved 20/20. |
| H — Track B | **Fails:** 133 median mechanical probes versus roughly 64 checks plus 64 output steps for an exposed plant; there is no meaningful compression gap. |
| V — verifiable | Passes: distinctness, range, adjacency, and one common colour are checked exactly in linear time. |
| Alternative negative/optimal certificates | Verifiable but easy: bipartite BFS or visible degree/neighbourhood grouping produces them. |
| Steps 1–4 | Not run, as required after the Step-0 H failure. |

The decisive issue is not the witness format. It is that the theorem guarantees
many cycles in a dense setting while the suggested planting distribution makes
one of them exceptionally cheap to find. Shipping it would turn a tiny random
guess probability into a false hardness claim.
