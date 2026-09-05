# Rejected: arXiv:2209.08757

This attempt fails **H on Track B**. It does not fail generation or exact
verification.

## Paper result and candidate family

Section 1.1 defines Path Set Packing as selecting at least `k` pairwise
edge-disjoint paths from an explicitly supplied collection. Theorem 1 proves
W[1]-hardness parameterized by vertex-cover number, and Theorem 2 proves
W[1]-hardness on maximum-degree-four graphs parameterized by pathwidth plus
solution size. Those are worst-case parameterized results; neither theorem
establishes hardness for a planted random distribution, so they do not by
themselves support Track A.

The retained module instead tested Track B in the paper's polynomial tree-host
regime. Section 5.1, Proposition 1 and its forest corollary state that maximum
Path Set Packing is polynomial-time computable on a tree or forest. On the
module's star, paths are edges of a bipartite graph, so augmenting-path matching
is the reference algorithm. The generator composes two projective-linear
permutations whose union is one even incidence cycle; either alternating class
is a known packing, represented compactly by a normalized `2 x 2` matrix.

## The required cost comparison

At the original shipping candidate `q=1009`, the mechanical reference algorithm
averaged **16,241 counted graph/field operations and 0.0026 seconds** over eight
seeds. At `q=4001`, the recorded reference run used **65,441 operations**. The
compact projective route is bounded by **92 exact operations**: follow a constant
number of alternating cycle edges and interpolate a projective map from three
correspondences.

That gap is real, so the existence of the polynomial algorithm is not the reason
for rejection; it is why the family was correctly labelled Track B. The family
fails because the compact route was not difficult for the evaluated no-tool
models to discover and execute. The script-owned bare hardening run recorded:

| preset | q | solved / attempts |
|---|---:|---:|
| easy | 1009 | 3 / 3 |
| medium | 2003 | 3 / 3 |
| hard | 4001 | 3 / 3 |

Every scored reply parsed and verified exactly. The automatic next level,
`q=8009`, was attempted, but all redraws returned HTTP 403 key-limit errors;
those errors are preserved in `llm_loop_transcript.jsonl` and are not counted as
model failures. No `hardened` verdict exists.

Increasing `q` grows only the path table. It does not increase the length or
conceptual depth of the 92-operation shortcut, and the two-vendor results were
unchanged across a fourfold growth in `q`. Thus this construction does not meet
Track-B hardness at any tested shippable preset. Shipping it would contradict
STEP 4.

## Other tracks

A Track-A generator based on the Section 3 or Section 4 multicoloured-clique
reductions would still need distributional evidence against the domain-standard
clique/CSP algorithm. Planting a clique and transforming it supplies G, but the
paper's worst-case W[1]-hardness does not supply that missing distributional H.
No such claim is made here.

The implementation is retained as `rejected_gen_2209_08757.py` so the decision
can be replayed if the benchmark or oracle conditions change.
