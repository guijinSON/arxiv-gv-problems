# Strong identification codes for graphs (arXiv:2108.06733)

**Status:** all local gates pass. The required multi-vendor hardness claim is **not established** because every bare, structural-hint, and placebo oracle request returned OpenRouter HTTP 403 `Key limit exceeded`. Those script-owned error transcripts are retained and are not counted as model failures.

| Profile | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style constrained subset search |
| Certificate | integer tuple: a fixed-size vertex set |
| Intuition | symmetry — repeated directed differences expose an affine relabelling |
| Domain essentiality | native; no reduction |

## Problem and trust model

[Ganesan, *Strong Identification Codes for Graphs*](https://arxiv.org/abs/2108.06733), Definition 1, calls a vertex set `C` an index-`r` identification code when every ordered pair `v != u` has at least `r` code vertices in `N[v] \ N[u]`. The solver receives the paper's native object: an exact finite graph encoded by closed-neighborhood bit rows, an allowed vertex pool, and a marked subset. It must return 24 permitted vertices, exactly five marked, satisfying that definition. `verify` checks every ordered pair by exact integer bit operations and accepts any valid code, never by comparing with the planted answer.

Generation is inverse and exact. The base answer is fixed first. Each vertex then receives a constant-weight neighborhood signature, with at least `r` directed differences between every two signatures. Symmetry of the code rows makes the graph undirected. A random affine vertex relabelling carries the certificate, and code/decoy labels have the same one-vertex marginals. This is construction, not a search for a code.

## Why Track B

The paper has no computational-hardness theorem: Section 2, Theorem 1 is a probabilistic upper bound whose proof directly constructs a code by sampling `Z` and repairing bad vertices; Section 3, Theorem 2 and its auxiliary Lemma 3 are probabilistic existence results for strong-neighborhood graphs. A Track A claim would therefore be unjustified.

The problem-class baseline is pseudo-Boolean DPLL with unit/cardinality propagation and a full-constraint greedy CSP plus legal one-vertex-repair branching heuristic. Across eight shipping instances it solved 8/8 using 4,234,396 packed-wide heuristic operations, estimated as 17,145,069,404 64-bit word operations, plus 55,075,836 DPLL constraint scans in 18.00 seconds total. Its worst case is exponential. A separate algorithm complete for this generated distribution exhausts affine images of the base template in `O(n^2 k)` time before exact checks; it solved 8/8 after 17,278,488 modular image operations and 719,937 candidates in 3.32 seconds total. The compact route notices the repeated directed-difference multiplicity among the marked labels and needs at most 250 scalar modular operations. This compression gap—not NP-hardness—is the Track B claim. Theorem 1's trivial/easy regime also matters: if the graph already has the `r`-strong-neighborhood property, the whole vertex set is a code. The fixed 24-entry requirement and pool constraints prevent that answer.

## Worked demo

The complete `demo`, seed 0 statement is:

```text
Find a strong identification code in a finite graph.

Definitions and exact conventions:
- The graph is simple and undirected, with vertices 0 through 12.
- N[v] is the closed neighborhood of v: vertex v itself together with every vertex adjacent to v.
- A vertex set C is an identification code of index r when, for every ORDERED pair of distinct vertices (v,u), at least r vertices of C lie in N[v] but not in N[u]. Thus both orders (v,u) and (u,v) are required.
- Here r = 1.
- The graph is encoded below by one hexadecimal bit row for every N[v]. In row v, bit j (the coefficient of 2^j, with bit 0 the rightmost bit) is 1 exactly when j belongs to N[v]. Leading zeroes are included. Every row includes its diagonal bit v.

Closed-neighborhood rows:
0: 04c9
1: 059e
2: 0aee
3: 0a7f
4: 109a
5: 1bac
6: 1a4d
7: 0ab7
8: 1322
9: 0bec
10: 1c03
11: 1eec
12: 1d70

Answer constraints:
- Return exactly 6 DISTINCT vertex numbers from this allowed pool:
  [0, 1, 6, 7, 8, 12]
- Exactly 3 returned vertices must belong to this marked subset:
  [0, 6, 12]
- The answer is a set: order has no mathematical meaning and repetitions are forbidden. Write it as one increasing JSON list.
- Every integer endpoint is inclusive: valid graph vertices range from 0 through 12.

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 6 distinct integers in increasing order.
Example format (not necessarily a solution): <answer>[0, 1, 2, 3, 4, 5]</answer>
Output nothing else inside the tags.
```

The answer is `[0, 1, 6, 7, 8, 12]`. `verify(instance, answer)` returns `(True, "ok")`; deleting the last entry returns `(False, "wrong length: expected 6, got 5")`. A person can solve this demo on paper because its allowed pool is exactly the answer set.

## Difficulty presets

| Preset | Graph `n` | Index `r` | Pool | Markers | Required | Answer | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 13 | 1 | 6 | 3 | 3 | 6 | hand example; harness skips it |
| easy | 127 | 2 | 48 | 8 | 5 | 24 | oracle run blocked before a valid attempt |
| medium | 257 | 2 | 80 | 10 | 5 | 24 | not reached |
| hard | 509 | 2 | 120 | 11 | 5 | 24 | designated shipping preset; local gates pass |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted and 12/12 compactly recovered witnesses verify |
| G2 | pass | six corruptions rejected; the five mandatory cases have five distinct reasons |
| G3 | pass | tagged prose and an untagged JSON fence round-trip |
| G4 | pass | 0/200,000 structure-aware guesses; language size 369,093,607,947,184,151,991,960 |
| G5 | pass | shipping sampled density 0/200,000; demo exact count 1; PB-DPLL/CSP reference 18.00 s / 17.15B estimated word operations plus 55.08M scans |
| G6 | pass | degree, sampled-greedy, 256-restart, and by-hand label attacks all 0/8; PB-DPLL/CSP and complete affine references both 8/8 |
| G7 | pass | `n=1019`, pool 240 verifies; answer remains 24 entries |
| G8 | pass | 60/60 invariance checks, 20/20 transported witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 93 characters, about 24 tokens, 24 atoms, at most 250 exact operations |

## Oracle loop and G9 diagnostics

No row below is a valid oracle attempt. The harness correctly redraws errors and then stops rather than manufacturing hardness evidence.

| Arm | Preset | Valid solved/attempts | Error calls | Result |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 | HTTP 403 key limit; hardness verdict unavailable |
| structural | hard | 0/0 | 4 | HTTP 403 key limit; diagnostic unavailable |
| placebo | hard | 0/0 | 4 | HTTP 403 key limit; diagnostic unavailable |

`hinted - placebo` is unavailable, not evidence of zero effect. Restore OpenRouter quota and rerun all three arms before shipping. The intended route remains within G9(c): the measured answer is 93 characters / 24 atoms and the worst compact route observed was 250 exact modular operations.

## Use

```python
import gen_2108_06733 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
instance = g.make_instance(seed=123, **params)
answer = g.parse_answer("<answer>" + __import__("json").dumps(instance["answer"]) + "</answer>")
assert g.verify(instance, answer) == (True, "ok")
```

After valid oracle evidence exists, emit from the repository root with:

```bash
bash scripts/emit.sh 2108.06733 20 hard
```

## Caveats

The 0/200,000 figure is sampled from the exact stated prior—24-subsets of the pool containing exactly five markers—not from arbitrary integer noise. It is an empirical upper-scale check, not a proof of uniqueness; other valid codes are accepted. The construction is easy for software that tests affine templates, exactly as Track B declares. The panel implements pseudo-Boolean DPLL and a packed-bitset CSP greedy/repair heuristic but does not run an external industrial SAT/ILP package or a spectral relaxation; the latter is less natural here because the certificate is a constrained multicover of directed neighborhood differences, not a planted graph partition. The marker condition intentionally leaves a clean joint modular signal, though no individual code vertex has a privileged label distribution. Color refinement is a full canonical form on these individualized random graphs, but only a stable-quotient invariant if an unusual instance does not individualize. Most importantly, multi-vendor no-tool hardness has not been established because the available OpenRouter quota is exhausted.
