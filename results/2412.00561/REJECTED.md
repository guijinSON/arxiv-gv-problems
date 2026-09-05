# Rejected at Step 0: arXiv 2412.00561

## Decision

No module is shipped.  The proposed native family—produce an explicit rational
plane curve of degree \(d=(p+q)/3\) with a prescribed \((p,q)\)-cusp—fails **G**
and **V**, independently of track.  The paper proves that such a curve exists,
but its proof does not output a polynomial equation, a rational parametrization,
or another finite curve witness that the generator can carry into the answer.
The nearby finite substitutes clear G and V only by compiling the geometry into
elementary arithmetic; those substitutes fail **H on Track A**, and also fail
**H on Track B** because their mechanical and compact routes have essentially
the same length.

This decision is based on the complete v2 source of McDuff--Siegel,
[*Sesquicuspidal curves, scattering diagrams, and symplectic
nonsqueezing*](https://arxiv.org/abs/2412.00561), not its abstract.

## What the paper actually constructs

The exact curve definition is in the discussion following Theorem B.  A curve
\(C\subset\mathbb{CP}^2\) is \((p,q)\)-well-placed with respect to a fixed
uninodal cubic \(\mathcal N\) when it meets \(\mathcal N\) only at its node, is
locally irreducible there, and has local intersection multiplicities \(p\) and
\(q\) with the two branches.  Theorem B says that, for coprime \(p>q>1\) with
\(3\mid p+q\), a rational degree-\((p+q)/3\) curve with the required cusp exists
exactly for the Fibonacci family below \(\tau^4\), or for \(p/q>\tau^4\).

The certificate-producing chain is Sections 4--6:

1. Proposition 4.2.1 gives a bijection between well-placed curves and curves in an
   edge/weighted blowup of a toric surface.  It transports a curve already in
   hand; it does not construct one from \((p,q)\).
2. Theorem 5.2.3 (the paper's scattering/curve correspondence) infers existence
   from a nonzero coefficient in a Kontsevich--Soibelman scattering diagram.
3. Its proof passes through relative Gromov--Witten invariants and nonemptiness
   of a compactified moduli space (Theorem 5.2.5, Lemma 5.2.7, and Corollary 5.2.9).
   These are existence/counting arguments, not an algorithm returning a member
   of that moduli space.
4. Section 6 proves that the relevant coefficient is nonzero using the
   change-of-lattice lemma (Lemma 6.1.2) and scattering-positivity results
   (Theorems 6.2.1 and 6.2.3).  Again, the output is support/nonvanishing, not a
   curve equation.

Consequently, using Theorem B as a "theorem-backed construction" would leave
the claimed answer absent.  Finding coefficients of a plane curve or a
parametrization afterward would be solving the generated instance, which G
explicitly forbids.

V fails for the same proposed answer.  A bare claim that the curve exists is not
a witness.  A usable exact certificate could contain a homogeneous equation or
rational parametrization plus finite data proving birationality, the prescribed
local branch/contact orders, and rationality.  The paper supplies none of that
data for the general family.  Replacing it by the nonzero scattering coefficient
does not fix V: nonvanishing is only a theorem-mediated existence proxy, not an
object whose inspection verifies the submitted curve.

## Track audit and measured cost comparison

The paper does expose several finite, exactly checkable questions, so each was
tested as a possible Track B family before rejecting.

| candidate | mechanical route at an answer-cap-sized instance | compact route | result |
|---|---:|---:|---|
| Decide the dense-region branch of Theorem B / Corollary 6.3.3 | For promised coprime \(p,q\), one addition and residue, then \(r=2p-7q\), a sign test, and \(r^2>45q^2\): **at most 10 exact arithmetic/comparison operations** | The same exact inequality: **8--10 operations** | No Track B gap; Track A is false. |
| Compute the \(\mathbb{CP}^2\) fundamental-bijection vector \(\wp(p,q)\) from equation (4.3.1) | One branch comparison and, e.g. for \(p/q\ge2\), \((q,5q-p)\): **4 arithmetic/comparison operations** (under **12** even including the displayed lattice change) | The displayed piecewise formula: **the same 4--12 operations** | No Track B gap; Track A is false. |
| Give an adjunction nonexistence certificate | Evaluate \(d=(p+q)/3\) and \(2\delta=(d-1)(d-2)-(p-1)(q-1)\): **10 arithmetic/comparison operations** | The same evaluation: **10 operations** | Valid negative witness, but no hardness on either track. |
| Evaluate Theorem A above the accumulation point | Reduce \(3a/(a+1)\): **one addition, one multiplication, one gcd/reduction** | Exactly the displayed formula: **the same 3 operations** | A number alone is not an embedding/optimality witness; even as arithmetic it has no gap. |
| Compute a scattering count | Section 5.2 explicitly says any fixed count is algorithmically computable by scattering; the Kontsevich--Soibelman method works order-by-order in \(t\) | The paper gives support/positivity, not a short exact coefficient or a finite curve witness in the general dense region | Potentially large mechanical cost, but **no compact witness-producing route** to compare with it.  This cannot be converted into Track B merely by returning a theorem citation. |

The operation counts above do not depend on using tiny integers: at a hypothetical
shipping instance with 2048-bit \(p,q\) (already over 1,200 input characters),
the first four routes still execute the same number of big-integer operations.
Counting bit operations makes both columns grow together; it creates no
compression.  Conversely, making the order-by-order scattering calculation
large does not help, because the paper's short route proves only nonvanishing
and never emits the demanded curve certificate.

Theorem A's Fibonacci staircase is no exception.  Locating a lower-staircase
interval takes \(O(k)\) Fibonacci recurrence steps (or equivalent exact
continued-fraction work), and the compact exact route performs the same
recurrence.  Raising \(k\) enlarges the typed integers rather than revealing a
short invariant-based solution.

## Why no analogue was substituted

One could inverse-generate a generic parametrized cusp such as a projective
transform of a monomial curve, or ask only whether an integer vector lies in the
dense cone.  The former is not the minimal-degree sesquicuspidal family proved
by Theorem B and has an elementary planted parametrization; the latter discards
the algebraic curve and its singularity entirely.  They would be convenience
analogues, not native coverage of this paper, and neither supplies the missing
hardness claim.

No generator, self-test report, or oracle transcript was created because the
failure occurs at the mandatory pre-code triage.  There is therefore no
`cap_bound` or G9 rejection and no partially built module to retain.
