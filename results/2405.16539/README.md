# EGMC MinRank witness generator — arXiv:2405.16539

| profile | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | matrix certificate |
| Intended intuition | decomposition: expose the common kernel of a low-rank residual |
| Domain essentiality | native |
| Reduction | none |

## What this is

This module turns [*MinRank Gabidulin encryption scheme on matrix codes*](https://arxiv.org/abs/2405.16539) into the paper's native public decoding problem.  The solver receives an ordered basis `M0,...,M(K-1)` of an Enhanced Gabidulin Matrix Code over `GF(q)` and a noisy matrix `Y`.  It must return the `K = k*n` field coefficients for which

`E = Y + x0*M0 + ... + x(K-1)*M(K-1)`

has rank at most `r`.  The answer is a `k`-by-`n` coefficient matrix, compactly serialized as fixed-width hexadecimal strings.  `verify` decodes those strings, forms the residual, and computes its rank by exact finite-field Gaussian elimination.  It never reads the planted answer.

The instance is certified by inverse generation: sample the coefficient matrix and an independent uniformly random matrix of rank at most `r`, then assemble `Y`.  The public basis itself follows Definitions 14–16: a Gabidulin code over `GF(q^n)` is expanded over `GF(q)`, random columns are appended, and independent invertible left/right masks are applied.  This is not a random-code surrogate.

## Why Track A is justified

Definition 10 fixes MinRank; Figure 4 fixes the exact ciphertext equation.  Proposition 3 makes public decryption conditional on solving MinRank or recovering the hidden EGMC structure.  Section 6.2 analyzes hybrid, kernel, minors, and Support-Minors attacks.  The shipping preset is exactly the 128-bit Figure 7 row `q=16, m=n=23, k=7, ell1=0, ell2=5, r=8`, where the paper reports base-2 work exponents 172 (Support Minors), 262 (hybrid), 276 (kernel), and 160 (structural recovery).

The polynomial-time Gabidulin decoder in Section 2.4 does **not** make this Track B: it needs the secret extension basis, evaluation vector, and masks, none of which are in the instance.  Conversely, an unenhanced Gabidulin matrix code is easy to distinguish using its stabilizer algebra, and Section 6.1 explains why the added random columns and masks are necessary.  Small `n`, decoding beyond the unique radius, leaking the masks, or omitting the enhancement would invalidate the hardness claim.

The local kernel baseline implements one exact restart of Equation (7): guess seven right-kernel vectors, build 161 linear equations, and solve them over `GF(16)`.  One restart averages 5,441,545 field operations and 1.165 seconds; it succeeds on 0/8 audit seeds.  The paper's complexity includes the exponential probability of guessing the true kernel.

## Worked demo

The `demo` preset with seed 0 is hand-scale: only eight coefficient strings exist, so a person can try all of them and rank-reduce three-by-four matrices.

```text
Work over GF(2); matrices have 3 rows and 4 columns.
Y:0000/1101/0010
M0:1011/0110/1001
M1:1110/0001/0010
M2:0111/0100/1100
Find x0,x1,x2 such that rank(Y+x0*M0+x1*M1+x2*M2) <= 1.
Output: <answer>["100"]</answer>
```

```python
>>> verify(inst, ["100"])
(True, "ok")
>>> verify(inst, ["001"])
(False, "residual rank 2 exceeds bound 1")
```

## Difficulty presets

| preset | q | n | k | extra columns | r | answer symbols | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 3 | 1 | 1 | 1 | 3 | hand-solvable illustration |
| easy | 2 | 9 | 3 | 2 | 3 | 27 | oracle run not scored: API limit |
| medium | 4 | 15 | 5 | 3 | 5 | 75 | not reached by oracle |
| hard | 16 | 23 | 7 | 5 | 8 | 161 | **shipping preset; exact Figure 7 row** |

`escalate()` increases only the number of random columns after `hard`, keeping the 161-symbol witness fixed.  This grows the determinantal and structural haystacks rather than the answer.

## Local gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; 12/12 JSON round trips |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | realistic fenced/prose response round-tripped |
| G4 | pass | 0/200,000 structured guesses; exact probability `16^-161 ≈ 1.37e-194` |
| G5 | pass | one exact shipping witness; kernel baseline 5,441,545 operations mean |
| G6 | pass | outlier, greedy, 256-restart, and kernel attacks all 0/8 |
| G7 | pass | `n=46` build verifies; 106.53 seconds in the measured run |
| G8 | pass | 40/40 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 183 characters, about 46 tokens, 161 logical field elements, 161 post-identification placements |

## Oracle loop and G9 diagnostics

The required harness was run twice, but the OpenRouter key had reached its account-wide total limit.  The second script-owned transcript contains the following errors; the harness correctly scored none as a model failure.  Therefore there is currently **no hardened verdict**, and this result must not be submitted until a funded key reruns the bare and two G9 arms.

| preset | seed | model | scored | reason |
|---|---:|---|---|---|
| easy | 417116264 | Gemini 3.1 Pro Preview | no | HTTP 403: key total limit exceeded |
| easy | 471053841 | Grok 4.6 | no | HTTP 403: key total limit exceeded |
| easy | 2029172209 | Grok 4.6 | no | HTTP 403: key total limit exceeded |
| easy | 1005677035 | Grok 4.6 | no | HTTP 403: key total limit exceeded |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 | pending; no call was scoreable |
| structural hint | 0 / 0 | pending; no call was scoreable |
| placebo hint | 0 / 0 | pending; no call was scoreable |

The structural hint only names the kernel invariant; it does not provide a sequence of operations.  `hinted - placebo` is not yet measurable.

## Use

```python
from gen_2405_16539 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=0, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer('<answer>["100"]</answer>')
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after the oracle evidence is complete:

```bash
python3 results/2405.16539/gen_2405_16539.py
bash scripts/emit.sh 2405.16539 20 hard
```

## Caveats

- The paper's figures are security estimates, not a reduction proving average-case hardness for every generated seed.  Track A rests on the same MinRank/EGMC assumptions as Proposition 3.
- `0/200,000` measures the declared uniform prior over all correctly shaped coefficient matrices.  It rules out blind guessing but does not estimate a structured cryptanalytic prior; G6 is the separate construction-aware check.
- The implemented standard attack is the kernel attack with one restart.  A production Gröbner/Support-Minors implementation, the full structural bilinear attack, GPU search, and external CAS/cryptanalytic packages were not run.
- The full basis is rendered rather than compressed to a systematic public key, so a shipping prompt is about 110 kB.  This is faithful and exact, but it may stress model context and attention independently of MinRank reasoning.
- The 161-operation G9 figure counts field-symbol placements after the correct translate is identified.  It does not claim that public MinRank decoding itself takes 161 operations; that search is precisely the Track A hardness claim.
- The doubled-size construction is deliberately expensive in pure Python.  Normal shipping instances build in roughly four to six seconds on this machine.
- Oracle and G9 evidence is blocked by the OpenRouter account limit.  The present `llm_loop_transcript.jsonl` is valid script output but contains only errors, so it is not hardness evidence.
