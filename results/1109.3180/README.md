# Verified problem generator for *Bisections of graphs*

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | subset sum |
| Certificate form | integer tuple |
| Native objects | a regular graph `K_N` minus disjoint cycles; a balanced vertex bipartition represented by cycle indices |
| Intended intuition | decomposition: residue classes modulo 997 expose four-term additive parallelograms |
| Domain essentiality | native |
| Reduction | none |

## What the family is

This module turns Lee, Loh, and Sudakov's [*Bisections of graphs* (arXiv:1109.3180)](https://arxiv.org/abs/1109.3180) into exact maximum-bisection instances.  An instance specifies a finite simple graph compactly: start with `K_N` and remove the edges of a disjoint union of cycles.  It asks for one side of a bisection with `N^2/4` crossing edges, represented by indices of whole missing cycles.

The representation is exact, not a sampled graph.  Every vertex has degree `N-3`.  A balanced cut has only `N^2/4` cross pairs available, so it reaches the target exactly when none of the removed cycle edges crosses.  Since every removed cycle is connected, a valid side is a union of whole cycles.  `verify` checks the answer's shape, distinct indices, exact half-sum, and exact crossing count using integers only.

Generation is inverse.  For each hidden quartet it samples the four cycle orders

`997u+r, 997(u+d1)+r, 997(u+d2)+r, 997(u+d1+d2)+r`.

The lowest plus highest equals the two middle orders.  The generator randomly chooses either equal-sum pair, then shuffles every cycle.  It knows the witness before the graph exists; the collision audit only excludes unintended extra identities.

## Why Track B, and what is easy

This is not a Track A claim.  Section 1 defines bisection and explains the elementary greedy half-edge baseline.  Section 2 analyzes random paired bisections, and Section 3 proves Theorem 1.3 by maximum matching, ordered pairing, and deterministic greedy splitting.  Those results make the prior-triage proposal—plant a cut at a modest crossing threshold—unsuitable: random or greedy answers would be common.  The generated task instead asks for the exact maximum.

An efficient reference algorithm exists.  It forms all pair sums of the `c` cycle orders, sorts them, and reads off the disjoint repeated-sum collisions in `O(c^2 log c)` exact operations.  At the shipping preset (`c=80`) the final eight-seed run formed 3,160 sums per instance and averaged 43,058 comparison/scan operations and about 0.0016 seconds.  The compact route notices the hidden residue classes: 80 reductions modulo 997 and two additions in each of 20 buckets, 120 exact arithmetic operations total.  The gap—plus the bare/hinted contrast below—is the Track B hardness claim.  Theorem 1.14 is also relevant context: these instances are regular graphs, the paper's own native objects, although the special residue construction is this generator's inverse-generation device rather than a theorem of the paper.

## Worked demo

With `seed=0`, the demo graph has `N=725288`, degree `725285`, target `131510670736`, and four missing cycles:

```text
index: cycle_length
0: 177334
1: 184313
2: 178331
3: 185310
```

The complete rendered statement defines vertices `(i,j)`, deletes consecutive edges inside each listed cycle, requires exactly two zero-based indices, and uses `<answer>...</answer>` JSON tags.  One answer is:

```text
<answer>[1, 2]</answer>
```

Here `184313 + 178331 = 362644 = N/2`, so `verify(inst, [1, 2])` returns `(True, "ok")`.  The corruption `[0, 2]` returns `(False, "listed cycles contain 355665 vertices, not 362644")`.  A person can solve this smallest setting on paper by checking its six pair sums; the huge vertex count is harmless because the graph is represented exactly by four cycle orders.

## Difficulty presets

| Preset | Hidden quartets | Missing cycles | Quotient bits | Answer indices | Compact operations | Reference operations | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 1 | 4 | 8 | 2 | 6 | 28 | hand example |
| easy | 20 | 80 | 28 | 40 | 120 | 43,058 | **ships; bare held 0/3** |
| medium | 32 | 128 | 34 | 64 | 192 | 121,829 | available, not reached |
| hard | 48 | 192 | 40 | 96 | 288 | 296,354 | available, not reached |

Larger `n` means more independently shuffled identities and a larger fixed-cardinality answer space.  After named presets, `escalate` raises coefficient entropy without lengthening the witness.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 16/16 preset-seed instances; compact route also verified |
| G2 corruptions | pass | drop, replacement, duplicate, empty, and out-of-range all rejected with five distinct reasons |
| G3 round trip | pass | tagged and fenced model-style replies recovered; garbage returned `None` |
| G4 guess resistance | pass | 0/200,000; space `107507208733336176461620` |
| G5 density/baseline | pass | shipping density 0/200,000; demo has exactly 2 valid answers; reference 344,464 operations over 8 seeds |
| G6 adversaries | pass | all six attacks 0/8; successful reference 8/8 as Track B requires |
| G7 scale | pass | doubled instance built with 160 cycles and its plant verified |
| G8 canonical key | pass | 80/80 component relabellings, 80 local dihedral edge checks, 120 carried/swap witnesses, 20/20 unrelated keys distinct |
| G9 no-tool cap | pass | 160 chars, 40 estimated tokens, 40 atoms, 120 intended operations |

The six failing attacks were largest-order and smallest-order outliers, a cardinality-aware greedy fill, alternating input indices, the tempting two-smallest choice inside the correct residue buckets, and 256 random restarts.  The random-restart panel performed 2,048 total restarts.  The exact global collision-table reference solved 8/8, as expected for Track B.

## Bare oracle loop

| Preset | Model | Seed | Solved | Result |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 186988848 | no | parseable list, wrong exact half-sum |
| easy | GPT-5.6 Terra | 1871023469 | no | first 40 indices, wrong exact half-sum |
| easy | GPT-5.6 Terra | 1026629632 | no | no witness; incorrectly claimed a one-million vertex-count discrepancy |

The last graph was regenerated and its displayed orders sum exactly to `15593118770650`, the stated value, so that failure is oracle arithmetic rather than a renderer bug.  The script verdict is `hardened` at `easy` with zero escalations.

## G9 arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0 / 3 | held |
| structural | 3 / 3 | the invariant makes the route executable |
| placebo | 0 / 3 | a neutral added sentence did not help |

`hinted - placebo = 1.0`.  The hint therefore carries real structural information, and the difficulty is finding the modulo-997 decomposition.  Its `too_easy` hinted verdict is diagnostic, not a shipping gate.  One placebo provider exhausted its response without an answer; the other two produced invalid half-sums.  The answer and route remain comfortably inside the G9 caps.

## Use

```python
import gen_1109_3180 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
candidate = g.parse_answer(f"<answer>{inst['answer']}</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit shipping instances with:

```bash
scripts/emit.sh 1109.3180 20 easy
```

The module uses only the standard library; `gvlib` is unnecessary for these integer identities.

## Caveats

This is a deliberately structured subclass, not evidence that the paper's general graph-bisection distribution is hard.  It becomes easy for a tool that computes residues modulo 997 or all pair sums, and the G9 hint makes all three tested models solve it.  The 0/200,000 guess result is only for a uniform prior over fixed-size cycle-index subsets; it does not model a solver that notices residues, pair-sum collisions, or the compact graph representation.

The graph can have trillions of vertices, but it is an exact succinct graph, and both posing and checking use its native cycle-complement representation.  I did not materialize its adjacency matrix or run an SDP/ILP, because that would expand a succinct instance enormously; the exact collision-table algorithm already solves every generated instance and is stronger for this representation.  Spectral ranking by degree has no signal because the graph is regular, but a symbolic analysis of the complement exposes the supplied cycle orders immediately.  Finally, the collision filter costs quadratic generation time and is intended only to remove accidental alternative identities; the planted certificate is chosen before that audit and never recovered by it.
