# Rejected: the planted distribution fails hardness

Paper: [V. R. Singireddy and M. Basappa, *Complexity and Approximability of Edge-Vertex Domination in UDG*](https://arxiv.org/abs/2111.13552) (arXiv:2111.13552v3).

## Step-0 findings

Section 1 defines an edge `[u,v]` to edge-vertex dominate exactly the vertices in the union of the closed graph neighborhoods of `u` and `v`.  Section 3 defines the decision problem as asking for an EVDS of cardinality at most `k`.  Lemmas 2--4 reduce Vertex Cover on planar maximum-degree-3 graphs to EVDS on a specially embedded unit disk graph, and the theorem following Lemma 4 proves worst-case NP-completeness.  The reduction is the only hard parameter regime established by the paper.

The easy results matter.  Section 4, Theorem 2 gives a PTAS with running time `n^{O(c^2)}`, where `c=(1/epsilon) log(1/epsilon)`.  Section 5's final theorem gives a 5-approximation in `O(m+n)` time.  These algorithms do not return an exact threshold witness, so they do not alone reject an exact EVDS family; they do reject any attempted family that merely asks for the paper's easy approximate witness.

## Gate decision

The retained attempted module inverse-generates a rational unit-disk representation by planting `k` edges and sampling every other point inside their domination regions.  This clears G and V: the planted witness verifies exactly, corruptions are rejected, and the answer is JSON-native.  It fails **H on Track A**, specifically G5/G6.

The paper's NP-completeness theorem does not transfer to this distribution: these point clouds are not outputs of the Section 3 planar-Vertex-Cover reduction.  At the oracle-selected shipping preset (`n=180`, `k=10`, `m=1087` for the fixed density seed), a standard exact 0--1 set-cover branch-and-bound represents each graph edge by `N[u] union N[v]`.  With a 1,000,000-node cap it recovered a verifier-accepted witness on **4/8** fixed seeds.  The successful cases took 184, 430, 121,296, and 288,764 nodes; all eight attempts together took 4,410,678 nodes and 1.388381 seconds.  Because Track A requires every domain-standard attack to have zero successes, one success would reject the family; four are decisive.  The detailed run is in `selftest_report.json`.

The final bare oracle loop happened to return `hardened` at this preset (0/3 solved), but that does not override the construction-aware/domain-standard attack.  Its three parsed proposals respectively left 48 vertices undominated, contained a non-edge, and left 38 vertices undominated; the script-owned details remain in `llm_loop_transcript.jsonl`.

## Why this is not Track B

Track B was considered before rejection.  There is no demonstrated short exact shortcut here.  The mechanical exact attack costs 184--1,000,001 branch nodes per measured instance.  The proposed geometric "lens" route is not a compact route: after labels, translation, and grid isometry are randomized, even reconstructing the UDG from 180 coordinates takes `C(180,2) = 16,110` exact squared-distance tests, before local cover choices are made.  The earlier claimed count of 136 operations had no executable derivation and is withdrawn.  Thus the by-hand route is not shorter than the mechanical work; it is the same graph reconstruction and covering search without tools.

The alternative suggested directly by the paper is also not a useful Track B benchmark.  Section 5's efficient algorithm scans `m+n` objects (1,267 at the measured seed) and emits a 5-approximate EVDS.  A by-hand implementation must perform essentially that same scan; there is no dozen-step invariant or symmetry compressing it.  Asking for that output would test bookkeeping, while retaining the exact threshold yields the Track-A failure above.

Escalating only the number of decoy points would not repair the logical gap: it would tune this planted distribution after a successful attack while leaving the paper's proven reduction regime unused.  A future viable attempt would need to inverse-generate hard planar maximum-degree-3 Vertex Cover instances with known covers, carry them through Lemmas 2--4, keep the resulting EVDS under the 256-atom answer cap, and defeat a fresh exact covering attack.  This attempt does none of those things.

The failed generator and the script-owned oracle evidence are retained for audit, as required.
