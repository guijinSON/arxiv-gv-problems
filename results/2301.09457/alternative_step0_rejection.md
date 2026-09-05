# Superseded Step-0 alternative: why the final family is Track B

This was the initial rejection analysis. It remains as an audit trail for the
native formulations that were considered, but it is **not** the final decision.
The finished module found a Track B gap by composing Theorem 6.1's native
trifference-coordinate identity with a missing-row Walsh construction: generic
finite-field elimination is mechanical, while the solver-visible invariant is
compact. The authoritative status and caveats are in `README.md`.

Paper: Anurag Bishnoi, Jozefien D'haeseleer, Dion Gijswijt, and Aditya
Potukuchi, [*Blocking sets, minimal codes and trifferent
codes*](https://arxiv.org/abs/2301.09457), arXiv:2301.09457v3 (2024).

## Decision

No generator is shipped. The prior-triage proposal--construct a finite-field
code or blocking set from an algebraic recipe and ask for an incidence/code
certificate--cannot make **G, H, and V hold simultaneously** for a family
supported by this paper.

- **Track A fails H.** The paper proves extremal size bounds and equivalences,
  not computational or distributional hardness. Its explicit blocking-set
  constructions have direct linear-algebraic local witness algorithms. Its
  probabilistic construction proves only that some random choice works; a
  generator cannot know that a sampled choice is blocking without performing
  the global search it is meant to avoid. General hypergraph-cover or
  code-minimality hardness would not establish hardness for an inverse-planted
  distribution.
- **Track B also fails H for every scalable native witness found.** On the
  tetrahedron construction, both the standard mechanical method and the
  shortest route reduce to the same scan for two independent columns followed
  by one 2-by-2 finite-field solve. On the displayed `[24,6]_3` trifferent code,
  the standard method is a scan of only 24 columns. Enlarging the concatenated
  construction makes that scan long, but the paper supplies no shorter public
  invariant for locating a separating coordinate; a coordinate privately
  planted by the generator would not be a solver-visible compact route.
- **The optimization formulation does not rescue either track.** Section 6.3
  finds the small values by ILP and reports that Gurobi handles `k <= 5` in a
  few minutes but not `k=6`. A feasible blocking set is not a certificate of
  optimality, and the paper provides no bounded branch-and-bound, dual, or
  algebraic certificate that the requested checker could verify cheaply. For
  the already computed small cases, the displayed table/matrix is a finite
  lookup rather than an unlimited hard family.

This is primarily an **H failure on both tracks**, with a separate **G failure**
for the random-existence construction and a **V failure** for optimum claims
without an executable optimality certificate. It is not `cap_bound`: the most
promising fixed-size witnesses fit comfortably, but their direct algorithms
are already short. Steps 1--4 were not run, and no module, self-test report, or
oracle transcript was fabricated.

## The paper's exact native objects

The definitions and equivalences that control the decision are these:

- Section 1 defines an affine `s`-blocking set in `F_q^k` as a set meeting
  every affine subspace of codimension `s`.
- Definition 2.12 calls a projective point set strong blocking when its
  intersection with every hyperplane spans that hyperplane.
- Definition 2.11 calls a linear code minimal when no nonzero codeword support
  properly contains the support of another nonzero codeword. Theorem 2.15
  identifies nondegenerate minimal codes with strong blocking sets formed by
  the projective columns of a generator matrix.
- Lemma 1.2 (proved as Lemma 2.21 in the body) says that a projective strong
  `(s-1)`-blocking set becomes an affine `s`-blocking set after taking the
  union of its vector lines through the origin.
- Section 6 defines a ternary linear trifferent code: every three distinct
  codewords have a coordinate containing all of `F_3`. Theorem 6.1 identifies
  this with a symmetric affine 2-blocking set formed from the generator
  columns, and Theorem 6.2 identifies it with code minimality.

These are already finite-field vectors, matrices, subspaces, and codewords.
No graph, SAT, or integer-coordinate surrogate is necessary or justified.

## What produces each possible certificate

### 1. The probabilistic upper-bound construction does not give G

Theorem 1.1, Section 3, samples `m` independent `s`-dimensional linear
subspaces through the origin. The proof bounds the expected number of missed
codimension-`s` affine subspaces below one, so **there exists** a successful
sample. It does not say that every sample succeeds and does not output which
sample does.

A Las Vegas generator that samples until exhaustive incidence testing says the
union is blocking would obtain its answer by solving the generated instance.
At dimension `k`, direct certification requires considering the

`(q^s - 1) * GaussianBinomial(k,s,q)`

codimension-`s` affine subspaces not through the origin. Supplying a complete
incidence map as the witness would scale with that same exponential list and
would fail the answer cap. Thus Theorem 1.1 is an existence theorem, not the
theorem-backed per-instance generator required by G.

### 2. The tetrahedron construction gives G and V, but its witness is easy

Section 5 calls the following construction "the tetrahedron": choose `k`
projective points in general position and take every projective line joining a
pair. In coordinates relative to those basis points, its affine image under
Lemma 1.2 is exactly the set of vectors supported on at most two coordinates.

Let a codimension-two affine subspace be presented exactly as

`A x = b` over `F_q`,

where `A` is a rank-two `2 x k` matrix. Because the columns of `A` span
`F_q^2`, some two columns `A_i,A_j` are independent. Solve

`[A_i A_j] [lambda, mu]^T = b`.

Then `x=lambda*e_i+mu*e_j` is in the tetrahedron union and in the requested
affine subspace. The checker needs only two exact row equations and a
two-support check, so V is excellent. But the algorithm producing the witness
is already the compact route: retain the first nonzero column, scan until a
nonparallel column is found, and solve one 2-by-2 system.

For a representative would-be shipping setting `q=2003`, `k=90`, a sparse
certificate `(i,j,lambda,mu)` has only four atoms. Even the language restricted
to two nonzero coefficients contains

`C(90,2) * 2002^2 = 16,052,056,020`

candidates, so naive uniform guessing is not the issue. An adversarial rank-two
matrix whose first 89 columns are parallel forces 89 determinant tests. Counting
two products and one subtraction per test, eight field operations for Cramer's
rule, and at most 13 Euclidean divisions for inversion modulo 2003 gives at most
**288 exact arithmetic operations**. A local CPython benchmark of 100,000 such
worst-position searches took **4.940641 seconds**, or **49.41 microseconds per
instance**.

The **mechanical cost is those same 288 operations** and the **compact route is
the same 288-operation algorithm**, for cost ratio 1. At random inputs an
independent pair normally appears immediately, making both routes about a dozen
field operations. Raising `k` merely lengthens the identical scan; above about
90 worst-position columns it also pushes the intended method beyond G9's
300-operation cap. Revealing an extra symmetry that singles out the pair would
shorten both routes and would be benchmark-invented structure, not a result of
this paper.

The full projective-space/simplex variant is no harder: the same two-column
solve produces a point. This one-sentence algorithm is the Step-0
discriminating test that rules out a Track A claim and leaves no Track B gap.

### 3. A separating coordinate of the explicit ternary code is too easy

Theorem 6.1 says that for two translated message differences `u,v` and a
generator column `g_j`, a trifferent coordinate is exactly a column satisfying

`{u^T g_j, v^T g_j} = {1,2}` in `F_3`.

The proof of Theorem 1.7 displays an explicit `6 x 24` generator matrix for a
`[24,6]_3` trifferent inner code. The standard algorithm is therefore to scan
the 24 columns and evaluate two length-six dot products. A full scan costs at
most **528 elementary field additions/multiplications** (two dot products,
each six products and five additions, at 24 columns), and often stops much
earlier. The compact route supplied by Theorem 6.1 is precisely that same
column test. Moreover, a coordinate answer has only 24 possible values, so its
guess probability is at least `1/24`, far above G4's threshold.

Row operations, coordinate permutations, or nonzero coordinate scalings carry
the known code and its certificate to an equivalent code, but they do not
create canonically new problem parameters or enlarge the 24-coordinate answer
space. Repetition enlarges the printed code while preserving the same constant
fraction of separating copies.

Theorem 1.7 concatenates this inner code with an algebraic-geometric outer code
to obtain an infinite sequence. A mechanical separating-coordinate scan is
linear in the concatenated length. The paper gives no compact locator for an
arbitrary triple beyond testing coordinates. Choosing a triple and one known
coordinate first would pass inverse generation, but the location would be
private generator state: the solver would still have only the scan. That is no
Track B route. Claiming Track A would be equally unsupported because the paper
contains no average-case hardness theorem for planted triples in concatenated
codes.

### 4. Constructing a whole code or blocking set violates either V or the cap

A solver could instead be asked to return an entire strong blocking set or
trifferent generator matrix. The explicit `6 x 24` inner matrix has 144 field
entries and fits, but it is printed verbatim in the proof of Theorem 1.7; its
row/column disguises are equivalent copies that a correct canonical key should
collapse. Scaling the dimension makes a literal generator matrix or point list
grow at least quadratically in the relevant coordinates and quickly exceeds
256 atoms.

A short macro naming the Section 5 construction is not by itself a witness.
The checker would have to expand it and verify the universal strong-blocking or
trifference property. Trusting Lemma 5.2, Theorem 5.1, or Theorem 1.7 without
executing their hypotheses would violate the witness rule. Exhaustively checking
all hyperplanes or all codeword triples is exponential in the dimension; the
paper does not provide a bounded symbolic certificate that compresses those
universal checks.

### 5. The ILP/table route supplies no admissible scalable optimum family

Section 6.3 formulates the minimum symmetric affine 2-blocking-set problem as a
binary ILP with one variable for every vector of `F_3^k` and constraints for
every codimension-two affine subspace, plus hyperplane lower bounds. The paper
states that Gurobi 10.0 found the values for `k <= 5` within a few minutes and
could not compute the exact value for `k=6`; it records only `22 <=
b_3^*(6,1) <= 24`.

This is not a Track A family: the only positive instances explicitly available
are a five-row table and the displayed 24-column construction. Nor is it Track
B: the paper gives no short insight that reproduces the branch-and-bound
optimum proof. A primal blocking set proves only feasibility, while the LP
relaxation dual generally proves only a fractional lower bound. The paper does
not ship a branch-and-bound transcript, cutting-plane proof, or another bounded
exact object meeting the witness rule. Consequently an optimum task fails G/V
at scalable parameters and becomes constant-size lookup at the parameters the
paper actually solved.

## Other native formulations considered

| Candidate task | G | H | V | Result |
|---|---:|---:|---:|---|
| Find a point where a tetrahedron blocking set meets a supplied codimension-two affine subspace | theorem-backed | direct `O(k)` rank-two solve; Track A false and Track B ratio 1 | two exact equations | **Reject on H** |
| Find a trifferent coordinate for three words of the displayed `[24,6]_3` code | transform known code/triple | 24-column scan; answer guessed with probability at least `1/24` | evaluate three symbols | **Reject on H/G4** |
| Use the random subspaces from Theorem 1.1 as a blocking set | not known without exhaustive testing | no distributional hardness theorem | global incidence scan is exponential | **Reject on G** |
| Return a whole explicit strong blocking set/minimal code | explicit for the displayed case | displayed construction or finite lookup | universal property is not cheaply executable at scale | **Reject on H/V/cap** |
| Return an optimum symmetric 2-blocking set | feasible set is available for small `k` | ILP/table, no Track A distribution or Track B shortcut | no exact integrality/optimality certificate supplied | **Reject on G/H/V** |
| Return a support-containment pair proving a planted code nonminimal | inverse generation | paper has no hardness theorem for that planted distribution; hiding the pair gives no compact route, exposing it is easy | exact codeword/support comparison | **Reject on H on both tracks** |

## Final gate disposition

| Requirement | Outcome |
|---|---|
| G -- certificate known by construction | Passes for the explicit tetrahedron and fixed displayed code; fails for a generic sample from Theorem 1.1 and for scalable optimum claims. |
| H -- Track A structural hardness | **Fails:** no theorem in the paper covers computational hardness of the generated distribution; the main local witness problems have elementary linear-algebra algorithms. |
| H -- Track B no-tool compression | **Fails:** tetrahedron intersection has identical mechanical and compact routes (288 versus 288 operations at the representative maximum); longer concatenated scans have no paper-supplied compact route. |
| V -- exact witness checking | Passes for local incidences and separating coordinates; fails for optimum/universal claims unless a prohibitively large exhaustive certificate is added. |
| Overall | **Rejected at Step 0.** No single paper-supported family clears G, H, and V together. |

The decisive sources are Lemma 1.2/Lemma 2.21, Definitions 2.11--2.13,
Theorem 2.15, the tetrahedron paragraph at the start of Section 5, Theorem 5.1
and Lemma 5.2, Theorems 6.1--6.2, the ILP and timing paragraph in Section 6.3,
and the displayed concatenated construction in the proof of Theorem 1.7.
