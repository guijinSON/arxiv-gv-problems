# Projective subspace--line witnesses from arXiv:2512.24689

| profile field | value |
|---|---|
| track | **B** — no-tool compression |
| native domain | geometry |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | polynomial |
| intended intuition | invariant: recognize a cyclically shifted, scaled power basis and its defining-polynomial relation |
| domain essentiality | native |
| reduction | none |

## What the family asks

[Csajbók et al., *Small 3-fold blocking sets in PG(2,p^n)*](https://arxiv.org/abs/2512.24689) constructs three pairwise disjoint linear Rédei-type blocking sets. Section 2.2 represents each blocking set by an `(h+1)`-dimensional subspace of `GF(q^h)^3`; Section 4.1 cycles three such subspaces with `(x:y:z) -> (z:x:y)`.

An instance gives bases for those three subspaces over `GF(2)`, one projective line for each, and the exact line evaluation of every basis row. The solver must return one nonzero binary polynomial whose coefficient vector, used in every basis, gives a nonzero point on all three marked lines. Verification recomputes the three finite-field linear combinations and line incidences exactly. The task is not to rediscover the blocking sets: they are built by the paper's construction and are part of the instance.

## Why Track B is honest

The family is not claimed hard in a complexity-theoretic sense. Dense binary Gaussian nullspace elimination solves it in `O(n^3)` bit operations. At the shipping preset the reference implementation solved 8/8 instances, averaging **118,592.375 counted bit operations and 0.00147 s**. This successful algorithm is reported separately from the failing attacks.

The compressed route uses the invariant planted by construction. The displayed line-evaluation columns are a scaled cyclic ordering of `1, alpha, ..., alpha^n`; their unique binary dependence is the defining polynomial `m(alpha)=0`. Locating the cyclic break and rotating the displayed modulus relation takes at most **66 exact field operations** at shipping size. Without seeing this structure, a no-tool solver must carry out the dense elimination.

The paper also identifies regimes that would make a direct construction benchmark uninformative. Section 4.1 dispatches `h=2` with a partition into Baer subplanes, while Section 2.1 gives especially small line-union constructions in small characteristic. This module uses `q=2`, `h=n>=4`, Theorem 4.1, and the `h>=4` functional construction of Proposition 4.4. For `q=2`, the final functional coefficient is fixed directly from `1/(alpha+1)`; no generated witness is found by solving its generated instance.

## Worked demo (`n=4`, seed 7)

This smallest instance is hand-solvable: XORing the first three `S` values gives zero in every panel, identifying `11100`. The complete rendered statement is:

```text
PROJECTIVE SUBSPACE--LINE INTERSECTION CERTIFICATE

Let F = GF(2)[X]/(m(X)), where m(X) = X^4 + X + 1.
Its bit-polynomial integer is 0x13 and deg(m)=4.
A hexadecimal field element encodes the coefficients of 1,X,...,X^(n-1) in its bits.
Field addition is bitwise XOR.  Field multiplication is carryless polynomial multiplication
followed by reduction modulo m(X).  All arithmetic below is exact in F.

A projective point of PG(2,F) is a nonzero triple (x,y,z), up to multiplication
by a nonzero field element.  A line [a,b,c] contains it exactly when
a*x + b*y + c*z = 0 in F.

Each panel gives an F_2-basis b_0,...,b_n of one of three (n+1)-dimensional
F_2-subspaces U of F^3.  Such a U induces the linear blocking set
L_U = {<u>_F : u in U and u != 0}.  The three underlying blocking sets are
pairwise disjoint Redei-type sets from the construction; together they form
a 3-fold blocking set.  The row S is an audit value equal to the exact line
evaluation a*x+b*y+c*z of that row.

Find one nonzero binary coordinate polynomial C(T)=c_0+...+c_4T^4.
Use the SAME 5 coefficients in all three panels.  For every panel,
the vector sum c_0*b_0 XOR ... XOR c_n*b_n must be nonzero and lie on
that panel's line.  Coefficients are in GF(2), and row indexing is 0-based.

PANEL 0 (blocking-set component 0):
line = [0x3, 0x7, 0xa]
row : X-coordinate  Y-coordinate  Z-coordinate  | S
  0 : 0x4 0x8 0x8 | 0xe
  1 : 0xc 0x3 0x9 | 0xb
  2 : 0x8 0x8 0x7 | 0x5
  3 : 0x1 0x6 0xa | 0xa
  4 : 0x2 0xf 0x1 | 0x7

PANEL 1 (blocking-set component 1):
line = [0x5, 0xc, 0xa]
row : X-coordinate  Y-coordinate  Z-coordinate  | S
  0 : 0x3 0x1 0x3 | 0xe
  1 : 0x8 0x8 0x8 | 0xb
  2 : 0xf 0xf 0xd | 0x5
  3 : 0x5 0x7 0x1 | 0xa
  4 : 0xe 0xc 0xd | 0x7

PANEL 2 (blocking-set component 2):
line = [0xf, 0x9, 0xe]
row : X-coordinate  Y-coordinate  Z-coordinate  | S
  0 : 0x7 0xf 0x0 | 0x5
  1 : 0x3 0xf 0x2 | 0x3
  2 : 0x0 0xf 0xb | 0x6
  3 : 0x0 0xf 0x6 | 0xc
  4 : 0xe 0x0 0x1 | 0xb

Encode C by the coefficient word c_0c_1...c_n (constant coefficient first).
It must contain exactly 5 characters, each 0 or 1, and may not be all zero.
Give your final answer inside <answer></answer> tags as a JSON object with
exactly the key "coefficients".  Example: <answer>{"coefficients":"10100"}</answer>
Output nothing else inside the tags.
```

The planted answer is `{"coefficients":"11100"}` and `verify` returns `(True, "ok")`. Dropping its final bit gives `{"coefficients":"1110"}` and returns `(False, "coefficient word is too short")`.

## Difficulty presets

| preset | n | answer bits | candidate space | status |
|---|---:|---:|---:|---|
| demo | 4 | 5 | 31 | hand-scale illustration |
| easy | 31 | 32 | 4,294,967,295 | bare oracle solved 1/3; not shipped |
| **medium** | **61** | **62** | **4,611,686,018,427,387,903** | **ships; bare oracle solved 0/3** |
| hard | 127 | 128 | `2^128-1` | available, not needed by hardening loop |

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified across all presets |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | realistic tagged/prose response round-tripped; garbage returned `None` |
| G4 | 0 hits in 200,000 structure-aware uniform nonzero polynomial samples |
| G5 | exactly 1 valid shipping answer; exact density `2.168404344971009e-19`; demo count 1/31 |
| G6 | four attacks each 0/8; reference Gaussian elimination 8/8 |
| G7 | doubled `n=122` instance built and verified |
| G8 | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 81 characters, 15 estimated tokens, 62 atomic elements, 66 intended operations |

## Oracle loop

| preset | seed | model | result | verifier reason |
|---|---:|---|---|---|
| easy | 1406649440 | GPT-5.6 Terra | failed | panel 0 combination not on line |
| easy | 843298787 | Gemini 3.8 Flash | **solved** | ok |
| easy | 1569191655 | Gemini 3.8 Flash | failed | panel 0 combination not on line |
| medium | 1129731644 | GPT-5.6 Terra | failed | panel 0 combination not on line |
| medium | 671581268 | Gemini 3.8 Flash | failed | panel 0 combination not on line |
| medium | 1811425555 | GPT-5.6 Terra | failed | panel 0 combination not on line |

The script-owned verdict is `hardened` at `medium` after one escalation.

## G9 three-arm diagnostic

| arm at n=61 | solved / attempts |
|---|---:|
| bare | 0 / 3 |
| structural hint | 0 / 3 |
| placebo hint | 0 / 3 |

`hinted - placebo = 0.0`. The structural hint bought no observed success in this small sample. That is weak evidence that merely naming the power-basis invariant is insufficient: exact recognition of the cyclic break remains part of the task. These arms are diagnostic, not gates.

## Use

```python
import gen_2512_24689 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=123)
candidate = g.parse_answer('<answer>{"coefficients":"..."}</answer>')
ok, reason = g.verify(inst, candidate)
```

From the repository root, emit fresh distinct shipping instances with:

```bash
bash scripts/emit.sh 2512.24689 20 medium
```

## Caveats

- The task is deliberately Track B. An implementation with bitsets solves shipping instances in milliseconds; the benchmark measures whether a no-tool solver sees and executes the shorter invariant route, not computational intractability.
- `P(guess)` is under the declared uniform prior on all nonzero length-62 binary coefficient words. It does not model a solver that recognizes a nullspace problem or exploits the displayed audit values.
- The audit values make exact checking transparent and keep the compact route under the no-tool cap. Consequently this family tests a projective incidence certificate inside the paper's constructed blocking sets, not the harder open problem of minimizing or classifying blocking sets.
- The adversary panel tests a per-row Hamming outlier, greedy XOR descent, 256 random restarts, and direct copying of the unshifted modulus. It does not test every sparse-linear-algebra implementation; Gaussian elimination is already reported as the successful reference algorithm.
- `canonical_key` handles common basis swaps/shears, ambient projectivities, Frobenius automorphisms, panel permutations, and orientation reversal. It does not canonicalize across different irreducible-polynomial presentations of the same abstract field; the generator uses one deterministic presentation for each `n`, so that symmetry is not produced by this family.
