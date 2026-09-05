# Rejected: arXiv 2304.09666

The tested family fails **H**, not G or V. It fails Track B at the bare-oracle hardening step, and it cannot honestly be presented as Track A.

## Paper result and native family tested

Definition 1.1 of [*List Defective Colorings: Distributed Algorithms and Applications*](https://arxiv.org/abs/2304.09666) defines a list defective coloring: every vertex chooses a color from its list, and the number of same-colored neighbors is at most the defect attached to that vertex-color pair. Section 1 explicitly identifies proper list coloring as the zero-defect special case. The retained prototype uses exactly that native object, not a graph surrogate for another domain.

Appendix A, Lemma A.1 is the decisive easy-regime theorem. Its unhappy-vertex potential descent constructs a coloring when

`sum_{x in L_v} (d_v(x)+1) > deg(v)`.

The prototype deliberately sits outside that regime: its lists have zero defect and size `threads`, while each of its `2p` vertices has degree `2p-2`; at the shipping preset this is `9 > 500`, which is false. Thus the rejection is not the mistaken claim that Lemma A.1 solves these generated instances.

The prototype inverse-generates a nonconstant affine polynomial over `F_p`, constructs a graph and lists around its evaluations, and retains that polynomial as the witness. This clears G. `verify` evaluates the polynomial, checks every list membership, and checks every zero-defect adjacency condition exactly, so it clears V.

## Why neither hardness track survives

Track A is unavailable because this generated distribution has a polynomial-time recovery algorithm. Three affinely independent vertices supply at most `threads^3` candidate value triples; interpolate each affine polynomial and check it on all vertices. The cost is `O(threads^3 * N)` exact field operations.

Track B was the plausible route, and the cost gap is real. At the declared shipping preset (`p=251`, `N=502`, `threads=9`), the retained implementation measured:

| route | measured cost |
|---|---:|
| mechanical three-anchor interpolation and full checking | 1,857,058 exact-operation units; 0.0874 s |
| compact nonedge-pair/intersection route | 131 exact-operation units |

The family is rejected because the compact route is too visible, not because an efficient mechanical algorithm exists. The complete-minus-matching graph has exactly `p` nonedge pairs and exactly `p` colors. Properness forces equal colors within each pair; singleton intersections of the two lists expose affine values, after which three values determine the polynomial. This is a substantial compression on paper, but it did not require the evaluated models to discover a difficult invariant.

The script-owned bare transcript defeated every tested level: easy `p=31` (3/3 solved), medium `p=127` (3/3), hard `p=251` (3/3), and escalations `p=503` (3/3), `p=1007` (2/3), and `p=2015` (3/3). A level is defeated when any attempt solves it, so all six levels were defeated. Overall, 17 of 18 replies verified. Increasing the field, graph, and decoy count while keeping the three-term answer fixed therefore did not create a no-tool challenge.

The prior triage suggestion—plant a coloring and reveal lists and a graph—does establish generatability, but supplies no theorem-backed reason that its planted distribution is hard. The concrete construction-aware test above instead showed an efficiently recoverable signature. Claiming hardness from general graph-coloring worst cases would not establish hardness for this distribution.

The prototype is preserved as `rejected_gen_2304_09666.py`, together with the script-generated `llm_loop_transcript.jsonl` and `.meta.json`, so the decision can be replayed or revisited. No G9 hinted-arm result is used in this rejection.
