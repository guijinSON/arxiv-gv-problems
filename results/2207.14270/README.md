# Skew-conjugacy locator generator (arXiv:2207.14270)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | polynomial |
| Intended intuition | invariant — replace iterative Ore LCLM arithmetic by the common norm of a full skew-conjugacy class |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

The generator is based on Gómez-Torrecillas, Lobillo, and Navarro, [*Skew differential Goppa codes and their application to McEliece cryptosystem*](https://arxiv.org/abs/2207.14270). It hands the solver a quotient field `L = GF(2^M)`, the Frobenius automorphism `sigma(u)=u^(2^delta)`, and `n=M/delta` points in one skew-conjugacy class. The points are promised left P-independent. The answer is their unique monic least common left multiple in the Ore ring `L[x;sigma]`, written as an exact sparse polynomial.

This is the paper's native algebra. Definition 3 in Section 2 fixes right roots and error locators; Proposition 15 in Section 4 constructs P-independent skew-conjugate points and identifies the locator of a complete class. There is no graph or generic CSP surrogate.

Checking is exact and cheap. `verify` parses the submitted coefficients, evaluates the Ore polynomial at every point using `N_j(b)=b sigma(b)...sigma^(j-1)(b)`, and independently checks that the skew-Vandermonde matrix has full rank. It never reads `inst["answer"]` and accepts any polynomial passing those checks.

## Why this is Track B

This family is deliberately **not** a structural-hardness claim. Ore polynomials form a Euclidean domain (Section 2), Algorithm 1 gives extended Euclidean arithmetic, and iterative least-common-left-multiple construction is polynomial time. Our exact reference implementation solves 8/8 shipping instances, averaging 0.221259 seconds, 6,268 finite-field multiplications, and 1,393,359 inner multiply-loop steps.

The compact route is Proposition 15: a full P-independent subset of one conjugacy class has locator `x^n - N(a)`. In characteristic two this is `x^n + N(a)`. Computing the orbit norm takes `n` multiplications and `n-1` Frobenius applications—15 high-level exact operations at shipping `n=8`—if the invariant is recognized. Without it, the solver must reproduce the iterative Ore-LCLM calculation. The generator knows the norm by composition while constructing the class; it does not solve the generated LCLM instance.

The easy regimes are therefore explicit rather than hidden: a CAS or the included reference algorithm solves every instance quickly, and Proposition 15 itself is an even shorter formula. This benchmark measures whether a no-tool solver can recognize and carry out that compression, not computational intractability.

## Worked demo

The `demo` preset with seed 0 renders the following complete instance:

```text
Compute an exact locator polynomial in a skew-polynomial ring.

Let L = GF(2^4) = GF(2)[z]/(P(z)), where P is the monic irreducible binary polynomial encoded by 0x13. Bit i of this integer is the coefficient of z^i. Field addition is bitwise XOR; field multiplication is carryless polynomial multiplication reduced modulo P. Every field element below is exactly 1 lowercase hexadecimal digits in this polynomial basis (no 0x prefix).

Define sigma(u)=u^(2^2). In the Ore ring L[x;sigma], coefficients are written on the left and x*u=sigma(u)*x. For b in L, define N_0(b)=1 and N_j(b)=b*sigma(b)*...*sigma^(j-1)(b). The right evaluation of f(x)=sum_j f_j*x^j at b is f[b]=sum_j f_j*N_j(b). Thus b is a right root exactly when f[b]=0.

The following 2 nonzero points are promised to be left P-independent: equivalently, the square matrix with entry N_j(b_i) in row j=0,...,n-1 and column i=1,...,n is nonsingular over L. They are also promised to lie in one sigma-conjugacy class, where b and b' are conjugate when b'=sigma(c)*b*c^(-1) for some nonzero c.

Points (their order has no significance):
  1: 5
  2: e

Find the unique monic Ore polynomial of degree exactly n having every listed point as a right root. A monic polynomial has coefficient 1 on x^n.

Represent the polynomial sparsely as a JSON list of its nonzero [exponent,coefficient] terms, in strictly increasing exponent order. Exponents are integers from 0 through 2; coefficients are exactly 1-digit lowercase hexadecimal strings. Omit zero coefficients; include the final term [2,"1"].

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the required syntax: <answer>[[0,"1"],[2,"1"]]</answer>
Output nothing else inside the tags.
```

The answer is `[[0,"7"],[2,"1"]]`, representing `x^2+7`. The demo is genuinely hand-solvable using the 16-element field table:

```python
>>> inst = make_instance(seed=0, **DIFFICULTY["demo"])
>>> verify(inst, [[0, "7"], [2, "1"]])
(True, 'ok')
>>> verify(inst, [[0, "7"]])
(False, 'leading term must be monic of degree n')
```

## Difficulty presets

| Preset | Points `n` | `delta` | Field bits `M` | Render chars (seed 0) | Status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 2 | 4 | 1,743 | hand example; never ships |
| easy | 8 | 32 | 256 | 2,546 | **shipping; bare oracle held** |
| medium | 12 | 32 | 384 | 3,345 | available; oracle did not need to reach it |
| hard | 16 | 32 | 512 | 4,399 | available; oracle did not need to reach it |

No named preset was rejected. The hardening loop stopped at `easy` because all three bare attempts failed there.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified across all presets |
| G2 | pass | 6/6 corruptions rejected with 6 distinct reasons |
| G3 | pass | realistic prose/fence/tag response round-tripped |
| G4 | pass | 0/200,000 structure-aware guesses; 32-bit candidate space (`2^32-1` nonzero fixed-field constants) |
| G5 | pass | shipping sampled density 0/200,000; demo exact solution count 1; 256-restart baseline 0.002585 s average |
| G6 | pass | four attacks each 0/8; polynomial-time reference solver 8/8 |
| G7 | pass | doubled `n=16` builds in 1.970447 s and verifies; field size grows 256 to 512 bits |
| G8 | pass | 140/140 symmetry/composition checks, 140/140 carried certificates valid, 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle still hardened; 143 answer chars, 36 estimated tokens, 4 atomic elements, 15 intended operations |

The four failing attacks were: smallest-encoding point as an outlier, ordinary commutative product as a greedy shortcut, a two-factor truncated norm as an in-context hand ansatz, and 256 random restarts drawn uniformly from the correct fixed field. Basis randomization and point shuffling remove positional signatures; the planted norm is uniform in `GF(2^32)*`.

## Bare oracle loop

| Model | Preset | Seed | Solved | Verification result |
|---|---|---:|---|---|
| Gemini 3.1 Pro Preview | easy | 939388178 | no | proposed polynomial fails at point 1 |
| GPT-5.6 Terra | easy | 189511569 | no | proposed polynomial fails at point 1 |
| Claude Sonnet 5 | easy | 1020217157 | no | proposed polynomial fails at point 1 |

All replies containing answers parsed. Two models chose the tempting but false universal constant `1`; the common relative norm is not generally 1 when the fixed field is `GF(2^32)`.

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. The hint correctly names the Proposition 15 norm identity, but it bought no observed solves: two hinted models still substituted norm 1, while one exhausted its response budget. That means the observed difficulty includes executing exact 256-bit field arithmetic after the structural insight, not just discovering the invariant. The answer is 143 characters (about 36 tokens), and the intended theorem route has 15 high-level field operations.

## Use

```python
from gen_2207_14270 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>[[0,"' + '0' * 63 + '1"],[8,"' + '0' * 63 + '1"]]</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 2207.14270 20 easy
```

## Caveats

- This is Track B: any environment with a CAS or ordinary Python can solve it quickly. It must not be cited as evidence that skew-Goppa decoding, Ore LCLM, or this generated distribution is computationally hard.
- G4 samples the strongest simple post-insight prior: a uniform nonzero constant from the 32-bit fixed field in a binomial `x^n+c`. Its 0/200,000 observation is compatible with the exact one-in-`2^32-1` density, but does not model nonuniform mathematical guesses such as `c=1`; those are covered separately by G6 and the oracle transcripts.
- The 15-operation intended count treats one finite-field multiplication and one Frobenius application as high-level exact operations. Their bit-level execution is much larger; the reference solver records 1,393,359 inner multiply-loop steps. The unchanged hinted failure shows this arithmetic burden is material, so the family is not a pure test of theorem recognition.
- The panel did not try external computer-algebra systems, optimized normal-basis arithmetic, or a precomputed finite-field table. Those would be expected to succeed and are represented by the successful exact reference algorithm.
- `canonical_key` intentionally identifies every reordered, globally conjugated, or Frobenius-transformed complete basis from the same class, because Proposition 15 gives all of them the same locator. It keys on the independently recomputed common norm, not on the seed or rendered text.
- The hard-coded quotient polynomials are checked by exact Rabin irreducibility tests in selftest. Missing or altered constants will fail before a trust claim is made.
- The implementation uses only the Python standard library; `gvlib` has no finite-field or Ore-polynomial primitive needed by this family.
