# Rejected: arXiv 2410.14605

## Decision

No problem family in the paper clears G, H, and V simultaneously. The most
promising native family clears G and V but fails **H on Track B** under the
required hardening loop. Track A is not claimed: the paper proves universality
and almost universality of fixed ternary quadratic sums, not hardness of finding
representations for the inverse-generated distribution.

The retained implementation is `rejected_gen_2410_14605.py`, and the
script-written evidence is `llm_loop_transcript.jsonl`.

## Paper triage

Section 1 defines a universal integer-valued polynomial by equality of its value
set over integer tuples with the nonnegative integers. Section 2 defines
equivalence of two such polynomials as equality of their represented sets.
Theorem 1.1 turns identities of products of Ramanujan theta functions into
equalities between representation counts and hence transfers universality or
almost universality. Its proof compares coefficients; it does not construct an
individual representation on the other side.

The only theorem-level object in the paper that yielded a scalable, exact
certificate by construction was the Section 2 equivalence (Lemma 2.1(ii),
equation labelled `513`)

\[
p_3(x)+p_3(y)\sim \frac{x(5x+1)}2+\frac{y(5y+3)}2.
\]

The retained generator composes this identity with a third triangular term and
carries a known representation across the equivalence. Completing squares turns
the conversion into multiplication by a Gaussian integer of norm five. The
candidate witness is an integer triple, and verification is exact substitution.
Thus it is native number theory, not a graph or finite-field surrogate.

The other apparent routes fail earlier:

- Sampling a triple and publishing only its value gives inverse generation and
  exact verification, but the solver has no compact route to recover a triple.
  It is pure representation search. The paper supplies no distributional
  hardness theorem for Track A, so cardinality alone cannot establish H.
- Theorem 1.1 and the theta-product identities guarantee positive representation
  counts, but coefficient comparison supplies no individual tuple. Generating a
  witness from those existence statements would require solving the generated
  representation instance, so G fails.
- Asking for universality itself would require an unbounded mathematical proof,
  not a finite witness that the checker can inspect, so V fails.

## Mechanical cost and compact route

This rejection is not based on the mere existence of an efficient algorithm.
The candidate was explicitly evaluated as Track B.

At the retained shipping candidate (`n=100000`, 12 independent rows), the
standard bounded exact pair enumeration with a triangular-discriminant test
solved 8/8 measured instances. It used a median of **5,080,805.5 pair probes**
(maximum 7,221,628) and **1.3901 seconds** median wall time (maximum 2.1104 s) in
Python. Counting the six integer operations used per probe gives roughly
**30.5 million elementary exact operations** at the median. The worst-case bound
is quadratic in the coordinate range per row.

The compact route completes the paired terms to odd squares, applies one of the
norm-five Gaussian coordinate maps, fixes signs/order by residues modulo 10,
and copies the unchanged triangular coordinate. The retained accounting is at
most **24 exact arithmetic operations per row, 288 operations for all 12 rows**.
That is a genuine mechanical/compact gap and therefore was worth a Track B
build.

It nevertheless fails H in the actual no-tool evaluation. The official bare
hardening transcript contains verified solutions at every attempted magnitude:

| preset | parameters | verified oracle solutions |
|---|---:|---:|
| easy | `n=100000, rows=12` | 3/3 |
| medium | `n=180000, rows=12` | 2/3 |
| hard | `n=300000, rows=12` | 2/3 |
| escalated | `n=600000, rows=12` | 2/3 |

Each rung is defeated when any oracle solves it. Nine of the twelve calls
returned witnesses accepted by the exact verifier. Several replies explicitly
identified the odd-square identities and Gaussian norm-five factorization.
Increasing the coordinate magnitude only enlarges the enumeration haystack; it
does not increase the 288-operation compact route, so further escalation on that
axis cannot repair the failure. Lengthening the answer enough to turn the task
into bulk arithmetic would test transcription and exceed the intended-route
budget rather than test the paper's structural insight.

## Failed gate

- **G:** passes for the retained candidate by a structure-preserving
  transformation of a held certificate.
- **V:** passes by exact integer range checks and polynomial substitution.
- **H / Track A:** unavailable; no cited theorem establishes hardness for the
  generated distribution.
- **H / Track B:** fails; the compact route was repeatedly executed without tools
  by the multi-vendor oracle pool, even after three magnitude escalations.

Accordingly, no module is shipped. The rejected module and its hardening evidence
are kept so this decision can be reproduced or revisited.
