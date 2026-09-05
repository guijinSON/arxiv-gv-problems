# Projective-line generator for arXiv:1902.05133

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | matrix certificate |
| Native objects | a homogeneous surface equation over `Q`; a projective line given by two linear equations |
| Intended intuition | change of variables: recognize a low-rank triangular Waring structure |
| Domain essentiality | native; no graph, finite-field, or convenience reduction |

## What the problem is

The family comes from Bauer and Rams, [*Counting lines on projective
surfaces*](https://arxiv.org/abs/1902.05133). Section 2 fixes the operative
definition: a line lies on a degree-`d` surface `F=0` when the restriction
`F|L` vanishes identically. Example 3.9 gives the Fermat surface
`y0^d+y1^d+y2^d+y3^d=0`, containing `3d^2` lines.

The generator uses odd `d`, two pairs of equal nonzero diagonal weights, and an
invertible upper-triangular rational change `y=A x`. It chooses `A` and a
standard Fermat line first, carries the line through the change, and only then
expands the surface into the coefficient table shown to the solver. Thus the
certificate is known by transformation, not by solving the generated surface.
The answer is a `2 x 4` reduced integer matrix
`[[1,0,u,v],[0,1,w,z]]`; the checker substitutes
`[-us-vt:-ws-zt:s:t]` and compares every coefficient with zero exactly.

Smoothness is also by construction: a weighted diagonal Fermat surface in
characteristic zero has no projective common zero of its four partial
derivatives, and an invertible change of coordinates preserves smoothness.

## Why this is Track B

The paper proves a geometric counting bound, not a complexity theorem, so a
Track A claim would be unsupported. An efficient recovery algorithm is known
for this generated distribution. Full triangular Waring deflation recovers the
four hidden linear forms in
`O(binomial(d+3,3))` exact coefficient operations, pairs equal recovered
weights, and row-reduces their sums. At shipping `d=23`, the reference run
solved 8/8 instances, scanning 23,400 power terms and performing 184,696 counted
operations in 0.401 seconds total (2,925 terms per instance).

The compact route reads only the four pure and six near-pure coefficient
slices. Along the hidden triangular flag these determine one form at a time;
equal weights identify the two cancelling odd-power pairs. It uses 10
coefficient lookups and at most 86 exact operations. The compression target is
recognizing that route inside a 2,600-row tensor, not denying
that a mechanical algorithm exists. If the four power forms or the coordinate
change were displayed, the family would be immediate; they are deliberately
expanded away.

## Worked demo

For `seed=7`, the complete hand-scale `demo` rendering is:

```text
FIND A PROJECTIVE LINE ON AN EXACT SURFACE

Work over the rational numbers.  The four homogeneous coordinates on
projective 3-space are x0,x1,x2,x3.  The surface X is the zero set F=0 of the
homogeneous degree-3 polynomial displayed below.  A table row

    e0,e1,e2,e3 : c

means the term c*x0^e0*x1^e1*x2^e2*x3^e3.  Exponents are nonnegative and sum
to 3; every nonzero term is listed exactly once, and every omitted
monomial has coefficient zero.  All coefficients are exact base-10 integers.

Your witness must be a projective line in the fixed dual affine chart

    x0 + u*x2 + v*x3 = 0
    x1 + w*x2 + z*x3 = 0,

where u,v,w,z are integers in the inclusive interval [-8,8].  These
independent equations define a line parametrized by

    [x0:x1:x2:x3] = [-u*s-v*t : -w*s-z*t : s : t]

for [s:t] in projective 1-space.  The line lies on X exactly when substituting
this parametrization into F gives the zero polynomial in s,t (all 4
coefficients must vanish).

Expanded coefficient table (20 rows):
  0,0,0,3 : -26
  0,0,1,2 : -9
  0,0,2,1 : -15
  0,0,3,0 : -3
  0,1,0,2 : -39
  0,1,1,1 : -66
  0,1,2,0 : -3
  0,2,0,1 : -39
  0,2,1,0 : -33
  0,3,0,0 : -13
  1,0,0,2 : 24
  1,0,1,1 : 24
  1,0,2,0 : 6
  1,1,0,1 : 48
  1,1,1,0 : 24
  1,2,0,0 : 24
  2,0,0,1 : -12
  2,0,1,0 : -6
  2,1,0,0 : -12
  3,0,0,0 : 2

Give your final answer inside <answer></answer> tags as the exact JSON integer
matrix [[1,0,u,v],[0,1,w,z]].  Do not use fractions, decimals, or entries
outside the stated inclusive bounds.  Row order is fixed by the two leading
pivots, repeats are not allowed, and indexing is 0-based.
Example of the required syntax (not necessarily a solution):
<answer>[[1,0,2,-3],[0,1,4,5]]</answer>
Output nothing else inside the tags.
```

The constructed answer is
`<answer>[[1,0,-2,0],[0,1,-1,2]]</answer>`, and `verify` returns
`(True, "ok")`. Changing `u` from `-2` to `-1` returns
`(False, "restriction is nonzero: coefficient of s^3*t^0 is -14")`.
A person can solve this demo on paper: the 20 cubic coefficients are small, and
the pure/near-pure slices expose the four triangular cubes successively.

## Difficulty presets

| Preset | Degree `d` | form-entry bound | answer bound | coefficient rows | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 2 | 8 | 20 | hand example; skipped by `harden.py` |
| easy | 23 | 15 | 1,024 | 2,600 | **ships; bare and hinted pools held** |
| medium | 29 | 19 | 2,048 | 4,960 | fallback |
| hard | 35 | 23 | 4,096 | 8,436 | fallback |

An earlier degree-17 rung held the bare pool but failed G9(b): after the
structural hint, GPT-5.6-terra produced a verified line. The single permitted
rung increase moved degree 23 into `easy`; no further hand-tuning occurred.
`escalate()` continues raising odd degree while the answer remains 2 x 4.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 preset/seed witnesses verify; JSON and expansion-cache checks pass |
| G2 | pass: five corruptions rejected with five distinct reasons |
| G3 | pass: prose/fence/tag round-trip succeeds; garbage returns `None` |
| G4 | pass: 0/200,000 bounded chart matrices valid; declared space 17,626,570,956,801 |
| G5 | pass: shipping density 0/200,000; demo exact count 1/83,521; reference solves 8/8 |
| G6 | pass: every failing attack below succeeds 0/8; reference algorithm is separate as Track B requires |
| G7 | pass: degree 47 builds, verifies, and raises reference terms from 2,925 to 20,825 with unchanged 2 x 4 answer shape |
| G8 | pass: 80 invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass: hinted pool 0/3; 29 chars, 8 atoms, about 8 tokens; compact route 86 operations |

| G6 attack | Successes | Counted work over 8 seeds |
|---|---:|---:|
| pure-coefficient outlier | 0/8 | 32 operations |
| greedy endpoint cancellation | 0/8 | 3,136 operations |
| 256 uniform random restarts | 0/8 | 2,048 candidates |
| in-context small-integer Waring ansatz | 0/8 | 5,000 candidates |

## Oracle loop

The final bare run held at degree 23 without escalation. Two models submitted
parseable but invalid matrices; Claude exhausted its 32k completion budget and
returned no answer, which the harness records explicitly rather than treating
as a parser success.

| Preset | Model | Seed | Solved | Exact outcome |
|---|---|---:|---|---|
| easy (`d=23`) | Grok 4.6 | 471806815 | no | nonzero `s^23 t^0` coefficient |
| easy (`d=23`) | Gemini 3.1 Pro Preview | 83207668 | no | nonzero `s^23 t^0` coefficient |
| easy (`d=23`) | Claude Sonnet 5 | 1677586747 | no | empty length-limited response, recorded as such |

## G9 arms

| Arm | Solved / attempts | Outcome |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; mandatory G9(b) passes |
| placebo hint | 0/3 | hardened diagnostic |

Hinted minus placebo is `0.0`. At degree 23 the structural sentence bought no
observed successes, so this run does not show an advantage from explicitly
naming the intended change-of-variables intuition. The failed degree-17 hinted
rung does show that the hint can carry real information. The final answer is 29
serialized characters for the measured shipping instance (8 atomic integers,
about 8 tokens), and the intended post-insight route uses 86 exact operations.

## Use

```python
import gen_1902_05133 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
assert g.verify(inst, inst["answer"]) == (True, "ok")

text = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(text)
print(g.verify(inst, candidate))
```

From the repository root:

```bash
bash scripts/emit.sh 1902.05133 20
```

The module uses only the Python standard library. `gvlib` is unnecessary here
because all surface, line, expansion, and verification coefficients are
integers.

## Caveats

- The 0/200,000 density is an observed fraction under the declared uniform
  prior on the four bounded chart entries. It is not an exact shipping solution
  count and, by itself, is not a statistical proof that the true probability is
  below `1e-6`. The exact demo count is only for degree 3.
- This is not an average-case hardness theorem. It is a Track B compression
  benchmark whose reference algorithm is explicitly efficient. A CAS with
  symmetric-tensor decomposition, or a solver that notices and executes the ten
  leading-slice equations, makes it easy.
- No general-purpose Gröbner-basis package, numerical tensor-decomposition
  library, or commercial computer-algebra system was run. Full exact triangular
  deflation is the domain-standard reference for this deliberately triangular
  distribution; the four failing attacks are weaker in-context probes.
- The 123k-character shipping prompt is large. One bare and one hinted Claude
  response exhausted the 32k output budget; the other four bare/hinted attempts
  were substantive wrong answers. Thus the oracle evidence is not six
  substantive matrices, and prompt length may contribute to failure.
- `canonical_key` is invariant under tested term reorderings, global scaling,
  upper-unipotent coordinate changes, and their compositions. It keys on the
  normalized diagonal-weight moduli and is not a complete algorithm for
  projective equivalence; exotic equivalent presentations may be missed.
- Restricting answers to the displayed integer affine chart is part of the
  problem language. The construction guarantees a witness there, but other
  projective lines outside that chart are intentionally not accepted as outputs.
