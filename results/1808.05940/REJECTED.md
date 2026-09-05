# Rejected at Step 0: the native obstruction class is finite and tiny

Paper: Adam S. Jobson and Andre E. Kezdy, [*All minor-minimal apex
obstructions with connectivity two*](https://arxiv.org/abs/1808.05940),
arXiv:1808.05940v2.

## Decision

No generator module is shipped. The proposed construction of connectivity-two
apex obstructions fails **G** as an unlimited scalable family, and every natural
search task on the paper's actual objects fails **H** under both tracks. Exact
verification is possible, so this is not a witness-rule rejection.

- **G fails for the native target.** The paper is a complete finite
  classification: Appendix A contains exactly 133 graph6 strings, representing
  every minor-minimal non-apex graph of connectivity two. Decoding the appendix
  gives orders 10 through 16 only. Relabelling these graphs does not create new
  canonical instances, and there is no `n` that can grow.
- **Track A fails H.** The paper gives no distributional hardness theorem.
  Planarity is explicitly noted as linear-time in the Introduction; testing a
  proposed 2-cut is one graph traversal, and finding all 2-cuts is standard
  polynomial-time graph decomposition. Exhaustively testing vertex pairs is
  already tiny at the paper's maximum order.
- **Track B also fails H.** At this bounded scale the mechanical algorithms are
  already tiny-script scale. The paper supplies no different
  instance-visible invariant that recovers a witness in substantially fewer
  steps. For construction from the Section 9 pieces, the displayed 2-sum is
  itself both the mechanical route and the compact route.

The prior-triage suggestion therefore cannot be made into the requested
unlimited family without discarding minor-minimality or adding a benchmark-only
padding/encoding trick.

## What the paper actually proves

Section 2 defines finite simple undirected graphs, graph minors, and
minor-minimal obstructions. Section 3 defines an apex graph as a graph with a
vertex whose deletion is planar. A graph in the obstruction set is non-apex,
while every proper minor is apex. A Kuratowski subdivision in `G-v` is the
paper's native finite witness that `v` is not an apex.

The restrictions that make the class finite are strong:

- Lemma 1 gives minimum degree at least three for every apex obstruction.
- Lemmas 7 and 8 say deleting any 2-cut gives exactly two components and that
  both augmented components are non-planar.
- Lemma 9 says the augmented light component at a basic 2-cut is isomorphic to
  exactly one of `K5`, `K3,3`, and `K3,3+e`; Lemma 10 says every 2-cut is basic.
- Theorems 12, 13, and 14 exhaust the cases with a non-planar heavy component,
  disjoint 2-cuts, and multiple intersecting 2-cuts.
- Theorem 25 covers the remaining vertices by branch vertices of two
  Kuratowski witnesses. The proof of Theorem 26 then bounds the heavy component
  by 10 vertices, reduces the unresolved case to connected planar graphs on
  5--9 vertices, and reports a computer check of all **87,816** such graphs.
  This yields the final 72 obstructions.
- Section 9 does not open an infinite minimal family. Theorem 27 and the
  preceding definition recast the construction using minor-minimal double-apex
  graphs, but the section concludes that there are only **57** rooted
  non-isomorphic graphs of that kind. It explains which 2-sums with `K5` or
  `K3,3` produce members of the already finite obstruction list.

Appendix A is consequently a classification table, not a parameterized hard
regime. I decoded all 133 graph6 entries: their vertex-order distribution is

| vertices | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| graphs | 4 | 16 | 25 | 34 | 35 | 18 | 1 |

They have 20--30 edges. These bounds rule out a native difficulty ladder.

## Why scaling transformations do not repair G

A random permutation of the vertices gives arbitrarily many labelled files but
not arbitrarily many problems. `canonical_key` is required to identify all such
relabelled copies, leaving at most 133 keys. It also leaves the answer space and
mechanical cost bounded.

Subdividing an edge does not preserve the property studied in the paper. If an
edge of an obstruction `G` is subdivided to make `G'`, contracting one segment
of the subdivided path recovers the non-apex graph `G` as a proper minor of
`G'`; therefore `G'` is not minor-minimal. This also conflicts with Lemma 1's
minimum-degree condition. Attaching planar gadgets has the same basic defect:
removing or contracting gadget edges leaves a proper non-apex minor.

Allowing arbitrary non-minimal double-apex graphs would be infinite, but it
would be a different target. The minor-minimal hypothesis is load-bearing in
Theorems 25 and 27, and the paper provides neither a hard distribution nor a
compact recovery invariant for roots of padded non-minimal graphs. Such padding
would make the challenge about the added encoding, not about this paper's
classification.

The still broader task "find an apex vertex in an apex graph" is infinite but
does not rescue the paper either. Inverse generation is easy: choose a planar
graph and add the apex first. The ordinary certificate algorithm then tries
each vertex and runs the linear-time planarity test on its deletion, so Track A
would be false. A one-vertex answer needs more than 1,000,000 eligible vertices
before structure-aware uniform guessing can fall below `1e-6`. On a sparse
explicit graph the direct route is then `Theta(n(n+m))`, about `Theta(10^12)`
vertex/edge inspections, but the paper supplies **no compact route at all** for
locating a privately planted apex. The only solver-visible route remains that
same candidate scan. Adding a modular label, special degree, or symmetric
padding rule would manufacture a compact route outside the paper and would
make the benchmark test that added encoding. Requiring a full planar embedding
instead merely turns the answer into an `Omega(n)`-atom object and violates the
256-atom cap long before the one-vertex guess space is adequate.

## Mechanical cost versus compact route (Track B audit)

The paper's one-time **87,816-graph** computation cannot be charged to each
solver instance. A generator sampling Appendix A knows the result by table
lookup. The per-instance native tasks are much smaller.

I decoded every Appendix A graph and ran the direct exact algorithm for finding
all 2-cuts: enumerate each unordered vertex pair, delete it, and perform a DFS.
The count below charges one operation for each start-vertex probe and adjacency
inspection. Across all 133 graphs it used 1,555--5,750 operations. The maximum
was attained by the 16-vertex, 27-edge graph6 entry
`Oo@_??B?ooB???f?_FrEC`; over nine batches of 1,000 scans in CPython 3.12, its
median wall time was **0.000208038 s** (range 0.000205540--0.000211950 s).

| candidate problem | mechanical method and measured cost | compact route available from the paper | outcome |
|---|---|---|---|
| Find any 2-cut of a promised obstruction | At most 120 pair deletions plus DFS; 5,750 counted operations and 0.000208038 s at the maximum measured entry | The same pair/decomposition scan; no theorem identifies the cut from a smaller visible invariant | Track B fails: no compression, and the mechanical route is already tiny |
| Identify which connectivity-two obstruction was supplied | Canonicalize/compare against the 133 Appendix A entries | The same finite classification lookup | Track B fails: lookup is the whole task |
| Build the Section 9 2-sum from a rooted double-apex card and `K5` or `K3,3` | Copy/merge constant-size edge sets; every result has at most 16 vertices and 30 edges | The identical displayed 2-sum construction, at most 30 output-edge insertions | Track B fails: mechanical and compact routes coincide and are by-hand scale |
| Certify that an Appendix A graph is an obstruction | Linear planarity tests nested over at most 16 vertices and 30 edge deletions/contractions, or a stored certificate/table entry | No shorter scalable route exists; the complete finite list is already supplied | Track B fails: bounded verification/lookup, not no-tool compression |
| Find an apex in an arbitrary inverse-planted apex graph | Try every vertex and apply linear-time planarity; `Theta(n(n+m))`, about `10^12` inspections for the sparse `n>10^6` regime needed by a one-vertex G4 answer | None supplied by the paper; on the generated instance the only honest route is the same scan | Track A fails by the algorithm; Track B fails because there is no compact route, while an added shortcut would be benchmark-only structure |

The strongest possible numerical gap in the paper is between the authors'
one-time classification search and their final table. That is not a legitimate
Track B gap for generated instances: handing the solver a member of the table
makes the table the reference algorithm, while withholding the table leaves no
paper-backed compact route.

## Answer-space and gate audit

Even the most natural witness-search questions fail the anti-guessing gate
before hardness is considered:

| answer | largest structure-aware language on the paper's objects | best possible random-guess bound |
|---|---:|---:|
| an unordered 2-cut | `C(16,2) = 120` pairs | at least `1/120 = 0.008333...` because every promised graph has a cut |
| one obstruction identifier | 133 table entries | `1/133 = 0.007518...` |
| one of the five structural cases | 5 cases | at least `1/5` |

Requiring a verbose collection of Kuratowski subdivisions or planar embeddings
could enlarge a syntactic certificate language, but it would not enlarge the
underlying instance family, make `n` scale, or hide the polynomial-time
planarity/decomposition algorithms. Inflating certificate syntax is not
hardness.

| requirement | result | evidence |
|---|---:|---|
| G -- known witness by construction | Passes only for a finite table | Appendix A supplies 133 graph6 entries; Section 9 supplies 57 rooted cards |
| G -- unlimited/scalable family | **Fail** | all native obstructions have 10--16 vertices; relabellings canonicalize together; subdivisions destroy minimality |
| H -- Track A structural hardness | **Fail** | no hard distribution is proved, and the natural graph tasks have polynomial algorithms |
| H -- Track B no-tool compression | **Fail** | 5,750 mechanical operations versus the same 5,750-operation cut scan; constant-size 2-sum construction is at most 30 edge insertions by either route |
| G4 -- guess resistance for natural short answers | **Fail** | lower bounds 1/120 and 1/133, both far above `1e-6` |
| G7 -- scaling | **Fail** | the complete class has maximum order 16 |
| V -- exact checking | Passes in isolation | DFS verifies a 2-cut; Kuratowski subdivisions and planar embeddings can certify the apex conditions |
| overall | **Rejected at Step 0** | no one family satisfies G, H, and V under either track |

No generator, self-test report, or oracle transcript was created: Steps 1--4
would only disguise the already decisive G/H failures.
