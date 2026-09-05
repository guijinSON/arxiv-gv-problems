# Prior Step-0 rejection (retained audit): arXiv 2601.04295

This initial analysis applied to the paper's fixed 60-point instance. It is
retained as an audit trail. A subsequent Track B build tested certified disjoint
composition and fixed-witness-length decoy crowding; the mandatory oracle loop
then solved 9/9 and confirmed rejection. `REJECTED.md` is the current decision.

Paper: Paulo Henrique Cunha Gomes, [“An explicit family of 30 blocks meeting every
6-set of [60] in at least two points”](https://arxiv.org/abs/2601.04295).

## Decision

This paper does not support a problem family satisfying G, H, and V simultaneously.
I read the full paper, including the exact construction in Section 2, Theorem 1 and
its proof in Section 3, the complete block list in Section 4, and the Johnson-space
interpretation in Section 5. The native candidate families fail **H on Track A and
Track B**. G and V are available, but the certificate is produced by the paper's
own linear-time explicit recipe. I therefore stopped at Step 0 and did not create a
generator or spend oracle calls on a family already known to be easy.

## What produces the certificate?

Section 2 partitions `[60]` into ten 6-point base blocks, pairs the base blocks,
splits each base block into two triples, and emits all four unions of one triple
from either side of each pair. Equivalently, the 60 points are partitioned into
five 12-point components, each component is partitioned into four triples, and
the six pairwise unions of those triples are emitted. Those five copies contribute
exactly 30 blocks.

The certificate-producing algorithm is therefore the displayed construction
itself. At the paper's parameters its exact mechanical cost is:

| operation | count |
|---|---:|
| write the ten base blocks | `10 * 6 = 60` point occurrences |
| write the twenty recombined blocks | `20 * 6 = 120` point occurrences |
| total certificate output | **180 point occurrences in 30 blocks** |

The compact route has the same cost: apply Section 2's formula and write those
same 180 required point occurrences. There is no shorter executable route hidden
behind a million-operation mechanical computation; the output alone has 180 atoms.
A structural certificate using the equivalent four-triples-per-component form is
shorter (20 triples, 60 point occurrences), but Section 2 gives those triples
directly as consecutive groups, so both the mechanical route and compact route are
the same 60 copies plus constant bookkeeping. This is not Track B compression.

## Why the obvious problem formulations fail

| Candidate task | Gate failure | Measured or exact reason |
|---|---|---|
| Construct 30 valid blocks on `[60]` | H, Track A | Section 2 is an explicit `O(output size)` algorithm and Theorem 1 proves its output valid. There is no hard parameter regime in the paper. |
| Construct 30 valid blocks on `[60]` | H, Track B | Mechanical cost and compact-route length are both exactly 180 output placements (or both 60 placements for the four-triple structural certificate). The gap is 1:1. |
| Given a 6-set `S`, return a block meeting it twice | H and G4 | The proof of Theorem 1 is an algorithm. Classify six points into base blocks (six classifications); if no class repeats, classify the six base blocks into five fixed pairs (six more classifications), then classify the two selected points into halves (two comparisons). Thus the mechanical and compact routes are the same, at most **14 classifications** plus writing one 6-point block. The structure-aware answer space has only 30 blocks, so a uniformly guessed listed block succeeds with probability at least `1/30`, far above `1e-6`. |
| Return all blocks meeting a supplied `S` twice | H | Scan 30 blocks, at most 180 point-membership inspections; the structural shortcut is of comparable size and the entire computation is below the 300-operation no-tool cap. |
| Certify that no uncovered 6-set exists | H | A five-component/four-triple decomposition is a finite exact witness, and the checker can reconstruct the six pair-unions in each component. But Section 2 hands that decomposition to the solver directly. Brute enumeration of all `C(60,6) = 50,063,860` target sets is unnecessary and cannot be used as the mechanical baseline when the executable certificate algorithm is explicit. |
| Recover the decomposition from randomly relabelled blocks | H / G8 support | Equal incidence columns immediately recover the 20 triples in at most `60 * 30 = 1,800` Boolean inspections. More importantly, this inverse problem is not posed or analysed in the paper, and every seed obtained only by relabelling is the same canonical instance, so it cannot pass the required unrelated-seed distinctness test. |
| Hide the 30 blocks among random decoys | paper support | This would create a planted hypergraph-pattern recovery benchmark. Neither Theorem 1 nor any other part of the paper gives distributional hardness for it; the decoys, recovery objective, and parameter regime would all be external inventions. It cannot honestly supply Track A hardness or native coverage for this paper. |

## Track analysis

**Track A fails.** The paper contains one theorem, Theorem 1. It is a correctness
theorem for the explicit construction, not a worst-case or distributional hardness
result. The construction and the witness-finding proof are efficient in the entire
parameter regime the paper states. There is no NP-hardness, average-case hardness,
FPT lower bound, or difficult distribution to cite in `hardness_basis`.

**Track B also fails.** For constructing the block family, the mechanical method is
the compact construction and both take 180 unavoidable output placements. For
finding a block witnessing Theorem 1 for a supplied set, the paper's proof and the
compact pigeonhole route are the same at most 14 classifications. In both native
formulations the mechanical and compact costs are comparable; there is no
compression insight to test.

Treating a generic covering-design search over all $\binom{60}{6}=50{,}063{,}860$
candidate target sets as the Track B reference computation would be misleading.
That search is never required on this distribution: the instance has no data beyond
the fixed ground-set size, and Section 2 gives one uniform output-linear algorithm
for every allowed partition. The expensive generic search is therefore not an
algorithm that produces these certificates; it is a deliberately inferior way to
ignore the applicable construction. Unlike a legitimate Track B instance, there is
no instance-specific quantity for the solver to recover before the shortcut applies.

This also prevents an unlimited generator. At fixed parameters all choices of base
partition, pairing, triple split, point names, and block order are isomorphic copies
of the same 5-component hypergraph. A correct `canonical_key` must collapse them.
Adding forbidden blocks, decoys, arithmetic labels, or other seed-dependent side
constraints could create different planted-recovery instances, but none of those
objects or objectives occurs in the paper and none inherits a hardness claim from
Theorem 1.

Generalising from five components to `q` components does not repair this. Emitting
the construction remains linear in—and lower-bounded by—the answer length. For the
witnessing-block task, the natural candidate space has `6q` blocks, so G4 would
require `q > 166,666` even if exactly one block worked, while the pigeonhole input
contains `q+1` points and its intended scan already exceeds the 300-operation cap.
That trades mathematical difficulty for input scanning rather than producing a
no-tool insight problem.

## Gate outcome

| Gate | Outcome |
|---|---|
| G — generatable by construction | Passes: Section 2 directly supplies the block family and Theorem 1's proof supplies a witnessing block for every 6-set. |
| H — Track A structural hardness | **Fails:** an explicit linear-time construction and constant-size witness algorithm are given in Sections 2–3. |
| H — Track B no-tool compression | **Fails:** mechanical and compact costs are 180 vs. 180 output placements for construction, or at most 14 vs. 14 classifications for witness finding. |
| V — cheap exact verification | Passes with a four-triples-per-component certificate and exact set unions/intersections. |
| G8 — canonical diversity | **Fails for construction instances:** every seed-level variation licensed by Section 2 is a relabelling of the same incidence structure. |

The prior-triage suggestion correctly identified a theorem-backed construction, but
it identified a certificate generator rather than a hard witness search. Building a
module around it would satisfy G and V while knowingly violating H.
