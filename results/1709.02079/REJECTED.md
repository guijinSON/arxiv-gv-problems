# Rejected at Step 0: the stated private-key family is empty

Paper: Khadijeh Bagheri, Mohammad-Reza Sadeghi, and Daniel Panario,
[*A Non-commutative Cryptosystem Based on Quaternion Algebras*](https://arxiv.org/abs/1709.02079)
(arXiv:1709.02079v1).

## Proposed family

The natural family suggested by the paper is BQTRU key recovery.  An instance
would contain the public quaternion polynomial

\[
  \widetilde H=F^{-1}\circ G+\vartheta\pmod q,
\]

and a witness would be the paper's private short vector
\((\vec G,\vec F,-\vec\rho(\gamma))\), checked by exact cyclic bivariate
convolution and evaluation on the grid of roots of unity.  This would be
generatable by sampling the private data first, and verification would be
exact and inexpensive.

It cannot be instantiated faithfully, however, because the paper's stated
private-key conditions are inconsistent.

## The contradiction

Section 2 defines each small polynomial in the sets used by the scheme as a
ternary polynomial with `2d` nonzero coefficients.  The brute-force analysis
in Section 5 removes any possible ambiguity about the signs: it counts one
component as

\[
  {n^2\choose d_f}{n^2-d_f\choose d_f},
\]

which is exactly the number of polynomials with `d_f` coefficients equal to
`+1` and `d_f` coefficients equal to `-1`.  Section 3 chooses every component
\(f_i\) of

\[
  F=f_0+f_1i+f_2j+f_3k
\]

from that set.  Consequently,

\[
  f_i(1,1)=d_f-d_f=0\quad\text{for every }i,
\]

and therefore \(F(1,1)=0\) in the quaternion algebra over \(\mathbb F_p\).

The same key-generation section also requires \(F\) to be invertible in
\(\mathbb A_p\) for decryption.  Evaluation at \((1,1)\) is a unital ring
homomorphism from
\(R'_p=\mathbb F_p[x,y]/(x^n-1,y^n-1)\) to \(\mathbb F_p\).  Applying it to
an alleged identity \(F\circ F_p^{-1}=1\) would give

\[
  0\circ F_p^{-1}(1,1)=1,
\]

which is impossible.  Equivalently, the determinant/norm of the split
quaternion matrix for \(F\) vanishes at \((1,1)\), so it is not a unit of
\(R'_p\).

This is not a rare key-generation failure that rejection sampling can repair:
it holds for every member of the paper's counted private-key language and for
every advertised parameter set, including \((n,p,q,d_f)=(7,3,113,7)\) and
\((11,3,199,17)\).

There is a second construction leak from the same fact.  Every balanced
component of \(G\) also vanishes at \((1,1)\), so the set

\[
  T=\bigcap_{i=0}^3\{(a,b)\in E:g_i(a,b)=0\}
\]

always contains the publicly predictable point \((1,1)\).  Thus the ideal
choices are not distributed as the unrestricted count used in the paper's
brute-force estimate.

## Failed gate and why no surrogate is shipped

**G fails.**  There is no certificate-producing key-generation algorithm for
the exact key language and invertibility constraints stated in the paper,
because that language contains no valid decryption key.

Three apparent workarounds are not faithful:

- Allowing unbalanced signs can make \(F\) invertible, but changes `L_f` and
  invalidates the paper's key-space formula and advertised hardness regime.
- Omitting invertibility modulo `p` produces a short solution of the public
  lattice equation, but not a BQTRU private/decryption key.
- Choosing an arbitrary public \(\widetilde H\) can produce a sparse
  convolution puzzle, but not a ciphertext under the paper's cryptosystem.

Any of those could be labelled a convenience analogue, but none supports the
requested native cryptographic-witness family.  Because Step 0 requires
rejection as soon as G, H, or V fails, no `gen_1709_02079.py`, fabricated gate
report, or oracle transcript is provided.

## Additional hardness caveat

Even after repairing the key language, Track A would need fresh evidence.
Section 5's main theorem argues only that the planted vector is *most likely*
short under a hybrid norm, and its proof invokes qualitative claims that
Lagrange coefficients are “very larger” rather than a proved distributional
bound.  The Gentry-style reduction is explicitly left as a conjectural
security claim.  The paper therefore does not transfer its displayed
`>2^166` estimate to an unbalanced-sign repair.
