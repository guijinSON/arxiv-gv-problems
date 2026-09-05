# arXiv:0906.1849 — coupled-parity 3-SAT generator

This is a verified Track B result. All exact gates pass, and the script-owned bare
oracle ladder selected `hard`: the configured two-vendor pool solved `easy` and
`medium`, then failed all three `hard` attempts. The structural-hint and placebo
diagnostics were attempted afterward but the bare run exhausted the OpenRouter quota;
their untouched error transcripts are retained and no hint-effect claim is made.

## Profile

| field | value |
|---|---|
| Track | B — an efficient reference algorithm is disclosed |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: one Boolean bit per variable |
| Intended intuition | invariant: four clauses encode a parity row and the coupled operator is an involution |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

The solver receives an ordinary 3-CNF formula and must return any satisfying Boolean
assignment. A signed integer `j` is `xj`, and `-j` is `NOT xj`. Verification evaluates
the three literals in every clause using exact Boolean operations. This is the native
search object in [Ghosh and Misra, *A Randomized Algorithm for
3-SAT*](https://arxiv.org/abs/0906.1849): Section 1 fixes the definitions and explicitly
uses 3-variable XOR formulae; Theorems 3.1 and 3.2 analyze them and DEL–PPZ.

For `n=2m`, a random directed cycle `p` defines a binary operator

```text
(Ax)_i     = x_i     XOR x_p(i) XOR x_(m+p(i))
(Ax)_(m+i) = x_(m+i) XOR x_p(i) XOR x_(m+p(i)).
```

Writing `A=I+N` gives `N^2=0` over GF(2), hence `A^2=I`. The generator samples `x`
first, computes `r=Ax`, randomly relabels variables, and expands every parity equation
into the four 3-CNF clauses forbidding wrong-parity triples. Extra rows are sampled
from the same marginal distribution and use the same four-clause representation. Their
triples form a linear 3-uniform packing and avoid core pairs: no individual row is a
format or sign outlier, while pair co-degree two identifies the correlated involutive
core. Since the core is invertible, the whole formula has exactly one solution. No
solver is used by `make_instance`.

## Why Track B

This is not a Track A claim. Section 1 says 2-SAT is linear-time, so that easy regime
is avoided. The paper's disjoint XOR example is also avoided because its components
separate immediately. At the hard preset there are `s=1`, 960 critical clauses, and
`T_av=12`; Theorem 3.2 therefore selects the `poly(n) * 1.5875^n` branch for the
paper's general-purpose randomized route. That is an upper bound, not evidence of
distributional hardness.

For this distribution, grouping equal unsigned triples and running exact GF(2)
Gaussian elimination is the honest reference algorithm, with expected
`O(M+n^3)` work. It solved 8/8 hard instances using 420,554 counted scalar operations
on average (454,114 maximum) and at most 0.004501 seconds in the recorded run. The
compact route recognizes the pair-cycle operator and applies `x=Ar`: 160 binary XORs.
It still inspects 3,840 literal occurrences to recover the rows; this bookkeeping cost
is disclosed because it is the main no-tool caveat. The gap between roughly 420,000
mechanical operations and 160 exact operations—not computational intractability—is
the Track B claim.

## Worked demo (`seed=7`)

A person can solve this smallest instance on paper by grouping the four clauses on
each unsigned triple and evaluating six parity equations.

```text
Find a satisfying assignment for the following 3-CNF formula.

There are Boolean variables x1 through x6. A positive signed integer j
means the literal xj; a negative signed integer -j means NOT xj.
Each displayed line is one clause: the OR of its three literals. The
whole formula is the AND of every clause. Variable indices are 1-based.
Every answer entry must be exactly 0 (false) or 1 (true).

n = 6; number of clauses = 24
Clauses:
C0001: -6 +3 -1
C0002: -4 +1 +5
C0003: +5 -3 +2
C0004: +6 +2 -1
C0005: -2 -3 -5
C0006: -6 -1 -2
C0007: -2 +3 -4
C0008: -4 -5 +6
C0009: +5 -2 +3
C0010: +4 -5 -6
C0011: +2 +3 +4
C0012: +3 +6 +1
C0013: -6 +1 +2
C0014: -1 -5 -4
C0015: +5 +4 +6
C0016: +6 -1 -3
C0017: -4 -3 +2
C0018: +1 -3 -6
C0019: +4 +1 -5
C0020: -2 -3 +4
C0021: +4 -1 +5
C0022: -2 +1 +6
C0023: -6 -4 +5
C0024: -5 +3 +2

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 6 bits in the order [x1,x2,...,x6].
Example format: <answer>[0,1,0,1]</answer>
The example only illustrates syntax; it does not have the required length.
Output nothing else inside the tags.
```

The answer is `<answer>[1,1,0,0,1,0]</answer>`.
`verify(inst, [1,1,0,0,1,0])` returns `(True, "ok")`. Flipping its first bit
returns `(False, "clause 12 is unsatisfied")`.

## Difficulty presets

| preset | n | decoy parity rows | clauses | status |
|---|---:|---:|---:|---|
| demo | 6 | 0 | 24 | hand-solvable illustration |
| easy | 24 | 24 | 192 | solved by 2/3 oracle attempts |
| medium | 48 | 96 | 576 | solved by 1/3 oracle attempts |
| hard | 80 | 240 | 1,280 | **ships; held against 3/3 attempts** |

`escalate()` first adds parity-row crowding at fixed answer length, then increases `n`.
`SHIPPING_DIFFICULTY="hard"`, matching the harness's `hardened` verdict.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged fenced JSON round-trips; answers are JSON-native |
| G4 | 0/200,000 uniform admissible assignments valid; exact language size `2^80` |
| G5 | constructed exact count 1; sampled 0/200,000; fixed reference 388,608 operations and 0.004908 s |
| G6 | seven attacks each 0/8; reference GF(2) algorithm 8/8 |
| G7 | doubled `n=160` instance verifies; search space grows `2^80` to `2^160` |
| G8 | 20/20 composed relabellings and 20/20 pair-polarity changes invariant; 20/20 carried witnesses valid; 20/20 unrelated keys distinct |
| G9(c) | 161 characters, about 41 tokens, 80 atoms, 160 exact XORs; compact solver verifies |

The attacks are sign majority, occurrence median, public-order alternation,
label-based pair orientation, `2n` greedy clause repairs, 512 pair-aware random
restarts over only `2^40` orientations, and local parity-RHS voting. The successful
Gaussian route is reported separately, as Track B requires.

## Oracle loop and G9 arms

The bare loop used master seed `3966999533770291671`, effort `medium`, and the
script's configured OpenAI/Google pool. `easy` and `medium` were defeated, and `hard`
held. A hard Gemini response derived most variables but ended at the response-length
limit before emitting `<answer>`; this is recorded as a failed attempt, not hidden.

| preset | seed | model | solved | result |
|---|---:|---|---:|---|
| easy | 151425499 | OpenAI Terra | no | clause 4 unsatisfied |
| easy | 242416563 | Gemini 3.8 Flash | yes | verified |
| easy | 48189836 | Gemini 3.8 Flash | yes | verified |
| medium | 393134179 | Gemini 3.8 Flash | yes | verified |
| medium | 1909360909 | OpenAI Terra | no | clause 30 unsatisfied |
| medium | 2141266422 | OpenAI Terra | no | clause 15 unsatisfied |
| hard | 1841965180 | OpenAI Terra | no | clause 7 unsatisfied |
| hard | 1478485780 | Gemini 3.8 Flash | no | length-limited; no tagged answer |
| hard | 2090061675 | Gemini 3.8 Flash | no | clause 103 unsatisfied |

| G9 arm at hard | scored solved/attempts | API-error calls | conclusion |
|---|---:|---:|---|
| bare | 0/3 | 0 | hardened |
| structural hint | 0/0 | 4 | unavailable after quota exhaustion |
| placebo hint | 0/0 | 4 | unavailable after quota exhaustion |

Hinted-minus-placebo is undefined because the two diagnostic arms had no scored
attempts; `0.0` is only a neutral machine-readable placeholder. Nothing can be
concluded about whether the stated involution hint helps. The bare verdict and the
answer-size/operation measurements are independent of that diagnostic failure.

## Use

From the repository root:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("g", "results/0906.1849/gen_0906_1849.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=123, **g.DIFFICULTY["hard"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

Emit with `scripts/emit.sh 0906.1849 20 hard`.

## Caveats

The family becomes easy for code that groups the parity blocks and performs GF(2)
elimination; that is intentional. `P(guess)=0/200,000` concerns the uniform prior over
all syntactically valid 80-bit answers. It does not model parity-aware reasoning; the
pair-aware restart panel gives a stricter practical check but still samples only 512
of `2^40` orientations.

The compact arithmetic count excludes the 3,840 literal inspections and associated
grouping, so a no-tool failure may still reflect bookkeeping volume. One hard Gemini
attempt in fact found nearly the whole parity solution but exhausted 32,000 response
tokens before producing a witness; this is evidence that at least part of the measured
difficulty is bookkeeping/output discipline. No industrial
CDCL/PPSZ implementation, Schöning walk, or repeated DEL–PPZ implementation was run;
the exact parity/Gaussian algorithm is stronger on this distribution. The canonical
key normalizes variable renumbering, input ordering, pair-member exchange, pairwise
literal complementation, and cycle rotation. It deliberately uses a coarser pair-cycle
hypergraph invariant rather than attempting full signed-CNF isomorphism; 20 unrelated
seeds remained distinct. Finally, the structural and placebo G9 diagnostics remain
unavailable because the successful bare run exhausted the external quota, so the data
supports the bare no-tool hardness claim but not any claim about hint sensitivity.
