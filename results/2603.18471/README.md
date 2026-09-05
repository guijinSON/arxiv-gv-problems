# arXiv 2603.18471 — affine kidney-exchange cycle factors

**Status: parked (`cap_bound`), not shipped.** The local correctness gates pass,
but the required oracle loop solved every tested level. Under the benchmark
contract this is not a rejection of the paper and no preset is claimed to be
hardened.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate form | exact symbolic affine-map word |
| Intuition | invariant: normalized local anchors expose a shared fixed point |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The source is Tian and Xiao, [*A Faster Deterministic Algorithm for Kidney
Exchange via Representative Set*](https://arxiv.org/abs/2603.18471), especially
the formal KEP definition in Section 1. The solver receives a directed
compatibility graph represented exactly by affine maps over a prime field. All
vertices are patient-donor pairs, arranged in cyclic layers; there are no
altruists. The answer selects one offered map per layer. If their composition is
the identity, their arcs expand to a full packing of vertex-disjoint cycles that
meets the transplant target. `verify` checks table membership and composes the
maps with exact modular arithmetic, so no search or numerical approximation is
part of grading.

This is native KEP data, not a graph reduction of a different mathematical
object: the implicit graph, cycle bound, target, and packing witness are exactly
the objects in the paper. The affine tables are a compact exact representation
of the graph's complete arc set.

## Why Track B, and why it is parked

The paper itself rules out a Track A claim. Theorem 1 deterministically solves
general KEP in `O*(6.855^t)` time; Theorem 2 gives an `O*(2^|V|)` dynamic program,
and Theorem 3 gives randomized `O*(4^t)` color coding. In this promised affine
subfamily, a more relevant mechanical algorithm stores all affine normal forms
for half of the word and matches inverse normal forms from the other half. Its
complexity is `O(L n^(ceil(L/2)))` time and `O(n^floor(L/2))` memory. At hard seed
2024 it used 272,482 composition extensions, 1,365,236 counted field operations,
248,497 stored normal forms, and about 0.18 seconds.

The compact route normalizes each local anchor by its layer offset, intersects
the resulting fixed-point sets, and checks the selected slopes. It costs 259
exact arithmetic operations at the hard preset. This is a real mechanical-to-
compact gap, but the no-tool pool recognized it at every level, including the
`n=14` escalation. Increasing `n` again crosses the 300-operation intended-route
cap under the declared operation model. The harness therefore returned
`cap_bound`; the family is retained for audit but does not ship.

The easy regimes from the paper are explicit here. The target `t=pL` grows with
the instance, so the FPT parameter is not held small. Also `l_c=L<t`, putting the
family in Lemma 3's bounded-packing regime rather than the large-bound case that
Section 3 first dispatches with k-Path/Long Directed Cycle routines. Section 5
specifically leaves faster algorithms for small constant length bounds as an
open practical direction; this generator's stronger affine promise is disclosed
instead of being mistaken for general KEP hardness.

## Worked demo (seed 7)

This is the complete rendered demo statement; a person can solve it on paper by
adding each anchor to its layer offset modulo 101 and finding the value common to
all four layers.

```text
Kidney exchange: certify a full bounded-cycle packing

All arithmetic below is modulo the prime p=101. The directed compatibility
graph has 4 layers. Its vertices are pairs (i,x), where i is in 0..3 and x is in
0..100. Every vertex is a patient-donor pair; there are no altruistic donors.
Paths are forbidden (path limit 0), the cycle limit is 4 edges, and the target is
404 transplant edges.

For a displayed pair [q,a] in layer i and every x, the complete arc set contains
  (i,x) -> ((i+1) mod 4, y)
where
  y = q + offset[i] - offset[(i+1) mod 4] + a*(x-q) (mod 101).
No other arcs exist.

Layer 0, offset 19: [11,9] [90,80] [22,66]
Layer 1, offset 50: [58,69] [23,30] [92,70]
Layer 2, offset 83: [93,13] [99,6] [59,14]
Layer 3, offset 6:  [0,59] [22,57] [35,48]

Select exactly one displayed pair from every layer so that following the four
selected affine maps returns every layer-0 residue x to itself. Return one JSON
object with sole key "maps" and records {"layer", "anchor", "slope"} for all
layers 0..3. Give it inside <answer></answer> tags and put nothing else inside.
```

The certificate is:

```json
{"maps":[{"layer":0,"anchor":22,"slope":66},{"layer":1,"anchor":92,"slope":70},{"layer":2,"anchor":59,"slope":14},{"layer":3,"anchor":35,"slope":48}]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the first slope
by 101 returns `(False, "record 0 has an out-of-range affine parameter")`.

## Difficulty and measurements

`SHIPPING_DIFFICULTY="hard"` remains the provisional interface preset used by
the local gates; it is **not** a shipping claim after the `cap_bound` verdict.

| Preset | Choices/layer `n` | Layers `L` | Prime `p` | Word space | Oracle result |
|---|---:|---:|---:|---:|---|
| demo | 3 | 4 | 101 | 81 | hand-scale, skipped by harness |
| easy | 5 | 8 | 1009 | 390,625 | solved 3/3 |
| medium | 8 | 10 | 5003 | 1,073,741,824 | solved 3/3 |
| hard | 12 | 10 | 10007 | 61,917,364,224 | solved 3/3 |
| escalated | 14 | 10 | 10007 | 289,254,654,976 | solved 3/3; then `cap_bound` |

| Gate | Result |
|---|---|
| G1 | 12/12 planted certificates verify; 12/12 JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose + fenced JSON round-trips; garbage returns `None` |
| G4 | 0 hits / 200,000 structure-aware random words |
| G5 | demo has exactly 1 valid word of 81; hard sampled density 0/200,000; baseline 1,365,236 field operations |
| G6 | four attacks each 0/8; reference meet-in-the-middle 8/8; fixed-point shortcut 8/8 as expected |
| G7 | doubling `n` from 12 to 24 raises the word space from 61,917,364,224 to 63,403,380,965,376 and still verifies |
| G8 | 80/80 relabelling invariance checks and 80/80 carried witnesses pass; 20/20 unrelated keys distinct |
| G9(c) | 399 characters, about 100 tokens, 30 atomic values, 259 intended operations |

## Oracle loop

Every oracle answer parsed and verified. The transcript contains two available
models from two vendors, sampled afresh by the harness.

| Preset | Seeds | Solved | Verification |
|---|---|---:|---|
| easy | 47547995, 1440594885, 1899920720 | 3/3 | all `ok` |
| medium | 409908250, 1812099191, 799966105 | 3/3 | all `ok` |
| hard | 1278597618, 1389830452, 1793977207 | 3/3 | all `ok` |
| escalated | 1236766900, 1108652347, 992148780 | 3/3 | all `ok` |

## G9 diagnostic arms

There is no hardened shipping preset, so the contract's instruction to stop on
`cap_bound` was followed. The hard bare arm is the corresponding three calls
from the main loop; hinted and placebo runs were not purchased and therefore no
`g9_*_transcript.jsonl` files are claimed.

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 3/3 at provisional hard | the invariant was already discoverable |
| structural hint | 0/0, not run | no diagnostic inference |
| placebo hint | 0/0, not run | no diagnostic inference |

Hinted-minus-placebo is undefined with zero attempts (stored as 0.0 only because
the module schema requires a numeric field). The answer-size measurements are
399 characters / 100 estimated tokens / 30 atomic values, and the intended route
uses 259 exact operations.

## Use

```python
from gen_2603_18471 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer('<answer>{"maps":[]}</answer>')
print(verify(inst, candidate))
print(verify(inst, inst["answer"]))
```

From the repository root, local sample emission is:

```bash
bash scripts/emit.sh 2603.18471 20
```

Do not submit those samples as a hardened release while `.meta.json` records
`cap_bound`.

## Caveats

- The random-guess result is for the honest statement-aware prior: one uniformly
  chosen offered map per layer. It does not model a solver that notices the
  repeated normalized fixed point; the oracle results show that such a solver is
  effective.
- The affine promise is much easier than general KEP and is deliberately a Track
  B family. The paper's representative-set algorithm, an ILP model, SAT encoding,
  and a full explicit-graph cycle-packing solver were not implemented.
- The canonical key covers map reordering, cyclic layer renumbering, global affine
  coordinate relabelling, and their compositions. Full isomorphism of the implicit
  directed graphs is not attempted; the key is the strongest cheap invariant used.
- The earlier layered length-two-chain draft was even easier: two Hopcroft-Karp
  matchings took only 3,361 edge scans and the oracle solved its hard rung. It is
  retained as `rejected_gen_2603_18471.py` for audit, but no `REJECTED.md` exists
  because the paper itself is parked rather than rejected.
