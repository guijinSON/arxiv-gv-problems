# Verified problem generator for arXiv:2307.03794

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph: bipartite perfect matching |
| Certificate | integer tuple encoding an alternative agent-to-house matching |
| Intended intuition | invariant: improving edges lie in conserved modular-sum layers |
| Domain essentiality | native; `reduction_kind = none` |

## Problem and trust status

This family uses the native house-allocation model of Aziz, Csáji, and Cseh, [*Computational complexity of k-stable matchings*](https://arxiv.org/abs/2307.03794). A solver receives agents with strict incomplete preference lists and a displayed current matching `M`. It must give another matching that every agent strictly prefers, which is a concrete certificate that `M` is not `n`-stable (equivalently, not weakly Pareto optimal). Verification performs exact range, distinctness, and preference-membership checks and never reads `inst["answer"]`.

All deterministic local gates pass. The required multi-vendor hardness claim remains **unverified**: the bare, structural-hint, and placebo runs were made with `harden.py`, but OpenRouter returned HTTP 403 `Key limit exceeded` on every retry before an oracle answered. Errors count as neither successes nor model failures. The script-owned transcripts are retained, and there is no claimed `hardened` verdict.

## Why this is Track B

Section 3.1 fixes the allocation objects and strict-preference semantics; Section 3.2 defines `k`-stability and identifies `n`-stability with weak Pareto optimality. Observation 4.2 and Corollary 4.3 give the reference certificate-producing algorithm: construct the improvement graph and run Hopcroft–Karp in `O(sqrt(n) m)` time. It solves 8/8 shipping instances, using 36,422 edge scans in total (4,553 per instance on average) and 0.045371 seconds on the final audit run. Thus a Track A claim would be false.

The generator composes several cyclic perfect matchings and then independently shuffles agent codes, house codes, catalog order, and every preference row. In hidden coordinates `i,j` over `Z_n`, one layer has constant `i+j mod n`. Recognizing the conserved sum lets a solver recover an entire layer in 221 exact modular operations at the shipping preset; without it, the mechanical route operates on a shuffled degree-6 bipartite graph. Theorem 4.6 proves NP-completeness for the different *existence* problem at fixed `0<c<1`; this module deliberately does not misuse that worst-case result as evidence about its generated distribution. The polynomial verification result is the easy regime that determines the Track B label.

## Worked demo

`make_instance(n=5, layer_count=2, scale=3, seed=0)` renders in full as:

```text
HOUSE ALLOCATION: CERTIFY FAILURE OF n-STABILITY

There are 5 agents A0,...,A4.  The objects are 5 better-house
codes B0,...,B4 and 5 private current objects C0,...,C4.
A matching assigns at most one acceptable object to each agent and uses
each object at most once. Preference lists below are strict and run from
best to worst; being unmatched is worse than every listed object.

The displayed current matching M assigns Ai to Ci for every i.  Agent Ai
strictly prefers another matching M' to M exactly when M' assigns Ai an
object appearing to the left of Ci in Ai's preference list.

For this problem, a matching is k-stable when no alternative matching is
strictly preferred by at least k agents. Here k=n, so certify that M is
not n-stable by giving an alternative matching preferred by every agent.

The scalar z attached to each A and B label is instance data in Z_q, with q=15.
All modular arithmetic uses the representatives 0,...,q-1. The B code,
not its scalar z, is what must be written in the answer.

Better-house catalog (catalog order has no significance):
  B0[z=13] B4[z=1] B1[z=4] B2[z=10] B3[z=7]

Strict preference lists (0-indexed agent codes):
  A0[z=10]: B2 > B0 > C0 [current]
  A1[z=1]: B3 > B1 > C1 [current]
  A2[z=7]: B0 > B4 > C2 [current]
  A3[z=4]: B1 > B4 > C3 [current]
  A4[z=13]: B3 > B2 > C4 [current]

Output exactly 5 integers in fixed agent order A0,A1,...,A4.
Entry i is the code j of the better house Bj assigned to Ai. Codes are
0-indexed integers from 0 through 4; order matters by agent, every
code must occur exactly once, and repeats are forbidden.

Give your final answer inside <answer></answer> tags as comma-separated integers.
Example syntax: <answer>2, 0, 1</answer>
Output nothing else inside the tags.
```

The answer `[0, 3, 4, 1, 2]` gives every agent a distinct preferred house, so `verify(inst, answer) == (True, "ok")`. Replacing its last entry by `0` returns `(False, "matching constraint is violated by a repeated house")`. A person can solve this demo on paper by finding either constant-sum layer.

## Difficulty presets

| Preset | Agents / answer atoms | Layers per row | Scalar scale | Status |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 3 | hand-solvable illustration |
| easy | 80 | 4 | 101 | first bare-oracle rung; API-blocked |
| medium | 150 | 5 | 1,009 | locally verified |
| hard | 220 | 6 | 4,001 | `SHIPPING_DIFFICULTY`; locally verified |

Difficulty raises the graph size, decoy crowding, and arithmetic label height. No preset was rejected by a local gate. Shipping at `hard` is provisional because Step 4 could not obtain a scored oracle attempt.

## Gate results

| Gate | Final measured result |
|---|---|
| G1 | 12/12 planted witnesses verify across every preset |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | all 220 entries round-trip through tagged prose; answer is JSON-native |
| G4 | 0/200,000 valid structure-aware uniform-permutation guesses; declared space `220!` |
| G5 | shipping density 0/200,000; demo exactly 2/120; fixed shipping seed costs 3,449 HK edge scans and 0.000372 s |
| G6 | seven attacks × eight seeds, zero successes; Hopcroft–Karp and the compact audit each solve 8/8 as expected |
| G7 | doubled `n=440` instance builds in 0.001477 s and verifies |
| G8 | 100/100 invariance and 100/100 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 771 characters, 193 estimated tokens, 220 atoms, 221 exact operations; within every cap |

The exact machine-readable figures, including all attack names and counters, are in `selftest_report.json`.

## Oracle loop and G9 diagnostics

| Arm | Preset | Seeds attempted | Scored solved/attempts | Result |
|---|---|---|---:|---|
| bare | easy | 67381540, 697888213, 1604392877, 501224963 | 0/0 | four HTTP 403 errors; run aborted |
| structural | hard | 4481046, 685280852, 1739543763, 701997171 | 0/0 | four HTTP 403 errors; run aborted |
| placebo | hard | 837822928, 1351216608, 1845466563, 591153440 | 0/0 | four HTTP 403 errors; run aborted |

The hinted and placebo copies contained only the shipping preset, as required. Since neither arm completed a call, `hinted - placebo` is undefined and supports no conclusion about the claimed invariant. The structural hint names only the conserved-sum invariant; it does not provide a multi-step procedure.

## Use

```python
import gen_2307_03794 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
answer = inst["answer"]
assert g.verify(inst, answer) == (True, "ok")
wire = "<answer>" + ",".join(map(str, answer)) + "</answer>"
assert g.parse_answer(wire) == answer
```

From the repository root, emit records with `bash scripts/emit.sh 2307.03794` after a successful Step 4 run.

## Caveats

Any bipartite-matching implementation makes this family easy, and the conserved-sum shortcut makes it easy once recognized; that is exactly why it is Track B. The zero-hit guess result is for the declared uniform prior over all house-code permutations. It is not an average-case theorem, does not estimate a model's learned prior, and does not imply that only six valid matchings exist. The panel tried row-code extrema, first-listed choices, scalar proximity, a plausible but wrong constant-difference ansatz, deterministic greedy, and 256 randomized greedy restarts. SAT, ILP, and generic constraint solvers were not separately tested because Hopcroft–Karp is the domain-standard method here and already succeeds.

The canonical key removes code permutations, presentation order, coordinate translations, and multiplication by units of `Z_n`; an exotic non-affine isomorphism between two circulant layer sets could still evade it. The answer is close to the 256-atom cap, and the compact route uses 221 of the allowed 300 operations, so this is near the intended no-tool boundary. Most importantly, no multi-vendor difficulty conclusion is justified until the OpenRouter account limit is restored and all three arms are rerun.
