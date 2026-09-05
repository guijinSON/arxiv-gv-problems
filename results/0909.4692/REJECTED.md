# Rejected: Planar Subgraph Isomorphism Revisited (arXiv:0909.4692)

## Decision

The attempted family passes **G** and **V**, but fails **H on Track A**.  It
plants a spanning cycle in a planar cubic host, carries that cycle through a
random relabelling, and verifies a submitted cyclic vertex map by exact edge
membership.  The failure is distributional hardness: a construction-aware
local-constraint attack returns a verified Hamiltonian cycle on 7 of 8 audit
seeds at both the proposed shipping size and the largest named preset.

Track B was considered before rejecting.  It does not rescue this family:
recognising the relevant invariant only reformulates the same exponential
search, so there is no short, executable post-insight route.

## Paper evidence and parameter regime

Section 2 defines subgraph isomorphism as an ordinary, non-induced subgraph
copy, so the planted host's extra matching edges are legal.  The Introduction
states that Subgraph Isomorphism remains NP-complete on planar graphs and names
Hamiltonicity as a special case.  That is worst-case evidence, not evidence for
the generated distribution.

Theorem 1 is the decisive easy-regime result: for a planar host on `n` vertices
and a pattern on `k` vertices, the paper constructs, counts, and enumerates
copies in `2^{O(k)} n` time.  The attempted family therefore set `k=n` rather
than keeping the pattern fixed.  Section 5 and the appendix implement the bound
with sphere-cut decomposition and embedded dynamic programming; the appendix
gives explicit upper bounds `2^(21.02 k) n` for plane patterns and
`2^(27.26 k) n` for general planar patterns.  Those bounds do not imply that a
random planted subclass is hard.

## The attack that breaks the family

The host is made from an even spanning cycle plus two noncrossing perfect
matchings, one on the even cycle positions and one on the odd positions.  Give
alternate cycle positions bits 0 and 1.  Every vertex then has two
opposite-bit cycle neighbours and one same-bit matching neighbour.  Equivalently,
every closed neighbourhood `{v} union N(v)` contains exactly two zeroes and two
ones.

The retained module implements a DPLL attack on these exact-2-in-4 constraints.
It fixes one bit to remove global complementation, propagates every forced
cardinality constraint, and branches on the most constrained unassigned
vertex.  For each complete colouring it checks whether the bichromatic edges
form one spanning cycle.  Any cycle returned is passed through the ordinary
`verify` function; the attack never compares against the planted answer.

| Preset | n | Verified successes | Node counts over seeds 9100--9107 |
|---|---:|---:|---|
| proposed shipping (`medium`) | 120 | 7/8 | 14,849; 318; 13,097; 200,001 (cap); 87,111; 5,264; 12,686; 18,733 |
| largest named (`hard`) | 148 | 7/8 | 3,874; 50,365; 690; 22,209; 143,184; 19,563; 200,001 (cap); 20,069 |

In the isolated benchmark, the `n=120` runs took 37.94 seconds in aggregate
(median 1.57 seconds and median 13,973 nodes); `n=148` took 59.58 seconds in
aggregate (median 3.54 seconds and median 21,139 nodes).  Wall time is
machine-dependent, but the verified success counts and deterministic node
counts reproduce exactly.  Track A requires every recorded attack to have zero
successes, so one success would be fatal; these presets have seven.

## Mechanical cost versus compact route

- **Mechanical route:** the strongest relevant method for this generated
  subclass is the exact-2-in-4 DPLL attack above.  At `n=120` it needs a median
  13,973 search nodes (1.57 seconds) and succeeds on 7/8 seeds under a
  200,000-node cap.  The paper's general embedded dynamic program is
  `2^{O(k)} n`, but it is not the best method for this planted distribution.
- **Compact route after seeing the invariant:** the same exact-2-in-4 search.
  The invariant does not identify which incident edge is the matching edge,
  and no propagation-only or closed-form recovery was found.  Thus its measured
  length is again at least the median 13,973 branch nodes, before counting the
  work inside a node.  The mechanical/compact gap is effectively 1, and the
  route already exceeds the 300-operation no-tool limit by more than 46 times.

Consequently this is not a Track B no-tool-compression problem.  Increasing
`n` until the bounded attack happens to time out would merely enlarge the same
search and the spanning-cycle witness; it would not create a compact route.

## Preserved evidence

The attempted generator is retained as `rejected_gen_0909_4692.py`, including
the breaking attack.  `selftest_report.json` records the failed adversary panel.
The existing hardening transcript and `.meta.json` are also retained, but the
oracle run was incomplete after an account-limit error and is not used as the
basis for this rejection.
