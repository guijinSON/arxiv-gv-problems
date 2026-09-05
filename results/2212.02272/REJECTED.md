# Rejected: arXiv 2212.02272

## Decision

This paper does not yield a shippable family under the tested native construction.
G and V pass, but **H fails on Track B**.  Track A is not claimed: the paper proves
a bounded-dichromatic-number theorem, not a hardness theorem for the generated
distribution.

The retained candidate module is `rejected_gen_2212_02272.py`.  The authoritative
script-owned evidence is `llm_loop_transcript.jsonl` with the terminal verdict
`too_easy`; `.meta.json` records the same verdict and its master seed.

## Paper facts used at STEP 0

Section 2 defines the exact native objects.  Digraphs are loopless and have no
parallel or antiparallel arcs.  `H`-free means no **induced** copy of `H`, and
triangle-free means that the underlying undirected graph has clique number at most
two.  A dicolouring is a vertex partition into acyclic induced subdigraphs.

Theorem 1 proves that every induced-directed-`P6`-free, triangle-free oriented graph
has dichromatic number at most 382.  Lemma 3 says that a digraph with no odd directed
cycle is 2-dicolourable.  Proposition 4 characterizes a `k`-dicolouring by an order
with no all-backward directed path on `k+1` vertices.  Section 4 begins the main proof
from a shortest odd directed cycle and builds a bounded-dichromatic dipolar set.

These results make odd directed cycles and dicolourings the paper's native finite
witnesses, with cheap exact checking.  They do not supply a hard distribution.  The
proof ingredients are constructive polynomial graph operations at fixed forbidden
patterns; declaring Track A would therefore be unsupported.

Paper: [“(P6, triangle)-free digraphs have bounded dichromatic number”](https://arxiv.org/abs/2212.02272).

## Candidate construction and the gates it clears

The retained module inversely generates a directed odd 5-cycle in an orientation of
a blow-up of `C5`.  The underlying graph is triangle-free, and exhaustive quotient
checking finds zero bag patterns that could induce a six-vertex path.  Generation
samples a hidden rank first, publishes four compatible congruences, and carries the
rank through exact affine permutations.  It therefore knows the five cycle vertices
by composition of identities and never solves the generated instance.

The checker independently recomputes the five ranks and arc directions and accepts
any clockwise or counterclockwise directed 5-cycle in bag order; it never reads
`inst["answer"]`.  On the fully measured `n=59` version, all local gates passed:

| Measurement | Result |
|---|---:|
| Structure-aware candidate space | 25,919,821 common-rank tuples |
| Random guessing | 0 / 250,000 |
| Exact demo solutions | 1 among 210 candidates |
| Mechanical scan, median | 27,563,621 modular tests; 3.48 s |
| Mechanical scan, maximum over 8 seeds | 44,617,223 tests |
| Four attacks | 0 / 8 successes each |
| Reference scan | 8 / 8 successes, as expected on Track B |
| Canonical-key invariance | 80 / 80 transformations |
| Unrelated canonical keys | 20 / 20 distinct |
| Answer size | 5 atoms, about 12 tokens |
| Compact intended route | at most 174 operations on the original ladder |

The four failing attacks were minimum-degree/rank outlier selection, greedy recovery
from the smallest displayed label, 4,096 random common-rank restarts, and the obvious
single-congruence ansatz.  A successful exhaustive common-rank scan was reported
separately as the Track B reference algorithm.

## Why H fails

The standard mechanical route scans the common hidden rank.  It costs `O(N)` exact
congruence tests; explicit SCC/cycle search is even larger because the succinct graph
has `5N` vertices and `5N^2` edges.  The compact route is:

1. recognize that adjacent affine mask steps cancel in inverse pairs;
2. use cyclic rank monotonicity to force all five cycle ranks to agree;
3. combine four coprime congruences by CRT; and
4. invert the five remaining affine maps.

At the final tested level (`n=251`, 24 mask pairs), `N=4,918,826,669`.
For the three actual transcript seeds, a literal common-rank scan would perform
7,282,538,034; 7,175,256,290; and 5,618,719,169 rule tests, respectively.  The
compact route takes 220, 219, and 222 counted exact operations.  The earlier
`n=59` scan was executed and timed; the billion-test final costs are exact loop-count
calculations from the same algorithm, not invented wall-clock measurements.

So there is a real mechanical/compact gap.  The rejection does **not** say “an
efficient algorithm exists, therefore reject.”  It says that the compact route is
too exposed to test discovery: the mandated no-tool oracle pool executed it anyway.

The final hardening run used five levels and 15 distinct instance seeds.  At least
one model solved every level, and 14 of 15 calls produced verified cycles:

| Level | Parameters | Solved |
|---|---|---:|
| easy | `n=155, mask_pairs=20` | 2 / 3 |
| medium | `n=179, mask_pairs=22` | 3 / 3 |
| hard | `n=203, mask_pairs=24` | 3 / 3 |
| escalated | `n=227, mask_pairs=24` | 3 / 3 |
| escalated | `n=251, mask_pairs=24` | 3 / 3 |

Both fixed-answer-length axes were exercised: rank-space crowding grew and the
cancellable affine mask grew from 20 to 24 pairs.  `escalate()` then returned `None`.
The harness recorded `too_easy`, not `cap_bound` or `budget_bound`; the five-atom
answer was nowhere near either output cap.

## Why no alternative family is shipped

Asking only for the paper's guaranteed 382-dicolouring is not a useful replacement:
on this native blow-up class a stable-bag colouring is immediate, while a generic
inverse-planted dicolouring would have no distributional hardness theorem from this
paper.  Lemma 3's 2-dicolouring certificate and Proposition 4's ordering certificate
are both produced by direct polynomial graph routines; they could support Track B
only if a non-obvious compact route survived the same no-tool panel.  The native
odd-cycle candidate was the strongest short witness found, and its compact invariant
was solved across the entire prescribed ladder.

Accordingly, this result rejects the tested paper-to-problem conversion on H while
preserving the working generator and all evidence for later re-audit.
