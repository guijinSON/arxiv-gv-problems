# Planted disjoint-clique witnesses

This module turns Ames and Vavasis, [*Convex optimization for the planted k-disjoint-clique problem*](https://arxiv.org/abs/1008.2814), into a witness search task. The solver receives a simple undirected graph as a labeled 0/1 adjacency matrix and must return `k` pairwise vertex-disjoint cliques of one stated size. A checker verifies sizes, ranges, disjointness, and every required edge by lookup. It accepts any valid collection, not only the plant, and makes no optimality or uniqueness claim.

Generation samples the witness first, forces its within-clique edges, samples every other edge independently with probability `1/2`, and finally uniformly relabels all vertices and shuffles displayed rows. The required size is `r = floor(n^(9/20)) + 1`, so it is asymptotically `o(sqrt(n))`.

## Why this regime is hard

Section 2 defines a `k`-disjoint-clique subgraph as `k` disjoint cliques that need not cover all vertices, and observes worst-case NP-hardness already at `k=1`. The witness task uses that feasibility core rather than the paper's maximum-node objective, because claiming optimality is not cheaply checkable.

The generator deliberately avoids both recovery results. Section 3, Theorem 3.1 recovers adversarial instances with only `O(r_hat^2)` suitably degree-bounded extra edges. Section 4's random model is the model used here, but Theorem 4.5 has a dominant `sqrt(N)` term; the following examples require minimum clique size at least order `sqrt(N)` and restrict the clique count. Section 5 further notes that its bound at `p=1/2` cannot hold below `3 sqrt(N)`, although its simulations recover some smaller cliques. Here `r=N^0.45+O(1)`, outside the proved polynomial regime. No polynomial-time algorithm is known for planted clique at this sub-square-root scale; that average-case hardness is a standard conjecture, not proved by this paper. Section 6 explicitly says matching lower bounds are open.

## Worked `demo` example

This is the complete output of `make_instance(n=16, k=2, seed=0)`:

```text
Planted k-disjoint-clique witness problem

The graph has 16 vertices numbered 0 through 15 inclusive.
It is a simple undirected graph: it has no loops, and adjacency is
symmetric. A clique of size r is a set of r distinct vertices for which
every pair of different vertices is joined by an edge.

Find exactly 2 pairwise vertex-disjoint cliques, each of size exactly 4.
The cliques need not cover every vertex. The order of the cliques and the
order of vertices inside a clique do not matter. Vertices may not repeat
inside a clique or occur in two different cliques.

ADJACENCY MATRIX
Each labeled row contains exactly one bit per vertex. In row v, bit j is
1 exactly when vertices v and j are adjacent; positions are counted from
0 at the left. Every diagonal bit is 0. Rows may be displayed out of
numeric order, so use the integer label before the colon.
13: 1101110101011001
9: 0111000010100110
2: 1100111111101010
3: 0100110111111101
5: 0111101110000111
12: 1111101100010100
7: 0011110000101101
15: 0101111100000110
10: 1111101111010010
6: 0010110000111011
8: 1011110001100000
11: 1101101000101110
1: 0011110001111111
0: 0010100010111100
14: 0110011001110001
4: 1111011110111101

Return a JSON array containing exactly 2 arrays. Each inner array must
contain exactly 4 distinct 0-based vertex numbers. JSON integers only:
do not use names, ranges, ellipses, or repeated values.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example syntax only (for two cliques of size three):
<answer>[[0,4,9],[2,5,7]]</answer>
Output nothing else inside the tags.
```

The planted output is `<answer>[[4,7,13,15],[2,5,6,14]]</answer>`. `verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping `15` from the first clique returns `(False, "wrong clique size at clique 0: expected 4, got 3")`.

## Difficulty presets

| Preset | `n` | `k` | `r` | Render size | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 16 | 2 | 4 | 1,583 chars | Oracle solved 3/3; example only |
| `easy` | 144 | 3 | 10 | 22,751 chars | **Ships; local gates pass and 3/3 deciding vendors failed** |
| `medium` | 225 | 3 | 12 | 53,126 chars | Available; not reached |
| `hard` | 400 | 3 | 15 | 163,551 chars | Available; not reached |
| `extreme` | 625 | 4 | 19 | 395,526 chars | Available; not reached |

An earlier `n=64, k=2, r=7` rung is not retained: despite three oracle failures in a discarded run, G6 rejected it because degree-greedy solved 4/8 seeds and 24-restart randomized greedy solved 8/8. `escalate()` increases `n` by 50% (at least 64) while retaining the sub-square-root exponent.

## Gate results at shipping difficulty

| Gate | Measured result |
|---|---|
| G1 | 15/15 plants verified: 5 presets × 3 seeds |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | Exact nested JSON recovered through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; prior is a uniform unordered collection of 3 disjoint 10-subsets; space `7.6108591564668016950083925430123137143136e42` |
| G5 | Exact control: 110/450,450 witnesses valid, fraction `2.442002442002442e-4`; shipping enumeration capped to `None` |
| G6 | Degree-outlier greedy 0/8; left-to-right greedy 0/8; 24-restart induced-degree greedy 0/8 |
| G7 | Doubled `n=288` builds and verifies; `r` grows 10→13 and the candidate space grows |
| G8 | 80/80 invariance checks and 80/80 carried witnesses passed; 20/20 unrelated keys distinct |

## Official oracle loop

The harness used fresh seeds and three distinct vendors at each level. Full replies, timings, HTTP statuses, and finish reasons are in `llm_loop_transcript.jsonl`.

| Preset | Model | Seed | Result | Checker outcome |
|---|---|---:|---|---|
| `demo` | `google/gemini-3.1-pro-preview` | 812438248 | solved | `ok` |
| `demo` | `anthropic/claude-sonnet-5` | 1943991620 | solved | `ok` |
| `demo` | `x-ai/grok-4.6` | 2003245630 | solved | `ok` |
| `easy` | `openai/gpt-5.6-terra` | 1347993041 | failed | missing edge `20-51` in clique 0 |
| `easy` | `x-ai/grok-4.6` | 155789554 | failed | missing edge `16-49` in clique 1 |
| `easy` | `anthropic/claude-sonnet-5` | 1665229993 | failed | empty length-limited response after 32,000 completion tokens |

Verdict: `hardened` after one escalation; shipping preset `easy` with `n=144, k=3`.

## Use

```python
import gen_1008_2814 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 1008.2814 20 easy
```

## Caveats

- Worst-case NP-hardness does not prove this planted distribution hard. Theorem 4.5 is sufficient, not a lower bound, and Section 5 reports recovery below its theoretical boundary. Spectral/SDP recovery, branch-and-bound, SAT/MIP encodings, and modern planted-clique algorithms were not benchmarked here.
- `0/200,000` is the observed rate under the exact shape-aware uniform prior. It is not a statistical proof that the true probability is below `10^-6`, and it says nothing about graph-aware sampling. Multiple valid witnesses, including accidental cliques, may exist.
- The restart panel used 24 starts and an induced-degree growth rule. It did not test tabu search, simulated annealing, local clique swaps, exact maximum-clique software, or large restart budgets.
- The planted and decoy vertices share labels and the same non-forced edge law, but clique membership necessarily raises a planted vertex's expected internal degree. The tested degree attack did not exploit that shift successfully at shipping size; stronger statistical attacks may.
- One of the three deciding oracle failures was an empty length-limited response. The other two returned full, parseable, shape-correct witnesses that failed exact edge checks.
- `canonical_key` is a complete canonical serialization when 1-WL makes all vertices unique, as it did in the tested random instances. Its stable-profile fallback is only a strong invariant; adversarial nonisomorphic graphs could collide.
