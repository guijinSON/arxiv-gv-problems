# Rejected Kempe reconfiguration candidate — arXiv:2112.02313

> **Audit outcome:** do not ship this family. The implementation is retained as
> `rejected_gen_2112_02313.py`, and [REJECTED.md](REJECTED.md) records the
> deciding H/G9 failure. The older sections below document the attempted build.

## Profile and trust status

| field | value |
|---|---|
| track | **A — structural hardness** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple (a sequence of `[vertex,color]` moves) |
| intended intuition | search pruning by quotienting anchors that name the same bichromatic component |
| domain essentiality | native |
| reduction | none |

The construction and verification gates pass, including 200,000 random candidates and six attacks over eight shipping seeds. The family nevertheless fails H/G9(c): 225 operations replay an already-known certificate, while recovering it still requires the component-quotient search (at least 220,001 generated successors in the measured run). The required external oracle claim is also incomplete: two genuine easy-preset attempts failed, after which OpenRouter returned HTTP 403 “key limit exceeded” on every redraw.

## Problem family

This module covers the native Kempe-reconfiguration objects in Bonamy, Delecroix, and Legrand-Duchesne, [“Kempe changes in degenerate graphs”](https://arxiv.org/abs/2112.02313). The solver receives a relabeled rectangular grid and two proper 3-colorings. A move chooses one current bichromatic connected component and swaps its two colors. The answer is an exact-length move sequence taking the start coloring to the target.

Generation is by composition of identities: begin with a proper checkerboard coloring, scramble it using valid Kempe changes, sample the answer walk, and replay that walk to obtain the target. No endpoint instance is solved during certificate construction. `verify` ignores `inst["answer"]`; it recomputes every component and compares the final coloring exactly.

## Why Track A is the honest claim

Section 1 defines the objects, and Lemma 1.1 guarantees that all (k)-colorings of a (d)-degenerate graph are Kempe equivalent for the tight regime (k=d+1). The same discussion says the proof can produce exponentially long sequences and that a polynomial bound in the general degeneracy setting remains open. It also explicitly names rectangular grids as 2-degenerate graphs with unbounded treewidth.

The shipping 10×10 grid uses (d=2,k=3), has treewidth 10, maximum degree 4, and average degree 3.6. Thus it is outside the paper’s three polynomial regimes: Theorem 0.1 needs maximum degree at most (k); Theorem 0.2 needs maximum average degree strictly below (k); and Theorem 0.3 needs treewidth at most (k-1). This is not an average-case theorem for the planted distribution. The evidence for that narrower distributional claim is G5/G6: exact bidirectional BFS over distinct component moves exhausted 220,000 generated successors on every shipping instance, stored a mean 92,389 states, reached only depth 3 from either end, took 0.587 seconds per instance, and solved 0/8. A separate width-256 component beam generated 1,371,118 successors over eight instances and also solved 0/8.

## Worked demo

The `demo` preset with seed 3 renders this complete instance:

```text
Vertices: 1..9; colors: 1,2,3; graph: a relabeled 3 by 3 grid.
Edges:
[[1,2],[1,6],[1,8],[2,4],[3,6],[3,7],[3,8],[4,5],[4,8],[5,9],[7,9],[8,9]]
Start:
[1,2,1,1,3,2,2,3,1]
Target:
[3,1,3,3,2,1,1,2,3]
Return exactly 2 Kempe moves as JSON [vertex,target_color] pairs.
```

The answer is `[[6,1],[5,2]]`; `verify(inst, answer)` returns `(True, "ok")`. Dropping its last move gives `[[6,1]]`, which returns `(False, "too few moves: got 1, expected exactly 2")`. A person can solve this demo on paper by drawing the twelve edges and tracing the two changing bichromatic components.

## Difficulty presets

| preset | vertices | grid | moves | burn-in | minimum endpoint Hamming distance | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 9 | 3×3 | 2 | 18 | 2 | hand example |
| easy | 36 | 6×6 | 16 | 144 | 20 | locally valid; oracle unavailable |
| medium | 64 | 8×8 | 16 | 256 | 40 | locally valid; oracle unavailable |
| hard | 100 | 10×10 | 16 | 400 | 64 | **shipping preset pending oracle evidence** |

Escalation grows the grid side one row and column at a time and raises the attack budget while keeping both the answer at 16 moves and the endpoint-distance threshold fixed. All four post-hard rungs reachable within the harness budget (11×11 through 14×14) constructed and verified across eight test seeds each. Beyond the 20×20 language bound, the generator reports `cap_bound` because maintaining this construction's route under the 300-operation cap is no longer reliable.

## Gate results

| gate | final measured result |
|---|---|
| G1 | 12/12 planted certificates verified |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged prose/Markdown round-trip passed; garbage returned `None` |
| G4 | 0 hits / 200,000 structure-aware dynamic samples; space (200^{16}) |
| G5 | shipping sampled density 0/200,000; demo exact answer-string count 42; exact BFS hit 220,001 successors in 3.028 s mean in the fresh audit |
| G6 | outlier, forward greedy, reverse greedy, random-restart-32, exact bidirectional BFS, and bidirectional beam all 0/8 |
| G7 | 200-vertex instance built in 0.56 s and verified; candidate space increased |
| G8 | 140/140 relabelings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | **fails honestly**: 111 characters, 28 estimated tokens, 32 atoms, but at least 220,001 recovery operations; 225 was replay-only |

## Oracle loop

The final bare harness reached only the first `easy` rung. Terra and Gemini each completed one genuine attempt and returned a parseable but invalid witness. The next four redraws returned HTTP 403. Per the harness contract, errors do not consume attempts; consequently there is no `hardened` or `too_easy` verdict.

| preset | seeds | completed attempts | solved | outcome |
|---|---|---:|---:|---|
| easy | 1389075849, 1635123667 | 2 | 0 | both answers invalid; four later HTTP 403 redraw errors |

## G9 diagnostic arms

| arm | solved / completed attempts | result |
|---|---:|---|
| bare | 0/0 | pool unreachable |
| structural hint | 0/0 | pool unreachable; transcript retained |
| placebo hint | 0/0 | pool unreachable; transcript retained |

The hinted-minus-placebo difference is unavailable, not zero. The answer uses 111 characters and 32 atomic integers. The earlier 225-operation figure measures replay after the witness is known, not witness recovery; the corrected lower bound is the 220,001 successors exhausted by the standard component-quotient search, so G9(c) fails.

## Use

```python
import rejected_gen_2112_02313 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

This retained module is for reproducing the rejection audit and must not be emitted.

## Caveats

The attempted Track A claim is empirical for this planted distribution, not implied by Lemma 1.1 and not a proof of average-case hardness. G4 samples uniformly from the statement-visible sequence language: at each state it chooses one of (n) anchors and either other color. Multiple anchors can name the same Kempe component, so 0/200,000 is a density over answer strings, not over distinct state transitions; G6 separately searches the quotient by distinct components.

The generator would become easier if the walk were shorter, if intermediate colorings were exposed, or if endpoint discrepancies became monotone under the planted moves. It filters the obvious greedy and restart leaks. The standard exact bidirectional BFS was node-limited after 220,000 generated successors per instance; it is not a completed exhaustive search. No SAT/SMT encoding, disk-backed meet-in-the-middle search, or full implementation of the potentially exponential Las Vergnas–Meyniel recursion was attempted. Finally, the four-vendor no-tool evidence and the hinted/placebo diagnostic remain missing until the OpenRouter key limit is restored; this directory should not be submitted as hardened before rerunning those scripts.
