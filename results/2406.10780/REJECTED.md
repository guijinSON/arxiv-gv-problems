# Rejection: arXiv:2406.10780

Paper: [Colouring negative exact-distance graphs of signed graphs](https://arxiv.org/abs/2406.10780), Naserasr, Ossona de Mendez, Quiroz, Šámal, and Yu. This audit used the full 16-page v2 source dated 1 July 2026, not only the abstract.

## Verdict

No family is shipped. The paper supplies clean generatable and exactly verifiable colouring witnesses, so **G and V can pass**, but the paper-backed families fail **H on both Track A and Track B**.

- **Track A fails:** the paper proves colouring upper bounds and explicit constructions, not a hard search regime or a hard input distribution. The natural theorem-backed regime, signed graphs of treewidth at most 2, has a constructive linear-time colouring algorithm in Section 2. An attempted inverse-planted extension outside that regime was also immediately solved by the standard exact colouring attack (measurements below).
- **Track B fails:** in each native construction, either the compact route is no shorter than the mechanical certificate-producing route, or the structural answer is exposed by an obvious in-context attack. There is no hidden invariant whose discovery replaces a genuinely large computation.

The failing gate is therefore **H**, not the witness rule. No generator module was retained because the decision was reached during Step 0 and the only experimental candidate was an in-memory prototype, not a module.

## Exact definitions and results checked

The Introduction defines the exact-distance \(-k\) graph by joining vertices at graph distance exactly \(k\) when **every** length-\(k\) path between them is negative. Its strong version instead requires **some** negative length-\(k\) path. This distinction rules out silently treating the two objects as interchangeable.

The relevant results are:

| Location | Result | Consequence for a generator |
|---|---|---|
| Theorem 1.5 and Section 2 | If the underlying graph has treewidth at most 2, its strong exact-distance \(-2\) graph is 7-colourable. | The proof gives the witness by deleting a degree-2 simplicial vertex and applying one row of Table 1 when the vertex is restored. |
| Theorem 1.6 and Section 4 | Every signed planar graph has a 77-colourable exact-distance \(-2\) graph. | This is an upper-bound construction through a reduction/isometric-path ordering, not a theorem identifying a hard search distribution; the bound is not even claimed tight (the paper notes 76 is obtainable). |
| Theorems 1.7, 1.8, and 3.1 | Generalised colouring-number orderings yield explicit greedy colourings of exact-distance graphs. | Once the relevant ordering is part of a theorem-backed construction, the proof mechanically produces the colour vector. |
| Section 2 after Table 1 | The 140-vertex target \(\hat P_{1,3,3}\) consists of triples \((x,A,B)\). | The displayed colouring is the direct formula \((x,A,B)\mapsto x\), so it is a lookup/evaluation family rather than search. |
| Section 5, before Proposition 5.1 | A clique of size \(t\) plus an independent set of \(2^t\) distinct sign vectors makes the latter a clique in the strong exact-distance square. | The prospective clique witness is explicitly the independent set; degree/sign-vector inspection and distinct colours solve it directly. |

The paper contains no NP-hardness theorem, no average-case hardness statement, and no parameter regime supporting a Track A claim. Importing generic worst-case graph-colouring hardness would not establish hardness for an inverse-planted distribution and would not be a result of this paper.

## Mechanical cost versus compact route

### Section 2 treewidth-2 family

For a 2-tree on \(n\) vertices, a perfect-elimination order can be recovered in \(O(n+m)=O(n)\) time, since a 2-tree has \(m=2n-3\). Given that order, the proof uses one of the eight rows of Table 1 for each of the \(n-2\) restored vertices.

At the largest explicit colouring permitted by the 256-atom answer cap, the **mechanical cost** is at most 254 table applications plus a linear scan of 509 edges (about 763 incidence/table actions under this coarse accounting). The **compact route** is not asymptotically or practically shorter: a conventional witness must still emit 256 vertex colours, hence needs at least 256 output actions. Both routes are linear and of the same hand-scale order. Making the graph larger only lengthens the witness and reaches the answer cap; it does not grow a fixed-length haystack.

The 140-state target reformulation does not help Track B. Its compact route is one direct coordinate read per target vertex, \(c(x,A,B)=x\), while the mechanical route is the same 140 reads. There is nothing hidden to discover.

### Section 5 sign-vector clique

This construction does create a numerical gap but no difficult question. Under the answer cap, \(t=7\) is the largest parameter allowing the independent-set clique to be written explicitly: \(2^7+7=135\) vertices. A naive **mechanical cost** for checking all pairs is

\[
7\binom{128}{2}=56{,}896
\]

coordinate comparisons. The **compact route** is one observation: two distinct binary sign vectors differ in a coordinate, so their two-edge path through that clique coordinate is negative. But the requested clique is exactly the visibly specified independent set, and a colouring assigns a distinct colour to every one of its members. The by-hand attack “select the independent-set vertices and give them distinct colours” succeeds deterministically. Thus this is guessable once posed, and it cannot supply the fourth failing in-context attack required for Track B. At \(t=8\), even the explicit vertex-colour witness already has \(264>256\) atoms.

## Tested inverse-planted candidate

I also tested the prior-triage idea rather than rejecting it from theory alone. For a planted 3-colourable graph \(H\), each edge was subdivided once. The two incidences were given opposite signs according to the cyclic order of the endpoint colours. Terminals retained their planted colours and each subdivision vertex received the third colour. Exact recomputation shows this is a proper 3-colouring of the resulting strong exact-distance \(-2\) graph, so this route passes G and V by inverse generation.

It fails H. A standard DSATUR backtracking implementation solved all eight shipping-sized trials for each tested density:

| terminals | mean target degree | total signed-graph vertices | DSATUR successes | search nodes | total wall time for 8 |
|---:|---:|---:|---:|---:|---:|
| 80 | 3.5 | 211–233 | 8/8 | 210–232 | 0.298 s |
| 80 | 4.0 | 228–249 | 8/8 | 234–263 | 0.333 s |
| 80 | 4.5 | 246–266 | 8/8 | 252–494 | 0.441 s |

The middle row is the relevant under-cap range: all eight instances had at most 249 answer atoms, and every instance was solved in at most 0.055 seconds. The 4.5 row sometimes exceeds the 256-atom cap and is included only to show that adding density did not harden the distribution. Earlier terminal-only tests over sizes 45, 60, 80, and 100 likewise took only 44–320 nodes. This is precisely the failure mode warned about in the task: inverse planting establishes existence, not distributional hardness.

## Why no alternative is being claimed

One could impose an unrelated SAT gadget, accept only a finite-field polynomial description of a colouring, or hide one of the explicit constructions behind an artificial encoding. None of those reductions is central to this paper. They would be benchmark-convenience discretisations whose difficulty comes from the added encoding, not from negative exact-distance colouring. The task expressly forbids using such a surrogate as native coverage.

Accordingly, the reviewable conclusion is:

- **G:** available by the Section 2 construction or inverse planting;
- **V:** cheap and exact by recomputing distance-2 negative paths and comparing colours;
- **H / Track A:** fails because no paper-backed hard distribution is given, and the tested planted distribution falls to the standard algorithm;
- **H / Track B:** fails because the constructive route and explicit answer have comparable length, while the only large mechanical/compact gap has an obvious successful by-hand attack.
