# Rejected at Step 0: no defensible hard witness family

Paper: Joan-Josep Climent and Juan Antonio López-Ramos, [*Public Key
Protocols over the Ring \(E_p^{(m)}\)*](https://arxiv.org/abs/1606.05457)
(arXiv:1606.05457).

## Decision

No generator module is shipped. The paper supplies native, exactly checkable
algebraic witnesses, so G and V are attainable, but none of its cryptographic
search problems supports the required H claim.

| Candidate family | G / V | Algorithm producing an attack witness | H outcome |
|---|---|---|---|
| Section 3 semigroup action problem: find \(A\in E_p^{(m)}\) with \(AM=MA\) and \(A\cdot R=T\) | Sample a commuting \(F\), publish \(T=F\cdot R\); verify the two displayed equalities exactly | Micheli–Weger, Proposition 15, reduces the conditions to successive systems of linear congruences and proves the CLR protocol is breakable in polynomial time | Fails Track A |
| Section 4 DHDP/EGDP: recover the shared ring element | Sample \(A_1,A_2\in H(M)\), multiply; a linear-decomposition coefficient matrix is an exact certificate | Khathuria–Micheli–Weger, Algorithm 1, solves an \(m^2\)-equation, \(m^2\)-unknown linear system over \(\mathbb Z/p^m\mathbb Z\), then evaluates \(\sum_{i,j}\lambda_{ij}M^iG_BM^j\) | Fails Track A |
| Literal factor recovery: find \(A_1,A_2\in H(M)\) with \(G_A=A_1XA_2\) | Inverse generation and exact multiplication work | The source paper gives no hardness theorem, distributional analysis, or parameter regime for factor recovery; the protocol goal is already defeated without recovering the private factors | Cannot substantiate Track A |

The later DHDP/EGDP attack has stated complexity \(O(m^6)\)
\(\mathbb Z/p^m\mathbb Z\)-operations (equivalently
\(O(m^8\log(p)^2)\) bit operations). Its authors report 23.1 days for the
previously proposed \(p=2,m=128\) parameters. Thus a large instance can make
the mechanical route expensive, but that fact alone is not structural
hardness.

## Why Track B was not used

Track B also requires a compact, solver-discoverable route whose post-insight
work fits the 300-operation cap. Neither the source paper nor the two
cryptanalyses provide such a route for a naturally generated distribution.
The known routes are precisely the congruence sieve or the large modular
linear solve. Sampling a private key gives the *generator* a trapdoor witness;
it does not give the solver a compact route. Adding an artificial correlation
that encodes the sampled key in unrelated public entries would create a
construction-specific puzzle rather than a family justified by this paper.

The DHDP linear certificate also runs into the answer cap in the regime where
the published attack is genuinely burdensome: it contains \(m^2\)
coefficients, already 16,384 atomic elements at \(m=128\), far above the limit
of 256. Asking for the shorter private factor pair avoids that certificate but
also loses the paper-backed efficient reference route required for an honest
Track B claim.

## Exact Step 0 findings

- Section 2 defines \(E_p^{(m)}\) as row-wise modular matrices and characterizes
  its center (Theorem 2). These are the native objects; no graph or finite-field
  surrogate is needed or appropriate.
- Section 3 defines the SAP encryption and proves only necessary conditions
  excluding a *central* solution (Theorem 3 and Corollary 1). It gives counts
  such as \(|Z(E_p^{(m)})|=p^m\) and discusses the scarcity of units, but it
  does not prove hardness for a generated distribution.
- Section 4 defines \(H(M)\), DHDP, and EGDP. Theorem 4 proves equivalence of
  breaking EGDP and solving DHDP; it is not a hardness theorem.
- The easy regimes are not merely hypothetical. The SAP protocol was broken
  by a polynomial-time congruence-system attack, and the two decomposition
  protocols were broken by modular linear algebra.

## Sources

- Source paper, full text and definitions: <https://arxiv.org/pdf/1606.05457>
- G. Micheli and V. Weger, *Cryptanalysis of the CLR-cryptosystem*, especially
  Proposition 15: <https://ora.ox.ac.uk/objects/uuid:efe27809-22e5-4418-9d12-138fdb4b0e77>
- K. Khathuria, G. Micheli, and V. Weger, *On the algebraic structure of
  \(E_p^{(m)}\) and applications to cryptography*, Section 3 and Algorithm 1:
  <https://arxiv.org/abs/1810.02964>

Because rejection occurred before implementation, there is intentionally no
`gen_1606_05457.py`, `selftest_report.json`, or oracle transcript. Creating
those files would falsely imply that Steps 1–4 had been reached.
