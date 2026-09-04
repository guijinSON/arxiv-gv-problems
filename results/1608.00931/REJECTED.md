# Rejected at Step 0

Paper: Alberto Borobia and Roberto Canogar, [*The real nonnegative inverse
eigenvalue problem is NP-hard*](https://arxiv.org/abs/1608.00931).

No generator is shipped. The paper was read in full, including the definitions
in Sections 1--3, the reductions in Section 4, and the certificate discussion in
Section 5. The two plausible families fail different mandatory gates.

## 1. Native RNIEP witness: fails V or lacks H

The native search task would give a real spectrum and ask for an entrywise
nonnegative matrix having that spectrum. Section 5 explicitly says that NP
membership of the rational RNIEP is unknown: even for rational eigenvalues, a
realizing matrix may have real entries, and the paper does not provide a finite
exact representation whose spectrum can always be checked in polynomial time.
The paper asks whether a rational realizing matrix must exist; it does not prove
that it does.

Inverse-generating a *rational* nonnegative matrix and publishing its exact
characteristic polynomial would repair G and V for that restricted subfamily:
the planted matrix is known by construction and Bareiss polynomial arithmetic
can compare characteristic polynomials exactly. It does not repair H. Theorem
4.2 proves worst-case NP-hardness through a particular reduction from
PARTITION; it says nothing about the distribution of spectra of sampled
nonnegative rational matrices. Claiming Track A for that distribution would
therefore substitute worst-case hardness for distributional hardness. The
paper also supplies no compact structural reconstruction route that could
justify Track B, and a matrix large enough to support a serious search would
conflict with G9(c)'s 256-atom/2,000-character answer cap.

## 2. Suleimanova--Perfect certificate: G and V pass, H and G9 do not

Lemma 4.1 maps a PARTITION instance

`I = (i_1, ..., i_n)`

to the rational spectrum

`(S/2, S/2, -i_n, ..., -i_1)`, where `S = sum(I)`.

A yes certificate is a partition of the negative eigenvalues into two
Suleimanova lists of sum zero. Section 5, Theorem 5.4 proves that membership in
the Suleimanova--Perfect criterion is NP-complete and that such a partition is
a polynomially checkable certificate. This is the paper's strongest candidate
for an exact bounded witness family.

To make only yes-instances without solving them, however, the generator must
plant an equal partition first. That creates a *planted number-partitioning
distribution*. Neither Lemma 4.1 nor Theorem 5.3 proves that this distribution
is hard; they establish worst-case hardness for unrestricted inputs. Random
number partitioning has strongly regime-dependent behavior, including a
phase transition controlled by the number of value bits per item, so an
unspecified random/planted regime cannot inherit the theorem's hardness.

The standard attacks are pseudo-polynomial subset-sum dynamic programming,
meet-in-the-middle/complete differencing, and lattice reduction in low-density
regimes. Choosing values merely large enough to make those mechanical attacks
costly would still leave no compact route after the intended insight: the
solver would have to perform the partition search itself. That violates
G9(c)'s requirement that the intended route take at most 300 exact arithmetic
operations. Conversely, adding a visible pairing or digit invariant to create
a compact route gives a polynomial-time method for the generated distribution
and invalidates Track A; under Track B it becomes the obvious in-context attack
and is expected to solve the instance, conflicting with the required failing
attack panel and likely the structurally hinted G9(b) run.

## Gate summary

| proposed family | G | H | V | decisive issue |
|---|---:|---:|---:|---|
| arbitrary native RNIEP | unclear | worst-case only | fail/unknown | Section 5 gives no generally finite exact matrix witness |
| inverse-generated rational matrix | pass | fail | pass | no hardness theorem or measured basis for this distribution |
| planted SP/PARTITION certificate | pass | fail | pass | Theorem 5.4 is worst-case; planting does not preserve that claim |
| planted SP with an exposed shortcut | pass | Track A fail / Track B too easy | pass | shortcut is itself an efficient attack on the distribution |

Because no candidate clears G, H, V, and G9 simultaneously, creating
`gen_1608_00931.py`, `selftest_report.json`, or oracle transcripts would turn a
known Step 0 failure into misleading artifacts. They are intentionally absent.
