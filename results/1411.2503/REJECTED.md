# Rejected at Step 0: arXiv:1411.2503

Paper: Jean-Guillaume Dumas and Jean-Baptiste Orfila, [Generating S-Boxes
from Semifields Pseudo-extensions](https://arxiv.org/abs/1411.2503).

## Decision

No module is produced. The paper supplies exact, cheaply checkable finite-field
and semifield objects, so verification is not the problem. It supplies neither a
scalable hard search distribution (Track A) nor a compact, sub-300-operation
route to the truth-table invariants that differs from their mechanical
computation (Track B). Shipping the suggested invariant-computation family would
therefore make a hardness claim contradicted by the paper's own method.

## The Step 0 question

**What algorithm produces the certificate, and what does it cost?**

For the proposed S-box construction, Section 2, Lemma 2 gives the certificate
directly. Given a pseudo-irreducible `X^2 + alpha X + beta`, it defines every
value of the bijection `T'` using a constant number of additions,
multiplications, and inversions in the 16-element semifield. Constructing its
entire 256-entry truth table is consequently a direct 256-step table
calculation, not a hard witness search.

For the cryptographic properties, Section 4 gives executable finite sums and
maxima. For a truth table of size `N`, a differential-distribution table takes
`O(N^2)` exact updates. All vectorial Walsh coefficients can be computed in
`O(N^2 log N)` exact butterfly updates (or the displayed definition can be used
naively in `O(N^3)`), and algebraic degree follows from Boolean Möbius transforms
in polynomial time. At the paper's only S-box size, `N = 256`, these are small,
deterministic computations.

Section 5 confirms that this is how the advertised properties were obtained:
the authors construct the S-boxes, "apply all the tests of Section 4," and say
that they obtained the selected boxes "by testing all possible
pseudo-irreducible polynomials." The APN and avalanche claims are likewise
reported as experimental results, not guaranteed for a scalable parameter
regime by a theorem.

## Gate analysis

| Gate | Result | Reason |
|---|---|---|
| G | Partial only | Lemma 2 theorem-backs bijectivity, but not maximal nonlinearity, differential uniformity 4, APN behavior, degree, avalanche, or bit independence. Those are learned by running the tests. |
| H / Track A | Fail | The paper states no average-case or distributional hardness theorem. The natural certificates are produced by the displayed formula or polynomial-time truth-table algorithms. |
| H / Track B | Fail | Computing all invariants by hand is tedious, but the paper gives no compact route that recovers them in at most 300 exact operations. Asking for one or a few `T'` values instead makes the displayed formula itself the short mechanical route and leaves too small an answer space. Asking for the whole table exceeds the intended-route cap and tests transcription/arithmetic. |
| V | Pass in isolation | Bijection and every listed truth-table invariant can be recomputed exactly from finite tables. This does not rescue H. |
| Scaling | Fail | The native construction studied is an 8-by-8 S-box on `(S_16)^2`. Section 3 discusses semifield generation only for `q = 2, n <= 8`; the good cryptographic scores are experimental specifically at 256 entries, with no hardness-preserving asymptotic regime. |

## Easy regimes and misleading alternatives

- Section 2's pseudo-inverse is an explicit formula. Turning it into an
  evaluation problem is an arithmetic exercise, not search hardness.
- On an actual finite field the construction reduces to ordinary inversion in
  `F_(2^8)`, which has standard efficient arithmetic and is even more structured.
- The matrix-spread-set characterization in Section 3 makes a proposed
  semifield easy to verify, but the paper's enumeration algorithm is explicitly
  exhaustive (`O(n^3 2^(n^2))` naively, improved by Gray-code tabulation). The
  paper does not turn that worst-case enumeration into a hard generated
  distribution. Planting field multiplication matrices would instead create an
  efficiently constructible special case.
- Relabellings or affine variants of one of the fixed 256-entry tables do not
  establish a scalable distribution; a correct canonicalization must also not
  count mere reorderings as unlimited new mathematics.

The prior triage hypothesis therefore fails at its key step: the paper can
construct functions and can *compute* their invariants, but it does not construct
functions together with the claimed cryptographic invariants by theorem or
identity. Treating those computed values as the hard witness would violate the
discriminating test in the task.
