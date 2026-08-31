# Rejected at Step 0: no defensible hard witness-search family

Paper: Xin-Rong Dai, [*Factorization of Finite Cyclic Group
Z_(pqr)^2: Szabó Pairs and Full Tiling Structures*](https://arxiv.org/abs/2601.07135),
arXiv:2601.07135v2.

## Decision

The natural candidate is: for distinct primes `p,q,r`, construct one or both
sets `A,B` of size `p*q*r` such that every residue modulo
`M=(p*q*r)^2` has exactly one representation `a+b`. This candidate satisfies
G and V, but it does **not** satisfy H, so no generator was produced and the
hardening loop was not run.

| criterion | result | evidence |
|---|---:|---|
| G — generatable | yes | Definition 1.1 explicitly parametrizes Szabó pairs. Its condition (I) constructs `A` from three complete residue-selector sets, while (II)–(IV) construct `B` from translated periodic pieces. |
| H — hard | **fail** | Theorem 1.1 is an if-and-only-if classification of every factorization in the paper's stated regime and says that one orientation must be a Szabó pair. Section 1.2 calls this a “full answer” to Problem 1. Section 3 supplies the normal form and the transformations used to manufacture the complement. The paper contains no NP-hardness, search-hardness, or parameterized-hardness result. |
| V — verifiable | yes | The definition permits direct enumeration of all `|A||B|=M` sums. More strongly, Theorem 2.2 says factorization is equivalent to `|A||B|=M` and `Div(A) intersect Div(B)={M}`, which is exactly computable from pairwise gcds. |

## Why changing the size does not rescue H

The hard-looking parameter regime in the introduction is mathematical rather
than computational: `(p*q*r)^2` is the first regime not reducible to the
two-prime structural theorem. The paper then completely resolves that same
regime. Increasing the primes only enlarges objects governed by the same
explicit normal form:

- Proposition 3.3 gives
  `A = q^2*r^2*U + r^2*p^2*V + p^2*q^2*W`, with one freely selected
  representative in every residue class of `U,V,W`.
- In the sufficiency proof of Theorem 1.1, the starting complement is the
  explicit set `p*q*r * {0,...,p*q*r-1}`.
- Lemmas 3.1 and 3.2 give local translations of periodic pieces that preserve
  the factorization, and Definition 1.1 specifies the resulting `B` structure.

Thus a problem that hands the solver only `p,q,r` and asks for a witness has a
direct construction. Hiding `A`, `B`, or their construction choices does not
create a paper-supported hard family; it merely turns the explicit construction
into an encoding/recovery exercise. A partial-completion problem could be
invented, but this paper proves no hardness for it, so claiming H would be
unsupported.

## Easy regimes checked

Section 1.1 explains that when the factor sizes share at most two prime factors,
Sands' theorem plus the Coven–Meyerowitz characterization recursively describes
the factorization sets. The three-prime-square case is the paper's remaining
case, and Theorem 1.1 gives its full classification. No FPT lower bound or other
computational hardness regime is identified anywhere in Sections 1–6.

Per the task's Step 0 instruction, `gen_2601_07135.py`,
`selftest_report.json`, and `llm_loop_transcript.jsonl` were intentionally not
created. Running the mandatory gates or oracle loop for a family already known
to fail H would produce misleading evidence.

---

## Independent audit (not the builder's self-report)

The builder rejected on **H**, citing the classification. That citation is
correct, but it argues from what the paper *says*; the rejection is stronger than
it claims, and the one gap in it — the dismissal of the "partial-completion"
variant as merely *invented* — is the variant a generator would actually have
shipped. Both were checked by construction. See
[`audit_tiling_attack.py`](audit_tiling_attack.py).

### The natural family has a constant answer

The only formulation with a non-trivial-looking witness is *hand the solver `A`,
ask for `B`*. It is broken by a set that never inspects `A` at all:

\[
B_0 \;=\; pqr\,\mathbb{Z}_M \;=\; \{0,\;pqr,\;2pqr,\;\ldots\}, \qquad
A\oplus B_0=\mathbb{Z}_M \ \text{ for \emph{every} } A \text{ of form (I)}.
\]

One line proves it. Under CRT, \(\mathbb{Z}_M\cong\mathbb{Z}_{p^2}\times
\mathbb{Z}_{q^2}\times\mathbb{Z}_{r^2}\), and condition (I) makes \(A\) a *product
set*: its \(\mathbb{Z}_{p^2}\)-component is \(\{q^2r^2u_i \bmod p^2\}\), which
because \(u_i\equiv i \pmod p\) and \(\gcd(q^2r^2,p^2)=1\) is a complete residue
system mod \(p\). Any complete residue system mod \(p\) satisfies
\(U\oplus p\mathbb{Z}_{p^2}=\mathbb{Z}_{p^2}\); taking the product over the three
primes gives \(B_0\). This is the same set the paper itself uses as the starting
complement in the sufficiency half of Theorem 1.1 — it is a *universal* one.

Verified directly, 30 random form-(I) `A` per triple:

| \((p,q,r)\) | \(M=(pqr)^2\) | \(\lvert A\rvert\) | \(A\oplus B_0=\mathbb{Z}_M\) |
|---|---:|---:|---|
| (2,3,5)  | 900     | 30  | 30/30 |
| (2,3,7)  | 1 764   | 42  | 30/30 |
| (2,5,7)  | 4 900   | 70  | 30/30 |
| (3,5,7)  | 11 025  | 105 | 30/30 |
| (3,5,11) | 27 225  | 165 | 30/30 |
| (3,7,11) | 53 361  | 231 | 30/30 |
| (5,7,11) | 148 225 | 385 | 30/30 |

A witness the solver can print without reading the instance is the most complete
failure of **H** available.

### Even with the constant answer forbidden, the search collapses

Excluding \(B_0\) does not help, because the standard algorithm for the class —
exact cover, tiling \(\mathbb{Z}_M\) by translates of \(A\), branching on the
uncovered residue with fewest admissible translates — solves it outright. At the
smallest parameters \((2,3,5)\), with no structural hint supplied:

- **first complement: 31 search nodes, 0.09 s**;
- **20 000 distinct complements enumerated in 23 s** (78 887 nodes, search *not*
  truncated), every one re-verified by expanding all \(|A||B|=M\) sums.

Twenty thousand witnesses over a space of \(\binom{900}{30}\approx10^{54}\) still
understates the density: the enumeration was capped, not exhausted. A family in
which a blind exact-cover pass returns a witness in 31 nodes is not hard.

### The genuinely-Szabó regime is not merely hard to search — it is empty here

The one remaining escape would be to demand a \(B\) *not* contained in a proper
subgroup, which is the regime Theorem 1.1 actually characterises and which
excludes \(B_0\). Of all 20 000 complements enumerated for a random form-(I)
\(A\) at \((2,3,5)\), **zero** lie outside a proper subgroup. So for a
generically sampled \(A\) of form (I) there is no Szabó partner to find: a
generator would have to *plant* the pair by building \(A\) and \(B\) together
from Definition 1.1(I)–(IV). At that point the witness is recovered by replaying
the same definition that produced it, which is the classification-as-lookup
disqualifier in Step 0 — not a search.

### Scope

This closes the gap the builder left open. Its verdict stands, and on firmer
ground than citation: the family fails **H** in the "any complement" form (the
answer is a constant), in the "some other complement" form (31-node exact cover),
and in the "Szabó partner" form (nothing to find unless planted, and the plant is
read back off the definition). The paper is a complete structural classification,
and a complete classification is a lookup table, not a search problem.
