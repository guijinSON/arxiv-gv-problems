# Rejected: no supported hard certificate-search regime

Paper: Hao Shen, Junyu Guo, Junqi Liu, and Lihong Zhi,
[*Automated Tactics for Polynomial Reasoning in Lean 4*](https://arxiv.org/abs/2604.13514),
arXiv:2604.13514v1 (15 April 2026).

## Decision

No problem generator is shipped. The suggested ideal-containment/decomposition
task has **G (inverse generation)** and **V (exact verification)**, but this paper
does not establish **H (hardness)** for any parameter regime or generated
distribution. Moreover, the natural way to make the requested certificate a
bounded structured object makes recovery an ordinary linear-algebra problem over
the rationals.

This is a Step-0 rejection. Per the task instruction to stop when any of G, H, or
V fails, `gen_2604_13514.py`, `selftest_report.json`, and oracle-loop artifacts
were not created, and `scripts/harden.py` was not run. Random-guess and LLM
failures could not repair the missing mathematical hardness claim.

## What the full paper actually defines

The full LaTeX source and all nine pages of the paper were reviewed, not only the
abstract.

- Section 2.2 fixes the certificate representation: sparse multivariate
  polynomials with rational coefficients, serialized as coefficient/exponent
  lists and reified in Lean.
- Section 3 restricts the implementation to lexicographic order over
  `Q[x_0, ..., x_n]`.
- Section 3.1 gives the exact ideal-inclusion witness. For
  `I = <f_1, ..., f_n>` and `J = <g_1, ..., g_m>`, inclusion `I <= J` is
  certified by coefficient polynomials `c_ij` satisfying

  ```text
  f_i = sum_j c_ij * g_j
  ```

  for every `i`. Lean expands each identity and compares the resulting
  polynomials. Ideal equality consists of certificates for both inclusions.
- Section 3.2 similarly certifies a remainder using quotient polynomials,
  verifies a Groebner basis using Buchberger's criterion plus ideal equality,
  certifies ideal membership by an identity `f = sum_i c_i*s_i`, and certifies
  radical membership using an exponent together with an ordinary membership
  certificate for `f^n`.
- Sections 3.3 and 3.4 describe the search procedure actually supplied by the
  paper: `add_gb_hyp` computes a Groebner basis, and `gb_solve` obtains the
  relevant certificates through local SageMath, a SageMath API, or local SymPy.

The paper contains no complexity theorem, reduction, lower bound, benchmark,
FPT boundary, or claimed average-case hard distribution. Its statement that
`MvPolynomial` is non-computable and impractical for large symbolic computations
is about the Lean representation and motivates moving computation to a CAS; it
is not a hardness result for witness search. Indeed, Section 1 calls Groebner
bases an effective algorithmic framework for deciding ideal membership, and
Sections 3.2--3.4 implement that framework as the standard solver.

## Why the triaged decomposition generator fails

Suppose inverse generation first samples polynomials `c_1, ..., c_m` and
generators `g_1, ..., g_m`, then emits

```text
f = sum_i c_i * g_i.
```

This certainly knows a valid answer, and exact sparse expansion verifies it.
It does not yield a defensible hard family.

### Bounded certificates are linear algebra

A self-contained instance must pin down the witness shape. If it gives a degree
bound or an allowed monomial support for each `c_i`, put one unknown rational
coefficient on each allowed monomial, expand `sum_i c_i*g_i`, and equate its
coefficients with those of `f`. This is a linear system over `Q`. Gaussian
elimination returns some valid certificate in time polynomial in that explicit
coefficient system. The solver need not recover the planted certificate, and
crowding it with more rational solutions does not defeat this attack.

The same observation applies when only a total-degree bound is stated: enumerate
the permitted monomials and solve the resulting Macaulay-style linear system.
Choosing enough variables or a large enough degree can make that expanded system
large, but then apparent difficulty comes from an exponentially expanded search
basis rather than from a hard regime proved or studied by this paper. Relative to
the explicit matrix being solved, the standard attack remains polynomial.

Adding requirements such as minimum support, coefficients in a small finite set,
or a shortest decomposition could turn recovery into a combinatorial task, but
none of those constraints occurs in the paper. A shortest/minimum certificate
would also make optimality the claim, which the task expressly forbids.

### Unbounded certificates do not rescue the contract

If no degree/support bound is supplied, a certificate is an unbounded-length
object. The paper gives no polynomial witness-size guarantee for the generated
instances and no hard answer-first distribution. A solver can use precisely the
Groebner-basis/normal-form machinery implemented by the paper, or search degree
bounds successively using the linear system above. Planting cancellations at a
secret high degree is not evidence that either method is hard, and it can make
the output and exact expansion arbitrarily large.

### Nearby paper tasks also lack the required combination

| Candidate witness | Why it cannot be shipped from this paper |
|---|---|
| Quotients proving a stated remainder | Multivariate division is the natural direct algorithm; Section 3.2 delegates it to the external solver and checks the returned identity and degree condition. |
| A Groebner basis plus certificates | Buchberger's algorithm is the mandatory domain attack and is exactly what Sections 3.2--3.4 invoke. The paper supplies no generated regime on which it fails or even performance measurements. |
| Ideal-equality certificates | These are just two collections of the same membership decompositions, so bounded versions reduce to rational linear systems. |
| Radical-membership exponent and coefficients | Section 3.2 asks the external solver for both. The exponent/certificate size is not bounded, and no hard positive-instance distribution is given. |
| A non-membership result | This is an absence rather than an admissible positive witness; the paper uses a nonzero normal-form remainder to decide it. |
| A sparse or small-coefficient decomposition | This is a new constrained-representation problem not defined or analyzed in the paper. Any hardness claim would be imported speculation. |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- inverse generation | Pass in principle | Sample `c_i` first and form `f = sum_i c_i*g_i`. |
| H -- no polynomial/closed-form method in a justified regime | **Fail** | The paper has no hardness theorem or hard parameters; bounded certificate recovery is linear algebra, and the paper implements the Groebner/CAS domain solver for the general task. |
| V -- cheap exact verification | Pass for explicit certificates | Multiply sparse polynomials, sum, normalize rational coefficients, and compare exactly as in Sections 2.2 and 3.1. |
| G1--G8 | Not run | Step 0 requires stopping after H fails. |
| LLM hardening loop | Not run | Oracle failures cannot establish a missing complexity regime and would be especially misleading against a deterministic linear-algebra attack. |

## What would be needed for a viable family

A defensible successor would need a source that defines a bounded positive
certificate problem and proves hardness for the exact parameter regime used by
the generator, together with an answer-first distribution that preserves that
hardness. It would also need to test at least rational linear solving, bounded
Macaulay matrices, Buchberger/F4-style Groebner computation, and
construction-specific cancellation/support attacks. Those ingredients are not
present in arXiv:2604.13514, so adding them here would no longer be turning this
paper's result into a verified generator.
