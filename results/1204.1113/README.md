# Verified generator for arXiv:1204.1113

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity / root search |
| Certificate | two-integer encoding of a prime-field root |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

The module implements root finding for a univariate sparse polynomial over
`F_p`, the native object of Bi, Cheng, and Rojas,
[“Sub-Linear Root Detection, and New Hardness Results, for Sparse Polynomials
Over Finite Fields”](https://arxiv.org/abs/1204.1113). The solver receives the
prime and all nonzero coefficient/exponent pairs and must return the unique
nonzero root. Verification is exact substitution modulo `p`.

## Why it can be trusted

Generation is a certificate-carrying transformation, not a solve. It first
builds

`g(y) = (y-3)(H(y)^2+1)`

over a fixed Mersenne prime `p = 3 mod 4`. Since `-1` is not a square, the
second factor never vanishes and `3` is the unique root. A random unit `h`
modulo `p-1`, random exponent translation, random coefficient scale, and term
shuffle produce `f(x)`, while Section 3.1's invertible power substitution
carries the root to `x = 3^(h^-1) mod p`. The checker independently evaluates
the rendered sparse polynomial and never reads `inst["answer"]`.

## Why Track B, not Track A

Theorem 1.4 proves only worst-case NP-hardness when the term count grows; it
does not prove this planted distribution hard. These instances have a disclosed
efficient solver. Because `H` has zero next-to-leading coefficient, the two
highest transformed coefficients obey `c_low = -3*c_high`. A coefficient index
finds that unique pair in linear time; their exponent difference is `h`.
Extended Euclid and binary powering then recover the root. Complexity is
`O(n + log p)` exact operations. At shipping `n=48`, `p=2^31-1`, it solved 8/8
in a median 161 counted operations and about 0.000014 seconds.

The compact mathematical route is the same change of variables, but executing
it unaided still requires locating a relation among 48 shuffled terms, a
31-bit modular inverse, and exact modular powering. The structural-hint arm
named the relation and all three vendors still failed. The easy regimes are
stated rather than hidden: Section 1.1 says deciding whether an element is a
`d`-th power is polynomial in `log d + log q`, so a binomial family was
rejected; Theorem 1.1 gives a deterministic fixed-`t` root detector in
`4^t(t log q)^O(1) + t^(1/2+o(1))q^((t-2)/(t-1)+o(1))` bit operations. This
generator makes no Track A claim from either theorem.

## Worked demo

The demo is hand-scale: the reference route needs 33 counted operations, and a
person can alternatively test the 126 nonzero residues. For seed 0 the complete
rendered instance is:

```text
SPARSE POLYNOMIAL ROOT OVER A PRIME FIELD

Let p=127. Arithmetic is in the prime field F_p: two integers denote
the same field element exactly when they have the same remainder modulo p.

The polynomial is
    f(x) = sum c*x^a over all pairs (c,a) below, computed modulo p.
All coefficients and exponents are ordinary decimal integers. Exponentiation
means field exponentiation; in particular x^0=1, including when x=0. The pair
order is irrelevant, exponents lie in 0..p-2, and there are exactly n=8
nonzero terms. The polynomial has exactly one nonzero root in F_p (zero is
irrelevant and may or may not be a root).

(coefficient, exponent) pairs:
  (98, 102)   (87, 113)   (91, 42)   (21, 124)
  (60, 20)   (92, 9)   (79, 31)   (81, 53)

Find the unique nonzero integer root x with 1 <= x < p. Encode it in exactly two
base-B limbs [high, low], where B=16, so that
x = high*B + low and 0 <= high,low < B. The brackets are omitted in the
answer block.

Give your final answer inside <answer></answer> tags, as two comma-separated
decimal integers high, low.
Example format: <answer>0, 1</answer>
Output nothing else inside the tags.
```

Here `(98,102)` and `(87,113)` are the unique minus-three coefficient pair,
so `h = 102-113 = 115 mod 126`, `h^-1 = 103 mod 126`, and
`3^103 = 101 mod 127`. Thus the answer is `<answer>6, 5</answer>` because
`101 = 6*16+5`.

```python
>>> verify(demo, [6, 5])
(True, 'ok')
>>> verify(demo, [6])
(False, 'too few limbs')
```

## Difficulty presets

| Preset | Terms `n` | Prime | Reference ops, seed 0 | Status |
|---|---:|---:|---:|---|
| demo | 8 | `2^7-1` | 33 | hand-solvable illustration |
| easy | 48 | `2^31-1` | 164 | **ships; bare and hinted hardened** |
| medium | 72 | `2^61-1` | 269 | available, not needed |
| hard | 96 | `2^127-1` | 478 | available, not needed |

No named preset was rejected. The first tested rung held, so the harness did not
escalate to a larger arithmetic/transcription burden.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset–seed plants verify; 12/12 JSON round trips |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | realistic fenced two-limb response round-trips |
| G4 | pass | 0/200,000 uniform nonzero field guesses; space 2,147,483,646 |
| G5 | pass | shipping density 0/200,000; exactly one root by construction; 4,096-restart baseline took 0.396414 s |
| G6 | pass | five attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | pass | doubled `n=96` verifies; reference work grows from 161 to 256 ops |
| G8 | pass | 100/100 symmetry keys and carried witnesses; 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle 0/3; 11 chars, 3 estimated tokens, 2 elements, 161 ops |

The failing attacks were coefficient-magnitude outlier selection, the first
input-pair greedy rule, the two largest coefficients, six small-root ansatzes,
and 256 uniform random restarts. The construction-aware algorithm is reported
separately because Track B expects it to succeed.

## Oracle loop

| Model | Preset | Seed | Solved | Exact outcome |
|---|---|---:|---|---|
| Grok 4.6 | easy | 1844121165 | no | parsed; encoded value was not a root |
| GPT-5.6 Terra | easy | 827512289 | no | parsed; encoded value was not a root |
| Claude Sonnet 5 | easy | 1654546044 | no | empty length-limited response after 32k completion tokens |

The script-owned bare verdict is **hardened** with zero escalations. Full
replies, timings, and provider metadata are preserved in
`llm_loop_transcript.jsonl` and `.meta.json`.

## G9 arms

| Arm | Solved / attempts | Result |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; all three parsed wrong roots |
| placebo hint | 0/3 | two parsed wrong roots, one length-limited empty response |

Hinted minus placebo is **0.0**. In this three-call diagnostic, explicitly
naming the coefficient relation bought no measurable success. This supports
the narrower conclusion that exact execution, not only discovery of the change
of variables, is difficult in context; three calls are too few for a causal
claim. The shipping answer has 11 characters, about 3 tokens, 2 atomic
elements, and the intended route has 161 counted exact operations.

## Use

```python
from gen_1204_1113 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer("<answer>123, 456</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit deterministic samples with:

```bash
bash scripts/emit.sh 1204.1113 20
```

The module uses only the Python standard library; `gvlib` is unnecessary for
prime-field substitution.

## Caveats

- The generated distribution is efficiently solvable by the disclosed
  coefficient-indexed algorithm. It is not average-case evidence for Theorem
  1.4 and must not be relabelled Track A.
- The exact one-root claim relies on the four fixed primes being Mersenne primes
  congruent to 3 modulo 4, making `-1` a quadratic nonresidue. Arbitrary
  `prime_bits` values are deliberately rejected.
- `P(guess)` samples uniformly from every nonzero field element, already
  enforcing both limb bounds. It measures blind guessing only and says nothing
  about a prior informed by the minus-three relation.
- No external CAS, generic finite-field factorer, exact-SVP implementation, or
  paper-wide Theorem 1.1 implementation was run. The distribution-specific
  linear-time reference solver is stronger here and succeeds 8/8.
- The canonical key handles term order, nonzero coefficient scaling, unit power
  relabelling, exponent translation, and their composition. It does not decide
  every possible functional equivalence of polynomials on `F_p^*`.
- One bare and one placebo oracle response exhausted the 32k completion-token
  budget without emitting a witness; the harness records these transparently
  as length-limited failures. The other seven relevant arm responses parsed,
  and all seven were rejected by exact substitution.
