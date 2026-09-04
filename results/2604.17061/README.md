# Signed tensor-degeneracy generator (arXiv:2604.17061)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | integer tuple (three exact projective vectors) |
| Intended intuition | decomposition — cancel near-negative slices to expose a signed path Laplacian |
| Domain essentiality | native |
| Reduction | paper-licensed: Theorem 3.5 and Proposition 4.2 |

## What the problem is

The source is Angshul Majumdar, [*∃R-Completeness of Tensor Degeneracy and a Derandomization Barrier for Hyperdeterminants*](https://arxiv.org/abs/2604.17061). The solver receives every integer slice of a rational 3-tensor `T`. It must return nonzero vectors `x,y,z` for which all three modewise contractions vanish. `x` and `y` are primitive integer representatives of bounded rational projective points; `z` selects the unique zero slice.

This is the paper's native tensor object. Definition 4.1 gives exactly the three checked contractions. Theorem 3.5 introduces the zero-slice pencil witness, and Proposition 4.2 proves that stacking the pencil matrices as tensor slices preserves those equations exactly. Verification uses integer bilinear contractions only, reads no planted answer, and accepts any witness in the declared bounded language.

## Why this is Track B

Theorem 4.3 proves unrestricted real 3-tensor degeneracy is ∃R-complete, but that worst-case theorem says nothing about this inverse-planted distribution. This module therefore makes no Track A claim.

An efficient algorithm for the generated distribution is explicit. Add all `m` slices. The dense terms cancel and leave

`Q = diag(x) * L_path * diag(y)`.

Starting from the projective normalization, the two off-diagonals of `Q` propagate every sign of `x` and `y`; the unique zero slice gives `z`. This costs `O(m n^2)` exact operations. At shipping `n=16,m=65`, the implementation solves 8/8 instances in 16,700 integer operations and about 0.0007 seconds on average.

The compressed route is to pair near-negative slices first and add only their four-entry residuals. It takes at most 188 exact arithmetic operations after the pairing is recognized. Without tools, finding those pairs among 65 dense matrices is the intended obstacle. The structural hint solved 2/3 instances at `easy`, so G9(b) rejected that rung; all three hinted models failed after promotion to `medium`.

The important easy regimes are explicit. The aggregate decoder makes every generated instance polynomial-time solvable. The zero slice also makes `z` immediate. Section 5 says a single hyperdeterminant certificate exists only in boundary format; the shipping shape `16 x 16 x 65` is not boundary format (`65 != 16+16-1`). The paper gives no average-case claim for this planted distribution.

## Worked demo

`demo`, seed 0, is hand-solvable: pair slices `(0,5)`, `(1,6)`, and `(3,4)`, add their sparse residuals, and read the signed path off-diagonals.

```text
Find an exact degeneracy witness for a rational 3-tensor.

The tensor T has shape 3 x 3 x 7. Its third-mode slices A_k are the
integer matrices printed below, with k=0,...,6. For column vectors x,y
of length 3 and z of length 7, define M(z)=sum_k z[k] A_k.

A tensor-degeneracy witness is a triple of nonzero vectors satisfying:
1. x^T A_k y = 0 for every k=0,...,6;
2. M(z)y is the all-zero length-3 vector;
3. M(z)^T x is the all-zero length-3 vector.

x and y must be primitive nonzero integer vectors with entries in [-3,3]
and first nonzero coordinate positive. z is binary with one 1 selecting
the unique all-zero slice. Indices are 0-based.

slice 0:
  -3 -1 -1
   0  2  0
  -1 -2  4
slice 1:
   3 -1  0
  -3 -4 -1
  -1 -1 -4
slice 2:
   0  0  0
   0  0  0
   0  0  0
slice 3:
   5  5  0
  -4  3  4
   3  3  3
slice 4:
  -4 -4  0
   3 -4 -4
  -3 -3 -3
slice 5:
   3  1  1
   0 -3 -1
   1  3 -3
slice 6:
  -3  1  0
   3  4  1
   1  1  4

Give the JSON object inside <answer></answer> tags.
```

The answer is:

```json
{"x":[1,1,1],"y":[1,-1,1],"z":[0,0,1,0,0,0,0]}
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping the last coordinate of `x` returns `(False, "x has wrong length: expected 3, got 2")`.

## Difficulty presets

| Preset | `n` | Slices `m` | Tensor entries | Render chars, seed 0 | Answer-space bits | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 3 | 7 | 63 | 1,623 | 14.36 | hand example; never ships |
| easy | 14 | 29 | 5,684 | 16,672 | 76.61 | bare held, but structural hint solved 2/3: rejected by G9(b) |
| medium | 16 | 65 | 16,640 | 45,738 | 87.84 | **shipping; all three G9 arms held** |
| hard | 18 | 109 | 35,316 | 94,789 | 99.07 | available; not needed |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified across all presets |
| G2 | pass | 6/6 corruptions rejected with 6 distinct reasons |
| G3 | pass | prose + fenced JSON + tags round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; bounded language size `276105487994159556202086400` (87.835 bits) |
| G5 | pass | shipping density estimate 0/200,000; demo exact answer count 1; 64-restart attack cost 2.330103 s; reference cost 16,700 ops / 0.000696 s |
| G6 | pass | all four attacks 0/8; reference decoder 8/8 as expected |
| G7 | pass | doubling to `n=32` built in 0.020892 s; 132,096 entries; planted witness verified |
| G8 | pass | 180/180 keys invariant, 180/180 carried witnesses valid, 20/20 unrelated keys distinct |
| G9 | pass | hinted `medium` hardened; worst answer 243 chars, about 61 tokens, 97 atoms; intended route 188 operations |

G6's failures were: lowest-`L1` slice outlier 0/8, greedy single-slice signs 0/8, 64-restart coordinate descent 0/8, and constant/alternating/diagonal by-hand ansatzes 0/8. The successful aggregate decoder is correctly outside `attacks` as Track B's `reference_algorithm`.

## Bare oracle loop at shipping

| Model | Seed | Solved | Parser / verifier result |
|---|---:|---|---|
| Grok 4.6 | 72536 | no | parsed; first contraction nonzero at slice 0 |
| Claude Sonnet 5 | 800030410 | no | empty length-limited reply after using the response budget |
| GPT-5.6 Terra | 158644465 | no | parsed; first contraction nonzero at slice 0 |

All three calls used `medium` reasoning and the shipping preset. Provider errors are absent from this final bare transcript.

## G9 arms at shipping

| Arm | Solved / scored attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0` at shipping. The hint did carry real information at the rejected `easy` rung, where Gemini and Grok solved 2/3 scored instances. Its lack of measured benefit at `medium` therefore suggests that identifying and transcribing the correct 65-slice pairing remains material even after the decomposition is named. The shipping answer cap is 243 characters, about 61 tokens and 97 atomic coordinates; the intended post-insight route is 188 exact arithmetic operations.

## Use

```python
from gen_2604_17061 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["medium"])
question = render(inst)
candidate = parse_answer('<answer>{"x":[1],"y":[1],"z":[1]}</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root:

```bash
bash scripts/emit.sh 2604.17061 20 medium
```

## Caveats

- This is Track B. Any ordinary Python implementation can aggregate the slices in under a millisecond. It must not be cited as evidence that the generated distribution, tensor degeneracy generally, or hyperdeterminant vanishing is computationally hard.
- G4 samples uniformly from primitive vectors in `[-3,3]^16` modulo projective sign and fixes the statement-implied zero-slice `z`. Its 0/200,000 observation is only a density estimate under that prior; it does not cover construction-aware guesses, which G6 and the oracle runs address separately.
- The 188-operation count begins after near-negative pairs are identified. It excludes the comparisons needed to locate those pairs in 65 dense slices; this visual matching burden is real and may contribute to the oracle failures.
- One bare and one hinted shipping failure were empty Claude replies after the 32,000-token completion budget. Those two rows are valid under the harness, but are weaker evidence than the parsed, contraction-failing responses. The placebo Claude response did parse and fail exactly.
- The attack panel did not run a CAS, Gröbner-basis solver, homotopy continuation, or optimized tensor software. Such tools are unnecessary for this distribution because the disclosed aggregate decoder is much faster and solves every tested instance.
- `canonical_key` is invariant under slice/row/column permutations, independent coordinate sign changes, transposition of the first two modes, global or per-slice nonzero integer scaling, and tested compositions. It uses sorted, scale-normalized absolute coefficient multisets per slice. This is only a strong cheap invariant: it can collide for inequivalent tensors with the same coefficient multisets and does not canonicalize arbitrary rational `GL` basis changes.
- The zero slice is deliberately visible because it is the paper's exact Theorem 3.5 construction. The benchmark is about recovering `x,y`, not `z`. Outside boundary format there is no single hyperdeterminant checker supplied by the paper.
- `gvlib` is imported when present for repository consistency, but this family needs only exact integer arithmetic and retains a standard-library-only fallback.
