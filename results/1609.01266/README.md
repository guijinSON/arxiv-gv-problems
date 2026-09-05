# arXiv 1609.01266 — verified MCW generator (G9 incomplete)

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (a set partition into triples) |
| Objects shown to the solver | weighted pseudo-grid column tuples and the paper-licensed 3-PARTITION core |
| Intended intuition | constraint propagation |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 5, Theorem 20 |

## What this family is

[Soulignac and Terlisky, *Minimal and minimum unit circular-arc models*](https://arxiv.org/abs/1609.01266) defines Minimum Cycle Weighing by columns of a pseudo-grid digraph (MCW) in Section 5. An MCW instance is a sequence of four-integer column weights; permuting columns and swapping the two `x` or `y` coordinates changes the maximum weighted cycle. Theorem 20 proves MCW strongly NP-complete, and Theorem 21 maps it to minimum unit circular-arc representation.

This generator uses the exact Theorem-20 reduction, not an unrelated graph surrogate. It first samples a certified 3-partition, builds the reduction's `L_i`, item and `H_i` tuples, and shuffles all tuples. The solver returns a partition of the item-tuple indices into triples. `verify` checks the set partition and sums, reconstructs the normalized MCW sequence, and independently recomputes its maximum cycle weight with exact integer max-plus dynamic programming. The solver sees the paper's auxiliary MCW objects; this is licensed-reduction coverage, not direct coverage of circular-arc coordinates.

## Why it is hard

This is Track A. Theorem 20 proves strong NP-completeness by reducing 3-PARTITION to exactly the displayed pseudo-grid regime. Shipping instances have 24 triples, `T=n²`, every item strictly between `T/4` and `T/2`, and a uniformly shuffled mixture of item and anchor columns. Generation retains only planted instances on which value-band grouping, largest-first greedy pairing, 64 random exact-triple restarts, and a 5,000-node MRV Algorithm-X search all fail. The witness is still the partition sampled before construction; none of those attacks supplies it.

The easy side matters. Section 4.1, Theorem 15 computes a *minimal equivalent* UCA model in `O(n³)` time and `O(n²)` space, so merely planting arcs and asking for an equivalent or feasible unit model would not support Track A. Theorem 3 also checks a fixed descriptor and constructs a model or negative cycle in `O(n²)`. This module instead targets the paper's isomorphism/minimum hardness route. Given a proposed MCW sequence, its maximum cycle is polynomial-time checkable, exactly as the membership-in-NP argument of Theorem 20 requires.

The theorem is worst-case; it does not prove this planted distribution hard. The distribution claim rests on the measured attack panel and oracle loop below, and should be read with the caveats at the end.

## Worked demo (`seed=123`)

This is the complete no-hint rendering of the smallest supported instance. It is deliberately hand-solvable: all nine item values are 3, so any partition of the item indices into triples works.

```text
Find a normalized certificate for this Minimum Cycle Weighing (MCW) instance.

Definitions.
There are k=15 weighted column tuples X[q]=(x0,x1,y0,y1), listed below in shuffled order with 0-based indices.
The MCW pseudo-grid has 2k=30 columns and 4k=60 rows, with a vertex v(q,r) at every column q and row r.
A diagonal edge goes from v(q,r) to v(q+1,r-1), a vertical edge goes from v(q,r) to v(q,r+1), and a horizontal edge goes from the last column back to the first in the same row whenever the stated vertices exist.
For tuple (x0,x1,y0,y1) at tuple-position j and p=r mod 2: the diagonal leaving even column 2j has weight xp; a diagonal leaving an odd column and every horizontal edge have weight 1; a vertical edge leaving even column 2j has weight yp+xp+1; and a vertical edge leaving odd column 2j+1 has weight y(1-p)+xp+1.
The weight of a cycle is the sum of its edge weights, and wg(Y) is the maximum cycle weight after the tuples have been reordered into sequence Y.

This instance is in the normalized Theorem-20 reduction form. You must identify every item tuple, meaning a tuple (T,s,1,1), and partition their 0-based input indices into exactly n triples.
For i=0,...,n-1 define l_i=2(n^2+i), h_i=l_i+2, and y_inf=h_n^2. The anchor tuples are L_i=(l_i*T,1,y_inf-l_i*T-1,y_inf-2) and H_i=(1,h_i*T,y_inf-h_i*T-1,y_inf-2).
A certificate is valid exactly when every item index appears once and the three s values in every triple sum to T. The checker forms Y=(L_0, triple_0, H_0, L_1, triple_1, H_1, ..., L_(n-1), triple_(n-1), H_(n-1)), with no coordinate swaps, and independently recomputes that wg(Y) is at most the displayed bound.
The order of the triples and the order of indices inside each triple do not matter. Repeats are forbidden; anchor-column indices are not item indices.

n = 3
T = 9
y_inf = 676
cycle-weight bound = 20243

Shuffled tuples, as index: (x0,x1,y0,y1):
0: (9,3,1,1)
1: (198,1,477,674)
2: (9,3,1,1)
3: (1,180,495,674)
4: (180,1,495,674)
5: (9,3,1,1)
6: (9,3,1,1)
7: (9,3,1,1)
8: (1,216,459,674)
9: (9,3,1,1)
10: (1,198,477,674)
11: (9,3,1,1)
12: (9,3,1,1)
13: (162,1,513,674)
14: (9,3,1,1)

Give your final answer inside <answer></answer> tags as a JSON array of exactly 3 three-integer arrays.
Example: <answer>[[3,17,42],[8,11,29]]</answer>
Output nothing else inside the tags.
```

One answer is `[[9,7,2],[12,14,6],[5,11,0]]`; `verify` returns `(True, "ok")`. Replacing item 9 by anchor 1 gives `[[1,7,2],[12,14,6],[5,11,0]]`, and `verify` returns `(False, "anchor used: column 1 is not an item tuple")`.

## Difficulty presets

| Preset | Triples `n` | Item indices in answer | Filter node cap | Random restarts | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 9 | 0 | 0 | hand-scale illustration |
| **easy** | **24** | **72** | **5,000** | **64** | **ships; bare prompt hardened** |
| medium | 36 | 108 | 20,000 | 96 | reserve rung |
| hard | 48 | 144 | 50,000 | 128 | reserve rung |

`escalate` first raises both attack conditioning limits at fixed `n`, so the answer stays the same length. It increases `n` only after the filter reaches 800,000 nodes, and returns `"cap_bound"` at 85 triples.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; every answer JSON-round-tripped |
| G2 | pass | 7 corruptions rejected with 7 distinct reasons |
| G3 | pass | tagged/fenced JSON plus surrounding prose round-tripped; raw fenced JSON is also accepted |
| G4 | pass | 0/200,000 uniform structure-aware set partitions valid; candidate space about `2.08e61` |
| G5 | pass | shipping density sample 0/200,000; exact demo count 280/280; strongest attack cost 40,008 nodes, 15,467,731 option checks, 1.338273 s across 8 instances |
| G6 | pass | value bands 0/8, greedy 0/8, random restart 0/8, MRV Algorithm X 0/8 |
| G7 | pass | `n=48` still builds and verifies; fixed-answer escalation raises filter 5,000→10,000 |
| G8 | pass | 40/40 reorder/composition invariance checks and carried witnesses; 20/20 unrelated keys distinct |
| G9 | **incomplete** | 271 characters, 68 estimated tokens (72-token relabelling worst case), 72 atoms, 48 exact additions; hinted oracle 0/2 before the API key limit |

As an additional verifier audit, the compressed `O(k²)` max-cycle DP matched an absolute-row DP on 600 random tuple sequences, and all 280 demo candidates were exhaustively graded.

## Bare oracle loop

API-error rows are retained in the transcript but excluded from scoring. The final bare run completed normally and hardened at easy.

| Preset | Seed | Model | Solved? | Outcome |
|---|---:|---|---|---|
| easy | 1340134410 | GPT-5.6 Terra | no | one triple summed to 574, not 576 |
| easy | 2046782695 | Claude Sonnet 5 | no | empty length-limited response |
| easy | 1281820048 | Gemini 3.1 Pro | no | one triple summed to 580, not 576 |

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened at shipping easy |
| structural hint | 0 / 2 | **incomplete:** third scored attempt blocked by OpenRouter key total limit |
| placebo hint | 0 / 2 | **incomplete:** third scored attempt blocked by OpenRouter key total limit |

The provisional hinted-minus-placebo difference is `0.0`, but the required three-attempt arms did not finish. Each arm recorded two genuine failures; then Grok timed out and subsequent redraws received HTTP 403 `Key limit exceeded (total limit)`. The harness correctly refused to make a hardness claim. The module therefore reports G9 as failing/incomplete and is **not ready to submit** until both arms are rerun with a replenished OpenRouter key. Answer size is 271 characters / 68 estimated tokens / 72 atoms; the worst relabelling measured 72 tokens. The intended certificate uses 48 exact additions.

## Use

```python
from random import Random
from gen_1609_01266 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
prompt = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate)[0]
```

From the repository root, emit artifact rows with:

```bash
bash scripts/emit.sh 1609.01266 20
```

## Caveats

- Theorem 20 is a worst-case result, not an average-case theorem for this planted distribution. Conditioning on failure of one bounded MRV implementation is empirical hardening, not a complexity proof for the distribution.
- `0/200,000` is the observed hit rate under a uniform prior on all partitions of the item indices into unlabeled triples. It does not estimate a solver's non-uniform, value-aware prior, nor does it statistically prove a probability below `1e-6`.
- The generator deliberately runs a bounded exact-cover attack while selecting instances. This can make construction slower, but it never uses a solution returned by that attack; the answer was sampled first and carried through the paper's reduction.
- No industrial CP-SAT, ILP, SAT encoding, dancing-links implementation, or parallel exact-cover solver was run. A stronger solver may crack the shipping preset quickly.
- The answer is a normalized reduction witness, not a full circular-arc coordinate model. Theorem 21 licenses the connection to minimum UCA representation, but this module should not be counted as direct geometry coverage.
- The demo is intentionally degenerate—all item values are equal—so it demonstrates formatting and exact verification rather than difficulty.
- G9 is presently incomplete for an external reason: both final-renderer hint arms stopped at 2/3 scored attempts after the OpenRouter key hit its total limit. Do not treat the existing `selftest_report.json` as all-passing or submit this directory until those arms finish and `selftest()` is rerun.
