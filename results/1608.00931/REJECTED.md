# Rejected: arXiv:1608.00931

## Decision

The attempted family passes **G** and **V**, but fails **H on Track B**, specifically
the mandatory polarity-flipped gate G9(b).  It must not ship.

The family uses the paper's own objects and reduction.  Section 2 defines the
Suleimanova--Perfect (SP) criterion.  Section 4, Lemma 4.1 maps a positive integer
list `I` to the real spectrum

`(sum(I)/2, sum(I)/2, -i_n, ..., -i_1)`

and proves that an equal partition of `I` gives two Suleimanova sublists.  Section
5, Theorem 5.4 identifies such an SP partition as a polynomially checkable
certificate and proves the rational SP-membership problem NP-complete.  Inverse
generation from composed four-term identities therefore gives a valid witness
without solving the generated instance, and `verify` checks it by exact integer
summation without consulting the plant.

## Why neither hardness track survives

Track A was never supportable for this distribution.  Every generated instance has
a deliberately public construction-specific decoder: reducing the magnitudes
modulo 997 yields four-element buckets, and one of the three pairings in each bucket
has equal sum.  The decoder is expected linear time and recovered a verified witness
on 8/8 shipping instances.  The paper's NP-completeness theorem is worst-case and
does not make this inverse-generated distribution hard.

Track B initially looked viable because the construction-blind mechanical route was
much larger than the compact route:

| attempted rung | mechanical cost | compact route |
|---|---:|---:|
| `n=36`, 32-bit payloads | fixed-cardinality Horowitz--Sahni meet-in-the-middle; 141,506--266,452 measured state operations per instance, about 0.05--0.08 s | residue buckets and local pair tests; at most 90 exact operations |
| `n=64`, 48-bit payloads | `2^31 + 2^32 = 6,442,450,944` required half-subset states; a measured 1,048,576-state prefix took 0.092 s (full extrapolation is roughly 566 s before memory overhead) | residue buckets and local pair tests; 124 operations on the G9 instance and at most 160 by the declared bound; 8/8 solved in 0.000175 s total locally |

Those figures establish a real mechanical/compact gap, but G9(b) asks the more
important question: does the family still defeat the oracle pool once the compact
insight is stated?  It does not.

- At `n=36`, the bare three-vendor run hardened, but **all 3/3 structurally hinted
  vendors solved**.  This triggered the one permitted move up the preset ladder.
- At `n=64`, an `openai/gpt-5.6-terra` oracle given the required one-sentence hint
  returned a certificate that parsed and verified exactly.  One success is enough
  to fail G9(b).

The prompt permits only one upward move after a hinted failure.  Retuning the
modulus, obscuring the decoder, or escalating again would fit the generator to the
observed oracle run, so none was attempted.

## Other routes considered

The prior triage suggestion--sample a nonnegative matrix and publish its real
spectrum--does not repair this result as stated.  Section 5 explicitly notes that
for a rational spectrum the obvious realizing matrix certificate can have real
entries, and polynomial-time exact verification is not established in general
(the paper does not even place rational QNIEP in NP).  Restricting to an easily
serialized rational matrix would make construction and verification possible, but
the sampled matrix itself would be a direct planted answer and the obvious structured
matrix families considered here offered no independently supported hardness
distribution.  Group-1 criteria are also excluded by Theorem 5.3, which places their
rational decision problems in P via at most quadratic-time inequality checking.

Accordingly, the reviewed paper supplies a sound generatable and verifiable SP
certificate family, but the tested construction is too responsive to its own
structural hint to qualify for this benchmark.
