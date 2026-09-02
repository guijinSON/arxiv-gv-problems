# Critical Node Cut witness generator for arXiv:2506.23363

This module turns [*Parameterized Critical Node Cut Revisited*](https://arxiv.org/abs/2506.23363) by Knop, Melissinos, and Vasilakis into an unlimited exact-witness task. A solver receives a shuffled simple graph and must name exactly `k` vertices whose deletion leaves zero connected vertex pairs. Zero pairs means no edge remains, so the witness is precisely a size-`k` vertex cover. `verify` checks the list and every edge in linear time, accepts any valid cover, and never reads the planted answer.

## Why this is a hard regime

Section 2 gives the exact CNC definition and the connected-pair formula; the Introduction explicitly identifies `x=0` with Vertex Cover. Thus worst-case NP-hardness already holds in this exact specialization, with no closed form or known polynomial-time algorithm. The generator samples a balanced NAE-3-SAT assignment and all future clause omissions first, builds paired complementary clauses around it, applies the standard SAT-to-Vertex-Cover gadgets, then uniformly relabels the graph. The two literal vertices of each variable have equal degree and are exchanged by a global complement automorphism; all clause vertices have degree three. The plant is therefore not a degree, sign-frequency, or construction-order outlier.

The paper's stronger Section 3 theorem (`thm:CNC:fes`) proves W[1]-hardness for the combined parameter `k + fes + maximum-degree + pathwidth`; this generator does **not** claim to instantiate that reduction or prove average-case hardness from it. Instead, `k` and the random incidence core grow linearly. This avoids the easy regimes catalogued in the Introduction and Sections 4–5: trees, bounded treewidth (`n^O(tw)` exact DP and FPT in `x+tw`), small `k`, bounded max-leaf number, vertex integrity, modular-width, and constant clique-width. The paper's treewidth FPT approximation scheme does not settle exact feasibility at objective zero.

## Worked demo (`demo`, seed 0)

The complete rendered instance is:

```text
CRITICAL NODE CUT — EXACT ZERO-PAIR WITNESS

You are given a simple undirected graph.  Vertices are the integers 1 through
24, inclusive.  Each row in the edge list is one unordered
edge {u,v}; there are no loops or duplicate edges.

For a deletion set S, remove every vertex in S and every incident edge.  Two
distinct remaining vertices form a connected pair when an undirected path
joins them in the remaining graph.  If the remaining connected components
have sizes c_1,c_2,..., the number of unordered connected pairs is
sum_i c_i*(c_i-1)/2.

Find exactly 14 distinct vertices whose deletion leaves at most
0 connected pairs.  Because the bound is zero, equivalently every
listed edge must have at least one endpoint in your deletion set.  Order does
not matter.  Repeated vertices are forbidden, and no vertex outside the
inclusive range 1..24 is allowed.

VERTEX_COUNT 24
EDGE_COUNT 30
DELETE_EXACTLY 14
CONNECTED_PAIR_BOUND 0
EDGES
19 20
5 21
6 8
5 18
4 20
2 22
11 14
16 23
5 23
4 12
1 11
12 17
4 9
3 10
6 15
9 20
11 15
2 14
3 7
17 18
18 23
3 24
16 19
1 7
8 10
13 21
14 15
22 24
9 13
10 24
END_EDGES

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 14 distinct vertex integers.
Syntax example only, for a hypothetical instance asking for three vertices:
<answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

One answer is `<answer>7, 12, 8, 9, 11, 16, 24, 18, 5, 20, 2, 13, 15, 3</answer>`. `verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the final `3` returns `(False, "expected exactly 14 vertices, got 13")`.

## Difficulty presets

| Preset | Variables `n` | Mean constraint degree | Graph vertices | Edges | `k` | Status |
|---|---:|---:|---:|---:|---:|---|
| `demo` | 6 | 1 | 24 | 30 | 14 | Readable calibration only; fails G4 and was solved by 3/3 oracles |
| `medium` | 66 | 8 | 1,188 | 2,178 | 770 | **Ships; hardened** |
| `hard` | 90 | 8 | 1,620 | 2,970 | 1,050 | Available, not needed by the oracle loop |
| `extreme` | 114 | 8 | 2,052 | 3,762 | 1,330 | Available, not needed by the oracle loop |

An earlier `n=60, degree=8` candidate was rejected because the random-restart hill climber solved seed 5 (1/8 panel instances). Raising the core to `n=66` while preserving density and symmetry reduced that same attack to 0/8.

## Gate results

| Gate | Final measurement |
|---|---|
| G1 | 16/16 planted witnesses verified (4 presets × 4 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | Model-style fenced/prose response round-tripped all 770 IDs |
| G4 | Visible gadget blocks recovered exactly; 0/200,000 structure-aware guesses verified; analytical upper bound `1.0829e-115` |
| G5 | 144/1,961,256 naive candidates valid on the enumerable instance (`7.3422e-5`) |
| G6 | Outlier 0/8; max-uncovered-degree greedy 0/8; 16-restart hill climb 0/8 |
| G7 | `n=132` built and verified; vertices 1,188→2,376, search bits 1,107→2,218 |
| G8 | 60/60 invariance checks, 20/20 transported witnesses, 20/20 unrelated keys distinct |

The exact machine-readable measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle hardening loop

The final, script-owned run used master seed `10947898096777182509`, recorded in `.meta.json`. The demo was deliberately easy. Three distinct vendors then failed on `medium`, so the harness stopped after one escalation with `verdict: hardened`.

| Preset | Model | Seed | Result | Checker reason |
|---|---|---:|---|---|
| demo | Anthropic Claude Sonnet 5 | 798501224 | solved | `ok` |
| demo | Google Gemini 3.1 Pro Preview | 414397069 | solved | `ok` |
| demo | OpenAI GPT-5.6 Terra | 422128683 | solved | `ok` |
| medium | Google Gemini 3.1 Pro Preview | 185811089 | failed | uncovered edge `795 1079` |
| medium | OpenAI GPT-5.6 Terra | 1069201450 | failed | uncovered edge `1021 1082` |
| medium | xAI Grok 4.6 | 1739701175 | failed | uncovered edge `827 1173` |

See [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) for replies, parsing flags, timing, and full reasons. Every medium reply contained a parseable tagged witness; no parser failure or API error contributed to the verdict.

## Use

```python
import gen_2506_23363 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit fresh distinct shipping instances with:

```bash
bash scripts/emit.sh 2506.23363 20 medium
```

## Caveats

The NP-hardness statement is worst-case; planting, local gates, and the LLM panel do not prove this distribution average-case hard. Gadget boundaries are cheaply recoverable, so a solver can reduce the graph back to balanced NAE-3-SAT; that is intentional. G4 samples uniformly from the forced local shape—one endpoint of every variable edge and two vertices of every clause triangle—rather than from arbitrary `k`-subsets. Zero hits is a point estimate with resolution `1/200,000`, not a statistical proof that the true probability is zero or below that resolution.

The cheap adversary panel did not test complete SAT/Vertex-Cover solvers, modern noisy WalkSAT, spectral recovery, or message passing. The prescribed oracle models all returned invalid covers at medium, but this only establishes failure for those prompts, seeds, and token budgets. Finally, exact graph isomorphism is not known to be tractable in general: `canonical_key` uses triangle-enriched stabilized Weisfeiler–Leman color and edge histograms. It passed all required transformations and distinctness trials but can theoretically collide on non-isomorphic adversarial graphs.
