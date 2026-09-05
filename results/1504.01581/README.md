# Compact Delsarte duals of twisted Gabidulin codes

> **Build status:** the generator and every local G1--G9(c) gate pass. The
> required four-vendor oracle evidence is unavailable: all bare, structural-hint,
> and placebo calls were rejected by OpenRouter with HTTP 403 `Key limit
> exceeded (total limit)` before inference. The script-owned transcripts are
> retained, but this result is not submission-ready and makes no empirical claim
> that the oracle pool fails the shipping instance.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | exact linear algebra |
| Certificate form | exact symbolic normal-basis coordinate word |
| Intended intuition | duality: Frobenius is adjointed through the trace |
| Domain essentiality | native |
| Reduction | none |

## What the family is

[John Sheekey, *A new family of linear maximum rank distance codes*
(arXiv:1504.01581)](https://arxiv.org/abs/1504.01581) constructs the twisted
Gabidulin code

`H_k(eta,h) = {a0*x + ... + a_(k-1)*x^(3^(k-1)) + eta*a0^(3^h)*x^(3^k)}`

over `GF(3^n)`. The solver receives the field exactly (an irreducible modulus
and a checked normal basis), the parameters, and `eta`. It must give the
normal-basis coordinates of the unique `lambda` in the exact, unshifted dual
constraint

`g0 = lambda * gk^(3^(n-h))`.

Generation samples `eta` from the required norm coset. Lemma 3 and Theorem 5
in Section 3 therefore prove that the generated code is MRD; the generator
never enumerates ranks or solves its own output. Verification checks the exact
trace-adjoint identity

`lambda = -eta^(3^(n-h))`.

In a normal basis, cubing is a cyclic coordinate shift, so this is exact digit
arithmetic. The verifier does not read `inst["answer"]`. Section 3, Theorem 6
states the dual in the usual Frobenius-shifted `H_(n-k)` normal form; this module
keeps the coefficient positions unshifted, making the displayed endpoint
constraint the literal orthogonal complement rather than merely an equivalent
code.

## Why this is Track B

An efficient algorithm is explicit and disclosed. Expand multiplication by
`eta` and Frobenius as `n`-by-`n` matrices, form the field-trace Gram matrix,
and compute the adjoint block. The implemented reference costs `O(n^3)` GF(3)
operations after extracting the systematic endpoint block; a completely
generic nullspace in the `n^2`-dimensional ambient space costs `O(n^6)`. At the
shipping preset (`n=48`) the structured reference solved 8/8, averaging
**1,711,839 counted scalar operations** and **0.09175 seconds** in the retained
run. The latest audited run measured the same operation count and **0.04967
seconds**; wall time varies, while the exact operation count does not.

The compact route uses `Tr(a^(3^h)b)=Tr(a b^(3^(n-h)))`: rotate the `eta`
coordinates right by `n-h`, then negate each trit. Its conservative count is
**104 exact operations**. This million-operation versus 104-operation gap—not
complexity-theoretic hardness—is the Track-B claim. The complete small-field
classifications in Section 1.5 and the displayed `q=3,n=4` matrices in Section
4 were avoided because they reduce to lookup.

## Worked demo

`make_instance(n=5, k=2, seed=7)` renders the following complete problem:

```text
Find the compact Delsarte dual of a twisted Gabidulin code.

All definitions and conventions follow.
Let F = GF(3)[z]/(P(z)), where the coefficients of the monic irreducible
polynomial P are listed from z^0 through z^5:
  P coefficients: 2 2 1 0 1 1
Field arithmetic is exact modulo 3 and P.  The element theta of F has
polynomial-basis coordinates, from z^0 through z^4:
  theta coordinates: 1 1 0 0 0
The ordered normal basis is
  B = (theta, theta^3, theta^(3^2), ..., theta^(3^4)).
Thus a field element is an n-coordinate column over GF(3), and cubing it
cyclically shifts its coordinates one place to the RIGHT.  Coordinates and
all subscripts below are zero-based.

A 3-linearized polynomial is a formal sum f(x)=sum_i f_i x^(3^i), with
coefficients f_i in F.  Its coefficient trace pairing with g is
  <f,g> = Tr_F/GF(3)(sum_i f_i g_i).
The Delsarte dual C^perp is the set of all g satisfying <f,g>=0 for every
f in C.

Here n=5, k=2, and h=1.  The nonzero twist eta has normal-basis
coordinate word
  eta = 11211
and it satisfies N_F/GF(3)(eta) != (-1)^(n*k).  Define the twisted code
  C = { a0*x + a1*x^3 + ... + a_(k-1)*x^(3^(k-1))
         + eta*(a0^(3^h))*x^(3^k) : a0,...,a_(k-1) in F }.

Your witness is the normal-basis coordinate word of the unique nonzero
lambda for which C^perp has the compact description
  { g0*x + gk*x^(3^k) + ... + g_(n-1)*x^(3^(n-1)) :
       gk,...,g_(n-1) in F and g0=lambda*(gk^(3^(n-h))) }.

Return exactly 5 ternary digits, one per normal-basis coordinate in the
displayed order.  Digits are in {0,1,2}; the all-zero word is forbidden.
No separators, sign, prefix, or omitted leading zeroes are allowed.

Give your final answer inside <answer></answer> tags as exactly that
5-digit ternary word.
Example format only: <answer>00001</answer>
Output nothing else inside the tags.
```

The answer is `<answer>21222</answer>`. `verify(inst, "21222")` returns
`(True, "ok")`; `verify(inst, "01222")` returns `(False, "the proposed
endpoint constraint is not trace-orthogonal")`. A person can solve the demo by
rotating `11211` four places right and negating its five trits.

## Difficulty presets

| Preset | `n` | `k` | Candidate words | Compact operations | Status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 2 | `3^5-1 = 242` | 18 | hand-scale illustration; hardening skips it |
| easy | 48 | 23 | `3^48-1` | 104 | shipping candidate; oracle unavailable |
| medium | 80 | 39 | `3^80-1` | 168 | reserve escalation rung |
| hard | 146 | 72 | `3^146-1` | 300 | final rung; exactly at the effort cap |

After `hard`, `escalate()` returns `cap_bound`: increasing `n` would exceed the
300-operation intended-route cap. `n` enlarges both the coordinate haystack and
the expanded dual calculation; `k` remains near half the extension degree.

## Gate results

| Gate | Measured result at shipping unless stated otherwise |
|---|---|
| G1 | pass: 12/12 planted checks and 12/12 exact norm-obstruction checks; field moduli pass exact Rabin irreducibility and normal-basis rank checks |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: 48-trit witness recovered through prose and a Markdown fence |
| G4 | pass: 0/200,000 structure-aware guesses; exact density `1/(3^48-1) = 1.25366e-23` |
| G5 | pass: exactly one valid word; 2,048 restart candidates across eight seeds; reference mean 1,711,839 operations and 0.04967 s |
| G6 | pass: five attacks each 0/8; the disclosed reference and compact route each 8/8 |
| G7 | pass: doubled `n=96` instance built and verified; space `3^96-1` |
| G8 | pass: 80/80 cyclic/non-monomial basis changes, field automorphisms, and compositions invariant; 80/80 carried witnesses valid; 20/20 unrelated keys distinct |
| G9(c) | pass: 50 JSON characters, about 13 tokens, 48 atoms, 104 intended operations |

Exact timing fields are in `selftest_report.json` and naturally vary by run.

## Oracle loop and G9 arms

No row below is a model failure: HTTP errors do not consume a scored attempt.

| Run | Preset | Seeds | Scored solved/attempts | Result |
|---|---|---|---:|---|
| bare | easy | 669273494, 82927125, 1330148028, 1048987756 | 0/0 | four HTTP 403 account-limit errors; no verdict |
| structural hint | easy | 1755713368, 2014353664, 1174589722, 382845299 | 0/0 | four HTTP 403 errors; hinted verdict unrun |
| placebo hint | easy | 988761698, 734900535, 690488180, 496025874 | 0/0 | four HTTP 403 errors; no comparison |

The numeric `hinted - placebo` placeholder is `0.0` because both denominators
are zero. No conclusion about the hint or the claimed duality intuition can be
drawn until the account limit is restored and all three arms are rerun.

## How to use it

```python
import random
import gen_1504_01581 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer("Reasoning... <answer>21222</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.random_candidate(inst, random.Random(1)) is not None
```

Once a bare oracle run returns `hardened` and `SHIPPING_DIFFICULTY` names the
held rung, emit from the repository root with:

```bash
bash scripts/emit.sh 1504.01581 20 easy
```

The module is standard-library-only and does no file I/O, network access, or
printing at import.

## Caveats

- This is deliberately Track B. A CAS or the included trace-Gram reference
  makes it easy; no average-case, cryptographic, or Track-A hardness is claimed.
- The oracle pool never ran, so local attacks alone do not establish no-tool
  model difficulty. This is the principal unresolved requirement.
- `0/200,000` samples uniformly from every nonzero normal-basis vector. It is an
  exact-language density estimate, not evidence against formula-aware guesses;
  those are probed separately by copy, sign-only, wrong-direction, off-by-one,
  and 256-restart attacks.
- The panel does not run Magma/Sage or materialize the full `n^2`-ambient dense
  nullspace. It runs the stronger practical structured coordinate adjoint and
  discloses that it succeeds 8/8.
- The embedded moduli are checked exactly for irreducibility and the normal
  elements for full rank when first used. Those one-time checks are cached, so
  wall-clock timings depend on whether field setup is warm.
- Canonicalization converts out of the displayed coordinates and therefore
  covers arbitrary normal-basis changes and field Frobenius automorphisms
  inside the embedded polynomial-field presentation. It is not a general
  equivalence test across different irreducible moduli or arbitrary
  rank-metric-code isometries.
- The useful fixed-length escalation axes are exhausted here: increasing the
  base field at fixed `n` enlarges the candidate language but does not make the
  trace-adjunction insight harder, and would mainly add modular arithmetic.
  Consequently the ladder grows `n` and the witness together, and explicitly
  parks at `cap_bound` before the 300-operation limit is exceeded.
