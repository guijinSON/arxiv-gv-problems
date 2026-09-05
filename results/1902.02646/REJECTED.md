# Rejected: arXiv 1902.02646

Paper: C. J. Jayawardene, W. C. W. Navaratna, and J. N. Senadheera,
[*All Ramsey \((C_n,K_6)\) critical graphs for large \(n\)*](https://arxiv.org/abs/1902.02646v3).

## Decision

No native family from this paper passes **H on either track**.  A hidden
five-clique-partition family would pass G by theorem-backed construction and V by
exact edge inspection, but a construction-aware degree/neighborhood scan recovers
the witness directly.  The paper proves a complete classification, not a hard
parameter regime.  Randomly relabelling one of its classified graphs does not change
that.

This is not a `cap_bound` rejection and it does not rely on an oracle or on G9(b).
The failure occurs at Step 0, before a generator should be built.  Consequently there
is no `gen_1902_02646.py`, self-test report, or hardening transcript to retain.

## Exact paper facts used at Step 0

Section 2 defines a Ramsey critical red graph exactly: on
\(r(C_n,K_6)-1=5(n-1)\) vertices it has no \(C_n\), and its independence number is
at most five (equivalently, the blue complement has no \(K_6\)).

The decisive result is Section 3, Lemma 4.  For every \(n\geq15\), every such graph
contains \(5K_{n-1}\).  Because those five cliques already contain all
\(5(n-1)\) vertices, they are a spanning five-block partition.  The end of its proof
also shows how the blocks arise: first four copies of \(K_{n-1}\) are found outside
an \((n-1)\)-cycle, and the cycle's vertex set is proved to induce the fifth clique.

Section 4 then removes any remaining search.  Type 1 graphs have at most one vertex
in each block incident with external edges, and **every subgraph of \(K_5\)** gives
one of the 34 non-isomorphic Type 1 graphs.  Every Type 2 graph is an indicated
vertex split of a Type 1 graph; Figures 3 and 4 list the 34 types of each kind.  Thus
there are exactly 68 non-isomorphic graphs, independent of \(n\) once \(n\geq15\).
This explicit 68-template classification is what produces the certificate.

The easy regime is therefore the entire regime covered by the paper, rather than a
small exceptional parameter range that a generator could avoid.  The variable
\(n\) only enlarges five homogeneous cliques; it does not enlarge the external
template search beyond the fixed classified list.

## Candidate families and failed gates

| candidate posed to the solver | outcome |
|---|---|
| Given \(n\), construct any critical graph | Trivial explicit formula: output five disjoint copies of \(K_{n-1}\).  It has no \(C_n\), and an independent set contains at most one vertex from each clique. |
| Identify the isomorphism type | The answer has only 68 possibilities, so even a uniform structure-aware guess succeeds with probability at least \(1/68\), far above G4's \(10^{-6}\) limit.  This is also a fixed classification-table lookup. |
| Given a randomly relabelled classified graph, return its five \(K_{n-1}\) blocks | G and V are sound, and the partition language is large, but the degree/neighborhood attack below succeeds on every instance.  H and mandatory G6 fail. |
| Return the whole red graph or coloring | An explicit adjacency matrix already exceeds the 256-atom and 2,000-character answer caps at the smallest \(n=15\).  Compressing it to a five-block template returns to the first trivial candidate. |
| Verify criticality by searching for a red \(C_n\) and blue \(K_6\) | The proposed negative-cycle check is exponential in the scalable parameter and is not a cheap witness verifier.  Checking membership in one of Section 4's templates is cheap, but makes the classification itself the certificate and again fails H. |

## Mechanical cost versus compact route

The strongest plausible candidate was the hidden partition.  I benchmarked the
near-cap setting \(n=31\), so the graph has 150 vertices and a partition answer has
150 atomic vertex labels.  For each of eight seeds I chose a random Type 1 subgraph
of \(K_5\), built its five 30-vertex cliques, and uniformly permuted all vertex
labels.

The standard promise-aware algorithm scans adjacency rows for an unused vertex of
red degree \(n-2\).  Such a vertex has no external edge, so its closed red
neighborhood is exactly one complete block.  Mark that block and repeat five times.
Section 4 guarantees many such non-external vertices; the fixed Type 2 splits do not
remove them.  This is an \(O(N+E)\) degree/neighborhood scan, not clique search.

On seeds 0 through 7 it recovered and verified all five blocks **8/8** times.  With
one operation charged for each adjacency-row degree/membership probe and one for
each copied block label, it used 157--180 operations (mean 164.25).  Repeated timing
of each materialized instance gave 0.0000354--0.0000371 seconds per recovery (mean
0.0000361 seconds).  If parsing every serialized adjacency entry is charged instead,
both methods additionally pay about 2,175 edge-entry inspections at this size.

There is no shorter Track B method hiding behind this mechanical one.  The proposed
compact route is precisely: notice the five near-cliques, locate a degree-\(n-2\)
row, and copy its closed neighborhood five times.  It uses the same 157--180
random-access operations (or the same input-reading cost) as the standard algorithm.
The mechanical cost and compact-route length are therefore equal, not separated by
the orders-of-magnitude gap Track B requires.  At larger \(n\), both grow together;
only transcription and input scanning get longer.

## Final gate assessment

| requirement | result |
|---|---|
| G -- generatable | Passes for the hidden-partition candidate via Section 3, Lemma 4 and the Section 4 templates. |
| V -- exact witness checking | Passes for a submitted partition by checking five equal, disjoint blocks covering all vertices and every within-block edge. |
| H -- Track A | **Fails.** No distributional hardness theorem is given, the support has only 68 structural templates, and the natural scan succeeds 8/8. |
| H -- Track B | **Fails.** The certificate-producing algorithm and the supposed compact insight are the same 157--180-operation scan. |
| G4/G6 for classification or partition variants | **Fail.** Classification has guess probability at least \(1/68\); hidden partition is solved by the required construction-aware outlier/degree attack. |
| Overall | **Rejected at Step 0.** |

The paper remains a useful extremal classification result, but its scalable parameter
only repeats vertices inside already identified clique blocks.  Turning that repetition
into a benchmark would measure input scanning or output transcription, not discovery
of a mathematical invariant.
