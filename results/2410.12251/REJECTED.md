# Rejected at Step 0: the proposed planted orbit is an easy average-case regime

Paper: Omkar Baraskar, Agrim Dewan, Chandan Saha, and Pulkit Sinha,
[*NP-hardness of testing equivalence to sparse polynomials and to constant-support
polynomials*](https://arxiv.org/abs/2410.12251), arXiv:2410.12251v1.

## Decision

No generator is shipped. The proposed family—sample a sparse polynomial, hide it
with a random invertible affine change of variables, and ask for a sparsifying
map—passes **G** and **V**, but it cannot support an honest **Track A** hardness
claim. The paper explicitly warns that equivalence testing for random sparse
polynomials has a randomized efficient algorithm, and the cited result recovers
the affine transformation rather than merely deciding existence.

The paper's worst-case NP-hardness theorem does not repair this: it is a reduction
from arbitrary 3-SAT instances and says nothing about the distribution produced by
random planting. A different generator based on satisfiable instances of that
reduction would need an independently justified hard distribution. The paper does
not supply one.

Track B also does not fit the proposed construction. Its known route is the
vector-space-decomposition equivalence algorithm itself; the paper supplies no
short, no-tool route from the displayed polynomial to the affine witness. Making
the planted transform visibly structured would invent a new leakage-based puzzle,
not extract a family justified by this paper. Accordingly, implementation stopped
before Steps 1--4, as the task requires after a Step-0 failure.

## What the paper actually proves

Problem 1 in Section 1.3 defines `ETsparse`: given a polynomial `f` in sparse
coefficient/exponent representation and an integer `s`, decide whether some
`A` in `GL(n,F)` and `b` in `F^n` make `f(Ax+b)` have at most `s` nonzero
monomials.

Theorem 1 gives deterministic polynomial-time many-one reductions from 3-SAT to
this problem over every field, both for general and homogeneous input
polynomials. Section 3 constructs the polynomial from a 3-CNF formula. Its forward
direction maps a satisfying assignment to a sparsifying matrix with entries in
`{-1,0,1}`; its reverse direction recovers a satisfying assignment from any
sufficiently sparsifying matrix. This is a **worst-case** result.

Theorem 4 and Section 6 give the analogous result for translations alone. For the
characteristic-zero construction, Proposition 6.1 writes the witness explicitly:
`b[x_0]=0` and `b[x_i]=(-1)^{u_i}` for a satisfying assignment `u`. Proposition
6.2 proves the converse. Thus an answer-first SAT construction would satisfy G,
and exact expansion/counting would satisfy V, but finding the shift is exactly the
planted SAT search problem selected by the generator.

Most importantly, the fourth remark following Theorem 1 identifies the easy
average-case regime. It cites Baraskar--Dewan--Saha, *Testing Equivalence to Design
Polynomials* (STACS 2024), for a randomized efficient equivalence test for random
sparse polynomials, even with only black-box access. The paper defines a random
sparse polynomial by forming every degree-`d` monomial through independent uniform
variable choices; coefficients may be arbitrary.

The cited paper's Theorem 3 is constructive. For `d >= 3t` (and the stated field
conditions), it runs in `poly((nd)^t)` field operations and outputs a matrix that
maps the input to a design polynomial. Its Remark 7 and Lemma 36 show that random
sparse polynomials are design polynomials with high probability in their stated
parameter range. It even uses the result to recover hidden affine transformations
in a cryptographic application. That is precisely the certificate-recovery attack
the proposed random-affine generator would have to defeat.

## Step-0 discriminating test

**What algorithm produces the certificate, and what does it cost?**

For the proposed random-sparse target distribution, the answer is the randomized
design-polynomial equivalence algorithm: `poly((nd)^t)` field operations (and
polynomial bit complexity over the rationals), under `d >= 3t` and the accompanying
random-design and field-size conditions. It outputs a valid affine map up to the
unavoidable permutation/scaling symmetries. Therefore its output is both the
requested witness and a disqualification from Track A.

Avoiding those parameter conditions does not turn the worst-case theorem into an
average-case theorem. It merely leaves the generated distribution without a
hardness basis.

## Why the remaining paper families do not rescue the task

### Use the paper's 3-SAT reduction directly

Sampling a satisfying assignment first and then sampling clauses satisfied by it
would be valid inverse generation. However, Theorems 1 and 4 transfer only
worst-case NP-hardness. They do not state that random planted 3-SAT—or any
particular answer-first distribution—is hard. The reverse directions make the
issue transparent: recovering a sparsifying map recovers a satisfying assignment.
Claiming Track A would therefore repeat the forbidden inference from worst-case
NP-hardness to generated-distribution hardness.

One could import a separate cryptographic or average-case SAT assumption, but that
would be the hardness source, not a theorem in this paper. It would also require a
new adversarial analysis of planting artifacts and is outside the supplied paper's
evidence.

### Use a known easy special class as Track B

The introduction and related-work section list efficient equivalence tests for
power-symmetric, sum-product, read-once, and constant-`t` design polynomials. These
would honestly provide a Track B reference algorithm. But the actual recovery
method uses high-order derivatives, adjoint algebras, generalized eigenspaces, and
factor recovery. The paper does not expose a compact route of at most 300 exact
operations that a no-tool solver could execute after one structural insight.
Specializing further until such a route is visible would make the affine map
recoverable by an obvious coefficient, factorization, or symmetry attack, defeating
the required four failing in-context attacks and the hinted G9 gate.

### Ask only for verification data

Substituting a proposed affine map and collecting equal exponent vectors is exact
and polynomial in the explicitly expanded output size. This makes the affine map a
valid witness, so V is not the problem. Returning the sparsified polynomial as
well, or changing the certificate to a monomial list, does not change the recovery
algorithm and cannot create H.

## Gate outcome

| requirement | result |
|---|---|
| G — answer known by construction | Would pass: sample the sparse polynomial and invertible affine map first |
| H — claimed hardness for the generated distribution | **Fails: the natural random-sparse regime has a constructive randomized equivalence algorithm; outside it the paper supplies only worst-case hardness, not distributional hardness** |
| V — exact witness checking | Would pass: exact affine substitution, coefficient collection, invertibility, and monomial counting |
| Track A | **Rejected** |
| Track B | **Rejected: no paper-backed compact no-tool route distinct from the mechanical recovery algorithm** |

No `gen_2410_12251.py`, `selftest_report.json`, `README.md`, or oracle transcript
was created. Running `scripts/harden.py` could only measure whether a few language
models implement the known attack; it could not override the algorithmic Step-0
failure.
