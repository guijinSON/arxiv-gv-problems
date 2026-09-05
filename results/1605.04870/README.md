# Verified t-multiple discrete logarithm generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | number theory |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | ordered integer exponent tuple |
| Intuition | decomposition: recognize a rank-one perturbation of the identity |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed: Section 4, Theorem 2 and equations (3)–(4) |

## What the problem is, and whether to trust it

This module turns Fu, Bao, Shi, and Wang's [*t-multiple discrete logarithm
problem and solving difficulty*](https://arxiv.org/abs/1605.04870) into exact
CRT-coordinate instances. The solver receives a product of prime-order modular
subgroups, `n` independent modular bases, and a target. It must return the
unique bounded exponent tuple whose base powers multiply to that target.

The instance shows both the modular CRT data and the discrete-log coordinates
licensed by equations (3)–(4). This is representational rather than native
black-box discrete-log hardness: the actual search is linear algebra over
`F_q`. Verification first substitutes the tuple into the exact coordinate
equation and then independently compares modular residues in every CRT factor.
It uses no floating point and never reads `inst["answer"]`.

Generation is inverse. It samples the exponent tuple `k`, chooses
`A = I + 1 v^T` with `1 + sum(v) != 0 (mod q)`, and emits `y = A k`. The matrix
determinant lemma makes `A` invertible, so the columns are independent order-`q`
bases and the bounded witness is unique. Prime testing is deterministic for the
module's 64-bit CRT factors. Rejection sampling makes `k` nonconstant, as required
to avoid Theorem 1's common-exponent collapse, and excludes every CRT component
where one base alone equals the target—the projection case in Theorem 2.

## Why this is Track B

The paper's Section 3 Definition 2 fixes the task and its independence
condition. Section 4 Theorems 1–2 describe easy collapses, while equations
(3)–(4) expose the linear system. The paper's exhaustive-search estimate and
claim that index calculus is unsuitable are not a theorem about this generated
distribution, so they do not support Track A.

Dense Gauss–Jordan elimination solves every generated instance in `O(n^3)`
field operations. At the tentative shipping preset (`n=74`, `q=10007`), the
recorded selftest measured 418,877 operations and 0.022 seconds; it succeeded on
8/8 adversarial-panel seeds. Enumerating the scalar correction instead costs
`q*n = 740,518` trials-by-coordinate. Once the rank-one decomposition is seen,
the tuple follows using at most `4n = 296` exact field operations. That gap—not
an unproved cryptographic claim—is the declared difficulty.

## Worked demo

For `make_instance(n=3, q=11, cofactor_start=20, seed=7)`, the rendered core is:

```text
N = 46386671
(p_j,h_j,target residue) = (331,270,85), (353,58,187), (397,290,126)
A = [2 3 10]
    [1 4 10]
    [1 3  0]       over F_11
y = [3, 2, 4]
```

The answer is `[10, 9, 0]`; `verify(inst, [10,9,0])` returns `(True, "ok")`.
Swapping its first two entries returns `(False, "coordinate 0 mismatch: product
log is 4, target log is 3")`. A person can solve this demo on paper by ordinary
three-variable elimination or by noticing that subtracting the identity leaves
three identical rows.

## Difficulty presets

| preset | n | q | answer-space bits | measured reference operations | status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 11 | 11 | 48 | hand-solvable illustration |
| easy | 30 | 1009 | 300 | 29,235 | not yet oracle-scored |
| medium | 52 | 5003 | 640 | 147,342 | not yet oracle-scored |
| hard | 74 | 10007 | 984 | 418,877 | tentative shipping preset |

`SHIPPING_DIFFICULTY` is currently `hard`. It remains tentative because the
required external oracle service was unavailable, as recorded below.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 witnesses verify; primes, exact orders, invertibility, and Theorems 1–2 regime checks pass |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `q^-n` |
| G5 | pass | demo has exactly 1 solution; hard sample density 0/200,000; reference 418,877 ops |
| G6 | pass | six attacks at 0/8; Gauss–Jordan solves 8/8 as expected |
| G7 | pass | doubled `n=148` instance builds and verifies |
| G8 | pass | 120/120 invariant keys, 120/120 carried witnesses, 20/20 unrelated keys distinct |
| G9 | **blocked** | answer 444 chars / 111 estimated tokens / 74 atoms; route 296 ops; oracle evidence unavailable |

The local report consequently says `all_passed: false`: this is deliberate and
honest, not a claim that the missing oracle calls failed to solve the family.

## Oracle loop and G9 arms

| run | preset | calls | outcome | reason |
|---|---|---:|---|---|
| bare | easy | 4 redraws | error | OpenRouter HTTP 403: key total limit exceeded |
| hinted | hard | 4 redraws | error | OpenRouter HTTP 403: key total limit exceeded |
| placebo | hard | 4 redraws | error | OpenRouter HTTP 403: key total limit exceeded |

No solved/attempts statistic or hinted-minus-placebo conclusion can be drawn:
API errors do not consume attempts and must never be counted as model failures.
`llm_loop_transcript.jsonl`, `g9_hinted_transcript.jsonl`, and
`g9_placebo_transcript.jsonl` are the harness-written error records. Once a
funded OpenRouter key is available, rerun all three arms and replace this table
with the script-owned evidence.

## Use

```python
from gen_1605_04870 import make_instance, verify, DIFFICULTY

inst = make_instance(seed=7, **DIFFICULTY["demo"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, after successful hardening:

```bash
python3 results/1605.04870/gen_1605_04870.py > results/1605.04870/selftest_report.json
bash scripts/emit.sh 1605.04870 20
```

The required bare harness command from this directory is:

```bash
python3 ../../scripts/harden.py gen_1605_04870.py
```

## Caveats

This is not evidence that the paper's proposed t-MDLP is cryptographically
secure. Publishing logarithmic coordinates deliberately makes this a Track B
compression task, and any CAS can solve it quickly. The 0/200,000 guess result
uses the exact stated uniform prior over `F_q^n`; it says nothing about solvers
that exploit the matrix. The adversary panel checks column statistics,
target-as-answer, diagonal-only and forward greedy rules, 64 scalar restarts,
and an average-shift ansatz. It does not test optimized sparse/bit-packed linear
algebra, because generic elimination is already acknowledged and measured as
the successful reference algorithm. Finally, the required multi-vendor and G9
evidence is absent until the OpenRouter spending-limit blocker is resolved, so
this directory is not ready for submission despite passing G1–G8.
