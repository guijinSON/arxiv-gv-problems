# Verified problem generator for arXiv:2201.03220

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: a canonical vertex subset |
| Intended intuition | constraint propagation through a near-saturated packing whose local edge statistics are tied |
| Domain essentiality | native; no reduction |

## Problem and trust model

This module instantiates the size-k search form of Maximum Induced Matching from Hoi, Sabili, and Stephan, [*An Exact Algorithm for finding Maximum Induced Matching in Subcubic Graphs*](https://arxiv.org/abs/2201.03220). The solver receives a connected cubic graph of girth at least five and must return exactly s vertices whose induced subgraph has degree one at every vertex. The checker only validates the submitted labels and recounts induced degrees, so it accepts every valid witness and never reads the planted answer.

Generation is inverse. A set S is sampled first and paired internally. Every vertex of S then receives two random neighbors outside S; unused outside stubs are paired. A configuration is retained only if it is simple, connected, cubic, and has no triangle or 4-cycle. A uniform vertex relabeling and shuffled edge list hide the construction order. The retained S therefore verifies by construction, without solving the generated graph.

## Why Track A

Section 1 gives the exact definition, cites NP-hardness already for planar 3-regular graphs, and lists polynomial-time classes such as trees, interval graphs, chordal graphs, and circular-arc graphs. The generated graphs are connected cubic graphs with cycles of length at least five, so they avoid the tree/low-degree simplifications and are not deliberately sampled from any listed easy class. Theorem 4 gives the older Maximum-Independent-Set reduction with O(1.3139^n) time. Section 4 and Theorem 5 give the paper's polynomial-space O(1.2630^n) exact algorithm—not a polynomial certificate-producing method.

That worst-case result does **not** establish hardness for this planted distribution. The distributional evidence is measured: on eight fixed shipping seeds, all local, greedy, restart, spectral, and exact line-graph-square attacks failed. The strongest implementation reached its 1,000,000-node cap on every seed. This is an empirical Track A claim, not an average-case theorem.

An earlier n=80 rung was rejected even though the oracle failed it: a 256-restart heuristic solved 1/8 audit seeds and the exact attack solved another. The ladder was moved upward before the final hardening run.

## Worked demo

The hand-scale `demo` instance at seed 0 has vertices 0 through 9, asks for six vertices, and has these edges:

```text
4-5  4-6  1-2  3-8  5-8
3-6  3-9  0-7  0-4  1-7
7-8  2-5  2-9  0-9  1-6
```

One answer is `<answer>[0, 2, 3, 5, 6, 7]</answer>`. It gives `verify(...) == (True, "ok")`. Dropping the final label gives `(False, "wrong number of vertices: expected 6, got 5")`. Exact enumeration finds 5 valid answers among 210 canonical six-vertex subsets. A person can solve this demo on paper by pairing the selected vertices and checking that no cross-edge remains; the larger presets are not intended for manual enumeration.

## Difficulty presets

| Preset | Vertices | Selected vertices | Matching edges | Status |
|---|---:|---:|---:|---|
| demo | 10 | 6 | 3 | hand example; skipped by hardening |
| easy | 120 | 68 | 34 | **ships; attack-clean and oracle-hardened** |
| medium | 160 | 92 | 46 | available escalation |
| hard | 200 | 116 | 58 | available escalation |

`escalate()` raises both ambient size and the planted fraction toward the cubic stub-capacity boundary. It reports `cap_bound` before the 256-atom output limit would be exceeded.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 16/16 preset–seed checks |
| G2 corruption | pass | 5/5 rejected with five distinct reasons |
| G3 round trip | pass | prose + fenced tagged JSON recovered exactly |
| G4 guessing | pass | 0/200,000 uniform size-68 subsets; language size 33,441,638,668,669,082,660,738,803,413,858,990 |
| G5 density/cost | pass | shipping sampled density 0; demo exact count 5/210; exact baseline 8,000,008 nodes and 20.09 s total |
| G6 adversaries | pass | every one of five attacks scored 0/8 |
| G7 scaling | pass | doubled instance n=240; candidate-space bit length 115 → 233 |
| G8 canonical key | pass | 60 invariance and 80 semantic checks; 20/20 unrelated keys distinct |
| G9 suitability | pass | 211 characters, about 53 tokens, 68 atoms, 204 adjacency inspections |

G6's randomized restarts found at most 31–32 edges against the 34-edge target. The exact domain attack is target-size MIS branch-and-bound on the Cameron line-graph-square conflict graph; each of eight runs stopped at 1,000,001 visited nodes without a witness.

## Bare oracle loop

The actual configured pool contained two vendors/models, and the harness redrew from it per call. These calls used the same parameters but preceded a final correction to the triangle-rejection predicate, so their seeds do not reproduce the exact current prompts. They are retained as historical hardening evidence, not represented as a completed oracle replay of the corrected generator.

| Model | Seed | Solved | Recorded reason |
|---|---:|---|---|
| google/gemini-3.8-flash | 1,145,262,915 | no | empty length-limited response; no parsed answer |
| openai/gpt-5.6-terra | 1,279,272,625 | no | parsed set had a vertex of induced degree 2 |
| openai/gpt-5.6-terra | 1,488,597,861 | no | parsed 67 labels instead of 68 |

Verdict: `hardened` at `easy`, with no escalation.

## G9 diagnostic arms

| Arm | Solved / scored attempts | Note |
|---|---:|---|
| bare | 0/3 | shipping transcript |
| structural hint | 0/3 | `hardened` |
| placebo hint | 0/2 | third slot could not be scored after four HTTP 403 key-limit redraws |

Hinted minus placebo is 0.0 on the available scored attempts. The structural hint bought no measured improvement, so these data do not show that the claimed constraint-propagation intuition helps the tested models. The incomplete placebo arm is preserved rather than converting API failures into oracle failures. G9 is diagnostic; the size/effort caps are the gated portion.

## Use

```python
import random
import gen_2201_03220 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + str(inst["answer"]).replace("'", '"') + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) > 10**30
random_guess = g.random_candidate(inst, random.Random(1))
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2201.03220
```

## Caveats

- The answer certifies a requested size-k induced matching, not global optimality. This is the witness-producing decision/search form of the paper's maximization problem.
- NP-hardness of cubic MIM does not imply this inverse-generated distribution is hard. G4 measures a uniform fixed-cardinality prior; a construction-aware prior could have much higher success probability.
- The “exact” attack is a capped generic line-graph-square brancher, not a complete implementation of the paper's Monien–Preis bisection and every Section 4 simplification rule. It demonstrates one million failed branch nodes, not a lower bound.
- The spectral probe is deterministic power iteration toward the smallest adjacency direction. Nonbacktracking spectra, belief propagation, SAT/ILP encodings, SDP relaxations, and learned attacks were not run.
- Girth equalizes radius-two conflict counts, but it does not make planted and non-planted edges identical under every higher-order statistic.
- `canonical_key` is a strong distance-histogram plus color-refinement invariant, not a complete cubic-graph isomorphism algorithm; adversarial non-isomorphic collisions are possible.
- The bare oracle evidence includes one empty length-limited response, and the available environment used a two-model pool. The placebo arm is only 0/2 because the OpenRouter key hit its total limit before a third scored attempt.
- The triangle-filter bug was discovered after those calls. All local gates were rerun on the corrected graph distribution, but the exhausted OpenRouter key prevented an exact oracle replay. A fresh funded run of all three arms remains required before submission.

The family becomes easy if the latent selected class can be recovered from a stronger global statistic or if a more capable exact/constraint solver crosses the planted boundary. Those are the first follow-up attacks to run before treating this construction as settled.
