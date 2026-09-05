# Rejected after Step 0: arXiv:2210.00207

Paper: Ansong Ma and Yuefang Sun, [*A minimum semi-degree condition for
unpaired many-to-many disjoint path covers in digraphs*](https://arxiv.org/abs/2210.00207).

## Decision

This paper does not yield an honest problem family under the requested gates.
`G` and `V` are available, but `H` fails on both tracks.

| Gate | Result | Reason |
|---|---|---|
| G — generatable | available | Sample `k` vertex-disjoint directed paths first and add distractor arcs; the sampled paths are a certificate. |
| H — Track A | **fails** | The paper proves an extremal existence condition, not computational hardness or hardness for a generated distribution. The natural planted dense distribution is easy for a construction-aware search. |
| H — Track B | **fails** | The paper supplies no solver-visible invariant, symmetry, or change of variables giving a compact route. Replaying the planted paths would be short, but those private generator choices are not recoverable from the instance. |
| V — verifiable | available | Check endpoints, directed adjacency, vertex-disjointness, and exact coverage in linear time in the written paths. |

## What the paper actually says

Definition 1 (Section 1) requires exactly `k` vertex-disjoint directed paths
whose initial vertices are the specified sources, whose terminal vertices are
the specified sinks in any permutation, and whose vertex sets cover the whole
digraph. Theorem 1 states that an `n`-vertex digraph with
`delta^0(D) >= ceil((n+k)/2)` has such a cover for every pair of disjoint
source and sink sets. The proposition immediately after Theorem 1 gives
extremal examples one below that bound when `n >= 3k`.

These are existence and sharpness results. There is no NP-hardness theorem,
average-case result, planted-distribution analysis, FPT lower bound, or other
hard parameter regime in the paper that could support Track A. Section 2 is an
inductive attempt to construct a cover by modifying a smaller cover, with the
base case delegated to Theorem 2 (Overbeck-Larisch's Hamiltonian-connectedness
condition). The current arXiv record is withdrawn and says explicitly that the
authors found a mistake in the claim on page 5, so this version's new proof
cannot be used as a theorem-backed certificate constructor.

## Measured failure of the proposed planted family

I tested the prior-triage proposal directly. For each seed, I sampled `k`
disjoint covering paths, inserted their arcs, independently inserted every
other possible arc with probability `0.62`, and rejection-resampled until the
paper's minimum semidegree condition held. The shipping-scale test used
`n=256`, `k=8`; hence the required minimum semidegree was `132`. This is the
largest explicit path witness allowed by the 256-atom output cap.

The attack converts the endpoint-constrained cover to a Hamiltonian-cycle
search in the standard way: sinks may go only to sources, sources may receive
only from sinks, and all other allowed transitions are original arcs. A
depth-first search orders choices by the number of remaining successors. It
solved all 8/8 independently generated instances.

| Measurement at `n=256, k=8` | Result |
|---|---:|
| successes | 8 / 8 |
| mean wall clock | 0.157 s |
| mean recursion nodes | 405.375 |
| mean successor/availability probes | 2,917,513.125 |
| node range | 398–416 |

The same attack solved 8/8 instances at `n=128, k=8` in about 0.021 seconds.
Thus worst-case hardness of Hamiltonian path cannot be transferred to this
dense random planted distribution. The experiment is not claimed as a theorem
about every conceivable planted distribution; it is evidence that the proposed
one fails, while the paper provides no theorem licensing a different hard
distribution.

## Track B audit: mechanical cost versus compact route

At the maximal writable size, the measured mechanical route above costs about
2.92 million elementary availability probes and 0.157 seconds. The apparent
compact route is to replay the planted cover, requiring `n-k = 248` arc steps
(or 255 successor choices after joining the paths). That route is **not
solver-accessible**: the planted order is private generator state, and planted
arcs are unmarked among identically represented distractor arcs. From the
instance, the shortest route found is the same mechanical search, so the
solver-visible mechanical/compact gap is 1:1, not a compression problem.

Making the plant recoverable by marking its arcs, exposing its permutation, or
imposing a new affine/circulant encoding would create a short route, but that
structure is absent from Sections 1–2 and would make the benchmark an invented
analogue rather than this paper's family. Increasing `n` is also unavailable for
an explicit cover: `n=256` already consumes the entire atomic-answer cap.

Accordingly, an efficient attack rules out Track A for the proposed
distribution, while the absence of any solver-visible shortcut rules out Track
B. No generator module was written because the task instructs rejection at
Step 0 when a gate fails.
