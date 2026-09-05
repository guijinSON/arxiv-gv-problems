# Verified LIMSAT witness generator for arXiv:1803.09963

> Status: the module and every local gate pass, but this result is **not yet
> shippable**. The required OpenRouter oracle run was attempted and aborted after
> every request returned HTTP 403 (`key limit exceeded`). The transcript records
> API errors, not model failures; no hardness result has been invented.

## Profile

| Field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: one Boolean truth vector |
| Native objects | sparse LIMSAT literal-clause incidence system; Boolean assignment |
| Intuition | invariant: a maximum-codegree pair sits inside a four-triple bit-recovery subsystem |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Guo et al., [*An Efficient Method to Transform SAT problems to
Binary Integer Linear Programming Problem*](https://arxiv.org/abs/1803.09963).
Section II.B and equation (2) turn CNF clauses into a sparse binary linear
inequality model: each clause requires the sum of its selected literal values to
be at least one. The solver receives those clause columns directly and must
return a truth vector satisfying every inequality.

Generation is inverse. It samples the answer first, divides the variables into
hidden components, and makes many three-variable XOR equations true under that
answer. Each XOR equation is represented by its exact four-clause CNF/LIMSAT
block. A protected full-rank subset makes the answer unique. `verify` never reads
`inst["answer"]`: it validates each four-clause encoding and evaluates the
displayed 0–1 inequalities exactly.

## Why Track B

This is deliberately not a Track A claim. The paper itself builds the LIMSAT
matrix in polynomial time and solves it with Gurobi; Section III reports runs
from seconds to thousands of seconds. For this generated distribution, an even
more specialized polynomial method exists: recognize every four-clause XOR
block and use exact GF(2) Gauss–Jordan elimination. Its complexity is
`O(M*N^2)` scalar Boolean operations. At the provisional hard preset, seed
314159 required 797,482 counted operations and 0.042 seconds; over eight attack
seeds the mean was 673,978 operations and 0.042 seconds (maximum 1,137,791).

The compact route notices the support invariant. In each component, four parity
labels on four anchor variables recover those bits, and the protected anchor
pair recovers every remaining bit. The intended route counts `2n = 224` XORs at
the hard preset. That is short enough in principle but not a mechanical scan or
elimination a no-tool solver can casually execute. The missing oracle run means
this practical claim still awaits the required independent evidence.

## Worked demo

The demo below is seed 11. It is genuinely hand-solvable: group each row as one
three-variable parity constraint, recover either four-variable component from
its four rows, and repeat for the other component.

```text
There are 8 Boolean variables y_1,...,y_8. A +i literal is y_i and a -i
literal is 1-y_i. Every parenthesized triple must have literal sum at least 1.

R1: (+2 -1 +3) ; (+2 +1 -3) ; (-2 +3 +1) ; (-2 -3 -1)
R2: (-7 -1 -2) ; (+2 -1 +7) ; (+1 -2 +7) ; (-7 +1 +2)
R3: (+7 -1 -3) ; (-1 +3 -7) ; (-7 +1 -3) ; (+1 +3 +7)
R4: (+7 +2 -3) ; (-2 +7 +3) ; (-3 -7 -2) ; (+3 +2 -7)
R5: (-4 +6 -5) ; (-4 +5 -6) ; (+6 +4 +5) ; (-5 +4 -6)
R6: (-4 +8 -5) ; (+8 +5 +4) ; (-5 -8 +4) ; (+5 -8 -4)
R7: (+8 -4 +6) ; (-6 +4 +8) ; (-8 -4 -6) ; (+6 +4 -8)
R8: (-8 +6 +5) ; (+8 +5 -6) ; (+8 +6 -5) ; (-5 -6 -8)

<answer>[1, 0, 1, 0, 0, 1, 1, 1]</answer>
```

`verify` returns `(True, "ok")`. Flipping the first bit returns
`(False, "row R1 column 3 has literal sum 0 < 1 (...)")`.

## Difficulty presets

| Preset | n | Components | Random-row coverage | Status |
|---|---:|---:|---:|---|
| demo | 8 | 2 | 100% | hand example; not shipped |
| easy | 64 | 10 | 75% | local gates pass |
| medium | 88 | 12 | 88% | local gates pass |
| hard | 112 | 14 | 95% | provisional shipping preset; local gates pass |

Escalation first raises redundant-row coverage at fixed answer length, then
reduces the component count so each component contains more same-form parity
rows. It reports `cap_bound` after exhausting that crowding axis because a longer
answer would push the compact route beyond 300 operations.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verify; JSON round-trip checked |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged answer recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware uniform binary guesses |
| G5 | pass | shipping density 0/200,000; demo exact count 1/256; baseline 797,482 operations |
| G6 | pass | four attacks, 0/8 successes each; reference eliminator 8/8 |
| G7 | pass | doubled instance at n=224 builds and verifies (2,034 XOR groups) |
| G8 | pass | 60 invariance and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 336 chars, 84 estimated tokens, 112 atoms, 224 intended XORs |

The four failing attacks are occurrence-rank guessing, literal-polarity
majority, 256 uniform random restarts, and a myopic one-pass clause repair. The
polynomial XOR/GF(2) solver is correctly reported as the Track B reference
algorithm, not disguised as a failing attack.

## Oracle loop and G9 diagnostics

The required bare run reached only the first (`easy`) level. The service refused
all calls before any model answered:

| Arm/preset | Calls | Solved | Outcome |
|---|---:|---:|---|
| bare / easy | 4 | 0 | all API errors (HTTP 403 key limit); no hardness verdict |
| structural hint | 0 | 0 | not run |
| placebo hint | 0 | 0 | not run |

Consequently `hinted - placebo` is not estimable, and there is no conclusion yet
about whether the stated invariant helps models. The local G9(c) caps pass, but
the three-arm diagnostic must be rerun with a working OpenRouter key. Each arm
must use its own scratch directory because `harden.py` overwrites transcripts.

## Use

```python
import importlib.util

spec = importlib.util.spec_from_file_location("g", "results/1803.09963/gen_1803_09963.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=11, **g.DIFFICULTY["demo"])
statement = g.render(inst)
candidate = g.parse_answer("<answer>[1,0,1,0,0,1,1,1]</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

The numeric directory is not a normal Python package name, so callers load the
module by path, as the repository scripts do. From the repository root, after a
successful oracle rerun:

```bash
bash scripts/emit.sh 1803.09963
```

## Caveats

- The family is easy with tools. XOR recognition plus elimination solves every
  measured instance; this is the point of the honest Track B label.
- `0/200,000` estimates density under a uniform prior over all correctly shaped
  bit vectors. It does not model a solver that recognizes parity or learns the
  component structure. The exact construction has one solution.
- A protected anchor pair has unusually high support codegree. It reveals the
  compact route but not its truth values; the occurrence-rank answer attack still
  failed 0/8. This is an intentional structural signal, not Track A evidence.
- Generic CDCL, a commercial MILP solver, SMT, and LP relaxations were not run.
  The exact XOR eliminator is stronger for this distribution, but those omitted
  attacks should still be measured if the benchmark's threat model changes.
- `canonical_key` is invariant under variable renaming, independent polarity
  switches, and all input reorderings. It uses support size, degree, pair
  codegree, and row-count signatures rather than solving hypergraph isomorphism;
  rare non-isomorphic collisions remain possible and are disclosed.
- Most importantly, the four-vendor hardening and both G9 diagnostic arms are
  outstanding because the available API key was quota-blocked. Do not treat the
  current transcript as evidence that any oracle failed the mathematics.
