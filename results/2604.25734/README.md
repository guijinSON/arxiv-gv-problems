# Radius-one Ulam k-Center generator

| axis | declaration |
|---|---|
| native domain | `combinatorics` |
| computational core | `exact_cover` |
| intended intuition | exact-cover complement as a vertex cover |

This is a **discretised analogue** of the paper's Ulam-center problem. Section
3.1 licenses the triangle-free Vertex Cover-to-Ulam leg; the preceding exact
cover-to-conflict-graph leg is this generator's elementary surrogate, not a
construction stated in the paper. It discards the explicit permutation strings
and unrestricted search over center permutations: the solver instead receives
an indexed 3-uniform set system and returns an exact cover whose complement
expands to the prescribed vertex-center witness. The compact encoding and
verifier retain the reduction's exact combinatorial semantics, but the solver
does not work directly with Ulam distance.

This module turns **Clustering Permutations under the Ulam Metric: A Parameterized Complexity Study** ([Bai et al., arXiv:2604.25734](https://arxiv.org/abs/2604.25734)) into a search problem with exact grading. The solver receives triples defining an exact-cover conflict graph and a lossless recipe for the paper's permutation instance. It returns an exact 3-set cover; this compactly encodes a vertex cover of a triangle-free 2-subdivision and hence a set of radius-one Ulam centers. Verification checks the exact cover, reconstructs the subdivided cover, and checks every path edge using integer/set operations.

## Why this is hard—and the easy regime avoided

Section 3.1 and Theorem 1 prove Ulam k-Center NP-hard for every fixed radius `d >= 1`, using triangle-free Vertex Cover. This generator uses exactly `d=1`. Its conflict-graph complement is the selected exact cover; 2-subdivision then puts it exactly in the theorem's triangle-free construction. Exact Cover by 3-Sets supplies the NP-hard search core.

Theorem 2 is the important warning: Ulam k-Center is FPT in `k+d`, with running time exponential in that parameter. Accordingly, `k` is not held small here—it grows with the conflict graph. The example preset is intentionally easy and is not shipped. Individual planted triples and decoys are both uniform 3-subsets; only the planted triples' joint partition property differs.

## Worked example (`example`, seed 0)

The complete rendered instance is:

```text
Radius-one Ulam k-Center (compact exact encoding)

The Ulam distance between two permutations of the same alphabet is their
length minus the length of a longest common subsequence. Equivalently, it is
the fewest operations that remove one symbol and reinsert it elsewhere.

First define a simple conflict graph H. Its 20 vertices
are the indexed triples below, over ground elements 0,...,11.
Two vertices are adjacent exactly when their triples share at least one ground
element. Triple order and the order of elements inside a triple have no
mathematical significance.

0: 3 4 7
1: 3 9 10
2: 1 3 5
3: 0 6 11
4: 1 7 8
5: 2 3 8
6: 2 5 10
7: 1 2 9
8: 1 8 9
9: 1 7 10
10: 3 9 11
11: 0 4 8
12: 1 2 4
13: 7 8 10
14: 5 7 9
15: 2 4 8
16: 5 6 11
17: 4 8 9
18: 1 5 11
19: 0 1 8

This losslessly specifies the Ulam instance:

1. Give the 118 edges of H their lexicographic order
   by endpoint indices. Replace edge i={u,v} by u--a_i--b_i--v. The resulting
   graph G is triangle-free, with 256 vertices and
   354 edges.
2. Give every vertex w of G private symbols (w,0),(w,1). The base permutation
   lists these pairs consecutively in vertex order, (w,0) before (w,1).
3. For each edge xy of G, one input permutation reverses exactly the two pairs
   for x and y. A vertex-center for w reverses exactly w's pair.

Provide a compact encoding of k=134 distinct vertex-centers with
inclusive Ulam radius 1. Select exactly 4 displayed triples that are pairwise
disjoint and cover every ground element exactly once. Their complement is a
vertex cover X of H. The checker expands X by including its vertex-centers and,
for every oriented conflict edge u<v, including b_i if u is in X and a_i
otherwise. A valid selection therefore encodes exactly 134 centers
and covers every edge-input of G at Ulam distance at most 1.

Output the selected triple indices as one JSON array of exactly 4 distinct
integers in strictly increasing order. Indices are 0-based and lie in
0,...,19. The set, not order, is mathematical; sorting
is the required unique wire encoding. Repeats are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>[0, 1, 2]</answer>
The real answer must contain exactly 4 indices. Output nothing else inside
the tags.
```

The actual witness is `<answer>[0, 3, 6, 8]</answer>`. `verify(inst, [0,3,6,8])` returns `(True, "ok")`; dropping one index returns `(False, "wrong number of triples: expected 4, got 3")`.

## Difficulty presets

| preset | witness triples `n` | public triples | status |
|---|---:|---:|---|
| `example` | 4 | 20 | demonstration only; all 3 oracle models solved it |
| `standard` | 80 | 480 | **shipping**; held against all 3 deciding vendors |
| `hard` | 104 | 624 | local gates pass; oracle escalation not needed |
| `extreme` | 136 | 816 | local gates pass; oracle escalation not needed |

## Mandatory gates

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified (4 presets × 3 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 80 indices recovered through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; candidates are uniform sorted 80-subsets of the 480 triples |
| G5 | shipping `standard`, `n=80`, seed 314159: enumeration returned `None`; sampled density 0/200,000 (`0.0`) in the declared language; exact Algorithm X did not solve and reached its 100,000-node cap in 2.840221 wall-clock seconds. Supplemental `n=4` exact counts: 1, 2, 1 out of 4,845 |
| G6 | 0/8 successes for each of 6 attacks; Algorithm X hit 100,000 nodes on all 8 |
| G7 | planted witness verifies at doubled `n=160`; candidate space grows from about `4.10e92` to `2.44e186` |
| G8 | 20/20 composed relabelings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |

The six G6 attacks are conflict-degree outlier selection, deterministic Algorithm-X greedy, 256 randomized restarts, normalized conflict-graph spectral recovery, maximal-matching cover relaxation, and exact Algorithm X capped at 100,000 nodes.

## Oracle hardening loop

The harness used master seed `14495473202701361289`, medium effort, and fresh vendors. The Grok timeout is an error and did not count; Terra was redrawn to preserve three deciding vendors.

| preset | model | seed | solved? | result |
|---|---|---:|---|---|
| example | Claude Sonnet 5 | 98484374 | yes | valid exact cover |
| example | GPT-5.6 Terra | 2046146755 | yes | valid exact cover |
| example | Gemini 3.1 Pro Preview | 692406171 | yes | valid exact cover |
| standard | Claude Sonnet 5 | 275857106 | no | exhausted 32k completion budget; emitted no answer |
| standard | Gemini 3.1 Pro Preview | 757386680 | no | parsed 80 indices; ground element 124 repeated |
| standard | Grok 4.6 | 1005570988 | error | 900-second deadline; excluded and redrawn |
| standard | GPT-5.6 Terra | 826352813 | no | parsed 80 indices; unsorted, and sorting still leaves ground element 180 repeated |

Verdict: `hardened`, shipping preset `standard`, after one escalation from the deliberately readable example.

## Use

```python
import random
import gen_2604_25734 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer("<answer>[...]</answer>")
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit fresh instances with:

```bash
bash scripts/emit.sh 2604.25734 20 standard
```

## Caveats

- The NP-hardness theorem is worst-case; it does not prove this planted distribution hard. The local attacks and multi-vendor loop are empirical evidence, not a reduction showing average-case hardness.
- `0/200,000` is the observed rate under a uniform exact-size subset prior. It neither proves the true probability is zero nor models guided search; its ordinary 95% zero-hit upper bound is roughly `1.5e-5`.
- One deciding oracle failure was length-limited rather than a wrong witness. The other two emitted parseable but invalid candidates. This is weaker evidence than three explicit incorrect witnesses and is recorded rather than hidden.
- On shipping seed 314159, exact Algorithm X did not solve before its 100,000-node cap and consumed 2.840221 wall-clock seconds. This is a measured capped cost, not evidence that unrestricted search takes a long time. The panel did not run an unrestricted DLX/CP-SAT/commercial MILP solver, an SDP, or long stochastic local search; more compute can solve finite instances.
- The renderer is a compact mathematical encoding of the paper's permutations, not an explicit listing of their millions of symbols. The checker independently expands the subdivision cover logic, but relies on the paper's elementary pair-scheme identity that a covered edge-input is distance one from its endpoint-center.
- `canonical_key` is a strong incidence-graph Weisfeiler–Leman invariant, not a complete hypergraph canon. Nonisomorphic exact-cover instances can theoretically collide.
