# arXiv 0901.2394 — determinant-factored Frobenius primary decompositions

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity / finite-field factorization |
| Certificate form | polynomial |
| Intended intuition | change of variables: expose the two characteristic polynomials of a second-order determinant recurrence |
| Domain essentiality | native |
| Reduction | none |

This module turns Trung T. Dinh's [*Growth of primary decompositions of
Frobenius powers of ideals*](https://arxiv.org/abs/0901.2394) into an exact
factor-certificate problem. The solver receives a prime-field quotient

`R = F_p[t,x]/(h(t)x)`, the ideal `I=(x)`, and the paper's recurrence defining
`h`. It must return every irreducible linear factor `tau_i=t+c_i`; those
polynomials specify the variable primary components `(x^p,tau_i)` of
`I^[p]=(x^p)`. Verification checks coefficient bounds, two Vieta identities,
and the complete product in `F_p[t]`. It does not read the planted answer.

## Why the construction is valid, and what “hard” means

Lemma 3.1 is the certificate theorem. If `I^[q]:h_q` is primary to `(x)`, the
irreducible-power factors of `h_q` give the other primary components. Here
`((x^p,hx):h)=(x)` follows directly from `gcd(h,x)=1`; `(x)` is prime, while
each component quotient is `F_p[x]/(x^p)`. Thus the factor list is an exact,
executable certificate of the displayed primary decomposition.

Section 4 writes its tridiagonal determinants as

`P_(j+1)=r1*P_j-c*P_(j-1)`.

The generator samples linear `A,B` first, sets `r1=A+B` and `c=A*B`, and
builds `h` from the known factors of
`P_(M-1)=(A^M-B^M)/(A-B)`. This is inverse generation plus an identity, not
factorization of an already-built input.

Track A would be false: Lemma 3.1 reduces the varying components to univariate
factorization, and finite-field factorization is polynomial-time. The Track B
reference is Cantor–Zassenhaus with classical polynomial arithmetic, expected
`O(d^2 log(d) log(p))` base-field work here. Across eight hard-preset instances
it solved 8/8 using 963,024 counted coefficient operations (120,378 average)
and 0.155497 s total in the final self-test. The compact route notices the
characteristic roots via the square `r1^2-4c` and uses the supplied order-16
root of unity; emitting all 15 factors is bounded by 125 field operations.
Small fields are easy by direct root scanning, so only `demo` uses one.

## Worked demo (`seed=0`)

The complete rendered instance is:

```text
Primary components of a Frobenius power

All arithmetic is in the prime field F_p with p = 29; field elements
are represented by their unique integers from 0 through p-1. A polynomial
[a0,a1,...,ad] means a0+a1*t+...+ad*t^d in F_p[t] (low degree first).

Let
  r1(t) = [12, 22]
  c(t)  = [16, 23, 12].
Define determinant polynomials P_0=1, P_1=r1, and
  P_(j+1) = r1*P_j - c*P_(j-1)  for j>=1.
For m=3, the monic normalization h of P_m is
  h(t) = [19, 17, 0, 1].
For reproducibility, omega=12 has exact multiplicative order
4 in F_p.

Now form the homogeneous quotient ring
  R = F_p[t,x] / (h(t)*x)
with deg(t)=0 and deg(x)=1, and let I=(x). Its p-th Frobenius power is
I^[p]=(x^p). The polynomial h is squarefree and splits into exactly m distinct
monic linear factors tau_i(t). If h=product_i tau_i, then
  (x^p) = (x) intersect (intersection_i (x^p,tau_i))
is a primary decomposition in R. Thus your task is to give the m variable
primary components by giving all of their tau_i factors.

Output exactly 3 distinct monic linear factors. Write each tau=t+c
as the two-coefficient JSON list [c,1], with 0<=c<p. The outer list is
unordered: any factor order is accepted. Repetitions are forbidden.

Give your final answer inside <answer></answer> tags as one JSON list of these
coefficient lists.
Example format: <answer>[[3,1],[17,1],[42,1]]</answer>
Output nothing else inside the tags.
```

Its answer is `<answer>[[18,1],[19,1],[21,1]]</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the final
factor returns `(False, "wrong number of factors: expected 3")`. This demo has
only 126 structure-aware candidates and is intentionally solvable by hand.

## Presets

`p` varies with the seed but is approximately `order*n`.

| Preset | `n` | order | factors / answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 5 | 4 | 3 / 6 | hand example; skipped by hardening |
| easy | 100,000 | 16 | 15 / 30 | first oracle rung |
| medium | 100,000,000 | 16 | 15 / 30 | larger field, same witness |
| hard | 1,000,000,000,000 | 16 | 15 / 30 | **nominated shipping preset** |

The module names `hard` as `SHIPPING_DIFFICULTY`. The mandatory external
hardening verdict is not available yet: the configured OpenRouter key returned
HTTP 403 “Key limit exceeded” on every attempted vendor call. Accordingly this
directory is a completed local build, not a claimed oracle-hardened submission.

## Gate results

| Gate | Result | Measurement |
|---|---:|---|
| G1 | pass | 16/16 planted witnesses and 16/16 independent compact reconstructions |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON inside prose and a Markdown fence round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `1/N`, `log10(N)=174.980684` |
| G5 | pass | one certified shipping answer; demo brute force found exactly 1; reference cost 963,024 operations / 0.155497 s |
| G6 | pass | four attacks at 0/8 each; Cantor–Zassenhaus at 8/8 as expected |
| G7 | pass | all preset spaces increase; doubled `n` verifies with the same 30 answer atoms |
| G8 | pass | 60/60 affine/generator invariance checks, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 275 chars, about 69 tokens, 30 atoms, 125 intended operations |

The four failing G6 attacks are balanced-coefficient outliers, consecutive
constants, a one-step recurrence ansatz, and 256 random restarts per seed.

## Oracle loop and G9 diagnostics

No row below is a model failure: all calls were API errors and therefore
consumed zero scored attempts, exactly as `harden.py` requires.

| Run | Requested preset | Completed attempts | API-error redraws | Verdict |
|---|---|---:|---:|---|
| bare | easy | 0 | 4 | blocked: OpenRouter key limit |
| structural hint | hard | 0 | 4 | blocked: OpenRouter key limit |
| placebo hint | hard | 0 | 4 | blocked: OpenRouter key limit |

Thus bare/hinted/placebo are `0/0`, hinted-minus-placebo is unavailable, and
no conclusion about the hint's causal value is justified. The three
script-owned transcripts preserve the 12 HTTP 403 records. Re-run them after
restoring OpenRouter quota; do not reinterpret these errors as unsolved calls.

## Use

```python
import random
import gen_0901_2394 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
prompt = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
guess = g.random_candidate(inst, random.Random(123))
```

From the repository root, after a successful oracle rerun:

```bash
bash scripts/emit.sh 0901.2394
```

## Caveats

- The external hardness evidence is incomplete because of account quota. This
  is the principal blocker; local attack failures cannot replace STEP 4.
- This is Track B only. A CAS or finite-field library factors these instances
  quickly; the benchmark claim is the measured no-tool compression gap, not
  computational intractability.
- The exact density uses a uniform prior over distinct monic linear factors
  conditioned on the first Vieta sum, which a solver gets for free. It does
  not model a solver already exploiting the characteristic recurrence.
- Cantor–Zassenhaus is the required domain-standard attack tested here. I did
  not separately benchmark Berlekamp, fast modular composition, or a general
  Gröbner-basis primary-decomposition package; all would be tool-using
  reference algorithms, not failing no-tool attacks.
- The family is a deliberately simple quotient satisfying Lemma 3.1, not the
  Singh–Swanson hypersurface analyzed later in Section 4. The recurrence is
  native and central, but the paper does not itself claim this planted
  distribution is hard.
- `canonical_key` is complete for affine changes of the single variable and
  changes of primitive subgroup generator. No larger, unproved notion of ring
  isomorphism is claimed.
