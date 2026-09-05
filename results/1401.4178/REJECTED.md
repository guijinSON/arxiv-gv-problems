# Rejected at Step 0: decomposition certificates do not yield a supported hard distribution

Paper: Béla Csaba, Daniela Kühn, Allan Lo, Deryk Osthus, and Andrew
Treglown, [*Proof of the 1-factorization and Hamilton decomposition
conjectures III: approximate decompositions*](https://arxiv.org/abs/1401.4178),
arXiv:1401.4178v2.

## Decision

No generator is shipped.  The prior-triage proposal—sample Hamilton cycles or
perfect matchings and publish their union—passes **G** by inverse generation and
passes **V** by exact edge checks, but it fails **H on both tracks**.

- **Track A fails.**  The paper proves existence in dense extremal graph
  regimes; it gives no average-case or planted-distribution hardness result for
  a union of randomly sampled factors.  The proof itself repeatedly reduces
  the construction to max flow, perfect matching, greedy matching, and a
  Hamilton-cycle construction in a robust outexpander.  Worst-case hardness of
  Hamilton decomposition outside these regimes would not establish hardness
  of the proposed answer-first distribution.
- **Track B also fails for the inverse proposal.**  A hidden random
  decomposition is private generator state, not a solver-visible invariant.
  Once the cycle/matching structure is hidden, the only route supplied is the
  same decomposition search used mechanically.  If instead the construction
  is made visible by using the Walecki symmetry invoked in Section 5.1, the
  paper's direct Walecki formula is already the certificate-producing
  algorithm: the purported compact route and the mechanical route are the same
  length.  There is nothing to compress.

This is not `cap_bound`.  A literal decomposition can fit the output cap at
small orders, but at exactly those orders the explicit structured
constructions are short.  Enlarging the theorem's graph makes the certificate
quadratic and crosses the cap; it does not reveal a fixed-length hardness axis.
Steps 1–4 were therefore not run, as required when Step 0 already fails H.

## The paper's actual objects and parameter regimes

Section 2 defines a decomposition as pairwise edge-disjoint spanning subgraphs
whose edge multisets sum to the original graph.  A 1-factorization is a set of
perfect matchings covering every edge.  A Hamilton decomposition consists of
Hamilton cycles, plus at most one perfect matching when the degree is odd.

The global results quoted as Theorems 1.1 and 1.2 apply only for sufficiently
large graphs:

- an even-order `D`-regular graph has a 1-factorization when
  `D >= 2 ceil(n/4) - 1`;
- a `D`-regular graph has a Hamilton decomposition when
  `D >= floor(n/2)`.

The current paper handles the two extremal structures rather than arbitrary
regular graphs.  Lemma 3.1 assumes a graph close to two equal cliques, together
with localized edge-disjoint exceptional systems.  A Hamilton exceptional
system is an exceptional path cover with a positive even number of `AB` paths;
a matching exceptional system has no `A'B'` edge.  Lemma 3.2 gives the analogous
result for a graph close to a complete balanced bipartite graph and balanced
exceptional systems.  Both statements use an asymptotic hierarchy

`1/n << epsilon_0 << 1/K << rho << 1`

and Section 2 explicitly says the hierarchy functions are not calculated.
Thus the lemmas do not by themselves provide a finite numeric preset for a
theorem-backed generator.  Inverse generation avoids that G problem, but does
not create H.

Sections 5–7 expose the constructive route.  Section 5.1 uses Walecki's theorem
to decompose the complete graph on the clusters into Hamilton cycles.  The
graph between consecutive clusters becomes a cyclic system whose edges
"wind around" that blown-up cycle.  Balanced extensions make the prescribed
path sequences locally balanced.  Lemma 7.1 then extends them to Hamilton
cycles.  Its proof:

1. takes a sparse superregular slice;
2. uses Lemma 7.2 to extend each path sequence to a directed 1-factor by
   bipartite perfect matchings;
3. uses Lemmas 7.3–7.4 to replace matchings and merge the factor's cycles.

The easy machinery is explicit.  Lemma 4.2 says its almost-regular bipartite
subgraph is obtained by MaxFlowMinCut and hence yields edge-disjoint perfect
matchings.  Lemma 7.2 invokes Hall's theorem and Lemma 4.2.  The bipartite-case
balanced-extension proof in Section 8 also says to find one set of matchings
greedily, then decomposes regular bipartite graphs into perfect matchings.
These are valid witness-producing tools, but they rule out pretending that the
dense theorem regime is a Track A search-hard distribution.

## Step-0 mechanical cost and compact-route comparison

The comparison below uses the largest natural literal certificates allowed by
the 256-atom cap.  An atom is one written vertex label; representing edges as
pairs cannot improve these counts without flattening the paper's objects into
opaque integers.

| Candidate family | Mechanical certificate production | Compact route | Disposition |
|---|---:|---:|---|
| Walecki decomposition of `K_23` (Section 5.1's reduced-graph object) | The explicit rotation/zig-zag formula emits `11 * 23 = 253` vertex occurrences.  A local exact benchmark made 200,000 certificates in 8.7681 s, **43.84 microseconds each**. | The identical rotation/zig-zag formula and the same **253 output placements**. | Track B fails: cost ratio 1 and the formula is already hand-scale under G9(c). |
| Full Hamilton decomposition at the theorem threshold `D=n/2` | At least `(D/2)n = n^2/4` cycle-vertex occurrences when `D` is even.  The cap permits at most `n=32`, where the output alone is **256 placements**. | A planted random factorization has **no shorter public route**; recovering it is the same decomposition search, followed by the same 256 writes. | Track A is unsupported; Track B has no compression. |
| Full 1-factorization at `D >= 2 ceil(n/4)-1` | It covers `Dn/2 = Omega(n^2)` edges, before counting the two endpoints needed to write each edge. | No bounded macro for an arbitrary generated dense graph is defined or proved in the paper. | Scaling the haystack necessarily scales the witness past the cap. |
| One Lemma 7.1 extension with `q=1` and `n=256` | The paper's route constructs cluster-by-cluster perfect matchings and then merges cycles; even writing the Hamilton cycle takes **256 placements**. | For a randomly planted cycle, no invariant is public, so the route is the same search.  Exposing an affine or Walecki rule makes that rule the direct algorithm and introduces structure not required by the lemma. | No honest Track B gap; Track A remains unsupported. |

The Walecki timing is not used as a complexity claim; the decisive measurement
is the exact 253-versus-253 operation count.  It answers the required Step-0
question: for the only paper-native symbolic shortcut that keeps a whole
decomposition writable, the algorithm producing the certificate *is* the
shortcut and costs the same number of output operations.

## Why the inverse construction is not Track A

Sampling the factors first only proves that one decomposition exists.  It says
nothing about the distribution of other decompositions or the cost of finding
one.  In the paper's regimes the generated graph is deliberately dense and
organized into almost-complete bipartite pairs or robustly expanding pieces,
precisely the structures exploited by the proof's flow, matching, and merging
steps.  A claim based on NP-hardness of Hamilton decomposition for general
graphs would concern a different distribution and parameter regime.

Using fewer planted cycles does not repair this.  It moves the graph outside
Theorems 1.1–1.2 and Lemmas 3.1–3.2, while still leaving an unsupported random
union distribution.  Using one easily checked Hamilton cycle instead of a
decomposition changes the task: it no longer certifies the approximate
decomposition that is the paper's result, and dense instances generally have
many unrelated witnesses.

## Why no symbolic-macro rescue is claimed

A macro is a sound witness only when its semantics can be expanded and checked
against the instance.  For complete reduced graphs, the Walecki macro does
this, but its explicit formula makes the answer immediate and gives the
253-versus-253 comparison above.  For an arbitrary inverse-generated union of
cycles, the paper provides no compact normal form.  Adding a hidden affine
labelling, circulant rule, or bespoke switch code would create a new
reconstruction puzzle; that extra algebraic structure is neither assumed by
the main lemmas nor produced by their proofs.  Calling it native coverage would
attribute the invented hardness to this paper.

## Final gate disposition

| Requirement | Result |
|---|---|
| G | **Passes for the proposal:** sample factors first and take their edge-disjoint union. |
| V | **Passes:** check that each part is a Hamilton cycle or perfect matching, check edge-disjointness, and compare the exact edge multiset with the graph. |
| H, Track A | **Fails:** no distributional hardness theorem covers the planted union; the paper instead exposes flow/matching/merging constructions in its dense regimes. |
| H, Track B | **Fails:** hidden random factors have no public compact route, while visible Walecki structure is generated directly in 253 operations and has no mechanical/compressed gap. |
| Overall | **Rejected at Step 0; no module or oracle artifacts created.** |

