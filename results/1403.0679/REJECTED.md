# Rejection: arXiv:1403.0679

Paper: Zekiye Sahin Eser and Laura Felicia Matusevich, [*Primary components of codimension two lattice basis ideals*](https://arxiv.org/abs/1403.0679).

## Decision

No family from the paper clears the hardness gate. The natural primary-component boundary family passes G by theorem-backed construction and passes V by exact integer recomputation, but it fails H on both tracks.

| gate | result |
|---|---|
| G | pass for the retained draft: Theorem 5.1 constructs the monomial boundary directly from a dependent opposite row pair |
| V | pass: normalize signs, compute a gcd and a rational row ratio, then compare the submitted sparse support exactly |
| H, Track A | fail: Theorem 5.1 is an explicit output-linear algorithm for every instance in the generated distribution |
| H, Track B | fail: the mechanical certificate algorithm and the supposed compact route are the same gcd formula, with no compression gap |

The previously built module is retained as `rejected_gen_1403_0679.py`, as required. It is evidence of the attempted family, not a shippable generator.

## Step 0 findings

Definition 2.11 defines the lattice basis ideal from the two columns of an integer matrix. Example 3.6 identifies the Andean monomial primes as pairs of linearly dependent rows in opposite open quadrants. Theorem 2.8 gives the band threshold and residue structure explicitly in terms of a gcd. Theorem 5.1 then states the relevant primary component itself:

for a positive target row `(r,s)`, its opposite multiple `-lambda(r,s)`, and `d = gcd(r,s)`, the minimal monomial generators have exponent pairs

```text
(k*d, lambda*(r+s-(k+1)*d)),  k = 0,...,(r+s)/d-1.
```

Thus the algorithm that produces the certificate is:

1. normalize the target-row signs;
2. compute `d = gcd(r,s)` and the exact multiplier `lambda`;
3. emit the displayed progression.

Its complexity is `O(log(max(r,s)) + T)` exact integer operations, where `T=(r+s)/d` is also the number of output monomials. No primary decomposition, graph search, Gröbner basis, or ideal-containment search is needed on this distribution.

## Mechanical cost versus compact route

The attempted shipping preset used a `3 x 2` matrix and `T=16` output terms.

| route | measured/estimated cost at that preset |
|---|---:|
| paper's Theorem 5.1 algorithm | 115--117 conservatively counted exact operations; median 0.00000674 s over eight seeds |
| compact route after seeing the gcd-residue structure | the same 115--117 operations and the same 16 emitted terms |
| obsolete draft scan | median 2,327,105 operations, but only because it tested every integer exponent despite already knowing that eligible exponents are multiples of `d` |

The obsolete scan is not a valid Track B reference algorithm. Replacing `range(0, x_max+1)` plus a divisibility test by `range(0, x_max+1, d)` reduces it immediately to the theorem's 16 iterations. The mechanical-to-compact ratio is therefore approximately `1`, not approximately `20,000`.

This is exactly the discriminating failure in the task specification: the certificate is the output of a tiny explicit algorithm run on the instance. Scaling the gcd only makes the printed exponents larger; it does not increase the number of algorithmic steps. Scaling `T` would lengthen the answer, so it cannot create a hidden haystack while keeping the witness fixed.

## Other native routes considered

- Theorem 2.8's band-graph question is even smaller: the first width with an infinite component is `r+s-gcd(r,s)`. Its mechanical and compact routes again coincide.
- Proposition 5.6 and Theorem 5.7 explicitly describe the Andean arrangement after dependent row pairs are found. Pair detection is polynomial by normalizing row directions and hashing them. A shorter route would have to come from an artificial planting pattern not supplied by the paper, so it would test the generator rather than the paper's mathematics.
- The prior-triage proposal to intersect chosen primary ideals does not work by construction: an arbitrary such intersection need not be a codimension-two lattice basis ideal. Certifying equality and primaryness in the general case requires ideal operations such as Gröbner bases or saturation, which would solve the generated instance rather than carry a paper-provided certificate into it.

## Why no oracle hardening was used

Step 0 already rejects the family on H, before the LLM loop. Earlier transcript files are retained because the draft had reached that stage, but every recorded call is an HTTP 403 quota error and none is hardness evidence. The rejection does not rely on G9 or on an oracle outcome.
