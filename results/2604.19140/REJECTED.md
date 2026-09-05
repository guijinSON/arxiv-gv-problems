# Rejected: arXiv 2604.19140

## Decision

The proposed native family passes **G** and **V**, but fails **H**.  It fails
Track A because the paper gives an efficient explicit certificate algorithm,
and it also fails Track B because the compact route is the same constant-length
calculation as that algorithm.  There is no mechanical-versus-structural gap to
measure.  No generator module was built after STEP 0.

Paper: [Quartic Rational Diophantine Quadruples and the Euler Surface](https://arxiv.org/abs/2604.19140),
version 1.

## Exact paper facts used in triage

Definition 1.1 says that a quartic rational Diophantine quadruple is a set of
four pairwise distinct, nonzero rationals for which every pairwise product plus
one is a fourth power in `Q`.

Theorem 1.2 is the infinitude statement.  Its certificate-producing result is
**Proposition 1.3**, not a search theorem.  For a nondegenerate rational Euler
surface point

```text
X^4 + Y^4 = Z^4 + W^4,
```

it gives the quadruple directly:

```text
a = (X^4-W^4)/(Z^2 W^2)    b = -W^2/Z^2
c = (Y^4-W^4)/(Z^2 W^2)    d =  Z^2/W^2.
```

The proposition also gives all six roots directly:

```text
Y/Z,  XY/(ZW),  X/W,  X/Z,  0,  Y/W.
```

The nondegeneracy test is the displayed condition (2),

```text
XYZW (X^2-Y^2) (X^2-W^2) (Y^2-W^2) != 0.
```

Section 2, especially Propositions 2.1--2.3 and the proof of Proposition 1.3,
explains why the special locus `v=0`, `ru=tw` collapses the compatibility
conditions and makes the square condition automatic.  In particular, every
output of the construction has the immediately usable relations

```text
b*d = -1,       a+c = b+d.
```

Euler's homogeneous parametrization is displayed immediately after
Proposition 1.3, and the specialization `(alpha,beta)=(1,t)` is followed by
explicit closed formulas for `a(t), b(t), c(t), d(t)`.  Theorem 3.1 repeats the
same explicit rational map for all even exponents and, with one extra square
condition, for odd exponents.

## G and V

Generation would be valid theorem-backed construction: sample `t`, evaluate
Euler's parametrization, reject the finite exceptional set by condition (2),
and apply Proposition 1.3.  No search is required.

Verification would also be exact and cheap.  A certificate can contain the four
rationals and the six displayed roots; the checker need only test distinctness,
nonzeroness, and six rational identities of the form `q_i*q_j+1 = r_ij^4`.

## The H failure, with both required costs

The natural instance suggested by the prior triage hands the solver a rational
Euler-surface point and asks for its quartic Diophantine quadruple.  The
domain-standard algorithm is Proposition 1.3 itself.

| quantity | measured/result |
|---|---:|
| notional shipping parameter | a 24-bit integer `t`, the largest tested setting whose JSON certificate (quadruple plus six roots) stayed below the 2,000-character cap |
| largest Euler coordinate | 164 bits |
| serialized certificate | 1,644 characters |
| mechanical route | 22 high-level exact rational operations |
| measured mechanical wall time | 0.0000148 s mean over 2,000 constructions with Python `Fraction` |
| exact six-identity verification | 0.0000348 s mean over 5,000 checks |
| compact route | the same Proposition 1.3 formulas, 22 high-level exact rational operations |

The count of 22 is eight multiplications, two subtractions, four divisions,
and one negation for `a,b,c,d`, followed by two multiplications and five
divisions for the nonzero roots (`v=0` is a literal).  Computing fourth powers
by repeated squaring is included in those multiplications.  Rational
normalization is performed by `Fraction` in the timing.

Thus the compact route is **no shorter** than the mechanical route: 22
operations versus 22.  Increasing `n` can only increase integer bit lengths;
it does not increase the number of decisions or hide any structure.  Such an
escalation tests exact-arithmetic and transcription stamina, not mathematical
intuition, and soon hits G9(c)'s answer-length cap.

This rules out both possible hardness claims:

- **Track A fails.**  There is a deterministic polynomial-time explicit
  algorithm on every generated instance; no distributional hardness remains.
- **Track B fails.**  The reference algorithm costs the same constant number of
  symbolic operations as the supposed shortcut.  There is no million-operation
  mechanical route opposed to a short invariant-based route.

The same conclusion holds if an instance supplies `t` instead of the Euler
point: evaluate the displayed degree-seven parametrization and then the same
map.  Both the standard and compact routes remain constant-length straight-line
evaluation.  If the statement instead supplies the six target pair-products,
the four unknowns are recovered by a constant number of field operations (for
example from three pair products and one exact rational square root), again
with no scaling search.

## Why the paper's large computation does not create Track B hardness

Section 2 reports a real and impressive exploratory computation: at height
bound `B=100,000`, the authors examined **219,415,142** generated pairs, using
**11,785 CPU hours**, and found 569 triples and 11 almost quadruples.  That
search helped discover the special locus `v=0`, `ru=tw`.

It is not the mechanical cost of the proposed generated instances.  Once the
instance is an Euler point (or a parameter on Euler's displayed curve),
Proposition 1.3 replaces that discovery search entirely.  Comparing 11,785 CPU
hours with 22 operations would therefore compare two different problems: an
unconditioned historical discovery search and a conditioned map-evaluation
instance.

## Alternatives considered

- Asking for *any* quartic rational Diophantine quadruple does not give an
  unlimited instance family: the same published example answers every prompt,
  so seed diversity and hardness disappear.
- Giving three members and asking for the fourth is even easier on the paper's
  generated distribution because `bd=-1`; trying the negative reciprocal is an
  obvious in-context attack.
- Giving the two nonspecial members does not help: the additional identity
  `a+c=b+d` and `bd=-1` reduce recovery to one rational quadratic.
- Hiding the explicit map behind an expanded polynomial, a decoy list, a
  coefficient-matching system, or an unrelated height/congruence condition
  would manufacture hardness not present in the paper's problem.  It would be
  a benchmark-convenience surrogate rather than the native family proposed by
  the paper and the prior triage.

Accordingly, the honest outcome is rejection at STEP 0 for **H on both tracks**,
not a Track A claim that conceals Proposition 1.3 and not a Track B claim that
uses the paper's historical discovery cost as though it were per-instance
solver cost.
