# Rejected: arXiv 2412.04967

Paper: Lixia Luo, Changheng Li, and Qiongxiu Li, [*Deterministic Algorithms to Solve the \((n,k)\)-Complete Hidden Subset Sum Problem*](https://arxiv.org/abs/2412.04967), arXiv:2412.04967v2.

## Decision

The proposed inverse family passes **G** and **V**, but it does not pass **H**. I therefore did not create `gen_2412_04967.py`, did not claim any mandatory gate passed, and did not run `scripts/harden.py`.

## Exact problem read from the paper

Section 1 defines an \((n,k)\)-complete HSSP instance as the multiset of **all** \(\binom{n}{k}\) sums of exactly \(k\) distinct positions of an unknown cardinality-\(n\) multiset \(X\), over an Abelian group and then over \(\mathbb R\) for the paper's algorithms. The paper assumes \(2\le k\le n/2\): the total of \(X\) is determined by the input, and complementing each \(k\)-sum gives the \((n-k)\)-sums.

Inverse generation would be immediate: sample an integer multiset \(X\) first and publish all exact \(k\)-subset sums. Verification would also be exact and cheap relative to the input: recompute those \(\binom{n}{k}\) sums from a candidate and compare multisets. Thus G and V are not the issue.

## Why H fails

Theorem 2 and Algorithm 2 (Sections 1 and 4.4) give a deterministic reconstruction procedure whenever the Moser-polynomial determinants are nonzero for every degree \(1,\ldots,n\). The procedure computes power sums from the published multiset, solves the partition-indexed linear systems, applies Newton identities, constructs the monic polynomial whose roots are the hidden elements, and recovers \(X\) from those roots. Table 1 in Section 5 describes this as the algorithm for the unique-solution regime.

This is polynomial in the size of the explicitly published instance, not merely an algorithm that looks large as a function of the hidden cardinality. Let

\[
M=\binom{n}{k},\qquad 2\le k\le n/2.
\]

For every \(u\le n\), conjugating partitions and then forgetting their weighted sum gives

\[
p(u,\le k)\le \binom{u+k}{k}\le \binom{n+k}{k}\le M^2.
\]

The last inequality follows by comparing at \(n=2k\) (the ratio decreases with \(n\)); it is also a deliberately loose bound. Hence the paper's stated arithmetic-operation bound

\[
O\!\left(\sum_{u=1}^{n}p(u,\le k)^3+Mn\right)
\]

is at most \(O(nM^6+Mn)\), therefore polynomial in the explicit input length. For integer-planted instances, the intermediate quantities have polynomial bit length and exact integer-polynomial factorization/root recovery is also polynomial-time. For fixed \(k\), the conclusion is even more immediate: \(p(u,\le k)=O(u^{k-1})\), and Theorem 1's ordered brute-force algorithm is polynomial as well.

## Why the singular cases do not rescue the family

Algorithm 2 can fail when a Moser determinant vanishes, but the paper does **not** prove that this exceptional search problem is hard. Section 1 says singular-pair characterization remains incomplete and states that, for fixed \(k\), only finitely many \(n\) can have multiple solutions. Section 5 lists singular-pair characterization as future work. That is not a theorem-backed, scalable hard parameter regime from which an unlimited generator can honestly be built.

The obvious infinite exceptional line \(n=2k\) is especially unsuitable as a fallback: complementing a \(k\)-subset makes every input invariant under a global reflection of the hidden multiset, and Section 5 specifically says the polynomial-time NS-family attacks perform well when \(n=2k\). The general HSSP NP-completeness cited in Section 1 concerns a different problem in which only an arbitrary collection of subset sums is supplied; it does not establish hardness for the complete all-\(k\)-sums restriction.

## Failed gate

| Gate | Result | Evidence |
|---|---|---|
| G | Would pass | Plant \(X\), then enumerate all exact \(k\)-subset sums. |
| H | **Fail** | Theorem 2/Algorithm 2 reconstruct the nonsingular regime in time polynomial in the explicit input size; exceptional regimes have no hardness theorem or scalable classification in the paper. |
| V | Would pass | Recompute and compare the complete multiset of sums exactly. |

Running the LLM hardening loop cannot repair a theoretical H failure, and a model failing to execute the reconstruction inside one response would not turn this polynomial-time family into a hard one.
