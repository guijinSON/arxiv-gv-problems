# Max-min CP elimination plans (arXiv:1708.09800)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite discrete |
| Computational core | linear algebra |
| Certificate form | integer tuple (the proof's recursive pivot triples) |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator is based on Mohindru and Pereira, [*The DJL Conjecture for CP Matrices over Special Inclines*](https://arxiv.org/abs/1708.09800). A solver receives a symmetric matrix over the finite max-min incline `L={0,...,31}`, where addition is `max` and multiplication is `min`. The requested witness is the recursive sequence of three-index pivots used by the proof of Theorem 3.2, followed by its ordered four-index or five-index base case.

The witness is native to the paper's factorization argument. `verify` checks every minimum and row-maximum pivot, expands the proof into at most `floor(n^2/4)` rank-one columns of support at most three, recomputes their max-min Gram product, and compares it exactly with the given matrix. It never consults the planted answer.

## Why Track B is honest

Theorem 2.1 says that complete positivity itself is easy to recognize here: for normal inclines it is characterized by all two-by-two principal inequalities, and a symmetric matrix with diagonal `31` automatically meets them in this max-min chain. A Track A claim would therefore be false.

The relevant mechanical method is the constructive proof of Theorem 3.2. Repeatedly scanning every remaining pair for a minimum and the selected row for a maximum costs `O(n^3)` exact comparisons. At the shipping preset the implemented reference scan succeeds on 8/8 instances, uses exactly **289,451 comparisons**, and averaged **0.021 seconds** in the recorded CPython selftest. Fast with tools is expected on Track B; 289,451 comparisons are not executable by hand in the evaluation context.

The compact route is to recognize that the least-valued pairs form one spanning path and that opposite path endpoints are greatest-valued partners. Walking that path and recording the recursive triples costs 224 pair lookups/emissions at `n=150`. Section 4's triangular-factor results were not used: under their hypotheses the triangular factor is copied directly from the matrix, so mechanical and compact routes are essentially the same and test no hidden structure.

## Worked demo

For `make_instance(n=6, noise_pairs=4, seed=7)`, the complete rendered data are:

```text
L = {0,...,31}, x ⊕ y = max(x,y), x ⊗ y = min(x,y).
A is symmetric 6 by 6, has diagonal 31, and default off-diagonal entry 15.
Entry-0 pairs: (0,4) (0,5) (1,2) (1,3) (3,5)
Entry-30 pairs: (0,1) (2,4)
Other overrides: (0,2):18 (0,3):12 (2,3):2 (3,4):20

Return {"pivots":[[u,v,w],...],"base":[...]}. At each pivot, A[u,w]
is a current global off-diagonal minimum and A[u,v] is a current row-u
maximum; remove u and v but retain w. The ordered final base has the same
conditions and contains every remaining index once.
```

One answer is:

```json
{"pivots":[[4,2,0]],"base":[0,1,5,3]}
```

`verify(inst, answer)` returns `(True, "ok")`. Replacing the last base index by the first returns `(False, "duplicate_base_entry: base indices must be distinct")`. This demo is hand-solvable: the five zero pairs visibly form the path `4-0-5-3-1-2`, whose opposite endpoints are the 30-pair `(2,4)`.

## Difficulty presets

| Preset | n | Middle-value overrides | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 6 | 4 | 7 | hand example; skipped by oracle loop |
| easy | 36 | 36 | 52 | oracle solved 1/3 |
| medium | 84 | 168 | 124 | oracle solved 2/3 |
| hard | 150 | 600 | 223 | **ships; oracle solved 0/3** |

`SHIPPING_DIFFICULTY = "hard"`.

## Gate results

| Gate | Result |
|---|---|
| G1 planted verifies | 12/12 preset/seed combinations |
| G2 corruption | 5/5 rejected with five distinct reason classes |
| G3 round trip | 73 pivot triples recovered from prose/fenced output |
| G4 guessing | 0/200,000 structure-aware random plans; observed rate 0 |
| G5 density/cost | shipping 0/200,000; demo exactly 54/2,880; reference 289,451 comparisons |
| G6 adversaries | four attacks, each 0/8; reference construction 8/8 as Track B expects |
| G7 scaling | planted witness verifies at doubled `n=300` |
| G8 canonicalization | 40/40 relabellings invariant and carried witnesses valid; 20/20 unrelated keys distinct |
| G9 caps | 1,119 chars, 448 conservative tokens, 223 atoms, 224 intended-route operations |

The four failing G6 attacks are static row-outlier ranking, displayed-index order, 32 random restarts per instance, and a static maximum-partner ordering. Random middle-valued overrides are what defeat row-sum and display-order signatures. The successful cubic construction is deliberately under `reference_algorithm`, not `attacks`.

## Bare oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 1069955622 | Gemini 3.8 Flash | failed | no complete answer |
| easy | 1726583901 | GPT-5.6 Terra | solved | verified plan |
| easy | 491410576 | Gemini 3.8 Flash | failed | no complete answer |
| medium | 1333069285 | GPT-5.6 Terra | solved | verified plan |
| medium | 1793088975 | Gemini 3.8 Flash | failed | exhausted response budget |
| medium | 542840229 | GPT-5.6 Terra | solved | verified plan |
| hard | 48443017 | Gemini 3.8 Flash | failed | stopped mid-reasoning; no answer tags |
| hard | 243220928 | GPT-5.6 Terra | failed | pivot-min condition failed at stage 42 |
| hard | 723001969 | Gemini 3.8 Flash | failed | no complete answer |

The harness verdict is `hardened` at `hard`. The two `parse_answer returned None` records across all arms were inspected: both replies end mid-reasoning and contain no answer block, so they are not parser false negatives.

## G9 hint diagnostic

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 2/3 | structure exposed |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is **2/3**. This is the desired diagnostic separation: once told that the extrema define the path/opposite-endpoint invariant, two models execute the compact route; merely adding a similar sentence does nothing. The hint result is recorded, not gated.

## Use

```python
from gen_1708_09800 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer('<answer>{"pivots":[[4,2,0]],"base":[0,1,5,3]}</answer>')
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 1708.09800 20
```

## Caveats

This is not evidence that max-min CP factorization is computationally hard; the paper gives the successful construction, and the generated distribution also has an intended linear shortcut. It measures whether a no-tool solver discovers that shortcut and transcribes a bounded proof plan accurately. The 0/200,000 guess figure is only for the declared prior: ordered current triples followed by a uniformly ordered base; it is not a confidence bound for informed heuristics. The extrema are deliberately structured, so an implementation that extracts the zero path will solve every instance—that is the intended compact route, not an untried attack. I did not benchmark SAT/SMT encodings or highly optimized path extraction because both add tools that the Track B setting excludes; I did test the paper's constructive scan and the four in-context alternatives above. The answer is integer-valued because the theorem's actual proof witness is a sequence of index choices; the checker still reconstructs and verifies the native incline-matrix factorization rather than reducing it to a graph problem.
