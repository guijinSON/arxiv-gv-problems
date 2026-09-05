# Verified nested-module generator for arXiv:2212.14814

> Status: every local G1--G9(c) gate passes. The script-owned bare oracle loop
> held `easy` on 3/3 attempts, so the shipping verdict is **`hardened` with zero
> escalations**.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `graph` |
| Certificate form | `integer_tuple` (the proof's three vertex pairs) |
| Native objects | simple graph; cotree cuts; nested `t`-module; cograph edit set |
| Intended intuition | decomposition through nested neighborhood contrasts |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and trust model

The source is Crespelle, Pellerin, and Thomassé, [*A quasi-quadratic vertex
Kernel for Cograph edge editing*](https://arxiv.org/abs/2212.14814). Section 2
defines a cograph as a graph with no induced four-vertex path and describes its
cotree. Section 4 defines `t`-modules and nested `t`-modules; Reduction Rule 4
edits the `A--I` edges and `A--K` nonedges, and Lemma 3 proves the rule safe.
Theorem 8 in Section 6 constructs the five parts from three cotree cuts, each
represented by a pair of vertices.

An instance hands the solver the graph itself as an exact adjacency matrix. The
solver returns the three anchor pairs. Their neighborhood symmetric differences
must expose nested sets `A ⊂ A∪B ⊂ A∪B∪C`. The verifier reconstructs all five
parts, computes each module's exact cut-edit distance, checks all four `3t+1`
buffer conditions, derives Rule 4's edits, and independently recognizes that the
edited graph is a cograph. It never reads the planted answer.

Generation is inverse, not search. The module assembles a cograph from the
same cotree layers used in Theorem 8, chooses clean anchor pools, and only then
toggles `t` pairs crossing all three cuts. Reversing those known toggles restores
the original cograph. Vertex permutation and optional complementation hide the
layout while carrying the anchors.

## Why Track B

This family is explicitly not a Track-A hardness claim. Theorem 8 says the
nested module is detectable in polynomial time: guess
`x,x',y,y',z,z'`, reconstruct the cuts, and test the definition. Its proof gives
`O(n^6)` for this six-anchor enumeration. The implemented reference memoizes all
pair contrasts; on the declared distribution its complexity is
`O(n^3 + r^3 n)`, where `r` is the number of repeated contrast signatures. It
solved 8/8 shipping instances, averaging **1,077,875.5 counted operations and
0.0141 s**, with maxima of 1,844,076 operations and 0.0182 s.

The compact route is to notice three complementary row pairs and read their
strictly nested contrast cuts. Once those pairs are spotted, the shipping bound
is 168 exact adjacency/set operations and the answer has only six integers.
The benchmark therefore tests recognition of the cotree decomposition, not the
ability to execute a million-operation graph scan without tools. The bare oracle
result confirms that no-tool gap. In the small G9 diagnostic,
both the structural and placebo arms solved one of three independent instances,
so that experiment does not isolate an effect from naming the invariant.

The paper identifies the easy boundary plainly. Theorem 8 supplies the
polynomial certificate-producing method; Corollary 10 supplies an
`O(k^2 log k)` vertex kernel for Cograph Editing; and its proof treats the fixed
range `k < 559` by brute force. Shipping uses `k=t=2`, so claiming that the
paper's parameterized worst-case result made this generated distribution hard
would be false.

## Worked demo

For `make_instance(seed=0, n=22, t=1, scramble=False)`, the complete rendered
instance is:

```text
Find a six-vertex certificate for a nested t-module cograph edit.

The input is a simple undirected graph G on the 0-based vertices 0,...,21.
Its adjacency matrix is displayed below: character j of row i is 1 exactly when
vertices i and j are adjacent.  The diagonal is 0 and the matrix is symmetric.

For a vertex v, N(v) is its set of neighbors.  For two distinct vertices u,v,
define their contrast cut

  D(u,v) = {u,v} union (N(u) symmetric-difference N(v)).

Return three anchor pairs [[x,x'],[y,y'],[z,z']].  They define

  A = D(x,x'),
  A union B = D(y,y'),
  A union B union C = D(z,z').

These three sets must be strictly nested.  The remaining vertices are split as
K = neighbors of x outside A union B union C, and I = the other outside
vertices.  Thus A,B,C,K,I must be five nonempty, pairwise-disjoint sets covering
all vertices.

A set X is a t-module when at most t adjacencies across the cut (X,V(G)-X)
must be toggled to make every vertex of X have the same neighbors outside X.
Equivalently, for each outside vertex w let d_w be its number of neighbors in X;
X is a t-module exactly when sum_w min(d_w, |X|-d_w) <= t.

Here t=1 and k=1.  Your anchors are valid only if all of the following hold:

1. A, A union B, and A union B union C are t-modules, and |A| > k+t.
2. At least 3t+1 vertices b in B are adjacent to every vertex of A and K and
   to no vertex of I.
3. At least 3t+1 other vertices b in B are adjacent to every vertex of K and
   to no vertex of A or I.
4. At least 3t+1 vertices c in C are adjacent to every vertex of A union B and
   K and to no vertex of I.
5. At least 3t+1 other vertices c in C are adjacent to every vertex of K and
   to no vertex of A union B or I.

The nested t-module rule toggles every existing A--I edge and every missing
A--K edge.  For this task those derived toggles must be nonempty, use at most k
pairs, and the resulting graph must be a cograph.  A cograph means a graph with
no induced path on four vertices (no four vertices whose induced subgraph is
exactly a three-edge path).

All six anchor indices must be distinct.  Within each pair write the smaller
index first.  The three pairs are ordered inner, middle, outer as above; pair
order is not interchangeable.  No repeated indices are allowed.

Adjacency matrix:
  0: 0011111100001111000011
  1: 0011111100001111000010
  2: 1100111100001111000010
  3: 1100111100001111000010
  4: 1111000011111111000010
  5: 1111000011111111000010
  6: 1111000111111111000010
  7: 1111001011111111000010
  8: 0000111100001111000010
  9: 0000111100001111000010
 10: 0000111100011111000010
 11: 0000111100101111000010
 12: 1111111111110000111110
 13: 1111111111110000111110
 14: 1111111111110001111110
 15: 1111111111110010111110
 16: 0000000000001111000010
 17: 0000000000001111000010
 18: 0000000000001111000110
 19: 0000000000001111001010
 20: 1111111111111111111100
 21: 1000000000000000000000

Give your final answer inside <answer></answer> tags as JSON in the exact form
[[x,x'],[y,y'],[z,z']], with three pairs and six 0-based integer indices.
Example: <answer>[[2,9],[4,17],[6,21]]</answer>
Output nothing else inside the tags.
```

The planted certificate is `<answer>[[1,3],[4,9],[13,17]]</answer>`.
`verify(inst, [[1,3],[4,9],[13,17]]) == (True, "ok")`; dropping the last
pair gives `(False, "expected exactly three anchor pairs")`. Because this demo
keeps the cotree layers in order, a person can solve it on paper by contrasting
the visibly related rows. The scrambled 52-row shipping version is deliberately
not a comfortable manual scan.

## Difficulty presets

| Preset | `n` | `t=k` | Six-anchor space | Status |
|---|---:|---:|---:|---|
| demo | 22 | 1 | 6,715,170 | ordered, hand-readable illustration |
| easy | 52 | 2 | 1,832,266,800 | **shipping; bare oracle held 3/3** |
| medium | 68 | 2 | 9,850,800,960 | unused fixed-witness escalation |
| hard | 84 | 2 | 36,583,338,960 | unused fixed-witness escalation |

No preset was rejected by a local gate. The oracle held the first evaluated
rung, so the higher rungs were not spent.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 16/16 preset/seed planted answers verify and JSON round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown |
| G4 | pass | 0/250,000 structured guesses in a 1,832,266,800-candidate language |
| G5 | pass | shipping density 0/250,000; reference mean 1.078M operations, 0.0141 s |
| G6 | pass | five attacks at 0/8; Track-B reference at 8/8 |
| G7 | pass | doubling to `n=104` verifies; answer remains six integers |
| G8 | pass | 20 permutations, 20 complements, 20 compositions preserve key/witness; 20/20 unrelated keys distinct |
| G9(c) | pass | 25 characters, 7 estimated tokens, 6 atoms, 168 intended operations |

## Oracle loop

The installed harness currently uses two vendors and draws three attempts. The
authoritative clean records are `llm_loop_transcript.jsonl` and `.meta.json`.

| Preset | Seed | Model | Result | Checker reason |
|---|---:|---|---|---|
| easy | 2018231071 | GPT-5.6 Terra | failed | first two contrast sets not nested |
| easy | 780761647 | Gemini 3.8 Flash | failed | no final tagged answer |
| easy | 1323802101 | Gemini 3.8 Flash | failed | empty length-limited response |

The script verdict is `hardened` at `easy`, with zero escalations. The second
reply ended mid-analysis without an answer, so its parse failure is not a G3
bug; the third response contained no text and is explicitly distinguished in
the transcript.

## G9 arms

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 1/3 | naming the nested-contrast invariant enabled one exact solution |
| placebo hint | 1/3 | one exact solution without structural information |

The hinted-minus-placebo difference is `0.0`. On this small sample, naming the
nested-contrast invariant bought no net success over a content-free sentence;
the diagnostic therefore does not establish that the claimed decomposition
intuition caused the successful solve. This is recorded as a limitation, not a
gate. The answer measures 25 characters, 7 estimated tokens, and 6 atomic
elements; the intended post-insight route is bounded at 168 operations.

## How to use

```python
import importlib.util

path = "results/2212.14814/gen_2212_14814.py"
spec = importlib.util.spec_from_file_location("gen_2212_14814", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=7, **params)
question = gen.render(inst)
candidate = gen.parse_answer(
    "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
)
assert gen.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
python3 results/2212.14814/gen_2212_14814.py
bash scripts/emit.sh 2212.14814 20 easy
```

The implementation is standard-library-only. It imports `gvlib` when present
to follow the repository convention, but this finite graph certificate does not
need its rational or polynomial helpers and degrades cleanly if they are absent.

## Caveats

This is a deliberately structured Track-B distribution, not evidence of
average-case hardness for Cograph Editing or nested-module detection. A graph
program solves it in milliseconds, as the disclosed reference measurements
show. A solver that recognizes the complementary row-pair construction also
finds it quickly; that is the intended success mode.

The 0/250,000 guess estimate samples uniformly from ordered triples of disjoint
canonical vertex pairs. It includes every shape/order restriction stated for
free, but it does not model a solver's strong graph prior; the much more relevant
construction-aware attacks are reported separately. Those attacks cover degree
outliers, largest and most frequent contrasts, a first-six-rows ansatz, and 256
random restarts. They do not include a production modular-decomposition package,
SAT/ILP encoding, or a learned row-clustering system. Such tools are expected to
succeed and are consistent with Track B.

`canonical_key` uses a complement-invariant 1-WL quotient, not exact graph
canonization, so nonisomorphic graphs can theoretically collide; it nevertheless
passed all required transformations and distinguished 20/20 unrelated seeds.
Finally, the task specification describes a four-vendor oracle pool, while the
installed `harden.py` currently contains a two-vendor pool (OpenAI and Google).
The transcript proves the installed harness criterion, not a four-vendor claim.
