# arXiv 2101.02314 — signed Walsh rational SOS generator

| Profile field | Value |
|---|---|
| Status | **parked — `cap_bound`, not released and not rejected** |
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | exact symbolic |
| Intuition | invariant: a signed XOR kernel has a two-level magnitude pattern on an annihilator subspace |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator is based on Jurij Volčič, [*Hilbert's 17th problem in free skew fields*](https://arxiv.org/abs/2101.02314). The solver receives an exact noncommutative rational function

`r = sum G[u,v] x_u z^-2 x_v`,

where every `x_u` and `z` is hermitian and multiplication does not commute. It must return eight explicitly parameterized rational functions whose hermitian squares sum to `r`. Each summand is a signed Walsh linear form followed by `z^-1`. The answer is a genuine symbolic rational certificate, not a sampled matrix evaluation. `verify` applies the involution, expands the eight products in the free words `x_u z^-2 x_v`, and compares every integer coefficient exactly.

Section 2.1 supplies the formal-rational-expression and involution definitions. Corollary 5.4 is the sum-of-hermitian-squares result. The generator uses inverse construction: it samples the eight summands first and expands them to obtain `G`; it never solves the generated instance.

## Why Track B, not Track A

Section 5.5 explicitly turns coefficient matching with a positive Gram matrix into a semidefinite program. Claiming structural hardness would therefore be false. This structured subfamily has an even faster exact reference algorithm: normalize the shared sign gauge and apply a Walsh-Hadamard transform to one canonical coefficient row. It runs in `O(N log N)` and recovered 8/8 hard-preset instances, averaging **1,160 exact integer operations** and **0.000069 s**.

The shorter route is to notice that absolute coefficients have only two levels. The large-magnitude XOR differences form the annihilator of the hidden three-dimensional frequency flat; the signs recover the distinguished character and shared mask. That route used at most **179 exact operations** at `N=128`. It is short enough after the invariant is seen, but the blind 1,160-operation transform is not a plausible no-tool calculation. The paper's general SDP is larger still.

The paper also notes that regularity itself can be difficult to decide, but this benchmark does not use regularity as a search task; it asks for the directly checkable rational identity. The oracle story is decisive and unfavorable: a corrected-parser run held at medium, but a structural hint solved medium 2/3; the single permitted move to hard was then solved bare 1/3. The next size, `N=256`, needs 328 logical answer atoms, beyond the 256-atom cap. The result is therefore parked as `cap_bound`, not shipped.

## Worked demo (`demo`, seed 3)

This is the complete small instance (the prose definitions are the same as in `render`): `z` and all `x_b` are freely noncommuting hermitian variables, `z^-2=z^-1 z^-1`, and

`q(a,c,sigma) = c * sum_b sigma_b (-1)^(a dot b) x_b z^-1`.

The instance is `r = sum G[u,v] x_u z^-2 x_v`, with row/column order

`010 000 001 110 100 111 101 011`

and exact coefficient matrix:

```text
010: 16 -8  8 -8  8 -8 -8  8
000: -8 16 -8  8 -8  8  8 -8
001:  8 -8 16 -8  8 -8 -8  8
110: -8  8 -8 16 -8  8  8 -8
100:  8 -8  8 -8 16 -8 -8  8
111: -8  8 -8  8 -8 16  8 -8
101: -8  8 -8  8 -8  8 16 -8
011:  8 -8  8 -8  8 -8 -8 16
```

The full answer is:

```json
{"mask":"+++-+++-","summands":[{"frequency":"000","scale":1},{"frequency":"001","scale":1},{"frequency":"010","scale":1},{"frequency":"011","scale":1},{"frequency":"100","scale":1},{"frequency":"101","scale":1},{"frequency":"110","scale":1},{"frequency":"111","scale":3}]}
```

`verify(inst, answer)` returns `(True, "ok")`. Removing the last summand returns `(False, "expected exactly 8 summands, got 7")`. A person can solve this demo on paper: all eight width-three frequencies occur, the diagonal `16=7+3^2` fixes the exceptional scale, and the remaining signs fix the mask.

## Difficulty presets

| Preset | Variables `N` | Max exceptional scale | Render size at seed 0 | Final outcome |
|---|---:|---:|---:|---:|
| demo | 8 | 9 | 2,386 chars | skipped; hand example |
| easy | 32 | 10,000 | 12,318 chars | 2/3 solved |
| medium | 64 | 100,000 | 50,279 chars | bare 0/3, but structurally hinted 2/3 solved |
| **hard (last admissible)** | **128** | **1,000,000** | **192,022 chars** | **bare 1/3 solved; `cap_bound`** |

## Gate results

| Gate | Result | Measurement |
|---|---:|---|
| G1 | pass | 12/12 planted certificates verified; every answer JSON-round-tripped |
| G2 | pass | drop, frequency-only swap, duplicate, empty, and out-of-range corruptions all rejected with distinct reasons |
| G3 | pass | tagged JSON recovered through surrounding prose/fences; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware random candidates; space size `15203206329744241947211473953125242623145227059200` |
| G5 | pass | hard-preset density 0/200,000; demo exact count 1/128; failing panel cost 0.492 s / 2,048 restarts |
| G6 | pass | six attacks, each 0/8; exact Walsh reference 8/8 as Track B requires |
| G7 | pass | doubled `N=256` instance built and its planted certificate verified |
| G8 | pass | 80/80 key-invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | 428 chars, about 107 tokens, 192 logical atoms, 179 intended operations; hard hinted 0/3 |

All local gates pass at hard, including the polarity-flipped hinted gate. The family nevertheless does **not** ship because STEP 4 bare hardening was solved 1/3 and the next genuine size violates the answer cap.

## Oracle loop and the cap-bound decision

| Preset | Model | Seed | Solved | Recorded reason |
|---|---|---:|---:|---|
| hard | GPT-5.6 Terra | 1299645123 | no | exact coefficient mismatch |
| hard | Gemini 3.1 Pro | 250383424 | no | mask had the wrong length |
| hard | Grok 4.6 | 323889623 | **yes** | exact witness verified |

This final, one-rung hard rerun is the official `llm_loop_transcript.jsonl`. Its script-owned verdict is `cap_bound`. The scratch harness reports `single_axis` because the mandated one-rung copy intentionally contained only hard and because its generic atom counter treats strings as one atom. The family-specific logical count is the decisive measurement: hard uses 192 atoms, while doubling to `N=256` uses `256 + 8*8 + 8 = 328` atoms. Raising only `scale_max` changes integer width but not the structural recovery problem.

For auditability, `medium_bare_transcript.jsonl` preserves the corrected-parser run that held medium 0/3 after easy was solved 2/3. `g9_medium_hinted_transcript.jsonl` records why medium could not ship: the structural hint solved it 2/3.

## G9 arms

| Arm | Solved / attempts | Verdict or observation |
|---|---:|---|
| bare | 1/3 | failed STEP 4; triggers the park |
| structural hint | 0/3 | hardened; G9(b) itself passes at hard |
| placebo hint | 0/3 | hardened diagnostic |

Hinted minus placebo is **0.0** at hard. Different random seeds/models make the surprising bare 1/3 versus hinted 0/3 result a diagnostic, not a causal claim. At medium, however, the structural hint solved 2/3 and forced the permitted one-rung move. The answer-size and route measurements at hard are 428 characters, 107 estimated tokens, 192 logical atoms, and 179 exact operations.

## Use

```python
from gen_2101_02314 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(model_reply)
ok, reason = verify(inst, candidate)
```

For local inspection only, records can be emitted from the repository root with:

```bash
bash scripts/emit.sh 2101.02314 20 hard
```

The module is standard-library-only; `gvlib` is not needed because verification reduces to integer coefficients of a fixed free-word basis. Do not include these records in a native release while `.meta.json` says `cap_bound`.

## Caveats

- This is Track B and it is parked. Software solves every generated instance quickly, and the final hard oracle pool also solved one instance without tools.
- The 0/200,000 guess rate is relative to the declared prior: a normalized sign mask, eight distinct frequencies, the scale forced by the diagonal, and a uniformly chosen exceptional frequency. It does not estimate arbitrary solver behavior or prove average-case hardness.
- The hard statement is large (about 192 KB; earlier transcripts reported roughly 92k prompt tokens). Several failures had malformed mask length or exhausted reasoning output. Although the answer and intended route meet G9(c), some measured difficulty is clearly context scanning and exact transcription.
- The next `N=256` instance verifies exactly and is mathematically available, but its 328 logical atoms exceed the output contract. This is the sole reason for `cap_bound`; it is not evidence against the paper or the family.
- The checker accepts every certificate in the stated bounded Walsh language, independent of the planted answer; it does not accept arbitrary unrestricted rational SOS decompositions outside that language.
- The panel tested magnitude outliers, low-index and low-Hamming greedy guesses, nearest-frequency and support-confusion ansatzes, and 256 random restarts. It did not run an external numerical SDP package. The stronger exact signed-Walsh algorithm was run instead and succeeded 8/8, as explicitly reported rather than hidden among failing attacks.
- `canonical_key` is exact for the generated signed-affine family: it quotients input order, affine binary-label changes, and independent variable sign changes. It is not a general canonical form for arbitrary rational functions.
