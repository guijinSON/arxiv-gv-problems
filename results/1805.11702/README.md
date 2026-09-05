# Tritangents and Their Space Sextics — verified generator

Status: **ready to ship**. Every local gate passes and the bare oracle loop
hardened the shipping preset at 0/3 solved.

| profile | value |
|---|---|
| Track | B — no-tool compression |
| native domain | geometry |
| object regime | finite field |
| computational core | polynomial identity |
| certificate form | polynomial (a four-coefficient linear form) |
| intended intuition | invariant: the cone-vertex second polar |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

This generator is based on Celik, Kulkarni, Ren, and Sayyary Namin,
[“Tritangents and Their Space Sextics”](https://arxiv.org/abs/1805.11702).
It hands the solver a singular quadric `Q`, a cubic `F`, and an exact
parametrization of their smooth degree-six complete intersection over `GF(p)`.
The witness is one normalized linear form defining a tritangent plane.

Definition 2.2 defines a tritangent through a doubled degree-three hyperplane
section. Equation (*) in Section 4.1 writes a sextic on the quadric cone as a
weighted cubic in `w`; Proposition 4.3 excludes planes through the vertex,
which represent the vanishing even theta characteristic rather than an odd one.
The verifier follows Algorithm 3.1's square-binary-sextic criterion: it
substitutes the candidate plane through the supplied cone parametrization and
uses exact finite-field gcds to require a nonzero scalar times the square of a
squarefree cubic. It accepts any valid plane and never reads `inst["answer"]`.

Generation is a composition of identities, not a solve. Before masking,
`F = u^3 + A(s,t)u + (s*t*(s-t))^2`; therefore `u=0` has three distinct
double contacts. The binary discriminant `-4*A^3-27*(s*t*(s-t))^4` is sampled
squarefree, which gives the smoothness certificate by the
discriminant/Jacobian criterion in characteristic other than 2 or 3. Adding
`Q` times a linear form and applying a dense `GL(4)` change preserve the
curve and carry the witness.

## Why Track B

Track A would be false. Algorithm 3.1 computes tritangents with resultants and
the 45 quartic equations for square binary sextics. Section 4.2 is easier still
when the original eight plane points are supplied: the 240 exceptional curves
produce the 120 tritangents by type. The generator deliberately does not expose
those eight points.

The executable reference algorithm enumerates rational curve points and their
tangent-plane pencils in `O(p^2)`. At the shipping preset it solved 8/8
instances, requiring at most 3,714,246 counted field operations and 0.646
seconds in the final audit. The compact route recognizes that the second polar
of `F` in the cone-vertex direction is the trace-zero plane; it solved 8/8 in
at most 165 field operations. This mechanical-versus-compact gap is the Track B
claim.

## Worked demo

`make_instance(n=7, seed=0, scramble=False)` renders:

```text
Find a tritangent plane to a space sextic over GF(7).

All arithmetic is modulo the prime 7.  Projective 3-space has homogeneous
coordinates (x0:x1:x2:x3).  A nonzero coefficient vector h=[h0,h1,h2,h3]
defines the plane H: h0*x0+h1*x1+h2*x2+h3*x3=0; scalar multiples define the
same plane.

The curve C is the complete intersection Q=F=0, where
Q = 1*x1^2 + 6*x0*x2
F = 1*x3^3 + 2*x2*x3^2 + 2*x2^2*x3 + 1*x2^3 + 2*x1*x3^2 + 5*x1*x2*x3 + 6*x1*x2^2 + 2*x1^2*x3 + 6*x1^2*x2 + 3*x1^3 + 6*x0*x3^2 + 1*x0*x2*x3 + 5*x0*x2^2 + 3*x0*x1*x2 + 1*x0*x1^2 + 2*x0^2*x3 + 4*x0^2*x1 + 2*x0^3

It is guaranteed that C is a smooth degree-6 curve and Q is a singular quadric.
For exact substitution, the following parametrizes Q:

  [x0,x1,x2,x3]^T = B * [s^2,s*t,t^2,w]^T,
B =
  1 0 0 0
  0 1 0 0
  0 0 1 0
  0 0 0 1

A plane is a valid answer precisely when it does not contain the singular point
B*[0,0,0,1]^T and, after its equation is used to eliminate w in the displayed
parametrization, F becomes a nonzero scalar multiple of the square of a
squarefree homogeneous cubic in s,t.  Equivalently, H meets C at three distinct
geometric points, each with multiplicity two.

Return one valid plane.  Use the unique normalization in which every hi is an
integer from 0 through 6 and the first nonzero hi is 1.

Give your final answer inside <answer></answer> tags, as a JSON list of exactly
four integers [h0,h1,h2,h3].
Example: <answer>[1,0,3,5]</answer>
Output nothing else inside the tags.
```

The answer is `[1,5,5,4]`. This unscrambled example is hand-solvable: the
three `x_i*x3^2` coefficients reveal the depressed weighted coordinate after
three divisions modulo 7. Verification returns `(True, "ok")`; dropping the
last coefficient returns
`(False, "plane must have exactly four coefficients")`.

## Presets and gate results

| preset | prime | normalized planes not through the vertex | status |
|---|---:|---:|---|
| demo | 7 | 343 | hand-solvable, unscrambled |
| easy | 503 | 127,263,527 | **ships; bare oracle hardened** |
| medium | 1009 | 1,027,243,729 | reserve escalation |
| hard | 2017 | 8,205,738,913 | reserve escalation |

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 witnesses and 16/16 squarefree smoothness certificates |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced tagged JSON parsed from prose; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact bound `120/503^3 = 9.4293e-7` |
| G5 | pass | demo has exactly 5 valid planes; shipping reference run used 1,753,226 operations |
| G6 | pass | five attacks each 0/8; reference and compact routes each 8/8 |
| G7 | pass | spaces increase strictly; doubled `n=1006` uses `p=1009` and verifies |
| G8 | pass | 60/60 relabelling checks, 60/60 transported witnesses, 20/20 distinct keys |
| G9(c) | pass | 15 characters, about 4 tokens, 4 atoms, 165 intended operations |

The G4 prior is uniform over every canonically normalized projective plane that
does not contain the known vertex—the exact language a solver gets after
enforcing the statement's free constraints. The classical 120 odd theta
characteristics give the exact upper bound even if every tritangent is rational.

## Oracle loop and G9 diagnostic

| bare preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | Google Gemini 3.8 Flash | 1897136931 | failed | parsed plane failed the square-section check |
| easy | OpenAI GPT-5.6 Terra | 2074467780 | failed | parsed plane failed the square-section check |
| easy | Google Gemini 3.8 Flash | 1499441931 | failed | parsed plane failed the square-section check |

The harness verdict is `hardened` with zero escalations.

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural | 0/3 | hardened |
| placebo | 0/3 | hardened |

Thus hinted minus placebo is `0.0`. The hint did not improve verified success.
One hinted response correctly named and attempted the second-polar computation
but made the modular arithmetic wrong; the diagnostic therefore suggests that
exact execution remains a material part of the difficulty even after the
invariant is recognized. The answer is 15 characters / 4 atoms, and the
intended route costs at most 165 exact operations, both inside G9(c).

## Use

```python
import importlib.util
import json

path = "results/1805.11702/gen_1805_11702.py"
spec = importlib.util.spec_from_file_location("tritangents", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=12, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
text = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(text)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1805.11702 20 easy
```

## Caveats

- The current repository harness used the two-model, two-vendor pool recorded in
  `.meta.json`, although its older header still says four vendors.
- This is a deliberately special smooth family. It tests discovery and execution
  of the vertex-polar invariant, not generic tritangent computation.
- The instances are over finite fields, as allowed by the paper, rather than the
  real or complex settings of some geometric applications.
- Uniform plane guessing does not model a solver that already searches polar
  covariants; it only quantifies the declared certificate-language prior.
- The Magma resultant/radical implementation of Algorithm 3.1 was unavailable.
  The measured reference is the exact `O(p^2)` tangent-incidence specialization.
- The attacks omit Gröbner-basis, XL, and learned coefficient-statistic methods.
  The successful polar method is disclosed separately as the intended route.
- The canonical key is invariant under ambient `GL(4)`, equation rescaling,
  term order, `GL(2)` source changes, and weighted-`w` shift/scale. Its
  degree-four binary-dodecic invariants are not a complete isomorphism classifier,
  so rare collisions between nonisomorphic curves remain possible.
