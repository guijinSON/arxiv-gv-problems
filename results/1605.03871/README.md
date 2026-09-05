# Temporal maximal Δ-clique generator (arXiv:1605.03871)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a vertex set plus a closed interval) |
| Intended intuition | invariant — first contact times are sums of hidden residues |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator is based on Himmel, Molter, Niedermeier, and Sorge, [“Adapting the Bron-Kerbosch Algorithm for Enumerating Maximal Cliques in Temporal Graphs”](https://arxiv.org/abs/1605.03871). It hands the solver a temporal graph as exact integer-stamped pair interactions. The requested witness is a size-`k` maximal Δ-clique lasting for the graph's entire closed lifetime. Verification implements Definition 2 directly: every chosen pair must meet every inclusive sliding Δ-window, no outside vertex may extend the clique, and the requested full lifetime is automatically time-maximal.

Generation is inverse. A known clique is selected first, inserted into a random-looking regular graph by degree-preserving 2-switches, and checked for maximality before its static edges are carried into two-contact temporal schedules. The answer is never found by solving the emitted instance. All vertices have the same full-lifetime temporal degree, so the planted vertices are not degree outliers.

## Why Track B, and what makes the paper's problem easy

Track A would be false. The paper's Algorithm 5 is a pivoted temporal Bron–Kerbosch enumeration algorithm. Theorem 2 gives the output-sensitive bound `O(x|E| + |E||T|)` for `x` time-maximal Δ-cliques, Corollary 1 gives an exponential general bound, and Theorem 3 gives `O(3^(d/3) 2^d |V||T||E|)`: enumeration is FPT when Δ-slice degeneracy `d` is small. Here `d` grows with `n` (68 at shipping), avoiding that small-parameter regime, but an exact implementation still solves the generated distribution quickly.

At the shipping preset, the specialized pivoted reference search used 39,720 counted operations, 4,905 recursive nodes, and 0.0056 s on the fixed G5 instance. Across eight G6 instances it solved 8/8 in 413,853 operations and 0.0635 s. A stronger 128-restart randomized greedy also solved 8/8 in 170,871 counted operations and 0.0253 s. Those successes are disclosed reference algorithms, not failed attacks.

The compact route exploits extra structure in the time stamps. Edge first-times are pairwise sums of latent vertex residues modulo `q`. Recovering the residues exposes the one omitted residue; one of its two consecutive boundary blocks is the planted clique. The measured route uses at most 296 exact operations. That is short enough after the invariant is seen, but the uncompressed scan of 4,692 schedules is not realistically executable by hand in context.

## Worked demo

This is the complete `demo`, seed 7. A person can solve it on paper: with only 10 vertices and 20 schedules, each schedule covers the full lifetime exactly when its two contacts are at most Δ apart and reach both boundary windows.

```text
Find a maximal Delta-clique with exactly 3 vertices and interval [0,21].
Vertices: 0,1,2,3,4,5,6,7,8,9
Closed graph lifetime: [0,21]; Delta = 11

u v t1 t2
0 2 0 11
0 3 10 21
0 4 6 17
0 7 9 20
1 4 4 15
1 6 5 16
1 8 6 17
1 9 2 13
2 3 5 16
2 5 7 18
2 9 10 21
3 5 6 17
3 6 1 12
4 6 8 19
4 7 10 21
5 7 5 16
5 8 4 15
6 8 10 21
7 9 8 19
8 9 7 18
```

The planted answer is:

```json
{"vertices":[2,3,5],"interval":[0,21]}
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping vertex 5 returns `(False, "need exactly 3 vertices")`. The demo has six acceptable witnesses among 120 shape-valid triples; uniqueness is neither promised nor required.

## Difficulty presets

| preset | vertices | regular degree | `k` | schedules | structure-aware candidates | result |
|---|---:|---:|---:|---:|---:|---|
| demo | 10 | 4 | 3 | 20 | 120 | hand example; oracle skipped |
| easy | 100 | 36 | 8 | 1,800 | 186,087,894,300 | oracle solved 1/3 |
| medium | 126 | 44 | 9 | 2,772 | 16,466,440,817,750 | oracle solved 1/3 |
| **hard** | **138** | **68** | **12** | **4,692** | **60,881,281,549,022,688** | **ships; oracle solved 0/3** |

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified across all presets |
| G2 | six corruptions rejected with six distinct reasons |
| G3 | tagged, fenced model response round-tripped; garbage returned `None` |
| G4 | 0 hits / 200,000 uniform sorted `k`-subsets with the forced interval |
| G5 | shipping sampled density 0/200,000; 39,720 reference operations, 4,905 nodes, 0.0056 s |
| G6 | five attacks × 8 seeds, all 0/8; both disclosed reference algorithms solved 8/8 |
| G7 | doubled instance has 276 vertices; planted and compact witnesses verify; answer atoms unchanged |
| G8 | 60/60 relabel/reorder and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 81 chars, 21 estimated tokens, 14 atoms, 296 intended exact operations |

The G4 prior is deliberately structure-aware: it samples uniformly from sorted, distinct size-`k` vertex sets and gives every candidate the forced full-lifetime interval. It therefore does not inflate the space with malformed answers.

## Bare oracle loop

| preset | seed | result | exact reason |
|---|---:|---|---|
| easy | 843341769 | failed | vertices not strictly increasing; sorting still left a missing pair |
| easy | 689858025 | failed | empty length-limited response |
| easy | 532810948 | **solved** | witness verified |
| medium | 2052747216 | failed | empty length-limited response |
| medium | 1313742095 | failed | vertices not strictly increasing; sorting still left a missing pair |
| medium | 395186499 | **solved** | witness verified |
| hard | 799668093 | failed | empty length-limited response |
| hard | 1819021754 | failed | pair 11,27 misses a Δ-window |
| hard | 1881469471 | failed | no parseable final answer after manual search |

The harness verdict is `hardened` at the named hard preset after two escalations.

## G9 three-arm diagnostic

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted − placebo = 0.0`. The hint named only the additive residue invariant and bought no measured success on this sample. This does not prove that the invariant is irrelevant: the transcripts show long manual graph work, and the compact implementation succeeds on 64/64 tested seeds. It does show that naming the invariant alone did not make reconstruction and exact transcription reliable. The answer and route remain within the gated caps: 81 characters, 14 atoms, and at most 296 exact operations.

## Use

From this directory:

```python
import random
import gen_1605_03871 as gen

inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer('<answer>{"vertices":[0],"interval":[0,1]}</answer>')
ok, reason = gen.verify(inst, candidate)
random_shape_valid_guess = gen.random_candidate(inst, random.Random(1))
```

From the repository root, emit verified records with:

```bash
bash scripts/emit.sh 1605.03871 20 hard
```

## Caveats

This is intentionally not evidence that maximal Δ-clique search is hard on this distribution: both reference solvers take milliseconds. It measures whether a no-tool model can compress thousands of temporal rows into the additive invariant and execute the resulting exact reconstruction. The full-lifetime restriction also makes temporal compatibility coincide with one static compatibility layer, although the input and verifier retain the paper's exact time-window semantics.

The 0/200,000 guess rate estimates only the declared uniform `k`-subset prior; it says nothing about learned or structure-aware search. A 64-restart randomized greedy failed 0/8 in the attack panel, but a 128-restart variant succeeded 8/8 and is reported prominently. The tests include degree and timestamp outliers, one-path greedy, randomized clique growth, deflated power iteration, and pivoted Bron–Kerbosch. They do not include an external SAT/ILP solver, a full SDP relaxation, or every modern maximum-clique implementation. Finally, `canonical_key` is complete for the generator's recovered-residue representation and tested symmetries, not a claimed general-purpose temporal graph isomorphism algorithm.

The repository hardener's 2026-09-05 default pool contained two vendors (OpenAI and Google), not the four-vendor pool described by its older top-level documentation; the script-owned metadata records the exact pool used. Thus the oracle evidence is cross-vendor but not four-vendor evidence.
