# Superseded rejection audit: arXiv:2602.13737

This file is retained as audit evidence. It evaluated the natural dense
plant-and-fill distribution and correctly found that distribution easy, but it
predated the later Track-B construction in `gen_2602_13737.py`. The replacement
keeps the native directed-factor object, discloses its polynomial modular-3SUM
algorithm, measures a 482,804-operation mechanical route against a 24-operation
symmetry route, and passes bare hardening at `d=401`. See `README.md` for the
new decision. The original analysis follows unchanged.

Paper: Theodore Molla and Andrew Treglown, [*Cycle tilings and
\(H\)-factors in directed graphs*](https://arxiv.org/abs/2602.13737).

## Decision

The natural generator passes **G** and **V**, but fails **H on both tracks**.
No module is shipped.

The native task considered was exactly the paper's task: the input is a finite
digraph and the answer is a spanning collection of vertex-disjoint copies of a
specified oriented cycle or transitive tournament.  Section 1.1 defines an
\(H\)-tiling and an \(H\)-factor, and Section 1.2 defines orientations of cycles
and prescribed cycle tilings.  A proposed factor is checked using only the
listed arcs, vertex disjointness, isomorphism to the requested tiles, and vertex
coverage, so verification is exact and linear in the certificate size.

Inverse generation is also immediate: sample a partition of the vertices into
ordered copies of \(H\), insert their arcs, and then add hiding arcs.  Thus G and
V are not the problem.  The problem is that the hiding arcs needed to erase the
plant's local signature create many cheap alternative factors.

## STEP 0: what produces the certificate?

The paper supplies sufficient-density existence theorems, not a hard search
distribution.

- Theorem 1.7 forces any prescribed spanning collection of oriented cycles
  under \(\delta^0(G) \ge (n+t)/2+\eta n\).  Its proof in Section 4 repeatedly
  uses random partitions, greedy cycle/path placement, and dense oriented
  Hamilton-cycle results.  In particular, Lemma 4.2 explicitly switches to a
  greedy construction when the requested small-cycle mass is small, while its
  remaining case partitions the graph and greedily closes paths into cycles.
- Theorem 1.9 gives an exact Ore condition for a transitive-triangle factor.
  Section 5 forms the underlying undirected graph, obtains a triangle factor,
  and replaces cyclic triangles through local six-vertex exchanges.
- Theorems 1.2, 1.5, and 1.10 likewise prove forcing results through regularity
  and absorption.  They do not state distributional search hardness.

Consequently, declaring Track A for the planted-and-filled distribution would
be false.  Worst-case hardness of unrestricted factor problems would not imply
hardness for these dense planted instances, and the paper contains no theorem
that does.

## Shipping-scale attack measurement

I tested the strongest especially clean native subfamily, Theorem 1.9's
\(T_3\)-factor problem, at the largest convenient scale below the 256-atom
answer cap:

| quantity | value |
|---|---:|
| vertices \(n\) | 192 |
| tiles / ordered triples in the witness | 64 |
| atomic vertex placements in the witness | 192 |
| random hiding-arc probability | 0.80 |
| independent seeds | 20 |
| required Ore lower bound \(4n/3-1\) | 255 |
| measured minimum Ore sum, min / median / max | 267 / 275 / 282 |

For every seed I planted a random ordered \(T_3\)-factor, added every other
possible arc independently with probability 0.80, checked the Ore hypothesis,
and then discarded the planted answer.  Two independent solvers were run:

| attack | successes | measured cost |
|---|---:|---:|
| exact-cover DFS, anchoring the least uncovered vertex | 20/20 | median 65 nodes, 317 candidate-triple tests, 0.00067 s; maxima 71 nodes, 885 tests, 0.00138 s |
| randomized greedy, closing the first available transitive triple | 20/20 | median 1 restart and 413.5 triple tests; maximum 3 restarts |

The exact-cover search had zero backtracks on 19 of 20 instances and six on the
remaining instance.  It found arbitrary valid factors, not the planted one.
This is precisely the distribution-level failure that a worst-case argument
would miss.

## Why Track B also fails

The **mechanical cost** at a plausible shipping preset is the measurement
above: 317 median candidate tests and 65 search nodes, substantially below a
millisecond in this environment.

The **compact route length** is not shorter.  Any answer must already write 192
vertex placements.  The construction's private planted partition is not
recoverable as an invariant from the rendered instance; it is merely generator
state.  Once the graph is dense enough to hide that partition, the generic
mechanical route needs only about 1.65 candidate tests per output vertex and no
backtracking on almost every seed.  Recognising the Ore/density regime therefore
does not compress a million-operation calculation into a short argument—the
standard search is already comparable to the unavoidable transcription cost.

Moving to sparse noise does not repair this as a paper-backed Track B family:
the forcing theorems no longer apply, and the hidden planted factor offers the
solver no compact invariant.  Mechanical search and the only genuine solver
route are then the same search.  Adding an affine code, special labels, or a
degree marker would create a shortcut, but it would test an artificial encoding
absent from the paper rather than cycle tilings or \(H\)-factors.

Thus there is no honest `TRACK = "A"` claim for the generated distribution and
no meaningful `TRACK = "B"` compression gap.  This is a failure of **H**, not of
the witness rule: planted factors remain perfectly valid, cheaply verifiable
certificates.
