# arXiv 2303.07825 — bounded affine Pell equations

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `other` (bounded binary quadratic Diophantine search) |
| Certificate | `integer_tuple` |
| Intuition | `change of variables` |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and trust status

The solver receives one binary quadratic equation over the integers and inclusive bounds for `x` and `y`, and must return any bounded integer zero. Verification is just bound checking and exact integer substitution. This is a native object from Ciobanu and Levine, [“Languages, groups and equations”](https://arxiv.org/abs/2303.07825): Theorem 6.4 treats arbitrary two-variable quadratic Diophantine equations, and Lemma 6.5 gives the Pell recurrence used by the construction.

The generator starts with `D=m^2-1` and the certified fundamental solution `(m,1)` of `U^2-DV^2=1`, advances the displayed recurrence, and transports the result through the determinant-one matrix `[[1+pq,p],[q,1]]`, an affine translation, and an optional coordinate swap. It therefore knows the answer by transformation of a known instance, not by searching the emitted box. G1–G9(c) pass locally. The required multi-vendor oracle claim is **not established**: six valid calls solved `easy` and `medium`, then OpenRouter exhausted the key before `hard` could receive a scoreable call. The script-owned transcript is retained, and no API error is counted as a model failure.

## Why Track B

Section 6 says that Lagrange reduction converts a general binary quadratic to a generalized Pell equation. Theorem 6.4 constructs the full solution language in nondeterministic `O(n^4 log n)` space, while Lemma 6.5 parametrizes Pell solutions by recurrence. The paper also identifies the easy Pell regimes: `D<=0` and square `D` have only finitely many solutions and are excluded here.

For the bounded task, the disclosed mechanical reference scans every allowed `x`, tests the quadratic discriminant for a square, and checks integral `y` roots. At configured shipping `n=250007`, eight measured instances averaged 103,400 iterations and 1,344,225 counted exact operations (0.06–0.43 seconds per instance across unloaded and busy shared-runner measurements); it solved 8/8 as Track B requires. The compact route observes that the homogeneous discriminant is `4D`, recovers the two shear parameters and affine shifts, and runs the Pell recurrence. It solved 8/8, and a broader 10,000-seed shipping sample solved every instance in at most 189 conservatively counted exact operations. That arithmetic gap is the claimed no-tool difficulty; there is no Track A distributional-hardness claim. Wall time is reported for reproducibility, not as the source of difficulty—the counted exact operations are the hardware-independent comparison.

## Worked demo

For `make_instance(n=9, seed=2)`, the full rendered mathematical data are:

```text
Find one integer solution of this bounded binary quadratic Diophantine equation.

An integer solution is an ordered pair (x,y) of ordinary base-10 integers for which the displayed polynomial is exactly zero. Multiplication is written with *, and x^2 means x*x.

Equation:
  -8*x^2 - 16*x*y - 7*y^2 + 16*x + 16*y - 9 = 0

Inclusive bounds:
  779 <= x <= 787
  -577 <= y <= -569

Both interval endpoints are included. The order matters: the first coordinate is x and the second is y. There are no floating-point approximations.

Give your final answer inside <answer></answer> tags as a JSON list of exactly two base-10 integers [x,y].
Example: <answer>[3,-17]</answer>
Output nothing else inside the tags.
```

The answer is `[782,-577]`; `verify(inst, [782,-577])` returns `(True, "ok")`. The corruption `[782,-576]` returns `(False, "exact substitution at (782,-576) gives -4425, not 0")`. A person can solve this smallest preset on paper by recognizing the Pell coordinate change or, less elegantly, checking the 81 bounded pairs.

## Difficulty presets

| Preset | `n` / interval width per coordinate | Candidate pairs | Status |
|---|---:|---:|---|
| demo | 9 | 81 | hand-scale illustration |
| easy | 2,003 | 4,012,009 | rejected by oracle: 3/3 solved |
| medium | 25,003 | 625,150,009 | rejected by oracle: 3/3 solved |
| hard | 250,007 | 62,503,500,049 | configured `SHIPPING_DIFFICULTY`; all calls hit quota before scoring |

Difficulty enlarges the box while the witness remains two integers. `escalate()` skips a measured over-effort rung, then offers `n=4000127` and `n=16000511`; it reports `cap_bound` before the following rung would exceed G9’s 300-operation route limit. Here `cap_bound` is an effort-cap diagnosis—the two-integer answer itself remains far below the character and atom caps.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose plus fenced JSON round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; space 62,503,500,049 |
| G5 | pass | exact count 1; density `1.5999104e-11`; strongest failed attack 65,536 candidates; reference mean 1,344,225 operations (see JSON for run-specific timings) |
| G6 | pass | four attacks each 0/8; exact reference and compact route each 8/8 |
| G7 | pass | doubling `n` quadruples the candidate space; planted answer still verifies |
| G8 | pass | 80 relabelling invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | maximum over 10,000 shipping seeds: 23 answer characters, 6 estimated tokens, 2 atoms, 189 intended operations; compact route failed 0 times |

## Oracle loop

The mandated harness produced the following bare-arm evidence before the key limit stopped it. `ok` means the returned pair passed exact verification. The four `hard` rows are redraws of one unconsumed slot, not four failed attempts.

| Preset | Seed | Model | Outcome | Why |
|---|---:|---|---|---|
| easy | 410792022 | `openai/gpt-5.6-terra` | solved | `ok` |
| easy | 671679334 | `google/gemini-3.8-flash` | solved | `ok` |
| easy | 997276591 | `google/gemini-3.8-flash` | solved | `ok` |
| medium | 1371340724 | `google/gemini-3.8-flash` | solved | `ok` |
| medium | 1502692967 | `openai/gpt-5.6-terra` | solved | `ok` |
| medium | 418219336 | `google/gemini-3.8-flash` | solved | `ok` |
| hard | 710816023 | `openai/gpt-5.6-terra` | error | HTTP 403 total key limit |
| hard | 2039749452 | `openai/gpt-5.6-terra` | error | HTTP 403 total key limit |
| hard | 405152564 | `openai/gpt-5.6-terra` | error | HTTP 403 total key limit |
| hard | 189853037 | `openai/gpt-5.6-terra` | error | HTTP 403 total key limit |

`harden.py` correctly stopped without writing a hardness verdict. Thus the configured `hard` preset is a candidate, not a shippable level.

## G9 diagnostics

| Arm | Valid solved/attempts | Error rows | Conclusion |
|---|---:|---:|---|
| bare | 0/0 at shipping `hard` | 4 | unavailable; no STEP 4 claim |
| structural | 0/0 | 4 | unavailable |
| placebo | 0/0 | 4 | unavailable |

Consequently `hinted - placebo` is undefined (`null` in the report) rather than evidence of zero structural help. The module records the arms as unrun. The configured structural hint only names the affine Pell coordinate system; it does not give the recovery procedure.

## Use

```python
from gen_2303_07825 import make_instance, render, parse_answer, verify

inst = make_instance(n=9, seed=2)
print(render(inst))
answer = parse_answer("<answer>[782,-577]</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful oracle rerun, emit samples with:

```bash
bash scripts/emit.sh 2303.07825 20
```

## Caveats

The exact density is for the uniform prior over the displayed integer box; it does not model a solver that recognizes the discriminant or the deliberately structured `D=m^2-1` family. Indeed, continued fractions, Lagrange reduction, or the included two-shear recovery make these instances easy with tools—that is why this is Track B. The panel did not implement a general continued-fraction solver, binary-quadratic-form reduction, or lattice reduction; it did run the complete bounded discriminant scan. The construction’s algebraic signature is demonstrably familiar to the current oracle pool at `easy` and `medium`, and may remain familiar at `hard`. Do not treat this directory as shippable until the bare loop produces a genuine `hardened` verdict and the two G9 diagnostic arms receive valid attempts.
