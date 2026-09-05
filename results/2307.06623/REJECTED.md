# Rejection: arXiv 2307.06623

Paper: Boštjan Brešar and Jaka Hedžet, [*Bootstrap percolation in strong products of graphs*](https://arxiv.org/abs/2307.06623).

## Decision

The natural generator passes **G** and **V**, but fails **H on both tracks**. No module was built because this is a Step 0 rejection.

| gate | result | reason |
|---|---|---|
| G — generatable | pass | Theorem 2.1 and Corollary 2.2 construct a minimum percolating set. |
| V — verifiable | pass | Exact synchronous bootstrap closure checks a proposed set using only adjacency and integer counts. |
| H — Track A | fail | The same theorem is an efficient construction for every instance in its stated regime, not merely a worst-case existence result. |
| H — Track B | fail | The theorem's mechanical algorithm and the compact route coincide; there is no compression gap. |

## The decisive construction

Section 1.1 defines synchronous $r$-neighbor bootstrap percolation. Theorem 2.1 proves that for

\[
G=G_1\boxtimes\cdots\boxtimes G_k,\qquad k\le r\le 2^{k-1},
\]

with connected nontrivial factors and enough product vertices, $m(G,r)=r$. Its proof is already an algorithm: choose any edge $u_iv_i$ in each factor and output any $r$ vertices of

\[
\{u_1,v_1\}\times\cdots\times\{u_k,v_k\}.
\]

Corollary 2.2 extends the equality to every $r\le 2^{k-1}$. The induction in the proof is also an executable correctness certificate: the chosen binary box infects first, after which connected-factor parent edges propagate infection through each coordinate.

As a sanity check, I generated 24 small random products of connected graphs with 2–4 factors, constructed the theorem's set for a random admissible threshold, and simulated synchronous closure exactly. All 24 sets infected every product vertex. This confirms G and V; it does not supply hardness.

Consequently the proposed "plant an initially infected set and hide it" distribution does not hide a scarce witness. Every choice of one edge per factor creates another minimum witness. A solver never has to recover the planted set.

## Mechanical cost versus compact route

At a representative cap-compliant shipping size $k=6,r=16$, with each connected factor supplied by an edge list, the theorem's standard method needs:

- 6 edge selections (the first edge of each nonempty factor edge list), and
- $16\times6=96$ coordinate emissions for the answer.

That is about **102 elementary selections/writes**, with time $O(k r)$ after reading the factor headers. The compact route is exactly the same **102-step** construction. Even if adjacency matrices are used and finding the first edge costs $O(\sum_i |V(G_i)|^2)$ probes, a no-tool solver must inspect the same input; the paper supplies no invariant that bypasses that scan. Thus there is no million-operation mechanical route compressed to a dozen conceptual operations, only the displayed construction itself.

The other exact family does not help. Theorem 2.3 gives

\[
m(C_n\boxtimes K_2^{\boxtimes(k-1)},2^{k-1}+1)
=2^{k-1}-1+\lceil n/2\rceil
\]

and explicitly outputs a whole clique layer plus alternating cycle layers. Mechanical work and compact work are both linear in the certificate length. Increasing $n$ lengthens the answer rather than the haystack, eventually hitting G9(c).

Section 3's strong-prism characterization (Theorem 3.2) and Section 4's bounds similarly assume or reuse percolating sets in the factor graphs; they do not provide a hard generated distribution. The open questions in Section 5 concern extremal values, not a certificate-producing hard search regime.

## Why withholding the factors is not a rescue

One could randomly relabel the product graph and ask the solver to recover product coordinates before applying Theorem 2.1. That would move the difficulty to strong-product factorization or to an artificial label code, neither of which is studied by this paper. With a generic relabelling, both the mechanical and intended routes require processing the encoded graph and exceed the 300-operation no-tool route at useful sizes. With a deliberately decodable labelling, the decoder becomes a planting signature and the construction-aware attack succeeds. Either version would misstate the paper's percolation construction as the source of hardness.

The rejection is therefore specifically **H**, not the witness rule: the paper gives excellent finite witnesses and exact verification, but no acceptable hard family under Track A and no genuine mechanical-versus-compact gap under Track B.
