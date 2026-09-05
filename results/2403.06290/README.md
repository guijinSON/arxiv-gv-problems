# Path-contraction endpoint certificates (arXiv:2403.06290)

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple: sorted endpoint pairs |
| Intended intuition | symmetry: exceptions to a coordinate half-swap involution |
| Domain essentiality | licensed reduction |
| Reduction | paper-central, Section 5.2, Theorem 4 |

This is representational coverage through the paper’s own central reduction, not native coverage of arbitrary Path Contraction instances. The solver receives both the Boolean-vector incidence table and the chordal split graph it defines; the search core is the Orthogonal Vectors instance used in Theorem 4.

## Problem and trust model

[Krithika, Kutty Malu, and Tale, *Revisiting Path Contraction and Cycle Contraction*](https://arxiv.org/abs/2403.06290) define an `H`-witness structure in Section 2 as a partition into nonempty connected bags whose bag-adjacency graph is exactly `H`. The forward proof of Theorem 4 constructs a split graph with independent sets `X,Y` and clique `Z={z_X,z_1,...,z_d,z_Y}`. Every orthogonal pair `x_i,y_j` yields four explicit bags whose quotient is `P4`.

An instance asks for a fixed number of endpoint pairs. For each pair, `verify` expands the paper’s four bags, constructs the graph, checks the partition, checks connectivity in every bag, compares all six inter-bag adjacencies with `P4`, and checks the contraction budget. It never reads `inst["answer"]`.

Generation is inverse. Endpoint vectors are sampled first; each designated `Y` endpoint is sampled inside the complement of its `X` endpoint. Decoys are then sampled from the same constant-weight Hamming layer, conditioned to create no additional orthogonal pair. The certificate is carried through the final row shuffles; neither the exhaustive scan nor the compact solver is run to discover it.

## Why Track B

This cannot honestly be Track A. The paper gives an `O*(2^k)` general algorithm (Theorem 1), cites an `O(nm)` chordal-graph algorithm before Theorem 4, and the displayed reduction instance is solvable by scanning all `n^2` cross-pairs in `O(n^2 d)`. At the shipping preset, the implemented exact scan succeeds on 8/8 instances, performs 1,216,800 Boolean coordinate products per instance, and averaged 0.077 seconds in the recorded self-test.

The compact route notices that swapping the two 36-coordinate halves is an involution. Every decoy row has its swapped mate on the same side; only the four endpoint rows do not. Two membership passes isolate those exceptions, after which only a 4-by-4 cross-product remains. The counted route is `2n+t^2=276` exact word operations and averaged about `4.9e-5` seconds in the implementation. Without that symmetry, a no-tool solver faces 16,900 shuffled cross-pairs and 72 coordinates per comparison.

The generator avoids the paper’s easy regimes: target `P3` is polynomial-time solvable (Introduction), planar Path Contraction is polynomial-time solvable (Theorem 3), and small `k` is handled by Theorem 1’s FPT algorithm. It uses the fixed-target `P4` construction of Theorem 4 with `k=|V(G)|-4`.

## Worked demo

For `make_instance(n=6, d=16, weight=5, target_count=2, seed=3)`, `render` returns:

```text
Find endpoint certificates for path contractions in a chordal split graph.

The graph G is defined as follows.  X={x0,...,x5} and
Y={y0,...,y5} are independent sets.  Z={zX,z0,...,z15,zY} is a
clique.  Each displayed row is a fixed-width hexadecimal integer.  Bit c means
the coefficient of 2^c (the rightmost hexadecimal digit contains bits 0..3).
Vertex xi is adjacent to zX and to coordinate vertex zc exactly when bit c of
its row is 1.  Vertex yj is adjacent to zY and to zc exactly when bit c of its
row is 1.  There are no other edges.  Thus G is a connected chordal split graph.

For a proposed pair [i,j], define Z1 as the neighbors of xi in Z, Z2 as the
neighbors of yj in Z, and Z3=Z\(Z1 union Z2).  The pair is valid exactly when
the following four nonempty bags form a path-witness structure in the listed
order:
  W1={xi}
  W2=Z1 union Z3 union (X\{xi})
  W3=Z2 union (Y\{yj})
  W4={yj}
A path-witness structure means that every bag induces a connected subgraph,
the bags partition all vertices, and two distinct bags have at least one edge
between them exactly when they are consecutive in the displayed order.  Such a
structure contracts G to the four-vertex path P4 using exactly k=26
edge contractions.

Return exactly 2 distinct valid pairs.  Indices are 0-based and lie in
0..5.  Order within a pair is always [X-index,Y-index].  Sort the list of
pairs lexicographically; repeats are forbidden.

X incidence masks:
  x0: 0xa602
  x1: 0x03a4
  x2: 0x6091
  x3: 0x8889
  x4: 0x9160
  x5: 0x8988

Y incidence masks:
  y0: 0x3a40
  y1: 0xc026
  y2: 0x26c0
  y3: 0x403a
  y4: 0x01e1
  y5: 0xa00b

Give your final answer inside <answer></answer> tags as a JSON list of 2
integer pairs sorted lexicographically.
Example of the required syntax only: <answer>[[0,0],[1,1]]</answer>
Output nothing else inside the tags.
```

The answer is `[[0,4],[1,5]]`.

```python
>>> verify(inst, [[0, 4], [1, 5]])
(True, "ok")
>>> verify(inst, [[0, 4]])
(False, "expected exactly 2 pairs")
```

A person can solve the demo on paper by doing at most 36 short hexadecimal AND checks.

## Difficulty presets

The live loop solved every former lower rung. Following the hardening contract, the ladder was slid upward and the first held escalation became the named `hard` preset.

| Preset | `n` per side | `d` | Weight | Required pairs | Candidate space | Result |
|---|---:|---:|---:|---:|---:|---|
| demo | 6 | 16 | 5 | 2 | 630 | hand-solvable; exact enumeration |
| easy | 100 | 64 | 20 | 4 | 416,416,712,497,500 | one live oracle solved this parameter set |
| medium | 130 | 64 | 20 | 4 | 3,397,671,432,817,025 | one live oracle solved this parameter set |
| **hard** | **130** | **72** | **20** | **4** | **3,397,671,432,817,025** | **ships; 0/3 bare solves** |

`escalate` increases `d` by 8 while holding `n`, the witness count, and the answer length fixed.

## Gate results

| Gate | Result | Recorded measurement |
|---|---|---|
| G1 | pass | 16/16 preset/seed cases; planted, compact, and exhaustive routes agree |
| G2 | pass | 6 corruptions rejected with 6 distinct reasons |
| G3 | pass | tagged JSON recovered from prose/fences; JSON-native round trip |
| G4 | pass | 0/200,000 structure-aware guesses; exact probability about `2.94e-16` |
| G5 | pass | shipping density above; demo exact count 1/630; reference scan 1,216,800 products and 0.077 s |
| G6 | pass | four failing attacks at 0/8; reference and compact algorithms both solve 8/8 as expected |
| G7 | pass | doubled `n=260,d=80` instance builds and verifies |
| G8 | pass | 80 invariant checks, 80 carried-witness checks, 20/20 unrelated keys distinct |
| G9(c) | pass | 40 chars, 10 estimated tokens, 8 atoms; 276 intended operations; worst-case bound 12 tokens |

## Bare oracle loop

The transcript was written by `scripts/harden.py` with master seed `10707896026807021279`. “Failed” includes the exact checker reason; API errors were not counted. The labels in this table are the pre-slide harness labels, so the parameter columns are authoritative.

| Round / label | `n,d` | Model | Seed | Result | Checker reason |
|---|---:|---|---:|---|---|
| 0 / easy | 70,64 | Terra | 1716071602 | failed | intersecting coordinate neighborhoods |
| 0 / easy | 70,64 | Gemini | 1422920680 | solved | ok |
| 0 / easy | 70,64 | Gemini | 300479756 | solved | ok |
| 1 / medium | 100,64 | Terra | 452814099 | failed | intersecting coordinate neighborhoods |
| 1 / medium | 100,64 | Gemini | 653430129 | solved | ok |
| 1 / medium | 100,64 | Terra | 110808842 | failed | intersecting coordinate neighborhoods |
| 2 / hard | 130,64 | Gemini | 533160537 | failed | empty length-limited response |
| 2 / hard | 130,64 | Terra | 1207259990 | failed | duplicate pair |
| 2 / hard | 130,64 | Gemini | 1767796417 | solved | ok |
| 3 / escalated | 130,72 | Gemini | 323464538 | failed | empty length-limited response |
| 3 / escalated | 130,72 | Terra | 1832161856 | failed | intersecting coordinate neighborhoods |
| 3 / escalated | 130,72 | Gemini | 765152454 | failed | no tagged answer after a long manual scan |

The harness verdict is `hardened` at `n=130,d=72`.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence above |
| structural hint | 1/3 | recorded verdict `too_easy`; diagnostic only |
| placebo hint | 2/3 | adding a non-structural sentence also changed outcomes |

Hinted minus placebo is `1/3 - 2/3 = -1/3`. This small three-call sample gives no evidence that naming the half-swap invariant helped; the placebo arm did better. It therefore does not support a causal claim about the declared symmetry intuition. The size/effort cap still passes: the measured answer is 40 characters, 10 estimated tokens and 8 atoms (12 tokens worst-case), and the intended route is 276 operations.

## Use

```python
import json
import gen_2403_06290 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2403.06290 20 hard
```

## Caveats

- A script solves every instance quickly. That is the Track B claim: the benchmark measures noticing and executing a compressed route without tools, not computational intractability.
- The 0/200,000 estimate samples uniformly from sorted four-subsets of the `n^2` typed `X`–`Y` pairs. It does not model a solver conditioned on the half-swap insight.
- The failing panel covers equal-degree outliers, a limited greedy minimum-intersection heuristic, 256 random restarts, and same/reverse row alignment. The paper-cited `O(nm)` chordal algorithm, an ILP encoding, and external SAT/SMT solvers were not implemented; the exact `O(n^2 d)` source-problem scan was run.
- Requiring four endpoint pairs composes four witnesses on one graph; the paper’s literal decision problem asks whether one exists.
- Decoys have the same fixed-weight one-row language as endpoints, but the two-cycle correlation is deliberately visible at the set level. Recognizing it makes the family easy.
- `canonical_key` uses 1-WL plus degree and common-neighbor multisets. It passed the tested row, coordinate, side, and composed relabellings, but it is not a complete graph-isomorphism canonical form.
- Two of the three bare shipping failures involved answer-budget/manual-scan exhaustion rather than a compact but wrong endpoint list. The transcript keeps this visible; the result should not be read as three identical reasoning failures.
- The module is standard-library-only; `gvlib` is unnecessary for this finite bit-set family.
