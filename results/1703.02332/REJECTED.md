# Rejected at STEP 0: arXiv 1703.02332

Paper: Till Fluschnik, Meike Hatzel, Steffen Härtlein, Hendrik Molter, and
Henning Seidler, [*The Minimum Shared Edges Problem on Grid-like
Graphs*](https://arxiv.org/abs/1703.02332).

## Decision

No module is shipped.  The prior-triage proposal—plant `p` routed paths in a
grid subgraph—passes **G** and **V**, but it does not pass **H** on either
track.  Planting proves that a routing exists; it does not make the generated
distribution hard, and the paper gives no average-case or planted-distribution
hardness result.  Keeping `p` small to keep an explicit path witness writable
also enters the fixed-parameter-tractable regime identified in the
Introduction.  Letting `p` grow avoids that easy regime but makes the natural
certificate exceed the 256-atom/2,000-character output cap.

This is principally an **H failure for Track A**.  The two paper-supplied
polynomial routes were also checked as possible **Track B** families before
rejecting; their mechanical and compact costs are recorded below.  The hard
holey-grid reduction has a large representation gap, but no efficient
certificate-producing algorithm or short solver-visible route for its
Vertex-Cover core, so it is not Track B.

## Exact definition and easy regimes

Section 2 defines a solution to an instance `(G,s,t,p,k)` as a multiset of
exactly `p` simple `s`--`t` paths for which at most `k` graph edges occur in at
least two paths.  This matters: merely naming shared edges is not the native
witness unless the checker also certifies that contracting them supports the
required flow.

Section 3.1 divides bounded grids into three regimes.

- **Lemma 1 (`p`-small):** when both grid dimensions are below `p`, an instance
  is feasible exactly when `dist(s,t) <= k`; repeating one shortest path is
  optimal.
- **Lemma 2 (`p`-large):** when both dimensions are at least `p`, three explicit
  arithmetic cases in the terminal-to-rim distances characterize feasibility
  and the proof directly constructs the paths.
- The intervening **`p`-narrow** regime is explicitly left open in this paper;
  the conclusion says ongoing work suggests it is polynomial-time.  It cannot
  support a hardness claim here.

The Introduction also records that MSE is FPT in `p`, polynomial on bounded
treewidth, and linear-time on unbounded grids.  Thus a writable planted family
with a fixed small number of paths would steer into known easy structure rather
than the hard parameter regime.

## Track B audit: complete grids

The complete-grid results do not have a meaningful mechanical/compact gap when
the instance is represented in its natural succinct form `(n,m,s,t,p,k)`.

| paper route | mechanical cost from the displayed parameters | compact route |
|---|---:|---:|
| Lemma 1 | two coordinate differences, one addition, one comparison: about **4 exact operations** | the identical Manhattan-distance calculation: about **4 operations** |
| Lemma 2 | degree/rim-distance calculations, at most two case tests, ceilings, additions, and one comparison: at most **20 exact operations** | evaluation of the same displayed piecewise formula: at most **20 operations** |

The paper calls the criterion linear-time because a grid may be supplied as an
expanded graph.  Expanding a million-cell grid only to charge the solver for
scanning it would manufacture a Track B gap through representation: the grid
dimensions and terminal coordinates already determine every edge.  The
certificate-producing construction is also the displayed formula itself, so
the obvious in-context arithmetic attack succeeds.  Complete grids therefore
fail **H on Track B**: the compact route is no shorter than the mechanical one.

## Holey grids: the hard theorem and certificate size

Section 3.2, **Theorem 1**, proves NP-hardness on subgraphs of bounded grids by
reducing Vertex Cover on maximum-degree-three graphs.  For a source graph with
`N=|V|`, `E=|E|`, and cover budget `K`, the proof sets

```text
M  = 2(E+1)+2
c' = 2N + EN - 2E
b  = 2Mc' + 1
a  = max(a0, E^3, b^2)
p  = KM + (N-K) + 1.
```

A source cover selects the `K` meta-grid rows that carry `M` paths; one further
validation path changes rows to cross every edge-column through a selected
incident row.  This is a valid theorem-backed construction, but the native path
witness is far beyond the output cap even for a tiny source.  Taking a cubic
source with `N=8`, `E=12`, and `K=4` gives exactly

```text
M = 28, c' = 88, b = 4,929, a = 24,295,041,
p = 117, and k' = 194,601,732.
```

At least 116 of the proof's paths traverse an `a`-chain, so an explicit routing
contains more than **2,818,224,756 edge occurrences** before the meta-grid,
rainbows, trees, and validation path are counted.  The mechanical construction
therefore costs billions of emitted edge occurrences already at this toy
source size; it cannot be the answer format.

The short alternative is to answer with the selected source rows, i.e. a
maximum-degree-three Vertex Cover, and let a checker execute the reduction's
counting identities symbolically.  That would be a legitimate
`licensed_reduction`, not a native path certificate.  It does not rescue H:

- On **Track A**, Theorem 1 is a worst-case reduction.  It does not say that a
  cover-first random cubic graph, a planted independent-set graph, or a planted
  routing distribution is hard.  Inverse planting is exactly what must be
  justified here, and no such distributional theorem appears in the paper.
- On **Track B**, finding those rows is the Vertex Cover search problem left by
  the reduction.  The paper supplies no efficient algorithm and no compact
  invariant for recovering a cover.  Exhaustive search costs up to
  `C(N,K)` cover tests while the alleged compact route has the same search; at
  `N=32,K=16` this is **601,080,390** candidates, not at most 300 operations.
  If the generator exposes the planted rows, both costs collapse to one linear
  scan and the problem is easy.  Restricting the source to bipartite or visibly
  decomposable graphs would add an external easy family rather than exercise
  Theorem 1's hard regime.

Thus the large gap between expanding the routing and writing a row set is only
a **certificate representation** gap.  It is not an efficient-versus-compact
algorithmic gap for obtaining the row set, which is the quantity Track B
requires.

## Why the prior triage family is not enough

For planted paths, verification is cheap and exact: check every consecutive
edge, both terminals, simplicity, the path count, and the number of edges with
multiplicity at least two.  Generation is also valid because the paths are
sampled first.  The missing gate is hardness:

1. with fixed `p`, the known FPT algorithm applies and the answer can remain
   writable;
2. with growing `p`, explicit paths violate G9(c);
3. a compressed shared-edge set still requires a flow certificate or an exact
   max-flow recomputation, and finding the set remains the MSE search problem;
4. nothing in Theorem 1 transfers worst-case NP-hardness to a distribution
   obtained by planting those paths, while construction-aware degree,
   congestion, cut, and max-flow attacks may expose the plant.

No oracle loop or gate report was run because STEP 0 already rules out the
proposed family.  No generator was written, so there is no `rejected_gen_*.py`
to retain.

## Final gate assessment

| candidate | G | V | H Track A | H Track B | outcome |
|---|---|---|---|---|---|
| inverse-planted explicit paths | pass | pass | fail: no hard generated distribution; fixed `p` is FPT | fail: no paper-supplied compact recovery route | reject |
| complete bounded grid (Lemmas 1–2) | pass | pass | fail: explicitly easy | fail: mechanical and compact costs are both 4–20 operations | reject |
| Theorem 1 holey-grid reduction, explicit routing | pass | pass | output cap blocks the hard regime | output cap blocks the witness | reject |
| Theorem 1 with a symbolic row-cover certificate | pass | pass | fail: only worst-case hardness, not inverse-generation hardness | fail: obtaining the cover has no efficient compact route in the paper | reject |

The paper therefore does not yield a self-contained family satisfying G, H,
V, and G9 under the required answer contract without importing a new hard
distribution or an unrelated succinct algebraic encoding.
