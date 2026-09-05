# Cubic claw/path edge decompositions

> **Current status:** the generator and local gates G1--G8 pass, and the G9 size/effort caps pass. The required fresh oracle and G9(b) calls are **not scored** because every OpenRouter redraw returned HTTP 403 (`Key limit exceeded`). This is an external blocker, not evidence that an oracle failed. Accordingly, `G9_no_tool_suitability.pass` and `all_passed` are false and this directory is not ready to submit.

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (an edge partition represented by nested edge-ID triples) |
| Native objects | labelled simple connected cubic graph; edge IDs |
| Intended intuition | constraint propagation from bridges and local edge-incidence degrees |
| Domain essentiality | native |
| Reduction | none |

## Problem and certificate

This module turns Bulteau, Fertin, Labarre, Rizzi, and Rusu’s [*Decomposing Cubic Graphs into Connected Subgraphs of Size Three*](https://arxiv.org/abs/1604.08603) into a witness problem. A solver receives a labelled simple connected cubic graph and must partition every edge into three-edge claws (`K1,3`) and three-edge simple paths (`P4`). The graph is the paper’s native object; no graph-to-SAT or other convenience reduction is used.

The witness is a JSON array of edge-ID triples. `verify` never reads the planted answer: it checks exact edge coverage and recomputes each triple’s endpoint-degree multiset, accepting `[1,1,1,3]` for a claw or `[1,1,2,2]` for a path. Thus verification is exact and linear in the written certificate.

## Why Track A is claimed

Section 1 fixes “decomposition” as an edge partition into subgraphs isomorphic to the allowed shapes. Section 4, Theorem 2 proves NP-completeness for exactly the simple connected cubic `{K1,3,P4}` regime. That is worst-case evidence, not an average-case theorem for this generator, so the distribution claim also rests on the measured attacks below.

The easy regimes identified by the paper are deliberately excluded. Proposition 2 says that a cubic graph has a `P4`-only decomposition exactly when it has a perfect matching, and Proposition 3 makes claw-only decomposition equivalent to bipartiteness. The generator attaches the paper’s co-fish gadget (Section 4, Lemma 3) on all three edges of at least one planted claw. The odd co-fish core forces its bridge in every perfect matching; doing this around one old claw centre leaves that centre unmatched. Every non-demo instance therefore has no perfect matching. Co-fish triangles also make it non-bipartite. Proposition 6’s polynomial `{K1,3,K3}` case is irrelevant because this task allows paths and disallows triangles.

The certificate is known by inverse generation, not by solving the emitted instance. A random mixture of claws and paths is sampled first; incidence roles are identified into a simple connected cubic base; the explicit co-fish local identity carries that partition through every attachment. Vertices, edge rows, groups, and IDs inside groups are then independently shuffled.

For an arbitrary emitted instance, the domain-standard route is exact-cover search. The measured minimum-column Algorithm X implementation reached its 200,000-node cap on 8/8 shipping seeds: 1,600,000 nodes and 88.7790 seconds total, with no witness found. There is no known efficient general method for this generated distribution. The bridge invariant supplies propagation but does not reduce the random base to a formula, which is why this is Track A rather than Track B.

## Worked `demo` example

The smallest preset is genuinely hand-scale. With `seed=0`, `render` returns:

```text
CUBIC GRAPH EDGE DECOMPOSITION

The input is a simple undirected graph. Vertices are the integers
1 through 8. Edges are numbered 1 through 12
in the table below. Each table row has the form `edge_id: endpoint endpoint`.

Partition every edge into groups of exactly three. Each group must be
one of these (the chosen three edges need not be an induced subgraph):
  * K1,3 (claw): three edges sharing one centre and having three distinct leaves;
  * P4 (path): a simple path of three edges on four distinct vertices.

Every edge ID must occur exactly once. Groups and IDs within a group may
be in any order. Repetitions are forbidden. Vertex and edge IDs are 1-indexed.

EDGES
1: 6 7
2: 3 4
3: 1 3
4: 1 6
5: 4 5
6: 5 7
7: 1 2
8: 3 5
9: 2 4
10: 2 8
11: 6 8
12: 7 8

Your answer must be a JSON array of exactly 4 arrays,
each inner array containing exactly three integer edge IDs.
Give your final answer inside <answer></answer> tags, in that JSON format.
Example: <answer>[[1,2,3],[4,5,6]]</answer>
The example only illustrates syntax and is not an answer to this instance.
Output nothing else inside the tags.
```

One valid answer is `<answer>[[8,3,2],[7,10,9],[12,11,4],[1,6,5]]</answer>`. It gives `verify(inst, answer) == (True, "ok")`. Removing the last ID from the first group gives `(False, "piece_arity: group 1 has 2 IDs")`. A person can solve this four-piece illustration on paper by following incidences from a low-choice edge.

## Difficulty presets

`n` is the number of base vertices before co-fish attachments; one selected claw adds 18 vertices and 27 net edges. `hard` is the intended shipping preset once the external gates can be rerun.

| preset | base `n` | claw fraction | marked-claw fraction | final vertices / edges at seed 0 | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 0.50 | 0.00 | 8 / 12 | hand-solvable illustration; skipped by hardening |
| easy | 20 | 0.50 | 0.20 | 38 / 57 | ladder rung; historically solved by one oracle |
| medium | 32 | 0.50 | 0.22 | 68 / 102 | ladder rung; historically solved by one oracle |
| **hard** | **48** | **0.50** | **0.25** | **102 / 153** | intended shipping candidate; fresh run blocked by quota |

`escalate()` first keeps the witness at 153 IDs while raising co-fish crowding (`n=30`, four anchors); this made the same capped Algorithm X attack slower while remaining 0/8. It then uses the remaining output budget (`n=48`, four anchors, 180 IDs / 481 conservative tokens) and returns `"cap_bound"` before another increase would cross the answer-token cap.

## Gate results

| gate | result |
|---|---|
| G1 | pass: 16/16 planted witnesses verified across four presets and four seeds |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: tagged JSON surrounded by prose and a Markdown fence round-tripped |
| G4 | pass: 0/200,000 structure-aware random edge partitions verified |
| G5 | pass: shipping density 0/200,000 sampled; one-sided 95% upper bound `1.49785e-5`; strongest attack 1,600,000 nodes / 88.7790 s / 0 successes |
| G6 | pass locally: outlier, greedy, 256 random restarts, and capped Algorithm X each scored 0/8 |
| G7 | pass: doubling base `n` from 48 to 96 built 306 edges and the carried witness verified |
| G8 | pass: 60/60 relabelling invariance checks, 60/60 carried-witness checks, and 20/20 unrelated keys distinct |
| G9 | **not passed:** caps are 607 chars / 409 conservative tokens / 153 atoms / 153 accounting operations, but hinted-oracle G9(b) has zero scored attempts because of HTTP 403 |

For supplementary scale only, exhaustive enumeration at `n=12`, 18 edges found 618 valid partitions among 190,590,400 candidates (`3.24256e-6`). This smaller count is not substituted for shipping density.

## Oracle loop and G9 arms

The current bare run never reached a scored attempt. `harden.py` correctly retried four times and stopped rather than recording API errors as model failures:

| arm | preset | model | seed | scored result | reason |
|---|---|---|---:|---|---|
| bare | easy | Claude Sonnet 5 | 302293191 | error, excluded | HTTP 403 key limit |
| bare | easy | Grok 4.6 | 1989023747 | error, excluded | HTTP 403 key limit |
| bare | easy | Claude Sonnet 5 | 58072484 | error, excluded | HTTP 403 key limit |
| bare | easy | Claude Sonnet 5 | 1761442549 | error, excluded | HTTP 403 key limit |

The G9 diagnostic is likewise unavailable:

| arm | solved / scored attempts | API errors | verdict |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | unavailable |
| structural hint | 0 / 0 | 4 | unavailable |
| placebo hint | 0 / 0 | 4 | unavailable |

Hinted minus placebo is undefined with zero scored attempts. The structural hint is only the paper’s invariant—“Every bridge must be the middle edge of a three-edge path in any valid decomposition.”—and does not give a procedure or derived answer. The earlier workspace contained a genuine bare run for the same hard instance distribution that held 0/3 at `hard`, but the required fresh run opened the transcript with mode `w` before encountering the quota error. That historical summary is not treated as current gate evidence.

## Use

```python
import random
import gen_1604_08603 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
baseline_guess = gen.random_candidate(inst, random.Random(7))
```

After replenishing the OpenRouter quota, rerun the bare and two isolated G9 arms, update `G9_ARM_RESULTS`/`G9_HINTED_VERDICT` from scored records, and regenerate `selftest_report.json`. From the repository root, emission is:

```bash
bash scripts/emit.sh 1604.08603 20 hard
```

## Caveats

- Theorem 2 is worst-case NP-completeness; it does not prove average-case hardness of this inverse-generated distribution. The attack panel is empirical evidence only.
- Co-fish gadgets are recognizable. The construction-aware bridge-neighbourhood heuristic failed 0/8, but no optimized external DLX, SAT, ILP, CP-SAT, or gadget-contraction solver was run. A stronger co-fish contraction attack is the clearest unresolved risk.
- G4 samples uniformly from partitions of all edge IDs into unordered triples. It enforces arity, group count, no repetition, and exact coverage. It does not condition every triple to be a legal claw/path, because assembling only mutually disjoint legal triples is the exact-cover search itself. Thus `0/200,000` describes this declared prior, not every heuristic prior.
- The 153 “intended-route operations” count is one exact placement/accounting action per edge after structural choices. It does not count speculative exact-cover branches; if the benchmark interprets G9(c) as requiring the entire search—including failed branches—to stay under 300 operations, this family should fail that cap rather than ship.
- `canonical_key` is a strong relabelling-invariant multiset of rooted one-dimensional colour-refinement quotients, not a complete graph-isomorphism canonical form. Highly regular non-isomorphic graphs can theoretically collide.
- The current external evidence is incomplete. The three transcript files intentionally preserve only quota errors, and `.meta.json` has no hardening verdict. Do not submit or represent the family as fully hardened until successful scored runs replace them.
