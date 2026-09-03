# Flat-folding NAE signal-consistency generator

| axis | declaration |
|---|---|
| native domain | `logic` |
| computational core | `csp_sat` |
| intended intuition | constraint satisfaction under signal-switching symmetry |

This is a **discretised analogue**, not a coordinate-level flat-folding family. `NATIVE["reduction"]` points to Section 3.3 and Theorem 2 of David Eppstein’s [*Computational Complexities of Folding*](https://arxiv.org/abs/2410.07666). The generator retains the reduction’s Boolean variable signals and signed not-all-equal clause gadgets, but discards crease geometry, coordinates, pleats, overlap order, and the bounded-ply embedding.

## Decision

This artifact is rejected and must not ship as a hard family. The selected shipping preset remains `medium` (`n=192`, `degree=7`), but random-restart WalkSAT finds a verified witness on every one of the eight G6 shipping seeds. On the shipping instance used for G4/G5, the same attack found a witness in 3.6501815889496356 seconds after 438,392 iterations and 12 started restarts. The declarations and measurements are complete; the failed hardness gates are intentionally preserved.

## What the problem is

The solver receives Boolean signal variables and signed NAE-3 clauses. A positive literal evaluates to its signal state and a negative literal to its complement. It must assign every signal so that no clause’s three evaluated bits are all equal. Verification checks one bounded Boolean assignment directly against every clause and never reads the planted answer.

`CERTIFICATE_LANGUAGE` declares one canonical signed-token representative per Boolean assignment. `random_candidate` samples that language uniformly, and `search_space(inst)` returns exactly `2^n`. The verifier additionally accepts reordered tokens as equivalent wire syntax; those aliases are not counted as distinct semantic candidates.

Section 3.3 fixes the NAE3SAT gadgets used by the paper’s reduction, and Theorem 2 transfers an ETH lower bound to the resulting flat-folding construction even at bounded ply. Theorem 1 identifies a tractable parameter regime in ply and cell-adjacency treewidth. Those results motivate the regular factor graphs here, but they do not prove this planted distribution hard—and the measurements show that it is not.

## Worked example (`easy`, seed 0)

```text
FLAT-FOLDING SIGNAL CONSISTENCY

A crease-pattern variable gadget has two possible local flat-folded
states, encoded 0 and 1.  Choose a state x_i for every signal i.
Each listed clause gadget touches exactly three signed signals and is
legal precisely when their three evaluated values are NOT all equal.
A token +i evaluates to x_i; a token -i evaluates to 1-x_i.
Thus each clause must contain at least one evaluated 0 and at least one
evaluated 1.

There are 12 signals, numbered 1 through 12 inclusive.
There are 24 clause gadgets:
C001: -5 -11 -9
C002: -3 +2 +1
C003: +8 -6 +9
C004: +7 +1 -4
C005: +9 -6 +5
C006: +6 +12 -11
C007: +6 -10 -12
C008: +4 -12 -2
C009: +9 -2 -11
C010: -5 +7 -10
C011: +9 +4 +2
C012: +12 +10 -4
C013: -3 +8 +6
C014: -7 -11 +10
C015: +5 -7 -1
C016: -12 -10 -11
C017: +1 +3 -8
C018: -4 +5 -8
C019: +11 +3 +1
C020: +5 +3 +1
C021: -6 -12 -4
C022: -8 +2 +3
C023: +10 -9 -7
C024: -2 -8 +7

Return exactly one signed integer for each signal.  Token +i means
x_i=1 and token -i means x_i=0.  Every absolute index 1..n must occur
exactly once; token order is irrelevant and repeated indices are not
allowed.

Give your final answer inside <answer></answer> tags, as a
space-separated list of the signed integers.
Example format: <answer>1 -2 3 -4 5 -6 7 -8 9 -10 11 -12</answer>
Output nothing else inside the tags.
```

The planted witness is `<answer>1 -2 -3 -4 -5 6 -7 -8 9 10 11 -12</answer>`. `verify` returns `(True, "ok")`; dropping the last token returns `(False, "wrong token count: expected 12, got 11")`.

## Difficulty presets

| preset | signals | degree | clauses | status |
|---|---:|---:|---:|---|
| `easy` | 12 | 6 | 24 | all three oracle attempts solved it |
| `medium` | 192 | 7 | 448 | selected shipping preset; rejected by G5 and G6 |
| `hard` | 240 | 7 | 560 | planted witness verified; not selected by the harness |

## Gate results

| gate | measured result |
|---|---|
| G1 | pass: 15/15 planted witnesses verified |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: 192 tokens recovered through prose and a Markdown fence |
| G4 | pass: 0/200,000 uniform semantic assignments verified at the shipping preset |
| G5 | **fail**: shipping density sample was 0/200,000, but WalkSAT found a verified witness in 3.6501815889496356 seconds, 438,392 iterations, and 12 started restarts |
| G6 | **fail**: WalkSAT solved 8/8 shipping seeds; literal imbalance, greedy, capped DPLL, and spectral rounding each solved 0/8 |
| G7 | pass: doubling from 192 to 384 signals doubled clauses from 448 to 896 and the plant verified |
| G8 | pass: 20/20 relabelled keys invariant, 20/20 carried witnesses valid, and 20/20 unrelated keys distinct |

The additional exact calibration at `n=18`, `degree=8` found 4 valid assignments among 262,144 candidates, a fraction of `1.52587890625e-05`. It is labelled calibration only and is not substituted for the shipping measurement.

## Oracle loop

| preset | model | seed | result |
|---|---|---:|---|
| `easy` | Grok 4.6 | 249939870 | solved and verified |
| `easy` | Claude Sonnet 5 | 1155090752 | solved and verified |
| `easy` | GPT-5.6 Terra | 1046440646 | solved and verified |
| `medium` | Claude Sonnet 5 | 1014878277 | failed; length-limited empty response |
| `medium` | Grok 4.6 | 712244960 | failed at clause C012 |
| `medium` | GPT-5.6 Terra | 1290825666 | failed at clause C001 |

The oracle harness called `medium` hardened, but G6 overrides that result: conventional local search solves the same preset cheaply.

## Use

```python
import random
import gen_2410_07666 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer("<answer>...</answer>")
ok, reason = gen.verify(inst, candidate)
```

From the repository root, diagnostic instances can be emitted with:

```bash
bash scripts/emit.sh 2410.07666 20 medium
```

## Caveats

- The zero-hit shipping density is an observed fraction under uniform complete assignments. It does not establish that the true density is zero and says nothing about guided search.
- The strongest tested attack succeeds, so the large `2^192` language is not evidence of practical difficulty. The wall time is specific to this run and machine; the success and iteration counts are the more portable findings.
- This CSP is only the signal-consistency layer of the paper’s geometric construction. It does not expose or verify actual crease coordinates, nonintersection, overlap order, pleat layout, or bounded ply.
- The panel did not run an industrial SAT solver or unrestricted stochastic search. Those omissions cannot rescue the family because the included WalkSAT attack already rejects it.
- `canonical_key` uses signed and unsigned spectral moments, not complete signed-hypergraph isomorphism, so nonisomorphic cospectral instances can theoretically collide.
