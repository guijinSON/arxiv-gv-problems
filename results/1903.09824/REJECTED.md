# Rejected at Step 0: the paper's certificate is already its linear-time algorithm

Paper: Tai Do Duc, [*New Constructions of Group-Invariant Butson Hadamard
Matrices*](https://arxiv.org/abs/1903.09824), arXiv:1903.09824v4.

## Decision

No generator is shipped.  The native construction passes **G** on a verified
specialization and passes **V**, but it fails **H under both tracks**.  In
particular, this is not a Track-A family merely because the formal answer space
of phase vectors is large: Lemma 3.1 writes every phase down explicitly, and
Theorem 3.3 only concatenates those blocks over coset representatives.  The
certificate-producing algorithm is therefore the displayed construction
itself.

This is a Step-0 rejection, so there is intentionally no
`gen_1903_09824.py`, `selftest_report.json`, README, or oracle transcript.  The
task requires stopping before Steps 1--4 when G, H, or V fails.

## What the paper actually defines

Section 2, Result 2.2 is the exact definition needed by a checker.  For a finite
group `G`, put

`D = sum(a_g g)` and `H[g,k] = a_(g k^-1)`.

The entries form a group-invariant `BH(G,h)` matrix exactly when every `a_g` is
an `h`th root of unity and the group-ring identity
`D D^(-1) = |G|` holds.  Equivalently, every nonidentity periodic
autocorrelation is zero.  Thus a phase-exponent vector is a finite witness and
can be checked exactly in `O(|G|^2)` group operations; no floating point or
oracle is needed.

The easy side is not a special case hidden later in the paper; it is the main
contribution:

- Lemma 3.1 gives `D_i` coefficient by coefficient in three parity cases.  In
  its first case the exponent is `j^2 k + m i j (mod h)`; the other two cases
  are equally explicit displayed quadratic formulas.
- Lemma 3.2 proves the needed norms by quadratic Gauss-sum cancellation.
- Theorem 3.3 forms `D = sum_i D_i x_i` from coset representatives.
- Theorems 4.3 and 4.6 do the analogous job over a finite local ring: after a
  displayed vanishing sum or the displayed root-sum data is chosen, the proof
  assigns every coefficient directly.  Remarks 4.4 and 4.7 explicitly point
  out the broad easy regime `6 | h`.
- Result 4.8 transfers the same coefficient array directly to a perfect
  phase array; Theorem 4.10 and Corollary 4.11 are again existence-by-explicit-
  construction results, not search-hardness results.

The paper contains no worst-case, average-case, or planted-distribution
hardness theorem for recovering any of these objects.

## Certificate-production test, with measured costs

I measured a native nonabelian specialization for which the construction is
valid without relying on a questionable noncentral rearrangement in the proof.
Take

`G = C_8 x Q_8`, `n = 64`, `h = 8`, `k = 8`, and `m = 1`,

where the displayed `C_8` is central and normal.  Index the eight `Q_8` cosets
by `i = 0,...,7` and the cyclic subgroup by `j = 0,...,7`.  Lemma 3.1 reduces
to the 64 coefficients

`a_(j,i) = zeta_8^(i j)`.

The full expanded witness has 64 phase exponents (192 characters as a Python/
JSON-style integer list).  Producing it takes exactly 64 modular
multiplications and 64 reductions, **128 exact arithmetic operations**.  A
200,000-run CPython timing gave **1.409 microseconds per complete witness**.
An independent exact group-ring check evaluated all `64^2 = 4,096`
correlation terms, reduced root sums using `Phi_8(x) = x^4 + 1`, and accepted;
2,000 timed checks averaged **0.164 ms** each.

Those numbers answer the required Track-B question:

| answer representation | mechanical certificate route | compact route after insight |
|---|---:|---:|
| expanded 64-entry phase vector | 128 modular operations plus 64 writes | the same 128 operations and writes; every requested entry still has to be emitted |
| quadratic phase rule | substitute `n=64,h=8,k=8,m=1` into Lemma 3.1 | the identical substitution; the paper has already supplied the rule |

At the maximum 256-atom answer size, the same issue persists: construction is
`Theta(|G|)` and expanded output is `Omega(|G|)`.  Increasing the group only
scales the displayed loop and the answer together.  There is no million-step
mechanical route compressed to a short invariant; the ordinary route is
already the compact route.

## Verification caveat in Theorem 3.3

There is also a correctness obstacle to using Theorem 3.3 at its advertised
full generality.  Its proof changes

`D_i x_i x_j^-1 D_j^(-1)` into
`x_i x_j^-1 D_i D_j^(-1)`

using only normality of the cyclic subgroup.  Normality permits conjugating a
subgroup element across `x_i x_j^-1`; it does not permit this commutation while
leaving `D_i` unchanged.

An exact countercheck occurs already at `n=64,h=8`.  Let

`G = D_16 x C_4`, with `D_16 = <r,s | r^8=s^2=1, srs=r^-1>`,

so `<r> ~= C_8` is normal of index 8 and every numerical hypothesis of
Theorem 3.3 holds.  Choose coset representatives `(s^b,c)`, indexed by
`i=4b+c`, and use the theorem's `a_(r^j s^b,c)=zeta_8^((4b+c)j)`.
For the shift `(s,0)`, the eight exponent counts in the alleged zero
autocorrelation are

`[32, 0, 8, 0, 16, 0, 8, 0]`.

Their root sum is `16`, not zero.  Therefore a verified generator could not
blindly sample every group promised by the theorem.  Restricting to a central
cyclic subgroup (as in `C_8 x Q_8` above) repairs G, but does nothing for H.
The local-ring constructions avoid this particular noncommutative step, yet
remain explicitly computable and fail H for the same reason.

## Why Track A fails

Track A requires no known efficient general method on the generated
distribution.  Here the paper provides a deterministic `Theta(|G|)` method on
every safe generated instance: evaluate the displayed exponent formula and
place its blocks on the cosets.  The worked `C_8 x Q_8` instance is produced in
1.409 microseconds.  A formal language of `8^64` arbitrary phase vectors does
not change that; it only ignores the construction that a solver is entitled to
use.

Relabelling a group table to hide the cyclic subgroup would not establish
Track A either.  Element-order enumeration and normal/central subgroup tests
are polynomial-time finite-group-table algorithms, and the paper proves no
distributional hardness for a relabelled-table recovery problem.

## Why Track B fails

Track B requires a large measured gap between the ordinary algorithm and a
short structure-aware route.  The table above shows no gap: 128 operations
versus the same 128 operations for an expanded witness, or one displayed-formula
substitution versus that same substitution for a compressed witness.  The
checker is more expensive (`4,096` correlation terms), but verification cost is
not certificate-production cost and cannot be used to manufacture hardness.

Making a puzzle by deleting coefficients, corrupting phases, or hiding the
normal subgroup would add a decoding or table-isomorphism problem not studied
in this paper.  Any hardness would come from that added obfuscation, not from
Theorem 3.3 or the local-ring constructions.  It therefore cannot rescue this
paper as a native Track-B family.

## Gate outcome

| requirement | result |
|---|---|
| G -- generatable | **Passes only on verified specializations:** direct evaluation of Lemma 3.1; the advertised arbitrary-normal-subgroup version has the exact counterexample above. |
| H -- Track A | **Fails:** the paper gives a deterministic `Theta(|G|)` certificate producer for the generated distribution. |
| H -- Track B | **Fails:** 128 mechanical arithmetic operations versus the same 128-operation compact route at the measured 64-entry setting. |
| V -- verifiable | **Passes:** exact group-ring autocorrelation in `O(|G|^2)`; measured 4,096 terms and 0.164 ms. |
| Steps 1--4 | Not run, as required after the Step-0 H failure. |

The witness is mathematically rich and exactly checkable.  The disqualifying
fact is narrower: the paper itself already computes it as cheaply as it can be
written.
