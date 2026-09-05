# Verified problem generator for arXiv:2004.10596

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple |
| Native objects | undirected simple graph, hexadecimal adjacency rows, set of `k` vertices |
| Intended intuition | invariant — a repeated low-degree neighborhood identifies adjacency rows whose GF(2) parity is the clique indicator |
| Domain essentiality | native; `reduction_kind="none"` |

## Problem and trust model

The solver receives an undirected simple graph and must return exactly `k` distinct, increasing vertex numbers whose every pair is an edge. This is the native `k`-clique search problem defined in Section 2.6.1 and implemented by the edge/clique detector blocks in Sections 4.1.4–4.1.5 of Sanyal (Bhaduri) et al., [*Circuit Design for Clique Problem and Its Implementation on Quantum Computer*](https://arxiv.org/abs/2004.10596). The graph is printed as fixed-width hexadecimal adjacency rows with the bit convention stated in full. Verification performs exact range, order, distinctness, and adjacency-bit checks and accepts any valid clique; it never reads the planted answer.

Generation is inverse, not search. One vertex is sampled from each hidden part, all edges of that transversal are inserted, and the remaining compatibility edges and a parity-probe gadget are sampled around it. A final random vertex permutation carries the known certificate into public labels. The module is deterministic from `(n, seed)`, uses only the Python standard library, and its answer is JSON-native.

## Why Track B, not Track A

The paper proves no average-case hardness theorem for this planted distribution, so general CLIQUE NP-hardness would not justify Track A. The paper instead supplies the mechanical side of a Track B gap: Section 4.2 explicitly constructs all `C(N,k)` vertex combinations, Section 5 gives `O(k C(N,k)+k)` oracle-synthesis gates, and Section 7 gives `O(sqrt(C(N,k)/m))` Grover iterations for `m` marked cliques. It also identifies its favorable circuit regime as `N >> k`; fixed small `k` is exactly the regime where classical enumeration is polynomial in `N`, so that fact is disclosed rather than hidden.

At shipping `N=216, k=8`, the paper-style route has `103,073,959,989,495` subsets and about `10,152,534` Grover iterations for one marked answer. A much better exact classical algorithm also exists: the included increasing-order bitset branch-and-bound has worst-case `O(N^k)` for fixed `k` (`O(N^8)` here), solves 8/8 shipping tests, and measured a mean 1,959 recursive intersections and 0.016318 seconds. After seeing the invariant, the compact route compares the repeated witness rows and XORs the four indicated adjacency rows one hexadecimal digit at a time: at most 174 exact check/XOR/extraction operations. That is the claimed no-tool compression gap.

The construction balances planted and decoy expected core degree, randomly relabels everything, and makes the random core `k`-partite so most attractive partial cliques are dead ends. Four to six marker incidences are sampled from the same Bernoulli law conditioned only on the parity identity. The attack panel checks degree outliers, deterministic greed, randomized greedy restarts, a parity-blind marker ansatz, and a centered spectral method.

## Worked demo

`make_instance(seed=3, **DIFFICULTY["demo"])` renders the complete instance below. Rows are displayed by increasing degree, but the left column remains the vertex label.

```text
Find a k-clique in an undirected simple graph.

A clique of size k is a set of exactly k distinct vertices such that every two different chosen vertices are joined by an edge. Vertex numbers are the integers 0 through 17. Here k = 4 and N = 18.

The graph is given by hexadecimal adjacency rows. Every row is a fixed-width 5-digit nonnegative hexadecimal integer. In row i, bit j is 1 exactly when {i,j} is an edge; bit 0 is the least-significant (rightmost) bit. Leading zeroes are significant only for keeping the width fixed. The decimal degree is supplied as a redundant check. The diagonal bits are 0 and the rows are symmetric.

Rows are listed by increasing degree (then by vertex number); the row label, not the display position, is the vertex number.

row  degree  adjacency_hex
  1       1  00001
  0       3  09002
  3       3  01120
  7       3  08840
  4       4  04a40
  5       4  01308
 10       4  02844
 14       4  0a014
 17       4  02844
 12       5  02829
  9       6  18134
 16       6  0a344
 13       7  35444
 15       7  14b81
  2       8  36f00
  6       8  32d90
  8       8  18a6c
 11       9  295d4

Output the vertices in strictly increasing order. Order otherwise does not matter, repetitions are forbidden, and all bounds are inclusive.
Give your final answer inside <answer></answer> tags as one JSON list of exactly 4 integers.
Format example only (not claimed to be a clique here): <answer>[0,1,2,3]</answer>
Output nothing else inside the tags.
```

Rows 10 and 17 repeat, so their common neighborhood is `{2,6,11,13}`. XORing those four rows leaves bits `{8,9,15,16}`. Therefore `<answer>[8,9,15,16]</answer>` gives `(True, "ok")`; dropping 16 gives `(False, "expected exactly 4 vertices")`. Exact enumeration finds two valid demo answers. A person can solve this smallest preset on paper with four five-digit rows.

## Difficulty presets

| Preset | Core `n` | Total `N` | `k` | Markers | Witness copies | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 12 | 18 | 4 | 4 | 2 | hand-solvable illustration |
| easy | 208 | 216 | 8 | 4 | 4 | **provisional shipping preset** |
| medium | 216 | 224 | 8 | 6 | 2 | larger haystack, less repeated-row redundancy |
| hard | 224 | 232 | 8 | 6 | 2 | largest named rung |

No preset was rejected by a local gate. “Provisional” is important: the external oracle pool was quota-blocked before it could issue a STEP 4 verdict.

## Local gates

| Gate | Result | Measured evidence at shipping unless noted |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset/seed instances; constructed parity route also recovered each answer |
| G2 corruption rejection | pass | empty, wrong length, swapped order, duplicate, and out-of-range rejected with five distinct reasons |
| G3 round trip | pass | tagged JSON recovered from fenced surrounding prose |
| G4 guess resistance | pass | 0/200,000 structure-aware guesses; candidate language size `88,535,640,906,570` |
| G5 density + baseline | pass | shipping estimate 0/200,000; strongest failing attack budget 1,866,240 units/instance and measured 0.907319 seconds/instance on the loaded worker |
| G6 adversary panel | pass | all five attacks 0/8; exact reference algorithm 8/8, as Track B expects |
| G7 scaling | pass | doubling core 208→416 grows candidate space `8.85e13`→`2.25e16`, answer stays 8 vertices |
| G8 canonical key | pass | 60/60 relabellings invariant, 60/60 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) caps | pass | worst-case 33 characters, about 9 tokens, 8 atoms; 174 intended exact operations |

Wall-clock values were measured while the shared worker was heavily loaded; deterministic operation/node counts are the more reproducible cost evidence. Full data is in `selftest_report.json`.

## Oracle loop and G9 diagnostics

The required harness was run from this directory. Gemini consumed its 32,000-token budget without emitting an answer; this is one valid unsolved attempt under the harness rules. The OpenAI vendor then returned HTTP 403 `Key limit exceeded` on all redraws, so the harness aborted and wrote no `harden_verdict`. Errors are not counted as model failures.

| Preset | Seed | Model | Scored result | Reason |
|---|---:|---|---|---|
| easy | 1181558389 | `google/gemini-3.8-flash` | unsolved | empty length-limited response |
| easy | 1273231796, 1257202423, 786948157, 1061681362 | `openai/gpt-5.6-terra` | errors, not attempts | OpenRouter total-key limit |

| G9 arm | Solved / valid attempts | Status |
|---|---:|---|
| bare | 0 / 1 | incomplete; pool became unreachable |
| structural hint | 0 / 0 | all calls HTTP 403 |
| placebo hint | 0 / 0 | all calls HTTP 403 |

`hinted - placebo` is undefined because neither diagnostic arm obtained a valid call. No conclusion about hint effectiveness is possible. The script-owned transcripts are retained exactly as produced. This result must not be called hardened or submitted until quota is restored and all three arms are rerun; G9(c)’s local size/effort gate still passes.

## Use

```python
import importlib.util

path = "results/2004.10596/gen_2004_10596.py"
spec = importlib.util.spec_from_file_location("clique_gen", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
inst = mod.make_instance(seed=7, **params)
question = mod.render(inst)
answer = mod.parse_answer(f"<answer>{inst['answer']}</answer>")
assert mod.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2004.10596 20 easy
```

## Caveats

This is not evidence for average-case planted-clique hardness. It is deliberately Track B, and the included exact branch solver is fast with tools. The 0/200,000 estimate applies only to the declared prior—uniform increasing `k`-subsets after the necessary degree filter—and establishes a sampling resolution, not a proof that the answer is unique or that another prior is equally weak. The demo has two answers, and `verify` correctly accepts either.

The panel does not include an SDP relaxation or a production maximum-clique package. A 256-restart tool-driven greedy search solved 6/8 of an earlier 228-vertex version; that is compatible with Track B but would destroy Track A. The final in-context panel uses 16 restarts and is 0/8 at shipping. The twin-neighborhood gadget intentionally makes the problem easy once its GF(2) role is recognized—that recognition is the benchmarked insight.

`canonical_key` uses a degree-seeded stable 1-WL quotient. It is invariant under tested vertex relabellings but may collide on specially constructed nonisomorphic graphs; full graph isomorphism is not attempted. Finally, the oracle evidence is incomplete because the shared OpenRouter key was exhausted, not because the family failed STEP 4. Rerunning `harden.py` with restored quota is the remaining external requirement.
