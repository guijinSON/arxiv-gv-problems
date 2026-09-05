# Projective-hyperplane witnesses from arXiv:2603.22960

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | geometry / finite field |
| Computational core | linear algebra |
| Certificate | a normalized `1 × n` matrix over `F_p` |
| Intended intuition | constraint propagation |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

The source is Chen, Hua, Li, and Wu, [*Locally 2-homogeneous block designs*](https://arxiv.org/abs/2603.22960). Section 3, Example 3.1(1) defines the projective-space design `PG(d-1,q)`: its points are one-dimensional subspaces of `F_q^d`, its blocks are hyperplanes, and point membership in a block is containment. Theorem 1.2 lists this as infinite family (1.1).

An instance supplies exact sparse representatives of projective points spanning one hyperplane over a prime field. The solver returns the hyperplane's uniquely normalized normal row. Verification checks the normalization and every finite-field dot product. The generator samples the normal first and creates a connected system of orthogonal points, so it knows the certificate without solving its output.

## Why Track B, and what is easy

This paper is a classification, not a computational-hardness paper. Section 2 gives a five-step subgroup/orbit procedure implemented in Magma for sporadic cases, while Section 3 directly constructs the infinite families. Nothing supports a Track A claim.

For this task, ordinary modular Gaussian elimination is the reference algorithm. On the shipping `192 × 128` rank-127 systems it is `O(m n^2)` and the included implementation solved 8/8 instances, averaging 56,700 exact field operations and 0.02–0.04 seconds total for the eight-instance panel across runs on this host. That is cheap with a program and not executable by hand. The shorter route notices that every two-coordinate point is a multiplicative relation in the unknown normal: traverse a spanning tree from coordinate zero. It uses 127 field multiplications, below the no-tool cap, but first requires recognizing and organizing the shuffled relation system.

## Worked demo

With `seed=0`, the demo is over `F_3` in five coordinates:

```text
P0: 0:2 1:2
P1: 0:2 2:2
P2: 1:1 2:2
P3: 1:2 3:2
P4: 0:1 3:2
P5: 1:1 4:2
P6: 3:2 2:2
```

The answer is `<answer>[[1,2,2,1,2]]</answer>`. The calls return:

```python
verify(inst, [[1, 2, 2, 1, 2]])
# (True, "ok")
verify(inst, [[1, 2, 2, 1]])
# (False, "wrong column count: expected 5, got 4")
```

This smallest setting is genuinely hand-solvable: start with `a_0=1` and propagate the seven small-field relations.

## Difficulty presets

| preset | n | field | extra points | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 3 | 2 | 5 | hand example |
| easy | 24 | 10-bit prime | 8 | 24 | oracle run attempted |
| medium | 64 | 19-bit prime | 24 | 64 | locally verified |
| hard | 128 | 29-bit prime | 64 | 128 | **shipping preset, pending oracle access** |

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; 12/12 JSON round trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic fenced/prose response round-tripped |
| G4 | 0/200,000 structure-aware random candidates verified |
| G5 | shipping sampled density 0/200,000; demo has exactly 1 solution; Gaussian baseline 8/8 |
| G6 | frequency outlier, all-ones greedy, 4096 random restarts, and one-pass scan: each 0/8 |
| G7 | doubled `n=256` instance built and verified; escalation also raises field size and redundant-point count at fixed answer length |
| G8 | 100/100 keys invariant and witnesses preserved under reorderings, projective rescaling, permutations, shears, and compositions; 20/20 unrelated keys distinct |
| G9(c) | 1,383 characters, about 346 tokens, 128 atoms; intended route 127 field operations |

## Oracle loop and G9 arms

The required harness was invoked, but OpenRouter returned HTTP 403 `Key limit exceeded` on every retry before a valid oracle attempt occurred. Errors are not model failures, so there is currently **no oracle-backed hardness verdict** and this directory is not ready for submission. The script-owned error transcript is retained rather than rewritten.

| arm | solved / valid attempts | result |
|---|---:|---|
| bare | 0 / 0 | blocked by OpenRouter account limit |
| structural hint | 0 / 0 | four API errors; no valid attempt |
| placebo hint | 0 / 0 | four API errors; no valid attempt |

The hinted-minus-placebo diagnostic is therefore unavailable. Once account access is restored, rerun each arm in its own scratch directory as required by the task, then update this table and `G9_ARM_RESULTS` from the script-owned transcripts.

## How to use it

```python
from gen_2603_22960 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2603.22960 20
```

## Caveats

- The family is easy with a finite-field implementation: Track B claims only a no-tool gap, and the successful reference algorithm is reported explicitly.
- `0/200,000` measures the declared prior of normalized all-nonzero rows. It is not an estimate against candidates produced by Gaussian elimination or full iterative propagation.
- The true iterative spanning-tree method deliberately succeeds; G6 tests four weaker, tool-free shortcuts, not the intended insight itself. No SAT/SMT, external CAS, or independent computer-algebra package was tried.
- `canonical_key` uses the strongest cheap invariants that survive arbitrary basis changes: field order, dimension, and point count. It intentionally over-collapses inequivalent configurations sharing that triple. Shipping seeds remain distinct because their sampled prime fields differ.
- `REJECTED.md` and `rejected_gen_2603_22960.py` predate this build and audit a different direct-intersection formula task. They are retained as provenance; the present hyperplane-normal family instead makes and measures the separate Gaussian-elimination-versus-propagation claim above.
- The local gates do not replace STEP 4. A valid bare transcript plus structural and placebo transcripts are still required before this can be called hardened or shipped.
