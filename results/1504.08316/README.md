# Verified problem generator for arXiv:1504.08316

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | exact linear algebra over GF(2) |
| Certificate | canonical signed-integer Boolean assignment |
| Intended intuition | constraint propagation through a hidden tight cycle |
| Domain essentiality | native |
| Reduction | none |

This module turns Abbe and Edwards, [“Concentration of the number of solutions
of random planted CSPs and Goldreich's one-way function candidates”](https://arxiv.org/abs/1504.08316),
into a supply of exact planted 3-XORSAT instances.  The solver receives Boolean
parity equations and must return a satisfying assignment.  Verification simply
checks the answer grammar and XORs the three submitted bits in every equation.

## Why it can be trusted

Generation is inverse: a uniform assignment is sampled before any public
constraint.  A random cyclic ordering supplies all consecutive three-variable
supports, and every right-hand side is evaluated on the plant.  If 3 does not
divide `n`, subtracting adjacent cyclic equations gives `x_i=x_(i+3)` in the
homogeneous system.  Cyclic closure and one original equation force every bit
to zero, so this subsystem is nonsingular and the public formula has exactly
one solution.  Additional constraints cannot introduce another solution.

Cycle supports and decoy supports have the same uniform marginal distribution
over three-subsets; their right-hand sides are generated identically.  Only the
joint incidence pattern distinguishes the planted subsystem.  The checker does
not read `inst["answer"]` and accepts any valid witness (uniqueness happens to
make that witness canonical).

## Why Track B, not Track A

Section 2.1 gives the CSP and planted-CSP definitions and explicitly includes
`k`-XORSAT.  Theorem 1 proves concentration of the normalized logarithm of the
solution count; it is not an inversion-hardness theorem.  Section 3 notes known
easy Goldreich predicates and says compatibility between concentration and
hardness is unclear, while Section 5 leaves that issue open.  A Track A claim
would therefore overstate the paper.

This family has a disclosed polynomial algorithm: dense Gaussian elimination
over GF(2), `O(m n^2)` in this implementation.  On eight candidate-shipping
instances (`n=83`, `m=283`) it solved 8/8, averaging **105,895 cell-level bit
XORs** and **0.016 s** per instance in the final recorded run.  The compact route is to recognize a
spanning tight cycle and follow its step-three recurrence, requiring **248
exact XORs** after recognition (95 support-search nodes on average in the
audited implementation).  The Track B claim is the gap between those routes in
a no-tool context, not average-case XORSAT hardness.

## Worked demo

The `demo` preset at seed 0 is hand-solvable:

~~~text
There are Boolean variables x0,...,x4. Find the unique assignment satisfying:
  E0000: x2 XOR x0 XOR x3 = 0
  E0001: x3 XOR x2 XOR x1 = 0
  E0002: x2 XOR x1 XOR x4 = 0
  E0003: x1 XOR x0 XOR x4 = 1
  E0004: x4 XOR x0 XOR x3 = 1
Return signed entries in variable order: +(i+1) for xi=1, -(i+1) for xi=0.
~~~

The answer is `<answer>[1, 2, -3, 4, 5]</answer>`.

~~~python
>>> verify(demo, [1, 2, -3, 4, 5])
(True, 'ok')
>>> verify(demo, [-1, 2, -3, 4, 5])
(False, 'equation E0000 is violated')
~~~

A person can solve this smallest setting by XOR elimination on five equations.

## Difficulty presets

| Preset | Variables | Equations | Compact XORs | Status |
|---|---:|---:|---:|---|
| demo | 5 | 5 | 14 | hand-scale illustration |
| easy | 11 | 15 | 32 | first oracle rung |
| medium | 83 | 283 | 248 | candidate shipping preset |
| hard | 98 | 398 | 293 | available escalation |

`SHIPPING_DIFFICULTY` currently names `medium`, but it is only a candidate until
the required oracle run completes.  A stronger hill-climbing audit rejected the
earlier 600-decoy medium setting (2/8 successes); a 32-seed sweep also found
successes at 300 and 400 decoys.  The current 200-decoy medium setting failed on
all 32 fresh sweep seeds, and the 300-decoy hard setting failed on another
32/32.  More satisfied decoys are not monotone here: they eventually make the
planted optimum easier for coordinate ascent.  `escalate()` uses the tested hard
rung and then returns `cap_bound`, because increasing `n` would push the compact
route beyond 300 XORs.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed plants verify and JSON round-trip; compact solver independently succeeds |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose and fenced JSON round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `2^-83` |
| G5 | pass | one certified shipping solution; demo count 1; 847,161 reference XORs/0.130 s and 12,026,368 hill-climb checks/3.524 s over eight instances |
| G6 | pass | four attacks each 0/8; Gaussian elimination 8/8 as expected |
| G7 | pass | doubled `n=166`, `m=566` instance builds and verifies |
| G8 | pass | 80/80 symmetry and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst case 324 characters, 81 estimated tokens, 83 atoms, 248 exact XORs |
| G9(a,b) | **blocked** | each arm reached 0 valid attempts because every vendor redraw returned HTTP 403 |

The four failing attacks are RHS-incidence majority, four-pass single-bit
coordinate descent, 32 random-restart two-pass hill climbs, and the obvious
all-zero no-tool ansatz.  The successful standard algorithm is reported only
under `reference_algorithm`, as Track B requires.

## Oracle loop and G9 arms

| Run | Solved / attempts | Outcome |
|---|---:|---|
| bare hardening | 0 / 0 valid attempts | blocked: all redraws were HTTP 403 account-limit errors |
| structural hint | 0 / 0 valid attempts | blocked: all four redraws were HTTP 403 account-limit errors |
| placebo hint | 0 / 0 valid attempts | blocked: all four redraws were HTTP 403 account-limit errors |

There is no hinted-minus-placebo estimate and no hardening verdict yet.  The
four error records per arm, produced by `harden.py`, remain in the three
transcripts; they are operational evidence, not failures by an oracle.  The
structural hint names only the invariant: “Some cyclic ordering of all variables
makes every three consecutive variables the support of an equation.”  Once
OpenRouter quota is restored, rerun the bare ladder and both isolated G9 arms,
then replace the module's `G9_ORACLE_RESULTS` with their actual counts.

## Use

~~~python
import json
from gen_1504_08316 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
candidate = parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
ok, reason = verify(inst, candidate)
~~~

From the repository root, after a successful hardening run:

~~~bash
python3 results/1504.08316/gen_1504_08316.py > results/1504.08316/selftest_report.json
bash scripts/emit.sh 1504.08316 20
~~~

## Caveats

This is a structured subfamily of the paper's planted 3-XORSAT objects, not a
sample from the independent binomial ensemble of Theorem 1, so it must not be
used as evidence for that ensemble's inversion hardness or concentration rate.
The exact `2^-83` guess density applies to a uniform prior over complete
canonical assignments; it does not imply computational hardness and is paired
with the successful elimination measurement for that reason.  The attack panel
does not include a production SAT solver, belief propagation, or advanced code
decoding; Gaussian elimination is stronger and exact for this linear class.
The canonical key uses incidence color refinement rather than exact hypergraph
isomorphism, so rare nonisomorphic collisions are theoretically possible.
Increasing the decoy count beyond the reported window can help local search
rather than hurt it; the retained presets reflect the measured safe window, not
a monotonicity theorem.  Finally, G9 and the multi-vendor oracle requirement
remain genuinely unmet until the external account limit is fixed; no success
claim is inferred from the failed API calls.
