# Rejected: arXiv 2512.19313

Paper: Claude Carlet and Alexander Kholosha, [“Results on cubic bent and weakly regular bent p-ary functions leading to a class of cubic ternary not weakly regular bent functions”](https://arxiv.org/abs/2512.19313).

## Decision

This paper does not yield a problem family satisfying G, H, and V simultaneously. I read the full 31-page paper and its LaTeX source, including the exact definitions in Section 2, the cubic-like characterization in Section 3, the Walsh-derivative identities in Section 4, and the main construction and its proofs in Section 5. No generator module or hardening transcript was produced because the task explicitly requires stopping when the family fails a gate.

The prior-triage proposal—instantiate a constructed p-ary polynomial and ask for a bent function—fails **H**. Section 5's main trinomial theorem explicitly constructs

\[
F(x)=\operatorname{Tr}^{4k}_k\!\left(x^{3^k+2}-x^{2\cdot3^k+1}
+\zeta^{t(3^k+1)/2}x^{3^j+1}\right)
\]

whenever `n = 4k`, `j` has parity opposite to `k`, and `t` is odd. It also proves that every nonzero component is cubic, bent, and not weakly regular. Producing such a polynomial is therefore a direct evaluation of the displayed construction, not a hard witness search. Sampling the coefficients first does not repair this: the solver can reproduce the same formula in polynomial time.

## Candidate witness searches considered

| Candidate task | Gate failure | Reason |
|---|---|---|
| Output a bent/non-weakly-regular member of the trinomial class | H | The main theorem in Section 5 is an explicit closed-form construction in the full admissible parameter regime. |
| Given a nonzero direction `c`, output `d` for which the second derivative is a nonzero constant | H | Section 3 proves this is equivalent to bentness for cubic functions. For fixed `c`, the nonconstant coefficients of `D_{c,d}f` are linear constraints in `d`; after solving them by finite-field linear algebra, the remaining constant is a degree-at-most-two form. The Section 5 proof goes further and supplies suitable subspaces/case formulas for `d`. This is polynomial-time algebra, not exponential search. |
| Output a full cubic-like certificate (one `d` for every nonzero `c`) | V / witness size | It contains exponentially many directions in the succinct dimension parameter, so the witness and checker are exponential-size. |
| Output or verify a Walsh spectrum / bentness claim | V | Direct exact Walsh evaluation enumerates the entire field (and all coefficients for a full check). That is exponential in `n`. In the regimes where Sections 4–5 provide symbolic Walsh formulas, verification becomes a theorem/formula lookup and again fails H. |
| Find a component that is not weakly regular | H | The Section 5 theorem says every nonzero component has this property, so any nonzero component coefficient is a valid answer. |
| Recover the dual in the paper's explicit cases | H | Section 5 derives the Walsh transform and dual explicitly for odd `k` with `j` equal to `0` or `2k`, including concrete coordinate formulas and examples. |
| Invert the constructed vectorial map | H not supported | The paper makes no one-wayness or preimage-hardness claim. Its map has a `4k`-dimensional domain and `k`-dimensional codomain, and the explicitly analysed odd-`k` cases are transformed to a Maiorana–McFarland form containing the term `x_0 x_3`, which exposes direct algebraic preimage choices before any extra constraints. Adding a random affine slice could create a generic-looking polynomial-system problem, but that would be a new hardness construction not established by this paper. |

## Easy regimes and why they matter

Section 2 states that original Maiorana–McFarland functions are bent exactly when their defining map is a permutation, already an efficient structural criterion. Its concatenation constructions likewise manufacture bent functions from supplied bent functions and permutations. Section 3's cubic-like theorem is an exact characterization for cubic functions, but its individual direction witnesses reduce to elementary finite-field algebra as described above. Section 5 places important odd-`k`, `j in {0, 2k}` components inside a particular Maiorana–McFarland concatenation form and calculates their Walsh transforms. These are precisely the regimes that would make a generated search instance easiest, not hardest.

The paper contains no NP-hardness result, no average-case hardness result, and no parameterized-hardness result for any associated witness search. It is a construction-and-classification paper: its substantive achievement is proving properties of explicitly given functions. Turning those properties into an allegedly hard benchmark would confuse mathematical proof complexity or exponential truth-table evaluation with a hard, cheaply checkable witness problem.

## Gate outcome

| Gate | Outcome |
|---|---|
| G — inverse-generatable | Possible for several artificial formulations |
| H — no known polynomial/closed-form solution | **Failed** for paper-native construction and derivative witnesses; unsupported for an invented preimage restriction |
| V — cheap exact checking | **Failed** for bentness/Walsh-spectrum certificates; possible only for preimages, whose hardness is not supplied by the paper |

Accordingly, the family is rejected before implementation and before the LLM hardening loop. No empirical oracle failure can substitute for the missing H justification, and running the loop on a knowingly invalid family would not make it acceptable.
