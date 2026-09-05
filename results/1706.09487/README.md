# arXiv 1706.09487 — verified seeded-cluster generator

| Profile field | Value |
|---|---|
| Track | B — the efficient mechanical algorithm is disclosed and measured |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | integer tuple: seven added vertices at shipping size |
| Intended intuition | symmetry: a power-map fibre is an orbit of roots of unity |
| Domain essentiality | native |
| Reduction | none |

## What the family is

[Bliznets and Karpov, *Parameterized Algorithms for Partitioning Graphs into Highly Connected Clusters*](https://arxiv.org/abs/1706.09487) define **Seeded Highly Connected Edge Deletion** in Section 3.1. Given a graph, a seed set `S`, an addition count `a`, and an edge budget `k`, one must retain one highly connected component `C` containing `S` with `|C|=|S|+a`, while edge deletions make every vertex outside `C` isolated. “Highly connected” uses the paper's strict condition: every induced degree is greater than `|C|/2`.

Here the vertices are nonzero affine residues modulo a prime, and equal values of `(x-shift)^s` form clique components. The solver supplies the other vertices in the seed's clique. That vertex list is a compressed deletion witness: retain precisely the edges inside it and delete every other edge. `verify` recomputes induced degrees and the deletion count exactly; it never reads `inst["answer"]`.

## Why Track B

This is deliberately not an average-case hardness claim. Theorem 4 gives a generic `2^{O(sqrt(k) log k)}` algorithm, Theorem 5 supplies its kernel, and this generated subclass is much easier still: an explicit graph exposes the seed's connected component, while the succinct version is solved by scanning all residues and comparing their `s`-th powers. The measured scan solves 8/8 shipping instances in **4.649 seconds and 141,557,859 exact modular operations on average**.

The compact route is to compute `zeta = g^((p-1)/s)`, whose order is `s`, and take the affine orbit `shift + (seed-shift) zeta^j`. It needs at most **73 exact operations** and returns seven vertices. The benchmark tests whether a no-tool solver recognizes and executes that symmetry instead of scanning tens of millions of residues. An ordinary program, CAS, or finite-field package makes the family easy, as Track B requires us to say.

## Worked demo

`make_instance(n=13, s=4, spread=0, seed=0)` renders in full as:

```text
Seeded Highly Connected Edge Deletion in a finite graph.

Definitions.
A finite undirected loopless graph on r vertices is highly connected when every vertex has degree strictly greater than r/2.
For a chosen vertex set C, use the following compressed deletion set: delete every graph edge that is not wholly inside C.
This leaves the induced graph on C and makes every vertex outside C isolated.

The graph is specified exactly by the following rule; there is no unstated edge list.
All arithmetic is modulo the prime p = 13.
The vertices are the residues 0,1,...,12, except shift = 4, which is omitted.
Set s = 4 and phi(x) = (x-shift)^s modulo p.
Two distinct vertices x and y are adjacent exactly when phi(x) = phi(y).
A primitive generator of the nonzero residues modulo p is g = 2.
The graph has exactly 18 edges.

The supplied seed set is S = {0}.
Choose exactly a = 3 additional vertices X, and put C = S union X.
The compressed deletion set defined above may contain at most k = 12 edges.
After those deletions, C must be the one highly connected component and every other vertex must be isolated.

Output X as an unordered JSON list of exactly 3 distinct base-10 integers.
Every entry must lie in the inclusive range 0..12; the omitted shift and the seed are forbidden.
Order does not matter and repetitions are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON list of integers.
Format-only example (not an answer to this instance): <answer>[1,2,3]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[8,10,11]</answer>`. `verify(inst, [8,10,11])` returns `(True, "ok")`; `verify(inst, [8,10])` returns `(False, "expected exactly 3 additional vertices, got 2")`. A person can solve the demo by hand: modulo 13, `zeta = 2^3 = 8`, and the four-element orbit of the seed displacement supplies the clique.

## Difficulty presets

The table uses seed 0. Other seeds move the prime upward within the same scale. The hardening run first solved smaller provisional rungs, so the ladder was slid upward; the successful `n=33,554,432` escalation is now named `hard`.

| Preset | `n` | Seed-0 vertices | Answer length | Status |
|---|---:|---:|---:|---|
| demo | 13 | 12 | 3 | hand-solvable illustration |
| easy | 524,288 | 524,352 | 7 | provisional equivalent was defeated by 2/3 oracles |
| medium | 4,194,304 | 4,194,328 | 7 | provisional equivalent was defeated by 1/3 oracles |
| hard | 33,554,432 | 33,554,472 | 7 | **ships; 0/3 solved** |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify and JSON-round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and fences; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; sampled space size about `4.49e50` |
| G5 | pass | shipping density 0/200,000; demo has exactly 1/165 valid candidates; strongest failing panel tested 2,088 candidates |
| G6 | pass | six attacks at 0/8; reference scan 8/8 at 4.649 s and 141,557,859 operations mean |
| G7 | pass | fixed seven-entry witness while a test instance grows from 45,613,080 to 91,226,136 vertices |
| G8 | pass | 80 affine/generator/twin-swap invariance checks, 80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 61 characters, about 16 tokens, 7 atoms, 73 intended operations |

## Oracle loop

The final script-owned `llm_loop_transcript.jsonl` is a reproducible shipping-only confirmation with master seed `170609487`: seeds 776301995, 93047830, and 1808313208 all failed because their parseable lists were not highly connected. The longer discovery run is preserved as `initial_ladder_transcript.jsonl`; its results before the ladder was renamed are below. A rung is defeated if any attempt succeeds.

| Parameters / run label | Seeds | Solved | Reason |
|---|---|---:|---|
| `n=33,554,432` / final hard confirmation | 776301995, 93047830, 1808313208 | **0/3** | all candidates failed high connectivity |
| `n=4,096` / easy | 1651316124, 523046197, 1677695461 | 3/3 | exact witnesses verified |
| `n=65,536` / medium | 736443462, 1835153459, 308636188 | 3/3 | exact witnesses verified |
| `n=524,288` / hard | 131389900, 2101948643, 1714799957 | 2/3 | one candidate failed high connectivity |
| `n=4,194,304` / escalated | 376941712, 1539425813, 193010130 | 1/3 | two candidates failed high connectivity |
| `n=33,554,432` / escalated, now hard | 219278667, 555578515, 1984693834 | **0/3** | all candidates failed high connectivity |

## G9 arms

| Arm | Solved / attempts | Outcome |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. The structural hint bought no measured improvement: at shipping scale, exact modular execution appears to dominate even when the orbit invariant is named. That weakens any claim that failures isolate symmetry recognition alone, although the 73-operation cap keeps the intended route within the no-tool policy. The answer is 61 characters / 7 atoms.

## Use

```python
import json
import gen_1706_09487 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1706.09487 20 hard
```

## Caveats

- The graph is given succinctly by an exact adjacency rule rather than an expanded edge list. Expanding it, using a finite-field library, or scanning the residues makes the instance easy. This is why the claim is Track B only.
- The generated graphs are disjoint unions of equal cliques, a very easy subclass of the paper's general problem. The benchmark covers the native witness and verifier, not the paper's worst-case parameterized lower bounds or a hard planted distribution.
- `P(guess)` is uniform over all correctly sized, distinct vertex lists after excluding the omitted residue and seed. It measures blind structure-aware guessing, not a solver using the root-of-unity prior; exactly one candidate is valid by construction.
- The failing panel tried equal-degree/small-label outliers, nearest-label greed, an additive quotient-step guess, a reflection plus greedy completion, unreduced primitive-generator powers, and 256 random restarts per seed. It did not try a CAS, external finite-field code, or tool-enabled LLMs, all of which are outside the no-tool claim.
- The paper's generic Theorem 4 bound is not the baseline used to inflate difficulty. The stronger subclass-specific linear scan is disclosed and measured. The zero hinted-placebo gap means this family should not be used as clean evidence that a model specifically failed to notice symmetry.
