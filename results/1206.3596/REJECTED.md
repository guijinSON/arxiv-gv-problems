# Rejection report — arXiv:1206.3596

Paper: Douglas F. Rall and Kirsti Wash, [“Identifying codes of the direct product of two cliques”](https://arxiv.org/abs/1206.3596).

## STEP 0 verdict

Reject at **H (hardness)** on both tracks. G and V are available: the paper gives
identifying codes by construction, and a proposed code can be checked exactly by
testing domination and comparing all closed-neighborhood intersections. The
obstruction is that the same construction which supplies the planted certificate
also solves every instance in the paper's distribution.

The exact object is a subset `C` of the vertices `(i,j)` of the direct product
`K_n x K_m`. Distinct vertices `(i,j)` and `(i',j')` are adjacent exactly when
`i != i'` and `j != j'`. Section 1.1 defines an identifying code as a dominating
set for which all sets `N[v] intersect C` are distinct. This is the native graph
problem; no surrogate was considered.

## Why Track A fails

Section 2 and Theorems 1–5 completely classify the optimum for every pair of
nontrivial cliques (apart from `K_2 x K_2`, which has twins and hence no identifying
code). More importantly for this decision, Section 4 does not merely prove an
existence theorem:

- Theorem 1 writes down the optimum for `K_2 x K_m`.
- Theorem 2, for `n >= 3` and `m >= 2n`, explicitly gives
  `D = {(i,2i-1),(i,2i): 1 <= i <= n-1} union
  {(n,j): 2n-1 <= j <= m-1}` and proves that its size `m-1` is minimum.
- Theorems 3–5 give similarly explicit sets `D_1`, `D_2`, or `D_3` for every
  remaining regime `6 <= n <= m <= 2n-1`; the few smaller cases are the finite
  table in Section 2.

Thus the generated distribution has a deterministic `O(n+m)` certificate-producing
algorithm. Worst-case hardness of identifying-code problems on arbitrary graphs
would not be evidence about this fully classified product-of-cliques distribution.
Planting one of the displayed sets and randomly permuting row or column names does
not change that algorithm.

## Why Track B also fails: mechanical cost versus compact route

Use the cap-compliant representative `K_64 x K_128`. Theorem 2 directly emits an
optimal code of 127 vertex pairs. Evaluating the two coordinates `2i-1` and `2i`
for `i=1,...,63`, plus the two range endpoints, costs at most **130 exact integer
operations** and 127 output emissions. A direct JSON serialization measures 1,018
characters for its 127 vertex pairs (254 scalar entries), so this is already near
the 256-atom output cap.

The compact route is **the very same displayed formula**. It also costs at most
**130 exact integer operations** and necessarily the same 127 output emissions.
The mechanical/compact operation ratio is therefore 1.0; there is no million-step
mechanical route compressed to a short invariant, and nothing substantive for a
no-tool solver to discover. At smaller sizes both counts shrink together. At
larger sizes the answer-length cap is reached before a computation-versus-insight
gap can appear.

One could manufacture apparent difficulty by hiding the row/column factorization
inside an arbitrary adjacency matrix, by asking for completion of a partially
erased code, or by placing the true code among decoys. Those are additional graph
recognition/search tasks not studied or licensed by this paper; they would test the
obfuscation rather than Theorems 1–5. They were therefore not used to turn a failed
native family into a benchmark-convenience analogue.

## Gates

| gate | result | reason |
|---|---|---|
| G — generatable | pass in principle | Section 4 supplies explicit optimum codes. |
| H — Track A | **fail** | The paper solves the entire generated distribution in `O(n+m)`. |
| H — Track B | **fail** | 130 mechanical operations versus 130 compact-route operations at the cap-compliant representative. |
| V — verifiable | pass in principle | Exact set intersections decide domination and separation in polynomial time. |

No generator was written, so there is no hardening transcript or discarded module
to retain. The rejection is made at STEP 0, before implementation, as required.
