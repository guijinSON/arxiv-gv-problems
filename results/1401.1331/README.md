# arXiv 1401.1331 — noisy short-interval polynomial recovery

| profile | value |
|---|---|
| Track | **B** — no-tool compression; no Track A claim |
| Native domain / regime | algebra / finite field |
| Computational core | exact linear algebra (bounded-distance decoding) |
| Certificate | polynomial coefficient vector over `GF(p)` |
| Intended intuition | invariant: a common second finite difference cancels the noise |
| Domain essentiality | native; no reduction |

## What the family asks

The solver receives noisy values of the sparse polynomial
`f(X)=a4*X^4+a3*X^3` over `GF(p)`, evaluated at ordinary integers in a short
interval.  It must return `[a4,a3]`.  The checker evaluates that polynomial
modulo `p` at every displayed point and compares the centered residue error to
the exact integer bound `Delta`; it accepts any coefficient pair satisfying all
samples and never reads the planted answer.  This is the native noisy
interpolation problem defined in §1.2 of [Garcia-Morchon, Rietman, Shparlinski,
and Tolhuizen](https://arxiv.org/abs/1401.1331), specialized to the known sparse
support explicitly discussed there.

## Why Track B, and what is easy

Theorem 9 (§4.1), using the lattice of §3.2 and fixed-dimensional exact CVP in
Lemma 7, gives a deterministic polynomial-time recovery algorithm in its
parameter regime.  A Track A claim would therefore be false.  The paper also
explains two important easy/impossible boundaries: low coefficients must be
known with `h^k > Delta p^epsilon`, while exceptional polynomials and the HIMMO
regime can make complete recovery impossible (§§1.2, 5, and 7).

The measured reference here is the exact two-unknown bounded-distance decoder:
enumerate the two allowed sample errors, solve a `2 x 2` modular system, and
check all samples.  It costs `O((2 Delta+1)^2 m)` operations for `m` samples.
Across eight hard instances it averaged 117,236 error pairs, 938,121
instrumented exact operations, and 1.262 seconds in the final recorded run.
The compact route comes from
the paper's discrete-difference viewpoint in §5.2: in one packet, the three
error triples share a second difference.  Subtracting their observed second
differences gives two noiseless equations.  That route used at most 294 exact
operations, but only after the correlation is noticed.

## Worked demo

For `make_instance(n=1, p_bits=7, delta=2, h=18, seed=0)`, the complete data
portion is:

```text
p = 127, Delta = 2, f(X) = a4*X^4 + a3*X^3
Packet 1:
  Triple 1: (8,5)  (7,95)  (9,13)
  Triple 2: (0,1)  (-2,74)  (-1,59)
  Triple 3: (16,4)  (15,69)  (14,68)
Output <answer>[a4,a3]</answer>.
```

The answer is `<answer>[109,50]</answer>` and `verify` returns `(True, "ok")`.
Swapping it to `[50,109]` returns `(False, "sample 0:0:1 has centered distance
11 > 2")`.  This smallest setting is solvable on paper by taking the three
second differences and solving the resulting two modular equations.

## Difficulty presets

| preset | packets / samples | `p` bits | `Delta` | status |
|---|---:|---:|---:|---|
| demo | 1 / 9 | 7 | 2 | hand example; not hardened |
| easy | 2 / 18 | 31 | 31 | rejected by Step 4: one oracle solved it |
| medium | 3 / 27 | 61 | 63 | oracle run blocked by exhausted external quota |
| hard | 5 / 45 | 89 | 255 | provisional `SHIPPING_DIFFICULTY`; all local gates pass, no oracle shipping verdict |

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verified and JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response round-tripped; garbage returned `None` |
| G4 | 0 hits in 200,000 structure-aware uniform coefficient guesses |
| G5 | hard density 0/200,000; demo has exactly 1 valid answer of 16,129; reference mean 117,236 pairs / 938,121 operations |
| G6 | four attacks each 0/8; reference and compact algorithms each 8/8 |
| G7 | doubled 10-packet instance built and verified; answer stayed two elements |
| G8 | 60/60 reordering/reflection invariance and witness checks; 20/20 unrelated keys distinct |
| G9(c) | 57-character conservative answer bound, 2 atoms, 294 intended-route operations |

## Oracle loop and G9 arms

The script-owned bare run completed `easy` and then exhausted the configured
OpenRouter key.  API errors are not counted as model failures, so this run does
**not** establish a shipping hardness verdict.

| arm / preset | model and seed | result |
|---|---|---|
| bare / easy | Gemini 3.8 Flash, 338593001 | failed: empty length-limited response |
| bare / easy | GPT-5.6 Terra, 1628622123 | solved |
| bare / easy | GPT-5.6 Terra, 1028575232 | parsed answer failed verification |
| bare / medium | four redraws | HTTP 403 key-limit errors; no attempt counted |
| hinted / hard | four redraws | HTTP 403 key-limit errors; 0/0 scored attempts |
| placebo / hard | four redraws | HTTP 403 key-limit errors; 0/0 scored attempts |

Thus hinted minus placebo is unavailable, not zero evidence.  The two G9
transcripts are retained exactly as written by `harden.py`; the intended-route
and answer-size caps still pass.  Re-run all three arms after replenishing the
OpenRouter quota before submission.

## Use

```python
from gen_1401_1331 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
answer = parse_answer("<answer>[1,2]</answer>")
print(verify(inst, answer))
```

From the repository root, after a successful shipping hardening run:

```bash
scripts/emit.sh 1401.1331 20 hard
```

## Caveats

This distribution deliberately contains a finite-difference correlation; a
solver that detects it has the compact algorithm and the family becomes easy.
The 0/200,000 guess result is only for the uniform prior on both legal field
coefficients and says nothing about correlation-aware decoders.  The reference
implementation is a transparent exhaustive specialization, not an
implementation of Micciancio--Voulgaris exact CVP, and the latter was not run.
No LLL library, SMT solver, or external lattice package was available or tried.
Most importantly, the external quota expired before `medium` or `hard` received
three valid oracle attempts.  The module is locally verified, but it must not be
submitted or described as hardened until that evidence exists.
