# Exact congruence witnesses for dynamic unit disks

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | geometry |
| object regime | rational exact |
| computational core | linear algebra |
| certificate form | exact symbolic |
| intended intuition | invariant — recover the two-color parity of a concealed affine lattice |
| domain essentiality | native |
| reduction | paper-licensed; Section 5.5, Theorem 5 |

This generator is based on Bhore, Nöllenburg, Tóth, and Wulms,
[“Fully Dynamic Maximum Independent Sets of Disks in Polylogarithmic Update
Time”](https://arxiv.org/abs/2308.00979). It presents insertion-only sequences
of closed unit disks with exact rational centers. The solver returns one affine
congruence rule per panel; expanding the rules must select the requested number
of pairwise-disjoint disks. The checker evaluates the congruences and compares
squared rational distances exactly. It never reads the planted answer.

Trust status: G1–G8 pass and the script-owned hard bare oracle run held 0/3.
G9 is **incomplete, not passed**: the hard hinted arm has one genuine failure,
after which OpenRouter exhausted its key limit; the placebo arm could obtain no
non-error response. The module is therefore ready except for external oracle
quota, but it is not submission-ready and `selftest_report.json` says
`all_passed: false` rather than inventing the missing evidence.

## Family and construction

Section 1 defines geometric independent set as a pairwise-disjoint disk
subcollection. Section 5.5 proves Theorem 5 by inserting every disk of a static
unit-disk instance one by one, which licenses the insertion-only form here. In
each panel an odd square grid is transformed by an exact rational rotation,
scale, and translation. Neighboring grid sites intersect and every other pair
is disjoint. One checkerboard class is therefore known before generation.

For lattice directions `e1,e2` from an even corner `(X0,Y0)`, the expression

```text
(e2_y-e1_y)(X-X0) + (e1_x-e2_x)(Y-Y0)
```

equals `det(e1,e2)` times the sum of the two lattice coordinates. Its zero
class modulo `2*abs(det)` is the planted symbolic witness. This is a
transformation of a known instance, not a solution recovered by search.

## Why Track B

This distribution has an efficient exact algorithm, so no Track A claim is
made. The reference implementation reconstructs all disk intersections in a
panel, finds a degree-two corner, two-colors the lattice, and converts the
larger color class back to a congruence. Its complexity is `O(P*n^4)` with the
implemented all-pairs geometry step. At hard it used 776,160 exact distance
tests plus 13,440 incidence scans (789,600 operations total) and averaged about
0.18 seconds.

The compact route recognizes the lattice directly and derives each rule from
two directions. It is measured at 272 exact operations for all eight shipping
panels. The first several displayed centers are deliberately collinear, raw
small-modulus coordinate parity is masked, and coefficients are large enough
that neither route is mechanically comfortable without tools.

The easy regimes were taken seriously. The paper’s introduction notes a static
PTAS for unit disks; Theorem 1 maintains a 12-approximation with `O(log n)`
worst-case updates, and Lemma 4 supplies its four shifted-grid bound. Those
methods do not emit the exact congruence requested here. The generated lattice
regime itself is nevertheless polynomial-time solvable by the reference
algorithm above, which is why the family is explicitly Track B.

## Worked demo

For `make_instance(n=3, panels=1, coord_bits=5, seed=0)`, the complete disk
block in the rendered statement is:

```text
PANEL 0 SCALE 94 TARGET 5
1 -246 203
2 -153 327
5 -122 110
6 -60 451
4 -29 234
7 2 17
8 64 358
3 95 141
0 188 265
END_PANEL 0
```

Every center is `(X/94,Y/94)` and every radius is 1. A valid response is:

```text
<answer>{"rules":[{"a":1543,"b":1549,"c":31,"m":1550}]}</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the rules by
an empty array returns `(False, "wrong rule count: expected 1, got 0")`. The
demo is genuinely hand-scale: it has nine disks, one rule, a 19-operation
compact derivation, and five selected disks.

## Difficulty presets

| preset | grid side | panels | disks | coordinate bits | rule integers | rendered chars (seed 0) | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 1 | 9 | 5 | 4 | 1,997 | hand example; skipped by hardening |
| easy | 13 | 4 | 676 | 16 | 16 | 24,267 | solved 3/3 in the original bare ladder |
| medium | 17 | 6 | 1,734 | 24 | 24 | 70,125 | bare held, but structural hint solved 1/2 completed attempts |
| hard | 21 | 8 | 3,528 | 32 | 32 | 159,234 | **shipping candidate; bare held 0/3, G9 incomplete** |

After hard, `escalate()` raises coefficient entropy at fixed grid and answer
shape, up to the answer cap. The answer is not lengthened to manufacture
difficulty.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 realistic tagged/fenced responses parsed; garbage rejected |
| G4 | 0/200,000 structure-aware bounded-rule guesses; observed probability 0 |
| G5 | shipping density 0/200,000; exact count unavailable; reference 776,160 distance tests + 13,440 scans, about 0.18 s |
| G6 | axis outlier, first-three greedy, 256 random restarts, and small-modulus ansatz all 0/8; reference algorithm 8/8 as expected |
| G7 | doubled-size 14,792-disk instance and fixed-shape coefficient escalation both verified |
| G8 | 20/20 composed invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | **incomplete**; 731 chars, 183 conservative tokens, 32 atoms, 272 intended operations all fit, but hinted/placebo oracle evidence is incomplete |

Exact values are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The final hard bare run used reasoning effort `medium` and is preserved in
[`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl).

| preset | model | seed | solved | exact result |
|---|---|---:|---:|---|
| hard | GPT-5.6 Terra | 504593590 | no | panel 3 selected 1 instead of 221 |
| hard | Claude Sonnet 5 | 1272036654 | no | panel 0 selected 441 instead of 221 |
| hard | Gemini 3.1 Pro Preview | 969742841 | no | panel 0 selected 1 instead of 221 |

The original ladder evidence is retained as
`g9_medium_bare_transcript.jsonl`: easy was solved 3/3, while medium held 0/3
after two Grok timeouts were discarded and redrawn.

## G9 arms

| hard arm | solved / completed attempts | status |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 1 | incomplete: one failure, one incomplete body, then key-limit 403s |
| placebo hint | 0 / 0 | incomplete: all calls key-limit 403s |

The numerical hinted-minus-placebo value is reported as `0.0`, but no
conclusion should be drawn from it because the denominators are incomplete.
At medium, the structural hint did help: Terra solved after Gemini failed, so
G9(b) correctly forced the single permitted move to hard. Hard’s answer is 731
characters (183 conservative tokens), 32 atomic integers, and the compact route
is 272 operations.

## Use

```python
from gen_2308_00979 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

Once G9 has three completed hinted and placebo attempts and the report is
regenerated, emit from the repository root with:

```bash
bash scripts/emit.sh 2308.00979 20 hard
```

## Caveats

- The hard family is not yet shippable because OpenRouter’s key limit prevented
  completion of G9. Refill/replace `OPENROUTER_API_KEY`, rerun the isolated hard
  hinted and placebo directories, update `_ORACLE_EVIDENCE`, and rerun
  `selftest()`.
- `0/200,000` is a sampled rate, not proof of zero density. The prior is uniform
  over the exact bounded grammar, including many rules that select the wrong
  number of disks. It is structure-aware about answer shape and coefficient
  bounds, but it is not a learned prior conditioned on likely lattice moduli.
- The reference algorithm is intentionally reported because this is Track B.
  A faster lattice-recognition or spatial-hashing implementation would lower
  its wall time; the benchmark claim concerns unaided exact execution, not
  computational intractability.
- The adversary panel did not try an SMT solver, integer-relation software,
  lattice reduction, or a vision-assisted parser. It did test the construction’s
  coordinate outliers, the tempting first-three basis, small raw parities, and
  random bounded formulas.
- The 159k-character hard prompt is large. Although the answer and intended
  mathematics fit the stated caps, some model failure may reflect navigation
  through exact input as well as recognition of the invariant.
- `canonical_key` is complete for generated square panels through exact
  pair-distance multisets and ignores their irrelevant separated placement; it
  is not a general canonizer for arbitrary disk configurations.
