# Transported Waring decompositions for arXiv:1801.05377

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | polynomial (five weighted linear forms) |
| Intended intuition | invariant: a square-zero matrix algebra collapses a long product to endpoint data |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The source is Anna Seigal, [*Ranks and Symmetric Ranks of Cubic Surfaces*](https://arxiv.org/abs/1801.05377). Section 1 identifies a homogeneous cubic in four variables with a symmetric `4 x 4 x 4` tensor and defines a Waring decomposition `F=sum w_i L_i^3`. Section 2 displays the simultaneous `GL(4)` coordinate action and observes that it carries rank decompositions with it. An instance gives a five-cube decomposition of a base cubic, a succinct chain of exact coordinate changes, and all 20 coefficients of the transformed cubic. The solver must return five transformed linear forms.

The answer is a genuine native algebraic witness, not indices into a compiled graph. `verify` expands the five weighted cubes over the integers and compares all 20 coefficients. It does not read `inst["answer"]`, and it accepts every bounded, normalized five-form identity satisfying the statement.

## Why this is Track B

Track A would be false here. Section 2's coordinate formula directly gives a sequential algorithm: construct every `M_k` and transport through all `n` changes. At shipping `n=8192`, that reference algorithm succeeds on 8/8 instances, uses 1,597,580 counted exact operations, and took 0.212 seconds per instance in the final self-test. General Waring-decomposition algorithms also exist, while Sylvester's Pentahedral Theorem in Section 2 says that the generic five-cube decomposition is unique; none of that supports a structural-hardness claim for this distribution.

The benchmark instead tests whether a no-tool solver notices that the two displayed generators satisfy `N_i N_j=0` for every pair. The long matrix product then depends only on two sums, and each sum telescopes because `d_j(k)=h_j(s_(k+1))-h_j(s_k)`. Binary modular exponentiation obtains the final state. The compact route used 237 counted operations; the 61-bit modular arithmetic is still not a sequence a model can execute casually without tools. The initial 19-bit-modulus ladder was solved throughout and reached `budget_bound`; the shipped ladder therefore grows the modulus, a fixed-witness-length axis, rather than merely lengthening the answer.

The easy paper regimes were deliberately not presented as hard: the theorem of Friedland quoted in Section 2 proves equality of rank and symmetric rank when rank is at most flattening rank plus one, and the paper handles many cubic surfaces through classification or explicit normal forms. This generator does not ask for a rank decision or pretend those cases are difficult.

## Worked demo (`seed=0`)

This is the complete output of `render(make_instance(seed=0, **DIFFICULTY["demo"]))`. A person can solve it on paper: there are only three changes, so either direct transport or the square-zero shortcut is hand-scale.

```text
Transported Waring decomposition of a cubic surface

A linear form is a0*x0+a1*x1+a2*x2+a3*x3.  A five-term Waring
decomposition of a homogeneous cubic F is an identity

    F(x) = sum_(i=1)^5 w_i * L_i(x)^3.

All arithmetic in this problem is exact integer arithmetic.  Row vectors
represent linear forms.  Replacing x by a 4x4 matrix M times x sends the row
of L to row(L)*M, and it sends every cube in the displayed decomposition in
the same way.

The base cubic is already decomposed as follows (the five weights are
distinct):
  weight 4: (x0 - x1 + 2*x2 - x3)^3
  weight 18: (x0 - x2 - 2*x3)^3
  weight 26: (x0 + x1 + x2)^3
  weight 28: (x0 + x1 + 2*x3)^3
  weight 34: (x0 + 2*x1 + 2*x3)^3

It undergoes n=3 successive coordinate changes M_0,...,M_(n-1).
Define states as the least nonnegative residues

    s_0 = 11
    s_(k+1) = 15*s_k mod 17,

for integer k with 0 <= k < n.  For h=[c0,c1,c2], h(s) means the ordinary
integer c0+c1*s+c2*s^2 after s has been replaced by its least nonnegative
residue.  Here

    h0 = [-1, 1, 0]
    h1 = [1, -1, -1].

The two generator matrices are

N0 =
  [0, 0, 0, 0]
  [0, 10, 4, 2]
  [0, -15, -6, -3]
  [0, -20, -8, -4]
N1 =
  [0, 0, 0, 0]
  [0, 5, 2, 1]
  [0, -5, -2, -1]
  [0, -15, -6, -3]

For 0 <= k < n, let

    d_j(k) = h_j(s_(k+1)) - h_j(s_k)       for j=0,1,
    M_k = I_4 + d_0(k)*N0 + d_1(k)*N1.

The changes act in increasing-k order, so a base row L becomes
L*M_0*M_1*...*M_(n-1).  The resulting target cubic has the following 20
coefficients.  A line e0,e1,e2,e3: c means coefficient c on
x0^e0*x1^e1*x2^e2*x3^e3.

  3,0,0,0: 110
  2,1,0,0: 169194
  2,0,1,0: 67584
  2,0,0,1: 34020
  1,2,0,0: 876369462
  1,1,1,0: 700997580
  1,1,0,1: 352156452
  1,0,2,0: 140180148
  1,0,1,1: 140842752
  1,0,0,2: 35377272
  0,3,0,0: -8087454578
  0,2,1,0: -10360564818
  0,2,0,1: -4671233838
  0,1,2,0: -4406493714
  0,1,1,1: -4000403076
  0,1,0,2: -897654846
  0,0,3,0: -622504184
  0,0,2,1: -852767868
  0,0,1,2: -385520880
  0,0,0,3: -57381096

Find five transformed linear forms whose weighted cubes equal that target.
Output one object for each of the five displayed weights, in strictly
increasing weight order.  Each form must be [1,a,b,c], all entries must be
integers, |a|,|b|,|c| <= H=2567, and the five forms must be distinct.

Give your final answer inside <answer></answer> tags as a JSON list of objects
with exactly the keys "weight" and "form". Output nothing else inside the tags.
```

Answer:

```json
[{"weight":4,"form":[1,-61,-22,-13]},{"weight":18,"form":[1,-2565,-1027,-515]},{"weight":26,"form":[1,-14,-5,-3]},{"weight":28,"form":[1,1861,744,374]},{"weight":34,"form":[1,1502,600,302]}]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Increasing the first form's `x1` coefficient by one returns `(False, "weighted cube expansion does not equal the target cubic")`.

## Difficulty presets

| preset | chain length `n` | modulus | base/h bounds | status |
|---|---:|---:|---:|---|
| demo | 3 | 17 | 2 / 1 | hand-solvable illustration |
| easy | 8,192 | `2^61-1` | 5 / 7 | **ships; bare hardened 0/3** |
| medium | 16,384 | `2^89-1` | 6 / 8 | reserved escalation |
| hard | 32,768 | `2^107-1` | 7 / 9 | reserved escalation |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted checks across every preset |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | tagged JSON recovered from prose/fences; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 structure-aware samples; 1,992-bit sampled language |
| G5 | pass | shipping sampled density 0; 256-restart attack 0/8, 0.0076 s/run; reference 1,597,580 ops, 0.212 s |
| G6 | pass | six attacks all 0/8; sequential reference and compact route both 8/8 |
| G7 | pass | doubling `n` doubles reference work from 1,597,580 to 3,195,020 ops; answer stays 25 atoms |
| G8 | pass | 60 invariance and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 744 chars, about 186 tokens, 25 atoms, 237 intended operations |

## Bare oracle loop

| preset | model | seed | solved | recorded reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 631629364 | no | candidate had the wrong term count |
| easy | GPT-5.6 Terra | 1698242829 | no | supplied code, not a nonempty answer list |
| easy | Gemini 3.8 Flash | 1917087511 | no | five-form expansion was incorrect |

The script-owned verdict is `hardened` at `easy`, with zero escalations.

## G9 diagnostic arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 2 / 3 | solved in two independent calls |

The hinted-minus-placebo rate is `-2/3`. The structural hint did not help on these unpaired random draws; the placebo arm did surprisingly better than both bare and hinted. This small sample does not show a causal negative effect. It does show that the claimed invariant is not sufficient by itself to remove the exact-arithmetic burden, and that oracle/model/seed variance is material. G9(a,b) are diagnostic only. The gated measurements are 744 serialized characters, 25 atomic elements, and 237 intended exact operations.

## Use

From the repository root:

```python
import random
import sys
sys.path.insert(0, "results/1801.05377")
import gen_1801_05377 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))
candidate = g.parse_answer("<answer>...</answer>")
print(g.verify(inst, candidate))
print(g.verify(inst, inst["answer"]))  # (True, "ok")
print(g.random_candidate(inst, random.Random(9)))
```

Emit artifacts with:

```bash
bash scripts/emit.sh 1801.05377 20 easy
```

## Caveats

- This is not evidence that generic Waring decomposition or tensor rank is hard. The base decomposition and coordinate chain are part of the instance, and a tool-equipped implementation solves the shipping preset in about 0.2 seconds.
- The sampled `P(guess)=0/200000` is relative to the explicitly bounded prior: ordered distinct normalized forms in `[-H,H]^3`, with weights fixed. It does not model a solver that has inferred correlations from the matrices. Zero observed hits is not a confidence proof that the unknown true density is zero.
- The adversary panel covers unchanged forms, first-step greedy transport, a generator-magnitude outlier, an endpoint ansatz that omits the initial value, a diagonal-only ansatz, and random restarts. It does not run a general-purpose computer-algebra Waring solver, because sequential transport is already a stronger guaranteed algorithm for the extra chain data supplied here.
- `canonical_key` is exact for term reordering and affine coordinate changes in the normalized `x0=1` chart, using the weighted fifth point's barycentric coordinates. Full `GL(4)` canonicalization, which would change the bounded answer language and its normalization, is not attempted.
- The generator does not certify uniqueness or minimality of every sampled decomposition; neither is needed by the question. It certifies and checks the requested five-term identity exactly, and accepts alternative valid identities inside the stated language.
- `gvlib` is imported when present, but this family needs only standard-library integer arithmetic and degrades cleanly if `gvlib` is unavailable.
