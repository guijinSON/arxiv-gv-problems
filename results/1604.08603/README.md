# Cubic claw/path edge decompositions

- **Native domain:** combinatorics
- **Computational core:** exact cover
- **Intended intuition:** exact-cover constraint propagation for an edge decomposition

This generator turns Bulteau, Fertin, Labarre, Rizzi, and Rusu's paper [*Decomposing Cubic Graphs into Connected Subgraphs of Size Three*](https://arxiv.org/abs/1604.08603) into a witness problem.  A solver receives a labelled simple connected cubic graph and must partition every edge into 3-edge claws (`K1,3`) and 3-edge simple paths (`P4`).  A witness is a JSON list of edge-ID triples.  Verification is linear in the answer length: check exact coverage, then recompute the four endpoint degrees of every triple.

## Why this is the hard regime

Section 1 defines an `S'`-decomposition as an edge partition into copies of the allowed graphs.  Table 1 classifies every nonempty subset of `{K1,3, K3, P4}` on cubic graphs.  This module uses exactly `{K1,3, P4}`, which is NP-complete by Theorem 2 in Section 4.  The exclusions matter: Proposition 3 makes claw-only decomposition equivalent to bipartiteness; Proposition 2 makes path-only decomposition equivalent to having a perfect matching; and Proposition 6 puts `{K1,3,K3}` in P.  The paper gives no FPT or approximation result that solves this witness regime.

The generator first samples a random mixed claw/path decomposition and identifies its incidence roles into a simple connected cubic base graph.  It then applies the co-fish construction of Section 4, Lemma 3, to all three edges of several sampled claws.  Each replacement has an explicit planted local decomposition.  In every perfect matching the bridge into a co-fish's odd five-vertex core must be used, so the adjacent subdivision vertex cannot match back into the base.  Attaching all three edges at one old claw centre therefore leaves that centre unmatched: every generated instance lacks a perfect matching and avoids Proposition 2.  A co-fish contains triangles, so the graph is also non-bipartite and avoids Proposition 3.  Finally, vertex labels, edge rows, groups, and IDs inside groups are shuffled.

## Worked easy example (`seed=0`)

The complete rendered instance is:

```text
CUBIC GRAPH EDGE DECOMPOSITION

The input is a simple undirected graph. Vertices are the integers
1 through 38. Edges are numbered 1 through 57
in the table below. Each table row has the form `edge_id: endpoint endpoint`.

Partition every edge into groups of exactly three. Each group must be
one of these (the chosen three edges need not be an induced subgraph):
  * K1,3 (claw): three edges sharing one centre and having three distinct leaves;
  * P4 (path): a simple path of three edges on four distinct vertices.

Every edge ID must occur exactly once. Groups and IDs within a group may
be in any order. Repetitions are forbidden. Vertex and edge IDs are 1-indexed.

EDGES
1: 23 36
2: 1 20
3: 13 32
4: 16 22
5: 24 38
6: 9 10
7: 8 37
8: 1 3
9: 3 7
10: 2 22
11: 15 28
12: 27 36
13: 6 37
14: 8 26
15: 21 25
16: 23 35
17: 7 35
18: 11 15
19: 10 18
20: 15 31
21: 22 30
22: 6 24
23: 21 36
24: 16 29
25: 27 31
26: 5 13
27: 17 27
28: 26 37
29: 12 32
30: 5 18
31: 4 16
32: 2 4
33: 19 38
34: 1 7
35: 5 25
36: 11 32
37: 25 34
38: 20 35
39: 8 24
40: 11 13
41: 12 21
42: 14 38
43: 4 29
44: 33 34
45: 14 33
46: 9 33
47: 14 31
48: 28 30
49: 9 17
50: 17 18
51: 28 34
52: 6 26
53: 3 20
54: 10 12
55: 19 23
56: 2 29
57: 19 30

Your answer must be a JSON array of exactly 19 arrays,
each inner array containing exactly three integer edge IDs.
Give your final answer inside <answer></answer> tags, in that JSON format.
Example: <answer>[[1,2,3],[4,5,6]]</answer>
The example only illustrates syntax and is not an answer to this instance.
Output nothing else inside the tags.
```

A valid answer is:

```text
<answer>[[16,1,17],[32,31,43],[4,24,56],[40,26,3],[8,53,9],[48,10,21],[6,19,54],[45,46,44],[47,25,12],[38,2,34],[35,30,15],[52,39,14],[27,50,49],[37,51,11],[41,23,29],[5,42,22],[33,55,57],[7,13,28],[18,20,36]]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Removing the last ID from its first group returns `(False, "piece_arity: group 1 has 2 IDs")`.

## Difficulty presets

`n` counts base vertices; co-fish replacements add 18 vertices per selected claw.  Sizes below are representative for the stated parameters (rounding controls the selected-claw count).

| preset | base `n` | claw fraction | marked-claw fraction | final vertices / edges | status |
|---|---:|---:|---:|---:|---|
| easy | 20 | 0.50 | 0.20 | 38 / 57 | rejected: Grok solved its oracle instance |
| medium | 32 | 0.50 | 0.22 | 68 / 102 | rejected: Grok solved its oracle instance |
| **hard** | **48** | **0.50** | **0.25** | **102 / 153** | **shipping; all three scored attempts failed** |

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified (3 presets × 4 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | realistic prose/fence/tag response round-tripped exactly |
| G4 | 0/200,000 structure-aware random edge partitions verified; `< 1e-6` |
| G5 | at shipping `hard` (`n=48`, 153 edges): 0/200,000 sampled candidates verified (observed fraction 0; one-sided 95% upper bound `1.49785e-5`); Algorithm X used 1,600,000 nodes over 8 capped runs in 44.2327 s, with 0 successes |
| G6 | 0/8 successes for each of outlier, greedy, 256-restart, and 200,000-node Algorithm X attacks; Algorithm X runs took 3.7635–8.5286 s each |
| G7 | doubling base `n` from 48 to 96 built 306 edges and the plant verified |
| G8 | 60/60 relabelling checks invariant, 60/60 carried witnesses verified, 20/20 unrelated keys distinct |

The exact measurements, including the per-seed Algorithm X node counts and wall times, are in [`selftest_report.json`](selftest_report.json).  For comparison only, exhaustive enumeration on the smaller `n=12`, 18-edge instance found 618 valid answers among 190,590,400 candidates (`3.24256e-6`); this reduced-instance number is not the shipping G5 result.

## Oracle hardening loop

The harness master seed was `7711185395423585077`; effort was `medium`.  “Invalid shape” means the response parsed but at least one edge triple was neither a claw nor a four-vertex path.  Empty length-limited responses are shown explicitly.  The Grok timeout on hard was an error and was redrawn, so it did not count as a failed attempt.

| preset | model | seed | outcome | reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 898058147 | failed | invalid shape, group 6 |
| easy | Grok 4.6 | 1108568122 | **solved** | verified `ok` |
| easy | Claude Sonnet 5 | 1291348702 | failed | empty, 32k-token length limit |
| medium | Gemini 3.1 Pro Preview | 1014408957 | failed | invalid shape, group 20 |
| medium | Claude Sonnet 5 | 2084566138 | failed | empty, 32k-token length limit |
| medium | Grok 4.6 | 595443646 | **solved** | verified `ok` |
| hard | Claude Sonnet 5 | 1773782304 | failed | empty, 32k-token length limit |
| hard | Grok 4.6 | 965353100 | error/excluded | 900-second total deadline |
| hard | Gemini 3.1 Pro Preview | 349987110 | failed | invalid shape, group 1 |
| hard | GPT-5.6 Terra | 220298671 | failed | invalid shape, group 1 |

The authoritative records, including full replies and HTTP metadata, are in [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) and [`.meta.json`](.meta.json).

## Use

From this directory:

```python
import random
import gen_1604_08603 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
random_baseline = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit 20 fresh hard instances with:

```bash
bash scripts/emit.sh 1604.08603 20 hard
```

## Caveats

- Theorem 2 is worst-case NP-completeness for the whole cubic `{K1,3,P4}` class; it does **not** prove that this planted distribution is average-case hard.  The local gates and oracle loop are empirical evidence only.
- Co-fish gadgets are recognizable.  A construction-aware bridge-neighbourhood attack failed 0/8, but no proof rules out a more sophisticated gadget contraction followed by SAT, ILP, CP-SAT, or matching repair.  No optimized external DLX/ILP solver was run; the domain attack is pure-Python Algorithm X capped at 200,000 search nodes per seed.
- The shipping density is a sample result, not an exact count: 0/200,000 observed hits has a one-sided 95% upper bound of `1.49785e-5`.  Likewise, each Algorithm X run stopped at its 200,000-node cap; taking 44.2327 s in aggregate without finding a witness measures this baseline's cost, but does not prove that another exact-cover implementation cannot solve the instances cheaply.
- G4 samples uniformly from partitions of every edge into unordered triples.  It already enforces exact coverage, no repetition, group count, and arity.  It does not condition every triple to be a legal claw/path, because combining only legal triples while preserving exact coverage is the exact-cover problem being measured.  Thus 0/200,000 bounds this stated prior, not every heuristic prior.
- One of the three scored hard failures was an empty response after spending the 32k completion budget.  The harness counts that as failure by policy, but it is weaker evidence than the two nonempty, parsed, invalid witnesses.
- `canonical_key` is a strong relabelling-invariant multiset of rooted colour-refinement quotients, not a complete graph-isomorphism canonical form.  Non-isomorphic highly regular graphs could collide, although 20/20 unrelated test instances were distinct.
