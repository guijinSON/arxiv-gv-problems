# Rejection audit — arXiv:1512.04748

Paper: [*Cubic Graphs with Total Domatic Number at Least Two*](https://arxiv.org/abs/1512.04748), Akbari, Motiei, Mozaffari, and Yazdanbod.

## Decision

No generator is shipped.  The natural theorem-backed family passes **G** and **V** but fails **H on Track A**, and it also fails the distinct **Track B compression test**.  The prior-triage planted family does not repair this: the paper proves no distributional hardness result for randomly planted cubic graphs.

| gate | result | reason |
|---|---:|---|
| G — generatable | pass | Section 2, Theorem 2 guarantees a 2-coupon coloring for every cubic graph with no (not necessarily induced) copy of `L`; Lemma 2 and the theorem proof construct the coloring.  Inverse planting would also give a certificate. |
| H — Track A | **fail** | Lemma 2 explicitly gives an iterative algorithm for the promised class.  It performs constant-size local graph updates while adding vertices, after which the proof of Theorem 2 colors constant-size pieces and propagates colors locally.  With adjacency lists this is linear in the number of vertices. |
| H — Track B | **fail** | The paper's mechanical route is already the compact route: find a triangle or square locally, update one constant-size member of the six-graph family, and propagate a color.  Both routes are `Theta(|V|)` and differ only by a small constant; there is no invariant/change-of-variables shortcut replacing a large computation. |
| V — verifiable | pass | Scan the three neighbors of every vertex and check that both colors occur, exactly in `Theta(|V|)` time. |

## STEP 0 findings

The Introduction fixes the exact object.  A total dominating set meets the **open** neighborhood of every vertex.  A 2-coupon coloring is therefore a map `c: V -> {0,1}` such that every vertex has at least one neighbor of each color.  For a cubic graph the executable checker merely tests that its three neighbor colors are not all equal.

The paper's easy mechanism is load-bearing:

- Section 2, Lemma 1 says that, under the forbidden-`L` promise, every vertex lies in a triangle or a 4-cycle.
- Section 2, Lemma 2 does not merely prove existence: it says "we prove this lemma by providing an algorithm" and builds an `F`-partition through local updates.  Every update handles one of six constant-size graphs.
- The proof of Section 2, Theorem 2 colors the easy pieces independently and handles triangles and the graph `Z` by repeatedly inspecting an outside neighbor and propagating a color.  This is another local pass.
- The Introduction also records other easy regimes: every regular graph of degree at least four is covered by the cited regular-uniform-hypergraph theorem, and a cycle has two disjoint total dominating sets exactly when its order is divisible by four.

Thus the algorithm that produces the certificate on the paper's own promised family is a linear-time local construction, not an SDP, SAT search, or exponential enumeration.

## Mechanical cost versus compact route

The comparison was made at a 252-vertex representative, large enough that a natural compressed witness listing one selected vertex in each of 84 triangle pieces remains hand-writable and stays below the 256-atom answer cap.  On a cubic triangle-expansion representative, a direct adjacency-set implementation measured:

| work | counted primitive operations |
|---|---:|
| discover the 84 triangle pieces | 177 neighbor-pair membership tests |
| construction-specific known-certificate selection | 84 port selections |
| paper's local color propagation | at most 84 outside-edge inspections + 252 color assignments |
| exact verification | 756 neighbor-color inspections |
| paper certificate route, excluding verification | **at most 513** |

The direct local discovery, construction-specific certificate selection, and verification benchmark averaged **0.00090 seconds** in CPython over 20,000 repetitions on this runner.  The 177, 84, and 756 figures are observed loop counts.  The 336-operation propagation figure is a conservative count read directly from the theorem proof: process each triangle once, inspect at most one outside edge, and assign each vertex once.

After the supposed "insight" (recognize the triangle pieces), a solver still performs the same local color propagation: up to 336 operations, or up to 513 when the partition is not leaked as extra input.  Both the mechanical and insight-aware routes are therefore `Theta(|V|)` with the same per-piece action.  A specially labelled construction could expose an antipodal perfect matching and reduce this representative to 84 port selections, but that is not an invariant from the paper: if exposed, the required in-context matching attack succeeds; if hidden by relabelling, recovering it is again the computation.  Thus even the contrived best case replaces 513 tiny local actions with 84 obvious selections, not a million-operation mechanical route with a dozen-step insight.  There is no defensible Track B compression gap.

## Why the planted alternative is not Track A

Sampling a coloring first and then adding cubic edges whose neighborhoods see both colors would satisfy G, and checking that coloring would satisfy V.  It does not establish H.  The paper contains no hardness theorem for that planted distribution, no average-case lower bound, and no parameter regime in which a standard coloring algorithm is shown to fail.  Worst-case hardness of total-domatic problems on other graph classes would not imply hardness of this generator's conditioned random instances.  Declaring Track A for that proposal would therefore replace the required evidence with an unsupported worst-case-to-distribution inference.

## Bottom line

For the paper's theorem-backed objects, the certificate-producing algorithm and the shortest visible solution route are the same local linear construction.  For the broader planted proposal, the source supplies no distributional hardness basis.  Consequently no family from this paper clears all of G, H, and V under either track.
