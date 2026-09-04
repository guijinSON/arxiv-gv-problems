# Rejected: arXiv:2602.19989

Paper: Simone Costa and Stefano Della Fiore, [“New bounds for (weak)
sequenceability in Z_k”](https://arxiv.org/abs/2602.19989).

## Decision

The native family was buildable, but it fails the mandatory G9(b) hinted-oracle
gate on **Track B**.  I therefore reject it rather than ship a family that tests
only whether the solver was told the trick.

G and V do not fail.  The generator inverse-generated an ordering in the
paper's native cyclic-group objects, and the checker independently verified the
permutation, every exact modular partial sum, all pairwise distinctness, and the
required nonzero sums.  The failed component is H as operationalized by Track
B's no-tool requirement and, specifically, the polarity-flipped G9(b) gate.

Track A is not available as a fallback.  This planted distribution has an
efficient exact recovery algorithm, and the paper supplies no average-case
hardness result for it.  Calling it Track A would hide the very algorithm that
solves the generated distribution.

## Paper triage

Section 1 fixes the exact witness: for an ordering a_1,...,a_n, the partial sums
p_1,...,p_n must be pairwise distinct, and p_1,...,p_(n-1) must be nonzero.  The
final sum may be zero.  Theorem 1.3 proves classical sequenceability only in the
sparse regime |A| <= exp(c(log p)^(1/3)); Theorem 1.4 gives the corresponding
t-weak existence regime.  Lemma 2.7 produces existence with positive
probability via the one-shot random construction and the Lovasz Local Lemma; it
is not a displayed polynomial-time certificate-output algorithm.

The easy/proved regimes stated in the introduction also matter: earlier work
covers |A|<=12, log(p)/log log(p), and exp(c(log p)^(1/4)) ranges.  A random set
in those very sparse regimes would make collisions rare and random orderings
too successful.  The attempted generator therefore used dense sets, with
n=128 in Z_137 and then n=160 in Z_167, and knew a sequencing by inverse
generation rather than by invoking the asymptotic theorem.

## Construction and algorithm audit

For a primitive root q modulo the prime k and nonzero u, the planted ordering
was

    a_i = u(q-1)q^i,  0 <= i < n.

Its j-th partial sum is u(q^(j+1)-1), so primitivity gives an exact certificate
without search.  The public instance retained only the unordered set A.

An efficient algorithm exists for this distribution.  The mechanical reference
algorithm counts all pairwise modular quotients in A, identifies the ratio with
n-1 consecutive occurrences, and walks the multiplicative cycle.  Its
complexity is O(n^2 log k).  Measured costs were:

| attempted rung | mechanical operations | mechanical wall time | compact route |
|---|---:|---:|---:|
| n=128, k=137 | 17,672 | 0.000874 s | 201 exact operations |
| n=160, k=167 | 27,208 | 0.001349 s | 203 exact operations |

The compact route observes that only k-1-n nonzero residues are absent.  Those
few missing residues form the complementary geometric run, so pairwise
quotients need be computed only in the short complement before continuing the
cycle through A.  This real mechanical-versus-compact gap justified trying
Track B; the family is **not** rejected merely because an efficient algorithm
exists or because the compact route is the same length.  It is rejected because
models actually executed the compact route once the structural hint named it.

## Measured gate evidence

Before the oracle test, the n=128 rung had 0 valid random permutations in
200,000 structure-aware samples.  Each of four attacks had 0 successes over 8
seeds: increasing residue order, smallest-feasible greedy, 256 randomized
feasible-prefix restarts, and alternating low/high residues.  The successful
reference algorithm was correctly reported separately.  The serialized answer
used 414 characters (128 atomic elements), and the intended route used 201
counted exact operations, so G9(c) was within all caps.

The bare hardening run at n=128 held: 0/3 vendors returned a verified witness.
The structural-hint run at the same rung did not hold: Gemini, Grok, and
GPT-5.6-terra each returned a verified witness, for **3/3 solved**.  I used the
single rung increase allowed by G9(b).  At n=160, k=167, the first completed
hinted attempt (Gemini, seed 1985518726) again returned a verified witness.
That is already sufficient to fail the rung, so the remaining paid calls were
stopped.

Thus the hint failed G9(b) both at the original shipping rung and after the one
permitted upward move.  The task explicitly requires rejection at that point;
no further hand-tuning or escalation is justified.
