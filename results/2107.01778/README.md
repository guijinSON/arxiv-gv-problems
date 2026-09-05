# Exact zero witnesses for linear tropical valued CSPs

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | optimization |
| object regime | continuous analytic |
| computational core | linear algebra |
| certificate form | rational vector |
| intended intuition | invariant — paired dense rows have a one-coordinate difference |
| domain essentiality | native |
| reduction | none |

This generator uses Fujii, Iwamasa, and Kimura, [“Quantaloidal Approach to
Constraint Satisfaction”](https://arxiv.org/abs/2107.01778). It hands the solver
a linear tropical valued CSP over the reals: finitely many rational affine
residuals and the objective `F(s) = max_e |a_e·s-b_e|`. The required witness is
a bounded rational assignment with `F(s)=0`. Verification substitutes the
assignment into every form using exact rational arithmetic. Since `F` is
nonnegative, zero also certifies global optimality.

Trust status: all local gates G1–G9(c) pass. The required STEP 4 oracle evidence
is **incomplete, not passed**. The funded key completed eight calls: `easy` and
`medium` were solved 3/3, while two `hard` attempts failed. It then returned HTTP
403 “Key limit exceeded” four times before the third `hard` attempt, so the
harness correctly refused to issue a verdict. The structural and placebo arms
are authentic `harden.py` outputs but are error-only and supply no evidence.

## Family and construction

Section 5 defines a tropical valued CSP by
`Sol(I)(s) = sup(rho(s(x))-sigma(x))` and asks for its infimum. Section 5.2
specializes this to linear real-valued relations, where `Sol(I)` is a maximum
of affine functions. Each displayed equation in this module abbreviates the
two paper-native forms `a·s-b` and `-a·s+b`.

Generation is inverse. It first samples pairwise-distinct bounded rationals
`s_j`, then samples integer rows and sets every right-hand side to `a·s`.
Among paired rows, one pair changes only coordinate `j` for every `j`; subtracting
that pair proves and recovers `s_j`. Other pairs change two coordinates and are
near misses. Base rows and coefficient replacements use the same sampling rules
in both pair types; the number of changed coordinates is the structural signal.
The generator therefore knows the witness
before it creates the instance and never solves its output.

## Why Track B

This is explicitly not a Track A claim. Proposition 5.2 and Theorem 5.4 give the
finite-domain CSP/TVCSP classification, while Section 5.2 reduces linear TVCSP
minimization to linear programming, hence gives a polynomial-time mechanical
method. For the zero-level system used here, the implemented exact reference is
fraction-free Bareiss elimination: `O(m n^2)` arithmetic for `m` equations and
`n` variables. At hard it solved 8/8, used 1,406,272 counted exact operations,
and took at most 4.492 wall-clock seconds in the final, heavily contended shared-
runner self-test.

The prior-triage suggestion of a planted finite CSP was not used: Theorem 5.4 is
a worst-case dichotomy and gives no distributional-hardness guarantee for a
planted satisfiable distribution. Section 5.2 instead licenses the explicit
Track B claim made here.

After recognizing the invariant, each of 64 coordinates needs one RHS
subtraction, one coefficient subtraction, and one exact division: 192 exact
operations. The benchmark is the gap between scanning a large dense system and
noticing that positionwise row pairs isolate coordinates. The paper’s easy
regime is not hidden: Section 5.1 gives the finite-domain Siggers dichotomy, and
Section 5.2 says the continuous linear case here is in P.

## Worked demo

For the `demo` preset and seed 0, the complete rendered instance is:

```text
Linear tropical valued CSP over the real numbers

There are 3 real variables s_0,...,s_2.
For every displayed equation e, let
  r_e(s) = a_e,0*s_0 + ... + a_e,2*s_2 - b_e.
The tropical minimax objective is
  F(s) = max_e max(r_e(s), -r_e(s)) = max_e |r_e(s)|.
This is the maximum of finitely many rational affine forms, so F(s) >= 0.
The instance promises one unique vector in the bounded language below with F(s)=0.
Find that vector.  Reaching zero also certifies global optimality because F is nonnegative.

Each equation line has the exact format
  index : b | a_0 a_1 ... a_2
and means sum_j a_j*s_j = b.  Indices and variables are 0-based.
All coefficients are integers and every b is an exact reduced rational.
Equation order does not change F.

n = 3; equations = 8
certificate bounds: 0 < |numerator| <= 4, denominator <= 2, entries pairwise distinct

EQUATIONS
0 : -7/2 | 1 -2 -1
1 : -29/2 | 3 -3 1
2 : -7/2 | 1 2 3
3 : 37/2 | -3 2 -3
4 : -23/2 | 1 -2 1
5 : 3/2 | 3 1 1
6 : -7/2 | 1 -2 -1
7 : 41/2 | 1 2 -3
END EQUATIONS

Give your final answer inside <answer></answer> tags as exactly 3 comma-separated
reduced rationals in variable order s_0,...,s_2.  Write an integer q as q and
a nonintegral rational as num/den with a positive denominator.
Syntax example: <answer>1/2, -3, 4/5</answer>
Output nothing else inside the tags.
```

The answer is `<answer>1/2, 4, -4</answer>` and verifies as `(True, "ok")`.
Replacing its first entry by `5` returns `(False, "entry 0 violates the declared
numerator/denominator bounds")`. A person can solve this demo on paper by
comparing rows 0–3 with rows 4–7 and using the three one-coordinate pairs.

## Difficulty presets

| preset | variables | one-coordinate pairs | two-coordinate near misses | equations | rendered chars (seed 1) | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 3 | 3 | 1 | 8 | 1,321 | hand example; hardening skips it |
| easy | 12 | 12 | 6 | 36 | 2,742 | solved by oracle 3/3 |
| medium | 32 | 32 | 16 | 96 | 10,952 | solved by oracle 3/3 |
| hard | 64 | 64 | 32 | 192 | 40,188 | 0/2 solved; third attempt blocked; provisional ship |

`escalate()` first raises `n`, coefficient/rational entropy, and near-miss
density together to `n=96`; it then holds the 192-atom answer and 288-operation
route fixed while continuing to add near misses and coefficient entropy. A
six-step dry run reached 894 equations while remaining below the output and
operation caps. `SHIPPING_DIFFICULTY` remains provisional until STEP 4 can run.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verified across every preset |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 32-entry prose/fence/tag response round-tripped; JSON native |
| G4 | 0/200,000 uniform structure-aware guesses; space is about `1.76e185` |
| G5 | exactly one shipping solution; density 1 / about `1.76e185`; 0/200,000 sampled; one 256-restart repair attack used 16,384 updates and at most 29.161 s; eight-seed panel total 197.559 s |
| G6 | column outlier, diagonal-dominance greedy, 256-restart coordinate repair, and adjacent-row hand scan all 0/8; Bareiss reference 8/8 |
| G7 | doubled instance has 128 variables/384 equations and verifies |
| G8 | 60/60 relabelling/sign/reordering invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 608 chars, 152 conservative tokens, 128 scalar atoms, 192 intended operations — all within caps |

Exact integers and wall-clock values are in
[`selftest_report.json`](selftest_report.json).

## Oracle loop

Each required command was run in its proper directory. The bare loop completed
all calls at `easy` and `medium`, then two of three calls at `hard`. Four redraws
failed with the key-limit response, after which `harden.py` aborted, as it must:
API errors are not model failures. The G9 copies contained only `hard`.

| preset | seed | model | scored result | why |
|---|---:|---|---|---|
| easy | 1128792221 | GPT-5.6 Terra | solved | exact witness verified |
| easy | 2035808116 | Gemini 3.8 Flash | solved | exact witness verified |
| easy | 2074640600 | GPT-5.6 Terra | solved | exact witness verified |
| medium | 2133032986 | GPT-5.6 Terra | solved | exact witness verified |
| medium | 1551633440 | Gemini 3.8 Flash | solved | exact witness verified |
| medium | 1837162255 | Gemini 3.8 Flash | solved | exact witness verified |
| hard | 1360511678 | GPT-5.6 Terra | failed | parsed vector contained forbidden zeros |
| hard | 923509528 | Gemini 3.8 Flash | failed | parsed vector had nonzero residual 324 |
| hard | 2137562110, 1589875815, 499951360, 908213001 | both pool models | errors, not attempts | HTTP 403 key limit |

## G9 arms

| arm | counted solved / attempts | provider errors | result |
|---|---:|---:|---|
| bare | 0 / 2 | 4 | two hard failures, then HTTP 403 key-limit abort |
| structural hint | 0 / 0 | 4 | HTTP 403 key-limit abort |
| placebo hint | 0 / 0 | 4 | HTTP 403 key-limit abort |

The hinted-minus-placebo value is unavailable; the report stores `0.0` only as
a schema-compatible placeholder when both denominators are zero. No conclusion
about hint responsiveness is justified yet. The measured answer is 608 JSON
characters, 152 conservative tokens, and 128 scalar atoms; the compact route is
192 exact arithmetic operations.

## Use

```python
from gen_2107_01778 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

After the oracle quota is restored and all three arms are recorded, emit from
the repository root with:

```bash
bash scripts/emit.sh 2107.01778 20
```

## Caveats

- This result is not submission-ready until a funded `OPENROUTER_API_KEY`
  completes the third bare `hard` attempt and the two isolated G9 arms. The
  present bare transcript is partial; the G9 files are authentic but error-only.
- `0/200,000` samples the exact promised prior: ordered, pairwise-distinct
  rationals within the stated bounds. It does not model a learned solver prior
  conditioned on the visibly paired rows. The exact solution count is one, but
  the sampled number alone would not prove that.
- The Track B claim is about unaided execution, not computational
  intractability. A program exploiting the row pairing runs in `O(mn)` scans
  plus 192 arithmetic operations and is faster than generic elimination.
- The adversary panel did not run a commercial LP solver, an SMT solver, a
  lattice-basis attack, or an optical/table parser. The successful exact
  elimination reference covers the zero-level linear system, but those tools
  could reduce wall time or expose other construction signals.
- Some model failure at hard may reflect navigating 40k rendered characters as
  well as discovering the invariant. The answer and exact arithmetic route fit
  G9(c), but prompt navigation remains a confound to be assessed by the three
  oracle arms.
- `canonical_key` uses eight rounds of weighted bipartite color refinement. It
  is invariant under the generated relabellings and strong on this distribution,
  but it is not a complete isomorphism algorithm for arbitrary weighted affine
  systems.
