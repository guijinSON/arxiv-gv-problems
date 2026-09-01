# E-set partition generator for arXiv:2007.09736

## What the family is

The module turns the E-set idea in Italo J. Dejter's paper, [*Total coloring and efficient domination applications to non-Cayley non-Schreier vertex-transitive graphs*](https://arxiv.org/abs/2007.09736), into a witness search problem.  The solver receives a connected, regular, undirected graph and must color every vertex so that each closed neighborhood contains every color exactly once.  Equivalently, every color class is an efficient dominating set (E-set): every vertex outside that class has exactly one neighbor in it.  The witness is the vertex-color list.  `verify` checks lengths, ranges, class sizes, edges, and neighborhoods in linear time and accepts any valid partition, not just the plant.

Generation is inverse.  The module first shuffles a balanced hidden color vector.  For each pair of colors it then draws a random perfect matching between their fibers, resampling the matchings if the resulting graph is disconnected.  Thus every vertex has the same degree, labels are shuffled, and plant edges and non-plant edges are not separate distributions.

## Why it is hard, and what is easy

Section 1 of the paper fixes the exact E-set definition, and Theorem 1 connects totally efficient colorings to partitions into E-sets.  On a connected `(q-1)`-regular graph, such a partition is exactly a locally bijective homomorphism (graph covering projection) onto the complete graph `K_q`: every vertex has one neighbor of each other color.  Theorem 4.5 in Kratochvíl, Proskurowski, and Telle's [*Complexity of Graph Covering Problems*](https://www.cs.uoregon.edu/Reports/TR-1994-018.pdf) states that `K_q`-Cover is NP-complete for every fixed `q >= 4`.  Shipping fixes `q=6`; the fiber size `n` grows, so this is not a small-parameter escape.  A related primary result proves that even [partitioning cubic graphs into 1-perfect codes is NP-complete](https://doi.org/10.1016/0012-365X(94)90026-4).

The paper's featured graphs are an easy regime and are deliberately excluded.  Theorem 2(ii) and Theorem 10 give the `ST^2_k` partition by the explicit coordinate classes `Sigma_i^k`; Section 6, especially Theorem 12, does the same for the pancake family.  Generating those graphs would make the requested witness a lookup.  This module instead samples general random covers.  The complexity theorem is worst-case, not an average-case proof for this planted distribution; the local attacks and oracle loop are the empirical evidence for the shipped distribution.

## Worked easy example (`n=5, q=4, seed=0`)

```text
Partition a graph into efficient dominating sets

The input is a finite undirected simple graph.  Its vertices are the integers
0 through 19, inclusive.  Each unordered edge is listed once as u-v;
there are no loops, and the order of endpoints and edges has no meaning.

A set S of vertices is an efficient dominating set (an E-set) when every
vertex outside S has exactly one neighbor in S.  Find a partition of all
vertices into exactly 4 E-sets, named by colors 0 through 3.  In other
words, assign one color c[v] to each vertex v so that the closed neighborhood
consisting of v and all its neighbors contains every color 0 through 3
exactly once.  Consequently adjacent vertices have different colors.  Every
color must occur exactly 5 times.

Every vertex has degree 3.  The graph has 20 vertices and
30 edges:
2-6 4-10 6-10 5-9 6-17 1-7 0-5 9-12 3-4 2-8
16-19 12-13 12-18 2-10 7-14 0-9 13-18 1-16 3-15 5-17
3-11 11-17 1-19 8-19 14-18 0-7 8-16 11-13 4-15 14-15

Order matters only by vertex index: the first output integer is c[0], the
second is c[1], and so on through c[19].  Color names may be globally
permuted.  Repeated colors are required, but there must be exactly 20
comma-separated integers, each in the inclusive range 0..3.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of the 20 colors in vertex order.
Example of the syntax: <answer>0, 2, 1, 0</answer>
Output nothing else inside the tags.
```

One answer is:

```text
<answer>2, 3, 3, 2, 0, 3, 2, 0, 0, 1, 1, 1, 0, 3, 1, 3, 1, 0, 2, 2</answer>
```

`verify(inst, inst["answer"]) == (True, "ok")`.  Replacing its first color by `4` gives `(False, "a vertex color is outside 0..3")`.

## Difficulty presets

| Preset | `n` | `q` | Vertices | Degree | Edges | Status |
|---|---:|---:|---:|---:|---:|---|
| easy | 5 | 4 | 20 | 3 | 30 | All three final-run oracles solved it; not shipped |
| medium | 40 | 6 | 240 | 5 | 600 | **Shipping**; all local gates and three-vendor oracle panel held |
| hard | 56 | 6 | 336 | 5 | 840 | Reserve escalation rung; planted checks pass, not needed by oracle loop |
| discarded prototype | 20 | 5 | 100 | 4 | 200 | Rejected by G6: 128-restart greedy solved 7/8 seeds (512 restarts solved 8/8), despite an earlier oracle run holding |

`n` is the cover-sheet/fiber size.  With fixed `q`, raising `n` enlarges the constrained coloring problem without moving into a known easy target regime.  `escalate` multiplies this axis by 1.75, capped at 64.

## Mandatory gates

| Gate | Measured result |
|---|---|
| G1 planted verifies | 15/15: 3 presets × 5 seeds |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round trip | prose + Markdown-fenced tagged answer parsed to all 240 colors |
| G4 balanced guessing | 0 hits / 200,000 structure-aware balanced samples; empirical rate 0 |
| G5 sparse small case | 48 valid / 65,536 naive vectors = 0.000732421875 |
| G6 adversaries | outlier 0/8; left-to-right greedy 0/8; 128-restart randomized greedy 0/8 |
| G7 scaling | `n=80`: 480 vertices and 1,200 edges; plant verifies |
| G8 structural key | 60/60 invariance, 20/20 carried transforms valid, 20/20 unrelated keys distinct |

The shipping structure-aware candidate space is `240!/(40!)^6`; the much larger naive space is `6^240`.  Both exact integers are in `selftest_report.json`.

## Oracle loop

The final transcript was produced by `scripts/harden.py` at reasoning effort `medium`; the builder model was excluded.  All replies parsed, so none of the failures is a parser artifact.

| Preset | Model | Seed | Result | Verification |
|---|---|---:|---|---|
| easy | Gemini 3.1 Pro Preview | 1792906046 | solved | `ok` |
| easy | GPT-5.6-terra | 2079962268 | solved | `ok` |
| easy | Claude Sonnet 5 | 853160412 | solved | `ok` |
| medium | Grok 4.6 | 842827329 | failed | wrong color count (expected 240) |
| medium | GPT-5.6-terra | 1108109126 | failed | adjacent vertices share a color |
| medium | Gemini 3.1 Pro Preview | 2033446098 | failed | adjacent vertices share a color |

Verdict: `hardened`, after one escalation, with shipping parameters `{"n": 40, "q": 6}`.

## Use

```python
import random
import gen_2007_09736 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
answer = gen.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
guess = gen.random_candidate(inst, random.Random(9))
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 2007.09736 20 medium
```

Run the local gates with `python3 results/2007.09736/gen_2007_09736.py`.

## Caveats

- NP-completeness is worst-case.  It does not prove that random planted covers are average-case hard, or that every seed is equally hard.
- The 0/200,000 G4 result is empirical, not a statistical proof that the true rate is below one in a million.  Its prior is uniform over balanced color vectors, which enforces the obvious class-size rule, but it does not model a solver that propagates square-graph constraints; such a solver is stronger.
- G6 tried degree/triangle outliers, deterministic square-graph greedy coloring, and 128 randomized DSATUR-style restarts.  It did not try a SAT/ILP solver, full backtracking, spectral recovery, belief propagation, or specialized graph-cover algorithms.  The discarded 100-vertex prototype shows why this caveat matters.
- `canonical_key` hashes a structural deck of rooted color-refinement quotients, never the seed, answer, or rendering.  It is invariant under vertex renumbering, edge order, and endpoint reversal, but it is not a complete graph-isomorphism canon; rare nonisomorphic graphs can collide and isomorphic graphs will not split.
- `enumerate_all` deliberately returns `None` above 250,000 naive vectors.  Exact solution multiplicity is therefore unknown for shipping instances; global color permutations guarantee at least `q!` witnesses.
- Instances become easy if the hidden fiber labels leak.  Labels are shuffled and all vertices have equal degree, but untested higher-order statistical signatures may remain.
