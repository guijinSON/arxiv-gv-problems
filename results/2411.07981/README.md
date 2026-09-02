# Contained Steiner triple systems

This generator turns Michael Zheng's paper [*Codegree conditions for (fractional) Steiner triple systems*](https://arxiv.org/abs/2411.07981) into a witness-search problem.  The solver receives vertices and an inline list of allowed triples, then returns exactly `n(n-1)/6` allowed triples covering every unordered vertex-pair exactly once.  `verify` normalizes order, checks membership, and counts pairs in polynomial time; it accepts every valid system, not only the plant.

The answer is generated first as a randomly relabelled Bose Steiner triple system.  The host is its union with independently relabelled systems from the same distribution.  Each source layer is exchangeable with the plant, each pair has at most `layers` possible third vertices, and there is no separate decoy distribution.

## Why this is the hard version

Section 1 fixes the integral definition and the equivalent decomposition viewpoint.  The paper's Theorem 1.5 is a sufficiently-large, very-dense existence theorem (minimum codegree about `0.8579n`); the shipping host has codegree at most 5 on 21 vertices and deliberately does not rely on that regime.  Section 1.2 says the *fractional* relaxation is constructed by linear optimization / maximum flow, and Sections 2–4 give an explicit fractional weighting, so fractional weights would fail H and are not used.

The general integral search problem is NP-hard: [Colbourn (1983)](https://doi.org/10.1016/0097-3165(83)90031-6) proves partial-Steiner-system completion NP-complete.  Completion reduces to this problem by allowing each required partial block and every triple that avoids its already-covered pairs; the required blocks are then forced.  This theorem does not prove average-case hardness of the generator's special union-of-layers distribution, so the local attacks and oracle loop below are essential empirical checks.

## Worked example

The smallest named shipping preset is `medium` and renders 3.2 KB at seed 0.  To keep the example readable in full, this uses the identical construction at its supported minimum, `n=9, layers=3, seed=0`:

```text
STEINER TRIPLE SYSTEM INSIDE AN ALLOWED 3-UNIFORM HYPERGRAPH

The vertices are the integers 0 through 8, inclusive.
An unordered pair means two distinct vertices; (a,b) and (b,a) are
the same pair.  A triple is an unordered set of three distinct vertices.

Choose exactly 12 distinct triples from the allowed list below so
that every unordered pair of distinct vertices occurs in exactly one
chosen triple.  Order within a triple and order among triples do not
matter.  Repeated vertices and repeated triples are forbidden.

ALLOWED_TRIPLES 32
2 3 4
1 4 7
0 1 6
1 2 7
0 4 5
5 6 8
4 5 6
0 2 3
2 6 7
1 6 8
1 4 8
1 5 7
2 4 6
0 1 5
0 4 7
4 5 7
1 2 5
2 4 8
0 1 2
0 7 8
1 3 8
3 4 6
0 6 7
3 5 6
0 4 8
0 3 5
3 5 7
0 6 8
1 3 6
3 7 8
2 5 8
1 3 4
END_ALLOWED_TRIPLES

Give your final answer inside <answer></answer> tags, as one JSON array
containing exactly 12 three-integer arrays.  JSON whitespace and
the order conventions above are ignored.
Example: <answer>[[0,1,2],[0,3,4]]</answer>
Output nothing else inside the tags.
```

Planted witness:

```json
[[1,5,7],[0,1,2],[0,3,5],[1,4,8],[2,5,8],[2,6,7],[0,4,7],[2,3,4],[1,3,6],[4,5,6],[3,7,8],[0,6,8]]
```

`verify(inst, inst["answer"]) == (True, "ok")`.  Dropping the final triple gives `(False, "wrong number of triples: expected 12, got 11")`.

## Difficulty presets

`n` is restricted to the strictly growing Bose subsequence `n = 3 mod 6`; `escalate` raises `n` by 6 and adds two layers.

| preset | vertices | layers | required triples | allowed triples at seed 0 | status |
|---|---:|---:|---:|---:|---|
| medium | 21 | 5 | 70 | 318 | **ships**; all gates and oracle hold |
| hard | 27 | 6 | 117 | 632 | available |
| extreme | 33 | 7 | 176 | 1,122 | available |
| rejected calibration | 15 | 4 | 35 | 123 | rejected by G6: each deterministic greedy solved 2/8 and random restart solved 7/8 |

## Gate results

| gate | measured result |
|---|---|
| G1 | 15/15 plants verified (3 presets × 5 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 2/2 model-style variants parsed, including untagged fenced JSON |
| G4 | 0/200,000 structure-aware guesses; each guess was already a complete STS |
| G5 | exactly 3 answers for each `n=9` seed; fractions `1.33e-8`, `5.47e-9`, `2.13e-8` of the naive subset spaces |
| G6 | codegree outlier 0/8, MRV lexicographic greedy 0/8, 24-restart mild heuristic 0/8 |
| G7 | order 45 (more than double 21) built; 330-block plant verified among 1,578 allowed triples |
| G8 | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |

The full machine-readable measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The final `harden.py` run used effort `medium`.  The Grok timeout is an error/redraw and contributed no hardness evidence.

| preset | model | seed | result | checker evidence |
|---|---|---:|---|---|
| medium | x-ai/grok-4.6 | 655226155 | API error | hard deadline; redrawn |
| medium | openai/gpt-5.6-terra | 1142062122 | failed | returned 64 of the required 70 triples |
| medium | google/gemini-3.1-pro-preview | 666549324 | failed | pair `[0,2]` occurred twice |
| medium | anthropic/claude-sonnet-5 | 1063722745 | failed | empty length-limited response after 32,000 completion tokens |

The first parser version missed an untagged fenced JSON array in an intermediate run.  That array was recovered after the G3 fix and was invalid (pair `[0,2]` was uncovered); the final transcript was then regenerated from scratch.

## Use

```python
from gen_2411_07981 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2411.07981 20 medium
```

Run local gates with `python3 -c 'import gen_2411_07981 as g; print(g.selftest())'` from this directory.  The oracle evidence was produced only by `python3 ../../scripts/harden.py gen_2411_07981.py`.

## Caveats

- The 0/200,000 G4 result is empirical, not a statistical proof that the true probability is below `1e-6`.  Its prior is an independently relabelled Bose STS, which enforces all shape and pair-cover constraints but is not uniform over every STS(21).
- Every hidden source layer is itself a valid answer, so solutions are intentionally non-unique.  All layers use the same Bose isomorphism class; a specialized algebraic layer-recovery attack could exploit that, and was not tested.
- The attack panel does not include a SAT/ILP solver, deep exact-cover backtracking, simulated annealing, or learned distinguishers.  NP-hardness is for the general problem, not a proof for this planted distribution.
- `canonical_key` is a strong Weisfeiler–Lehman-style incidence invariant, not a complete hypergraph isomorphism algorithm.  It is invariant under vertex and input relabelling in the tests and separated 20/20 unrelated instances, but rare non-isomorphic collisions are possible.
- Complete hosts are easy by the classical explicit STS constructions, the fractional relaxation is polynomial-time, and the rejected `n=15` window is easy for cheap random restart.  Those regimes should not be substituted for the shipping parameters.
