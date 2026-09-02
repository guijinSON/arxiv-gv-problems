# Restricted 3-local permutation Mastermind generator

This module turns Bernardo Subercaseaux’s paper [“Price of Locality in Permutation Mastermind: Are TikTok influencers Chaotic Enough?”](https://arxiv.org/abs/2601.19161) into a witness problem. A solver receives a compact, lossless 3-local black-peg transcript. It must return a full permutation whose consecutive three-position block orientations satisfy every transcript gadget. Checking is linear in the answer and clauses: validate the permutation and substitute its A/B block choices into each exact-one constraint. Any valid witness is accepted; the checker never reads the planted answer.

## Why this is a credible hard family

Section 1.1 defines black-peg score and \(\ell_k\)-locality. Section 6, Theorem 23 proves 3-Local-PM-SAT NP-complete via Monotone-1-in-3-SAT. Claim 24 and Table 2 are the exact construction used here: three blocks are walked through nine support-3 moves, and feedback `0 0 0 0 0 0 1 2 3` occurs exactly when one block uses \(\alpha=(2,3,1)\) and two use \(\beta=(3,1,2)\). The reverse walk returns to identity, so gadgets concatenate without losing locality.

The important boundary is also in Section 6: Theorem 28 puts 2-Local-PM-SAT in randomized polynomial time, specifically \(O(N^7\log^2 N)\). This generator therefore uses genuine 3-cycles, never the tractable transposition-only regime. It samples the A/B witness first, generates one-A/two-B clauses around it, gives both plant sides the same degree-2/degree-3 distribution, shuffles all labels and rows, rejects disconnected incidence graphs, and then expands each row by the paper’s fixed gadget.

The paper’s full reduction uses \(O(n^2)\) extra queries to force the block codebook. This family states that codebook as part of the witness shape, then uses the paper’s local clause transcript verbatim. Thus Theorem 23 proves hardness of the encompassing transcript problem and Claim 24 proves the encoding, but it is not an average-case hardness proof for this particular planted distribution. The required oracle and attack evidence below fills that empirical gap.

## Difficulty presets

| preset | blocks \(n\) | permutation \(N=3n\) | clauses | status |
|---|---:|---:|---:|---|
| `easy` | 36 | 108 | 30 | all 3 oracles solved; rejected |
| `medium` | 72 | 216 | 59 | Grok solved; rejected |
| `hard` | 120 | 360 | 98 | **shipping; hardened** |
| `extreme` | 180 | 540 | 148 | available, not reached |

Every preset uses clause ratio `0.82`. `escalate()` multiplies the block count by 1.5 while preserving that sparse satisfiable regime. `SHIPPING_DIFFICULTY` is `hard`.

## Worked `easy`, seed 0 example

Below is the full output of `render(make_instance(n=36, seed=0, clause_ratio=0.82))`.

```text
Restricted 3-local permutation Mastermind witness problem

A permutation of 1,...,108 is an ordered list in which every integer occurs
exactly once. Positions and values are both 1-indexed. Split them into 36
ordered blocks: block i consists of 3i-2, 3i-1, 3i. A permitted secret must use
one of exactly two orientations independently in every block:

  A_i = (3i-1, 3i, 3i-2)
  B_i = (3i, 3i-2, 3i-1).

The full secret is the concatenation of those 36 block triples, in block order.
Thus order matters, values may not repeat, and no other block orientation is
allowed.

Here is the lossless compact representation of a black-peg transcript. A
black-peg score is the number of positions where a query permutation equals the
secret. For three positions p,q,r, move A(p,q,r) replaces the current entries
(g[p],g[q],g[r]) by (g[q],g[r],g[p]); move B(p,q,r) is its inverse. Each move
changes exactly three positions, so consecutive queries are 3-local.

For every listed clause (i,j,k), start at the identity query and perform:

  A(3i-2,3j-2,3k-2), A(3i-1,3j-1,3k-1), A(3i,3j,3k),
  A(3i-2,3i-1,3i), A(3j-2,3j-1,3j), A(3k-2,3k-1,3k),
  B(3i-2,3j-2,3k-2), B(3i-1,3j-1,3k-1), B(3i,3j,3k).

The nine resulting black-peg scores must be
  0 0 0 0 0 0 1 2 3.
Then undo those nine moves in reverse order; the resulting scores must be
  2 1 0 0 0 0 0 0 0,
returning to the identity (whose score is 0) before the next clause. This is a
complete procedural specification of every query permutation and score; there
are no omitted queries. For the two permitted block orientations, matching the
gadget is equivalent to requiring exactly one of blocks i,j,k to have type A.

As a redundant check obtainable by adding all clause equations, if d_i is the
number of listed clauses containing block i and x_i is 1 for type A (0 for B),
then sum(d_i*x_i) must equal 30. Here the degree list d_1,...,d_36 is:
  2 2 2 3 3 3 2 2 2 3 3 3 3 3 3 3 2 2 2 3 3 2 2 3 2 2 3 2 3 3 2 2 2 3 2 3

Instance: 30 clauses. Each row is "row_number: i j k" and contains three
distinct 1-indexed block numbers. Clause order and the order within a row have
no semantic effect.

1: 27 34 2
2: 16 29 4
3: 22 17 23
4: 18 16 20
5: 20 35 11
6: 34 8 12
7: 28 33 16
8: 30 15 19
9: 31 8 25
10: 7 33 35
11: 36 28 32
12: 5 22 3
13: 5 10 34
14: 10 15 36
15: 11 27 21
16: 5 12 9
17: 13 6 36
18: 6 13 14
19: 24 1 27
20: 18 30 4
21: 1 14 13
22: 15 24 26
23: 4 26 19
24: 20 12 14
25: 11 24 32
26: 17 7 21
27: 23 3 21
28: 31 25 29
29: 30 9 2
30: 29 6 10

Find any permitted secret permutation matching every score in the transcript.
Give your final answer inside <answer></answer> tags, as all 108 integers of the
permutation in position order, separated by commas.
Format example for a two-block permutation: <answer>2, 3, 1, 6, 4, 5</answer>
Output nothing else inside the tags.
```

One valid answer is:

```text
<answer>3, 1, 2, 6, 4, 5, 8, 9, 7, 12, 10, 11, 15, 13, 14, 18, 16, 17, 21, 19, 20, 24, 22, 23, 27, 25, 26, 29, 30, 28, 33, 31, 32, 35, 36, 34, 38, 39, 37, 42, 40, 41, 45, 43, 44, 47, 48, 46, 50, 51, 49, 54, 52, 53, 57, 55, 56, 60, 58, 59, 63, 61, 62, 66, 64, 65, 69, 67, 68, 72, 70, 71, 74, 75, 73, 77, 78, 76, 80, 81, 79, 84, 82, 83, 87, 85, 86, 89, 90, 88, 93, 91, 92, 95, 96, 94, 99, 97, 98, 102, 100, 101, 104, 105, 103, 108, 106, 107</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping its final value returns `(False, "wrong length: expected 108 integers, got 107")`.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted instances verified; all 8 expanded gadget truth-table cases agreed with exact-one |
| G2 | empty, dropped, duplicate, out-of-range, and swapped answers all rejected with 5 distinct reasons |
| G3 | realistic prose/fenced response round-tripped all 108 values; garbage returned `None` |
| G4 | **0/200,000** hard-preset structure-aware guesses verified; sampled space size `59,494,005,495,808,124,888,239,538,103,054` |
| G5 | exact small count: 3 valid / 7,938 checksum-respecting candidates = `3.779289493575208e-4` |
| G6 | outlier, greedy, bounded random restart, and zero-free-variable Gaussian attacks each solved 0/8 hard instances; first three best residuals were 50, 8, 7, while Gaussian produced no Boolean candidate in 8/8 |
| G7 | doubled hard instance built at 240 blocks / 720 permutation values / 197 clauses and its plant verified |
| G8 | 140/140 symmetry/composition checks invariant and carried witnesses verified; 20/20 unrelated keys distinct |

The full machine-readable measurements are in `selftest_report.json`.

## Oracle hardening loop

All calls used fresh seeds and medium reasoning through the mandated four-vendor pool. An empty length-limited response counts as an unsolved attempt under the harness rules; the 900-second timeout is an error and was redrawn.

| preset | seed | model | result | why |
|---|---:|---|---|---|
| easy | 305405822 | GPT-5.6 Terra | solved | witness verified |
| easy | 587507083 | Grok 4.6 | solved | witness verified |
| easy | 1692569012 | Gemini 3.1 Pro Preview | solved | witness verified |
| medium | 1572863239 | Claude Sonnet 5 | failed | empty after 32k completion-token budget |
| medium | 484233452 | Grok 4.6 | solved | witness verified |
| medium | 1749277391 | GPT-5.6 Terra | failed | parsed answer violated clause 1 |
| hard | 1357735874 | Grok 4.6 | error | 900-second timeout; discarded and redrawn |
| hard | 909245643 | Grok 4.6 | failed | empty response after 27,914 completion tokens |
| hard | 1871844052 | Claude Sonnet 5 | failed | empty after 32k completion-token budget |
| hard | 877255110 | Gemini 3.1 Pro Preview | failed | parsed answer violated clause 1 |

The harness verdict is `hardened` at `hard`, after two escalations. Exact records and replies are in `llm_loop_transcript.jsonl`; seeds, pool, effort, and verdict are in `.meta.json`.

## Use

```python
import random
import gen_2601_19161 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer(model_reply)
ok, reason = g.verify(inst, candidate)
assert g.verify(inst, inst["answer"]) == (True, "ok")
guess = g.random_candidate(inst, random.Random(7))
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2601.19161 20 hard
```

## Caveats

- The hard theorem is worst-case; it does not prove this balanced planted distribution hard on average. A specialized SAT, exact-cover, or integer-programming solver may beat these presets. The oracle panel tests language models, not industrial solvers.
- The G4 prior is uniform over A/B choices satisfying the freely deducible degree checksum. It is much stronger than sampling from \((3n)!\), but it does not model learned clause correlations. `0/200,000` is the measured rate, not a rigorous probability upper bound.
- The panel did not test spectral/community detection, full CDCL or dancing-links search, unbounded random restarts, or Gaussian elimination followed by exhaustive nullspace search. It tested only a per-variable outlier score, deterministic greedy cover, bounded swap descent, and the simple all-free-variables-zero linear solution.
- Two of the three deciding hard-preset failures emitted no answer within the configured reasoning/output budget. Only Gemini emitted a parseable invalid witness. The harness accepts that as `hardened`, but the conclusion is budget-sensitive and should not be read as three independently wrong full answers.
- `canonical_key` uses stable color refinement plus incidence/co-occurrence profiles. It is invariant under the tested block and input relabellings and separated all tested seeds, but it is not a complete hypergraph-isomorphism canonizer and may over-collapse rare non-isomorphic instances.
- The compact problem states the block codebook directly instead of printing the paper’s quadratic block-enforcement prelude. This keeps questions usable while preserving the support-3 clause gadgets, but it is an explicit restriction beyond ordinary unrestricted 3-Local-PM-SAT.
