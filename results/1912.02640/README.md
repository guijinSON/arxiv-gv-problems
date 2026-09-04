# Verified generator for arXiv:1912.02640

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | integer tuple encoding two native field elements |
| Intended intuition | change of variables |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Li, Li, Helleseth, and Qu, [*Cryptographically Strong Permutations from the Butterfly Structure*](https://arxiv.org/abs/1912.02640).  Section II defines the closed butterfly over `GF(2^n)` and Theorem 1 gives its exact good-coefficient condition.  An instance supplies an irreducible binary modulus and the normalized invariant `t = phi2/phi4`; the solver must return native field elements `alpha,beta` satisfying the theorem's two identities.  `verify` recomputes those identities with carryless polynomial multiplication, so checking is exact and cheap.

Generation never solves the emitted equations.  It samples `s` first and composes

`t=s^2+s`, `d=t+1`, `alpha=s^2/d`, and `beta=d^(-3)`.

For odd `n`, `t` has trace zero and `d` is nonzero.  Direct substitution gives `phi2=t*phi4`, `phi2^2=phi1*phi4`, and `phi4!=0`; replacing `s` by `s+1` gives the second witness.  This is a composition-of-identities construction, and `verify` never reads `inst["answer"]`.

## Why this is Track B

This is not a computational-hardness claim.  Given `t`, the Artin–Schreier half-trace finds an `s` with `s^2+s=t`, after which the displayed formulas recover a witness.  With schoolbook binary-field arithmetic this costs `O(n^3)` bit operations.  At the shipping preset, the measured mean was 111 field operations, 4,285 low-level bit-loop operations, and 0.000289 seconds over eight successful reference runs.

That algorithm is precisely why Track A would be false.  Section V gives a second warning: experiments at `n=3,5` suggest the paper's butterflies are affine equivalent to a Gold function.  The family also excludes the trivial `alpha=beta=1`, whose normalized invariant is zero.  The benchmark claim is only that carrying out dozens of 31-bit carryless products and modular reductions without a sandbox is unreliable, while recognizing the substitution compresses the route below the 300-operation cap.

## Worked demo (`n=3`, seed 0)

The complete rendered mathematical instance is:

```text
Recover coefficients of a cryptographic closed butterfly

Work in the binary finite field F = GF(2^3) represented as F_2[X]/(P).
Field elements are decimal integers from 0 through 7.  Integer bit j is
the coefficient of X^j.  The irreducible modulus is the integer

    P = 11

(its bit n is the leading X^n term).  Addition in F is bitwise XOR.  To
multiply, multiply the corresponding binary polynomials without carries and
take the remainder modulo P.  Every product and power below is in F.

For coefficients alpha,beta in F, the paper's i=1 closed butterfly is

    R(x,y) = (x + alpha*y)^3 + beta*y^3,
    V(x,y) = (R(x,y), R(y,x)).

Define its three coefficient expressions

    phi1 = alpha^6 + alpha*beta + beta^2 + 1,
    phi2 = alpha^6 + alpha^5 + alpha^4 + alpha^2 + alpha
           + alpha^2*beta + beta^2 + 1,
    phi4 = alpha^6 + alpha^4 + alpha^2 + beta^2 + 1.

The public normalized invariant is

    t = 2.

Find two decimal integers [alpha,beta] such that, in F:

  1. 0 < alpha,beta < 8, alpha != 1, and alpha != beta;
  2. phi4 != 0;
  3. phi2 = t*phi4; and
  4. phi2^2 = phi1*phi4.

These are exactly the normalized i=1 coefficient identities used in Theorem 1
of the paper; a valid pair defines the displayed closed butterfly.  There may
be more than one accepted pair, and any pair satisfying every condition is a
valid witness.  All bounds are inclusive where written, and the list order is
[alpha,beta], not [beta,alpha].

Give your final answer inside <answer></answer> tags as one JSON list of two decimal integers.
Example: <answer>[2, 3]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>[4, 7]</answer>` and `verify(inst,[4,7])` returns `(True,"ok")`.  Swapping it gives `verify(inst,[7,4]) == (False,"the normalized identity phi2=t*phi4 fails")`.  A person can solve this demo on paper by tabulating its 36 structurally legal pairs; `enumerate_all` confirms exactly two witnesses.

## Difficulty presets

| Preset | Extension degree `n` | Role / outcome |
|---|---:|---|
| demo | 3 | hand-scale example; not hardened |
| easy | 31 | **shipping**; bare oracle panel held 0/3 |
| medium | 47 | available escalation; not reached |
| hard | 61 | available escalation; not reached |

Larger `n` increases both the roughly `2^(2n)` certificate language and the cost of exact polynomial-basis arithmetic.  The G7 build used the next valid odd degree beyond twice shipping size, `n=63`, and its planted witness verified.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed planted witnesses; JSON round-trip |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose/fence/tag round-trip; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 structure-aware samples |
| G5 | pass | shipping observed fraction 0; 4,096-restart baseline failed in 0.0825 s; demo has 2 exact answers |
| G6 | pass | four attacks each 0/8; reference half-trace 8/8 as expected |
| G7 | pass | `n=63` built and verified |
| G8 | pass | 80/80 Frobenius invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle held; 23 chars, 23-token conservative upper bound, 2 elements, 111 intended field operations |

The four failing G6 attacks were extreme-Hamming-weight coefficient guesses, lexicographically small greedy guesses, 512 uniform legal restarts, and the in-context ansatz using `t`, `t+1`, `t^2`, and `t^2+1`.  The successful half-trace reference algorithm is reported separately, as Track B requires.

## Oracle loop

| Preset | Model | Seed | Solved | Recorded reason |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 79076252 | no | parsed pair failed `phi2=t*phi4` |
| easy | Claude Sonnet 5 | 970053 | no | exhausted 32k completion budget with an empty body |
| easy | Gemini 3.1 Pro Preview | 312626404 | no | parsed pair failed `phi2=t*phi4` |

The official verdict is `hardened` at `n=31` with zero escalations.  A prior error-only run repeatedly timed out on Grok and was discarded because errors are not hardness evidence; the retained run uses recorded master seed 6 and three distinct vendors.

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted - placebo = 0.0`.  The hint therefore bought no observed oracle success.  This supports the narrow conclusion that exact no-tool field arithmetic remains a barrier, but it does **not** show that the pool was specifically sensitive to the claimed change-of-variables intuition.  The shipping answer measured 23 characters, a conservative upper bound of 23 tokens (one per character), 2 atomic elements, and 111 field operations on the intended route.

## Use

```python
from gen_1912_02640 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
answer = parse_answer("<answer>[123, 456]</answer>")
print(verify(inst, answer))
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 1912.02640
```

## Caveats

- The half-trace reference solver makes the family trivial with a finite-field implementation; this is deliberately Track B and must never be cited as cryptographic or average-case hardness.
- The 0/200,000 guess result concerns the declared uniform prior on distinct nonzero coefficient pairs with `alpha!=1`.  It does not model a solver that has derived the trace-zero parameterization; mathematically there are two accepted pairs for the generated nonzero `t`.
- Claude returned empty length-limited bodies in all three arms, and placebo Gemini did so as well.  Those are valid outcomes under the supplied harness but weaker evidence than the parsed, incorrect Terra and bare/hinted Gemini witnesses.
- The panel did not run a Gröbner-basis package, a SAT encoding of field bits, or learned cross-instance attacks.  Those would be expected to succeed with tools and would not contradict Track B.
- `canonical_key` normalizes every Frobenius automorphism in the fixed polynomial presentation.  It does not solve isomorphisms to alternative irreducible-polynomial presentations; the generator avoids that ambiguity by deterministically using the first irreducible modulus for each `n`.
