# arXiv:1509.08807 — verified P3-free Edge Deletion generator

| profile field | value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | matrix certificate |
| Intended intuition | invariant: compare coordinate-difference spans inside maximal cliques |
| Domain essentiality | native; no reduction |

## What the family asks

The source is [Aravind, Sandeep, and Sivadasan, *Parameterized Lower Bounds and Dichotomy Results for the NP-completeness of H-free Edge Modification Problems*](https://arxiv.org/abs/1509.08807).  The selected native problem is **P3-free Edge Deletion**, also called Cluster Deletion.  An induced P3 is a three-vertex graph with exactly two edges; a graph is P3-free precisely when all connected components are cliques.

The solver receives the complete adjacency lists of a graph and a four-dimensional coordinate over a displayed prime field for every vertex.  Its answer is a full-rank 2-by-4 matrix.  The matrix row span partitions the vertices into coordinate cosets; every graph edge crossing between cosets is deleted.  `verify` uses exact modular row reduction, counts those deletions, and checks that every retained connected component is a clique.  It accepts every valid matrix in the declared bounded language and never reads the planted answer.

Generation is inverse.  The graph is the line graph of a regular bipartite graph, whose edges are the disjoint union of its left-star and right-star clique factors.  Either factor is a known deletion witness.  Random labels and an invertible affine map turn the two factors into two hidden complementary planes in `F_p^4`; the generator carries one plane through that map.

## Why Track B is honest

Section 2 fixes the edge-modification definition.  Proposition 2.4(i) identifies the easy deletion boundary (patterns with at most one edge).  Proposition 4.1(i) states that P3-free Edge Deletion is NP-complete and has no `2^{o(k)} |G|^{O(1)}` algorithm under ETH; Theorem 4.14 gives the full deletion dichotomy.  The introduction also notes Cai's FPT algorithm, so the generated budget grows linearly rather than remaining a small parameter.

That worst-case result is **not** claimed for this distribution.  A Lehot/Roussopoulos-style line-graph star reconstruction followed by modular basis extraction solves the promise family in `O(|V|+|E|)` for fixed degree and dimension.  At the current easy shipping candidate it uses 1,952 counted operations and about 0.00033 seconds in CPython (the report contains the fresh timing).  The compact route, once the invariant is noticed, finds one four-vertex star clique and subtracts its coordinates to get two independent difference vectors; its conservative bound is 76 exact operations.  Without that recognition, even the polynomial mechanical scan is too long to carry out in-context by hand.

## Worked demo (`seed=0`)

This is the full nine-vertex demo (field modulus 127, deletion budget 9):

```text
coordinates
0: 107 40 121 58
1: 109 40 56 78
2: 108 40 22 67
3: 108 22 20 109
4: 109 6 82 45
5: 107 6 20 25
6: 107 22 119 100
7: 108 6 48 34
8: 109 22 54 120

adjacency
0: 1 2 5 6
1: 0 2 4 8
2: 0 1 3 7
3: 2 6 7 8
4: 1 5 7 8
5: 0 4 6 7
6: 0 3 5 8
7: 2 3 4 5
8: 1 3 4 6
```

One answer is `{"dimension":2,"basis":[[1,0,1,0],[0,0,3,1]]}`.  `verify` returns `(True, "ok")`.  Dropping its second row returns `(False, "wrong row count: basis must have exactly two rows")`.  A person can solve this demo on paper: vertices 0, 1, and 2 form a visible star clique, and two independent coordinate differences inside such a clique span a valid plane.

## Difficulty presets

Here `n` is the size of each side of the hidden bipartite root; the displayed graph has `n*degree` vertices.  The answer always has two rows and eight field entries.

| preset | `n` | degree | field bits | graph vertices | budget | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 3 | 3 | 7 | 9 | 9 | hand-scale illustration |
| easy | 19 | 4 | 31 | 76 | 114 | current shipping candidate; oracle run pending |
| medium | 31 | 4 | 61 | 124 | local gates pass |
| hard | 61 | 4 | 89 | 244 | local gates pass |

## Gate results

| gate | result |
|---|---|
| G1 | pass: planted answer and JSON round-trip on 16 preset/seed pairs |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: fenced JSON with surrounding prose round-trips; garbage returns `None` |
| G4 | pass: 0/200,000 structure-aware full-rank matrices; exact probability `9.4039548197e-38` |
| G5 | pass locally: exact valid count `42,535,295,766,082,104,863,878,380,214,699,425,792` in a space of `452,312,846,898,269,724,422,641,179,651,871,741,369,401,956,496,199,509,819,379,681,247,279,185,920`; reference cost 1,952 operations |
| G6 | pass: five attacks, 0/8 successes each; reference algorithm 8/8 as expected |
| G7 | pass: 76 to 156 graph vertices while the answer stays at 9 atoms |
| G8 | pass: 60/60 relabelling/affine/composed checks, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9 | **blocked**: size caps pass (112 characters, 28 estimated tokens, 9 atoms, 76 operations on the report seed; the bounded worst case is 30 tokens), but all three oracle arms were unscorable |

## Oracle loop and G9 arms

All three required runs were invoked through `scripts/harden.py` in separate directories, but OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw.  The script-owned error rows remain in `llm_loop_transcript.jsonl`, `g9_hinted_transcript.jsonl`, and `g9_placebo_transcript.jsonl`; no API error is counted as an attempt or as model failure, and no hardness verdict is claimed.

| arm/preset | seeds/calls | solved | result |
|---|---|---:|---|
| bare/easy | four fresh seeds | 0/0 scored | four API errors; harness aborted |
| hinted/easy | four fresh seeds | 0/0 scored | four API errors; harness aborted |
| placebo/easy | four fresh seeds | 0/0 scored | four API errors; harness aborted |

Thus hinted-minus-placebo is not yet meaningful.  After the OpenRouter limit is restored, rerun the bare harness from this directory, then rerun structural and placebo copies in separate scratch directories as prescribed by G9.  Do not treat the current 0/0 figures as evidence.

## Use

```python
import gen_1509_08807 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["easy"])
statement = g.render(inst)
answer = g.parse_answer('<answer>{"dimension":2,"basis":'
                        + __import__("json").dumps(inst["answer"]["basis"])
                        + '}</answer>')
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, after the oracle evidence is complete:

```bash
bash scripts/emit.sh 1509.08807 20
```

## Caveats

The family is easy for software that recognizes the line-graph promise; that is why it is Track B.  The exact guess density is uniform over ordered full-rank 2-by-4 matrices, not over a human's highly informed prior, and therefore proves only resistance to the declared structure-aware random sampler.  The panel tried coordinate outliers, small-coordinate rows, an edge-plus-axis ansatz, an induced-P3 span, and 512 random restarts; it did not benchmark a general ILP/CP-SAT implementation or a production Cluster Deletion FPT solver.  The canonical key is a strong affine-local determinant invariant rather than a complete graph-with-coordinates isomorphism canonizer.  Most importantly, oracle and hinted-oracle resistance remain unmeasured until the external key limit is repaired.
