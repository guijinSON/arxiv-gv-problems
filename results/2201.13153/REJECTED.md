# Rejected: no admissible SSB family survived the one-retry oracle rule

Paper: Marco Cesati, [*A new idea for RSA backdoors*](https://arxiv.org/abs/2201.13153), arXiv:2201.13153.

## Decision

The native inverse-generated family passes **G** and **V**, but it does not pass
the required hardness workflow. It cannot be Track A because the paper itself
gives an efficient recovery algorithm when the escrow prime is supplied. It was
therefore tested honestly as Track B. The first candidate passed bare STEP 4,
but a structurally hinted oracle solved it. On the single harder rung permitted
by G9(b), a bare oracle then solved the instance. A further escalation would
violate the explicit one-retry limit, so the family is rejected rather than
tuned past the evidence.

The retained implementation is `rejected_gen_2201_13153.py`. It is evidence for
reopening the decision, not a shipping generator.

## STEP 0: what produces the certificate

Section 4.1 defines the Single Semiprime Backdoor (SSB). A balanced semiprime
`N=p*q` is vulnerable when a prime escrow key `T` and an integer `k`,
`1 < k <= K`, satisfy

```text
p = k*q (mod T).
```

Figure 1 constructs such primes before multiplying them, so inverse generation
knows the factor certificate without factoring its own output. Sections
4.2.1--4.2.3 give the recovery algorithm from `N` and `T`: enumerate `k`, test
`N/k mod T` for quadratic residuosity, take its modular square roots, enumerate
the high-level quotient coefficients, lift candidate factors, and check their
product. Section 4.3 bounds this at

```text
O(K * (alpha+c)^3 * 2^(2c))
```

and at `O(alpha^4)` under the recommended `K=O(alpha)`, `c=O(log alpha)`
regime. Table 1 reports successful SageMath recovery through RSA-4096 sizes.
Thus exposing `T` while claiming Track A would hide a known polynomial-time
algorithm.

Withholding `T` is not a defensible Track A alternative. The visible task then
becomes ordinary balanced-semiprime factorization; the paper proves no
distributional hardness theorem for this inverse-generated SSB ensemble, and
the paper-specific congruence no longer supplies an intuition route to the
solver.

## Attempted Track B family

The solver received exactly the paper's native integers `N`, `T`, and `K`, and
had to return the smaller prime factor. The generator sampled a prime `T`, a
larger prime coefficient `k`, a small 3/5/7-smooth residue `a`, and quotient
coefficients `pi,nu`, then formed

```text
q = nu*T + a
p = pi*T + k*a
N = p*q.
```

It retained only trials for which `p` and `q` were distinct primes of the
declared bit length and the first three base-`T` digits had no carries. This is
a subfamily of Section 4.1's H0 condition, not a graph or finite-field
surrogate. The checker independently verifies range, divisibility, ordering,
and exact multiplication and never reads `inst["answer"]`.

The compact route is the carry-free identity

```text
N = (pi*nu) T^2 + a(pi+k*nu) T + k*a^2.
```

The square-free part of the constant base-`T` digit reveals `k`; the square
part gives `a`; the two remaining digits give a product and weighted sum for
`pi,nu`, hence a quadratic with square discriminant. The structural hint used
for G9 named only the invariant:

> The least-significant digit of N in base T has a deliberately small
> square-free part.

It did not chain steps, state a derived value, or disclose the answer.

## Mechanical cost versus compact route

The efficient algorithm was not the reason for rejection; there was a real
Track B gap.

At the initial candidate (`K=251`, 61-bit factors, `c=6`), eight local runs of
the faithful Section 4.2 scan all succeeded. The median was **1,363,490**
high-coefficient iterations, **10,908,436** counted exact operations, and
**0.918 s**. The compact identity took a median **46** operations and at most
**60**.

At the one permitted harder rung (`K=509`, 61-bit factors, `c=7`), the exact
instance solved by the bare oracle required **5,118,731** coefficient
iterations, **40,951,134** counted operations, and **1.908 s** in the local
Section 4.2 implementation. The compact route for that same instance took
**44** counted operations. The answer was one 61-bit integer, so neither the
2,000-character/256-atom output cap nor the 300-operation compact-route cap was
binding.

## Local gates before oracle testing

At the initial candidate, all local gates other than the then-pending G9 oracle
arm passed:

| check | measured result |
|---|---:|
| planted verification and JSON round trips | 12/12 |
| corruptions | 5/5 rejected with distinct reasons |
| model-style parse round trip | passed |
| structure-aware random guesses | 0/200,000 |
| exact demo solution count | 1 |
| Pollard-rho baseline | failed after 32,768 iterations; 0.037 s |
| six non-reference attacks | 0/8 successes each |
| Section 4.2 reference algorithm | 8/8 successes |
| canonical factor-label symmetry | 20/20 |
| unrelated canonical keys | 20/20 distinct |
| compact route | median 46, maximum 60 operations |

The failed attacks were treating the low base digit as a factor, 4,096-step
Fermat search, 256 structure-aware random restarts, the by-hand ansatz
`k<=31`, trial division through 10,000, and Pollard rho with eight 4,096-step
restarts. These checks rule out those shortcuts but cannot override a verified
oracle solve.

## Oracle evidence

The initial bare run at `K=251`, `c=6` was fully script-owned and hardened:

| arm | model | seed | result |
|---|---|---:|---|
| bare | `google/gemini-3.1-pro-preview` | 296636650 | failed |
| bare | `x-ai/grok-4.6` | 1862440309 | failed |
| bare | `anthropic/claude-sonnet-5` | 526032017 | failed |

That evidence is in `llm_loop_transcript.jsonl`, with the matching verdict in
`.meta.json`.

The valid structural-hint arm was then solved:

| arm | model | seed | result | elapsed |
|---|---|---:|---|---:|
| hinted | `x-ai/grok-4.6` | 1486523997 | **solved, verifier `ok`** | 629.52 s |

Grok explicitly computed `N mod T`, decomposed it as `223*15625^2`, recovered
the quotient coefficients, and returned the verified smaller factor. This
record is `g9_hinted_transcript.jsonl`.

G9(b) permits one move upward. The ladder was shifted to `K=509`, `c=7`, and
bare STEP 4 was rerun. It was defeated before a hinted retry was even relevant:

| arm | model | seed | result | elapsed |
|---|---|---:|---|---:|
| harder bare | `google/gemini-3.1-pro-preview` | 1723863244 | failed | 27.16 s |
| harder bare | `x-ai/grok-4.6` | 2101354576 | **solved, verifier `ok`** | 530.46 s |

Those records are in `g9_retry_bare_transcript.jsonl`. The run was stopped
after the decisive solve so the general-purpose escalator could not silently
exceed G9's one-rung allowance. No placebo arm was purchased after the gated
failure; consequently no hinted-minus-placebo inference is claimed.

## Final gate outcome and caveats

| requirement | outcome | reason |
|---|---:|---|
| G -- generatable | pass | factors are sampled before multiplication |
| V -- exact witness | pass | exact divisibility and product verification |
| H -- Track A | fail | Section 4.3 gives polynomial recovery with `T` |
| H -- Track B | locally credible | 10.9M versus 46 median operations initially |
| STEP 4 bare, initial | pass | three distinct vendors failed |
| G9(b), initial | fail | invariant-only hint enabled a verified solve |
| one permitted harder rerun | fail | a bare oracle returned a verified factor |
| overall | **rejected** | no admissible shipping rung survived the mandated loop |

The random-guess estimate samples alpha-bit integers after a small-prime wheel;
it does not model a specialist factorization algorithm. GNFS was not
implemented locally. Pollard rho and Fermat are meaningful cheap attacks, but
their failure is not evidence against GNFS. Most importantly, the planted
3/5/7-smooth residue is a deliberate Track B signal: it creates the compact
route and also makes the family vulnerable once a solver recognizes the base-
`T` invariant. The oracle evidence shows that recognition is within the tested
models' reach, so shipping this family would not meet the requested bar.
