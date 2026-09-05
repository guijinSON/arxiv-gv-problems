# arXiv 2601.07809 — implicit equation under hidden reparametrization

| profile field | value |
|---|---|
| Track | **B** — no-tool compression, not a complexity-hardness claim |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate | homogeneous ternary polynomial |
| Native objects | rational parametrized plane curve, ternary polynomial over Q, projective coordinate map, polynomial map of the parameter line |
| Intended intuition | change of variables: use the unchanged low Taylor frame instead of implicitizing the high-degree parametrization |
| Domain essentiality / reduction | native / none |

## What the problem is

[Orevkov, *On curves of degree 10 with 12 triple points*](https://arxiv.org/abs/2601.07809), Proposition 1(a), gives an explicit rational parametrization of an irreducible degree-10 plane curve and its homogeneous Cartesian equation. An instance presents a high-degree polynomial parametrization obtained from that curve by a common covering of the parameter line, three independent coordinate scalings, and a shear. The solver must return the normalized homogeneous degree-10 polynomial that vanishes on it. The answer is a sparse integer polynomial, not indices or a graph surrogate.

The generator samples the covering and coordinate map first and pulls the paper's equation through the inverse map. It therefore knows the answer by composition of identities. `verify` checks the answer's exact bounded syntax, reconstructs the coordinate map from the Taylor frame, expands the paper's polynomial through it, recovers the common covering from the full target parametrization, recomputes all target coefficients, and compares exactly. It never reads `inst["answer"]`, uses floats, or calls a solver.

## Why Track B

Track A would be false. Proposition 1 writes the certificate down, §1.2 derives it by an explicit birational substitution and the change `s=t^3+2`, and §2.5 computes deformation coefficients through repeated linear systems (with Maple code supplied by the author). There is no distributional hardness theorem in the paper.

The honest mechanical algorithm here is degree-bounded implicitization. Evaluate the 66 possible degree-10 monomials of `(P,Q,R)` at enough exact field points and find their one-dimensional nullspace. The included reference implementation has complexity `O(n^2 + m^3)` for `m=66`; over eight shipping seeds it solved 8/8 and used exactly 24,922,866 modular operations total, 3,115,358 on average. Repeated local runs ranged from 0.23 s to 0.42 s per instance.

The compact route is different. Because the common covering is `h(t)=t+O(t^4)`, coefficients of degrees 0, 1, and 3 retain the seed curve's Taylor frame. Those nine small entries reveal the three scales and shear. Pulling the displayed seed equation through that map takes 140 counted exact multiply-adds. That is within the no-tool cap, but recognizing and executing it is not the same as mechanically performing about 3.1 million modular operations.

The easy cases deliberately avoided are the untransformed seed (the answer can be copied), a visible unit-scale shear (the leading coefficient ratio reveals it), and small parameter degree (ordinary implicitization has little mechanical bulk). Independent scales mask the leading-ratio signature; increasing `n` enlarges the parametrization while the degree and number of answer terms stay fixed.

## Worked demo (seed 0)

The demo uses the identity coordinate map, so a person can solve it on paper by noticing that `P=x0(h)`, `Q=y0(h)`, and `R=z0(h)` and then copying the displayed `F0`. This is intentionally illustrative rather than hard. Here is `render(make_instance(seed=0, **DIFFICULTY["demo"]))` in full:

```text
Exact implicit equation of a parametrized plane curve

A polynomial parametrization t -> (P(t):Q(t):R(t)) of a projective plane curve
is given below. All coefficients and all arithmetic are exact integers. A
homogeneous polynomial K(X,Y,Z) is an implicit relation when the univariate
polynomial K(P(t),Q(t),R(t)) is identically zero coefficient by coefficient.

The source construction is Orevkov's degree-10 curve. Its seed coordinates are
  x0(s)=s^9+5s^6+9s^3+6
  y0(s)=s^10+6s^7+11s^4+6s
  z0(s)=s^9+3s^6-3
For reference, its homogeneous relation F0 is listed sparsely below. A row
"c: [i,j,k]" means c*X^i*Y^j*Z^k, and unlisted coefficients are zero:
  -1: [10,0,0]
  -2: [9,0,1]
  3: [8,0,2]
  9: [7,3,0]
  6: [7,0,3]
  24: [6,3,1]
  -3: [6,0,4]
  13: [5,3,2]
  -6: [5,0,5]
  -18: [4,6,0]
  -8: [4,3,3]
  1: [4,0,6]
  -24: [3,6,1]
  -11: [3,3,4]
  2: [3,0,7]
  9: [2,6,2]
  -1: [2,3,5]
  9: [1,9,0]
  18: [1,6,3]
  2: [1,3,6]
  -9: [0,9,1]
  -3: [0,6,4]
  -1: [0,3,7]

Target parametrization (the parameter t and its marked 4-jet at t=0 are part of
the data; coefficient rows not printed are zero):

P(t), rows are exponent: coefficient
  36: 1
  33: 9
  30: 36
  27: 84
  24: 131
  21: 156
  18: 159
  15: 136
  12: 93
  9: 58
  6: 32
  3: 9
  0: 6

Q(t), rows are exponent: coefficient
  40: 1
  37: 10
  34: 45
  31: 120
  28: 216
  25: 294
  22: 336
  19: 330
  16: 266
  13: 180
  10: 109
  7: 50
  4: 17
  1: 6

R(t), rows are exponent: coefficient
  36: 1
  33: 9
  30: 36
  27: 84
  24: 129
  21: 144
  18: 129
  15: 96
  12: 54
  9: 19
  6: 3
  0: -3

Find a homogeneous integer polynomial K of total degree exactly 10 satisfying
K(P(t),Q(t),R(t))=0 identically. There are 66 possible degree-10 monomials.
Normalize the answer by requiring the coefficient of X^10 to be exactly
-D = -1. Every coefficient must lie in the inclusive interval [-B,B], where
B = 49. This normalization makes the answer unique.

Write K as a sparse JSON list. Each nonzero term is
[coefficient,[i,j,k]] and denotes coefficient*X^i*Y^j*Z^k. Coefficients and
exponents are JSON integers, never decimals or strings. Omit zero coefficients.
Order terms by decreasing i and, for equal i, decreasing j. Repetitions are not
allowed. The order of factors X,Y,Z is fixed and indices are exponent values,
not positions. For syntax only, an example two-term list is
[[-1,[10,0,0]],[1,[0,0,10]]].

Give your final answer inside <answer></answer> tags, as the sparse JSON list.
Example: <answer>[[-1,[10,0,0]],[1,[0,0,10]]]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[[-1,[10,0,0]],[-2,[9,0,1]],[3,[8,0,2]],[9,[7,3,0]],[6,[7,0,3]],[24,[6,3,1]],[-3,[6,0,4]],[13,[5,3,2]],[-6,[5,0,5]],[-18,[4,6,0]],[-8,[4,3,3]],[1,[4,0,6]],[-24,[3,6,1]],[-11,[3,3,4]],[2,[3,0,7]],[9,[2,6,2]],[-1,[2,3,5]],[9,[1,9,0]],[18,[1,6,3]],[2,[1,3,6]],[-9,[0,9,1]],[-3,[0,6,4]],[-1,[0,3,7]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last term returns `(False, "polynomial identity fails exact coefficient comparison")`.

## Difficulty presets

| preset | `n` | composition height | transform height | status |
|---|---:|---:|---:|---|
| demo | 4 | 1 | identity | hand-solvable illustration |
| easy | 10 | 2 | 8 | bare held, but rejected for shipping because hinted Gemini solved 1/3 (G9(b)) |
| medium | 20 | 2 | 10 | **ships**; bare and structural-hint arms both held 0/3 |
| hard | 32 | 3 | 12 | available, not needed by the final ladder |

## Gate results at shipping preset

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified across all presets |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced model-style answer round-tripped; garbage returned `None` |
| G4 | 0/200,000 valid structure-aware random coefficient vectors; declared space has 65 independent bounded slots |
| G5 | shipping density sample 0/200,000; strongest baseline solved 8/8 using 24,922,866 modular operations total |
| G6 | four attacks each 0/8; reference implicitizer 8/8 as expected |
| G7 | doubled covering degree 20→40 built and verified; answer remained 26 terms in the measured seed |
| G8 | 60/60 projective-scaling invariance checks, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass: hinted still hardened; max over 200 seeds 972 chars, 243 estimated tokens, 104 atomic integers; intended route 140 operations |

## Shipping oracle loop

The one Grok error was a 900-second provider timeout and was redrawn; it is not counted as a failure. Claude's empty length-limited response does count under the harness policy and is disclosed below.

| preset | model | seed | result | exact grading reason |
|---|---|---:|---|---|
| medium | Gemini 3.1 Pro | 124301985 | failed | polynomial identity fails at `t=0` |
| medium | GPT-5.6 Terra | 15887177 | failed | zero coefficients were not omitted |
| medium | Grok 4.6 | 18346355 | error/redrawn | total deadline exceeded |
| medium | Claude Sonnet 5 | 102186122 | failed | empty length-limited response after exhausting 32k completion tokens |

## G9 three-arm diagnostic

| arm | solved / attempts | observation |
|---|---:|---|
| bare | 0 / 3 | shipping statement held |
| structural hint | 0 / 3 | polarity-flipped gate held |
| placebo hint | 1 / 3 | Grok solved; Gemini and Terra failed |

`hinted - placebo = -1/3`. The structural hint bought no measured success over the matched placebo; the single placebo solve is more plausibly sampling/provider variance or generic hint priming than evidence that the named Taylor-frame intuition helped. At `easy`, however, the structural hint did help one Gemini instance, which is why the ladder moved exactly once to `medium`.

## Use

```python
import json
import gen_2601_07809 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
statement = g.render(inst)
wire_answer = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
assert g.verify(inst, g.parse_answer(wire_answer)) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2601.07809 20 medium
```

## Caveats

The 0/200,000 guess result is for the declared language: all normalized degree-10 integer coefficient vectors within the instance's bound. It is not a posterior probability after recognizing Orevkov's transformation family. The separate transformation-prior restart attack tried 256 guesses on each of eight seeds and also found none, but a solver that recovers the Taylor frame is expected to win.

The attack panel did not run a commercial CAS resultant, Gröbner-basis projective-equivalence solver, or lattice/PSLQ reconstruction. It did run an exact domain-standard implicitizer to completion. Its subsecond wall time is why this is Track B, not Track A; the meaningful quantity for the no-tool claim is its roughly 3.1 million modular operations versus the 140-operation structural route.

When `gvlib` is available the generator uses its exact sparse-polynomial composition. If it is absent, the module falls back to its own standard-library `Fraction` expansion; no third-party dependency is required, and both paths are checked against one another during development.

The canonical key treats the parameter coordinate and marked 4-jet as part of the framed object and removes common projective scaling of `(P,Q,R)`. It does not decide general `PGL(3,Q)` equivalence of ternary forms; that is the strongest cheap invariant implemented here. Finally, one of the three bare failures was an empty length-limited Claude response, so the bare evidence contains two substantive wrong submissions rather than three. The hinted gate is cleaner: all three providers returned explicit, parseable but incorrect polynomials.
