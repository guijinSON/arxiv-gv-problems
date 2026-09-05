# Rejected at Step 0: the proposed planting has no supported hard distribution

Paper: Negin Karisani, E. S. Mahmoodian, and Narges K. Sobhani,
[*On the star arboricity of hypercubes*](https://arxiv.org/abs/1312.5698)
(arXiv:1312.5698v2).

## Decision

No generator is shipped. The prior-triage proposal—sample a partition of a
graph's edges into star forests and hide the part labels—passes **G** by inverse
generation and **V** by a linear exact check, but it fails **H on both tracks**.

- **Track A fails.** Section 1 says that deciding whether an *arbitrary* graph
  has star arboricity at most two is NP-complete, citing [4] and [6]. The paper
  proves no average-case, planted-distribution, or parameterized hardness result
  for a random union of planted star forests. Worst-case NP-completeness does not
  imply that this answer-first distribution is hard. In fact, all of the paper's
  own hypercube regimes are handled by direct product, matching, or square-color
  constructions.
- **Track B fails for the hidden planting.** The sampled partition is private
  generator state, not a solver-visible invariant. Once its colors are erased,
  the paper provides no shorter route for recovering that particular random
  partition than the generic decomposition search. Exposing the structures the
  paper actually uses does not repair this: Lemma 4's alternating-cycle method,
  Theorem 2's displayed galaxy construction, and Theorem 4's blow-up are already
  the certificate-producing algorithms. At writable sizes their mechanical and
  compact routes have the same linear output cost.

This is not a rejection merely because an algorithm exists. The measured
mechanical/compact comparison below shows that the paper-native algorithms do
not have the large compression gap required by Track B. A later tagged-mask
prototype was built to test whether a symbolic certificate could rescue the
family; it is retained as `rejected_gen_1312_5698.py`, but the audit below shows
that its compression gap comes from added benchmark annotations rather than
from the paper. It is therefore evidence for the rejection, not a shipped
module.

## Exact definition and the paper's regimes

Section 1 defines a **galaxy** (star forest) as a vertex-disjoint union of
stars. The star arboricity `sa(G)` is the minimum number of galaxies whose edge
sets partition `E(G)`. Thus a literal witness is one galaxy label per edge; a
checker can compare the edge multiset and, in each color, verify that every
connected component has at most one vertex of degree greater than one.

The paper's hardness sentence concerns arbitrary input graphs. Its substantive
results concern the much narrower and highly symmetric hypercubes `Q_d`:

- Theorem C (quoted from [11]) gives
  `sa(Q_(2^k-2)) = 2^(k-1)`, and Corollary 2 gives
  `sa(Q_(2^k-1)) = 2^(k-1)+1`.
- Proposition 1 obtains the value for dimensions
  `2^k + 2^j - 4` by the Cartesian-product inequality of Lemma 1.
- Theorem 2 explicitly constructs `2^(k-1)+2` galaxies for
  `Q_(2^k+1)`. It starts with Lemma 3's vertex classes, chooses one of the two
  perfect matchings between every pair of classes, and sends the remaining
  edges to the two galaxies supplied by Lemma 4.
- Lemma 5 and Table 2 collect the resulting exact small values. Theorem 3 and
  Corollary 4 produce upper bounds for other dimensions by repeatedly factoring
  the cube as a Cartesian product.
- Section 4, Theorem 4 turns a proper coloring of the square graph `G^2` into a
  galaxy partition: each pair of square-color classes induces a matching, a
  class-interaction graph is decomposed, and its galaxies are blown up to `G`.

These are exactly the easy regimes a generator would have to avoid. Avoiding
them leaves the proposed arbitrary planted-union distribution, for which this
paper supplies no distributional hardness claim.

## What produces each candidate certificate

| Candidate family | Certificate-producing method in the paper | Consequence |
|---|---|---|
| Lemma 4 tripartite graphs | The graph on `V1 union V2` is a disjoint union of even cycles. Alternate every cycle into perfect matchings `M1,M2`; add all `V1`--`V3` edges to the first galaxy and all `V2`--`V3` edges to the second. | A deterministic linear scan constructs the witness. |
| Theorem 2 hypercubes | The proof writes each of the first `2^(k-1)` galaxies from the indexed classes `A_i(c)` and oriented perfect matchings; Lemma 4 handles the remainder. | The theorem's displayed construction is the compact route and the mechanical route. |
| Proposition 1 / Theorem 3 products | Lemma 1 concatenates known galaxy partitions of the Cartesian factors. | Certificate production is direct composition, linear in the emitted partition. |
| Theorem 4 square coloring | Decompose the color-class interaction graph `H` and blow up each of its galaxies along the induced matchings. | Once the square coloring is supplied, the lift is direct; searching for the coloring would be a different problem, with no hardness theorem here. |
| Random union of planted galaxies | Sample the answer first and take the union. | G and V pass, but no theorem or measured paper-native invariant supports H for that distribution. |

The first row is especially decisive: the proof itself identifies the standard
algorithm—cycle walking and alternating matchings—rather than leaving a hard
search problem.

## Mechanical cost versus compact route

For a concrete boundary measurement, I instantiated Lemma 4 with
`|V1|=|V2|=42` and `|V3|=84`. The `V1`--`V2` subgraph is one alternating
84-cycle, and each vertex of `V1 union V2` has two neighbors in `V3`. The graph
has **252 edges**, just below the 256-atom cap for a literal edge-color witness.
A standard-library implementation of the proof's construction was run 10,000
times:

| quantity | measured value |
|---|---:|
| edges inspected / colored per construction | 252 |
| witness entries emitted | 252 |
| total wall clock for 10,000 constructions | 2.337445 s |
| mean wall clock per construction | 233.744 microseconds |
| compact post-insight route | the same 252 edge-color assignments |

The operation-count ratio is therefore **252:252 = 1**. Alternating the cycle
is both the structural insight and the complete certificate-producing
algorithm; there is no million-operation mechanical route compressed to a
dozen hand operations.

The same output lower bound applies to the cube constructions. `Q_d` has
`d*2^(d-1)` edges. A literal optimal decomposition of `Q_6` already needs
**192 edge labels**, and `Q_7` needs **448**, beyond the cap. Producing the
`Q_6` certificate from the paper's class/matching construction and taking the
compact route both require at least the same 192 output placements. Theorem 2's
first nontrivial cases make the jump especially clear: `Q_5` has 80 edges,
whereas `Q_9` has 2,304.

A symbolic macro does not create Track B hardness. If the macro denotes the
paper's displayed construction, that same formula is the direct mechanical
answer, so the compact and mechanical descriptions are identical. Randomly
renumbering a hypercube does not create unrelated instances under G8, and a
coordinate frame for an unmarked hypercube is not hard to guess because every
origin and ordering of its incident coordinate directions gives another valid
frame. Adding fingerprints or precolored constraints to select a secret frame
would manufacture a reconstruction puzzle absent from the paper; the hardness
would come from those added constraints, not from star arboricity.

## Why the planted proposal is not rescued by worst-case hardness

The proposed generator could independently sample several star forests, reject
duplicate edges, shuffle the edge list, and retain the hidden labels. That only
proves existence of one answer. It does not control the number of alternative
decompositions, planting leakage, or the cost of finding any valid partition.
The NP-completeness statement in Section 1 is for arbitrary graphs and does not
identify this distribution or a parameter regime from which distributional
hardness follows.

Making the random components look alike can defeat simple degree and ordering
attacks, but it still would not establish Track A. Conversely, making the
planting follow Lemma 4, Theorem 2, or Theorem 4 supplies the solver with the
same cycle, product, or square-color structure that makes certificate production
linear and eliminates a Track B gap. A SAT reduction or a cryptographic hiding
layer could create another benchmark, but neither is central to this paper and
would be a convenience reduction rather than native coverage.

## Generator experiments

Two concrete attempts were made after the paper triage.

First, I generated an ordinary graph as the union of two independently shuffled
`K_1,3` factors and retained their hidden edge colors. For a triangle-free graph,
the condition that each color class is a galaxy can be expressed by forbidding a
monochromatic three-edge path. A domain-standard DPLL attack with NAE unit
propagation found a balanced valid partition at `N=128`, `m=192` in **15--122
branch nodes** across eight seeds (0.022--0.336 seconds in the unoptimised Python
prototype). At smaller sizes it was likewise routine. This directly falsifies a
Track-A claim for the natural inverse-generated distribution; merely increasing
the random-guess space does not make it hard.

Second, `rejected_gen_1312_5698.py` adds a unique bit-vector tag and a public
slot to every edge, plus a designated probe vertex. A Boolean linear form on the
tags denotes the edge partition. It is internally well formed: the planted
witness verified on all 12 preset/seed trials, 0 of 200,000 bounded-language
random masks verified at the proposed hard preset, five heuristic attacks had
0/8 successes, and arbitrary vertex renaming preserved its canonical key on
20/20 trials. The successful GF(2) reference decoder used **697,717 scalar bit
operations and 0.068 seconds**, while the engineered slot pattern reduced that
to a claimed 257 operations.

That second gap does not rescue the paper. The tags, slots, and probe do not
occur in arXiv:1312.5698, and the short route recovers their planted parity mask;
it does not discover a galaxy decomposition by using a theorem or construction
from the paper. Deleting those annotations deletes the shortcut while leaving
the star-arboricity instance intact. The honest profile would therefore be a
benchmark-convenience reconstruction overlay, excluded from native release by
the task's schema. It cannot be relabelled `domain_essentiality="native"` merely
because the final verifier also scans two star forests.

The required oracle harness was invoked once on this retained prototype. The
harness itself wrote `.meta.json` and four error records to
`llm_loop_transcript.jsonl`, but every OpenRouter redraw returned HTTP 403
`Key limit exceeded`; no oracle result was scored. This external failure is not
used as evidence for either hardness or rejection.

## Final gate disposition

| Requirement | Result |
|---|---|
| G -- generatable | **Passes for the proposal:** sample the galaxy partition first and form its union. The paper's own constructions also pass by theorem-backed construction and composition. |
| V -- exact verification | **Passes:** check edge coverage/disjointness and check each colored component is a star, all in linear time. |
| H -- Track A | **Fails:** only worst-case NP-completeness for arbitrary graphs is stated; no result covers the planted distribution. |
| H -- Track B | **Fails:** a hidden random plant has no public shortcut, while every solver-visible paper-native construction has mechanical and compact costs of the same order and, at the measured boundary, exactly 252 versus 252 output assignments. |
| Overall | **Rejected on H/provenance; the later module is retained under the required `rejected_gen_` name, and its failed external oracle attempt is preserved.** |

The result is therefore a reviewable H rejection, not `cap_bound`: the cap
illustrates why literal cube decompositions cannot be scaled, but the deciding
failure is already the absence of either distributional Track A support or a
Track B compression gap at writable sizes.
