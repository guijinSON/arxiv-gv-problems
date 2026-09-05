# Rejected: arXiv 1705.09517

Paper: Pasin Manurangsi and Aviad Rubinstein, [*Inapproximability of VC
Dimension and Littlestone's Dimension*](https://arxiv.org/abs/1705.09517).

## Decision

No generator is shipped.  The natural VC-dimension family clears **G** and
**V**, but it does not clear **H on Track A or Track B**.  The Littlestone
alternative also exceeds the witness-size cap in the regime where the paper's
hardness theorem applies.

This decision is based on the full paper, especially Section 2's definitions,
Theorems 1 and 13, Section 3.1 (the failed candidate reduction), Theorem 21,
and Appendix A / Theorem 32.  It is not based on the abstract.

## Step 0: what produces the certificate?

For VC dimension, the native instance is an explicit binary incidence matrix:
rows are universe elements and columns are concepts.  A valid witness is a
size-`d` set of rows whose column restrictions contain every one of the `2^d`
binary patterns.  Checking a proposed set is exact and costs
`O(d * |C|)` bit inspections (or the corresponding word operations).  Thus V
is excellent.

The general certificate-producing method is the quasi-polynomial algorithm
identified in the Introduction: enumerate all row subsets up to
`d <= log_2 |C|` and check their traces.  Its straightforward cost is
`O(|U|^d * d * |C|)`.  Unlike an SDP, spectral formula, or linear solve, this
does not by itself kill Track A.  The problem is that Theorem 1 is a
worst-case rETH lower bound, while a generator must justify hardness for the
particular distribution it emits.

For Littlestone dimension, the native positive witness is a full depth-`d`
mistake tree.  It has `2^d - 1` internal-node labels.  Theorem 21's completeness
depth is `2rk`; an explicit native tree therefore crosses the 256-atom answer
cap once `2rk >= 9`, long before the theorem's sufficiently-large-`r` regime.
Appendix A's Theorem 32 gives the exact recursive algorithm with running time
`O(|C| * (2|U|)^d)`; it does not provide a bounded generic tree certificate.

## Why the prior-triage family fails Track A

The proposed inverse generator—plant a shattered row subset and add decoy
concepts—does know its witness without solving the output instance, so G holds.
It is not the distribution in Theorem 1 or Theorem 13.  Theorem 13 obtains its
gap by reducing a bi-regular Label Cover instance in a particular parameter
regime (`r = sqrt(n)/log n`, completeness at least `2r`, and soundness at most
`(1+delta)r` when `val(L) <= delta^2/100`).  Its proof compares satisfiable and
low-value Label Cover inputs.  It says nothing about recovery on matrices
conditioned to contain an independently planted shattered set.

That distinction is observable, not merely formal.  In a prototype with
`|U|=60`, `d=8`, and `|C|=256`, the planted rows supplied all 256 traces and
balanced random rows were used as decoys.  A structure-aware backtracker that
enforces the necessary trace-balance condition recovered the planted witness
in 1,340 nodes / 0.069 seconds and 1,255 nodes / 0.064 seconds on seeds 0 and 1.
Those runs performed 343,040 and 321,280 column-trace updates respectively
(256 updates per expanded node).
This is precisely the kind of planting signature the required adversary panel
is meant to catch.  Adding random concepts weakens exact balance, but then no
theorem in the paper establishes hardness for the resulting planted
distribution.

Using Theorem 13 directly does not repair the claim.  Its completeness proof
does give a witness by construction,
`S_sigma = {x_(i,sigma|U_i) : i in [r]} union Y`, when a satisfying Label Cover
assignment is already held.  However, inverse-planting that Label Cover
assignment again creates a new planted-yes distribution not covered by the
rETH reduction.  Starting from the Moshkovitz--Raz PCP of Theorem 10 would
preserve the worst-case promise, but it does not manufacture an unlimited
distribution of satisfiable source instances with known assignments and a
distributional hardness guarantee.

Accordingly, a `TRACK = "A"` module would be asserting a hardness basis the
paper does not prove and the baseline experiment contradicts for the direct
planting proposal.

## Why it also fails Track B

Track B needs a short mathematical route after an insight, not merely a large
mechanical search.  For a generic explicit concept matrix, the paper's route to
a shattered set is the same subset enumeration just described.  In the
prototype, the mechanical route took about 0.07 seconds and 1.3k search nodes;
the only available by-hand route was the same balance propagation, i.e. about
321k--343k column-trace updates.  Even checking one already-guessed full
candidate takes `8 * 256 = 2,048` membership inspections, already beyond the
300-operation cap; it does not identify which candidate to check.
There is no shorter invariant in the paper that identifies the planted rows.
The mechanical and compact routes are thus comparable—the supposed compact
route is simply the mechanical search executed by hand.

It is possible to add an external marker (special row ordering, affine labels,
de Bruijn blocks, checksums, or a supplied correlation table) so that the
planted rows can be read off in a few dozen operations.  That would make a
Track B puzzle, but its difficulty would come from recognizing builder-added
metadata, not from the VC or Littlestone objects or any construction in this
paper.  A construction-aware attack would use the same marker.  Shipping that
as native coverage would therefore be misleading.

## Gate summary

| Candidate | G | H-A | H-B | V | Other blocker |
|---|---:|---:|---:|---:|---|
| Direct planted shattered subset | pass | **fail** | **fail** | pass | standard balance search exposes the plant |
| Theorem 13 reduction from an inverse-planted Label Cover instance | pass | **fail** | **fail** | pass | theorem does not cover the planted source distribution; no compact recovery route |
| Theorem 21 Littlestone mistake tree | pass in completeness case | not reached | not reached | pass | explicit witness exceeds G9(c)'s 256-atom cap |

The failed gate is therefore H for both available tracks (and G9(c) for the
native Littlestone witness).  No `gen_1705_09517.py` was written, so there is no
partially built module to retain under a `rejected_gen_` name.
