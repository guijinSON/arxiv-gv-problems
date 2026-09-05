# Verified generator for arXiv:1605.08905

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT (graph colouring) |
| Certificate form | integer tuple, serialized as a colour word |
| Intended intuition | constraint propagation through overlapping dipath cliques |
| Domain essentiality | licensed reduction |
| Reduction | paper-central, Section 4, Lemma 22 |

## What the problem is

This module implements one family from Duffy, MacGillivray, and Sopena,
[“A Study of k-dipath Colourings of Oriented Graphs”](https://arxiv.org/abs/1605.08905).
The solver receives an acyclic oriented graph made from the paper's five-vertex
`H_{3,4}` gadgets and must return a normalized 3-dipath 4-colouring.  A word of
one port colour per gadget is a compact witness: the checker expands its three
internal colours deterministically, builds the entire oriented graph, and uses
exact breadth-first searches to check every directed-path endpoint at distance
at most three.  It never reads the planted answer.

Generation is inverse, not a solve.  The generator first samples four hidden
equal colour classes.  Edge-disjoint matchings and colour-preserving degree
switches create a regular source graph with no within-class edge.  It then
randomizes labels and an acyclic orientation and carries the held colouring
through exactly the transformation of Lemma 22.

## Why the Track-A claim is plausible

Theorem 23 proves NP-completeness for fixed `t > k >= 3`, even when the oriented
input has directed girth at least `k+1`.  This family uses `k=3`, `t=4`, and is
acyclic (infinite directed girth).  That theorem is only worst-case evidence;
the distributional evidence is the measured panel below.  At shipping size,
exact DSATUR/DPLL exhausted 1,000,001 nodes in 31.041302 seconds without
finding a colouring.  The
generator deliberately avoids the same theorem's polynomial boundary `t <= k`.
It also avoids the `t <= 2` easy regime in Theorem 24 and the special cases in
Theorem 19.

All public source vertices have degree nine.  Random relabelling removes an
ordering signal, while the switches erase the exposed perfect-matching layers
and the exact per-class neighbour counts that would otherwise give a planted
spectral eigenvector.  Plants and decoys are not separate populations: every
edge is sampled under the same hidden-partition rule.

## Worked demo

For `make_instance(n=8, regular_degree=3, switch_rounds=0, seed=31415)`, the
complete additional-arc list is:

```text
O4->I3  O7->I6  O7->I0  O5->I1  O6->I0  O7->I5
O5->I0  O4->I2  O2->I1  O3->I2  O3->I6  O4->I1
```

Every gadget `i=0,...,7` also contains exactly
`Oi -> Si -> Ti -> Pi -> Ii`; there are no other arcs.  The output contract asks
for eight symbols in `1..4`, fixes `w[0]=1` and `w[5]=2`, assigns `w[i]` to both
ports, and puts the other three colours on `Si,Ti,Pi` in increasing order.

```python
>>> inst["answer"]
'14321243'
>>> verify(inst, '14321243')
(True, 'ok')
>>> verify(inst, '14311243')
(False, 'additional arc O4->I3 has equal port colour 1')
```

This demo is genuinely hand-solvable: it is just an eight-gadget constraint
graph after noticing the two overlapping four-vertex dipath cliques.

## Difficulty presets

| Preset | Port gadgets | Oriented vertices | Degree | Switch rounds | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 40 | 3 | 0 | hand example |
| easy | 252 | 1,260 | 9 | 50 | **shipping; oracle held** |
| medium | 252 | 1,260 | 9 | 75 | reserve rung |
| hard | 252 | 1,260 | 9 | 100 | reserve rung |

`escalate()` increases switching at fixed answer length up to 200 rounds.  Only
after that axis is exhausted does it report `cap_bound`; increasing `n` would
push the witness past the 256-element output cap.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted instances verified; answers JSON-round-trip |
| G2 | empty, dropped, swapped, duplicated-across-arc, and out-of-range corruptions all rejected with distinct reasons |
| G3 | realistic prose/fence/tag response round-tripped |
| G4 | 0 valid in 200,000 uniform normalized colour words; language size `4^250` |
| G5 | shipping density 0/200,000; demo has exactly 112 normalized witnesses; DSATUR used 1,000,001 nodes and 31.041302 s without solving |
| G6 | five attacks, 0/8 successes each; detailed operation counts are in `selftest_report.json` |
| G7 | a doubled `n=504` instance (2,520 oriented vertices) built and verified |
| G8 | 60 relabelling/order/orientation compositions invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9 | 254 serialized characters, conservative 254-token bound, 252 atoms, 252 intended post-insight assignments |

## Oracle loop and G9 arms

The bare harness held the shipping rung immediately:

| Preset | Model | Seed | Solved | Checker result |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 405355966 | no | equal colours across an additional arc |
| easy | Claude Sonnet 5 | 449023812 | no | wrong word length |
| easy | Gemini 3.1 Pro Preview | 1907030281 | no | wrong normalized anchor colour |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`.  Thus the one-sentence structural hint did not
buy the oracle pool a verified answer.  This also says the shipping challenge
is dominated by the residual four-colouring search rather than by merely
recognizing the gadget equality.  One placebo attempt exhausted its response
budget; the other two placebo calls produced a malformed word and no parseable
tagged witness.

## Use

```python
from gen_1605_08905 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 1605.08905 20
```

## Caveats

Theorem 23 does **not** prove that this planted regular distribution is hard.
The zero-hit density estimate is relative to uniform words with the two stated
colour symmetries fixed; it does not model a learned or solver-guided prior.
The canonical key is a strong degree/triangle/common-neighbour invariant, not a
complete graph-isomorphism canonizer, although all tested relabellings preserve
it and all 20 unrelated trials differed.

Most importantly, larger experiments found partial heuristic vulnerability:
twenty long 200,000-step min-conflicts restarts solved 1/8 audit seeds from
random starts, and the same budget after a spectral initialization solved 2/8,
after millions of updates.  The gated 256-by-5,000 restart attack remained 0/8,
as did direct non-backtracking spectral clustering and the bounded exact
solver.  No industrial SAT/CP/ILP package, SDP relaxation, or search beyond the
reported budgets was run.  Dense instances become easier (the partition signal
strengthens), and sparse ones may acquire many alternative colourings, so the
degree-nine window is load-bearing rather than a general hardness theorem.
