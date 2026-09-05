# Canonical curves with low apolarity — verified generator

Status: **parked (`cap_bound`), not shipped and not rejected**. The local G1–G9(c)
checks pass, but the required bare oracle loop solved the largest admissible preset.
The next size exceeds the 300-operation no-tool cap.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | exact symbolic |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## The problem

The source is Ballico, Casnati, and Notari, [*Canonical curves with low
apolarity*](https://arxiv.org/abs/1003.3035). An instance gives every coefficient
of a rational cubic in the paper's divided-power monomial basis. The solver must
give a compact Walsh-character change of variables specifying linear forms
`L_a` for which `f = sum L_a^[3]`. The checker reconstructs those forms and
expands every divided cube with integer arithmetic; it does not read the planted
answer.

Section 1 fixes the relevant objects. Formula (1.1) defines the divided-power
action, Lemma 1.6 is the Apolarity Lemma relating a power-sum decomposition to an
apolar point set, and Theorem 1.7 identifies the `GL` orbit of the Fermat cubic
with the minimum-apolarity case. The generator remains in that native `GL`
orbit. It does **not** replace the cubic by a graph or finite-field surrogate.

## Why Track B

This paper supplies a classification, not a computational-hardness theorem.
Theorem 1.7 says precisely that the Fermat orbit is an easy structural regime,
so Track A would be false. The implemented reference method forms all exact
contraction matrices, inverts one, and performs simultaneous matrix-pencil
recovery. Its complexity is `O(n^4)` exact arithmetic; at `n=32` it solved 8/8,
with a median 2,297,919 operation slots and 2.54 seconds.

The compact route is to recognize the hidden Walsh-character basis. Repeated-index
coefficients fingerprint the Walsh spectrum, a single contraction slice carries
the hidden XOR law, and the inverse Walsh transform recovers the signed cube
scales. At `n=32` this is counted as 255 small exact operations. The gap is what
Track B was meant to test, but the oracle pool found the route at every tested
size.

## Worked demo

For `make_instance(n=4, scale_floor=2, seed=0)`, the rendered cubic is

```text
(0,0,0):-80  (0,0,1):224  (0,0,2):-42  (0,0,3):154  (0,1,1):-80
(0,1,2):154  (0,1,3):-42  (0,2,2):-80  (0,2,3):224  (0,3,3):-80
(1,1,1):224  (1,1,2):-42  (1,1,3):154  (1,2,2):224  (1,2,3):-80
(1,3,3):224  (2,2,2):-42  (2,2,3):154  (2,3,3):-42  (3,3,3):154
```

Its planted certificate is
`{"labels":[2,0,1,3],"scales":[4,2,3,5]}`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last label
returns `(False, "labels must contain exactly 4 entries")`. A person can solve
this demo on paper by comparing its four diagonal coefficients and one small
coefficient slice.

## Difficulty presets

| Preset | n | Scale floor | Nonzero cubic terms (seed 0) | Rendered chars | Outcome |
|---|---:|---:|---:|---:|---|
| demo | 4 | 2 | 20 | 1,692 | hand example; hardener skips it |
| easy | 8 | 5 | 120 | 3,226 | oracle solved 3/3 |
| medium | 16 | 9 | 816 | 14,923 | oracle solved 3/3 |
| hard | 32 | 17 | 5,984 | 112,678 | oracle solved 2/3; intended ship preset defeated |

There is no shipping preset. `SHIPPING_DIFFICULTY="hard"` records the last
tested candidate, not a release decision. `escalate()` returns `cap_bound`: the
verified `n=64` instance has 45,760 terms, but its compact route needs 575
operations, above the G9(c) limit.

## Gate results

| Gate | Result |
|---|---|
| G1 | 12/12 planted certificates verified |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | JSON/prose/fence round-trip passed |
| G4 | 0/200,000 structure-aware random candidates valid |
| G5 | demo has exactly 24/9,216 valid; shipping sample 0/200,000; strongest failing attack 2,048 nodes in 20.13 s |
| G6 | five attacks at 0/8; reference method 8/8, 2,297,919 median operations |
| G7 | doubled `n=64` instance built and verified (45,760 terms) |
| G8 | 60/60 relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | 226 chars, 57 estimated tokens, 64 atoms, 255 intended operations |

## Bare oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 206774527 | Gemini 3.8 Flash | solved | exact witness verified |
| easy | 1170648516 | GPT-5.6 Terra | solved | exact witness verified |
| easy | 2084885031 | Gemini 3.8 Flash | solved | exact witness verified |
| medium | 356591744 | Gemini 3.8 Flash | solved | exact witness verified |
| medium | 758002046 | GPT-5.6 Terra | solved | exact witness verified |
| medium | 1208386591 | GPT-5.6 Terra | solved | exact witness verified |
| hard | 553746208 | Gemini 3.8 Flash | solved | exact witness verified |
| hard | 851280016 | GPT-5.6 Terra | failed | coefficient `(0,0,0)` mismatch |
| hard | 1875153704 | Gemini 3.8 Flash | solved | exact witness verified |

## G9 diagnostic arms

| Arm | Solved/attempts | Interpretation |
|---|---:|---|
| bare | not separately run | the required bare ladder above is the decisive evidence |
| hinted | 0/0 | not run after `cap_bound` |
| placebo | 0/0 | not run after `cap_bound` |

The hinted-minus-placebo difference is therefore not measured. Per the task's
`cap_bound` rule, the extra arms were not purchased after the family became
ineligible to ship; no transcript has been invented.

## Use

```python
from gen_1003_3035 import make_instance, verify

inst = make_instance(n=4, scale_floor=2, seed=0)
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

If this parked family is later reactivated, emit samples from the repository
root with `bash scripts/emit.sh 1003.3035`. Do not submit it under the present
oracle verdict.

## Caveats

The generated cubics are a highly structured rational subfamily of the Fermat
`GL` orbit, not arbitrary canonical curves, and the module does not construct a
curve whose Artinian reduction yields each cubic. It covers the paper's native
apolar cubic/decomposition object, not its geometric classification.

The `0/200,000` estimate is relative to the declared prior: independent uniform
coordinate permutations and signed permutations of the allowed scale
magnitudes. It is not a bound against structure-aware recovery; the oracle
results demonstrate that distinction sharply. The coefficient-histogram
`canonical_key` is invariant under variable relabelling but is only a strong
cheap invariant, not a complete cubic-isomorphism test. Numerical tensor methods,
Gröbner-basis decomposition, and external CAS implementations were not tested.
