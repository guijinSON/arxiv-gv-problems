# Hidden-basis infinitesimal automorphisms (arXiv:0709.1499)

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | matrix certificate |
| Intended intuition | change of variables: recover a hidden integral basis from a constant Gram matrix |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Norbert Riedel, [*Markoff Equation and Nilpotent
Matrices*](https://arxiv.org/abs/0709.1499v6), Section 2 of the last substantive
revision. It defines the upper-unitriangular matrix `M(a,b,c)` over an arbitrary
commutative ring, displays a nonzero matrix `R` satisfying
`R^T M + M R = 0`, and gives the change-of-basis law in Proposition 2.1(b).

The generator substitutes nonconstant monomials in `Z[x]` for `a,b,c`, chooses
an upper-unitriangular `P in SL(3,Z)`, and hands the solver only
`B=P^T M P`. The requested witness is the normalized polynomial matrix
`X=P^-1 R P`, checked by exact expansion of `X^T B+B X=0`. This is generation
by composition of the paper's identity with a structure-preserving map; no
coefficient system is solved during generation. The solver manipulates the
paper's bilinear forms and polynomial matrices directly, not a discrete
surrogate.

The arXiv record is withdrawn. The generator does **not** use the paper's
withdrawn headline claim that a dominant Markoff number uniquely determines a
triple. It uses only the Section 2 identity and Proposition 2.1(b), both of which
`verify()` rechecks exactly on every instance.

## Why this is Track B

Track A would be false: Section 2 explicitly displays `R` up to scale, and a
generic polynomial-time algorithm exists. The reference implementation evaluates
at `D+1` finite-field points, solves a normalized 9-variable linear system at each
point, and performs Newton interpolation. Its complexity is
`O(D*9^3 + 9D^2)` field operations for `D=3n`. On shipping seed 800 it used
1,047,704 counted operations and 0.060105 seconds; it solved 8/8 audit instances.

The compact route notices that the hidden polynomials have no constant term, so
`B(0)=P^T P`. Because `P` is upper unitriangular, three constant entries recover
it exactly. Conjugating by `P^-1` exposes `M(a,b,c)`, after which the universal
Section 2 formula gives `R`, and conjugating back gives `X`. The reporting seed
uses 259 exact coefficient operations. The gap is therefore between a mechanical
million-operation route that software executes easily and a sub-300-operation
change of variables that must first be seen.

An earlier direct version exposed `M(a,b,c)` itself and was solved by the oracle
at every tested degree from 40 through 505. Hiding the basis is the substantive
hardening change; merely enlarging exponents did not help.

## Worked demo

The complete demo statement is:

```text
Polynomial infinitesimal automorphism problem

Work in the univariate polynomial ring Z[x].  The following matrix B(x)
represents a bilinear form (rows are displayed from top to bottom):

  B[0] = [1, 1, 0]
  B[1] = [0, 1, 0]
  B[2] = [0, 0, 1]

Find a 3 by 3 matrix X(x) of polynomials with integer coefficients such that

  transpose(X(x))*B(x) + B(x)*X(x) = the zero matrix,

and with the normalization

  X[1][1] = -1.

Matrix indices are zero-based, so X[1][1] is the central entry.  The answer must
have total degree at most D=0, exactly K=4 nonzero monomial terms across all nine
entries, and every coefficient must have absolute value at most H=2.  A zero
coefficient must be omitted.  Terms may be listed in any order, but an exponent
may occur at most once in an entry.

Give your final answer inside <answer></answer> tags as JSON for a 3 by 3 matrix.
Encode each polynomial as a list of terms ["num/den", [exponent]]; coefficients
here are integers, so den must be 1.  The zero polynomial is [].
Output nothing else inside the tags.
```

Its answer is:

```json
<answer>[[[["1/1",[0]]],[["2/1",[0]]],[]],[[["-2/1",[0]]],[["-1/1",[0]]],[]],[[],[],[]]]</answer>
```

This demo is hand-solvable. Internally, `verify(inst, inst["answer"])` returns
`(True, "ok")`; removing the first term returns
`(False, "wrong support size: expected 4 nonzero terms")`.

## Difficulty presets

| Preset | `n` | `D=3n` | input coefficient bound | hidden-basis bound | Status |
|---|---:|---:|---:|---:|---|
| demo | 0 | 0 | 2 | 1 | hand-solvable illustration |
| easy | 60 | 180 | 5 | 3 | **ships; bare oracle held 0/3** |
| medium | 120 | 360 | 7 | 5 | local gates pass; not reached by oracle |
| hard | 200 | 600 | 9 | 7 | local gates pass; not reached by oracle |

`SHIPPING_DIFFICULTY = "easy"`. Escalation raises both the coefficient-matching
degree and the range of hidden bases while the witness support remains bounded.

## Gate results

| Gate | Result | Measurement at shipping unless noted |
|---|---|---|
| G1 | pass | 12/12 planted witnesses over four presets; JSON round-trip included |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; candidate language about 855 bits |
| G5 | pass | demo exact count 1/3,584; shipping sample 0/200,000; strongest failing attack 2,048 checks in 0.088030 s |
| G6 | pass | four attacks each 0/8; polynomial-time reference algorithm 8/8 as expected |
| G7 | pass | doubled `n=120` verifies and raises language size from 855 to 1,073 bits |
| G8 | pass | 640/640 composed symmetries invariant and real; 20/20 unrelated keys distinct |
| G9(c) | pass | representative 1,235 chars / 207 atoms / 309 tokens; sampled worst case 1,300 / 210 / 325; intended route 259 operations |

The four G6 attacks are high-degree support, low-degree greedy support, 256
structure-aware random restarts, and the tempting but wrong finite-cosquare
automorphism in place of the infinitesimal generator.

## Bare oracle loop

| Model | Seed | Result | Checker reason |
|---|---:|---|---|
| `google/gemini-3.8-flash` | 1045491066 | failed | proposed matrix failed exact modular evaluation |
| `openai/gpt-5.6-terra` | 916757901 | failed | no parseable tagged answer |
| `openai/gpt-5.6-terra` | 287817590 | failed | no parseable tagged answer |

The script-owned verdict is `hardened` at `easy`, with zero escalations.

## G9 arms

| Arm | Solved / attempts | Diagnostic verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 1 / 3 | too_easy (recorded, not gated) |
| placebo hint | 1 / 3 | too_easy (recorded, not gated) |

`hinted - placebo = 0.0`. In this three-call sample, naming the constant Gram
invariant did not outperform a stylistically similar placebo, so the diagnostic
does not isolate a causal hint effect. One hinted solver did use the clue
successfully, but one placebo solver also found a valid witness. The size/effort
caps remain the only gated part of G9 and pass.

## Use

```python
from gen_0709_1499 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer(model_reply)
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 0709.1499 20 easy
```

## Caveats

- This is strictly Track B. With a sandbox, the reference algorithm solves the
  shipping preset in well under a second; no complexity-theoretic hardness is
  claimed.
- G4 samples uniformly from the declared support/height language after fixing
  the stated central polynomial. Its 0/200,000 result says nothing about a model
  prior that recognizes Gram factors or the paper's universal formula.
- A Gröbner-basis or module-syzygy package, a general CAS simplifier, and other
  bilinear-form canonicalization algorithms were not tested. Any such tool is
  expected to make the family easy.
- The installed hardening harness used two vendors and three calls, repeating one
  vendor, rather than the four-vendor pool described in the task text. The exact
  pool is preserved in `.meta.json`; this limits the breadth of the empirical
  claim.
- `canonical_key` handles term reorderings, `x -> -x`, arbitrary tested
  upper-unitriangular basis changes, and the `a/c` transpose-reversal symmetry.
  It does not canonicalize all of `GL(3,Z)` or every automorphism of `Z[x]`.
- The source's Markoff-unicity argument is withdrawn, and the general injectivity
  conjecture is still described as open in later work. Neither claim contributes
  to generation, hardness, or verification here.
