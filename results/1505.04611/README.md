# arXiv 1505.04611 — cyclotomic intersection tables

> Build status: the generator and all local gates, including G9's only gated
> size/effort component, pass. The required external
> oracle runs are blocked because the supplied OpenRouter key returns HTTP 403
> `Key limit exceeded (total limit)`. The three script-owned error transcripts are
> preserved, but they are not claimed as hardness evidence; oracle hardening and
> the non-gated G9 diagnostic therefore remain incomplete.

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain / object regime | number theory / finite field |
| computational core | other (cyclotomic translate intersections) |
| certificate | indexed exact integer matrix/table |
| intuition | decomposition: `C0 union C1` omits the exponent of `-1` |
| domain essentiality | native |
| reduction | none |

## What the problem is and why it is checkable

The family comes from Michel and Ding, [*A Generalization of Combinatorial
Designs Related to Almost Difference Sets*](https://arxiv.org/abs/1505.04611),
especially Section 2 and the cyclotomic calculations in Lemma 3.1 and Theorem
3.2. In a prime field, the solver receives a primitive root and shifts of two
exponent sets: `C0` records exponents for which `alpha^z+1` is a nonzero square,
and `C1` those for which it is a nonsquare. For every shift, the solver returns
the sum of two exact intersection sizes. The witness is an indexed two-column
integer table. Verification uses only modular exponentiation, Euler's criterion,
and exact integer comparisons; it never reads the planted answer.

The arXiv source has a minor indexing typo: the definition says `i=1,2` and the
proof immediately uses `C0,C1`. The renderer pins down the standard literal
partition explicitly, and the implementation was checked against direct set
enumeration on small primes.

## Why Track B is the honest claim

The paper contains no search-hardness theorem, so Track A would be unsupported.
The ordinary literal algorithm builds the quadratic residues, constructs `C0`
and `C1`, and scans both intersections for each query. At the current hard
preset this is `O(q+nq)` time, 9,805,696 counted modular reductions,
multiplications, and membership tests, and roughly 0.2–0.5 seconds across local
audit runs (the final report records 0.38 seconds both for G5 and as the mean over the
eight G6 seeds; wall time varied with system load). The standard method solves 8/8, as
it should on Track B.

The compact route uses the proof's decomposition: `C0 union C1` contains every
exponent except the unique exponent of `-1`. A translate-intersection sum is
therefore controlled by the quadratic character of the one omitted translate.
The generated character arguments are small odd primes, so Jacobi reciprocity
classifies all 32 hard rows in 260 counted exact operations for the measured
shipping instance, with a generator-wide worst-case bound of 288. Theorem 3.2 is also
what makes the family easy with automation; there are no FPT or approximation
regimes to avoid because the paper is constructive rather than algorithmic.

## Worked demo

The `demo` preset with seed 0 renders the complete instance below. It is small
enough to solve by hand by listing squares modulo 41 (or using the omitted
exponent observation).

```text
q=41, alpha=6, exponents modulo 40
C0={z: 6^z+1 is a nonzero square mod 41}
C1={z: 6^z+1 is a nonsquare mod 41}
s_i=|C0 intersect (C0+w)|+|C0 intersect (C1+w)|

0: w=3,  x=11
1: w=6,  x=39
2: w=22, x=5
3: w=28, x=31

Each s_i is 18 or 19, with two of each.
```

The answer is `[[0,18],[1,19],[2,18],[3,19]]`, and
`verify(inst, answer)` returns `(True, "ok")`. Changing its first count to 19
returns `(False, "wrong balance between the two promised levels")`.

## Difficulty presets

| preset | rows `n` | prime `q` | balanced table space | status |
|---|---:|---:|---:|---|
| demo | 4 | 41 | 6 | hand illustration |
| easy | 28 | 65,537 | 40,116,600 | oracle unavailable |
| medium | 30 | 114,689 | 155,117,520 | oracle unavailable |
| hard | 32 | 147,457 | 601,080,390 | current provisional shipping setting |

`escalate()` first raises the modulus at fixed answer length through certified
prime/primitive-root pairs up to 2,013,265,921. It lengthens the table only after
that fixed-length axis is exhausted.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 preset/seed planted witnesses verified |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced, prose-surrounded JSON round-tripped |
| G4 | pass | 0/200,000 balanced guesses; exact density `1/601080390` |
| G5 | pass | shipping density above; demo count 1/6; reference 9,805,696 ops / 0.38 s in the final run |
| G6 | pass | four attacks each 0/8; literal reference algorithm 8/8 |
| G7 | pass | spaces strictly grow; doubled `n=64` builds and verifies |
| G8 | pass | 60/60 relabellings invariant and transported witnesses valid; 20/20 unrelated keys distinct |
| G9 | pass | 343 chars, 86 estimated tokens, 64 atoms, 260 measured operations (288 worst case) |
| G9 arms | incomplete diagnostic | OpenRouter quota prevented all scored bare, hinted, and placebo attempts |

## Oracle loop and G9 arms

| run | preset | seed(s) | solved | outcome |
|---|---|---|---|---|
| bare | easy | 353992312, 842357872, 1820122544, 285934117 | no scored attempts | four HTTP 403 quota errors; harness aborted |
| hinted | hard | 1492057091, 1277712190, 976702164, 864646990 | no scored attempts | four HTTP 403 quota errors; harness aborted |
| placebo | hard | 587221618, 1154897853, 1114966635, 387270727 | no scored attempts | four HTTP 403 quota errors; harness aborted |

The hinted-minus-placebo diagnostic is unavailable, so no conclusion about hint
responsiveness is claimed. Its stored numerical placeholder is `0.0`, not a
measured effect. Replenish or replace `OPENROUTER_API_KEY`, rerun the bare ladder,
then rerun both hard-preset arms before shipping.

## How to use it

```python
from gen_1505_04611 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, after a successful oracle run:

```bash
bash scripts/emit.sh 1505.04611 20
```

## Caveats

This is not a complexity-theoretic hardness claim. A CAS, a short Jacobi-symbol
program, or recognition of the omitted exponent makes every row easy. The G4
probability is for the exact promised prior—uniform balanced assignments of the
two displayed levels—not for arbitrary integer tables, and it measures guessing,
not reasoning. The generator conditions both answer classes on the same small
Jacobi-cost bound, but only magnitude, shift, parity, and 256 balanced random
restarts were tested; no external CAS, FFT batch-correlation code, or specialized
cyclotomy package was attacked. Most importantly, the four-vendor hardening and
G9 diagnostic arms have not completed because of external quota, so this directory
is not submission-ready despite the passing local mathematics and cap gate.
