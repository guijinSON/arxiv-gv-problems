# Rejection: arXiv:1903.12570 — *Sparse graphs are near-bipartite*

## Decision

The proposed native family fails **H**, on both possible tracks.  **G** and **V**
would be straightforward: sample a partition `V(G)=I union F`, add no edge inside
`I` and only forest edges inside `F`, and return `I`; a checker can test
independence and acyclicity in `O(|V|+|E|)` time without reading the planted
answer.  The obstacle is obtaining a defensible hardness claim for the generated
distribution.

This decision is based on the full v2 paper, especially the Main Theorem and
Theorems 1.1, 1.2, 2.2, and 2.3, together with Sections 2.1 and 5—not on the
abstract.

## Step-0 discrimination

The paper defines an nb-coloring to be a partition into an independent set `I`
and a set `F` whose induced multigraph has no circuit; in particular, two parallel
edges are already a circuit of length two (Sections 1 and 2.4).

The certificate-producing algorithm is explicit:

- Main Theorem (A), restated as Theorem 1.1, finds an nb-coloring of the stated
  sparse multigraphs in `O(|V|^6)` time.
- Main Theorem (B), restated as Theorem 1.2, finds one for the stated sparse simple
  graphs in `O(|V|^22)` time.
- Section 5 derives those bounds from the constructive proof.  Its main
  subroutine is the max-flow/min-cut potential minimizer of Theorem 2.2.
- The introduction also records an `O(|V|)` algorithm for subcubic `K4`-free
  graphs, and observes that every 2-degenerate graph is handled by the obvious
  linear greedy algorithm.

Consequently Track A is false in exactly the parameter regimes proved by this
paper.  The fact, also noted in the introduction, that unrestricted
near-bipartiteness is NP-complete is only a worst-case statement.  It supplies no
distributional-hardness theorem for an inverse-generated planted partition.

## Why this is not a missed Track-B family

I checked the paper's most promising compact native construction, `G_k` from
Section 2.1.  Deleting one inter-pair chain edge gives a positive instance by the
paper's own proof.  Every doubled edge forces one endpoint into `I` and the other
into `F`.  The deleted edge splits the displayed chain, after which the colors
propagate from its two ends.  Randomly relabelling the vertices hides names but
does not hide this structure: doubled edges and the quotient chain are recovered
by one adjacency scan.

At `k=120` this candidate has 244 vertices, 366 edge occurrences, and a 122-vertex
witness.  Its structure-aware candidate space is `2^122`; exactly four choices
arise from the two end pairs after the chain colors are forced, so its guess
density is `4/2^122 = 2^-120`.  It therefore clears guess resistance while still
failing hardness.

The two required cost figures are:

| route | shipping-size cost |
|---|---:|
| Mechanical specialization of the paper's greedy method | one multiset/adjacency scan plus one chain traversal: 366 edge reads, at most 244 vertex visits, and 120 pair propagations (`< 1,000` elementary graph operations) |
| Compact route after recognizing `G_k-e` | the same scan is needed to locate the doubled pairs and missing link, followed by the same 120 propagations; there is no asymptotically or materially shorter route |

As a sanity measurement, a deliberately unoptimized Python prototype that
repeatedly scans the constraints used 32,452 counted loop/propagation operations
and averaged 0.00304 seconds over 200 relabelled `k=120` instances.  At `k=64` it
used 10,164 operations and averaged 0.000756 seconds.  An ordinary queue-based
implementation has the `<1,000`-operation linear bound in the table.  Thus the
paper's compact construction is not a million-operation mechanical task hiding a
dozen-step invariant; recognizing the construction *is* the mechanical algorithm.

The other native candidate, minimizing the paper's potential function, has the
same problem.  Theorem 2.2 explicitly turns it into max-flow/min-cut in
`O((|V|+|E|)^3)`, or `O((|V|+|E|)^2 log(|V|+|E|))` for bounded edge size, and
Theorem 2.3 adds the requested constant-size boundary conditions.  A min-cut and
max-flow are excellent exact witnesses, but on a generator with a visibly
composed cut the compact route is just the same cut computation; hiding the cut
removes the sub-300-operation route rather than creating one.

For a generic planted `I,F` construction there are therefore only two outcomes:

1. planting leaves a recoverable degree, degeneracy, chain, or component signal,
   in which case a linear greedy/propagation attack is the compact route and
   succeeds; or
2. those signals are removed, in which case the solver has no short public
   invariant and must execute the polynomial algorithm/search itself, violating
   Track B's compression and 300-operation intended-route requirement.

No module was built because STEP 0 already disqualifies the proposed family.  A
future attempt would need a genuinely new, paper-native invariant whose recovery
is demonstrably much shorter than both the Section 5 algorithm and the strongest
construction-aware propagation attack; the paper's stated constructions do not
provide one.
