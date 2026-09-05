# Verified generator for arXiv:2605.11545

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | matrix certificate, represented by its Boolean rank-one factor |
| intended intuition | change of variables: recognize a dense cyclic convolution whose inverse is sparse |
| domain essentiality | licensed reduction |
| reduction | paper-licensed, Section 4.1 and Theorem 4.2 |

## What the family asks

This module instantiates the direct pseudo-moment construction in Guruswami,
Ren, and Tang, [*Strong Inapproximability for a Promise Rank Problem*](https://arxiv.org/abs/2605.11545).
The solver receives linear equations over `GF(257)` and the exact definition of
the corresponding degree-two pseudo-moment matrix subspace. It must give a
Boolean vector whose honest moment matrix is a nonzero rank-one member of that
subspace. The bit string is a succinct matrix certificate: Section 2 gives
`H_2(x)=v_2(x)v_2(x)^T`, and the empty-monomial coordinate is 1.

Generation is inverse, not solution by search. The generator samples the
Boolean factor `x` first, constructs a dense invertible cyclic operator `A`
from a finite geometric-series identity, and publishes `b=A*x`. The checker
does not read the planted answer. It validates the shape and recomputes every
equation modulo 257; Section 4.1's localizing identity then gives
`x^W f_i(x)=0` exactly for every required `W`.

## Why this is Track B

Theorem 1.2 and Theorem 4.2 are worst-case hardness results; they do **not**
prove distributional hardness for this inverse-generated specialization. A
Track A claim would therefore be unjustified. Moreover, the source equations
here are linear, so ordinary dense Gaussian elimination over `GF(257)` solves
every instance in `O(n^3)` time. At shipping `n=47`, the eight-instance panel
solved 8/8 in 143,556 exact field operations (17,944 per instance); repeated
local eight-instance panels remained under 0.01 seconds total.

The no-tool gap is between that mechanical elimination and a 95-operation
route: after recognizing the cyclic convolution and deriving its sparse
inverse, each output bit needs one field multiplication and one addition. The
paper's actually hard regime comes from arbitrary Boolean quadratic equations;
this benchmark deliberately uses the paper's completeness object while being
honest that its specialized reference algorithm is polynomial. Section 1's
diagonal-code embedding is another easy regime: rank one there is trivial to
detect, so it was not used.

## Worked demo

This is `render(make_instance(n=7, seed=0))` with no hint:

```text
Rank-one pseudo-moment matrix in a linear subspace over GF(257)

All arithmetic below is modulo the prime 257. There are 7 Boolean variables
x_0,...,x_6, so each x_j must be exactly 0 or 1. The public linear
polynomials are

    f_i(x) = sum_(j=0 to 6) A[i,j] x_j - b_i  (mod 257),

for i=0,...,6. The coefficient matrix A is given row by row below. Row
labels and variable indices are 0-based; each row has exactly 7 entries in
the order x_0,...,x_6.

0: 37 76 170 245 146 29 4
1: 4 37 76 170 245 146 29
2: 29 4 37 76 170 245 146
3: 146 29 4 37 76 170 245
4: 245 146 29 4 37 76 170
5: 170 245 146 29 4 37 76
6: 76 170 245 146 29 4 37

The right-hand side b, in row order 0,...,6, is:
117 156 189 164 47 205 23

These data define the following degree-2 pseudo-moment matrix subspace. Let V
be all subsets S of {0,...,6} with |S|<=2, including the empty set.
For one field value y_R for every subset R with |R|<=4, form the
29 by 29 matrix

    H(y)[S,T] = y_(S union T),  for S,T in V.

The subspace L consists of those H(y) satisfying, for every row i and every
subset W with |W|<=2,

    sum_(j=0 to 6) A[i,j] y_(W union {j}) - b_i y_W = 0 (mod 257).

Find a Boolean vector x whose honest moment matrix lies in L. Your submitted
bits encode that matrix succinctly: set y_R=product_(j in R) x_j (the empty
product is 1), equivalently H(y)=v_2(x)v_2(x)^T. Thus the encoded matrix is
automatically nonzero and rank one. Membership in L is equivalent here to all
displayed equations f_i(x)=0, because each localizing left side equals
(product_(j in W) x_j) f_i(x). You need not print H(y).

Output exactly 7 bits with no spaces, in x_0,...,x_6 order. Repetitions
of bit values are allowed; characters other than 0 and 1 are forbidden.

Give your final answer inside <answer></answer> tags, as the bit string.
Example: <answer>0100110</answer>
Output nothing else inside the tags.
```

The answer is `<answer>1011111</answer>`, and `verify` returns `(True, "ok")`.
Changing its first bit gives `0011111`, for which `verify` returns
`(False, "linear/localizing constraint 0 is violated")`. A person can solve
this demo on paper after finding the sparse cyclic inverse; seven modular
updates are small enough to carry out and check manually.

## Difficulty presets

| preset | variables `n` | inverse power | moment-matrix dimension | candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 1 | 29 | `C(7,w)` | hand example; not hardened |
| easy | 47 | 1 | 1,129 | `C(47,w)` | **ships; hardened** |
| medium | 63 | 1 | 2,017 | `C(63,w)` | reserve |
| hard | 65 | 2 | 2,146 | `C(65,w)` | reserve; deeper operator at nearly fixed witness length |

Escalation first raises the inverse power at fixed `n`, then raises `n` only
while the compact route remains within 300 exact operations.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified across all presets |
| G2 | drop, swap, duplicate, empty, and non-binary corruptions all rejected with 5 distinct reasons |
| G3 | prose/fence/tag round-trip parsed and verified |
| G4 | 0/200,000 exact-weight guesses; at test seed 123, `w=26`, space 12,551,759,587,422, exact density `7.9670e-14` |
| G5 | exactly one shipping solution; reference elimination 143,556 operations and 0.0070 s over the final 8-instance run |
| G6 | four attacks, 0/8 successes each; reference elimination 8/8 as expected |
| G7 | all named rungs verify, `n=94` verifies, and inverse power 2 verifies at fixed 47-bit length |
| G8 | 60/60 relabelling invariance checks and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | hinted oracle hardened; 49 serialized characters, 47 atoms, about 13 tokens, 95 intended operations |

The four failing attacks were column-correlation outlier guessing, greedy
single-bit improvement, 256 random restarts, and thirteen simple right-hand-side
ansatzes. Plants and guesses both use the uniform distribution on exactly
`n`-bit Boolean strings conditional on the Hamming weight that summing the
public equations reveals.

## Oracle loop

| preset | model | seed | solved | reason | elapsed |
|---|---|---:|---|---|---:|
| easy | `openai/gpt-5.6-terra` | 1986833058 | no | no tagged answer parsed | 67.00 s |
| easy | `x-ai/grok-4.6` | 1338295797 | no | constraint 0 violated | 272.55 s |
| easy | `google/gemini-3.1-pro-preview` | 1883551987 | no | constraint 0 violated | 36.25 s |

The script-owned verdict is `hardened` at `easy`, with no escalation.

## G9 diagnostic arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. The compliant hint only names cyclic
convolution, and it bought the oracle pool no measurable success. This suggests
that merely noticing circulant structure is insufficient; deriving and
executing the sparse inverse is the discriminating step. The exact inverse
formula itself is intentionally not in the hint: disclosing it made an earlier
diagnostic easy and would test obedience to a supplied procedure instead of
structural reasoning.

## Use

From this directory:

```python
import random
import gen_2605_11545 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer(f"Reasoning... <answer>{inst['answer']}</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 12_551_759_587_422  # C(47, 26) for seed 123
```

From the repository root, emit fresh, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2605.11545 20 easy
```

## Caveats

- This is not evidence of average-case or Track A hardness. Gaussian
  elimination solves the generated distribution quickly when tools are allowed.
- The exact density is known from invertibility. The random prior already uses
  the exact Hamming weight deducible from the public row-sum equation, but the
  0/200,000 figure still says nothing about a stronger algebraic attack.
- An automated circulant-polynomial factorization attack and general finite-field
  code-equivalence canonicalization were not implemented. The canonical key is
  invariant under equation and variable permutations but may miss duplicates
  related by arbitrary invertible row operations.
- The answer is the succinct Boolean factor, not all entries of the moment
  matrix. The checker validates the matrix through the paper's exact outer-product
  and localizing identities rather than materializing a 1,129 by 1,129 array.
- Only standard-library arithmetic is needed; `gvlib` is therefore not imported.
