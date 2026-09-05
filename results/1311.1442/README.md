# Monoid-knapsack witness generator for arXiv:1311.1442

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `number_theory` |
| Object regime | `finite_field` |
| Computational core | `subset_sum` (multiplicative) |
| Certificate | `integer_tuple`: 16 sorted carrier indices |
| Intended intuition | `search pruning`: preserve constant weight and match partial products |
| Domain essentiality | `native`; no reduction |

## Problem and trust model

This implements Problem 1 and the integer specialization in §2 of Micheli and
Schiavina, [*A general construction for monoid-based knapsack protocols*](https://arxiv.org/abs/1311.1442).
The solver receives nonzero residues `y[i]`, a prime modulus `p`, a ciphertext
`c`, and a required weight `w`; it must return the unique `w` indices whose
product is `c mod p`. Verification performs only shape checks and exact modular
multiplication.

Generation is inverse, not search: it samples the support first, samples distinct
hidden prime carriers, chooses an invertible exponent, and encrypts. The §2
injectivity proposition proves uniqueness because the carriers are distinct
primes, their complete product is below `p`, and the exponent is invertible
modulo `p-1`. Plants and decoys use the same distribution; support membership is
sampled independently of every carrier.

## Why Track A, and where the claim stops

The paper does **not** prove NP-hardness or give a reduction for its public
distribution. It explicitly treats public inversion as the cryptographic hard
problem. This module therefore makes the narrower empirical Track A claim: no
tested efficient method solves this generated regime. Shipping uses `n=64`,
`w=16`, random hidden 18-bit prime carriers, and the 2048-bit safe prime from
[RFC 3526 group 14](https://www.rfc-editor.org/rfc/rfc3526#section-3). The carrier
product is at most 1152 bits, leaving at least 896 bits of no-wrap headroom.

Two easy regimes from the paper are deliberately excluded. Remark 2.5 warns
that `p` close to the carrier product leaks the bare carriers and enables a
discrete-log reduction. Section 3.3 gives a linear-time attack when carrier
orders are pairwise coprime. With the safe prime `p=2q+1`, every shipping carrier
has order `q` or `2q`, so all orders share the same 2047-bit prime factor; exact
order-exception checks passed 8/8. Section 3.2 licenses constant-weight messages;
weight 16 avoids the very short-weight case while keeping the witness writable.

The strongest implemented direct attack is constant-weight meet-in-the-middle.
Its bounded run examined 115,968 states across eight instances in 28.30 seconds
and solved none. Even the central 8+8 split needs `2*C(32,8)=21,036,600` product
states, and a complete attack must cover the other split weights too.

## Worked demo

The `demo` preset at seed 0 renders the following hand-scale instance (the
identity exponent is intentional only on this rung):

```text
Multiplicative monoid-knapsack inversion
p = 2305843009213693951
ciphertext c = 104017
y[0] = 41
y[1] = 37
y[2] = 43
y[3] = 47
y[4] = 59
y[5] = 53
Return exactly 3 distinct zero-based indices in increasing order.
```

The answer is `<answer>[0, 2, 4]</answer>` because
`41*43*59 = 104017`. `verify(inst, [0,2,4])` returns `(True, "ok")`;
`verify(inst, [0,2])` returns `(False, "wrong length: expected 3 indices")`.
A person can solve this demo by ordinary factor matching.

## Difficulty presets

| Preset | `n` | `w` | Carrier bits | Modulus bits | Search space | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 6 | 3 | 6 | 61 | 20 | hand example |
| easy | 64 | 16 | 18 | 2048 | 488,526,937,079,580 | **ships; oracle held** |
| medium | 80 | 16 | 20 | 2048 | 26,958,221,130,508,525 | reserve |
| hard | 96 | 16 | 20 | 2048 | 662,252,084,388,541,314 | reserve |

`escalate()` increases the carrier count and range while keeping the answer at
16 indices, moving to RFC 3526 group 15 when 3072 modulus bits are required.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose + fenced JSON round-trip; answer JSON-native |
| G4 | pass | 0/200,000 uniform weight-16 guesses; exact density `1/C(64,16) = 2.047e-15` |
| G5 | pass | one solution by injectivity; baseline 115,968 nodes / 28.30 s |
| G6 | pass | five attacks, each 0/8; subgroup attack inapplicable on 8/8 |
| G7 | pass | doubled `n=128` verifies; answer remains 16 atoms |
| G8 | pass | 60/60 relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | pass | 62 chars, 33 token-like units, 16 atoms, 16 final verification multiplications |

The five G6 attacks are public-bitcount outlier selection, target-bit-similarity
greedy selection, 256 constant-weight random restarts, the paper’s coprime-order
subgroup attack, and bounded constant-weight meet-in-the-middle.

## Oracle hardening and G9 diagnostics

| Arm | Model | Seed | Result |
|---|---|---:|---|
| bare | OpenAI Terra | 1126478586 | parsed; wrong modular product |
| bare | Gemini 3.1 Pro | 2083474571 | parsed; wrong modular product |
| bare | Claude Sonnet 5 | 120101924 | parsed; wrong modular product |
| structural | Gemini 3.1 Pro | 926489620 | parsed; wrong modular product |
| structural | OpenAI Terra | 697233323 | parsed; wrong modular product |
| structural | Claude Sonnet 5 | 506603298 | parsed; wrong modular product |
| placebo | Gemini 3.1 Pro | 397858436 | parsed; wrong modular product |
| placebo | OpenAI Terra | 549271933 | parsed; wrong modular product |
| placebo | Grok 4.6 | 1031983083 | parsed; wrong modular product |

All arms were 0/3, so hinted minus placebo is `0.0`; the hint bought no observed
advantage. That weakens evidence that performance isolates the named search-
pruning intuition: at this preset the dominant obstacle may simply be exact
large-integer search. The diagnostic does not gate shipment. The bare harness
verdict was `hardened` at `easy` with zero escalations.

## Use

```python
from gen_1311_1442 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
answer = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, answer)
```

From the repository root, emit records with:

```bash
bash scripts/emit.sh 1311.1442 20
```

## Caveats

- Track A rests on the paper’s cryptographic assumption plus measured attacks,
  not a hardness theorem for this random distribution. Cardinality and zero
  random hits prove sparsity, not computational hardness.
- `random_candidate` is honest for a reader who enforces the stated weight,
  order, distinctness, and range. It does not model a cryptanalyst with a prior
  learned from untested algebraic leakage.
- Full NFS discrete logarithms, lattice reduction after logarithms, optimized
  birthday/generalized-birthday attacks, and a complete 21-million-plus-state
  meet-in-the-middle run were not executed. The module is standard-library-only;
  these omissions materially limit the claim.
- `canonical_key` handles all carrier reorderings. It does not quotient by every
  automorphism of the presented cyclic group; doing so cheaply is not known here.
- The RFC safe prime removes the paper’s coprime-order subgroup failure mode, but
  does not prove the resulting knapsack distribution secure. The unchanged G9
  result also cautions that this benchmark may measure arithmetic/search capacity
  more than recovery of a human-scale trick.
