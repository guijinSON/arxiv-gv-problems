# Integer triangles with a prescribed circumradius/exradius ratio

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `polynomial_identity` |
| Certificate | `integer_tuple` (the three side lengths) |
| Intended intuition | `change of variables` through semiperimeter deficiencies, the paper's quartic, and its elliptic curve |
| Domain essentiality | `native`; no reduction or discretised surrogate |
| Disposition | **Rejected prototype retained as `rejected_gen_2512_15237.py`** |

## Problem and trust status

The source is Halbeisen, Hungerbühler, and Shamsi Zargar, [*Integer triangles with a rational ratio of circumcircle radius to excircle radius*](https://arxiv.org/abs/2512.15237).  An instance gives a reduced rational number `N=P/Q`, an inclusive integer interval, and an order for the side roles `f,g,h`.  The solver must return three distinct odd side lengths in that interval that form a strict triangle and satisfy

`N = 2*f*g*h / ((f+g+h)*(f-g-h)*(g-h-f))`,

where `h` is the side touched by the chosen excircle.  Checking a witness is only range/parity/triangle testing and one exact integer cross multiplication.  `verify` accepts every valid witness and never reads the planted answer.

Generation is inverse and exact: it samples the three sides first from the same bounded language used by `random_candidate`, then computes and reduces `N`.  It rejects the paper's explicit square families and additional-square-torsion regime.  G1–G8 pass, but the family is rejected at G9(c): after recognizing the elliptic-curve substitution, a solver still has to perform the unbounded rational-point search.  The required four-vendor oracle evidence is also **not complete**: the supplied OpenRouter key returned HTTP 403 “Key limit exceeded” on every redraw.  The error-only transcript is preserved rather than replaced with invented results.

## Why this is Track A

Equations (2)–(3) in Section 1 fix the radius identity.  Section 2 constructs the quartic and elliptic curve.  Theorems 2 and 3 identify triangle recovery with finding a suitable non-torsion rational point on

`v^2 = u^3 + 2(2N^2+2N-1)u^2 - (4N-1)u`.

The paper does **not** prove NP-hardness.  A provisional Track A claim was tested on three random distinct odd 256-bit sides: the domain-standard bounded-height search tested 96,666 reduced rational `u` coordinates over eight instances and found none in 29.31 seconds, while four construction-aware attacks also failed.  That is evidence of expensive search, not of the compact mathematical route G9 requires.  On the fixed shipping instance, the same failed search already used 12,639 point trials—over the 300-operation cap—and still supplied no witness.  Accordingly the Track A claim is not shipped.

The easy regime to avoid is explicit.  Theorem 4 writes down triangles for `N=m^2+1` and `N=m^2-1`; generation tests exact rational squareness and excludes both.  The torsion points in Section 3 do not produce triangles.  A preliminary 96-bit version was also discarded because factoring the ratio numerator exposed too much of the sampled sides; a representative 256-bit numerator did not finish under GNU `factor` in a 15-second diagnostic.

## Worked demo

With `make_instance(n=4, lower_eighths=4, seed=1)`, the complete mathematical payload is:

```text
Target reduced rational ratio N = 26/55.
Every side must be a distinct odd integer in [8,15].
The answer position order is [f,g,h], and h is the distinguished excircle side.
Find a strict triangle with
R/r_h = 2*f*g*h / ((f+g+h)*(f-g-h)*(g-h-f)) = 26/55.
Output: <answer>[f,g,h]</answer>
```

The answer is `<answer>[11,9,13]</answer>`.  `verify(inst, [11,9,13])` returns `(True, "ok")`; swapping the distinguished side gives `verify(inst, [13,9,11]) == (False, "the exact circumradius/exradius ratio is not the target")`.  This demo has only 24 syntactically valid candidates and exactly two witnesses (the `f/g` swap), so it is genuinely hand-solvable by enumeration.

## Difficulty presets

| Preset | Side bits `n` | Lower endpoint | Candidate-space bits | Status |
|---|---:|---:|---:|---|
| `demo` | 4 | `4/8 * 2^n` | 5 | hand example only |
| `easy` | 256 | `7/8 * 2^n` | 756 | tested prototype; rejected by G9(c) |
| `medium` | 320 | `6/8 * 2^n` | 951 | available escalation |
| `hard` | 384 | `4/8 * 2^n` | 1146 | available escalation |

Larger presets widen the allowed interval as well as raising coefficient entropy; the answer remains exactly three integers.  A doubled `n=512` instance built and verified in the scaling gate.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted answers verified and JSON-round-tripped |
| G2 | pass | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced model-style answer parsed and verified |
| G4 | pass | 0 hits / 200,000 structure-aware uniform candidates; declared space has 756 bits |
| G5 | pass | shipping density 0/200,000; demo exact count 2/24; strongest baseline 96,666 nodes and 29.31 s |
| G6 | pass | landmark 0/8, greedy 0/8, random restart 0/8, factor grouping 0/8, elliptic height search 0/8 |
| G7 | pass | all named spaces strictly grow; `n=512` still verifies with 3 answer atoms |
| G8 | pass | 60/60 relabelling/composition checks and 20/20 distinct unrelated keys |
| G9(c) | **fail** | answer is only 238 characters/3 atoms, but the post-insight route already used 12,639 exact point trials without finding a witness; 18 was merely verification cost |

## Oracle loop and G9 diagnostics

The bare run reached no scored attempt.  These are script-produced errors, not model failures and not evidence of hardness.

| Preset | Seed | Model | Result | Why |
|---|---:|---|---|---|
| `easy` | 653705929 | Claude Sonnet 5 | error, not scored | OpenRouter HTTP 403 key limit |
| `easy` | 1484592741 | Grok 4.6 | error, not scored | OpenRouter HTTP 403 key limit |
| `easy` | 310155127 | Claude Sonnet 5 | error, not scored | OpenRouter HTTP 403 key limit |
| `easy` | 1535509886 | Claude Sonnet 5 | error, not scored | OpenRouter HTTP 403 key limit |

| G9 arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0 / 0 | not run; provider rejected every call |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

`hinted - placebo` is therefore undefined; the `0.0` placeholder in `selftest_report.json` must not be interpreted as an effect estimate.  Once quota is restored, rerun each arm in its own scratch directory and update the module evidence before shipping.

## Use

```python
from rejected_gen_2512_15237 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
answer = parse_answer("<answer>" + str(inst["answer"]).replace(" ", "") + "</answer>")
assert verify(inst, answer) == (True, "ok")
```

This is a rejected prototype and must not be emitted.  If a future construction supplies a genuine compact route and passes a fresh oracle run, the normal command from the repository root would be:

```bash
bash scripts/emit.sh 2512.15237 20 easy
```

## Caveats

Track A rests on a generated distribution and measurements, not a theorem of computational hardness.  More importantly, its expensive search is exactly why it fails the no-tool suitability requirement: there is no compact post-insight route.  The height-128 elliptic search is exact but shallow; Sage/Magma descent, ECM-assisted factor grouping, LLL, and a serious general Diophantine solver were not available under the dependency rules and were not tested.  The 0/200,000 guess result describes the stated uniform prior over ordered distinct odd triples only; it does not bound a solver using arithmetic structure.  Full integer factorization can reveal side factors when cancellation is small, and a stronger factor-and-partition attack remains a risk.  No oracle or G9 arm was scored because of the external quota failure, but that outage is not the rejection reason: the measured G9(c) failure is.
