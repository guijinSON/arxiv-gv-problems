# Plane quartics and heptagons — verified generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | telescoping |
| Certificate form | exact symbolic |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator is based on Agostini, Plaumann, Sinn, and Wesner, [*Plane
quartics and heptagons*](https://arxiv.org/abs/2408.15759).  A solver is handed
the paper's Scorza divisor classes in the numerical cycle ring of a product
`C^n`, together with exact rational weights, and must return the top
intersection in the collected form `A*3^n+B`.  The answer is two rational
coefficients encoded as a small JSON object.  `verify` checks the mixer form,
computes the endpoint quotient using integer arithmetic, and compares both
coefficients exactly; it neither uses floats nor reads `inst["answer"]`.

This is native algebraic coverage, not a graph or finite-field surrogate.  The
fixed-width mixer is only a succinct reindexing of rational scalar weights; the
object being intersected and the cycle-ring rules exposed to the solver are the
ones used in Section 4 of the paper.

## Why it is hard — Track B

Equation (4.2) identifies the Scorza class as
`2*x_1+2*x_2+Delta`, and Lemma 4.5 proves that its cyclic top intersection on
`C^n` is `2*3^n-6`.  Multilinearity pulls all rational weights outside the
intersection.  The generator composes XOR, odd affine maps modulo a power of
two, triangular XOR-shifts, and word rotations.  Each map is bijective, so all
hidden indices are a permutation of `0,...,n-1`; the weight product therefore
telescopes to `r(n)/r(0)`.

An efficient algorithm exists and is disclosed.  Exact factor-balance
enumeration applies every mixer operation at every index, uses `O(n*r)` time and
`O(n)` bytes, and solves 8/8 shipping instances.  At `n=8,388,608`, it used
276,824,073 counted exact/bitwise primitives and averaged 15.337 seconds in the
final selftest.  Recognizing the invariant reduces this to eight exact
arithmetic operations and a symbolic invocation of Lemma 4.5.  This is not a
Track A complexity claim.

The initial idea—plant a rational heptagon and ask for an inverse—was not used.
Section 2 says that `n=7` is the unique generically finite polygon-to-adjoint
case (`n<=6` has infinite fibres and for `n>7` a general target has no inverse).
Proposition 3.2 reconstructs through a Scorza intersection, while Section 5 uses
symbolic computation for the Klein quartic.  Theorem 5.5 counts the general
fibre but does not give a scalable exact inverse algorithm or a measured hard
distribution.  Claiming Track A for planted inverse instances would therefore
have been unsupported.

## Worked demo (`seed=0`)

This is the complete rendered instance for the hand-scale preset (line wrapping
is the only change).

```text
Compute an exact weighted Scorza-class intersection in collected form.

Let C be a smooth plane quartic, and let eta be an even theta characteristic
with h^0(C,eta)=0. On C^8, x_k denotes the pullback of the class of a
point from coordinate k, and Delta_kl denotes the pullback of the diagonal
from coordinates k and l. Coordinate indices are 1-based. For i=0,...,7,
put k=i+1 and l=((i+1) mod 8)+1 and define the Scorza divisor class

    S_i = 2*x_k + 2*x_l + Delta_kl.

The exact intersection rules are: degree(x_1*...*x_8)=1; x_k^2=0;
x_k*Delta_kl=x_k*x_l; a connected tree of distinct diagonal factors is its
small-diagonal class; and a connected cycle of diagonal factors has degree
-(2g-2)=-4 because g=3. Products over disconnected components multiply,
and degree is linear over rational coefficients. These rules completely
determine the top-degree product below.

All mixer values are unsigned 3-bit integers, hence lie in 0,...,7.
XOR, AND, <<, and >> are the usual bitwise operations with zero-filled shifts.
ROTL_3(x,s) rotates the 3-bit word x left by s positions. For each
i=0,...,7, start with x=i and apply these assignments in order; call the
final value j_i:

  1. x := x XOR 6
  2. x := (1*x + 4) mod 8

Define the positive integers

    r(z) = 126*z + 115,
    m(i) = 1 + ((5*i + 7) mod 8),

and the exact rational scale

    s_i = (r(j_i+1)*m(i)) / (r(j_i)*m(i)).

Compute the top intersection

    I = product over i=0,...,7 of (s_i*S_i).

Give I in collected symbolic form A*3^8+B as exactly two ordered terms.
Term 0 must have base 3, exponent 8, and a positive rational coefficient.
Term 1 must have base 1, exponent 8, and a negative rational coefficient.
A rational a/b is encoded as [a,b], with 1 <= |a| <= 8984
and 1 <= b <= 115; bounds are inclusive and b is positive.
Coefficients need not be reduced. The term order is mandatory.

Give your final answer inside <answer></answer> tags as one JSON object with
the sole key "terms" and exactly two objects of the displayed shape.
Example: <answer>{"terms":[{"coefficient":[2,1],"base":3,"exponent":8},{"coefficient":[-6,1],"base":1,"exponent":8}]}</answer>
Output nothing else inside the tags.
```

The answer is:

```json
{"terms":[{"coefficient":[2246,115],"base":3,"exponent":8},{"coefficient":[-6738,115],"base":1,"exponent":8}]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Adding one to the
constant numerator returns `(False, "constant coefficient is incorrect")`.
A person can solve this demo by listing all eight mixed indices or by spotting
the permutation and telescoping invariant.

## Difficulty presets

| preset | n | mixer operations | label bits | status |
|---|---:|---:|---:|---|
| demo | 8 | 2 | 7 | hand-scale illustration |
| easy | 2,097,152 | 11 | 40 | oracle-solved predecessor |
| medium | 4,194,304 | 12 | 44 | oracle-solved predecessor |
| hard | 8,388,608 | 12 | 44 | **shipping; held 0/3** |

The first bare run reached `budget_bound`; the harness explicitly permitted a
higher-preset rerun.  After sliding the ladder upward, the new `hard` rung held.
The module can still double `n` without lengthening the eight-atom answer.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | planted witness verified for 4 presets × 3 seeds |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose/fenced/tagged answer round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware random candidates valid |
| G5 | pass | shipping density sample 0/200,000; 4,096-restart baseline 0 hits in 0.027 s |
| G6 | pass | 4 attacks × 8 seeds, 0 successes; reference algorithm 8/8 |
| G7 | pass | doubled `n=16,777,216` builds and verifies |
| G8 | pass | 40 invariant re-encodings, 40 real-transform checks, 20/20 distinct unrelated keys |
| G9 | pass | 178 chars, 45 estimated tokens, 8 atoms, 8 intended exact operations |

The bounded shipping certificate language contains
`69,712,942,610,447,246,017,666,279,848,668,538,295,927,457,034,007,924,035,042,361,948,224`
encodings.  This cardinality is not used as a substitute for the measured
density or attack cost.

## Bare oracle loop

The table uses the preset labels recorded by `harden.py`; after the required
ladder slide, old `medium`, old `hard`, and `escalated` are current `easy`,
`medium`, and `hard` respectively.

| recorded/current preset | seed | model | solved | reason |
|---|---:|---|---:|---|
| easy/dropped | 993560010 | Gemini 3.8 Flash | yes | verified answer |
| easy/dropped | 1315164082 | GPT-5.6 Terra | yes | verified answer |
| easy/dropped | 1369053200 | Gemini 3.8 Flash | no | empty length-limited reply |
| medium/easy | 2102816667 | Gemini 3.8 Flash | no | empty length-limited reply |
| medium/easy | 400961049 | GPT-5.6 Terra | yes | verified answer |
| medium/easy | 1876519360 | GPT-5.6 Terra | yes | verified answer |
| hard/medium | 204367016 | Gemini 3.8 Flash | no | empty length-limited reply |
| hard/medium | 865208794 | GPT-5.6 Terra | yes | verified answer |
| hard/medium | 1334091532 | GPT-5.6 Terra | yes | verified answer |
| escalated/hard | 1589787661 | GPT-5.6 Terra | no | wrong leading coefficient |
| escalated/hard | 1392234307 | Gemini 3.8 Flash | no | empty length-limited reply |
| escalated/hard | 480953702 | Gemini 3.8 Flash | no | empty length-limited reply |

## G9 diagnostic arms

| arm | solved/attempts | interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 2/3 | the named invariant often unlocks the compact route |
| placebo hint | 1/3 | one solve is attributable to prompt/model variance |

`hinted - placebo = 1/3`.  The structural hint therefore had positive measured
value, consistent with `intuition_type="invariant"`, though the sample is only
three attempts per arm and this diagnostic is not a gate.  The hinted level's
diagnostic verdict is `too_easy`, which is expected and does not block shipping.

## Use

```python
import importlib.util
import json
from pathlib import Path

path = Path("results/2408.15759/gen_2408_15759.py")
spec = importlib.util.spec_from_file_location("gen_2408_15759", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
question = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Because a dotted numeric directory is awkward in ordinary Python import syntax,
`importlib.util.spec_from_file_location` is the portable choice when importing
directly from this result directory.  From the repository root, emit 20 shipping
instances with:

```bash
scripts/emit.sh 2408.15759 20 hard
```

## Caveats

- This is a no-tool benchmark, not evidence of computational intractability.  A
  linear factor-balance sweep solves every generated instance.
- The 0/200,000 guess rate is conditional on `random_candidate`'s explicit prior:
  both bases and exponents are fixed for free, while bounded signed rational
  coefficients are sampled independently.  It is not an exact solution count,
  and unreduced fractions give a valid value more than one encoding.
- Two of the three decisive bare failures were empty Gemini responses reported
  by the harness as length-limited/content-filter outcomes; only the Terra
  failure returned a substantive but incorrect coefficient.  The hardness
  evidence is therefore weaker than three independently wrong mathematical
  derivations, even though it satisfies the recorded harness contract.
- The mixer is an auxiliary presentation device, not a construction from the
  paper.  What is paper-native is the Scorza class and its intersection identity.
- No external CAS, arbitrary-precision performance implementation, or additional
  LLM family beyond the harness pool was tested.  Making the mixer explicit or
  supplying the structural hint often makes the instance easy, as the G9 arm
  shows.
