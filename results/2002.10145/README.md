# Fixed 4-colouring witness generator

This module generates a graph and asks for one proper 4-colouring: one colour in `1..4` per 0-indexed vertex, with different colours at the ends of every edge. Four clique vertices have fixed colours only to remove the irrelevant global permutation of colour names. A witness is checked exactly in linear time by checking its length, range, anchors, and every edge. The family is the fixed-`C` colouring problem defined in Section 2 of Armin Weiß, [*Hardness of equations over finite solvable groups under the exponential time hypothesis*](https://arxiv.org/abs/2002.10145).

## Why this is the paper's hard regime

Section 2 states that `C`-Colouring is NP-complete for every fixed `C >= 3` and, under ETH, has no `2^o(|V|+|E|)` algorithm. Section 4, Theorem 15 and Lemma 18, use exactly this fixed-colour witness problem as the source of the reduction to finite-group equations. This generator fixes `C=4`; it does not drift into the easy `C=1` or bipartite `C=2` cases, and `n` grows.

I deliberately did not ship the tempting “random group word plus a balancing constant” idea. The paper's Theorem 20 is a worst-case result for equations over certain Fitting-length-three and all Fitting-length-at-least-four solvable groups; an arbitrary balanced random word need not occupy that hard subclass and typically leaves about `1/|G|` of assignments valid. The Introduction also records polynomial algorithms for nilpotent groups and several Fitting-length-two groups. Using the reduction's fixed-colouring source keeps the definition and hardness regime exact.

Generation is inverse: sample a balanced colouring first, then select every non-anchor edge uniformly without replacement from pairs separated by that colouring. Candidates are discarded if degree-statistic guessing, deterministic DSATUR, randomized DSATUR restarts, or bounded exact DSATUR finds a witness. Plants and ordinary vertices do not use different distributions.

## Worked example

This is `make_instance(n=8, seed=7, avg_degree=5.0, attack_restarts=0, backtrack_floor=0, filter_attacks=False)`:

```text
FIXED 4-COLOURING WITNESS PROBLEM

The graph has 8 vertices, numbered 0 through 7 inclusive.
Each line in the edge list is one undirected edge 'u v'.
There are no loops. Edge order and endpoint order have no meaning.
Assign exactly one integer colour in the inclusive range 1..4 to every vertex.
For every listed edge u v, the two endpoint colours must be different.
Colours may be reused on nonadjacent vertices; there is no balance requirement.
Your output order matters: entry i is the colour of vertex i (0-indexed).
The graph contains a 4-clique used only to remove global colour-name symmetry.
The following anchor colours are mandatory:
  vertex 0 -> colour 1
  vertex 1 -> colour 2
  vertex 2 -> colour 3
  vertex 3 -> colour 4

n = 8
m = 20
edges:
0 1
0 2
0 3
0 4
0 5
0 7
1 2
1 3
1 4
1 7
2 3
2 4
2 6
3 5
3 6
3 7
4 5
4 6
5 6
6 7
end edges

Give your final answer inside <answer></answer> tags as exactly 8 comma-separated integers, in vertex-number order.
Do not include brackets, vertex labels, explanations, or any other text inside the tags.
For format only, a hypothetical 4-vertex answer would be:
<answer>1, 2, 3, 4</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>1, 2, 3, 4, 4, 2, 1, 3</answer>`. `verify(inst, [1,2,3,4,4,2,1,3])` returns `(True, "ok")`. Changing the last entry to `4` returns `(False, "edge (3, 7) has equal endpoint colours")`.

## Difficulty presets

| Preset | Vertices | Edges | Random restarts filtered | Exact-search floor | Status |
|---|---:|---:|---:|---:|---|
| `easy` | 140 | 630 | 32 | 10,000 nodes | **Ships; oracle held** |
| `medium` | 160 | 720 | 48 | 30,000 nodes | Local gates pass; oracle not reached |
| `hard` | 180 | 810 | 64 | 60,000 nodes | Local gates pass; oracle not reached |

The names are relative. `escalate()` adds 20 vertices, 16 restart attempts, and doubles the backtracking floor, up to 240 vertices.

## Gate results at the shipping preset

| Gate | Measured result |
|---|---|
| G1 planted verifies | 12/12 across every preset and four seeds |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | 140 entries recovered; 3/3 garbage cases rejected |
| G4 structure-aware guess | 0/200,000; anchors already enforced |
| G5 exact small count | 1/65,536 valid (`1.52587890625e-5`) |
| G6 adversaries | degree 0/8; greedy 0/8; 32-restart 0/8; 10,000-node exact 0/8 |
| G7 scaling | `n=280`, 1,260 edges, plant valid, exact attack exhausted 10,001 nodes |
| G8 canonical key | 100/100 transformations invariant and witness-preserving; 20/20 unrelated keys distinct |

## Oracle hardening loop

All scored calls used medium reasoning. The xAI timeout is retained as an error and did not count toward the verdict.

| Preset | Model | Seed | Result | Why |
|---|---|---:|---|---|
| `easy` | Claude Sonnet 5 | 442429118 | Failed | Empty length-limited response after 32,000 completion tokens |
| `easy` | Grok 4.6 | 172832078 | Error, excluded | 900-second hard deadline exceeded |
| `easy` | Gemini 3.1 Pro Preview | 1962320314 | Failed | Parsed 156 colours; 140 required |
| `easy` | GPT-5.6 Terra | 514926901 | Failed | Parsed 139 colours; 140 required |

The official harness verdict is `hardened`, with zero escalations and shipping preset `easy`.

## Use

```python
import random
import gen_2002_10145 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
demo_reply = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = gen.parse_answer(demo_reply)
ok, reason = gen.verify(inst, candidate)  # (True, "ok")
random_guess = gen.random_candidate(inst, random.Random(9))
```

From the repository root, emit 20 fresh, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2002.10145 20 easy
```

## Caveats

The ETH theorem is worst-case; it does not prove average-case hardness for this planted, filtered distribution. The local filters and three scored oracle failures are empirical evidence only. In particular, the shipped exact filter stops at 10,000 DSATUR branch nodes, and no industrial SAT/CP solver, spectral/community-recovery algorithm, large local-search budget, or learned solver was tested.

The observed `0/200,000` random-guess rate is under the stated uniform prior with all four anchor constraints enforced. It is not a statistical proof that the true rate is below `1e-6`, and it says nothing about guided search. The tiny exact fraction is measured on a separate 12-vertex dense sample.

Graph isomorphism is not cheaply canonical in general. `canonical_key` uses anchored one-dimensional Weisfeiler-Lehman refinement plus canonical multisets of vertex and edge signatures. It is invariant under every tested relabelling but can over-collapse rare non-isomorphic WL-equivalent graphs. Finally, one of the three counted oracle failures was length-limited with no visible answer; the other two returned malformed-length witnesses that parsed and failed exact verification.
