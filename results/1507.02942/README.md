# arXiv 1507.02942 — verified Nottingham-series iterates

> **Qualification status:** all local correctness, density, adversary, scaling,
> canonicalization, and size gates pass. The required four-vendor oracle and G9
> diagnostics are **pending** because OpenRouter returned HTTP 403 `Key limit
> exceeded (total limit)` on every retry. The error transcripts are preserved;
> they are not counted as model failures and this directory is not yet qualified
> for submission.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | polynomial |
| Native objects | truncated normalized formal power series and composition iterates over `F_p` |
| Intended intuition | change of variables: scaling the formal parameter normalizes the quadratic coefficient |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

The source is Fernández-Alcober and Gül, [*Beauville structures in finite
`p`-groups*](https://arxiv.org/abs/1507.02942). An instance gives several formal
series `f(t)=t+u t²+v t³` over a prime field and asks for their `p^m`-fold
composition iterates at the two surviving high degrees. The answer is an ordered
list of canonical sparse polynomials. Verification uses exact modular inversion,
exponentiation, and coefficient comparison, so no floating point, search, or
stored-answer lookup is involved.

This is the paper's native Nottingham-group arithmetic, not a graph or finite-field
analogue of a real/continuous problem. It is the calculation used by Lemma 3.3 and
Corollary 3.4 to control powers in distinguished diamonds and prove the later
Beauville results.

## Why Track B, not Track A

The prior idea—ask for Beauville generating pairs—fails the hardness triage.
Theorem 2.5 says that in the paper's semi-`p^(e-1)`-abelian or potent regime every
lift of a Beauville structure from `G/Phi(G)` works. Theorem 3.7 explicitly gives
`{u,v}` and `{uv²,uv⁴}` for the relevant Nottingham quotients when `p>=5`.
Those are efficient constructions and the witnesses are abundant.

The retained family is honestly Track B. Lemma 3.2 supplies a mechanical
coefficient route; the reference implementation directly repeats truncated
composition in `O(batch*p^m*z_m²)` exact field operations. At the hard preset it
solved 8/8 instances, averaging **26,426,636 modular operations and 2.101186 s**.
Corollary 3.4 instead gives the two coefficients of
`t+t²+lambda*t³`, and scaling conjugacy transports them to general nonzero `u`.
That compact algorithm takes **136 conservatively counted field operations** at
the hard preset. The benchmark asks whether a no-tool solver recognizes this
change of variables; it does not claim the computation is algorithmically hard.

## Worked demo (`seed=0`)

The complete rendered instance is:

```text
Compute exact high composition iterates of truncated formal power series.

All coefficients lie in the prime field F_5, represented by integers 0,...,4 with every operation reduced modulo 5.
For series h(t) and g(t), h composed with g means substitute g(t) for every t in h(t), expand, and reduce coefficients modulo p.
After every composition discard every monomial of degree at least 9; equivalently, work modulo t^9.
The E-fold iterate f^[E] is f composed with itself E times; f^[0](t)=t.

Here m=1, E=p^m=5, and
  z_m = 2 + sum_(j=1)^m p^j = 7.
There is 1 input, indexed 0:
  0: f_0(t) = t + 2*t^2 + 3*t^3

It is guaranteed that each requested iterate has exactly the form
  f_i^[E](t) = t + A_i*t^7 + B_i*t^8 (mod t^9),
where A_i and B_i are both in 1,...,4.
Find all of these output polynomials.  The outer-list order must match the input order; no input may be omitted or repeated.

Represent each polynomial canonically as
  [[1,[1]],[A_i,[7]],[B_i,[8]]].
Thus a coefficient is an integer residue and a monomial is a one-entry exponent list.  Terms must appear in increasing exponent order.

Give your final answer inside <answer></answer> tags, as one JSON array containing exactly 1 polynomial.
Example format only: <answer>[[[1,[1]],[1,[7]],[1,[8]]]]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[[[1,[1]],[1,[7]],[2,[8]]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the coefficient
`1` by `0` returns `(False, "polynomial 0 must have two nonzero high
coefficients")`. A person can solve this demo on paper: direct expansion is only
one fivefold iterate (438 primitive operations in this deliberately simple
implementation), while the scaling/Corollary route takes 13 field operations.

## Difficulty presets

| Preset | `n` → `p` | `m` | Series | Iterate | `z_m` | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 → 5 | 1 | 1 | 5 | 7 | hand example |
| easy | 7 → 7 | 1 | 4 | 7 | 9 | oracle not reached (quota error) |
| medium | 7 → 7 | 2 | 6 | 49 | 58 | local gates pass |
| hard | 11 → 11 | 2 | 8 | 121 | 134 | provisional shipping preset; oracle pending |

`escalate()` doubles `n` and increments `m`, which raises the next prime,
composition count, and truncation degree without changing the eight-polynomial
answer shape.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers verify |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose/fence round-trip and JSON-native answer |
| G4 | pass | 0/200,000 guesses; exact declared-space density `10^-16` |
| G5 | pass | demo has exactly 1 valid answer; hard baseline 26,426,636 ops / 2.101186 s |
| G6 | pass | six attacks, each 0/8; reference algorithm 8/8 as expected |
| G7 | pass | doubling `n` changes `p:11→23`, iterate `121→529`, answer stays 24 terms |
| G8 | pass | 60/60 invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 257 worst-case chars, 209 conservative tokens, 24 terms, 136 intended operations |

The six failing G6 attacks were: smallest nonzero residues, copying `(u,v)`, the
normalized deficit alone, Corollary 3.4 with scaling ignored, the `m=1` ansatz,
and 256 structure-aware random restarts per seed.

## Oracle loop and G9 arms

The bare script selected `easy` and made four retries; all were infrastructure
errors. They must not be summarized as “0/3 solved.”

| Arm/preset | Models and seeds | Valid attempts | Result |
|---|---|---:|---|
| bare / easy | Gemini `245954555`, Terra `396011994`, Gemini `1102992225`, Gemini `1080428668` | 0 | four HTTP 403 quota errors on the latest retry |
| structural / hard | Grok `1381750315`, Grok `999259870`, Claude `642378727`, Claude `874304451` | 0 | four HTTP 403 quota errors |
| placebo / hard | Grok `1134061861`, Claude `1772145449`, Claude `1911594541`, Claude `45302862` | 0 | four HTTP 403 quota errors |

Therefore hinted-minus-placebo is **not measured**, and no conclusion about the
claimed change-of-variables intuition is justified yet. The module records each
arm as 0 attempts with verdict `pending`; the transcript files retain the actual
errors. Re-run all three arms after replenishing the OpenRouter key, then replace
those pending values and re-run `selftest()`.

## Use

```python
import gen_1507_02942 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

After oracle qualification, emit from the repository root with:

```bash
scripts/emit.sh 1507.02942 20 hard
```

## Caveats

- The checker implements Corollary 3.4 and scaling conjugacy directly. This is
  deliberate for exact cheap grading, but makes the benchmark one of formula
  recognition, not general formal-series computation.
- The `10^-16` density is for independent nonzero high coefficients after all
  promises in the statement are enforced. A solver that derives algebraic
  correlations has a much sharper prior; density alone is not hardness evidence.
- Direct dense composition was measured. Faster power-series composition, a CAS,
  interpolation across the batch, and broader symbolic attacks were not tested.
- `canonical_key` is exact for input reordering and independent parameter
  scalings. It does not attempt a full classification under arbitrary Nottingham
  conjugacy, which may identify additional duplicates.
- Most importantly, the four-vendor no-tool loop has not produced a single valid
  attempt because the configured account is over its total limit. The family must
  not ship until the bare, hinted, and placebo runs complete.
