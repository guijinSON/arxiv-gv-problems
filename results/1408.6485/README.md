# arXiv 1408.6485 — verified domination-class generator

Status: the generator and every local gate pass, but the required external hardness experiment is **not complete**. OpenRouter returned HTTP 403 `Key limit exceeded` before any oracle produced an answer. The error-only transcripts are preserved; they are not counted as model failures and this result is not release-ready yet.

| Profile field | Value |
|---|---|
| Track | B — an efficient mechanical algorithm is disclosed |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | integer tuple (an unordered vertex list) |
| Intended intuition | symmetry: power-map fibres are false-twin classes in a regular graph |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

[McCreesh and Prosser, *Finding Maximum k-Cliques Faster using Lazy Global Domination*](https://arxiv.org/abs/1408.6485) define `v` to dominate `w` when `N(w) \ {v}` is contained in `N(v) \ {w}`. The solver receives a finite, undirected, loopless graph through an exact modular adjacency rule and a query vertex `v`; it must list every vertex dominated by `v`. The checker validates the list with exact finite-field exponentiation. It never reads the planted answer.

This uses the paper's native global-domination object, not the prior triage's planted random maximum-k-clique. Section 3.2 is the reason: the paper observes that random `G(n,p)^k` instances often become easy as distance powers make a k-clique cover the graph.

## Why Track B

Section 2 says that testing one domination pair is linear, finding every vertex dominated by one fixed vertex is quadratic, and finding all dominations is cubic; its bitset encoding accelerates these scans. For this implicit subfamily an even better formula-aware reference algorithm scans every residue and tests its `s`-th power in `O(p log s)`. At the shipping preset it solved 8/8 instances, as expected, averaging **0.412 seconds, 538,658 vertices, and 3,231,947 exact modular operations**.

The compact route is different. The graph is regular, so domination collapses to twinhood; equal `s`-th powers are precisely the false-twin fibres. Raising the supplied primitive generator to `(p-1)/s` gives an order-`s` root of unity, and multiplying the query displacement by its powers recovers the fibre. The measured worst case is 79 exact operations. This large scan-versus-symmetry gap is the Track B claim; with a CAS or short program the task is intentionally easy.

## Worked demo

This is `make_instance(n=11, s=2, seed=0)` in full:

```text
Find the complete global-domination class of one vertex in a finite graph.

Definitions.
For a vertex x, N(x) is the set of vertices adjacent to x.
A vertex v dominates a distinct vertex w when N(w) with v removed is a subset of N(v) with w removed.
All subsets and removals in that definition are ordinary set operations.

The graph is finite, undirected, and has no loops. It is specified exactly as follows; no unstated edge list is needed.
All arithmetic below is modulo the prime p = 11.
The vertices are all residues 0,1,...,10 except a = 6.
Set s = 2 and define phi(x) = (x-a)^s modulo p.
The supplied primitive generator is g = 8; rho = g^s modulo p = 9.
Two distinct vertices x and y are adjacent exactly when either

  phi(y) = rho * phi(x) modulo p,

or

  phi(x) = rho * phi(y) modulo p.

Query vertex: v = 7.
List every vertex w != v dominated by v. There are exactly 1 of them.
Your list is unordered: any order is accepted. Repeats are forbidden, and every entry must be a graph vertex.
Residues are written as ordinary base-10 integers in the inclusive range 0..p-1; the omitted residue a is not a vertex.

Give your final answer inside <answer></answer> tags, as one JSON list of integers.
Format-only example (not an answer to this instance): <answer>[0]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[5]</answer>`. `verify(inst, [5])` returns `(True, "ok")`; `verify(inst, [])` returns `(False, "answer list is empty")`. A person can solve this demo by hand: modulo 11, `(7-6)^2 = 1`, and the other nonzero square root gives `5-6 = -1`.

## Difficulty presets

The prime varies with the seed; the table shows seed 0. The answer stays fixed at seven vertices after the demo while the residue haystack grows.

| Preset | Nominal `n` | `s` | Seed-0 vertices | Answer length | Ships? |
|---|---:|---:|---:|---:|---|
| demo | 11 | 2 | 10 | 1 | no; hand example |
| easy | 4,096 | 8 | 4,128 | 7 | no |
| medium | 65,536 | 8 | 65,536 | 7 | no |
| hard | 524,288 | 8 | 524,352 | 7 | intended shipping preset, pending oracle evidence |

No preset has been rejected by a local gate. The external ladder could not score even `easy` because the shared OpenRouter key was over its total limit.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify and JSON-round-trip |
| G2 | pass | drop, replacement, duplicate, empty, and out-of-range corruptions all rejected with distinct reasons |
| G3 | pass | tagged JSON recovered from prose; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; sampled space size `8.218772673697723e45` |
| G5 | pass locally | shipping density 0/200,000; demo has exactly 1/9 valid answers; strongest failing panel used 2,088 candidates in 0.019 s |
| G6 | pass | six attacks each failed 0/8; reference scan solved 8/8 in 0.412 s and 3,231,947 operations on average |
| G7 | pass | seed-0 graph grows from 524,352 to 1,048,600 vertices when `n` doubles |
| G8 | pass | 80 key invariance and 80 carried-witness checks; 20/20 unrelated seeds distinct |
| G9(c) | pass | 61 characters, about 16 tokens, 7 atoms, 79 intended operations |

## Oracle loop and G9 arms

These rows are infrastructure failures, not mathematical failures.

| Run | Preset | Seeds written by `harden.py` | Valid solved/attempts | Outcome |
|---|---|---|---:|---|
| bare | easy | 1311880961, 365744023, 707860163, 226750422 | 0/0 | four HTTP 403 redraws; pool unreachable |
| structural hint | hard | see `g9_hinted_transcript.jsonl` | 0/0 | four HTTP 403 redraws; pool unreachable |
| placebo hint | hard | see `g9_placebo_transcript.jsonl` | 0/0 | four HTTP 403 redraws; pool unreachable |

`hinted - placebo` is therefore undefined in experimental terms (stored as 0.0 only because both denominators are zero). No conclusion about the claimed symmetry intuition can be drawn until the three arms have real attempts.

## Use

```python
import gen_1408_6485 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY["hard"])
question = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, after valid oracle evidence exists:

```bash
bash scripts/emit.sh 1408.6485 20 hard
```

## Caveats

- This benchmarks the paper's lazy global-domination relation, not maximum-k-clique branch-and-bound performance and not the empirical random graphs in Section 3.
- `P(guess)` is uniform over all distinct, correctly sized vertex lists. It measures blind structure-aware guessing, not a solver that recognizes the finite-field fibre; the latter has the 79-operation route by design.
- The graph is a highly algebraic regular cycle blow-up. A finite-field library, CAS, or ordinary program makes it easy, which is why the claim is Track B only.
- The panel tried equal-degree outliers, nearest labels, additive quotient steps, powers of two, a known reflection plus greedy completion, and 256 random restarts per seed. It did not try external CAS factorization or LLM tool use; those are outside the no-tool claim.
- Local mathematics was additionally checked by explicitly constructing all neighborhoods for the smallest `s=2,4,8` graphs and comparing the true domination class to the carried answer. The missing four-vendor results remain the decisive caveat.
