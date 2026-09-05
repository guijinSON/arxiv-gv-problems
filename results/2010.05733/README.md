# Graph-square-root generator for arXiv:2010.05733

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | matrix certificate (ordered maximal-biclique cover) |
| Intuition | decomposition: see the Boolean adjacency matrix as a union of maximal all-one rectangles |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 4 Lemma 6 |

This is representational coverage through a reduction that is central to the paper, not an unrestricted sample of all VC-k Root instances. The solver is handed the paper's graph gadget and its bipartite cross-edge matrix; the hard search is the Biclique Cover instance embedded by the authors.

## Problem and trust model

The source is Golovach, Lima, and Papadopoulos, [*Graph Square Roots of Small Distance from Degree One Graphs*](https://arxiv.org/abs/2010.05733). A solver receives a finite graph (G) in the exact form of Section 4's reduction and must give (k) inclusion-maximal bicliques covering every edge of a displayed bipartite graph (B). The certificate determines the neighborhoods of the gadget vertices (Z) in a root (H). `verify` checks the bicliques and maximality, constructs (H), checks the designated vertex cover, computes (H^2) with integer bitsets, and compares every adjacency bit with (G). It never reads the planted answer.

Generation is inverse, not solution-driven: sample (k) equal-sized bicliques, form their Boolean union (B), enlarge each sampled biclique to a maximal one, and apply the forward construction in Lemma 6. The generator therefore knows a certificate without solving the generated instance.

All deterministic G1–G9(c) gates pass. The mandated bare oracle loop rejected `easy` after one verified solve, then held `medium` at 0/3. Independent structural-hint and placebo runs at the shipping preset also held at 0/3.

## Why Track A

Section 3, Theorem 2 and Corollary 2 give an FPT algorithm taking \(2^{2^{O(k)}}n^{O(1)}\) time. That is the easy regime to avoid: a small fixed \(k\) would make this a false Track-A claim. The named ladder grows the biclique parameter from 2 to 16. Section 4, Lemma 6 reduces Biclique Cover with parameter \(k\) to VC-\((k+4)\) Root, and Theorem 5 rules out \(2^{2^{o(k)}}n^{O(1)}\) time under ETH.

That theorem is worst-case, not a theorem about this random planted distribution. Distributional evidence comes from the gates: on eight shipping-preset seeds, five construction-aware heuristics and an exact set-cover DPLL over *all* maximal bicliques found no certificate. DPLL exhausted 2,000,000 nodes each time (3.182 s mean, 4.371 s maximum on the final recorded local run). This is evidence, not a proof that the planted distribution is asymptotically hard.

## Worked demo

This is `render(make_instance(seed=0, **DIFFICULTY["demo"]))` in full:

```text
VC-(k+4) graph square root via maximal bicliques

All graphs here are finite, simple, undirected graphs.  The square H^2 of a
graph H has the same vertices as H, and two distinct vertices are adjacent in
H^2 exactly when their distance in H is at most two.

The input graph G has the ordered vertex groups
  X = [3, 8]
  Y = [10, 6]
  Z = [5, 0]
and six further vertices
  u=7, v=11, w=4,
  u'=9, v'=1, w'=2.

Within this statement, Xi means the i-th vertex in the displayed X list, and
Yj means the j-th vertex in the displayed Y list (indices start at 0).
The X-Y edges are the 1 entries of this 2-by-2 matrix; character j of row i
is 1 exactly when XiYj is an edge:
  X00: 01
  X01: 10

All remaining edges of G are defined as follows, with no other edges present:
X union Z union {u} is a clique; X union {v} is a clique; {u,v,w} is a
clique; Y union Z union {u'} is a clique; Y union {v'} is a clique; and
{u',v',w'} is a clique.  (A clique contains every edge between distinct
vertices in the named set.)

A biclique is a pair (A,D) of nonempty subsets A of X and D of Y for which
every possible A-D edge is present.  It is inclusion-maximal when no vertex of
X can be added to A and no vertex of Y can be added to D while preserving that
property.

Find an ordered list C0,...,C1 of exactly 2 inclusion-maximal bicliques
whose union covers every X-Y edge.  Repeated bicliques are allowed.  By the
construction, Ci specifies the neighbors in X union Y of Zi in a square root H;
the fixed root edges are uv, vw, u'v', v'w', all u-X edges, all u'-Y edges,
and every edge inside Z.  Thus your list is a compact matrix certificate for a
square root whose designated vertex cover is Z union {u,v,u',v'}.

Give your final answer inside <answer></answer> tags as a JSON array of exactly
2 pairs [x_bits,y_bits].  Each x_bits is a 2-character 0/1 string whose
character i selects Xi; each y_bits is a 2-character 0/1 string whose
character j selects Yj.  Order inside each bitstring is exactly the displayed
order, both strings must select at least one vertex, and the outer order is the
Z order.  Example of the required shape (not asserted to solve this instance):
<answer>[["10","10"],["10","10"]]</answer>
Output nothing else inside the tags.
```

The planted answer is `[["01","10"],["10","01"]]`. `verify` returns `(True, "ok")`. Dropping the second biclique returns `(False, "answer has too few bicliques: 1 < 2")`. A person can solve this demo by hand: its matrix is a two-edge matching, so its two maximal bicliques are the two singleton edges.

## Difficulty presets

Metrics below use seed 0; `medium` is the shipping preset selected by the bare oracle loop.

| Preset | side (n) | bicliques (k) | planted width | vertices of (G) | answer chars | maximal bicliques |
|---|---:|---:|---:|---:|---:|---:|
| demo | 2 | 2 | 1 | 12 | 28 | 2 |
| easy | 16 | 8 | 4 | 46 | 336 | 72 |
| **medium (ships)** | **26** | **13** | **6** | **71** | **806** | **1,523** |
| hard | 36 | 16 | 7 | 94 | 1,312 | 8,383 |

No preset was rejected by a deterministic gate. The oracle rejected `easy` because Gemini solved one of its three instances; `medium` then held against all three calls and became the shipping preset.

## Gate results

| Gate | Result | Recorded measurement |
|---|---|---|
| G1 | pass | 12/12 plants verified across all presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose/fence parse round-trip and JSON-native round-trip |
| G4 | pass | 0/200,000 structure-aware guesses; 1,902 maximal bicliques at sampled shipping seed |
| G5 | pass | shipping density 0/200,000; demo has exactly 2 valid ordered answers; DPLL mean 2,000,001 visited nodes |
| G6 | pass | six attacks, each 0/8; DPLL mean 3.182 s and max 4.371 s |
| G7 | pass | side doubled 26→52 while answer remains 26 atomic strings; plant verifies |
| G8 | pass | 120/120 invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 806 chars, 202-token size estimate, 26 atoms, 182 intended membership/union operations |

## Oracle loop and G9 diagnostics

The bare ladder was run by `scripts/harden.py`; “failed” means no verified witness, not an API failure.

| Preset | Seed | Model | Solved | Exact outcome |
|---|---:|---|---|---|
| easy | 927497817 | Gemini 3.8 Flash | yes | verified `ok` |
| easy | 1931589643 | GPT-5.6 Terra | no | biclique 0 contains a missing edge |
| easy | 1869417391 | GPT-5.6 Terra | no | biclique 7 is not maximal |
| medium | 1914813670 | Gemini 3.8 Flash | no | biclique 0 contains a missing edge |
| medium | 914560437 | GPT-5.6 Terra | no | empty answer |
| medium | 894554988 | Gemini 3.8 Flash | no | response budget exhausted with no content |

The three-arm diagnostic at the shipping preset is:

| Arm | Solved/attempts | Summary |
|---|---:|---|
| bare | 0/3 | two invalid answers; one empty length-limited response |
| structural hint | 0/3 | two invalid answers; one length-limited partial analysis with no answer block |
| placebo hint | 0/3 | one invalid answer; two empty length-limited responses |

`hinted − placebo` is 0.0. The structural hint names maximal all-one rectangles but gives no extraction procedure. Because both arms are at the 0/3 floor and several Gemini calls exhausted their response budgets, this run does not show that the hint is uninformative; it only shows no measured advantage at this sample size. Answer size is 806 characters / 26 atomic strings, and the intended post-insight certificate construction uses 182 primitive membership placements and rectangle unions.

## Use

```python
from gen_2010_05733 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
assert parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>") == inst["answer"]
```

Emit examples from the repository root with:

```bash
bash scripts/emit.sh 2010.05733 20 medium
```

## Caveats

- Theorem 5 does **not** prove this planted random distribution hard; it proves a worst-case parameterized lower bound. The attack panel and oracle run are distributional evidence, not a theorem.
- G4 samples uniformly from ordered tuples of maximal bicliques, incorporating the freely deducible maximality reduction. Its 0/200,000 result bounds only that prior; it does not model sophisticated correlated search.
- The exact DPLL is a strong standard-library baseline, not an industrial SAT/ILP implementation. No commercial MILP solver, dedicated Boolean matrix-factorization code, or SDP relaxation was run.
- One bare and three G9 responses ended without a candidate because the provider consumed its response budget. The harness scores these as failures, but the transcripts preserve the distinction from a mathematically wrong answer.
- `canonical_key` uses a side-swap-invariant 1-WL signature. It passed all generated relabellings and separated 20 unrelated seeds, but 1-WL is not a complete bipartite graph-isomorphism algorithm and can collide on adversarial graphs.
- The renderer exposes the paper's gadget partition. This deliberately measures the hard biclique decomposition rather than recognition of the reduction gadget.
