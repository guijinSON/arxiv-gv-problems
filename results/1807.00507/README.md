# Balanced n-fractions completion (arXiv 1807.00507)

> **Build status:** the generator and every local gate pass. The required external
> oracle run reached `hard`: two scored models failed there, but the third attempt
> could not be completed because the OpenRouter key exhausted its total quota.
> Those two failures are retained as evidence, but they are not a `hardened`
> verdict. Do not submit this result until the bare panel and the structural-hint
> and placebo runs finish.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple |
| Intended intuition | decomposition — find balanced three-fraction blocks with unit-fraction subtotals |
| Domain essentiality | native |
| Reduction | none |

## What the family is

Michael Codish's [*A SAT Encoding for the n-Fractions
Problem*](https://arxiv.org/abs/1807.00507) asks for nonzero decimal digits in
fractions `x/(10y+z)`, with bounded digit occurrences and total exactly one. This
module poses a native completion subfamily: every fraction row has one missing
digit, three rows form a band, and bands are grouped into panels with exact digit
counts. A witness is the flat list of missing digits.

Generation uses composition of identities, not search. Every stored three-row
template uses digits 1 through 9 exactly once and sums exactly to one of
`1/2, 1/3, 1/4, 1/6, 1/10`; the selected unit fractions sum to one. The generator
chooses templates and masks, then carries the already-known missing digits into the
answer. `verify` independently checks ranges, band distinctness, panel counts, and
the fraction sum by scaled integer arithmetic. It never reads `inst["answer"]`.

## Why this is Track B

There is no Track A claim. Sections 2.1--2.4 turn the digit and rational constraints
into finite integer constraints, and Section 3 compiles them to CNF with BEE and
solves them with Glucose. Table 1 reports 7.03 CPU seconds for the unconstrained
`n=18` puzzle and 102.20 CPU hours at `n=39`; those experiments are not a
distributional-hardness theorem.

For this generated completion distribution, the executable reference algorithm
enumerates all 51,840 count- and band-valid assignments for one nine-row panel and
meets their exact scaled sums against the second panel. Its complexity is `O(A*n)`
for the two shipping panels. Over eight audited shipping seeds it solved 8/8 in a
median about 0.48 seconds and 2,955,550 counted exact operations (maximum
3,972,242). This is the expected tool-enabled success and is recorded separately
from attacks.

The compact public route notices that each completed band contains digits 1 through
9 and has a unit-fraction subtotal. Only six assignments of the three complementary
digits remain per band; exact divisibility recognizes a unit fraction without access
to the private template table. Across six bands this takes 293 counted exact
operations. That route is short enough for G9(c), while the mechanical enumeration
is not executable by hand in context.

## Worked demo

`make_instance(seed=0, n=6, bands_per_panel=1)` renders in full as:

```text
BALANCED n-FRACTIONS COMPLETION

A fraction row (x,y,z) denotes x/(10*y+z); thus y and z are the tens and ones digits of a two-digit denominator. All digits are integers in the inclusive range 1..9, and repeated digits are allowed except where a band rule below forbids them.

There are n=6 fraction rows, divided into panels and three-row bands. Every row contains exactly one question mark.

Fill every question mark subject to all three rules:
1. In each three-row band, the three supplied missing digits are pairwise distinct.
2. In each panel, every digit 1..9 occurs exactly 1 time(s) among all numerator and denominator digit positions after completion.
3. The exact sum of all n completed fractions is 1.

Rule 2 implies that globally every digit occurs exactly n/3 times, which is the n-fractions occurrence bound. Panel and band order is only an ordering of terms; fraction rows may not be moved between the displayed bands when applying Rule 1.

Rows are numbered consecutively from 0. Data are written as `row: x y z`, with `?` marking the missing digit.

PANEL 0
  Band 0
    0: 5 ? 6
    1: ? 4 8
    2: 9 7 ?

PANEL 1
  Band 0
    3: 9 ? 2
    4: 3 4 ?
    5: ? 1 6

Output one flat JSON array of exactly 6 digits, in row-number order. Entry i replaces the question mark in row i. Do not output the fixed digits. JSON array order matters; no repeats are barred except by Rules 1 and 2.

Give your final answer inside <answer></answer> tags, as the JSON array just defined.
Example format: <answer>[1,1,1,1,1,1]</answer>
Output nothing else inside the tags.
```

The answer is `[1,3,2,7,8,5]`. A person can solve this demo on paper by testing the
six arrangements of each panel's three missing digits.

```python
>>> verify(inst, [1, 3, 2, 7, 8, 5])
(True, 'ok')
>>> verify(inst, [10, 3, 2, 7, 8, 5])
(False, 'digit at position 0 is outside 1..9')
```

## Difficulty presets

| Preset | Rows | Bands per panel | Structure-aware space at seed 0 | Status |
|---|---:|---:|---:|---|
| demo | 6 | 1 | 36 | hand-solvable illustration |
| easy | 9 | 1 | 216 | oracle run not completed |
| medium | 12 | 2 | 46,656 | oracle run not completed |
| hard | 18 | 3 | 2,687,385,600 | candidate shipping preset; local gates pass |

`SHIPPING_DIFFICULTY` presently names `hard`, but that is provisional until
`harden.py` returns a real verdict. `escalate` first merges the same six bands into
one panel, growing the haystack at the same 18-digit answer length. The next
supported longer instance would require more than 300 compact-route operations, so
the module then reports `cap_bound` rather than mislabelling an effort cap as
easiness.

## Local gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses; 21 exact template/decomposition checks; 12/12 JSON round trips |
| G2 | pass | empty, drop, range, duplicate, and swap corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose/fence; garbage returned `None` |
| G4 | pass | report seed: exact 1 valid / 2,687,385,600 candidates and 0/200,000 guesses; across 20 further shipping seeds, 1--6 valid and maximum density `2.233e-9` |
| G5 | pass | exact report-seed density `3.7210886297820456e-10`; baseline 4,115,210 operations and 0.661 s |
| G6 | pass | four attacks each 0/8; reference and compact routes each 8/8 |
| G7 | pass | doubled `n=36` witness verifies; space grows to 7,222,041,363,087,360,000 |
| G8 | pass | 80/80 invariant transforms, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 37 characters, 18 atoms, about 10 tokens, 293 intended operations |

The four failing attacks are nearest-visible-digit outliers, greedy equal panel
shares, 4,096 structure-aware random restarts per seed, and the in-context ansatz
that all bands have equal subtotals. The construction deliberately mixes one
`1/2` band with five `1/10` bands at the candidate shipping preset.

## Oracle loop and G9 arms

The bare ladder produced genuine scored results through two of the three `hard`
attempts. Errors are listed separately and do not count as model failures.

| Preset / arm | Normal solved / attempts | Current evidence |
|---|---:|---|
| bare `easy` | 3 / 3 | Gemini, Grok, and GPT all returned verified witnesses |
| bare `medium` | 1 / 3 | Gemini solved; Claude exhausted 32,000 output tokens and GPT returned a band-invalid answer; one Grok timeout was redrawn |
| bare `hard` | 0 / 2 | Claude exhausted 32,000 output tokens; GPT returned a count-valid answer with the wrong exact fraction sum |
| structural hint | 0 / 0 | not run because the bare three-model panel is incomplete |
| placebo hint | 0 / 0 | not run because the bare three-model panel is incomplete |

Hinted minus placebo is therefore undefined, and no conclusion about the intended
decomposition intuition is warranted yet. Four redraws for the third `hard` slot
returned HTTP 403 `Key limit exceeded`, after which the harness correctly aborted
without assigning a verdict. The required resumption command after quota is restored
is:

```bash
cd results/1807.00507
python3 ../../scripts/harden.py gen_1807_00507.py
```

After a hardened preset is known, run each G9 arm in its own scratch directory,
copy back the two transcripts, update `G9_RESULTS`, rerun `selftest`, and replace
this status section with the actual per-model table.

## Use

```python
from gen_1807_00507 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>[1,2,3]</answer>")
ok, reason = verify(inst, candidate)
```

Once the oracle evidence is complete, emit from the repository root with:

```bash
bash scripts/emit.sh 1807.00507 20 hard
```

## Caveats

- This is emphatically Track B. A short Python program, SAT/SMT solver, or the
  included exact meet-in-the-middle reference solves it; it is not evidence for
  complexity-theoretic hardness of n-fractions.
- Bands and panels are extra native-domain clues imposed on the paper's digit
  variables. They define a completion subfamily; the module does not reproduce the
  paper's unconstrained fixed puzzle at a given `n`.
- G4 samples uniformly only after enforcing the stated panel multiplicities and
  band distinctness. Its exact probability addresses that declared prior, not
  semantic heuristics; G6 covers four such heuristics but is not exhaustive.
- The arithmetic reference is a standard exact-sum meet-in-the-middle substitute
  for the paper's SAT route. Glucose itself was not installed and was not run.
- The templates are finite stored identities, though random masks, template choices,
  and orderings give distinct completion instances. The generator supports the
  paper-relevant bounded range through `n=36`, not unbounded `n` (the paper itself
  reports no solutions for `n >= 45`).
- The compact route sits close to the 300-operation cap (293). Its count includes
  decimal concatenation, exact division/multiplication, divisibility tests, and
  subtotal additions; it does not count visual scanning or writing the answer.
- Most importantly, external hardness is only partial: two distinct models failed
  the candidate shipping preset, but a third scored failure and both G9 comparison
  arms are still required after the OpenRouter quota is restored.
