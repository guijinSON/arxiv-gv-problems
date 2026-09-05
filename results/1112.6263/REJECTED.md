# Rejection: arXiv 1112.6263

The attempted family is rejected at **G9(c), no-tool suitability**, on
`TRACK = "A"`.  It must not be shipped.  The retained implementation is
`rejected_gen_1112_6263.py`.

## Step 0 result

Section 1 of Bardet, Faugère, Salvy, and Spaenlehauer,
[*On the Complexity of Solving Quadratic Boolean Systems*](https://arxiv.org/abs/1112.6263),
defines Boolean MQ SAT as finding one common zero of quadratic polynomials in
`F_2[x_1,...,x_n]`.  It restricts the main analysis to `m >= n`; it identifies
`m < n` and sparse constraint systems as easier regimes.  Section 5 separately
identifies structured systems with low witness degree as easier.

The attempted generator uses the native object and the square dense regime
`m=n`.  It samples a Boolean root first, samples every nonconstant coefficient,
and fixes each constant coefficient so the held root is a zero.  Therefore G
passes by inverse generation.  V passes because the checker evaluates all
quadratic monomials and equation parities exactly in `F_2`, accepting any common
zero without reading the planted answer.

The certificate is not produced by a polynomial-time method.  Section 2,
Algorithm **BooleanSolve**, specializes variables and uses Boolean Macaulay
linear algebra to prune branches.  Section 3, Theorem 2 gives, for square
strong-semi-regular systems, `O(2^(0.841n))` deterministic and expected
`O(2^(0.792n))` Las Vegas upper bounds.  Section 4 offers a conjecture and
experiments for *unconditional uniformly random* systems, not a hardness
theorem for this generator's root-conditioned distribution.  Thus Track A was
the only plausible label, and even that distributional hardness claim remained
provisional.

## Why the mandatory gate fails

At attempted shipping size `n=m=36`:

- the measured degree-3 square-free Macaulay/XL probe performs **55,950 exact
  row XORs in 0.86 seconds and does not find a root**;
- the paper's asymptotic exponent terms are about **3.83e8** operations for the
  Las Vegas bound and **1.30e9** for the deterministic bound (these are
  asymptotic context, not measurements at `n=36`);
- Section 4 reports that BooleanSolve only overtakes exhaustive search around
  `n=200` for the Las Vegas variant and around `n=280` for Gaussian
  elimination, so ordinary exhaustive search is the paper's practical baseline
  at this small size;
- a dense direct verification touches up to **24,012 displayed monomial slots**
  (`36 * (1+36+C(36,2))`) before representation-level bit packing.

There is **no compact route** encoded in these conditioned-random equations.
After noticing the Macaulay invariant, a solver still has to perform the same
large linear-algebra/search computation.  Consequently the compact-route cost
is not shorter than the mechanical route and is already bounded below by the
measured 55,950 unsuccessful row XORs.  This exceeds G9(c)'s limit of 300 exact
arithmetic operations.  The former value of 36 counted only writing the secret
after it had been supplied; it did not count finding it and was invalid.

Track B does not rescue this family: its required mechanical-versus-compact gap
is absent.  A degree-2 inconsistency certificate from Lemma 1 would be a valid
witness, but on a generic instance it is precisely the output of the Macaulay
linear solve.  Inverse-generating such a certificate would not create a short
solver-visible route unless extra structure were added; that would leave the
paper's random hard regime and would require a different family and a fresh
audit.

## Other evidence

G1–G8 pass in `selftest_report.json`; this does not override G9.  The required
four-vendor hardening and G9 arms were also attempted, but every request returned
HTTP 403 `Key limit exceeded`, so the retained transcripts contain no scored
oracle attempt.  That infrastructure failure is recorded but is **not** the
reason for rejection: the local route-cost gate already fails.
