# Cyclotomic odd-character sign polynomials (arXiv:1101.2994)

**Status: parked (`cap_bound`), not rejected and not ready for release.** The largest
legal answer was solved by one of three bare hard-oracle attempts. Making the same
family harder requires more than the 256 permitted coefficients, so `harden.py`
correctly stopped without declaring either the paper or the construction unsuitable.

| profile field | value |
|---|---|
| Track | B — an efficient exact algorithm is disclosed |
| native domain / object regime | algebra / rational exact |
| computational core / certificate | polynomial identity / dense sign polynomial |
| intuition | symmetry: complete root-of-unity orbit cancellation |
| domain essentiality | native; no reduction |

## Problem and trust model

[Feng and Xiang, *Cyclotomic Constructions of Skew Hadamard Difference
Sets*](https://arxiv.org/abs/1101.2994) define cyclotomic classes
`C_i = gamma^i <gamma^N>` in Section 1. Theorem 3.2 uses `N=2M`,
`M=p_1^m`, and a selector `I` containing one lift of every residue modulo `M`.
This generator uses its `m=s=1`, `p_1 = 7 (mod 8)` regime and constructs such a
selector by independent fair lower/upper lift choices.

The solver receives `I` and a formal primitive `2M`-th root `zeta`. It must return
the coefficient vector of `E(x)=sum_a (S_a/M)x^a`, where

`S_a = sum_(i in I) sum_(u=0)^(M-1) zeta^((2u+1)(a+i))`.

This is the exact odd-character sum in the proof of Theorem 3.2, not a graph
surrogate. For fixed `a+i`, the inner terms form a complete geometric orbit. All
orbits vanish except the unique selected lift complementary to `a` modulo `M`,
which contributes `+M` or `-M`. Generation composes those identities; verification
independently checks divisibility, parity, antipodality, and every coefficient. It
never reads `inst["answer"]` and uses no floating point.

## Why Track B

Track A would be false. Dense exact accumulation is a successful
`O(N M^2)` algorithm. At `M=127`, `N=254`, it performs **4,096,766** exact term
accumulations per instance; eight measured runs took **3.978104 s** total and
solved 8/8. Direct evaluation of the associated finite-field character sums would
range over `q=11^63` elements and is much larger.

The compact route is the cancellation step in the proof of Theorem 3.2: locate the
unique complementary lift for each residue and assign its sign. It takes 254 exact
operations once seen. Small `M`, or being handed this reduction as a procedure,
makes the task easy; the paper provides no computational hardness theorem. The
benchmark tests whether a no-tool solver discovers the orbit symmetry, not a
complexity-theoretic claim.

## Worked demo

For `make_instance(n=7, seed=3)`, `M=7`, `N=14`, and
`I=[8, 13, 9, 0, 4, 12, 3]`. The answer is

```json
[1, 1, 1, -1, -1, 1, 1, -1, -1, -1, 1, 1, -1, -1]
```

`verify(inst, answer)` returns `(True, "ok")`; flipping coefficient zero returns
`(False, "antipodal_rule_failed_at_0")`. A person can solve this demo on paper by
listing its seven odd-power orbit terms and grouping them geometrically.

## Difficulty and gates

| preset | requested/actual `M` | coefficients | dense terms | language size |
|---|---:|---:|---:|---:|
| demo | 7/7 | 14 | 686 | `2^7` |
| easy | 23/23 | 46 | 24,334 | `2^23` |
| medium | 71/71 | 142 | 715,822 | `2^71` |
| hard (last legal rung) | 127/127 | 254 | 4,096,766 | `2^127` |

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted answers verified and JSON round-tripped |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced model-style response round-tripped |
| G4 | pass | 0/200,000 structure-aware guesses; exact space `2^127` |
| G5 | pass | exact demo count 1/128; hard sample 0/200,000; reference 8/8 |
| G6 | pass | five attacks each 0/8; disclosed reference evaluator 8/8 |
| G7 | pass | doubled request chose `M=263` and verified |
| G8 | pass | 60/60 affine invariance/transports; 20/20 unrelated keys distinct |
| G9(c) | pass | 889 chars, 223 estimated tokens, 254 atoms, 254 operations |

## Oracle loop

The repository's current harness used its configured two-vendor pool. A preset is
defeated if any attempt solves it.

| preset | seed | model | result / reason |
|---|---:|---|---|
| easy | 898191116 | Gemini 3.8 Flash | solved |
| easy | 79541781 | GPT-5.6 Terra | solved |
| easy | 509594583 | Gemini 3.8 Flash | solved |
| medium | 749171710 | Gemini 3.8 Flash | solved |
| medium | 1498101469 | GPT-5.6 Terra | failed: antipodal error |
| medium | 1300610193 | GPT-5.6 Terra | failed: wrong length |
| hard | 928593466 | Gemini 3.8 Flash | failed: antipodal error |
| hard | 1149125989 | GPT-5.6 Terra | failed: antipodal error |
| hard | 1832562400 | Gemini 3.8 Flash | solved |

Final verdict: **`cap_bound`**. Easy and medium were defeated; hard was defeated by
one successful attempt; the next coefficient vector would exceed the output cap.

## G9 diagnostics

| arm at `M=127` | solved/attempts | verdict |
|---|---:|---|
| bare | 1/3 | hard level defeated |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Hinted-minus-placebo is **0.0**. The structural sentence bought no measured benefit
over placebo on these samples, so the run does not support a positive hint effect.
These arms are diagnostic, not gates. The gated caps are the 889-character,
254-atom answer and the 254-operation compact route, all within their limits.

## Use

```python
import json
import gen_1101_2994 as g

inst = g.make_instance(**g.DIFFICULTY["hard"], seed=42)
statement = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emission would be `bash scripts/emit.sh 1101.2994 20`,
but this parked result should not be emitted as a release family.

## Caveats

The family becomes easy immediately after the complete-orbit identity is noticed;
that is the intended Track B distinction. The `0/200,000` estimate samples uniformly
from sign polynomials already obeying the visible antipodal rule. It measures blind
guessing under that prior, not use of `I` or algebraic reasoning. The attacks cover
lift majority, sorted greedy alignment, random antipodal restarts, same-residue and
alternating ansatzes; they do not include a CAS, FFT-style cyclotomic reduction, or
explicit finite-field enumeration. The canonical key handles reorderings and affine
unit relabellings, not full equivalence of the developed designs. `gvlib` is probed
when available, but this family uses only standard-library exact integer arithmetic
and keeps working when `gvlib` is absent. Finally, the current oracle evidence spans
two vendors because that is the pool configured by the checked-in harness, despite
the task text describing a four-vendor pool.
