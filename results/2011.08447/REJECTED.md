# Rejected: arXiv 2011.08447

Paper: Yash Khanna, [*Exact recovery of planted cliques in semi-random
graphs*](https://arxiv.org/abs/2011.08447), arXiv:2011.08447v5.

## Decision

No family is shipped. Generatability and verification are straightforward:
sample a set `S`, force every edge inside `S`, and use the vertex list as the
certificate; checking size, range, distinctness, and all selected pairs is exact.
The failure is **H on Track A in the paper's theorem regime**, and **G9(c)'s
no-tool route requirement for the below-threshold Track A fallback and for Track
B**.

Definition 2 in Section 1.2 fixes the semi-random distribution. Theorem 2 gives a
deterministic polynomial-time algorithm that recovers `S` with high probability
when `p >= kappa log(n)/n` and `nu in (0,1)`, including the displayed regime
`k = Omega(max(sqrt(np(r+t+2)), lambda))` under its sparsity conditions. Section 2
and Algorithm 1 state what produces the witness: solve SDP 1, threshold the vector
norms, and greedily complete the clique. Thus the distribution for which this
paper proves exact recovery cannot honestly be Track A.

Track B does not rescue that regime. The proof explains why SDP mass concentrates
on the plant, but it supplies no invariant, symmetry, or change of variables that
identifies the clique without first computing the SDP. Algorithm 1's thresholding
and greedy completion begin only after that mechanical solve. The compact route is
therefore not shorter than the standard route.

The exploratory module tried the `r=t=0`, `p=1/2` special case below the recovery
threshold, where Section 1.4 reduces the model to ordinary planted clique and cites
the Barak--Hopkins--Kelner--Kothari--Moitra--Potechin sum-of-squares limitation for
`k=o(sqrt(n))`. That is plausible Track A evidence, and the local attacks did fail,
but it still does not yield a compliant no-tool problem: after noticing that clique
rows have persistent common neighborhoods, the solver must choose a successful
branch. Selecting that branch is the original exponential clique search, not an
insight followed by at most 300 exact operations. Counting only `k-1` intersections
and `C(k,2)` checks *after the correct branch has somehow been selected* assumes the
answer and is not valid G9(c) accounting.

## Mechanical cost versus compact route

For the paper's native efficient regime, even a modest `n=64` instance writes SDP 1
as a Gram-matrix program of order 65, with 2,145 independent symmetric entries. Its
displayed ordered-pair bounds alone contribute 8,064 scalar inequalities; the
normalization, row-sum, diagonal, anchor, and nonedge constraints add thousands
more. One dense cubic factorization at order 65 is about 91,541 scalar arithmetic
operations, and an ellipsoid/interior-point solve repeats comparable linear-algebra
work. Algorithm 1 then performs 64 threshold comparisons and as many as `n*k`
adjacency checks. The paper gives no compact route independent of this solve, so its
compact-route cost remains SDP-scale (well above 90,000 operations), not at most 300.

For the below-threshold exploratory preset `n=768`, `k=16`, the structure-aware
language contains
`C(768,16) = 598191506203970835856150766731728` candidates. The measured exact
greedy-color clique search exhausted 100,001 nodes on each of eight seeds (54.58
seconds total) without finding a witness. That is the mechanical cost signal. The
paper supplies no shorter route in this regime: the compact route is still the same
branch search, so its measured lower-bound proxy is already over 100,000 explored
nodes, rather than the claimed 135 operations that merely verify a branch once it
is known.

This comparison is why the existence of an efficient SDP is not being used as a
one-line rejection. Its mechanical cost is indeed far beyond unaided hand work; the
problem is that the supposed compact route never shrinks. In the below-threshold
fallback the efficient theorem disappears, but no compact route appears in its
place.

## Paper locations relied on

- Definition 2, Section 1.2: the seven-stage semi-random graph model.
- Theorem 2, Section 1.3: deterministic polynomial-time exact recovery in the
  stated parameter regime.
- Section 1.4: ordinary planted-clique special case, known easy thresholds, and
  the cited below-threshold sum-of-squares limitation.
- Section 1.5: SDP-mass/long-vector proof idea.
- Section 1.6, Lemma 1: robustness to the monotone adversary.
- Section 2, Lemma 3 and Algorithm 1: threshold set, SDP solve, and greedy
  completion.

The exploratory generator is retained as `rejected_gen_2011_08447.py`. Its local
G1--G8 report and failed hardening transcript are also retained for audit. The four
oracle calls in that transcript all received OpenRouter HTTP 403 key-limit errors;
they are API errors, not evidence of oracle failure and not part of this rejection.
