# Rejected at Step 0: no theorem-backed hard witness family

Paper: Jun Seok Oh, Sávio Ribas, Kevin Zhao, and Qinghai Zhong,
[*On zero-sum problems over metacyclic groups* \(C_n\rtimes_s C_2\)](https://arxiv.org/abs/2511.18246),
arXiv:2511.18246v2.

## Decision

The proposed product-one-subsequence family satisfies **G** and **V**, but it does
not satisfy **H** in the parameter regime established by the paper. No generator,
self-test report, or oracle transcript is being shipped.

## What the paper actually proves

Section 2 defines a sequence as an unordered multiset of group elements and calls
it product-one when its terms can be reordered to multiply to the identity.
Theorem 1.1 treats

\[
G=C_{3n_2}\rtimes_s C_2\cong C_{n_2}\times D_6,
\qquad \gcd(6,n_2)=1,
\]

with \(s\equiv-1\pmod 3\) and \(s\equiv1\pmod {n_2}\). It proves
\(\mathsf E(G)=9n_2\): every sequence of length \(9n_2\) contains a
product-one subsequence of length \(|G|=6n_2\). It also completely classifies
the length-\(9n_2-1\) sequences with no such subsequence. Theorem 1.2 combines
this with earlier results to give the direct and inverse classification for all
split metacyclic groups considered in the paper.

The paper contains no NP-hardness theorem, hard parameter regime, FPT lower
bound, or average-case hardness result for finding these subsequences.

## Why the natural search problem is polynomial in this regime

In Theorem 1.1, the explicit input contains \(L=9n_2\) group elements and the
requested witness has \(6n_2\) elements. By Remark 2.1, each element can be
represented as a pair in \(C_{n_2}\times D_6\), where the second factor has only
six possible values.

A polynomial dynamic program can process the input while recording:

- the selected cardinality (at most \(L\));
- the sum in \(C_{n_2}\) (only \(n_2\) states); and
- the multiplicities of the six \(D_6\) element types (at most
  \((L+1)^6\) states).

For each reachable multiplicity vector, a second dynamic program over those six
counts and the six possible running products decides whether the chosen \(D_6\)
multiset has an ordering with product equal to the identity. Backpointers recover
the selected indices and an ordering. The state space is large but polynomial in
the explicit sequence length because \(n_2=\Theta(L)\) and \(|D_6|=6\).

Thus planting a \(6n_2\)-term product-one witness inside a \(9n_2\)-term sequence
would create a verifiable yes-instance, but not a family with no known
polynomial-time method.

## Why the obvious workaround was not used

One could take a group modulus exponentially larger than the number of supplied
terms and ask for an arbitrary-cardinality product-one subsequence. Restricting
all terms to the cyclic subgroup then recovers a modular subset-sum problem. That
may furnish computational hardness from an external subset-sum result, but it is
not the Gao-constant parameter regime proved in this paper: the paper's theorem
requires input and witness lengths linear in the group order. Shipping that
workaround would therefore attribute a hard regime to the paper that it neither
states nor analyzes.

The family is rejected on **H** before implementation, as required by Step 0.

---

## Independent audit (not the builder's self-report)

The builder rejected at Step 0 on a sketched dynamic program. That sketch is
correct but loose — it tracks the six \(D_6\) element-type multiplicities, giving
\((L+1)^6\) states, and it was never run. The rejection was re-derived from the
group law and the attack was implemented and executed: see
[`audit_dp_attack.py`](audit_dp_attack.py).

### The exact structure that collapses the search

Write each term as \(x^{e}y^{a}\). From \(yx = xy^{s}\),

\[
(x^{e_1}y^{a_1})(x^{e_2}y^{a_2}) = x^{e_1+e_2}\,y^{\,a_1 s^{e_2}+a_2},
\qquad\text{so}\qquad
g_1\cdots g_m = x^{\sum e_i}\,y^{E},\quad
E=\sum_i a_i\,s^{q_i},
\]

where \(q_i=\#\{j>i: e_j=1\}\). Because \(s^2\equiv1\pmod n\), every coefficient
\(s^{q_i}\) is either \(1\) or \(s\) — the ordering of a subsequence, a priori
\((6n_2)!\) choices, collapses to a *binary coefficient assignment*, and exactly
which assignments are realisable is fully characterised:

- among the \(2k\) terms from \(x\langle y\rangle\), **exactly \(k\)** take
  coefficient \(s\) and \(k\) take coefficient \(1\), and every such split is
  realisable by a permutation;
- each term from \(\langle y\rangle\) takes coefficient \(1\) or \(s\)
  **freely**, provided \(k\ge1\); if \(k=0\) all coefficients are \(1\).

So a \(|G|\)-product-one subsequence exists iff some sub-multiset of size \(2n\)
admits a coefficient assignment, balanced on the \(x\langle y\rangle\) part,
summing to \(0 \bmod n\). That is a bounded-cardinality subset-sum modulo \(n\)
with a parity side-condition — decided by a DP over
\((\text{count},\ \#s\text{-coeffs}-\#1\text{-coeffs on }x\langle y\rangle,\ E \bmod n)\),
i.e. \(O(L^2 n)\) states and \(O(L^{2}n^{2})\) bit operations. Since the theorem
fixes \(L=9n_2=3n\), this is polynomial **in the explicit input length**, not
merely pseudo-polynomial.

### Evidence

`python3 audit_dp_attack.py` reproduces:

- **correctness** — agrees with exhaustive search over all subsets *and all
  orderings* on 400 random instances (mixed \(n\in\{3,5,6,9,10\}\), all valid
  \(s\)), 400/400 exact, and every emitted witness independently re-multiplies to
  \(1_G\);
- **speed at the paper's own parameters** — \(|S|=9n_2\), witness length \(6n_2\),
  pure-Python, single core:

  | \(n_2\) | \(\lvert G\rvert = 6n_2\) | \(\lvert S\rvert = 9n_2\) | witness | time |
  |---:|---:|---:|---|---:|
  | 5  | 30  | 45  | found, verified | 0.05 s |
  | 7  | 42  | 63  | found, verified | 0.13 s |
  | 11 | 66  | 99  | found, verified | 0.49 s |
  | 25 | 150 | 225 | found, verified | 5.57 s |

At \(n_2=25\) the instance already carries 225 group elements — far past what a
rendered prompt would reasonably hold — and it still falls in seconds. There is
no window between "small enough to pose" and "large enough to resist the DP".

### Scope of the rejection

This is not a statement about one preset. The obstruction is that the paper's
invariant *pins the witness length to \(|G|=2n\)*, so any faithful instance must
supply \(\Theta(n)\) terms, which makes the modulus polynomial in the input and
the residue DP always affordable. Escalating \(n\), crowding the sequence with
decoys, or tuning how near the plant sits to the \(\mathsf E(G)\) boundary all
leave that exponent unchanged. The family fails **H** for every regime the paper
establishes, so there was nothing for the hardening loop to be run against.

The builder's note on the workaround is endorsed: taking a modulus exponentially
larger than the term count and dropping the cardinality constraint does yield a
hard planted modular subset-sum, but the hardness would come from subset-sum, not
from \(\mathsf E(G)=3n\) or the inverse classification. That would credit this
paper with a hard regime it does not state.
