# Rejected: arXiv:0909.3424

## Decision

No self-contained generator is shipped.  The proposed rank-four specialization
family fails **G and V**, and its only exactly checkable weakening fails **H on
both tracks**.

The source is Bartosz Naskręcki, [*Infinite family of elliptic curves of rank
at least 4*](https://arxiv.org/abs/0909.3424).  This decision is based on the full
paper, especially Theorem 1.1, Lemma 2.1 and the algorithm in Section 2, the
independence proof and Tables 2--3 in Section 3, and the explicit discussion in
Section 4.2.

## Why the proposed rank certificate fails G and V

Theorem 1.1 displays four rational points on

`E_(u^2-u-3): y^2 + (u^2-u-3)xy = x^3 + (u^2-u-3)x^2 - x + 1`

when `(u,v)` satisfies

`v^2 = 2569 + 18u - 9u^2 - 18u^3 + 9u^4`.

Substitution checks that the four displayed pairs are points.  It does **not**
check that their Mordell--Weil classes are linearly independent.  Independence
is the property needed for the claimed rank certificate.

Section 3 proves independence only after removing finitely many parameter values.
It does so by translating possible divisibility by 2 into rational points on a
collection of curves of genera 2 through 28 and then invoking Faltings' theorem.
This is not an effective per-instance witness: the checker cannot inspect four
points and decide that none of the relevant high-genus exceptional equations has
a rational point.  Section 4.2 makes the obstruction explicit: the paper says
that an upper bound for the heights of the excluded rational points is hard to
obtain, and replaces an unlimited effective construction with a finite table of
low-height cases computed using Sage/mwrank and numerical regulators.

Consequently, sampling arbitrary multiples on the auxiliary rank-two elliptic
curve does not give a generator that *knows* the resulting four points are
independent.  It knows only that they lie on the curve.  The finite table is a
lookup collection, not an unlimited family.  A numerical regulator is not an
exact witness.  Thus the intended rank problem fails G, and a checker based only
on substitution fails V.

One could add bespoke good-reduction/non-divisibility certificates for selected
specializations, but the paper gives neither an infinite construction carrying
such certificates nor a theorem that makes arbitrary auxiliary-curve multiples
carry them.  Searching primes separately for every emitted instance would be
searching for the certificate after building the instance, which is forbidden by
G rather than a repair of it.

## Track A analysis

If the answer is weakened to the exactly verifiable claim “give the four
displayed rational points,” G and V pass but **H fails on Track A**.  The points
are the explicit output of Theorem 1.1:

`(0,1), (1,1), (u,u+1), (1/9,(9+3u-3u^2+v)/54)`.

There is therefore a constant-time algorithm for every instance in the generated
distribution.  This is not merely a worst-case caveat or an algorithm for a
special regime; it is the construction defining the proposed distribution.

## Mechanical cost versus compact route (Track B audit)

Track B does not rescue the weakened point problem because there is no compression
gap.

When `(u,v)` is supplied, the **mechanical algorithm** is the displayed formula.
Reusing `u^2`, it takes 10 exact rational arithmetic operations to form the curve
parameter and the two nonconstant point coordinates.  On the representative
paper specialization

`u = 1200/341, v = -6491653/116281`,

200,000 constructions with Python `Fraction` took 1.707665 seconds, or **8.538
microseconds per instance**.  Exact substitution of all four points took 5.145531
seconds total, or **25.728 microseconds per four-point check**.

The **compact route** is the same displayed formula and the same 10 operations.
It is not shorter than the mechanical route; there is nothing structural left to
discover after the instance supplies the theorem's parameters.

With only the coefficient `t=u^2-u-3` supplied, the apparent concealment is still
constant-size.  Direct elimination gives

`u = (1 ± sqrt(4t+13))/2`

and, modulo `u^2-u-t-3`, the auxiliary quartic becomes

`v^2 = 9t^2 + 36t + 2596`.

Thus both the standard mechanical route and the by-hand shortcut use roughly 25
exact arithmetic/root operations, followed by the same point formula.  Increasing
coefficient bit length makes both routes perform the same big-integer square roots
and only turns the task into arithmetic/transcription; it does not create the
million-operations-versus-dozens gap required for Track B.

## Other objects in the paper

- Lemma 2.1 is itself a classification of linear-x-coordinate points, obtained by
  coefficient comparison and a Gröbner-basis calculation.  Asking for its listed
  points is another constant-size formula/lookup task.
- Section 4's root numbers are explicitly computed from bad-reduction primes (the
  paper suggests Sage), and the rank-five claims there depend on the Parity
  Conjecture except for one isolated curve.  They do not supply an unlimited exact
  witness family.
- The finite low-height table and the isolated unconditional rank-five example are
  useful mathematical data, but neither is an unlimited generator.

The candidate was rejected at Step 0, before module code or oracle runs.  There is
therefore no `gen_0909_3424.py` to retain and no fabricated self-test or hardening
transcript.
