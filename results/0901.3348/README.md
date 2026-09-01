# Verified planted-clique witness generator

This directory turns Brendan Ames and Stephen Vavasis, [“Nuclear norm minimization for the planted clique and biclique problems” (arXiv:0901.3348)](https://arxiv.org/abs/0901.3348), into one self-contained search family. An instance is a labelled undirected simple graph. The solver returns exactly `k` distinct vertices whose every pair is an edge. The answer is a witness, not a claim that the clique is maximum: `verify` checks its range, cardinality, distinctness, and all `k(k-1)/2` edges exactly, and accepts any valid clique.

## Why this is the paper’s family, and why it may be hard

Section 3 fixes the exact clique definition. Section 3.3, conditions Γ₁–Γ₂, fixes the generator used here: choose the planted vertex set first, force every internal edge, then include every other possible edge independently with probability `p`. This module uses `p=1/2` and uniformly random planted labels, so plant and decoy labels have the same prior.

The paper mostly tells us what **not** to ship. Theorem 3.3 gives polynomial-time nuclear-norm recovery with high probability for `k >= α(p) sqrt(N)`. Section 3.2 also gives a recoverable adversarial regime with only `O(k²)` diversionary edges and bounded plant-to-outsider degree. The active family instead has a dense `G(N,1/2)` background and grows `k` near `2 log2(N)-2`, asymptotically below every constant multiple of `sqrt(N)`. Maximum clique is NP-hard (Sections 1 and 3), while efficient recovery in this sub-square-root planted regime is a standard conjecture rather than a theorem of this paper; the [Strongish Planted Clique Hypothesis paper](https://arxiv.org/abs/2011.05555) describes `N^O(log N)` as the state of the art under its stronger hypothesis, and [sum-of-squares lower bounds](https://arxiv.org/abs/1604.03084) give evidence against a broad algorithmic family. Thus H is evidence-backed but conditional, not proved average-case hardness.

## Worked demo (`seed=7`)

```text
Find a clique of the required size in the undirected simple graph below.

Definitions and conventions:
- The vertices are the integer labels 1 through 32, inclusive.
- A clique is a set of distinct vertices for which every pair of distinct vertices is joined by an edge.
- Return exactly 8 distinct vertex labels. Order does not change the set, and the checker accepts any order. Repeats are forbidden.
- The graph is given by its full adjacency matrix. In row i, character j is 1 exactly when vertices i and j are adjacent, and is 0 otherwise. Rows and character positions are both 1-indexed. The diagonal is 0 and the matrix is symmetric.

vertex_count: 32
required_clique_size: 8
adjacency_matrix:
1: 01011110011101111011110011011101
2: 10111110000010011111100000110111
3: 01001100110010001110101100000111
4: 11000011011011000110001000001111
5: 11100111101010110100111000001011
6: 11101001111011011111011101000011
7: 11011000000011100011101101001010
8: 00011100111011001100010000111101
9: 00101101001010011010100100011111
10: 10110101001010011111101110101000
11: 10011101110110001110111110110011
12: 10000000001011011011001000101010
13: 01111111111101000111101101101011
14: 10010111000110101100111000010010
15: 10001010000001010001000111110011
16: 11001100110100100100010010110101
17: 11100101111101000101110101000111
18: 01111101011011011011101110010011
19: 11110110111110000101001011110101
20: 11000110010110101110000011011001
21: 11101010111011001100011100111011
22: 10001101001001011000100101011001
23: 00111110011111000110100000011010
24: 00100110111010101100110011001001
25: 10000000011000110111000101110110
26: 10000110000010101011010110101001
27: 01000001011110110010100011011000
28: 11000001101001110111111010101011
29: 10011011110110000001111101110011
30: 11110001100000011010000010000011
31: 01111110101111101100101010011101
32: 11111101101010111111110101011110

Give your final answer inside <answer></answer> tags, as exactly 8 comma-separated integer labels.
Example format only: <answer>1, 2, 3, 4, 5, 6, 7, 8</answer>
Output nothing else inside the tags.
```

Answer: `<answer>2, 3, 5, 13, 18, 21, 31, 32</answer>`.

```python
verify(inst, [2, 3, 5, 13, 18, 21, 31, 32])
# (True, "ok")
verify(inst, [1, 3, 5, 13, 18, 21, 31, 32])
# (False, "missing edge between vertices 1 and 3")
```

## Difficulty and validation

| Level | `N` | `k` | Status |
|---|---:|---:|---|
| `demo` | 32 | 8 | Active readable preset; two of three final-run oracles solved it |
| rejected candidate | 128 | 10 | Removed: G6 deterministic greedy solved 6/12 seeds and randomized restarts solved 11/12, despite a preliminary oracle panel missing it |
| `hard` | 512 | 16 | **Shipping**; all local gates pass and final oracle panel solved 0/3 |

| Gate | Measured result |
|---|---|
| G1 planted verifies | 12/12 instances (2 presets × 6 seeds) |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | Prose + fenced tagged answer parsed and verified |
| G4 structure-aware guess | 0/250,000 uniform 16-subsets; candidate space `841141456821158064519401490400` |
| G5 exact sparse count | 2/77,520 at `N=20,k=7` = `2.5799793601651186e-5` |
| G6 attacks | outlier 0/12; deterministic greedy 0/12; 256-restart randomized greedy 0/12 |
| G7 scaling | `N=1024,k=18` builds and verifies; candidate space increases to `205966057488760845115333492006729616896` |
| G8 canonical key | 80/80 invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct; all 20 used exact discrete-refinement branch |

Final `scripts/harden.py` run (master seed `14105083934932727875`, effort `medium`):

| Preset | Model | Seed | Solved? | Evidence |
|---|---|---:|---|---|
| demo | x-ai/grok-4.6 | 1653249197 | yes | parsed witness verified `ok` |
| demo | openai/gpt-5.6-terra | 1648458909 | yes | parsed witness verified `ok` |
| demo | anthropic/claude-sonnet-5 | 991372269 | no | empty response after exhausting 32,000 completion/reasoning tokens |
| hard | anthropic/claude-sonnet-5 | 1064671041 | no | empty response after exhausting 32,000 completion/reasoning tokens |
| hard | openai/gpt-5.6-terra | 673074783 | no | parsed 16-set missed edge `(170,289)` |
| hard | x-ai/grok-4.6 | 745160560 | no | parsed 16-set missed edge `(1,87)` |

## Use

```python
import random
import gen_0901_3348 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
question = gen.render(inst)
candidate = gen.parse_answer("work... <answer>1, 2, 3</answer>")
ok, reason = gen.verify(inst, candidate)
guess = gen.random_candidate(inst, random.Random(99))
```

From the repository root, emit 20 fresh hard instances with:

```bash
bash scripts/emit.sh 0901.3348 20 hard
```

Run the local report again with `python3 results/0901.3348/gen_0901_3348.py`.

## Caveats

- Theorem 3.3’s constant `α(p)` is unspecified. Although the family’s scaling is `o(sqrt(N))`, the finite shipping point `16/sqrt(512) ≈ 0.707` is not formally proved outside the theorem’s sufficient easy region. The oracle and attack results are empirical, not a hardness proof.
- G4 samples uniformly from all correctly shaped `k`-subsets, with range, distinctness, arity, and order normalization built in. Zero hits does not estimate the success probability of a graph-aware heuristic, nor statistically certify a sub-`1e-6` upper confidence bound.
- The panel did not test optimized exact maximum-clique/branch-and-bound code, SAT/MILP encodings, GPU search, or an implementation of the paper’s nuclear-norm or spectral methods. Dense 512-vertex input also makes the rendered prompt about 266 KB, so representation burden may contribute to LLM failures.
- One of the three hard oracle failures was an empty length-limited response; only two hard vendors emitted explicit, parseable, invalid witnesses. The official harness deliberately counts the empty response as unsolved, and the transcript preserves that distinction.
- Other `k`-cliques may exist and are intentionally accepted; neither the generator nor checker certifies uniqueness or maximum size.
- Exact graph canonicalization is only used when deterministic color refinement makes every vertex color unique (20/20 G8 instances). For a rare non-discrete graph, `canonical_key` falls back to a strong relabelling-invariant degree/color/triangle/common-neighbor signature that may over-collapse nonisomorphic graphs; it never keys on seed or rendered text.
