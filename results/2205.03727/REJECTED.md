# Rejected at STEP 0: arXiv 2205.03727

Paper: Akash Kumar, Anand Louis, and Rameesh Paul,
[*Exact recovery algorithm for Planted Bipartite Graph in Semi-random
Graphs*](https://arxiv.org/abs/2205.03727).

## Decision

No generator was built. The native planted-set family clears **G** and **V** but
fails **H on both tracks**.

- **G would pass:** sample a balanced set `S=S1 union S2` first, place any
  connected `d`-regular bipartite graph on it, and then sample the cross and
  background edges exactly as in Definition 1 (or use the semi-random
  background in Definition 2). The two colour classes are known before the
  instance exists.
- **V would pass:** a candidate pair `(S1,S2)` is checked using only the graph
  and the pair: exact sizes, disjointness, no within-class edges, internal
  `d`-regularity, and connectedness. No hidden planted answer is needed.
- **H fails:** the paper is an exact-recovery algorithm paper. Its promised
  distribution is specifically constructed so that the planted set is
  recoverable efficiently, while its raw-adjacency formulation supplies no
  shorter no-tool invariant with which to replace that recovery computation.

This is not a rejection based only on the sentence “an algorithm exists.” The
mechanical and compact costs are compared below.

## What the full paper fixes

Definition 1 fixes the random planted model. The planted object is an
*arbitrary connected `d`-regular bipartite graph* on `k` vertices; cross edges
and edges outside the plant are independent Bernoulli-`p` edges. Definition 2
replaces the outside random graph by a spectrally constrained semi-random graph
and permits a monotone adversary to add outside edges. Thus the native answer is
the planted vertex set, optionally with its signed bipartition indicator; it is
not an adjacency-matrix surrogate or a generic graph reduction.

The decisive results are:

- Section 2, Theorem 17 (the formal version of Theorem 4): when
  `k >= 512 sqrt(n log n)/(alpha p^(7/2))`,
  `p >= 5 (log(k)/(gamma^4 k))^(1/6)`, and
  `d=gamma p k` with `gamma>=2/3`, a deterministic polynomial-time algorithm
  exactly recovers `S` with high probability. Algorithm 2 says to solve the
  displayed primal SDP and return precisely the indices of its nonzero vector
  rows. The proof constructs the matching dual certificate and makes the
  signed indicator the unique null direction.
- Section 1.4.5, “Low degree regimes,” Algorithm 1 and Lemma 16: for
  `d<=2pk/3` and `k>=6 sqrt(6 n log(n)/p)`, sorting the vertex degrees and
  taking the bottom `k` vertices recovers `S` with high probability.
- Section 3, Theorem 37 (the formal version of Theorem 5): in the random planted model there is also a
  deterministic `poly(n) k^(L_{-tau}+1)` recovery algorithm based on bottom
  eigenspace enumeration and a matching cleanup. Observation 6 notes that
  this is polynomial for constant `p`, a complete bipartite plant, a random
  regular plant, or an expander plant because the relevant threshold rank is
  constant.
- The proof overview in Section 1 explains why a naive spectral shortcut does
  *not* replace the SDP for an arbitrary plant: the planted graph may have many
  eigenvalues near `-d`, so the eigengap required by ordinary perturbation
  recovery need not exist.

These statements also identify the tempting easy families. A low-degree
construction is exposed by degree sorting. A complete-biclique, random-regular,
or expander construction enters the constant-threshold-rank special case. The
general high-degree construction is the regime solved by the SDP.

## Why Track A is false

Track A requires the *generated distribution*, not only the worst case, to lack
a known efficient general method. Theorem 17 proves the opposite for the
paper's semi-random distribution in its main parameter regime. Algorithm 1 does
the same in the low-degree regime, and Theorem 37 covers additional random
planted regimes.

Moving below all recovery thresholds would not repair this claim. Section 1
only says that efficient recovery is *not expected* for the `d=0`,
`k=o(sqrt(n))` planted-independent-set special case, by analogy with the
planted-clique conjecture. It proves no distributional hardness theorem there.
The NP-hardness cited for maximum induced bipartite subgraph concerns arbitrary
worst-case graphs and cannot certify a random planted generator. Claiming Track
A from either statement would make exactly the worst-case-versus-distribution
mistake prohibited by the task.

## Mechanical cost and the missing Track B compression

### Low degree

The standard algorithm and the best compact route are the same procedure:
inspect the adjacency data, count every degree, sort, and take the bottom `k`.
At a concrete proposed shipping size `n=2048`, an adjacency scan has exactly
`2048*2047/2 = 2,096,128` edge inspections; comparison sorting has at most
`2048*ceil(log2(2048)) = 22,528` key comparisons. A standard-library benchmark
over eight independently generated dense graphs took a mean **0.297112 s**
(range **0.270477--0.330925 s**).

The **compact route length is the same 2,096,128 inspections plus the degree
selection**, not a dozen operations. Supplying the degrees would shorten the
task only by compiling away the graph, and selecting the bottom entries would
then be a direct evaluation rather than a planted-graph recovery problem.
Mechanical/compact operation ratio: approximately **1:1**.

### High degree

The paper's standard method is the primal SDP. For `n=2048`, its symmetric
matrix variable already has `n(n+1)/2 = 2,098,176` scalar entries, before the
edge inequalities are processed. Algorithm 2's post-processing is just support
extraction from the computed optimum; it is not an independent shortcut.

For the arbitrary connected regular plant allowed by Definition 1, the paper
provides no compact route shorter than solving that optimization (or the
bottom-eigenspace enumeration of Theorem 37). The paper explicitly explains
that the signed indicator need not be recoverable from one distinguished
adjacency eigenvector. Consequently the **compact route is again the mechanical
route**: solve the SDP and scan its `n` row norms. Its operation count is not
smaller; even reading the dense instance takes the same 2,096,128 edge
inspections. A generic SDP implementation would add polynomially many
linear-algebra operations on top of that.

Writing `C_SDP(n,m)` for the operations used by whichever general SDP solver is
chosen, the comparison at `n=2048` is therefore
`C_SDP(2048,m) + 2,048` operations for the mechanical route and exactly
`C_SDP(2048,m) + 2,048` for the alleged compact route. The ratio is **1:1**.
The paper states only “polynomial time” for this routine and reports no empirical
solver runtime, so no invented wall-clock figure is attached to `C_SDP`.

| Native regime | Mechanical algorithm and cost | Compact route and cost | Gap |
|---|---|---|---:|
| Low degree, `n=2048` cost benchmark | 2,096,128 edge inspections + degree selection; 0.297112 s mean over 8 runs | the same scan and selection | about 1:1 |
| High degree | SDP solve `C_SDP(n,m)` + `n` support tests | the same SDP solve + support tests | 1:1 |
| Threshold rank `L_-tau` | Theorem 37: `poly(n) k^(L_-tau+1)` | the same eigenspace enumeration and matching cleanup | 1:1 |

Choosing a specially symmetric plant to invent a shorter route would change
the distribution and trigger Observation 6's easy cases; encoding the plant
in vertex labels or a compact formula would instead test a generator-added
label cipher, not the paper's graph recovery. There is therefore no honest
Track B gap between a large mechanical computation and a sub-300-operation
structural solution.

## Output-cap cross-check

The native witness contains `k` vertex identifiers (or `k` nonzero entries of a
signed indicator). The formal low-degree guarantee cannot coexist with the
256-atom cap: with the most favourable `p=1` and `k<=256`, Lemma 16 would
require

`k >= 6 sqrt(6 n log n)` with `n>=k`,

which already fails at `k=n=256` (`256 < 6 sqrt(6*256*log 256)`). The constants
in Theorem 17 are still larger (`512/alpha >= 3072`). This is not the deciding
rejection reason—H already fails as above—but it rules out pretending that a
small, writable instance lies in the paper's formal recovery regime. A
compressed description of an arbitrary planted set does not exist without
adding non-paper structure.

## Final gate result

| Requirement | Result |
|---|---|
| G — generatable | Passes in principle by inverse generation from Definitions 1/2. |
| V — exact witness checking | Passes by exact induced-subgraph, degree, connectivity, and bipartition checks. |
| H — Track A | **Fails:** Theorem 17/Algorithm 2 and the low-degree and threshold-rank algorithms recover the paper's planted distributions efficiently. |
| H — Track B | **Fails:** mechanical and compact routes coincide; there is no short invariant left after the insight, and the low-degree measured ratio is about 1:1. |
| Overall | **Rejected at STEP 0; no module or fabricated gate/oracle files were produced.** |
