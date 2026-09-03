# Rejected: arXiv 2605.28674

Paper: Amir Ali Ahmadi, Sanjeeb Dash, Yixuan Hua, and Bartolomeo
Stellato, [*Disjunctive Sum of Squares*](https://arxiv.org/abs/2605.28674)
(2026).

## Decision

The prior-triage proposal—sample disjunctive sum-of-squares identities, expand
them into a polynomial, and ask a solver to recover a certificate—fails
requirement **H (hard)** in the paper's defined certificate regime. Once the
algebraic disjunction and degree bound are part of the instance, the paper
explicitly reduces certificate search to semidefinite programming. Its main
results then provide complete constructive families of such disjunctions; one
refinement is searchable by second-order cone programming, and another needs
only coefficient checks or a linear program.

I therefore stopped at Step 0. No generator, self-test report, README, or
hardening transcript was created. Random-guess and LLM failures cannot turn a
problem with a standard convex-optimization solution into a hard witness
family.

## Exact definition from the paper

Section 2 defines an algebraic disjunction

\[
\mathcal D=\{\{q_{k,j}\}_{j=1}^{n_k}:k=1,\ldots,r\}
\]

by requiring the basic closed regions

\[
\Omega_k=\{x:q_{k,j}(x)\geq 0\text{ for every }j\}
\]

to cover all of \(\mathbb R^n\). A polynomial \(p\) of degree at most \(d\)
is SOS of order \(\bar d\) with respect to \(\mathcal D\) precisely when, for
every region \(k\), there are SOS polynomials \(s_{k,j}\) satisfying

\[
p=s_{k,0}+\sum_{j=1}^{n_k}s_{k,j}q_{k,j},\qquad
\deg s_{k,0}\leq\bar d,\quad
\deg(s_{k,j}q_{k,j})\leq\bar d.
\]

Thus a valid witness would have to include an SOS representation of every
multiplier and make every displayed polynomial identity hold exactly. With
explicit rational or integer summands, this is cheaply verifiable by expansion
and coefficient comparison, so **V is possible**. Sampling those summands
before expansion also makes **G possible**. Neither fact supplies H.

## The fatal standard algorithm

Immediately after Definition 2, the paper states that, for fixed \(\bar d\),
linear optimization over this cone is carried out by an SDP of size polynomial
in \(n\). In particular, when \(p\), \(\mathcal D\), and the degree bounds are
given, the unknown Gram matrices of the SOS multipliers occur linearly, and
coefficient matching gives linear equality constraints. Certificate recovery
is therefore the standard SOS semidefinite-feasibility problem—not an
exponential search through the planted coefficient lists. The SDP even splits
into one independent problem per subregion.

For fixed degree \(d\), the monomial vector used by a degree-\(d\) SOS Gram
matrix has \(\binom{n+d/2}{d/2}\) entries, polynomial in \(n\). Increasing the
number of variables while retaining the paper's fixed-degree regime therefore
does not evade the algorithm. Letting the degree grow only makes the explicit
polynomial/Gram representation itself grow and is not a hardness result for a
new planted distribution.

The later results make the obstruction stronger:

- Theorem 1 in Section 3 gives, for every fixed dimension and even degree, an
  **explicit** family \(\mathcal D^m\) such that every positive-definite form
  eventually has an order-\(d\) certificate.
- The local construction in Theorem 2 and Lemma 3 builds the certificate by
  adding a sufficiently large diagonal Gram contribution. The remark after
  Theorem 2 observes that the resulting certificate is scaled diagonally
  dominant in a rotated basis, so it can be found by an SOCP.
- Algorithm 1 searches the fixed spherical-cap disjunctions by independent
  SDPs and is complete to any requested optimization tolerance; Theorem 7
  supplies its convergence rate.
- Section 4's Definition 4 and Theorem 8 give an optimization-free alternative:
  after explicit linear changes of coordinates, certificate checking is just
  nonnegativity of coefficients. Imposing the condition is a linear program.
- Section 6 supplies adaptive spatial branch-and-bound algorithms rather than
  a hard search regime. The numerical section reports that the tested
  non-SOS polynomials need only a modest number of regions in nearly every
  case.

These are exactly the easy/search-direct results that an inverse generator
would have to avoid, but the paper gives no separate hardness theorem for
recovering a planted disjunctive SOS identity.

## Why hiding the disjunction does not repair H

Section 2 also considers jointly searching for the partitioning polynomials
and SOS multipliers. That formulation is bilinear and the paper proposes an
alternating SDP heuristic, but it proves no NP-hardness, average-case hardness,
or hard parameter regime for this joint search. Manufacturing a bounded-
integer decomposition puzzle by hiding \(\mathcal D\) would add constraints
not present in the definition and would rest H entirely on an unsupported
planted distribution. It would also change the standard domain attack from
the paper's fixed-disjunction SDP to an invented nonlinear factorization
problem.

Conversely, rendering \(\mathcal D\) is necessary for a self-contained cheap
checker to know that its regions really cover \(\mathbb R^n\). Checking that
an arbitrary solver-supplied collection of polynomial inequalities covers all
of \(\mathbb R^n\) is itself a quantified nonnegativity problem, not the
required cheap substitution/expansion verification. Restricting the answer to
syntactically covering sign disjunctions fixes V but still has no hardness
support in the paper.

The continuous non-unique Gram/square parameterization also makes a naive
coefficient-box `search_space` and random-guess experiment artificial: the
paper defines real SOS polynomials, not a finite coefficient alphabet. Adding
such an alphabet solely to obtain G4 would create a different problem while
leaving the SDP relaxation as the mandatory first attack.

## Other paper-native candidates considered

- **Certify polynomial nonnegativity or matrix copositivity.** Sections 3 and
  5 note NP-hardness, but the positive statement is universal. The paper's
  finite certificates are precisely the SDP/LP-generated objects above.
  Asking for the optimum of a polynomial or quadratic program would also
  violate the rule against answers whose optimality is the claim.
- **Find a point disproving copositivity.** A rational nonnegative point with
  \(x^TQx<0\) would be a cheap witness, but the paper supplies no answer-first
  hard distribution of non-copositive matrices. Making one by placing a
  negative direction in \(Q\) normally exposes that direction spectrally or
  through continuous quadratic optimization.
- **Find a clique.** Section 6.3.2 uses the Motzkin--Straus/copositive
  formulation to *compute the clique number* of four \(G(75,0.5)\) graphs and
  solves all four with few subregions. General CLIQUE is hard and a clique is
  verifiable, but planting a hidden clique would introduce a planted-clique
  distribution whose average-case hardness is neither proved nor studied in
  this paper. Its required standard attacks would be spectral and SDP methods,
  exactly the methods that commonly expose planted cliques.
- **Return the paper's lower/upper bound or convergence rate.** These are
  numeric/optimality claims, not structured witnesses allowed by the task.

## Gate outcome

| requirement | result | evidence |
|---|---:|---|
| G — answer-first generation | possible | sample square summands and expand the identities |
| H — no polynomial-time or closed-form method | **fail** | fixed-disjunction recovery is an SDP; the paper also gives SOCP, LP, and explicit complete constructions |
| V — cheap exact verification | possible | expand submitted squares/products and compare all coefficients |
| Overall | **rejected** | all three requirements must hold simultaneously |

No G1–G8 measurements or oracle calls were run after this analytical H
failure. Doing so would manufacture evidence for a family the paper itself
equips a solver to recover.
