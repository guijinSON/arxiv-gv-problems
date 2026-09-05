# Rejected at Step 0: arXiv 1802.09981

Paper: Pham Hoang Ha, [*Spanning trees in a Claw-free graph whose stems
have at most k branch vertices*](https://arxiv.org/abs/1802.09981) (2018).

## Decision

No paper-supported generated distribution clears **G + H + V**.  A listed
spanning tree is an exact, cheap witness, and inverse planting or a composition
of Euler tours can supply one without solving the emitted instance.  The
obstacle is **H on both tracks**.

* **Track A fails.**  The paper proves extremal existence conditions, not
  computational or distributional hardness.  Its proof does not give a
  certificate-producing sampler, and the natural inverse-generated claw-free
  distribution tested below is solved on 20/20 shipping-size instances by an
  ordinary degree-aware greedy path heuristic.
* **Track B fails.**  On the natural line-graph construction, the public
  certificate route is line-graph root reconstruction followed by an Euler
  tour.  That route and the supposed compact route are the same incidence
  reconstruction; the generator's private Walecki-cycle labels are not present
  in the problem.  Moreover, the much simpler by-hand-style greedy attack
  already succeeds 20/20, so the mandatory four-failing-attack panel cannot be
  reported honestly.

Implementation therefore stopped before Step 1, as the task requires.  No
generator, gate report, or oracle transcripts were fabricated.

## What the paper actually defines

Section 1 works with finite simple connected graphs.  A leaf of a tree has
degree one, a branch vertex has degree at least three, and
`Stem(T) = T - Leaf(T)` removes the leaves of the original tree once.  The
requested object is a spanning tree `T` for which `Stem(T)` has at most `k`
branch vertices.

For `l >= 2`, `alpha^l(G)` is the largest cardinality of a vertex set whose
distinct members have pairwise graph distance at least `l`.  The quantity
`sigma_k^l(G)` is the minimum degree sum over such `k`-sets and is defined to be
infinity when `alpha^l(G) < k`.

The two main results are:

* **Theorem 1.7:** a connected claw-free graph has the desired tree if
  `sigma_(k+3)^4(G) >= |G| - 2k - 5`;
* **Theorem 1.8:** the same conclusion follows from
  `sigma_2^5(G) >= |G| - 3k - 6`.

Theorem 1.9 specializes these statements to stems that are spiders when
`k = 1`.  These are sufficient existence conditions, not hardness results.

## Step-0 certificate question

The proof in Section 3 is by contradiction.  It chooses, among subtrees whose
stems have exactly `k` branch vertices, one that is successively extremal in
three quantities `(C1)--(C3)`, and then performs exchange arguments.  It does
not output a spanning tree from a graph satisfying either hypothesis.  Finding
the globally extremal starting subtree is already a search problem.

Consequently, sampling a graph only from a theorem hypothesis does **not** meet
G: the theorem promises a witness but its proof does not hand the generator a
finite witness without search.  The honest alternatives are to plant a tree
first or to compose a known traversal and carry it through a claw-free
construction.  Both pass G, but then need an independent hardness argument for
the resulting distribution.  The paper supplies none.

Verification itself is not a problem.  Given a proposed edge list, a checker
can test exact edge membership, `|V|-1` edges, connectivity, acyclicity, remove
the original leaves, and count degree-at-least-three vertices in the remaining
tree.  Thus V passes in isolation.

## The natural theorem-regime family tested

I tested the strongest faithful version of the prior-triage idea while keeping
claw-freeness guaranteed rather than hoping that arbitrary added edges preserve
it.

1. For odd `q = 41`, take Walecki's decomposition of `K_41` into 20
   edge-disjoint Hamilton cycles.
2. Select six cycles and take their union `H`.  Concatenating the six closed
   tours at their common vertex is a known Euler tour by composition; no search
   is used to obtain it.
3. Form the line graph `G = L(H)` and randomly relabel its vertices.  Line
   graphs are claw-free.  The Euler edge order in `H` becomes a Hamilton path
   in `G`, hence a spanning tree whose stem has zero branch vertices.

Here `H` is 12-regular with 246 edges, so `G` has 246 vertices, is 22-regular,
and has 2,706 edges.  Its natural path certificate has 246 integer atoms and
875 compact JSON characters, just below the task's 256-atom cap.  Twenty seeds
selected twenty distinct six-cycle subsets.

For all 20 sampled seeds, `alpha^4(G) <= 2`: thirteen line graphs had diameter
three, and seven had a few distance-four pairs (2--26 pairs), but none had a
triple pairwise at distance at least four.  Therefore
`sigma_3^4(G) = infinity`, placing every tested instance in Theorem 1.7's
`k = 0` regime rather than merely in an unrelated claw-free subclass.

The planted certificate is not statistically special: every line-graph vertex
has the same degree, and every chosen Walecki cycle is carried through the same
random relabelling as the others.  Nevertheless, the family is easy.

## Measured failure of H

The construction-aware standard route is:

1. recognize the line graph and reconstruct its 41-vertex root graph; and
2. run Hierholzer's algorithm on the even-degree root, mapping the Euler edge
   order back to line-graph vertices.

Both stages are linear in the represented graph size.  At the tested setting a
single scan already touches 5,412 line-graph adjacency entries, followed by
about 492 root-edge incidences and 246 emitted path vertices.  A public
"compact" route must recover the same incidence cliques before it knows which
randomly relabelled line vertex denotes which root edge, so it has the same
roughly 5,904 structural touches plus output.  The private six-cycle order
would take only 245 transitions, but using it requires the generator's hidden
cycle selection and relabelling inverse; it is not an insight available from
the public instance.  Thus the public mechanical/compact ratio is effectively
one, and the public route also exceeds the 300-operation no-tool cap.

More decisively, root reconstruction is unnecessary on this distribution.  I
ran the standard Warnsdorff-style path heuristic: from a random start, repeatedly
choose an unused neighbor with the fewest unused neighbors, breaking ties with
a seed-local RNG and allowing up to 32 starts.  At `q = 41`, six cycles:

| measurement | result |
|---|---:|
| verified Hamilton paths | **20 / 20** |
| median wall time | **0.0235429 s** |
| median neighbor probes | **64,922** |
| median path decisions | **245** |

Each returned Hamilton path is itself a valid paper witness, whether or not it
matches the planted traversal.  This is a successful in-context greedy attack,
so it cannot be hidden under Track B's successful `reference_algorithm` key;
the required `attacks` panel would fail G6.

I also tested two simpler variants before this one.  On randomly relabelled
`L(K_23)` (253 answer atoms, the largest odd complete-root case under the cap),
the same heuristic solved 20/20 in a median 0.0334116 seconds and 233,730
neighbor probes.  On 240-vertex line graphs of triangle-free 4-regular roots
formed from two known Hamilton cycles, randomized minimum-remaining-degree
search solved all eight measured seeds within 64 starts.  Sparsifying the
theorem-regime example therefore did not expose a usable hard window.

These measurements do not prove every inverse-planted claw-free distribution
easy.  They do show that the paper gives no basis for claiming the needed
distributional hardness, and that the natural native constructions are broken
by the domain-appropriate attack.  Further conditioning on this particular
heuristic would be benchmark-specific tuning absent from the paper.

## The sharpness construction cannot be used as stated

Section 2 claims its displayed graph has no spanning tree whose stem has at
most `k` branch vertices.  For `k >= 1`, the claim is false for the graph as
written.

Let `r = k+3`; the vertices `z_1,...,z_r` form the displayed clique.  In each
copy `D_i = K_m`, choose `d_i`.  Take the following spanning tree:

* the central star `z_1 z_i` for `i = 2,...,r`;
* `z_i d_i` and `d_i v_i` for every `i`; and
* `d_i x` for every other `x` in `D_i`.

After the leaves of this tree are removed, every `d_i` is a stem leaf,
`z_2,...,z_r` have stem degree two, and only `z_1` is a stem branch vertex.
Thus the construction has a spanning tree with one stem branch vertex, contrary
to the stated lower bound of `k+1` whenever `k >= 1`.  The `k = 0` instance is
an obstruction, but its three clique hubs are directly exposed by the block
structure and do not supply a hard family.  I therefore did not use Section 2
as a theorem-backed negative certificate.

## Other native tasks considered

| candidate | disposition |
|---|---|
| Sample a graph satisfying Theorem 1.7 or 1.8, then output the promised tree | **G fails:** the Section 3 contradiction proof does not construct the witness without extremal-tree search. |
| Plant a bounded-stem tree, then add claw-free-preserving structure | **H unsupported:** worst-case graph difficulty says nothing about the planted distribution; the natural line-graph realization is greedily solved. |
| Use `k=0` and ask for a Hamilton path, a stronger valid witness | **H fails empirically:** 20/20 at the largest diverse tested preset. |
| Use the Section 2 graph as a certified negative | **Paper guarantee fails for `k>=1`; H fails for the visible `k=0` block obstruction.** |
| Ask for a set attaining `sigma_k^l` | **V fails without an optimum certificate:** a set proves its own distance and degree sum, not that no better set exists. |
| Ask only whether a supplied tree is valid | **H fails:** that is direct linear-time verification with no witness search. |

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G -- certificate known by construction | Passes in isolation | Compose known Hamilton cycles into an Euler tour, then carry it to the line graph. |
| V -- exact witness verification | Passes in isolation | Exact edge, tree, stem, and branch-degree checks. |
| H -- Track A | **Fails** | No distributional hardness result; the natural theorem-regime family is solved 20/20 by greedy search. |
| H -- Track B | **Fails** | Public mechanical and compact routes are the same root reconstruction plus Euler traversal, and a simpler in-context attack succeeds 20/20. |
| Paper sharpness route | **Fails as written for `k>=1`** | The explicit central-star spanning tree above has exactly one stem branch vertex. |
| Overall | **Rejected at Step 0** | G, H, and V do not hold simultaneously for a paper-supported family. |

This rejection is not based merely on an efficient algorithm existing.  It
records both costs, explains why the generator's 245-step private traversal is
not a public compact route, and reports the successful 20-seed attack that
prevents either hardness label.
