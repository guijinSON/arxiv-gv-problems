# Proper conflict-free 5-coloring on bipartite 1-subdivisions

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a compressed coloring function) |
| Intended intuition | decomposition: detect five equal latent independent classes |
| Domain essentiality | native |
| Reduction | paper-licensed, Section 3 Lemma 3.3 |

## What the family is

The source is Ahn, Im, and Oum, [*The proper conflict-free k-coloring problem and the odd k-coloring problem are NP-complete on bipartite graphs*](https://arxiv.org/abs/2208.08330). The solver receives a graph `H` as the 1-subdivision of an explicitly listed core graph `G`: every core edge is replaced by a two-edge path. It must give the five colors on the original vertices. The checker executes the greedy extension from Lemma 3.3 and directly scans every edge and neighborhood of `H`. Thus the short answer is a complete symbolic specification of a PCF coloring, not a graph surrogate or an unchecked appeal to the theorem.

Generation is inverse and never solves its output. It first samples five equal hidden color classes, joins every pair of classes by independent edge-disjoint random perfect matchings, permutes vertices and color names, and retains that planted proper coloring. All core vertices have the same degree and every edge—planted or decoy—comes from the same matching process.

## Why Track A is claimed

Theorem 3.1 proves PCF `k`-coloring NP-complete on bipartite graphs for every fixed `k >= 3`. More specifically for this family, Lemma 3.3 shows that when `k >= 5`, `G` is `k`-colorable exactly when its bipartite 1-subdivision has a PCF `k`-coloring. The generator uses `k=5`, balanced 12-regular cores, and a growing number of original vertices. The theorem is a worst-case result, not a distributional proof; the evidence for this planted distribution is the measured adversary panel: balanced DSATUR failed on 8/8 shipping instances after 300,000 nodes each, as did the local-statistic, greedy, random-restart, and spectral attacks.

The easy regimes were deliberately avoided. Section 1 gives polynomial characterizations for `k <= 2`, and Section 5 notes an `O(n^3)` counting-MSO algorithm for each fixed `k` on bounded-clique-width graphs. The proof's greedy extension is also easy—linear in the edge set—but only *after* a proper core coloring is known. It produces the certificate from the planted coloring; it does not remove the core coloring search that Lemma 3.3 preserves.

## Worked demo

This is the full `demo` instance for seed 11 (line wrapping aside):

```text
Proper conflict-free 5-coloring of a bipartite 1-subdivision

A proper conflict-free (PCF) coloring of a finite simple graph assigns a color
to every vertex so that (i) adjacent vertices have different colors and (ii)
every non-isolated vertex has at least one neighbor whose color occurs exactly
once among all of that vertex's neighbors.  Neighborhoods are open: a vertex is
not its own neighbor.

The graph H below is specified as the 1-subdivision of a core graph G.  G has
original vertices 1 through 10.  For each displayed core edge u-v, in the exact
left-to-right order shown, H replaces u-v by u-s-v using one new subdivision
vertex s.  Thus H has 10+20=30 vertices, and is bipartite even though G
need not be.  Core edges are unordered, have no repeats, and vertex labels are
1-based.

Core edges (20):
2-6 7-8 1-7 2-3 1-8 6-9 3-9 2-9 6-7 3-5 4-6 1-5 5-8 2-4 3-4 4-8 9-10 1-10 5-10 7-10

Give a compressed PCF 5-coloring certificate: a JSON list of exactly 10
integers, where entry i is the color of original vertex i+1.  Allowed colors are
1,2,3,4,5; every color must occur exactly 2 times.  The listed core colors
must be proper on every displayed core edge.

The checker completes your list to all subdivision vertices deterministically.
It processes core edges in displayed order.  At each endpoint it marks that
endpoint's own color and, if one exists, the smallest color currently occurring
exactly once on already processed subdivision neighbors.  The new subdivision
vertex receives the smallest color in 1..5 not marked at either endpoint.  The
checker then directly verifies both PCF conditions on all of H.  Five colors
guarantee that the prescribed choice always exists for a proper core coloring.

Give your final answer inside <answer></answer> tags, as one JSON list of 10
integers.  Example syntax: <answer>[1,2,3,4,5]</answer> (your list must have
exactly 10 entries).  Output nothing else inside the tags.
```

A valid response is `<answer>[5,5,2,1,3,3,2,4,4,1]</answer>`. The module returns `verify(inst, answer) == (True, "ok")`. Dropping its last entry returns `(False, "too few colors: expected 10, received 9")`. A person can solve this 10-vertex illustration on paper; exact enumeration finds 8,640 labeled balanced answers, so the demo is intentionally explanatory rather than hard.

## Difficulty presets

| Preset | Core vertices | Core degree | Core edges | Vertices in H | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 10 | 4 | 20 | 30 | 10 | hand-scale; skipped by hardener |
| easy | 120 | 12 | 720 | 840 | 120 | **shipping; bare oracle held** |
| medium | 160 | 12 | 960 | 1,120 | 160 | available, not needed by ladder |
| hard | 200 | 12 | 1,200 | 1,400 | 200 | available, not needed by ladder |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified and JSON-round-tripped |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with 5 distinct reasons |
| G3 | pass | 120 entries recovered from tagged prose/fences |
| G4 | pass | 0/200,000 valid guesses from uniform exactly-balanced strings; declared space is about `7.28e79` |
| G5 | pass | shipping density 0/200,000; demo exact count 8,640; DSATUR averaged 300,030 nodes and 3.338 s |
| G6 | pass | all five attacks 0/8; DSATUR total 2,400,242 nodes, all capped |
| G7 | pass | doubled `n=240` instance built and verified; core edges grew 720 to 1,440 |
| G8 | pass | 60/60 relabel/reorder invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | 360 chars, about 90 tokens, 120 atoms; intended post-insight route 125 assignments/choices |

## Bare oracle loop

The harness used medium reasoning effort and parsed every response; these are genuine invalid colorings, not output-contract failures.

| Preset | Model | Seed | Solved | Verification result |
|---|---|---:|---|---|
| easy | openai/gpt-5.6-terra | 1760386464 | no | equal colors on core edge 100-120 |
| easy | google/gemini-3.8-flash | 1578406088 | no | equal colors on core edge 29-59 |
| easy | openai/gpt-5.6-terra | 274482538 | no | equal colors on core edge 32-54 |

Verdict: `hardened` at `easy`, with no escalation.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted - placebo = 0.0`. Naming the perfect-matching/latent-class decomposition did not help this pool, so the diagnostic does not show that the claimed intuition is readily actionable from the shuffled edge list. It also does not block shipping. The answer and effort figures are 360 serialized characters, 120 atoms, and 125 intended operations after recognizing the decomposition.

## Use

From the repository root:

```python
import random, sys
sys.path.insert(0, "results/2208.08330")
import gen_2208_08330 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
answer = gen.parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
candidate = gen.random_candidate(inst, random.Random(1))
```

Emit dataset records with `bash scripts/emit.sh 2208.08330 20 easy`.

## Caveats

NP-completeness does not prove this random planted distribution hard. DSATUR was resource-capped, and a stronger SAT/ILP encoding, belief propagation, an SDP, or a more sophisticated spectral/non-backtracking method may recover the classes. The implemented spectral test uses four bottom adjacency vectors and balanced k-means; no SDP was run because the paper does not propose one and the module must remain standard-library-only. The 0/200,000 guess result applies only to the uniform balanced prior required by the statement; it says nothing about adaptive local search or a learned prior.

The certificate is deliberately compressed to original-vertex colors; verification expands it exactly using Lemma 3.3. The canonical key is a strong relabeling-invariant collection of degree, triangle, and common-neighbor statistics, not a complete graph-isomorphism canonical form, so rare non-isomorphic collisions are possible. Lower degree, visible class-dependent statistics, `k <= 2`, bounded clique-width, or access to a large search tool would make the task easier. These limitations are why the module reports empirical distributional evidence rather than presenting the paper's worst-case theorem as proof about every generated instance.
