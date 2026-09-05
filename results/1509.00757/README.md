# Radial plane-diameter completion generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT over native face choices |
| Certificate | integer tuple: one plane-graph edge per marked face |
| Intended intuition | constraint propagation |
| Domain essentiality | native |
| Reduction | none |

This module turns [Golovach, Requilé, and Thilikos, *Variants of Plane Diameter Completion*](https://arxiv.org/abs/1509.00757) into a search problem over the paper's own objects.  The solver receives an unweighted plane graph, its marked pentagonal face boundaries, an edge budget, a per-face budget, and a diameter bound.  It must add one radial diagonal in each marked face.  The checker validates each chord against the cyclic face boundary and recomputes the completed graph's diameter by exact breadth-first search.

## Why Track B

Section 1 defines BBFPDC.  The two choices in each marked pentagon and the terminal-distance enforcement mirror Steps (iii*)–(iv*) and the pole argument in the BFPDC half of Theorem 1; Lemmas 6–7 supply the corresponding distance-gadget idea.  A Track A claim would be false here.  Theorem 2 gives an `O(N^3) + 2^(2^(O((kd) log d))) alpha(q)^2 N` FPT algorithm, hence polynomial dependence on graph size for fixed `k,d`, and this deliberately restricted distribution is easier still.

The measured reference method extracts the binary clauses made by the equal-radius sentinels, propagates them along the constraint path, and verifies the result by all-pairs BFS.  At the provisional shipping preset it solved 8/8 instances in a mean 0.444 seconds and 858,334 counted edge/constraint operations.  The compact route notices that neighboring pentagons share one hidden orientation and propagates a single choice, using 63 choices at `n=32`.  That mechanical-versus-compact gap is the Track B claim.

Generation is inverse: it samples one of the two global orientations first, builds symmetric face and sentinel gadgets around it, and only then randomly relabels vertices, rotates/reverses every face, shuffles the input, and adds same-radius decoy sentinels.  It never solves the generated instance.  The complementary orientation is also valid, and `verify` accepts it.

## Worked demo

The `demo` preset with seed 11 renders as follows (the final generic formatting example is omitted here only to save space):

```text
Vertices: 0,...,29.  Root R=19.  Add one radial diagonal in each face; d=6.
Existing edges:
2-13 9-13 5-23 1-8 13-23 3-26 19-22 0-19 8-10 10-20
16-25 10-14 11-19 19-29 8-16 9-19 7-23 17-29 7-26 1-19
26-28 7-21 14-24 0-10 15-20 7-14 19-21 17-27 6-12 16-28
8-20 7-28 12-22 11-28 2-4 6-28 6-18 2-12 12-13
F1: [19, 9, 13, 12, 22]
F2: [19, 0, 10, 8, 1]
F3: [11, 28, 7, 21, 19]
Output a JSON list of three canonical [u,v] pairs in F1,F2,F3 order.
```

The planted witness is `[[12,19],[8,19],[7,19]]`; `verify` returns `(True, "ok")`.  Reversing the first serialized edge to `[19,12]` returns `(False, "entry 1 is not in canonical u<v order")`.  A person can solve this smallest setting on paper by tracing the length-one terminal paths and testing the two orientations.

## Difficulty presets

| Preset | Faces `n` | Decoy sentinels | Tail length | Candidate space | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 0 | 1 | 2^3 | hand example |
| easy | 32 | 16 | 3 | 2^32 | provisional shipping preset |
| medium | 40 | 40 | 3 | 2^40 | local gates pass |
| hard | 48 | 96 | 3 | 2^48 | local gates pass |

`escalate()` first adds symmetric decoy sentinels at fixed `n`, growing the haystack without lengthening the answer.  Only after eight decoys per face does it increase tail length.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses across every preset |
| G2 | pass | empty/drop/swap/duplicate/out-of-range all rejected with 5 distinct reasons |
| G3 | pass | tagged JSON round-trip succeeds; garbage returns `None` |
| G4 | pass | 0/200,000 uniform structured guesses at shipping |
| G5 | pass | demo has exactly 2/8 solutions; shipping has 2 structural solutions in 2^32; restart baseline 0 successful seeds in 2,048 restarts, 0.188 s |
| G6 | pass | four attacks each 0/8; reference method 8/8 as expected |
| G7 | pass | doubled `n=64` instance builds and verifies; space grows to 2^64 |
| G8 | pass | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst observed over 500 seeds: 383 characters, 96 estimated tokens, 64 atoms, 63 intended-route choices |

The G4 prior is uniform over the two radial diagonals that remain in each face after reading the stated radial restriction.  It does not model a solver that has recognized the global orientation invariant; indeed, that recognition is the intended shortcut.  The zero observed hits is therefore evidence about blind structured guessing, not a complexity lower bound.

## Oracle loop and G9 arms

The required script-owned calls are currently blocked by the configured OpenRouter key: all redraws returned HTTP 403 `Key limit exceeded (total limit)`.  The harness correctly counted none of these as model failures.  These rows must be replaced by successful script runs before submission.

| Run | Preset | Scored attempts | Solved | Current result |
|---|---|---:|---:|---|
| bare hardening | easy | 0 | 0 | infrastructure-blocked, not a hardness verdict |
| structural hint | easy | 0 | 0 | not run |
| placebo hint | easy | 0 | 0 | not run |

Thus `hinted - placebo` is not yet measurable.  The structural hint names only the equal-radius orientation invariant; it does not give the propagation procedure.

## Use

```python
import random
import gen_1509_00757 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
text = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
assert g.search_space(inst) == 2 ** params["n"]
```

From the repository root, emit samples with `bash scripts/emit.sh 1509.00757 20` after the oracle evidence is complete.

## Caveats

This is a radial-certificate restriction of BBFPDC, not a claim that the generated distribution inherits Theorem 1's NP-hardness.  Explicitly exposing a consistent clockwise orientation, omitting independent face reflections, or giving the extracted sentinel clauses would make it easy.  The adversary panel checks endpoint degree, sentinel frequency, a clockwise ansatz, and 256 random restarts, but it does not include a general planar dynamic-programming implementation of the paper's very large FPT construction; the exact specialized reference method is stronger on this distribution and is reported instead.  Planarity comes from a chain of wedges sharing the root, with paired noncrossing paths between consecutive wedges; the checker validates the only permitted new embeddings face-by-face rather than independently recognizing planarity of the trusted generated base graph.  Finally, the four-vendor and G9 diagnostics remain an external infrastructure blocker, not evidence that the family is hard.
