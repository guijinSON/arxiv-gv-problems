# Rejected at Step 0: certificate search is either conic optimization or the displayed construction

Paper: Amir Ali Ahmadi, Sanjeeb Dash, Yixuan Hua, and Bartolomeo
Stellato, [*Disjunctive Sum of Squares*](https://arxiv.org/abs/2605.28674),
arXiv:2605.28674v1 (2026).

## Decision

No generator is shipped. The prior-triage proposal—sample a disjunctive SOS
identity and publish its expanded polynomial—passes **G** by inverse generation
and **V** by exact expansion, but it does not pass **H on either track**.

- **Track A fails.** For a fixed algebraic disjunction and degree, Section 2
  explicitly reduces certificate search to semidefinite programming of size
  polynomial in the number of variables. The local construction in Section 3
  has an SOCP refinement, and Section 4's coefficient certificates are found by
  explicit substitution (or imposed by an LP). More fundamentally, the paper's
  NP-hardness observation concerns general polynomial nonnegativity, not the
  answer-first distribution proposed here. Inverse planting does not transfer
  worst-case hardness to that distribution.
- **Track B also fails.** If the planted factors are generic and hidden, the only
  solver-visible route is the same SDP/SOCP recovery problem; the generator's
  private factors are not an insight available from the instance. If the
  construction from the proof of the local Positivstellensatz is exposed, that
  proof itself gives a short coefficient-allocation/diagonal-dominance
  algorithm. The mechanical and compact routes are then the same route, so
  there is no no-tool compression gap.

This is an H failure, not a witness-rule failure. A rational weighted-SOS list
would be a finite concrete witness, and a checker could verify every identity
with exact rational polynomial arithmetic. Steps 1--4 were therefore not run:
there is no `gen_2605_28674.py`, self-test report, README, or oracle transcript.

## The exact paper object

Section 2, Definitions 1 and 2, defines an algebraic disjunction

\[
\mathbb R^n=\bigcup_{k=1}^r
\{x:q_{k,j}(x)\geq0\text{ for }j=1,\ldots,n_k\}
\]

and says that a polynomial `p` is SOS of order `dbar` with respect to it when,
for every region `k`, there are SOS polynomials satisfying

\[
p=s_{k,0}+\sum_j s_{k,j}q_{k,j},
\qquad
\deg s_{k,0}\leq\bar d,
\quad \deg(s_{k,j}q_{k,j})\leq\bar d.
\]

These are the native objects: rational polynomials, algebraic regions, and SOS
identities. No graph or finite-field surrogate is needed, and using one would
discard the paper's content.

The paper then supplies all of the relevant easy mechanisms:

- Immediately after Definition 2, Section 2 states that, for fixed `dbar`,
  affine optimization over this cone is an SDP of size polynomial in `n`.
- Section 2's alternating-maximization procedure alternates between two SDPs.
  For the Motzkin examples it converges in fewer than 20 iterations, followed
  by rational coefficient polishing; the section also prints the resulting
  certificates.
- Section 3, Theorem 1 (the Disjunctive Positivstellensatz), gives an explicit
  family of disjunctions. Its local Theorem 2 and Lemma 3 construct the Gram
  representation by assigning polynomial coefficients to a matrix and adding
  a diagonal matrix until it is diagonally dominant. The remark following the
  local theorem identifies the result as scaled diagonally dominant SOS and
  states that the search can be performed by an SOCP.
- Section 3.3, Algorithm 1, is a complete hierarchy of fixed-size SDPs. Theorem
  7 gives convergence of its lower bounds, and the text gives `O(1/epsilon)`
  hierarchy iterations for tolerance `epsilon`.
- Section 4, Definition 4 and Theorem 8 (the Optimization-Free Disjunctive
  Positivstellensatz), replace SOS search by the explicit test that every
  coefficient of `p(V_k x)` is nonnegative. The paper states that checking is
  optimization-free and imposing the condition is an LP.
- Section 5.2 specializes the construction to disjunctive `P+N`
  decompositions for copositive matrices, again semidefinite representable.
  Section 6 then uses those SDPs inside spatial branch-and-bound.

Thus the paper supplies valid certificates and complete ways to obtain them;
it does not supply a hard answer-first distribution.

## Step-0 mechanical-cost and compact-route comparison

The following counts use a representative would-be shipping point of eight
variables, degree four, and two regions, large enough that a generic conic
calculation is not plausible by hand while a sparse answer could still fit the
2,000-character/256-atom cap.

For a nonhomogeneous quartic SOS, the degree-at-most-two monomial basis has

`C(8+2,2) = 45`

members, so its symmetric Gram matrix has `45*46/2 = 1,035` scalar entries. If
the region polynomial is quadratic, its degree-two SOS multiplier uses the
nine degree-at-most-one monomials and has another `9*10/2 = 45` Gram entries.
Consequently the two-region formulation has **2,160 scalar Gram variables** and
**990 coefficient equations** (`2*C(8+4,4)`). Even ignoring PSD-cone work, two
dense 495-by-495 normal-equation Cholesky factorizations cost approximately

`2 * 495^3 / 3 = 80,858,250`

scalar multiply-adds **per interior-point iteration**. The paper's alternating
scheme may require many such SDP solves; its displayed examples report fewer
than 20 outer iterations, not one arithmetic step. This is the relevant
mechanical cost for generic fixed-disjunction recovery.

There are then only two possible purported compact routes:

| Proposed family | Mechanical cost | Compact route length | Track-B result |
|---|---:|---:|---|
| Generic inverse-planted identities | At least the same 2,160-variable conic feasibility problem; about 80,858,250 dense normal-equation operations per Newton step at the representative point | **No separate route**: recovering the hidden planted factors is precisely the conic feasibility problem, so the shortest paper-backed route has the same cost (ratio 1) | Fail: private generator randomness is not a solver-visible insight |
| Section 3 local certificate, using the proof's diagonally dominant Gram allocation | One coefficient pass, row-absolute-sum updates, and the standard binomial-square decomposition of a diagonally dominant matrix | **The identical pass**. In any sparse specialization that meets the 300-operation intended-route cap, both routes use at most 300 exact operations (again ratio 1) | Fail: there is nothing to compress; hiding this cheaper algorithm and quoting the generic SDP would make the Track-B declaration dishonest |
| Section 4 coefficient certificate | Expand each `p(V_k x)` and check coefficient signs | **The identical substitutions and sign checks**; no shorter invariant is proved | Fail: below 300 operations it is directly executable, and above 300 it violates G9(c) unless a different shortcut is invented |

The large first number therefore does **not** rescue Track B. A large mechanical
route is useful only when the instance exposes a much shorter structural route.
Here, generic planting exposes none. The only paper-backed shortcut is the
explicit proof construction, and once that construction applies it is already
the cheapest mechanical algorithm.

## Why the inverse generator is not structurally hard

Sampling SOS summands first and expanding them changes only how the builder
learns the witness. It does not establish how a solver should recover it, nor
does it put the resulting distribution in a hardness regime proved in the
paper. The sentence in Section 3 preceding the subregion-bound Theorem 6 that
invokes NP-hardness of polynomial nonnegativity is a worst-case observation
used to explain an exponential region bound. It is not an average-case theorem about polynomials
conditioned on possessing a sampled sparse disjunctive certificate.

The natural way to manufacture a visible shortcut would be to restrict the
sampled squares to a recognizable symmetry, factor pattern, or disclosed
change of variables. That would be a new puzzle engineered by the benchmark,
not a compact route supplied by this paper. It would also need fresh evidence
against factor-pattern, coefficient-outlier, and obvious-ansatz attacks. The
paper provides no theorem supporting such a distribution.

## Other native witness formulations considered

| Candidate task | G | H | V | Outcome |
|---|---:|---:|---:|---|
| Recover all SOS multipliers for a fixed disjunction | Pass by inverse planting | **Track A fails:** SDP; **Track B fails:** no distinct compact route | Pass by exact expansion and nonnegative weights | Rejected |
| Produce the Section 3 local SOS identity | Pass by the theorem proof | **Fails:** the proof's coefficient/Gram construction is itself the direct algorithm | Pass by exact expansion | Rejected |
| Return transformed polynomials `p(V_k x)` with nonnegative coefficients | Pass by choosing `p,V_k` first | **Fails:** explicit substitution produces the answer | Pass by substitution and sign checks | Rejected |
| Return disjunctive `P+N` matrices for copositivity | Pass by inverse construction | **Fails:** fixed-disjunction search is an SDP; generic planting has no compact route | Pass by exact matrix equality, PSD certificate, and entrywise signs | Rejected |
| Return an exact global minimum from Algorithm 1 or spatial branch-and-bound | Not by the proposed inverse construction | Not reached | The paper's numerical tolerance output is not an exact witness without an added exact primal-dual or algebraic certificate | Rejected |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known by construction | Possible in isolation | Sample rational SOS pieces and expand, or use the constructive local theorem |
| H — Track A structural hardness | **Fail** | Fixed-disjunction recovery is SDP/SOCP/LP, and no distributional hardness theorem covers inverse planting |
| H — Track B no-tool compression | **Fail** | Generic plants have no public compact route; constructive plants have a compact route of the same length as their mechanical algorithm |
| V — exact witness checking | Possible in isolation | Expand rational weighted squares and compare every coefficient exactly |
| Overall | **Rejected at Step 0** | G, H, and V cannot be made to hold simultaneously using a family justified by this paper |

No G1--G9 measurements or oracle failures were fabricated after the analytical
H failure. In particular, an oracle's inability to carry out an SDP in its head
would not turn a hidden random factorization into a Track-B insight problem.
