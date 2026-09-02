# Equiangular integer-vector subset generator

This module turns the search step in [Greaves, Syatriadi, and Yatsyna, *Equiangular lines in Euclidean spaces: dimensions 17 and 18*](https://arxiv.org/abs/2104.04330) into a scalable witness problem. An instance gives a graph, compactly encoded as upper-triangle hex, which implicitly defines equal-length integer vectors. The solver returns exactly `k` vertex indices. Those vectors are pairwise equiangular exactly when the indices form a `k`-clique, so verification is just `k(k-1)/2` exact bit lookups.

## Why this is a hard, trustworthy family

The Introduction defines equiangular lines through equal absolute inner products. Section 2 supplies the operative construction: form a graph on norm-10 integer vectors, join vectors with inner product `±2`, and find a clique. The module uses the same compatibility-graph search, with a self-contained implicit vector encoding for which `x_i·x_j=1` exactly on graph edges. Thus an arbitrary graph maps directly to an instance, and the worst-case search problem is CLIQUE. The generated regime has `k` growing roughly as `2 log2(n)`, above the ordinary random-clique threshold but below `sqrt(n)`; it avoids the polynomial-time fixed-`k` regime.

The paper itself does **not** prove average-case hardness. Its Theorem 1.1 is the extremal result `N(17)=48` and `N(18)≥57`, not a complexity theorem. Section 2's four printed 57-line matrices would be a finite lookup and were deliberately not used. Section 8 says the paper's candidate-realization computations become expensive and that some existence questions are notoriously difficult, but the formal worst-case justification here is the exact reduction to CLIQUE.

Generation is inverse and symmetric. A uniformly random answer block is sampled first, all remaining vertices are randomly partitioned into blocks of the same size, every within-block edge is present, and every between-block edge is an independent fair bit. At every named preset, all vertices therefore have the same distribution; the stored witness has no special labels, degrees, or vector format. `verify` never reads `inst["answer"]` and accepts any clique.

## Worked example (`n=18`, a readable diagnostic size below the presets)

```text
EQUIANGULAR INTEGER-VECTOR SUBSET

There are 18 labelled vertices, numbered 0 through 17.  Their undirected
simple graph is encoded below by one hexadecimal integer.  Ignore whitespace
between its lines.  Expand it to exactly 156 binary bits, preserving
leading zeroes, then discard the first 3 padding bit(s).
The remaining 153 bits give edges in this exact order:
    (0,1),(0,2),...,(0,17),(1,2),(1,3),...,(1,17),...,
    (16,17).
A bit is 1 exactly when that unordered pair is an edge.  There are no loops.

This graph also defines 18 integer vectors x_0,...,x_17 without listing
their many zero coordinates.  There is one coordinate p_(a,b) for every pair
0 <= a < b < 18.  At p_(a,b), vector x_a has value 1, vector x_b has value 1
if a and b are adjacent (otherwise 0), and every other vector has value 0.
For each i, add private coordinates used only by x_i, each with value 1, until
the squared length of x_i is exactly 17.  This is always possible because
the pair coordinates contribute at most 17 to that squared length.

Consequently, every x_i has squared length 17, and for distinct i,j:
    x_i dot x_j = 1  if i and j are adjacent,
    x_i dot x_j = 0  otherwise.
Thus a set of indices gives equiangular lines with common absolute normalized
inner product 1/17 exactly when every two of its vertices are adjacent.

Find exactly 7 DISTINCT indices whose vectors are pairwise equiangular; in
graph terms, find a clique of size 7.  The order of the submitted indices
does not matter.  Repeated indices are forbidden.  Bounds are inclusive:
every index must lie from 0 through 17.

HEX-ENCODED UPPER TRIANGLE (39 hex digits)
0f2f13f8e6fee3796f35f9f971b5ed2febbb7e9

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 7 integer indices separated by commas.
Example of the required format: <answer>[3, 17, 42]</answer>
The example illustrates syntax only and is not an answer to this instance.
Output nothing else inside the tags.
```

For this complete small instance, `<answer>[1, 4, 6, 8, 9, 14, 15]</answer>` parses to the planted witness and `verify` returns `(True, "ok")`. Dropping the final index returns `(False, "wrong number of indices: expected 7, got 6")`.

## Difficulty presets

| preset | `n` | `k` | forced hidden cliques | structure-aware search space | status |
|---|---:|---:|---:|---:|---|
| easy | 720 | 18 | 40 | 340,878,354,033,029,714,100,530,249,783,249,440 | **shipping; oracle held** |
| medium | 950 | 19 | 50 | 2,588,024,826,210,482,171,871,615,235,088,118,594,300 | not needed by harness |
| hard | 1340 | 20 | 67 | 124,191,361,012,273,880,526,926,032,014,753,098,438,320,935 | not needed by harness |

An earlier asymmetric `n=196,k=12` prototype was rejected by G6: deterministic greedy and randomized restart each solved 1/8 seeds. A symmetric `n=392,k=14` prototype also let 96 randomized restarts solve 2/8 seeds. Those settings are not shipped.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 9/9 (3 presets × 3 seeds) |
| G2 corruption | 5/5 rejected through 5 distinct reasons |
| G3 round-trip | realistic fenced/prose response parsed; 4/4 garbage cases rejected |
| G4 guess resistance | 0/200,000 uniform unordered in-range distinct 18-subsets; measured `0 < 1e-6` |
| G5 sparse | exact small probe: 18 valid / 31,824 candidates = `5.6561e-4` |
| G6 adversaries | triangle/degree outlier 0/8; common-neighbor greedy 0/8; 96 randomized greedy restarts 0/8 |
| G7 scaling | `n=720,k=18` doubled to `n=1440,k=20`; plant verified and space increased |
| G8 canonical key | 80/80 relabellings invariant and carried witnesses valid; 20/20 unrelated keys distinct |

## Oracle loop

The official harness held the first preset, so no escalation was used.

| preset | model | seed | solved | evidence |
|---|---|---:|---|---|
| easy | Gemini 3.1 Pro Preview | 170138751 | no | parsed 18-set; vertices 18 and 55 were not adjacent |
| easy | GPT-5.6 Terra | 1083275531 | no | parsed 18-set; vertices 394 and 430 were not adjacent |
| easy | Claude Sonnet 5 | 729335132 | no | exhausted the 32k completion budget and emitted no answer |

## Use

```python
import random
import gen_2104_04330 as gen

inst = gen.make_instance(**gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY], seed=123)
question = gen.render(inst)
answer = gen.parse_answer("<answer>[...]</answer>")
ok, reason = gen.verify(inst, answer)
candidate = gen.random_candidate(inst, random.Random(99))
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 2104.04330 20 easy
```

## Caveats

- CLIQUE gives worst-case hardness, not a proof for this planted clique-cover distribution. Forty valid planted blocks make the shipping instances easier than a unique-clique instance in principle.
- G4 measures blind guessing under the correct prior—uniform unordered size-18 subsets with all shape constraints already enforced. It says nothing about branch-and-bound, SAT/ILP encodings, spectral community recovery, GPU search, or future algorithms.
- The tested attacks are degree/triangle outliers, deterministic common-neighbor greedy, and 96 randomized greedy restarts. Exact maximum-clique solvers and spectral attacks were not run locally; the multi-vendor LLM panel is additional empirical evidence, not a complexity proof. One of its three failures was completion-budget exhaustion, explicitly recorded above.
- Named presets have `n` divisible by `k`, making every vertex distribution identical. Arbitrary custom `n` may leave one shorter final block; use named presets when statistical symmetry matters.
- Exact graph canonization is as hard as graph isomorphism in general. `canonical_key` is exact when canonical 1-WL refinement individualizes all vertices (as it did in the tested random instances); its invariant fallback can merge non-isomorphic graphs, though it cannot split relabellings of the same graph.
