# arXiv:2506.12019 — verified Subset Sum generator

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | subset sum |
| Certificate | integer tuple (item IDs) |
| Intended intuition | symmetry |
| Domain essentiality | native |
| Reduction | none |

## What this family asks

The solver receives distinct positive integers with 1-based IDs and an exact
integer target, and must return a fixed-size subset of IDs whose values sum to
the target. This is the native problem defined in Section 1 of Thami Nkosi,
[“Algorithmic Structure in Subset Sum: Deterministic In-Bound Navigation and
the Counting Complexity Divide”](https://arxiv.org/abs/2506.12019), not the
paper's later SAT sketch or another surrogate. Verification only checks IDs,
distinctness, cardinality, and an exact integer sum.

The answer is known by inverse generation. Shuffled values are built in pairs
`M-g*q^i, M+g*q^i`, with `q` equal to 5 or 7. The generator first samples ten
pair positions and signs, then forms the target from those choices. A centre
larger than twice the total deviation forces every solution to contain exactly
ten items; uniqueness of balanced radix digits proves the planted subset is the
only solution. No completed instance is searched to manufacture its answer.

## Why Track B, and what is easy

The paper supplies no average-case hardness theorem for a planted distribution,
so this is deliberately not Track A. Section 3.13 says its own navigation is
output-sensitive `O(C)` in the number of in-bound candidates. It also identifies
sparse instances as easy, a middle density as harder, and excessive density as
easy again because solutions become abundant. Lemma 6 makes literal powers of
two directly decodable. Those facts rule out citing NP-completeness alone.

The disclosed mechanical route is cardinality-aware Horowitz–Sahni meet in the
middle, the `O(2^(n/2))` method listed in Section 3.13. At shipping `n=40`, eight
runs averaged 1,167,727 state visits and 5,468,684 counted operations (maximum
1,474,544 states and 7,089,798 operations). Wall time ranged from 0.22 s on an
unloaded run to 4.85 s on the final shared-host audit, so the operation and state
counts are the reproducible cost measures. The compact route notices equal-sum
pairs, takes deviations from their midpoint, and reads the target as a balanced
radix word. Its conservative arithmetic bound is 185 operations. The gap—over
a million mechanical states versus a short structural decode—is the Track-B
claim.

## Worked demo

For `make_instance(seed=0, n=8, k=3, scale_bits=2)`, the complete instance is:

```text
Target: 9945
1: 3749
2: 3455
3: 3623
4: 2573
5: 3599
6: 3605
7: 4631
8: 3581
Return exactly three distinct 1-based IDs.
```

The answer is `[1, 3, 4]`: `verify(inst, [1, 3, 4]) == (True, "ok")`.
Changing ID 4 to 5 gives `verify(inst, [1, 3, 5]) == (False, "subset sum differs
from target by 1026")`. A person can solve this demo on paper: opposite
extremes pair to 7204, their deviations from 3602 are `3,21,147,1029`, and the
target fixes three signed deviations.

## Difficulty presets

| preset | n | required IDs | scale bits | legal candidates | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 3 | 2 | 56 | hand-solvable illustration |
| easy | 28 | 10 | 16 | 13,123,110 | one oracle solved; escalation required |
| medium | 34 | 10 | 18 | 131,128,140 | not reached |
| hard | 40 | 10 | 20 | 847,660,528 | configured shipping preset; local gates pass |

`hard` is the intended shipping preset, but the result is not yet shippable:
the required external oracle evidence could not be collected with the supplied
OpenRouter key.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 20/20 planted witnesses verified; JSON round-trip checked |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged answer recovered from prose and a Markdown fence |
| G4 | pass | 0/250,000 legal uniform guesses; exact unique-witness probability 1/847,660,528 = 1.18e-9 |
| G5 | pass | shipping has one solution by construction and sampled density 0/250,000; demo enumeration is exactly 1/56; baseline figures above |
| G6 | pass | four attacks each 0/8; reference meet-in-the-middle 8/8 |
| G7 | pass | doubling to n=80 verifies; answer remains ten IDs; space becomes 1,646,492,110,120 |
| G8 | pass | 20 row-order, 20 positive-affine, and 20 reflected-affine composed checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst of 32 shipping seeds: 31 chars / 10 atoms / ≈8 tokens; intended route verifies in 185 operations |

The four failing attacks are closest-to-target-mean selection, residual-average
greedy selection, an in-context guess using alternating sides of the ten
innermost complementary pairs, and 512 uniform fixed-cardinality restarts.

## Oracle loop and G9 diagnostics

The script-owned bare run scored one model at `easy`, which solved correctly.
The other vendor then returned OpenRouter HTTP 403 `Key limit exceeded (total
limit)` on all four permitted draws; the harness correctly aborted rather than
treating API errors as model failures. The run therefore proves that `easy` must
not ship, but it does not decide `medium` or `hard`.

| preset | seed | model | scored result | reason |
|---|---:|---|---|---|
| easy | 365799881 | GPT-5.6 Terra | solved | returned a verified ten-ID subset |
| easy | 1941123870 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 62694413 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 1534906821 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 1400745199 | Gemini 3.8 Flash | error | HTTP 403 key limit |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 scored | blocked by key limit |
| structural hint | 0 / 0 scored | attempted; HTTP 403 key limit |
| placebo hint | 0 / 0 scored | attempted; HTTP 403 key limit |

Thus `hinted − placebo` is unavailable, not evidence of zero effect. The
structural hint names only the pair/radix invariant; it does not give a decoding
procedure. These zero-attempt diagnostics are an infrastructure limitation, not
a favorable hardness result.

## Use

```python
import gen_2506_12019 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer("<answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10</answer>")
ok, reason = g.verify(inst, candidate)
```

After a valid hardened run, emit records from the repository root with:

```bash
bash scripts/emit.sh 2506.12019 20 hard
```

## Caveats

The 0/250,000 guess result is conditional on the strongest obvious free prior:
a uniformly random set of exactly ten distinct IDs. It is not an estimate for
a solver that has recognized the complementary-pair code; that solver should
decode rather than guess. Meet in the middle was measured, but an LLL attack,
the paper's supplied C++ navigation code, and production SAT/ILP solvers were
not run. The construction's intended symmetry is itself a polynomial shortcut,
which is why this is Track B. Finally, no LLM-hardness conclusion is claimed:
`easy` was solved, while the quota failure prevented the required escalation and
all shipping-preset G9 measurements. Escalation keeps the ten-ID answer fixed
and grows the item haystack through `n=68`; it stops there because the next
compact decode would exceed G9's 300-operation ceiling, not because the answer
becomes longer.
