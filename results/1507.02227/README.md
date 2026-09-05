# Polynomial syzygies for arXiv:1507.02227

**Status: release-ready.** The local gates pass, and the required bare oracle run
returned `hardened` at the shipping preset.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | polynomial |
| Intended intuition | invariant: recognize mixed directions with high root multiplicity |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Bernardi, Gimigliano, and Idà, [*On Parameterizations of
plane rational curves and their syzygies*](https://arxiv.org/abs/1507.02227).
An instance gives three degree-`d` homogeneous binary forms `F0,F1,F2` over
`Q`, represented by exact coefficient vectors. The solver must return three
degree-`k` polynomials `A0,A1,A2` satisfying the moving-line identity

`A0*F0 + A1*F1 + A2*F2 = 0`.

These are the paper's native objects. Section 2, equation (2), gives the two
rows of the Hilbert–Burch matrix as generators of the syzygy module; Section
3 identifies a polynomial identity of this form with a moving line; and
Theorem 3.1 constructs the associated rational normal scroll from a minimal
moving line. Verification is exact polynomial convolution and coefficient
comparison. When `gvlib` is available, `gvlib.sparse_poly` independently
rechecks the same identity; the standard-library path remains complete.

Generation is inverse rather than search. Write `X=s+2t` and `Y=t`, choose

`alpha=(X^k,0,Y^k)` and

`beta=(Y^(d-k),X^(d-k),X^(d-k-1)Y + sum q_j X^(d-k-jk)Y^(jk))`,

form their three maximal minors, and apply a seed-selected unimodular mixing
of the target coordinates. The answer is `alpha` carried through the inverse
mixing. The minors have gcd one: one is `X^d`, one is divisible by
`X^(d-k)Y^k`, and the remaining one restricts to `Y^d` at `X=0`. Thus the
Hilbert–Burch resolution is minimal, and because `2k<d` its normalized
degree-`k` syzygy is unique. The parameterization is generically one-to-one:
if `z=Y/X`, two minor ratios give `-z^k` and
`z^d-z-sum q_j z^(jk)`; since `k` divides `d`, those ratios recover `z`
rationally.

## Why this is Track B

There is an efficient general algorithm, so this is not a Track A claim.
Coefficient matching builds an `(d+k+1) x 3(k+1)` matrix and modular Gaussian
elimination solves for its one-dimensional nullspace in
`O((d+k)(3k+3)^2)` field operations. Across eight shipping instances it
solved 8/8; the measured maximum was **52,891 field operations in 0.012 s**
on an `81 x 27` matrix. That calculation is easy for a program but far beyond
a no-tool, by-hand evaluation.

The compact route recognizes two directions in the span of the three input
forms: a `d`-th power and a form with root multiplicities `(d-k,k)`. Two small
coordinate relations then give the coefficients multiplying `X^k` and `Y^k`.
Expanding one binomial and combining the rows takes at most **146 exact
arithmetic operations** at shipping size. The benchmark tests whether the
solver finds this invariant.

The easy regime matters. Inequality (1) and Definition 1.1 in the Introduction
show that a sufficiently high-multiplicity point determines the splitting
type in the Ascenzi case. The generated curves are in that regime. Therefore
the problem gives `k` and asks for the actual mixed polynomial syzygy; it does
not claim that determining the splitting degree is hard. Displaying the
Hilbert–Burch rows or the target mixing would also make the witness immediate.

## Worked demo (`seed=0`)

The complete rendered demo is:

```text
Polynomial syzygy of a parameterized plane rational curve

Work over the rational numbers. For a degree-r homogeneous binary form
P(s,t), its coefficient vector [c_0,...,c_r] means
P(s,t) = sum_{i=0}^r c_i s^(r-i)t^i.

Here d=8, k=2, and B=36. The three degree-d forms are:
F0 = [3,46,306,1152,2676,3904,3466,1704,362]
F1 = [-4,-61,-404,-1516,-3514,-5120,-4543,-2236,-479]
F2 = [-5,-76,-501,-1868,-4292,-6176,-5380,-2576,-532]

Find three homogeneous degree-k polynomials A0,A1,A2 such that
A0*F0 + A1*F1 + A2*F2 is the zero polynomial.

Your answer must use the following finite normalized language. Represent
each polynomial sparsely as a list of terms
[[[numerator,denominator],[s_exponent,t_exponent]],...]. Use exactly
three polynomial lists. Every exponent is nonnegative and sums to k;
order terms by increasing t_exponent; omit zero terms; use reduced
rationals with positive denominator. In this instance every denominator
must be 1 and every |numerator| must be <= B=36. The coefficient
of s^2t^0 in A0 must be exactly 1. Order of A0,A1,A2 matters.

Give your final answer inside <answer></answer> tags, as one JSON array
containing the three sparse polynomial arrays.
Example of the required syntax (not a solution): <answer>[[[[1,1],[2,0]]],[[[-2,1],[0,2]]],[[[3,1],[1,1]]]]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[[[[1,1],[2,0]],[[4,1],[1,1]],[[5,1],[0,2]]],[[[2,1],[2,0]],[[8,1],[1,1]],[[6,1],[0,2]]],[[[-1,1],[2,0]],[[-4,1],[1,1]],[[-2,1],[0,2]]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Removing the last
term of the second polynomial returns
`(False, "syzygy identity fails at t-exponent 2")`. This demo is genuinely
hand-solvable: the small relations `(1,2,-1)` and `(1,-2,2)` expose the
`X^6Y^2` and `X^8` directions, after which only expanding
`X^2=s^2+4st+4t^2` remains.

## Difficulty presets

| Preset | `d=n` | `k` | Input coefficients | Worst answer atoms | Worst answer chars | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 2 | 27 | 36 | 175 | hand-scale illustration; not hardened |
| easy | 72 | 8 | 219 | 108 | 567 | **ships; bare oracle held 0/3** |
| medium | 120 | 12 | 363 | 156 | 887 | local gates pass; not needed by ladder |
| hard | 160 | 16 | 483 | 204 | 1,245 | local gates pass; not needed by ladder |

`escalate()` grows the coefficient haystack by replacing `d` with `d+4k`
while keeping `k` and the witness length fixed.

## Gate results

| Gate | Result | Measurement at shipping size |
|---|---|---|
| G1 | pass | 16/16 preset/seed planted witnesses verify; every answer is JSON-native |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | fenced JSON amid prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exactly one normalized answer in the bounded language |
| G5 | pass | shipping density sample 0/200,000; reference maximum 52,891 operations / 0.012 s |
| G6 | pass | four no-tool attacks each 0/8; reference elimination 8/8 as expected |
| G7 | pass | doubled degree `d=144` builds and verifies with the same 108 answer atoms |
| G8 | pass | 120/120 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 567 chars, about 142 tokens, 108 atoms, 146 intended-route operations |

The four failing attacks are per-form L1 outlier selection, a greedy relation
using only edge coefficients, 256 structure-aware random restarts, and the
obvious ansatz restricting every component to `s^k` and `t^k`. The successful
coefficient-nullspace algorithm appears separately as Track B's reference
algorithm.

## Oracle loop

The script-owned bare run held the first tested rung, so no escalation was
needed.

| Preset | Seed | Model | Solved? | Reason |
|---|---:|---|---|---|
| easy | 1515321233 | `openai/gpt-5.6-terra` | no | proposed witness failed at t-exponent 15 |
| easy | 1353344570 | `google/gemini-3.8-flash` | no | response ended mid-reasoning with no answer block |
| easy | 796218713 | `google/gemini-3.8-flash` | no | proposed witness failed at t-exponent 24 |

The missing answer block above was inspected: the response was truncated while
deriving a recurrence, so this is not a `parse_answer` defect.

## G9 arms

Only records at the shipping parameters are counted here.

| Arm | Solved / attempts | Verdict at shipping size |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 1/3 | solved by one oracle; diagnostic only |
| placebo hint | 0/3 | hardened |

The solved-rate difference `(hinted - placebo)` is **1/3 = 0.333**. Naming
the root-multiplicity invariant enabled one oracle to finish, while a
same-register placebo did not. This supports the intended interpretation:
the difficulty is primarily in finding the invariant. The structural harness
then escalated to `n=104, k=8`, which held 0/3. At shipping size the measured
answer is 567 characters (about 142 tokens), 108 atomic elements, and the
intended post-insight route costs 146 exact operations.

## Use

```python
import json
import gen_1507_02227 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
prompt = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(wire)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1507.02227 20
```

## Caveats

- The `0/200,000` density is sampled uniformly from the explicitly bounded,
  normalized integer-coefficient language. Uniqueness follows separately from
  the one-dimensional Hilbert–Burch syzygy space. The sample does not model an
  informed algebraist's prior or guesses outside that language.
- Gröbner-basis software, general binary-form factorization, tensor/Waring
  decomposition, and symbolic root-multiplicity algorithms were not run.
  Exact coefficient-nullspace elimination is the strongest implemented
  reference and succeeds quickly, as Track B requires.
- `canonical_key` exactly quotients target `GL(3)`, coordinate permutations,
  and the signed source exchanges generated by `s<->t` and `t->-t`. It is not
  a full canonical form under arbitrary `PGL(2)` reparameterization.
- One placebo response independently noticed useful structured combinations
  but exhausted its response before emitting a witness. The recorded 0/3 is
  therefore an output-under-budget result, not evidence that the placebo models
  saw no structure.
- Revealing the planted Hilbert–Burch rows, leaving target coordinates
  unmixed, or asking only for the splitting degree makes the family easy.
