# arXiv 1803.03302 — voxel-surface stripification generator

**Status: parked (`cap_bound`), not rejected and not shipped.** Every writable
preset passed the local gates, but each was solved by at least one bare oracle.
The next size has 258 answer atoms, over the 256-atom cap. The harness-owned
[`.meta.json`](.meta.json) records that terminal verdict.

| Profile field | Value |
|---|---|
| Track | **B** — an efficient algorithm exists and is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a panel permutation) |
| Intuition | decomposition: recognize the cube-attachment chain and splice five-face patches |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section B (mesh stripification as a dual-graph Hamiltonian cycle) |

## Problem and trust model

The source is Xi et al., [*Super Compaction and Pluripotent Shape
Transformation via Algorithmic Stacking for 3D Deployable
Structures*](https://arxiv.org/abs/1803.03302). The solver receives an actual
voxel solid, every exposed unit-square panel with exact integer geometry, and
the dual face-adjacency graph. It must return one normalized Hamiltonian cycle
through all panels—the single strip used by the paper.

Generation is by certificate-preserving composition, not search. Starting from
one cube, attaching a new cube removes one exposed face and exposes five. Those
five faces form a patch with a spanning path between whichever two old cycle
neighbors met the removed face, so the old face can be replaced locally. The
checker independently reconstructs the exposed voxel surface and shared edges,
then checks that the submitted ids are a permutation forming one cycle. It
never reads `inst["answer"]`.

This is representational rather than native geometric coverage: exact panel
geometry remains visible and is checked, but the solver's search is the graph
problem that Section B explicitly licenses.

## Why Track B, and why it is parked

Track A would be false. Section B says Taubin's triangulated-quad construction
is linear and that the authors use Concorde with almost-linear observed growth.
It also cites 2-factor extraction and cycle merging, which is the standard
reference implemented here. On eight 254-panel trials that reference solved
8/8: upper-median work was 7,506,977 primitive operations and 0.898 seconds in
the final run; the maximum was 166,296,780 operations and 21.635 seconds. Its
declared worst case is `O(R*F^3)` for `R` randomized Euler-tour restarts.

The compact route requires 186 local splice decisions at 63 cubes. The gap is
therefore real, but the bare oracle results show it is not large enough at any
writable size: easy, medium, and hard were all solved at least once. Increasing
to 64 cubes makes a 258-panel witness. Per the task's special rule this is a
format limit (`cap_bound`), not an H rejection.

The other paper-native choices do not rescue the family. Theorem 1 directly
stacks every strip into one or two piles, so that is easy on Track A and has no
better Track-B compression gap. Theorem 2 gives linear feasibility checking for
a proposed stacking, but the paper supplies no executable dual certificate of
global compactness. The conclusion explicitly leaves continuous folding-motion
feasibility unhandled.

## Worked demo

The demo is one voxel and six panels; a person can solve it on paper. Its full
rendered panel table is:

```text
Voxels: (0,0,0)
0 | (0,0,0) | -y | 2,3,4,5
1 | (0,0,0) | +y | 2,3,4,5
2 | (0,0,0) | -x | 0,1,3,5
3 | (0,0,0) | -z | 0,1,2,4
4 | (0,0,0) | +x | 0,1,3,5
5 | (0,0,0) | +z | 0,1,2,4
```

`<answer>[0,3,4,1,2,5]</answer>` verifies as `(True, "ok")`.
Dropping the last id gives `(False, "cycle omits one or more panels")`.

## Difficulty ladder

| Preset | Cubes | Panels / answer atoms | Bare result | Disposition |
|---|---:|---:|---:|---|
| demo | 1 | 6 | skipped by harness | hand example |
| easy | 47 | 190 | 2/3 solved | defeated |
| medium | 55 | 222 | 1/3 solved | defeated |
| hard | 63 | 254 | 1/3 solved | defeated; last writable rung |
| next | 64 | 258 | not run | over the 256-atom cap |

`SHIPPING_DIFFICULTY` remains `"hard"` as the last tested writable preset, but
there is **no shipping preset** because the harness verdict is `cap_bound`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verify and JSON-round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 normalized-permutation guesses; language is 1660 bits |
| G5 | pass | shipping density 0/200,000; baseline 17,646,497 operations, 2.344 s |
| G6 | pass | five attacks at 0/8; reference and compact routes both 8/8 |
| G7 | pass | panel counts 6, 190, 222, 254; doubled 506-panel build verifies |
| G8 | pass | 20/20 composed invariances and carried witnesses; 20/20 keys distinct |
| G9(c) | pass | 907 chars, 227 estimated tokens, 254 atoms, 186 operations |

## Bare oracle loop

| Preset | Seed | Model | Solved | Exact result |
|---|---:|---|---:|---|
| easy | 1856999300 | GPT-5.6 Terra | yes | ok |
| easy | 1008096441 | Gemini 3.8 Flash | yes | ok |
| easy | 1202422379 | GPT-5.6 Terra | no | repeated/extra panel |
| medium | 943578440 | GPT-5.6 Terra | no | non-hinge transition 36–1 |
| medium | 1176409469 | Gemini 3.8 Flash | no | reply ended mid-reasoning; no answer tags |
| medium | 798505199 | Gemini 3.8 Flash | yes | ok |
| hard | 370234762 | Gemini 3.8 Flash | no | omitted panel |
| hard | 547616664 | GPT-5.6 Terra | yes | ok |
| hard | 209774265 | GPT-5.6 Terra | no | repeated/extra panel |

The unparsed medium reply visibly contains no completed answer, so it is not a
G3 false negative. Full records are in
[`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl).

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | not summarized as a shipping arm | `cap_bound` loop above |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

The hinted and placebo arms were intentionally not run: `cap_bound` is a
terminal stop condition and no shipping preset exists to diagnose. Thus
`hinted - placebo` is not estimated. The last writable answer is 907 characters,
227 estimated tokens, and 254 atoms; its intended route is 186 exact local
decisions.

## Use

```python
import random
import gen_1803_03302 as g

inst = g.make_instance(n=1, seed=0)
statement = g.render(inst)
candidate = g.parse_answer("<answer>[0,3,4,1,2,5]</answer>")
assert g.verify(inst, candidate) == (True, "ok")
guess = g.random_candidate(inst, random.Random(7))
```

If a future answer cap permits a genuinely hardened rung, emit from the repo
root with `bash scripts/emit.sh 1803.03302`. Do not emit the current parked
result.

## Caveats

- The generated solids are monotone one-voxel-thick attachment chains, not the
  paper's arbitrary voxelizations. Recognizing that restriction makes them
  efficiently solvable; this is exactly why the claim is Track B.
- G4 samples uniformly from normalized permutations. It accounts for shape,
  range, uniqueness, rotation, and reversal constraints, but not graph-guided
  priors. G6 separately tested 256 graph-guided self-avoiding restarts per seed.
- Concorde itself was unavailable. The measured reference is the paper-cited
  randomized Euler 2-factor plus exact two-edge cycle-merging method.
- The attack panel did not test modern MILP/branch-and-cut or spectral/SDP
  relaxations. A spectral relaxation is not the natural domain attack for
  Hamiltonian cycle; branch-and-cut would likely strengthen the finding that
  this Track-B family is mechanically solvable.
- Panel labels are shuffled only to prevent positional leakage; label shuffling
  is not counted as hardness. Plants and all panels share the same geometric
  distribution, and every panel has degree four.
- Canonicalization is complete for translations and all 48 cubic coordinate
  symmetries of this generated voxel subclass. It is not a general polycube
  isomorphism solver.
