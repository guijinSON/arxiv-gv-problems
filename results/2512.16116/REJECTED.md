# Rejected: arXiv:2512.16116

Paper: [Rota-Baxter operators on braces, post-braces and the Yang-Baxter equation](https://arxiv.org/abs/2512.16116)

## Decision

No problem family from this paper clears **H**, on either track, while remaining in the paper's native objects. The paper does support inverse/theorem-backed generation (**G**) and exact substitution checking (**V**), but it supplies no hard parameter regime and its only concrete operator-search regime is completely classified by a constant-size calculation.

## The native candidate and why it fails

The strongest candidate suggested by the paper is: hand the solver the two-sided brace on the three-dimensional Heisenberg Lie algebra from Example 5.1 and ask for a matrix of a Rota-Baxter operator satisfying Definition 4.2. A generator could sample one of the matrices in Example 5.2 and then omit it from the instance. A checker could verify the two defining identities exactly over the rationals by coefficient comparison. Thus this candidate clears G and V.

It does not clear hardness:

- With no extra side conditions, the zero matrix is always a valid answer. Even requiring a nonzero answer does not help: Example 5.2(i) immediately gives a central rank-one map, for example `B31 = 1` with every other entry zero.
- Example 5.2 is a complete classification. Writing `a=B11`, `b=B12`, `c=B21`, `d=B22`, and `t=B33`, the paper's displayed identity reduces validity to `B13=B23=0` and four scalar coefficient equations. With `delta = a*d-b*c`, these are `t*b=0`, `t*c=0`, `delta=t*(1+2*a)`, and `delta=t*(1+2*d)`. This is also an executable exact checker.
- Enhanced operators are even easier: Example 5.2 proves that their only possibly nonzero entries are the two free central entries `B31,B32`.
- The other obvious witnesses are displayed directly. Proposition 2.18 constructs the relative Rota-Baxter operator as the identity map of a post-brace; Theorem 2.26 gives both Yang--Baxter solutions and their Drinfel'd isomorphism by formulas; Example 5.4 specializes those formulas explicitly; and Theorem 4.9 factors `a` using `B_+(a)=a circ B(a)` and `B(a)`. Asking for any of these merely asks the solver to evaluate the displayed construction.

Adding enough planted linear constraints to single out a sampled matrix would move the search into an artificial fixed-size linear system, not a hard regime established in the paper. Taking direct products or hiding the three-dimensional example by a growing change of basis would likewise be an extrapolation: the paper proves neither distributional hardness nor a compact recovery invariant for that construction. If the basis change is supplied, applying it is the mechanical route; if it is not supplied, finding it is an added decomposition problem unsupported by the paper.

## Track A audit

**Fails H on Track A.** The paper contains structural equivalences and constructions, not a complexity or average-case hardness theorem. In particular, there is no theorem and growing parameter regime supporting the required claim that the generated distribution resists known efficient general methods. The only fully worked search space is the fixed `3 x 3` classification in Section 5, Example 5.2.

## Track B audit: measured operation gap

**Fails H on Track B as well.** The mechanical and compact routes are too close to test no-tool compression.

| route | exact work in the paper's concrete regime |
|---|---:|
| Mechanical coefficient matching | 11 arithmetic operations to form `delta`, the two products `t*b,t*c`, and the two right-hand sides, plus 6 equality/zero comparisons |
| Compact route using Example 5.2 | 0 arithmetic operations for the zero or nonzero-central witness; at most 3 arithmetic operations plus one quadratic square-root choice in the `t != 0` classes |
| Generic linear side constraints (if artificially added) | Gaussian elimination in at most 9 unknowns, bounded by `9^3 = 729` elimination updates; the planted constraints, not the paper, would create this work |

Coefficient height can make the numerals longer, but it does not increase the number of unknowns or identities. Consequently there is no shipping size at which the standard method costs anything like a large mechanical computation while a short structural route remains. Both routes are constant-size, and the easiest admissible witness is immediate.

## Gates

- **G — would pass:** sample a classified matrix from Example 5.2, use Proposition 2.18, or use the formulas in Theorem 2.26/Example 5.4.
- **H — fails (A and B):** no hard distribution is established; the native concrete search is a fixed complete classification with immediate witnesses and an 11-operation exact test.
- **V — would pass:** coefficient matching exactly verifies the defining identities over rational inputs.

Because H fails at Step 0, no generator, oracle hardening run, or self-test report was produced.
