# Split-graph List Coloring certificates from arXiv:1910.10364

| classification axis | declaration |
|---|---|
| Native domain | combinatorics |
| Computational core | exact cover |
| Intended intuition | recognize exact cover inside the split-graph coloring reduction |

This is a discretised, restricted analogue of the paper's full List Coloring
family. Section 5, Lemma 5 licenses the Independent Set to split-graph List
Coloring step; this generator first restricts the arbitrary Independent Set
graph to the intersection graph of a planted regular 3-uniform hypergraph. It
therefore discards arbitrary graph instances and asks for only the compact set
of low-color clique vertices rather than an explicit color for every vertex.

## What this generates

This module turns I. Vinod Reddy's [*Parameterized Coloring Problems on Threshold Graphs*](https://arxiv.org/abs/1910.10364) into a witness-search task. The input is a list of 3-element sets. Those sets compactly define exactly the split graph and color lists in the paper's reduction: one clique vertex per set, and one independent-set vertex per intersecting pair. A solver returns the IDs of `n` pairwise-disjoint sets. Those IDs identify the clique vertices receiving the low colors; the rest of the proper list coloring follows deterministically. Checking only requires range, uniqueness, and set-intersection tests.

The generator samples the answer slots first, puts a random partition of `3n` elements in those slots, and fills the other slots from random residual stubs. Every set has size 3 and every element occurs exactly `degree` times. IDs and element labels are randomized, so the planted sets do not have a special size, frequency, or input position.

## Why this is a hard regime

Section 2 defines split graphs. Section 5, Lemma 5 proves List Coloring NP-complete on split graphs by reducing an arbitrary Independent Set instance `(G,k)`: clique vertices receiving colors `1..k` are exactly an independent set of size `k` in `G`. Here `G` is the intersection graph of the listed triples, so such an independent set is exactly an exact cover. The palette and clique both have `degree*n` members and therefore grow with `n`.

The easy regime is explicit in the same section. Lemma 6 gives an `O(K^K(m+n))` split-graph algorithm parameterized by the palette/list bound `K`: enumerate clique colorings, then extend each to the independent set greedily. Keeping `K` small would make a bad generator, so every preset grows it with `n`. Sections 3 and 4 give FPT algorithms for Precoloring Extension and Equitable Coloring near cliques/threshold graphs; this generator does not mistake those tractable families for the hard result.

## Worked easy instance (`n=6`, `degree=3`, `seed=0`)

The complete rendered instance is:

```text
Find a compact certificate for a proper list coloring of a split graph.

Definitions and construction.
A proper coloring assigns a color to every vertex so adjacent vertices
have different colors. A list coloring must assign each vertex a color
from that vertex's permitted list. A split graph has a clique (all pairs
adjacent) and an independent set (no pairs adjacent).

There are 18 clique vertices c_0 through c_17.
Clique vertex c_i represents triple T_i below and permits every color 1 through 18.
Two triples intersect when they contain at least one equal element.
For every intersecting pair T_i,T_j, the split graph has one independent
vertex p_{i,j}. It is adjacent to every clique vertex except c_i and c_j,
and its permitted colors are 7 through 18, inclusive.
There are no other vertices or edges. This completely defines the graph
and all lists; you do not need to print the full coloring.

A compact certificate is exactly the IDs of the clique vertices that
receive the low colors 1 through 6. It is valid exactly when the chosen
triples are pairwise disjoint. Because each triple has three elements and
there are 18 elements, choosing 6 pairwise-disjoint triples
also covers every element. Such a certificate always completes to a list
coloring: give selected clique vertices the low colors, unselected clique
vertices distinct high colors, and each p_{i,j} the high color of an
unselected endpoint.

Choose exactly 6 distinct triple IDs from 0 through 17, inclusive.
Order does not matter. Repeats are forbidden. Element labels are integers
from 0 through 17, inclusive.

Triples, in the format ID: element element element:
0: 3 11 17
1: 0 14 17
2: 0 2 4
3: 0 7 8
4: 6 7 11
5: 5 6 10
6: 2 13 14
7: 1 10 13
8: 2 4 8
9: 1 6 12
10: 7 9 14
11: 12 16 17
12: 3 5 16
13: 9 12 15
14: 5 13 15
15: 1 4 11
16: 3 8 9
17: 10 15 16

Give your final answer inside <answer></answer> tags, as a comma-separated list of triple IDs.
Example format: <answer>0, 1, 2</answer>
Output nothing else inside the tags.
```

The complete output is `<answer>1, 4, 7, 8, 12, 13</answer>`. `verify(inst, [1,4,7,8,12,13])` returns `(True, "ok")`; dropping the last ID returns `(False, "wrong length: expected 6 triple IDs, got 5")`.

## Difficulty presets

| preset | `n` | degree | triples/palette `K` | status |
|---|---:|---:|---:|---|
| easy | 6 | 3 | 18 | calibration only; all 3 oracle models solved it |
| medium | 40 | 5 | 200 | **shipping**; hardened |
| hard | 80 | 5 | 400 | local gates pass; oracle not reached because medium held |

## Gate results at shipping difficulty

| gate | measured result |
|---|---|
| G1 | 12/12 plants verify across all presets and four seeds each |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 40 IDs round-trip through prose, fences, and answer tags |
| G4 | 0/200,000 structure-aware random candidates verify; candidate space has 43 digits |
| G5 | shipping `n=40`, `degree=5`: 0/200,000 uniform candidates verified (observed fraction `0.0`); min-column Algorithm X reached its 10,000-node cap after 10,001 visited nodes in 0.1076663970015943 seconds and returned no witness |
| G6 | 0/8 successes for each of 5 attacks |
| G7 | doubled `n=80` instance builds and its plant verifies; search space grows from 43 to 86 digits |
| G8 | 60/60 invariant keys, 60/60 carried witnesses, 20/20 unrelated keys distinct |

The G6 attacks are minimum conflict-degree outlier selection, input-order greedy packing, 256 random greedy restarts, a bottom-adjacency-eigenvector spectral ranking with greedy repair, and min-column Algorithm X capped at 10,000 search nodes. The exact-cover attack hit its cap on all eight trials.

## Oracle hardening loop

The authoritative rows are in `llm_loop_transcript.jsonl`. The final run used reasoning effort `medium` and a 64,000-token ceiling; transport errors did not count.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 391680534 | solved | verified cover |
| easy | GPT-5.6 Terra | 135316192 | solved | verified cover |
| easy | Gemini 3.1 Pro Preview | 1521135225 | solved | verified cover |
| medium | GPT-5.6 Terra | 288683483 | failed | returned overlapping triples 156 and 162 |
| medium | Claude Sonnet 5 | 932532152 | failed | empty length-limited response after 64k completion tokens |
| medium | Grok 4.6 | 1986312803 | error, excluded | 900-second total deadline |
| medium | Grok 4.6 | 1109845671 | error, excluded | 900-second total deadline |
| medium | Gemini 3.1 Pro Preview | 441230736 | failed | returned overlapping triples 22 and 38 |

The script verdict is `hardened` at medium after one escalation. The Claude row is formally a failed attempt under the harness but is weaker evidence than the two explicit invalid witnesses; that limitation is not hidden.

## Use

```python
import random
import gen_1910_10364 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer("<answer>0, 4, 9</answer>")
ok, reason = g.verify(inst, candidate)
structured_guess = g.random_candidate(inst, random.Random(7))
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 1910.10364 20
```

## Caveats

The paper proves worst-case NP-completeness of the containing split-graph List Coloring class, not average-case hardness of this planted regular distribution. The 0/200,000 guess result is an observed rate under a uniform prior over distinct size-`n` ID subsets; it is not a statistical proof that every informed proposal distribution has probability below `1e-6`. Algorithm X was capped, and an uncapped exact solver eventually finds a finite witness.

The panel did not run a full SAT/ILP encoding, dancing links with advanced learning, multi-eigenvector/SDP relaxations, or MCMC. The spectral probe is a cheap single-vector method. The strongest shipping-preset G6 baseline reached its Algorithm X cap in just 0.1076663970015943 seconds. That cheap capped failure is weak evidence of hardness, not a solved lower bound. Also, `canonical_key` is a strong typed incidence-distance fingerprint, not a complete hypergraph-isomorphism canonical form, so adversarial non-isomorphic collisions are possible even though all tested relabelings and unrelated instances behaved correctly. Finally, plant triples are marginally distributed like decoys and all stated local degrees are balanced, but the planted sets are jointly disjoint; a stronger construction-aware global attack may exploit that correlation.
