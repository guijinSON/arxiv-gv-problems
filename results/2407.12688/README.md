# Verified generator for arXiv:2407.12688

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | integer tuple encoding one native field element |
| Intended intuition | decomposition: rank-two linearized part plus a rank-one fifth power |
| Domain essentiality | native; `reduction_kind="none"` |
| Shipping preset | **easy** |

This module turns Hasan and Kaur, [*Some new classes of permutation polynomials and their compositional inverses*](https://arxiv.org/abs/2407.12688), into exact preimage problems. The solver receives a 24-term polynomial over `K = F_p[z]/(z^3-g)` and a target, and must return the target's unique preimage as the three coefficients of a field element. `verify` substitutes that element using exact finite-field arithmetic and never reads the planted answer.

Theorem 3.8 proves that `f_5=A_a+A_(a^2)+Tr^s` is a permutation when `a` is a nonidentity norm-one element and `gcd(s,p-1)=1`. The generator constructs such an `a`, samples the answer first, forms its target, applies Definition 4.2's invertible linearized pre- and post-compositions, and expands the result. This is a transformation of a theorem-backed instance, not a solved instance. Proposition 4.1 and Section 4.1 give the local inverse structure. No discrete surrogate replaces the paper's finite-field objects.

## Why Track B

An efficient mechanical algorithm exists: enumerate `K`, evaluate the permutation, and stop at the target. With exact evaluator preprocessing it costs `O(p^3 log s)`. On the lower-edge shipping instance (`p=103`) the measured scan inspected 222,004 candidates and used 6,438,116 base-field operations; repeated runs took 1.2–2.1 seconds (1.691092 seconds in the recorded final run). A full table has 1,092,727 entries. This is easy for code and out of reach by hand.

The compact route first recognizes that the three `p`-power terms define a rank-two linear map while the other 21 terms are the expansion of a fifth power with one-dimensional image. A left-null functional then isolates the fifth power, and one exponent inversion plus a `3x3` solve recovers the preimage. The conservative route budget is 286 exact operations. The paper's direct normal form is an easy regime because Table 1 exposes its inverse coefficients; expanding a paper-licensed linear equivalence removes that lookup while preserving the native problem.

## Worked demo

`render(make_instance(seed=0, **DIFFICULTY["demo"]))` is:

```text
Invert one value of a permutation polynomial over a cubic finite field.

Let K = F_7[z]/(z^3-2).  (The integer 2 is a cubic nonresidue modulo 7, so z^3-2 is irreducible.)
Represent c0+c1*z+c2*z^2 by [c0,c1,c2], with every coordinate in 0,...,6.  All coordinate arithmetic is modulo 7.
Addition is coordinatewise.  Multiplication is determined by z^3=2; explicitly,
  [a0,a1,a2]*[b0,b1,b2] =
  [a0*b0+2*(a1*b2+a2*b1), a0*b1+a1*b0+2*a2*b2, a0*b2+a1*b1+a2*b0] mod 7.
For u in K, u^e means repeated multiplication in this field.
The sparse polynomial h(X)=sum_e c_e*X^e is listed below.  An entry e : [c0,c1,c2] gives exponent e and coefficient c0+c1*z+c2*z^2.
Terms may be added in any order, and exponents are ordinary nonnegative integers:

  155 : [4,1,0]
  245 : [2,1,6]
  107 : [2,5,3]
  5 : [2,4,5]
  49 : [1,6,4]
  65 : [2,6,6]
  197 : [1,3,5]
  53 : [5,0,2]
  11 : [1,5,3]
  35 : [2,2,3]
  7 : [4,4,5]
  203 : [5,0,1]
  149 : [3,3,1]
  77 : [1,6,6]
  113 : [2,3,5]
  71 : [4,2,0]
  119 : [3,6,4]
  101 : [5,5,6]
  59 : [4,4,0]
  29 : [5,0,4]
  1 : [4,0,5]
  161 : [5,3,3]
  23 : [5,6,5]
  17 : [3,5,2]

It is promised that h is a permutation of K, constructed by invertible linearized pre- and post-composition; therefore every target has exactly one preimage.  A linearized polynomial has the form r0*X+r1*X^p+r2*X^(p^2) and induces an F_p-linear map of K.
Find the unique x in K such that h(x)=[0,1,6].

Give your final answer inside <answer></answer> tags as exactly three comma-separated base-field coordinates c0,c1,c2.
Coordinates are 0-indexed polynomial-basis coefficients; order matters, repetitions and zero coordinates are allowed, and each must lie in the inclusive range 0,...,6.
Example format only: <answer>3, 1, 4</answer>
Output nothing else inside the tags.
```

The answer is `<answer>4, 6, 3</answer>`. `verify(inst, [4, 6, 3])` returns `(True, "ok")`; `verify(inst, [4, 6, 4])` returns `(False, "substitution mismatch at output coordinate 0: got 6, expected 0 (full output [6,0,1])")`. A person can solve this 343-element demo by hand with the decomposition, though the modular arithmetic is intentionally nontrivial.

## Presets

The seed chooses one of `prime_span` consecutive admissible primes. For every fixed seed, each rung has a larger modulus than the preceding rung while the answer remains three coordinates.

| Preset | `n` | `prime_span` | Possible `p` | Search-space range | Status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 1 | 7 | 343 | hand-scale illustration |
| easy | 103 | 32 | 103–613 | 1,092,727–230,346,397 | **ships; bare oracle held** |
| medium | 163 | 64 | 163–1297 | 4,330,747–2,181,825,073 | locally verified, not needed by oracle |
| hard | 193 | 128 | 193–2677 | 7,189,057–19,184,262,733 | locally verified, not needed by oracle |

## Gate results

| Gate | Result | Measurement at shipping unless stated |
|---|---|---|
| G1 | pass | 12/12 planted witnesses and compact inverses verified across all presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | fenced prose round-trip and JSON round-trip |
| G4 | pass | 0/200,000 structure-aware guesses; worst-case exact probability `1/1,092,727 = 9.1514e-7` |
| G5 | pass | demo exact count 1; shipping scan 222,004 candidates, 6,438,116 operations, 1.691092 s |
| G6 | pass | five attacks, 0/8 successes each; reference scan succeeds as expected |
| G7 | pass | doubling `n` changed `p` 103→223 and space 1,092,727→11,089,567 with three answer coordinates |
| G8 | pass | 120/120 order/Frobenius/linear-equivalence checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 12 serialized characters, 3 estimated tokens, 3 atoms, 286 intended operations; shipping maximum is 4 tokens |

## Oracle loop

The script-owned bare run hardened at `easy`; all replies parsed and all proposed witnesses failed exact substitution.

| Preset | Model | Seed | `p` | Solved | Why |
|---|---|---:|---:|---:|---|
| easy | Gemini 3.8 Flash | 2001949745 | 139 | no | wrong witness |
| easy | GPT-5.6 Terra | 388714050 | 367 | no | wrong witness |
| easy | Gemini 3.8 Flash | 176784199 | 433 | no | wrong witness |

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. In this small diagnostic the rank-decomposition hint bought no measured success, so there is no evidence that merely naming the intended intuition is sufficient. One hinted response and one placebo response exhausted their response budget without an answer; this limits the strength of that conclusion but is recorded verbatim in the transcripts. The G9(c) sizes are 12 characters, 3 atoms, and 286 exact operations on the measured instance.

## Use

```python
from gen_2407_12688 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("<answer>1, 2, 3</answer>")
print(verify(inst, candidate))
```

From the repository root:

```bash
bash scripts/emit.sh 2407.12688 20 easy
```

## Caveats

This is a Track B benchmark, not a complexity-theoretic hardness claim: code can solve it by enumeration, and a CAS that recognizes the rank-one power can execute the compact route. The exact `P(guess)` assumes a uniform prior over all `p^3` field elements; it proves uniqueness density, not resistance to structural inference. Plants and random guesses both live in the same field, but generation excludes degenerate targets whose linear or nonlinear component vanishes because those form easier orbits.

The attack panel tried copying the target/sparse basis elements, ignoring the nonlinear term, coordinatewise and whole-field fifth roots, and 256 random restarts. It did not run a dedicated finite-field factorization package, Gröbner basis implementation, or general sparse tensor-decomposition package. The canonical key exactly removes term order, Frobenius relabelling, and the generated Section 4.2 linear equivalences by using the public rank decomposition; for this generated class, seeds sharing `p`, `s`, and target-orbit flags are intentionally duplicates, so modulus variation supplies the diversity.
