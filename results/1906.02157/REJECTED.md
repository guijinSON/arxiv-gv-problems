# Rejected at STEP 0: arXiv:1906.02157

Paper: William M. Brummond, [“Kirkman Systems that Attain the Upper Bound on
the Minimum Block Sum, for Access Balancing in Distributed
Storage”](https://arxiv.org/abs/1906.02157).

## Decision

The paper-backed family suggested by triage—construct an optimal-minimum-sum
Kirkman system—passes **G** and **V**, but fails **H on both tracks**. No module
was written because the failure is stated by the paper's main construction,
before any generator work is needed.

- **G passes:** Section 3.2, Theorem 3.1 triples a known `KTS(n)` with
  `min_sum=n` into a certified `KTS(3n)` with `min_sum=3n`; Corollary 3.1.1
  starts at `KTS(3)` and iterates it. Section 3.3, Theorem 3.4 and Corollary
  3.4.1 give the analogous doubling construction for `KQS(4*2^k)`.
- **V passes:** a proposed system can be checked exactly by counting blocks,
  checking that every pair (KTS) or triple (KQS) occurs once, checking every
  parallel class partitions the point set, and comparing integer block sums
  with the stated bound.
- **Track A H fails:** the certificate is produced directly by the explicit
  formulas in Theorems 3.1 and 3.4. The paper proves existence by writing down
  the blocks and their parallel classes; it gives no hard search problem,
  hardness theorem, or hard parameter regime. A generator using those formulas
  would knowingly ship an efficiently constructible distribution.
- **Track B H fails:** the compact route is not shorter than the mechanical
  route. The only structural insight is “apply the displayed tripling (or
  doubling) formula,” after which the solver must perform the same arithmetic
  and transcribe the same full design as the reference construction. There is
  no hidden invariant, change of variables, or symmetry that compresses a
  substantially larger mechanical computation.

## Required mechanical-cost versus compact-route comparison

For the KTS route, a `KTS(N)` contains `N(N-1)/6` triples. Applying Theorem 3.1
from order `n` to order `N=3n` uses `2n + 18*n(n-1)/6` nonzero coordinate
offsets and emits `N(N-1)/2` integer coordinates. Direct measurement of the
JSON-native nested list gives:

| output order | blocks | answer atoms | compact JSON chars | additions in final lift |
|---:|---:|---:|---:|---:|
| 3 | 1 | 3 | 11 | 0 |
| 9 | 12 | 36 | 105 | 24 |
| 27 | 117 | 351 | 1,184 | 234 |
| 81 | 1,080 | 3,240 | 11,561 | 2,160 |

Thus the largest nontrivial KTS witness within G9(c)'s 256-atom cap is order
9. Its **mechanical cost** is 24 integer additions plus writing 36 labels. Its
**compact route** is exactly the same 24 additions and 36 labels; the gap is
zero. Moving to order 27 does not create a valid Track B benchmark: although
the final lift is still only 234 additions, its 351-atom answer already violates
the witness cap. Order 81 violates both the atom cap and the 300-operation cap.

The quadruple route has the same obstruction. `KQS(8)` has 14 blocks and 56
coordinate atoms and is explicitly listed in Appendix D; the very next order,
`KQS(16)`, has 140 blocks and 560 coordinate atoms, already beyond G9(c).
Theorem 3.4 is itself the mechanical and compact construction in both cases.

These costs are comparable because outputting the requested native object is
the work: every compact route still has to spell out every block and every
parallel class. This is not a Track B compression task.

## Why no surrogate family was substituted

One could hide point labels, delete a parallel class, or present a subset of
blocks as an exact-cover puzzle. Those transformations would manufacture a
different reconstruction/search problem. The paper neither studies their
complexity nor supplies a parameter regime for them, so their hardness would
come from the benchmark encoding rather than Theorems 3.1 or 3.4. In
particular, the prior-triage verifier (“check blocks, parallel classes, and every
block-sum threshold”) verifies the full explicit construction and does not
repair its failure of H.

Accordingly, this is a genuine **H rejection**, not `cap_bound`: the only
cap-compliant native instances are already solved by the same short formula,
and increasing order merely makes the uncompressed witness too long.
