# Rejected: arXiv 2107.03097

This paper was read in full before implementation.  No generator module was
built because the proposed native search family fails **H at Step 0 on both
Track A and Track B**.  Generation and exact substitution would be easy, but
the witness is already visible in every instance.

## Decision

| gate | result |
|---|---|
| G — generatable | Pass in isolation.  Theorem 1 supplies several integer solutions for every parameter `n >= 3`. |
| V — verifiable | Pass for finding one solution: substitute two integers and compare the resulting integer with `+1` or `-1`. |
| H — Track A | **Fail.**  Every instance has the constant solutions `(1,0)`, `(-1,0)`, `(0,1)`, and `(0,-1)`, so a deterministic constant-time attack succeeds on the entire distribution. |
| H — Track B | **Fail.**  The mechanical certificate route and the compact route are the same zero-search substitution; there is no compression gap. |

The relevant source is Ingrid Vukusic, [*On a cubic Family of Thue Equations
involving Fibonacci Numbers and Powers of Two*](https://arxiv.org/abs/2107.03097).
Theorem 1 states that, for every integer `n >= 3`,

```text
X (X - F_n Y) (X - 2^n Y) - Y^3 = +/- 1
```

has only the listed solutions

```text
(+/-1, 0), (0, -/+1), -/+(F_n, 1), -/+(2^n, 1).
```

Lemma 6 proves directly that all solutions with `|Y| <= 1` are precisely these
listed solutions.  Thus the prior-triage proposal to “choose `n` and an integer
solution” does not provide an inverse-generation degree of freedom: once `n`
is chosen, Theorem 1 has already classified the possible witnesses.

## The discriminating cost check

The algorithm that produces a witness is **not** the paper's Thue solver.  It
is the constant rule `return [1, 0]` (or, if `Y = 0` is forbidden, `return
[0, 1]`).  Construction uses **0 arithmetic operations** and writes two small
integers.  Direct verification takes at most **six elementary integer
operations** even without short-circuiting; with the zero factor exposed it is
one product observation and one comparison.

The compact route has exactly the same length:

1. set `Y = 0` and `X = 1`;
2. observe that the left side is `1`.

So the measured comparison is **0 certificate-construction operations versus
0**, or **at most 6 verification operations versus at most 6**.  The compact
route is no shorter than the mechanical route because they are the same route.
This is not a Track B no-tool-compression problem.

Adding natural exclusions does not repair H:

| requested witness | mechanical cost | compact route |
|---|---:|---:|
| any solution | return `(1,0)`: 0 arithmetic operations | identical |
| require `Y != 0` | return `(0,1)`: 0 arithmetic operations | identical |
| require `X*Y != 0` | copy `(F_n,1)` or `(2^n,1)` from the displayed factors: 0 arithmetic operations once the numeric instance is rendered | identical |
| expanded rather than factored coefficients | recover `F_n` and `2^n` as the two roots of `t^2-(F_n+2^n)t+F_n2^n`: a constant-size quadratic calculation | the same calculation |

If a renderer gives only symbolic `n`, serialising `2^n` or `F_n` merely adds
the unavoidable output computation.  Fast exponentiation/fast doubling takes
`O(log n)` big-integer operations, and writing the integer takes `Omega(n)`
bits.  There is still no shorter structural route; making `n` large would test
calculation and transcription and would run into G9(c), not create a valid
Track B family.

## Why the paper's expensive computation does not help

The expensive parts answer a different question: whether **additional**
solutions exist.  Section 3, Lemma 5 reports that PARI/GP's `thueinit` and
`thue` take a couple of minutes for `n <= 28`.  Section 4, Lemma 14 applies
Baker--Davenport reduction and checks convergents for `29 <= n <= 1000`; the
paper reports about one hour, with intermediate denominator bounds as large as
`3.29e99`.  Section 6, Lemma 18 then uses two LLL reductions to shrink the
remaining range.

None of those computations is needed to produce or validate one positive
witness.  Counting their cost as the witness-finding baseline would be the
precise Step-0 error the task warns against.

## Alternatives considered

- Asking for **all** solutions turns Theorem 1 into a lookup.  Checking that
  every listed pair substitutes correctly does not certify completeness; the
  paper's analytic and computer-assisted exclusion argument is not a bounded
  exact witness that this module could cheaply verify.  That variant therefore
  either still fails H or fails the witness rule for completeness.
- Asking for a certificate that no non-listed solution exists has the same
  witness-rule problem.  The proof uses real logarithmic estimates,
  continued-fraction reductions, and LLL computations rather than a compact
  rational refutation object supplied with each instance.
- A hidden random `GL(2,Z)` change of variables could obscure the four visible
  pairs, but then the difficulty is an added binary-form-equivalence puzzle,
  not a hard regime established in this paper.  If the change of variables is
  included, its inverse gives a witness by a constant-size `2 x 2` calculation;
  if it is withheld, there is no paper-backed distributional hardness claim or
  separate compact route.  Merely changing coordinates at fixed `n` also
  produces isomorphic instances that G8 must assign the same canonical key.
- Allowing an arbitrary right-hand side sampled from a planted `(X,Y)` would be
  inverse-generatable, but it leaves Equation (2), whose right-hand side is
  specifically `+/-1`, and the paper supplies no hardness theorem for that new
  planted distribution.

Accordingly, there is no honest shipping preset and no meaningful adversary
panel: the constant-witness attack would score **8/8 successes** (indeed, every
seed at every size).  Writing a module only to report that failure would add no
evidence beyond Theorem 1 and Lemma 6, so work stops at Step 0 as instructed.
