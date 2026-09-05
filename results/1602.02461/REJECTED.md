# Rejected at Step 0: arXiv 1602.02461

Paper: Henry A. Kierstead, Alexandr V. Kostochka, and Andrew McConvey,
[*Strengthening theorems of Dirac and Erdős on disjoint cycles*](https://arxiv.org/abs/1602.02461)
(2016).

## Decision

No paper-supported generated distribution clears **G + H + V**. The
prior-triage proposal—plant `k` vertex-disjoint cycles and add random graph
edges—does give the generator a witness, and that witness is checked exactly.
It fails **H on Track A**, however: the paper proves an extremal existence
condition, not average-case hardness for planted graphs, and the natural
distribution satisfying that condition is solved immediately by ordinary
triangle-packing heuristics and exact-cover search.

I also considered **Track B** before rejecting. It does not rescue this
proposal. Once the hidden plant is erased by random relabelling and random
edges, the public instance has no invariant, symmetry, or change of variables
that recovers the planted factor. The only known public route is the same
triangle-packing search used mechanically. Thus the mechanical and compact
routes are identical, while the route already violates the 300-operation cap.
Making labels encode the planted cycles would create an artificial label
puzzle absent from the paper, not a graph-theoretic compression problem.

Implementation stopped before Step 1, as Step 0 requires. No generator,
self-test report, README, or oracle transcripts were created.

## The exact objects and parameter regimes in the paper

For an integer `k`, Section 1 defines

- `H_k(G)` as the vertices of degree at least `2k`;
- `L_k(G)` as the vertices of degree at most `2k-2`; and
- `t_G` (formally fixed in Section 2) as the maximum number of
  vertex-disjoint triangles in `G`.

Theorem 1.4 says that a graph on at least `3k` vertices contains `k`
vertex-disjoint cycles if

`|H_k(G)| - |L_k(G)| >= 2k + t_G`.

Corollary 1.6 removes the computationally awkward parameter `t_G`: the
sufficient condition `|H_k(G)| - |L_k(G)| >= 3k` guarantees `k` disjoint
cycles. The special case in which every vertex is high is exactly the
Corrádi–Hajnal minimum-degree regime `|V(G)| >= 3k` and
`delta(G) >= 2k` (Theorem 1.1). Theorem 1.7 gives a planar regime with
`|H_k(G)| - |L_k(G)| >= 2k`, and Theorem 1.8 gives the same bound for graphs
with no two disjoint triangles.

The sharpness discussion after Theorem 1.4 matters for the proposed task. On
exactly `3k` vertices, any `k` disjoint cycles use every vertex and every cycle
has length three. The requested witness is therefore a triangle factor, not an
arbitrary collection of visibly planted longer cycles.

## What produces a certificate

The paper's Section 4 proof of Theorem 1.4 is a minimal-counterexample
argument. It fixes a low-degree vertex `x`, chooses a **maximum** family of
disjoint triangles containing `x`, maximizes a second attachment set, and then
uses auxiliary reachability digraphs and induction to derive a contradiction.
It is not an executable certificate-producing algorithm for a freshly sampled
graph: obtaining its initial maximum triangle family is already the packing
search.

Consequently there are only two honest generation routes here:

1. sample a graph satisfying a theorem hypothesis and then solve it to obtain
   cycles, which violates G; or
2. sample the cycles first and build the graph around them, which passes G but
   needs an independent hardness result for the resulting planted
   distribution.

The prior proposal takes route 2. Exact verification is cheap: check that each
listed cyclic sequence has distinct, in-range vertices, check every consecutive
edge including the closing edge, and check pairwise vertex disjointness. Thus
G and V are not the obstacle.

## Measured failure of the natural planted distribution

I tested the strongest natural version at the exact Corrádi–Hajnal threshold.
For each seed, the sampler:

1. shuffled `n=3k` vertices and planted a triangle factor;
2. independently added every other edge with probability `0.72`; and
3. added random missing incident edges until every degree was at least `2k`.

This puts every instance in Theorem 1.1 / Corollary 1.6's regime without
revealing the planted factor through the degree condition. Plants and added
edges are relabelled, and the algorithms below were not given the plant.

| `k` | `n` | attack | verified solves | median wall time | median search work |
|---:|---:|---|---:|---:|---:|
| 20 | 60 | fail-first Algorithm X on all graph triangles | 8/8 | 0.0812 s | 21 nodes |
| 30 | 90 | fail-first Algorithm X on all graph triangles | 8/8 | 0.4066 s | 31 nodes |
| 40 | 120 | fail-first Algorithm X on all graph triangles | 8/8 | 1.3185 s | 41 nodes |
| 40 | 120 | randomized fail-first triangle greedy | 20/20 | 0.1750 s | 1 restart |

At `k=40`, Algorithm X enumerated a median 108,856.5 triangles using 149,433
triangle-closing edge probes. It then found a factor in 41 nodes—the root plus
one node per output triangle—with no material backtracking. The randomized
greedy attack likewise solved every seed. These attacks may return a triangle
factor unrelated to the planted one, which is allowed because a correct
verifier must accept any valid witness.

The `k=40` answer would contain 120 vertex indices, comfortably below the
256-atom cap. The failure is therefore not `cap_bound`. Increasing `k` merely
makes a still-easy dense packing larger to transcribe.

## Track comparison and the two required costs

### Track A

Theorem 1.4 and Corollary 1.6 are existence results. They state no
distributional hardness theorem, and worst-case hardness of cycle or triangle
packing would not imply hardness of this planted dense distribution. The
domain-standard Algorithm X attack succeeds on 8/8, while even a randomized
greedy succeeds on 20/20. The required Track-A adversary panel would therefore
record successful attacks and fail G6.

### Track B

The mechanical certificate route at the largest tested, answer-cap-friendly
size costs a median **149,433 triangle-closing probes, 41 exact-cover nodes,
and 1.3185 seconds**. Its asymptotic triangle-enumeration cost is `O(n^3)`.

The compact route on the public instance is **the same route**: 149,433 probes
and 41 nodes in the measured implementation. There is no public remnant of the
sampled permutation or planted factor, and the paper supplies no invariant
that reconstructs it. Counting only the exact-cover decisions gives the same
comparison, 41 versus 41; counting the necessary inspection of the adjacency
data gives 149,433 versus 149,433. The ratio is 1, not a large mechanical
calculation compressed to a sub-300-operation insight. Treating the generator's
private planted answer as the “compact route” would hand the solver an oracle.

This is why the rejection is not based merely on an efficient algorithm
existing. The measured mechanical and compact routes coincide, so Track B
would test unassisted bulk graph search rather than recognition of structure.

## Other native candidates considered

| Paper result | Candidate witness | Outcome |
|---|---|---|
| Theorem 1.4 | `k` disjoint cycles under the `2k+t_G` imbalance | G/H conflict: evaluating or exploiting `t_G` requires a maximum triangle packing; planting one supplies G but no hard distribution. |
| Corollary 1.6 / Theorem 1.1 | triangle factor at `n=3k` | H fails on the natural planted distribution by the measurements above. |
| Theorem 1.7 | disjoint cycles in a planar graph | The proof is again by minimal counterexample and contraction; it gives neither a certificate-producing sampler nor a hard generated regime. Planting planar cycles would make hardness an unsupported new distributional claim. |
| Theorem 1.8 | disjoint cycles with at most one disjoint triangle | The contraction proof repeatedly asks whether intermediate graphs already contain `k` cycles. It does not yield an answer-first hard sampler. |
| Sharp example `SK_(3k-1)` after Theorem 1.4 | certified absence of `k` cycles | H fails: the subdividing vertex is the explicit obstruction, and the paper's one-line construction is also the complete certificate route. |
| Section 8's `4k`-vertex negative construction | certified absence of `k` cycles | H fails: compute the 2-core, observe it has `3k` vertices, and inspect the distinguished `x_0`, which lies in no triangle. The explicit obstruction is immediately recoverable. |

## Gate diagnosis

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known by construction | Possible in isolation | Plant the disjoint cycles before adding edges. The theorem alone does not output a certificate. |
| V — exact witness verification | Passes in isolation | Edge membership, distinctness, and disjointness are exact finite checks. |
| H — Track A | **Fails** | No average-case theorem covers the planted distribution; Algorithm X solves 8/8 and greedy solves 20/20 in the theorem's exact minimum-degree regime. |
| H — Track B | **Fails** | Mechanical and compact public routes are the same packing search (149,433 versus 149,433 probes; 41 versus 41 search nodes), with no paper-backed compression insight. |
| Overall | **Rejected at Step 0** | G, H, and V do not hold simultaneously for a paper-supported family. |

No G1–G9 or oracle results are claimed. The measurements above are Step-0
triage measurements of the proposed distribution, not fabricated shipping
gates.
