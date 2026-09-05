# Exact MUB overlap phases from rank-one bent quadratics

| profile | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | exact symbolic |
| intended intuition | symmetry: detect a scalar identity plus a rank-one form |
| domain essentiality | native |
| reduction | none |

This generator is based on William M. Kantor’s [“MUBs from bent
functions”](https://arxiv.org/abs/2605.17594). It hands the solver a symmetric
quadratic-form matrix `Q` over `F_3` and fourteen linear label differences.
For every one of fourteen labels it asks for the exact additive-character sum that is the inner
product of two of the paper’s unnormalised MUB phase vectors. The answer is a
compact factorisation in the exact ring
`Z[zeta]/(zeta^2+zeta+1)`, not a floating-point approximation.

Trust status: **shipping-ready at `medium`**. All local G1–G9(c) gates pass.
The script-owned bare hardening ladder found `easy` solvable once in three tries,
then held `medium` at 0/3 and set the hardened verdict. The current harness used
its configured two-vendor pool; two of the three `medium` failures were empty
provider `content_filter` responses, which the harness explicitly scores as
unsolved attempts. That limitation is recorded below rather than hidden.

## Construction and Track B claim

Section 2 defines
`e_(a,B)=sum_v zeta^(a·v+B(v)) e_v`, defines bent differences, and proves in
Theorem 2.1 that a mubent set produces mutually unbiased bases. Example 2.2
specialises to quadratic functions `v M v^T/2`: nonsingular matrix differences
are bent. Section 4 explains that the construction is not a new classification
and that essentially all known odd-characteristic examples are quadratic.

For each generated instance,

```text
Q = lambda I + mu r r^T  over F_3,
det(Q) = lambda^(n-1) (lambda + mu r^T r),
Q^-1 = lambda^-1 I
       - mu lambda^-1 (lambda + mu r^T r)^-1 r r^T.
```

The generator samples these factors first and composes the determinant and
inverse identities to obtain its witness. It never runs the dense solver.
Completing the square gives the exact overlap

```text
alpha_j = chi(det Q) (-1-2*zeta)^n zeta^(d_j^T Q^-1 d_j).
```

The checker independently performs dense Gauss–Jordan elimination over `F_3`,
recomputes the determinant character and every quadratic phase, and compares
them exactly. This is an efficient `O(n^3+q n^2)` algorithm, so the family makes
no Track A claim. At shipping size it used 160,211 field operations in the
fixed G5 measurement and averaged 159,863 operations over eight G6 seeds
(about 0.007 s in the final self-test). The compact rank-one route uses at most 261
field operations. The paper makes magnitudes immediate, so asking only for
`|alpha|^2` would be an easy constant-answer family; fourteen varying exact
phases avoid that regime.

## Worked demo

`make_instance(n=3, queries=3, changes=1, seed=0)` renders the following full
instance:

```text
Exact phases of quadratic MUB overlaps over F_3

All arithmetic in exponents is modulo 3.  Let F_3={0,1,2} and let zeta be
a formal primitive cube root of unity, so zeta^3=1 and
zeta^2+zeta+1=0.  Vectors have 3 coordinates indexed 0 through 2.

For the symmetric 3 by 3 matrix Q below and each listed label vector d_j,
define the exact character sum

  alpha_j = sum over x in F_3^3 of
            zeta^( 2*x^T*Q*x + d_j^T*x ).

Here 2 is 1/2 in F_3.  These are inner products of the unnormalised phase
vectors e_(a,B) used for mutually unbiased bases: Q is the matrix of the
quadratic bent-function difference and d_j is the label difference.  The
given Q is nonsingular, but no factorisation or inverse is supplied.

Q (one space-separated row per line):
1 2 1
2 1 1
1 1 1
END_Q

Label vectors d_j (query index, then 3 space-separated residues):
0 1 2 2
1 1 0 0
2 1 1 1
END_LABELS

Return one exact factorised certificate.  The integer sign must be -1 or 1,
and phases must contain exactly 3 integers, in query order, each in
{0,1,2}, such that for every j

  alpha_j = sign * (-1 - 2*zeta)^3 * zeta^phases[j].

The equality is exact in Z[zeta]/(zeta^2+zeta+1); no decimal approximation is
allowed.  Query order matters and repetitions among phase values are allowed.

Give your final answer inside <answer></answer> tags as one JSON object with
keys "sign" and "phases".  Format-only example:
<answer>{"sign":1,"phases":[0,0,0]}</answer>
Output nothing else inside the tags.
```

Its answer is `<answer>{"sign":-1,"phases":[1,0,1]}</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last phase
returns `(False, "too few phases: expected 3, got 2")`. The demo is genuinely
hand-scale: it has only 27 summands per overlap, although the rank-one route is
shorter.

## Difficulty presets

| preset | dimension | queries | rendered chars (seed 0) | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 3 | 1,477 | 4 | hand example; skipped by hardening |
| easy | 23 | 14 | 3,199 | 15 | one bare oracle solve; rejected as shipping rung |
| medium | 47 | 14 | 7,231 | 15 | **ships; bare oracle held 0/3** |
| hard | 83 | 14 | 17,599 | 15 | available but not reached by the bare ladder |

`escalate()` raises only the ambient matrix dimension, leaving the certificate
at fifteen atoms, and stops before the 300-operation compact-route cap. G7
separately verifies a size-doubled dimension-94 instance, where the same answer
shape replaces 1,057,556 dense field operations; that doubled point is a scaling
check, not a shipping candidate because its compact route exceeds G9(c).

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses and JSON round-trips; direct demo sums agree |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 tagged prose/fenced answers round-trip; garbage returns `None` |
| G4 | 0/200,000 structure-aware guesses; exact probability `1/4,782,969` |
| G5 | unique exact answer; 0/200,000 sampled; 160,211 operations, 0.006886 s |
| G6 | five attacks all 0/8; dense reference solves 8/8 as Track B expects |
| G7 | dimension 94 verifies; 1,057,556 reference operations; answer still 15 atoms |
| G8 | 20/20 GL+query-order invariance, 20/20 carried witnesses, 20/20 distinct keys |
| G9(c) | 50 worst-case characters, 13 conservative tokens, 15 atoms, 261 intended operations |

The machine-readable details are in
[`selftest_report.json`](selftest_report.json).

## Oracle loop and G9 arms

The bare ladder was run by `scripts/harden.py`; a level advances if any attempt
solves and holds only when all three do not.

| preset | seed | model | solved | evidence |
|---|---:|---|---:|---|
| easy | 1371786217 | GPT-5.6 Terra | no | parsed answer; phase mismatch at query 4 |
| easy | 1944678052 | Gemini 3.8 Flash | yes | exact certificate verified |
| easy | 1370345320 | Gemini 3.8 Flash | no | empty `content_filter` response |
| medium | 1959611488 | Gemini 3.8 Flash | no | empty `content_filter` response |
| medium | 2017755753 | GPT-5.6 Terra | no | parsed answer; phase mismatch at query 0 |
| medium | 882287658 | Gemini 3.8 Flash | no | empty `content_filter` response |

The G9 diagnostics each reran the shipping preset independently:

| arm | solved / attempts | result |
|---|---:|---|
| bare | 0/3 | shipping level hardened |
| structural hint | 1/3 | hint made one instance solvable |
| placebo hint | 1/3 | placebo also made one instance solvable |

The measured `hinted − placebo` rate is therefore `0.0`. At this sample size
the structural hint bought no net success beyond prompt perturbation, so the
diagnostic does not establish that the declared symmetry alone explains the
difficulty. The answer is 50 characters, about 13 tokens and 15 atoms; the
intended route is bounded by 261 exact operations. Full evidence is in
[`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl),
[`g9_hinted_transcript.jsonl`](g9_hinted_transcript.jsonl), and
[`g9_placebo_transcript.jsonl`](g9_placebo_transcript.jsonl).

## Use

```python
from gen_2605_17594 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2605.17594 20 medium
```

## Caveats

- The current script configured a two-vendor rather than four-vendor pool, and
  two of three shipping failures were empty `content_filter` responses. The
  hardened verdict is exactly what the repository harness produced, but a
  future audit may reasonably rerun with broader vendor coverage.
- `0/200,000` is a sample. The stronger exact number comes from the declared
  structure-aware language: a random candidate is granted the correct
  determinant sign and chooses fourteen independent ternary phases. It does not model a solver that has
  partially recovered several phases.
- Dense elimination takes only milliseconds with Python on this host. That is
  expected and is why this is Track B; the claim is solely about recognizing
  and executing the compact algebra without tools.
- The attacks cover constant phases, label-weight outliers, a first-coordinate
  greedy rule, a diagonal-only ansatz, and 256 random phase restarts. They do
  not cover every possible symbolic-algebra heuristic or a model equipped with
  a CAS. The exact rank-one recovery is intentionally the compact solution, not
  a failing attack.
- The canonical key is invariant under arbitrary invertible coordinate changes
  and query permutations and was collision-free on twenty unrelated seeds. Its
  color-refined Gram invariant is not a complete canonizer for every possible
  finite-field Gram graph.
- The shipping prompt is about 7.2k characters. Some oracle difficulty could
  come from navigating the matrix as well as recognizing rank one. Once the hidden
  all-nonzero direction is recognized, its norm is `n mod 3` and every full
  label has one exceptional coordinate, keeping intended arithmetic below the
  no-tool cap.
- The paper proves the MUB magnitude, not this exact-phase recovery task. The
  benchmark stays in the paper's native quadratic forms and phase vectors, but
  deliberately asks for more information than mutual unbiasedness alone needs.
