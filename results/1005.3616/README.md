# Conflict-free 3-colouring generator — arXiv:1005.3616

| profile | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain / regime | combinatorics / finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: one of three colours per vertex |
| Objects | 4-uniform hypergraph and a three-colour vertex colouring |
| Intuition | constraint propagation through higher-order edge intersections |
| Domain essentiality | native; paper-licensed selection of Section 4's non-geometric hypergraphs |

This generator implements Definition 1.1 of Shakhar Smorodinsky's survey
[“Conflict-Free Coloring and its Applications”](https://arxiv.org/abs/1005.3616).
The solver receives a 4-uniform hypergraph and must colour every vertex with
0, 1, or 2 so that every edge has a colour occurring exactly once. Verification
is an exact linear scan of the edges. Section 4 explicitly treats arbitrary
non-geometric hypergraphs, so this is a paper-licensed native branch of the
survey, not a graph surrogate for its geometric results.

## Why trust it, and why it is hard

Generation is inverse: a balanced colouring is sampled first, then every edge
is drawn from the same valid-edge distribution. The acceptance weights are
chosen so that a fixed same-colour pair and a fixed different-colour pair have
equal expected co-incidence. Thus the planted vertices are not degree outliers
and the usual pair-spectral signature is neutral in expectation. The generator
also rejects the easy two-colour special case exactly by Gaussian elimination
over GF(2); this screening does not find the held three-colour witness.

The survey itself gives polynomial constructions for several geometric regimes
(notably Section 5's `O(n log n)` algorithm producing an `O(log n)` disc
colouring), so those results do not support a Track A claim here. The relevant
worst-case result is Theorem 2 of
[Nakajima–Verwimp–Wrochna–Živný](https://arxiv.org/abs/2501.12062): promised
3-conflict-free colouring is NP-hard for 4-uniform hypergraphs. That theorem
does **not** prove this planted distribution hard. Distributional evidence is
the measured panel: bounded DPLL failed 8/8 after 20,008 nodes and 48,055,606
counted operations (23.263541 s total), and every planting-aware attack failed.

## Worked demo

For `make_instance(n=9, m=12, seed=0)`, the full rendered edge block is:

```text
vertices: 0 1 2 3 4 5 6 7 8
0: 0 1 2 8
1: 0 1 4 5
2: 0 2 3 5
3: 0 3 5 7
4: 0 3 5 8
5: 0 4 6 8
6: 0 4 7 8
7: 1 2 3 8
8: 1 2 4 7
9: 1 2 6 8
10: 1 3 4 5
11: 1 4 5 7
```

One answer is `[2,1,0,1,1,0,0,2,2]`.
`verify(inst, answer)` returns `(True, "ok")`; deleting its last entry returns
`(False, "too few vertex colours: expected 9, received 8")`. With only nine
vertices and 630 valid colourings among 18,150 admissible strings, this demo is
genuinely solvable and checkable by hand.

## Presets and gates

| preset | vertices `n` | edges `m` | status |
|---|---:|---:|---|
| demo | 9 | 12 | hand example; not hardened |
| easy | 120 | 360 | **shipping; held 3/3 oracle attempts** |
| medium | 180 | 558 | available, not needed |
| hard | 240 | 768 | available, within the 256-atom cap |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | fenced, prose-surrounded model answer round-trips |
| G4 | 0 hits / 200,000 uniform surjective ternary guesses |
| G5 | shipping sampled density 0/200,000; demo exact count 630/18,150; DPLL cost above |
| G6 | 8 attacks, each 0/8; all 8 DPLL runs reached the 2,500-node cap |
| G7 | doubled instance `n=240, m=720` builds and verifies |
| G8 | 20/20 relabelling invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 241 characters, 61 estimated tokens, 120 atoms, 120 intended post-insight assignments |

The bare hardening loop used the repository's current two-vendor pool (the
checked-in harness changed from four vendors on 2026-09-05):

| preset | model | seed | solved | exact failure |
|---|---|---:|---|---|
| easy | `google/gemini-3.8-flash` | 665185426 | no | edge 0: multiplicities `[2,2,0]` |
| easy | `openai/gpt-5.6-terra` | 1798283321 | no | edge 1: multiplicities `[2,0,2]` |
| easy | `openai/gpt-5.6-terra` | 582560251 | no | edge 12: multiplicities `[2,2,0]` |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping result is hardened |
| structural hint | 0 / 3 | hint did not make a verified solution reachable |
| placebo hint | 0 / 3 | same outcome as structural hint |

The structural-minus-placebo success-rate difference is `0.0`. At this sample
size, merely pointing to higher-order intersections bought nothing; this does
not establish that the claimed intuition is absent, only that the one-sentence
hint was insufficient.

## Use

```python
from gen_1005_3616 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh shipping instances with:

```bash
bash scripts/emit.sh 1005.3616 20 easy
```

## Caveats

The NP-hardness theorem is worst-case evidence, not an average-case theorem for
this planted model. Pair neutrality holds in expectation and does not erase
higher-order planting signals. DPLL was deliberately capped; no external SAT,
CP-SAT, tensor-spectral, SDP, or exhaustive higher-order recovery package was
run. The 0/200,000 density estimate concerns the declared uniform surjective
prior and says nothing by itself about a structured heuristic. Finally,
`canonical_key` is a six-round incidence-WL fingerprint plus exact intersection
histograms, not a complete hypergraph-isomorphism canonizer. These limitations
are why the empirical attack panel, its operation counts, and the raw oracle
transcripts are retained alongside the module.
