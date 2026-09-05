# Rejection: arXiv:1808.10677

Paper: Thomas Fernique, Amir Hashemi, and Olga Sizova, [*Empilements
compacts avec trois tailles de disque*](https://arxiv.org/abs/1808.10677),
version 2 (2018).

## Decision

No generator is shipped.  **G and V are possible, but H fails on Track A, and
the paper does not supply the mechanical/compact gap needed for Track B.**  This
decision is based on the full 30-page paper, its LaTeX source, and the seven Sage
programs linked in Appendix B, not on the abstract.

The paper's native problem fixes the largest radius to 1 and classifies the
pairs `0 < s < r < 1` for which a compact three-radius disk packing exists.  A
packing is compact precisely when disk interiors are disjoint and the contact
graph of tangent disks is triangulated (Sections 1--2).  Theorem 1 proves that
there are exactly **164** admissible normalized pairs.  Appendix A explicitly
exhibits one periodic packing for every pair, and Appendix B's
`empilements.sage` stores the 164 construction records.

Consequently the native normalized answer set is finite and tiny: uniform
guessing already succeeds with probability `1/164 = 0.006097...`, far above the
required `1e-6`.  Looking the answer up in the classification table is at most
164 comparisons.  If the requested witness is the packing rather than the
radius pair, the same lookup returns a complete Appendix B construction record:
the downloaded source contains 164 records of only 5--33 items (the maximum is
`rrrr / 11rrsr`).  Thus the reference algorithm costs at most 164 key
comparisons plus copying at most 33 record items.  Its compact route is the same
lookup-and-copy operation, not a hidden invariant.  Random scaling, rigid
motion, relabelling, or use of a larger period cell does not change `(r,s)` after
normalization and must be collapsed by an honest canonical key.  Treating the
scale as part of the answer does not help: one known center distance or one
known disk radius recovers it by a single division.

## STEP 0: what produces the certificate?

The original classification is computer-assisted, not a source of an unlimited
hard distribution.  Sections 3--5 turn small and medium corona angle sums into
integer bivariate polynomials.  Section 6 computes resultants, isolates real
roots, filters them with interval arithmetic, and finally checks the exact angle
equations.  Sections 7--9 add combinatorial exclusions.  Appendix A then gives
the certificate for every surviving case as an explicit periodic construction;
Appendix B says that `empilements.sage` is the encoding of all 164 such
packings.

The paper reports the following mechanical costs for the *one-time
classification*:

- generating all 1,654 medium-corona polynomials took 2 h 21 min; their average
  degree was 57 and the maximum was 416 (Section 5, footnote 2);
- the direct exact solve for coronas `111rr / 111rrs` took 1 h 21 min, whereas
  the resultant plus interval filters handled that example in about 15 s
  (Section 6);
- the one-small-corona branch produced 469,808 candidate pairs in under 4 min,
  and its exceptional Groebner-basis computation took 45 min (Section 9);
- for `11rrs / 11rrs^12`, merely producing the degree-416 polynomial took 6
  min and the resultant exceeded the authors' available memory (Section 6).

Those numbers do not create a Track B family.  For corona pairs on which this
mechanical route is expensive, neither the theorem nor its proof gives a short
instance-local invariant that recovers `(r,s)`.  The only short alternative is
to consult the completed 164-row classification, which is an external lookup,
not a witness derivable from the rendered instance.

## Why the proposed hidden-packing family also fails H

The triage suggestion was to choose an Appendix A periodic packing and hide its
radii and fundamental cell.  There are only two honest renderings, and neither
has a Track B gap.

1. If enough exact geometry is rendered for the checker to verify tangency and
   non-overlap, radii are recovered locally.  For a tangent triangle with center
   distances `d12`, `d13`, and `d23`,

       rho1 = (d12 + d13 - d23) / 2,
       rho2 = (d12 + d23 - d13) / 2,
       rho3 = (d13 + d23 - d12) / 2.

   The mechanical algorithm and the compact route are the same: select one
   triangular face and perform 9 exact additions/subtractions/divisions for its
   three radii, then propagate `rho_j = d_ij - rho_i` once per remaining disk.
   On `N` disk orbits this is at most `N + 9` arithmetic operations.  Enlarging
   a periodic patch only pads this linear pass; it does not hide a shorter
   mathematical idea.

2. If the Appendix B construction record is rendered, its format explicitly
   marks a repeated disk by a fourth tuple entry.  The supplied `domaine`
   routine scans the record once and obtains a period by subtracting the marked
   old center from the new center.  The mechanical cost for a record of length
   `N` is `N` marker checks plus four coordinate subtractions for the two
   periods.  The compact route is exactly those same two marked subtractions.
   Again there is no meaningful gap.

If exact centers, contact lengths, and duplicate markers are withheld, the task
reverts to solving the corona polynomial system from Sections 4--6.  Its
mechanical costs can be large, but the paper gives no compact route shorter than
that computation.  Adding a secret encoding, decoy radii, or an artificially
large supercell would therefore create an obfuscated inverse problem not
studied in the paper; it would not turn this classification theorem into a
self-contained no-tool compression task.

## Gates

| Gate | Result | Reason |
|---|---:|---|
| G | possible | The 164 Appendix A packings are theorem-backed certificates, and similarities/supercells carry them forward. |
| H, Track A | **fail** | Complete 164-case classification and explicit construction table; normalized guess probability is about 0.0061. |
| H, Track B | **fail** | With exact packing data, mechanical and compact routes are both `N + 9` operations (or one marker scan); without those data, no compact route is provided. |
| V | possible | Exact algebraic radii, center distances, periodic translations, non-overlap, tangency, and local triangulation can in principle be checked symbolically. |

The failure is intrinsic to turning this paper's classified objects into the
required unlimited hard distribution, not an answer-length cap and not the
retired G9 hinted-arm diagnostic.  No generator was written, so there is no
`rejected_gen_1808.10677.py` to preserve.
