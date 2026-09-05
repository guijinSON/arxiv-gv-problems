# Rejected: arXiv:2312.03399

Paper: Prosenjit Bose, Vida Dujmović, Hussein Houdrouge, Pat Morin, and
Saeed Odak, *Connected Dominating Sets in Triangulations*
([arXiv:2312.03399v2](https://arxiv.org/abs/2312.03399)).

## Decision

No generator is shipped.  The native witness problem clears **G** and **V**, but
fails **H on Track A**, and the paper does not supply the mechanical-versus-compact
gap needed to rescue it on **Track B**.

The native task would give an `n`-vertex plane triangulation and ask for a vertex
set `X` of size at most `floor((10*n-18)/21)` that dominates every vertex and whose
induced subgraph is connected.  A list of vertices is a perfectly good witness:
connectivity and domination are checked exactly in `O(n+m)` time.  The problem is
generation, not verification: the paper's proof itself produces that witness by a
linear-time algorithm.

## STEP 0 finding: what produces the certificate?

- Theorem 6 (Section 4.6) proves that `BetterGreedy(G)` returns a connected
  dominating set of size at most `(10n-18)/21`.
- Theorem 7 (Section 4.6) states that `BetterGreedy` has a linear-time
  implementation.  Its proof describes the executable machinery: a DCEL for the
  embedding, bucketed inner-degree counters, dom-respecting reductions, block-cut
  trees, contractions, and greedy 3-colouring.
- Theorem 1 packages these facts as an `O(n)` algorithm for the paper's headline
  `10n/21` bound.  Corollary 1 gives the equivalent spanning tree with at least
  `11n/21` leaves, also in `O(n)` time.

Therefore the domain-standard algorithm succeeds on every generated triangulation,
not merely on a special or average-case distribution.  Declaring Track A would be
false.  Random relabelling or planting a set before triangulating does not change
that conclusion at the paper's threshold.

## Track B audit: mechanical cost and compact route

The two required numbers are comparable rather than separated:

| route | cost at the largest nested-triangle size allowed by G9(c) |
|---|---:|
| paper's mechanical route | `O(n)`; at `n=540`, one linear pass over 540 vertices and `3n-6=1614` edges, i.e. 2,154 vertex/edge records up to the constant-factor DCEL and bucket updates |
| best paper-native compact candidate | still linear; on the nested-triangle construction below, at least 180 vertex outputs and 179 inter-layer adjacency choices, i.e. at least 359 elementary select/write actions |

The value `n=540` is the largest multiple of three (as required by this
nested-triangle construction) for which the theorem's worst-case bound can fit the
256-atom answer cap: `floor((10*540-18)/21)=256`.  For arbitrary triangulations the
last size under the atom cap is `n=541`; `n=542` requires 257 vertices in the
worst-case guarantee.
The exact boundary does not help: both routes are linear, and neither is a
dozen-operation symmetry, invariant, or change of variables.

The paper's own compact-looking family is the Section 1.1 lower-bound construction
of `n/3` pairwise nested, vertex-disjoint triangles.  It does not rescue Track B.
If the nesting layers are exposed in the problem statement, the obvious in-context
greedy attack chooses a vertex in each next triangle adjacent to the previous
choice and succeeds, so G6 fails.  If random labels and a shuffled edge list hide
the layers, a solver must recover the separating-triangle decomposition; that is
again a linear graph traversal, not a compact route.  At `n=540` the construction
also forces about `n/3=180` witness vertices before any reasoning steps are counted.

Thus the mechanical method is roughly a constant-factor full scan and the
purported shortcut is a constant-factor full scan/output of the same structure.
The gap is too small and of the wrong kind for Track B: it measures bookkeeping and
transcription rather than discovery of a short mathematical insight.

## Why the planted-solution hypothesis was not used

The prior triage suggested planting a connected dominating set and adding
triangulation edges.  That is inverse generation and would satisfy G, but it does
not establish H:

1. At the paper's `10n/21` threshold, Theorems 6 and 7 recover a valid witness in
   linear time regardless of how the graph was planted.
2. Asking for a substantially smaller planted set changes the benchmark to an
   exact-threshold distribution for which this paper proves no hardness theorem or
   hard parameter regime.  The paper's conclusion instead leaves improvement of
   the universal bound as an open extremal question.
3. A constant-size planted core would create a different, construction-dependent
   problem.  Without a paper-backed reduction or a demonstrated hard distribution,
   defeating a few generic probes would not justify the required Track A claim.

The minimum connected dominating set variant is not a workaround either.  Theorem
10 relates a minimum connected dominating set to a maximum induced outerplane
subgraph, but it does not provide an efficiently checkable lower-bound certificate
for optimality.  Supplying only a feasible set would not certify that it is minimum.

The paper's other native formulations do not open a different hardness gap.  The
spanning-tree formulation in Corollary 1 is obtained from the same linear-time
construction, and a tree certificate contains `n-1` edges unless one introduces a
non-native compression language.  The one-bend-free-set result (Theorem 3) is
obtained from those tree leaves and is again linear-time.  The surface extension
(Theorem 2 and Section 5) first computes a planarizing subgraph in linear time and
then invokes the planar algorithm.  Finally, asking for the outer-domatic batches
used in Section 2 only exposes the proof trace: on the nested-triangle examples the
trace and its vertex output are both linear in the number of layers.  None replaces
the full scan with a fixed-size invariant, symmetry, or change of variables.

## Gate summary

| gate | result |
|---|---|
| G | Passes in principle by the theorem-backed construction (`BetterGreedy`) or by planting. |
| H, Track A | **Fails:** Theorems 6 and 7 solve the native threshold task in `O(n)` on every instance. |
| H, Track B | **Fails:** 2,154-record mechanical scan versus at least 359 linear select/write actions on the paper's nested-triangle candidate; no sublinear compact insight, and exposing the structure makes greedy succeed. |
| V | Passes in principle: exact adjacency, domination, cardinality, and induced-connectivity checks take `O(n+m)`. |

Because the failure occurs at STEP 0, no Python module, self-test report, oracle
transcript, or G9 transcript was fabricated.
