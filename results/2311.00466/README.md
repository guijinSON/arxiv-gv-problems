# Verified generator for arXiv:2311.00466

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer tuple of hyperedge IDs |
| Intended intuition | invariant: constant endpoint quotient modulo `q` |
| Domain essentiality | native |
| Reduction | none |

## What the family is

This module turns Sylvain Guillemot's [*Parameterized covering in semi-ladder-free hypergraphs*](https://arxiv.org/abs/2311.00466) into exact Set Cover instances. There are equally many left and right vertices, and every hyperedge contains one of each. The solver must return `n` edge IDs covering every vertex; this is necessarily a perfect matching. Verification is a linear exact incidence check and accepts any valid cover, never merely the stored one.

The objects really are the paper's hypergraphs. Section 2, Theorem 1 says that a hypergraph is `d`-flat exactly when its intersection closure has no inclusion chain longer than `d+1`. Here the closure contains only the universe, 2-edges, singleton intersections, and the empty set, so every instance is 2-flat (equivalently, 3-semi-ladder-free). Generation samples multiplicative-coset matchings first and then shuffles their union; each multiplier is a bijection and hence a known certificate. No matching algorithm is used to produce `inst["answer"]`, and all multiplier layers have the same distribution.

## Why this is Track B

Track A would be false. The paper's Theorem 3 solves `d`-Flat Set Cover in `O(k^(dk) k ||H||)`, and Theorem 4 gives an `O(n^(2d+2))` kernelization. This generator is in an easier 2-uniform bipartite regime, where Hopcroft–Karp finds a cover in `O(|E| sqrt(|V|))`. At the current shipping preset (`n=151`, degree 14), the reference implementation solved 8/8 instances, averaging 5,008.5 edge scans and about 0.0007 seconds.

The compact route is shorter but has to be noticed and executed without tools. Vertex labels lie in `GF(q)^*`. Along any generated matching, `right_value / left_value (mod q)` is constant. Use an edge incident to the displayed anchor and its supplied inverse to obtain one multiplier, then identify the corresponding edge at every left vertex. This takes 152 exact modular multiplications at shipping size, versus mechanical matching over 2,114 shuffled edges. Theorem 7's compression lower bound is for fixed `d >= 3`; it is not average-case hardness and is not claimed here.

## Worked demo

`make_instance(n=7, q=29, degree=2, seed=3)` renders the following complete instance:

```text
Perfect cover in a promised 2-flat hypergraph

The prime modulus is q = 29. Vertex labels below are nonzero
residues modulo q; they are exact labels, not floating-point values.

There are 7 left vertices and 7 right vertices. Every hyperedge
contains exactly one left and one right vertex. A cover is a set of
hyperedges incident to every vertex. Find a cover of exactly
7 hyperedges. Since there are 14 vertices and each edge has two
endpoints, a valid answer necessarily uses every left vertex and every
right vertex exactly once.

Edge IDs and vertex indices are 0-based. Order of chosen edge IDs does
not matter; repeats are forbidden. The only allowed edge IDs are those
listed below.

The hypergraph is promised to be 2-flat: the intersection closure of
its edge family has no strict inclusion chain longer than three.
It is also promised to have a cover of the required size.

Field-labelled vertices:
left_index:value = 0:10, 1:8, 2:15, 3:27, 4:18, 5:12, 6:26
right_index:value = 0:14, 1:2, 2:3, 3:21, 4:17, 5:19, 6:11

One exact arithmetic datum is supplied for convenience:
left value 8 (index 1) has multiplicative inverse 11 modulo q.

Hyperedges (edge_id: left_index -> right_index):
0: 5 -> 3
1: 0 -> 2
2: 6 -> 3
3: 1 -> 0
4: 0 -> 4
5: 6 -> 1
6: 3 -> 0
7: 4 -> 5
8: 3 -> 6
9: 4 -> 4
10: 2 -> 5
11: 1 -> 1
12: 2 -> 6
13: 5 -> 2

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 7 distinct 0-based edge IDs.
Syntax example only: <answer>[3,17,42]</answer> (use the required length).
Output nothing else inside the tags.
```

One answer is `<answer>[2,4,6,7,11,12,13]</answer>`. Every selected edge has quotient 22 modulo 29. `verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last edge returns `(False, "wrong edge count: expected 7, got 6")`. The demo has 128 structure-aware candidates and exactly two covers, and is genuinely hand-solvable.

## Difficulty presets

| Preset | n | Degree | Edges | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 14 | 7 | hand example; never shipped |
| easy | 77 | 10 | 770 | 77 | hardening ladder |
| medium | 151 | 14 | 2,114 | 151 | **current shipping candidate** |
| hard | 231 | 20 | 4,620 | 231 | reserved escalation rung |

`escalate()` first increases degree at fixed `n`, growing the decoy haystack without lengthening the answer. The next available subgroup size after the capped regime would make the answer exceed 256 atoms, so it reports `cap_bound` rather than falsely rejecting the paper.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted certificates verified; every answer JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged fenced model-style answer parsed; 4/4 malformed strings rejected |
| G4 | 0/200,000 structure-aware guesses; candidate language `14^151` (575 bits) |
| G5 | shipping density 0/200,000; demo exactly 2/128; 256-restart attack failed in about 0.034 s |
| G6 | four attacks each 0/8; Hopcroft–Karp 8/8 as expected |
| G7 | doubled `n=302` instance built and verified; candidate-space bits doubled |
| G8 | 60/60 composed relabellings preserved key and carried witness; 20/20 unrelated keys distinct |
| G9(c) | 693 chars, 174 estimated tokens, 151 atoms; intended route 152 operations |

## Oracle loop and G9 diagnostic

The mandatory bare loop was invoked, but OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw. The official harness correctly stopped without a hardness verdict. The error records in `llm_loop_transcript.jsonl` are retained rather than rewritten. Consequently the three G9 oracle arms have not yet been run and this directory is **not submission-ready** until account capacity is restored.

| Arm | Solved / attempts | Status |
|---|---:|---|
| bare | — | externally blocked before a valid attempt |
| structural hint | — | not run |
| placebo hint | — | not run |

The local G9(c) cap is passed. No conclusion about hinted-minus-placebo is possible without valid oracle calls.

## Use

```python
from gen_2311_00466 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["medium"])
prompt = render(inst)
candidate = parse_answer(model_reply)
ok, reason = verify(inst, candidate)
```

From the repository root, emit after hardening succeeds with:

```bash
bash scripts/emit.sh 2311.00466
```

## Caveats

This is not a complexity-theoretic or average-case hardness claim: polynomial matching solves every instance in milliseconds, and a solver that notices the field quotient and can perform many exact 31-bit modular products should also solve it. The 0/200,000 estimate uses the declared prior—one uniformly random incident edge per left vertex—and says nothing about matching, quotient grouping, or another informed strategy. The panel tests edge-ID/degree outliers, smallest-right greedy matching, 256 random restarts, and a smallest-integer-gap ansatz; it does not test SAT/ILP encodings because Hopcroft–Karp strictly matches the generated subclass. The canonical key is an exact invariant using incidence intersection profiles and normalized multiplier layers, but it is not a complete bipartite graph-isomorphism canonical form. Finally, the finite-field labels add exploitable structure to a special native subclass; they are not part of the paper's compression lower-bound construction.
