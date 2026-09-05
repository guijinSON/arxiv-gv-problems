# Rejected: arXiv:1001.3573

The attempted family is rejected at **G9(b) on Track B**.  This is not a
failure of generation or verification: both of those parts work exactly.

## What was tested

The native problem is to find a finite integral point on
`C_k: Y^2 = X^6 + k`.  Section 1 defines the genus-two curve, and Section 2
gives the integral model `x^6 + k y^6 = z^2`.  Near the end of Section 5 the
paper gives the identity

`k = a^12/4 + 1`, with the point `(X,Y) = (a, 1 + a^6/2)` for even `a`.

The retained generator samples `a` first and constructs `k`, so G passes by
composition of identities.  Verification is the exact executable check
`Y^2 == X^6 + k`, so V passes and accepts any bounded valid point.

## Track decision and costs

Track A is not defensible.  Section 5 itself produces the certificate by an
explicit formula, and the paper's Sections 2--4 also describe rank,
congruence, and elliptic-Chabauty methods for its small-`k` cases.  There is no
paper theorem establishing distributional hardness for the inverse-generated
values of `k`.

Track B was tested rather than rejected merely because an algorithm exists.
At `n = 30,000,000`, the mechanical reference algorithm was a
congruence-sieved bounded-height enumeration.  Over eight seeds it visited a
median **24,308,149** candidate X values, performed a median **3,431,143** exact
square tests, and took **4.45 seconds** on this machine.  Its complexity is
`O(n M(log k))` up to multiplication factors, and it solved 8/8 as expected.
The compact route takes the neighboring square above `k`, subtracts `k`, and
extracts an exact sixth root; the instrumented maximum was **212 exact
arithmetic operations**.  Thus there is a real mechanical-versus-compact gap,
which is why the family was evaluated on Track B.

## Failing gate

The bare oracle arm at `n = 30,000,000` was hardened (0/3 solved).  With the
compliant one-sentence structural hint, "The two neighboring-square gaps
around k conceal an exact sixth-power relation," one oracle returned an exact
verified point: **1/3 solved**.  The family therefore fails the polarity-flipped
G9(b) gate.  The successful response is preserved in
`g9_hinted_medium_transcript.jsonl`.

A one-rung bare retry at `n = 100,000,000` was hardened 0/3, but the matching
hinted retry could not obtain a scored response because the OpenRouter key hit
its total limit; the 403 records are preserved in `g9_hinted/`.  I do not count
those API errors as model failures.  I also do not use the larger rung to
rescue the family: it changes only the number of digits, while the hint exposes
the same exact-root procedure.  Further escalation would test unaided
big-integer arithmetic rather than discovery of the paper's structure.

The placebo arm was not run after the key limit.  It is diagnostic rather than
gated and cannot repair the observed G9(b) failure.

## Why the other obvious family does not replace it

Choosing arbitrary rational `X,Y` and setting `k=Y^2-X^6` also clears G and V,
but supplies neither a paper-backed Track A hardness result for that generated
distribution nor a short solver-visible Track B route.  Asking for *all*
rational points would match the paper more closely, but a returned list is not
an executable completeness certificate, so it fails the witness rule.

Paper: [Bremner and Tzanakis, *On the equation Y^2 = X^6 + k*](https://arxiv.org/abs/1001.3573).
