# Rejected: arXiv:1507.05605

Paper: Amelia Perry and Alexander S. Wein, [*A semidefinite program for
unbalanced multisection in the stochastic block model*](https://arxiv.org/abs/1507.05605),
version 2.

## Decision

No generator was built. The native planted-partition recovery family fails **H on
Track A**, and the full-text Track B audit finds no compact no-tool route. The
partition-only verifier proposed in the prior triage also fails the witness rule.
This is a Step 0 rejection, before an oracle hardening run.

G itself is not the problem: one can sample the community labels first and then
sample each edge from the planted-partition model. Nor is exact verification
fundamentally impossible: Section 5 gives a dual SDP certificate. The obstruction
is obtaining a hard, writable, independently checkable witness under either
declared track.

## What the paper actually defines

Section 1.2.1 partitions the vertices into communities and independently includes
an edge with probability `p` within a community and `q` between communities.
Section 1.2.3 fixes the exact-recovery regime
`p = p_tilde log(n)/n`, `q = q_tilde log(n)/n`, with a constant number of
communities and constant limiting proportions. The required answer is the whole
partition, up to a permutation of community names.

Programs 4 and 5 in Section 2.2 optimize over the paper's centered partition
matrix, whose entries are `1` within a community and `-1/(r-1)` between
communities. Theorem 2 says that these SDPs recover that matrix as the **unique**
optimum with probability `1-o(1)` throughout the information-theoretically
feasible range of Theorem 3. Section 1.3 also records an efficient spectral
clustering plus local-refinement algorithm of Abbe and Sandon for the more general
block model. Thus the distribution suggested by the prior triage is expressly an
efficient-algorithm success distribution, not a Track A distribution.

The relevant easy/limiting regimes were not omitted: Section 4.4 shows that robust
algorithms cannot attain the general-block-model threshold, and Section 4.5 shows
why fully unknown parameters are incompatible with monotone robustness. Those
negative results do not rescue the proposed family: in the paper's planted
partition regimes, the parameters needed by Program 4 or Program 5 are supplied,
and Theorem 2 applies.

## Certificate audit

Comparing a submitted partition with hidden planted labels is not a witness check.
The labels are neither visible in the rendered instance nor certified by the
candidate; renaming the same secret as another instance field would not change
that. A graph can also admit a plausible or optimal partition different from the
random labels that happened to generate it.

The paper's executable witness is Proposition 10 in Section 5.3 (with the dual
written as Program 6 in Section 5.2). It uses dual
variables `nu` and `Gamma`, with

`Lambda = diag(nu) + omega J - A - Gamma`,

and checks exact positive semidefiniteness, strict positivity of every off-block
of `Gamma`, zero diagonal blocks, and the prescribed kernel of `Lambda`.
Sections 5.4--5.9 construct it using the per-vertex values `gamma_v`, the row sums
`R_vj`, and rank-one off-blocks
`Gamma_uv = R_uj R_vi / T_ij`. A checker could reconstruct the redundant matrices
from a candidate partition and the `gamma_v` values and perform these tests with
exact rational arithmetic. That clears V, but it does not clear H.

## Track A failure

Theorem 2 is precisely a polynomial-time recovery guarantee for the generated
distribution and parameter regime. Theorem 3 additionally says efficient
algorithms exist everywhere exact recovery is information-theoretically feasible.
Worst-case NP-hardness of the fixed-size MLE, mentioned in Section 2.1, is
irrelevant to this average-case distribution. Declaring Track A would therefore
contradict the paper.

## Track B mechanical cost versus compact route

I audited an explicit, self-contained dual witness rather than stopping at “an
SDP exists.” For `r=3`, carrying the `n` community labels and `n` rational
`gamma_v` values uses three atomic integers per vertex once rationals are
serialized as `[numerator, denominator]`. The 256-atom cap therefore limits this
representation to `n <= 85` (`3n = 255`). The remaining dual arrays are
deterministic from these values and need not be serialized.

At that largest admissible size:

| quantity | measured/countable cost |
|---|---:|
| unordered adjacency entries that Section 5's degree counts may inspect | `C(85,2) = 3,570` |
| dense cubic scale for one exact PSD/rank elimination | `85^3 = 614,125` scalar updates |
| certificate atoms before any optional matrix is included | `255` |
| allowed intended-route exact operations | `300` |

One can reduce the answer to the partition alone and make `verify` construct the
paper's `gamma`, `R`, `Gamma`, and `Lambda` arrays. That permits `n=256`, but it
only moves a polynomial-time certificate-construction algorithm into the checker;
it does not supply a shorter route for the solver. At that size there are 32,640
unordered adjacency entries to aggregate.

The paper's Section 5 change of variables is the shortest compact route found. It still
forms every relevant `E(v,j)` degree count from the random graph, computes one
`gamma_v` per vertex, constructs the `R_vj`, and checks the dual slack. That is at
least the same 3,570 graph-entry inspections as the direct mechanical
degree-profile/local-refinement route, before arithmetic or output. There is no
shorter symmetry, invariant, change of coordinates, or succinct description to
exploit: the labels and edges are independent random variables in the model.
Consequently the **compact route is not shorter than the lightest mechanical
route**; both aggregate the random edge observations, and both exceed the
300-operation no-tool cap by more than an order of magnitude.

For comparison with the named SDP, at `n=256` (the largest partition-only answer)
Program 4 has 32,896 independent symmetric matrix entries, and one dense PSD
eigendecomposition has cubic scale `256^3 = 16,777,216`. A local timing of that
single LAPACK primitive was 0.006706 seconds median over 12 warmed runs. This large
machine/by-hand gap is not a usable Track B shortcut: the only shorter known
recovery route still scans and aggregates the random graph rather than collapsing
to a few exact operations. It is ordinary computation, not a hidden structural
insight.

Making the graph deterministic or encoding the labels by an affine formula would
create a short route, but the hardness would then come from an added encoding
puzzle rather than this paper's stochastic-block-model mathematics. Making
communities cliques or exposing the support of `Gamma` makes the partition
immediately recoverable by connected components or zero-pattern inspection. Both
options fail the requested native-family standard.

## Gates implicated

- **Witness rule / V for the prior triage:** fails for a partition checked only
  against hidden planted labels.
- **H, Track A:** fails by Theorems 2 and 3.
- **H, Track B and G9(c):** the best compact route found is the same edge-aggregation
  computation as the mechanical method and needs at least 3,570 inspections at the
  largest size supporting a writable exact dual certificate, above the 300-operation
  cap.

No `gen_1507_05605.py` was written, so there is no rejected module to retain.
