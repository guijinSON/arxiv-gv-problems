# Binary directional coverage from cyclic parity blocks

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT expressed as binary directional coverage |
| Certificate form | exact symbolic fixed-width hexadecimal projection word |
| Intended intuition | change of variables: cancel adjacent cyclic windows |
| Domain essentiality | native |
| Reduction | none; the solver receives the paper's binary coverage object directly |

## What the family is

[Schneider and Maier, *Soft Tuy-Completeness for Robust Projection Selection in
Cone-Beam CT* (arXiv:2605.24023)](https://arxiv.org/abs/2605.24023) defines the
binary directional decision problem by a projection-by-direction matrix
`B`, a projection budget `k`, and a required coverage threshold `L` (Corollary
1). The solver receives exactly that finite coverage object. It must select at
most `n` of `2n` candidate projections and cover every sampled plane-normal
direction. Private directions force exactly one choice from each projection
pair, so the witness is written without ambiguity as an `n`-bit hexadecimal
word.

Generation is inverse. It samples the answer word first. Each three-bit parity
condition is expanded into four directions: a direction lists the three
projection choices that cover it and is left uncovered by exactly one of the
four wrong-parity patterns. Composing all four directions therefore certifies
one parity equation. A cyclic system of `n` such equations is nonsingular when
`3` does not divide `n`, and additional random balanced equations add crowding
and instance diversity. The generator only evaluates the sampled word while
building these columns; it never solves the emitted instance.

`verify` decodes any candidate word, validates the incidence blocks, and checks
every displayed coverage column directly. It does not read `inst["answer"]`.
All arithmetic and comparisons are exact integers; there are no floats or
external dependencies.

## Why Track B

Section 2 proves the unrestricted binary directional problem NP-complete via
Set Cover, but that worst-case theorem does not establish hardness of this
distribution. More importantly, Section 4.2 supplies an `O(kmz)` greedy
approximation, and Sections 6.1 and 8 show that it is exceptionally effective on
the paper's realistic CT data: the pooled median greedy/MILP objective ratio is
0.998, 72/240 greedy solutions are certified optimal, and 215/240 MILP runs
certify an optimum. A Track-A claim would therefore be misleading.

An efficient exact algorithm also exists for this constructed distribution.
Decode each four-direction block as one GF(2) equation and run Gauss--Jordan
elimination. Its complexity is `O((n+d)n^2)` scalar bit operations for `d`
decoy blocks. Across eight shipping seeds it solved 8/8, averaging **189,997
scalar operations**, 2,896 row XORs, and **0.0019--0.0037 s** across repeated
local runs. A clause-level DPLL
stand-in for the paper's MILP integer search also solved 8/8, averaging 63,287
literal inspections, 9.5 nodes, and 0.0053--0.0097 s. The actual Gurobi branch-and-cut solver was
not available and is listed as an untested attack below.

The compact route uses the blocks repeated twice. Their triples are consecutive
length-three windows around a hidden cycle. XORing adjacent equations cancels
their two shared variables and gives a step-three recurrence; because
`gcd(3,n)=1`, one traversal reaches every bit. One original equation chooses
between the provisional word and its complement. The conservative count is
`5n+8`, or **298 exact operations** at shipping. This is a no-tool compression
claim: 185,237 routine operations versus a short change of variables, not a
claim of cryptographic or distributional hardness.

## Worked demo

For `make_instance(n=5, decoys=1, seed=7)`, the complete rendered question is:

```text
Select projections that cover every sampled plane-normal direction.

Definitions and conventions.
There are candidate projections P(r,b), where r is an integer from 0
through 4 and b is 0 or 1. A direction is covered when at least
one selected projection appears in its displayed covering set. Different
directions are independent, including identical-looking repeated copies.
You may select at most k=5 projections. The threshold is L=49,
so all 49 directions must be covered.

Private directions.
For every r there is one direction v_r covered by exactly {P(r,0),P(r,1)}.
These private directions and the budget force every feasible selection to
contain exactly one projection from each pair r.

Remaining direction blocks.
A block with multiplicity C represents C distinct copies of each of its
four displayed directions. Repeated copies have the same covering set.
Block order, direction order, and order inside a covering set have no meaning.
  block 0 C=2: {P(1,0),P(3,1),P(0,0)} ; {P(1,1),P(3,0),P(0,0)} ; {P(0,1),P(1,0),P(3,0)} ; {P(0,1),P(1,1),P(3,1)}
  block 1 C=2: {P(1,1),P(4,0),P(2,1)} ; {P(2,0),P(4,0),P(1,0)} ; {P(1,0),P(4,1),P(2,1)} ; {P(1,1),P(2,0),P(4,1)}
  block 2 C=2: {P(0,0),P(2,0),P(3,0)} ; {P(2,1),P(3,0),P(0,1)} ; {P(2,1),P(0,0),P(3,1)} ; {P(0,1),P(3,1),P(2,0)}
  block 3 C=2: {P(2,0),P(0,0),P(4,1)} ; {P(2,1),P(4,0),P(0,0)} ; {P(0,1),P(4,0),P(2,0)} ; {P(2,1),P(0,1),P(4,1)}
  block 4 C=1: {P(4,0),P(0,1),P(1,1)} ; {P(0,0),P(1,1),P(4,1)} ; {P(4,0),P(1,0),P(0,0)} ; {P(0,1),P(4,1),P(1,0)}
  block 5 C=2: {P(4,1),P(1,0),P(3,1)} ; {P(3,0),P(1,1),P(4,1)} ; {P(3,1),P(1,1),P(4,0)} ; {P(3,0),P(1,0),P(4,0)}

Required witness and exact encoding.
Return one hexadecimal word z of exactly 2 digits and value below 2^5.
Leading zeroes are required. Bit r of z is counted from the least-significant
bit: bit 0 is the rightmost binary bit. Bit r=0 selects P(r,0), and bit
r=1 selects P(r,1). Thus z denotes exactly 5 distinct projections, with
no repetitions and no ordering ambiguity. Hexadecimal letter case is ignored.
Find any z whose selected projections cover every direction.

Give your final answer inside <answer></answer> tags as exactly the required
2 hexadecimal digits, without a 0x prefix.
Example format only: <answer>07</answer>
Output nothing else inside the tags.
```

The answer is `<answer>12</answer>`. `verify(inst, "12")` returns `(True,
"ok")`; `verify(inst, "00")` returns `(False, "direction 3 in block 0 is
uncovered")`. A person can solve this smallest setting by checking 32 words or
by doing the five-equation cancellation cycle.

## Difficulty presets

| Preset | `n` | Decoy blocks | Projections | Directions | Answer digits | Compact operations | Bare-oracle result |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 5 | 1 | 10 | 49 | 2 | 33 | hand-scale; skipped by hardening |
| easy | 23 | 20 | 46 | 287 | 6 | 123 | solved 3/3 |
| medium | 41 | 80 | 82 | 689 | 11 | 213 | solved 2/3 |
| **hard (ships)** | **58** | **180** | **116** | **1,242** | **15** | **298** | **failed 0/3; hardened** |

The named ladder raises both the answer entropy and crowding. After `hard`,
`escalate` grows only the decoy haystack, keeping the 58-bit witness and
298-operation compact route fixed.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 planted checks over every preset; every answer JSON-round-trips |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: a 15-digit word recovered through prose and a Markdown fence |
| G4 | pass: 0/200,000 structure-aware guesses; exact density `1/2^58 = 3.4694e-18` |
| G5 | pass: exactly one shipping answer; strongest failed attack used 28,304 candidate/flip evaluations in 1.2--2.3 s across repeated runs |
| G6 | pass: six attacks each 0/8; GF(2), DPLL, and compact references each 8/8 as expected |
| G7 | pass: doubled `n=116` instance built and verified; directions grew 1,242 to 1,764 at fixed decoys |
| G8 | pass: 40/40 composed relabellings invariant, 40/40 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass: 17 JSON characters, about 5 tokens, 58 semantic projection choices, 298 operations |

Exact timings, individual attack rows, and corruption reasons are in
`selftest_report.json`; timings naturally vary between runs.

## Bare oracle loop

| Preset | Seed | Model | Solved | Result |
|---|---:|---|---|---|
| easy | 634702988 | openai/gpt-5.6-terra | yes | word verified |
| easy | 687979613 | google/gemini-3.8-flash | yes | word verified |
| easy | 252229452 | google/gemini-3.8-flash | yes | word verified |
| medium | 209466523 | google/gemini-3.8-flash | yes | word verified |
| medium | 339927415 | openai/gpt-5.6-terra | no | claimed inconsistency; no tagged answer |
| medium | 1954690653 | google/gemini-3.8-flash | yes | word verified |
| hard | 1420695262 | google/gemini-3.8-flash | no | proposed word left block 0, direction 3 uncovered |
| hard | 244789189 | openai/gpt-5.6-terra | no | proposed word left block 6, direction 1 uncovered |
| hard | 1947867055 | openai/gpt-5.6-terra | no | proposed word left block 0, direction 3 uncovered |

The script-owned verdict is `hardened` at `hard` after two escalations. All
three hard replies were either correctly parsed and rejected by exact coverage
or contained no answer; there is no parser-induced false failure.

## G9 arms

| Arm | Solved/attempts at shipping | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 1/3 | one model found a valid word |
| placebo hint | 2/3 | two models found valid words |

`hinted - placebo = -1/3`. The structural hint did not outperform the matched
control, so this experiment does **not** support a causal claim that naming the
cycle invariant helped. The difference may reflect seed/model variation at only
three trials per arm. The hinted arm's diagnostic verdict is `too_easy`, which
does not block shipping under the post-2026-09-05 rule. The gated measurements
remain 17 characters, about 5 tokens, 58 semantic elements, and 298 exact
operations.

## How to use it

```python
import random
import gen_2605_24023 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer("Reasoning... <answer>12</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.random_candidate(inst, random.Random(1)) is not None
```

From the repository root, emit verified shipping instances with:

```bash
bash scripts/emit.sh 2605.24023 20 hard
```

The module is standard-library-only and performs no file I/O, network access,
or printing at import.

## Caveats

- This is deliberately Track B. Recognizing the parity quartets makes exact
  polynomial-time GF(2) elimination available; no Track-A average-case claim is
  made.
- The `0/200,000` estimate samples uniformly from the exact statement-aware
  language of one projection per private pair. It estimates blind-word density,
  not the success probability of a structured solver. The exact unique-solution
  argument is stronger for cardinality but still says nothing about algorithmic
  search cost.
- Duplicate core blocks are a visible structural signal. The intended challenge
  is recognizing their parity and cancellation interpretation, not locating a
  statistically hidden planted row.
- The paper's actual Gurobi MILP with LP relaxation, cuts, and certified bounds
  was not run because it is not an allowed dependency. DPLL is only a
  dependency-free exact-feasibility stand-in. No spectral method is relevant to
  this set-cover/CSP object, and no industrial CDCL/XOR-SAT solver was tested.
- Random decoy triples are logically redundant once the unique cyclic core is
  solved. They enlarge the displayed coverage haystack and generic elimination
  workload, but not the compact route.
- `canonical_key` is complete for the construction's arbitrary variable
  renamings, independent truth-label swaps, and storage permutations by reducing
  to the recovered cycle's dihedral normal form. It is not a general incidence-
  matrix isomorphism algorithm outside this family.
- The binary coverage matrices are native objects of Corollary 1, but they are
  abstract incidence matrices; the module does not claim that every generated
  column is realizable by physical source positions and unit-sphere directions.
  Accordingly the native domain is combinatorics, not geometry or CT physics.
