# Rejected: the hinted SSB recovery is executable by the oracle

Paper: Marco Cesati, [*A new idea for RSA backdoors*](https://arxiv.org/abs/2201.13153), arXiv:2201.13153.

## Decision

The attempted native Track B family fails the gated G9(b) no-tool test.  Its
first two-row shipping candidate defeated three bare oracle vendors, but Grok
4.6 recovered and verified both factors after receiving the one-sentence
structural hint.  The rules permit one move up the ladder, so the old medium
rung (three independent SSB rows) was promoted and both STEP 4 bare and G9(b)
were rerun.  The promoted bare rung again defeated three vendors, but Grok 4.6
again used the hint and returned all three exact smaller factors.  Because the
hint still breaks the family after the single permitted retry, no further
escalation or tuning is allowed.

The placebo arm was not run after this decisive gated failure.  There is no
`selftest_report.json` or accepted generator deliverable; the local module and
script-owned transcripts are retained only as reproducible evidence for the
rejection.

## What the paper actually says

Section 4.1 defines the Single Semi-prime Backdoor (SSB).  A balanced
semiprime `N=p*q` is vulnerable when, for a prime escrow key `T`, there is a
small integer `k` such that

```text
p = k*q (mod T).
```

The paper's generator samples primes and adjusts one into this residue class;
thus inverse generation can know the factorization before publishing `N`.
Section 4.2 gives the recovery algorithm when `N` and `T` are known.  For each
candidate `k`, it computes `N/k mod T`, tests whether it is a quadratic
residue, takes modular square roots to obtain the possible residues of `q`,
and exhausts the small high-level quotient coefficients before checking
`p*q=N`.

Section 4.3 is the decisive STEP 0 fact.  The paper bounds this recovery by

```text
O(K * (alpha+c)^3 * 2^(2c)),
```

and by `O(alpha^4)` in its recommended regime `K=O(alpha)` and
`c=O(log alpha)`.  The experimental section reports successful recovery even
for RSA-4096 instances.  Therefore a task that hands the solver the escrow key
cannot honestly claim Track A: the paper itself supplies a polynomial-time
certificate-producing algorithm.

Withholding `T` does not give a suitable alternative.  It reduces the visible
task to ordinary balanced-semiprime factorization, while the paper proves no
distributional hardness theorem for the inverse-generated SSB ensemble.  The
paper-specific congruence and its compact route would also be absent from what
the solver receives.  Calling that a native Track A family would trade on the
general RSA assumption rather than on a theorem about this generated
distribution.

## Attempted Track B construction

Each row exposed the paper's native integers `N`, `T`, and `k`, plus

```text
C = floor(p/T) + floor(q/T).
```

Supplying `k` and `C` specializes Section 4.2 by removing its two short
exhaustive loops.  Since every generated `T` is `3 mod 4`, the exact reference
route is:

1. compute `z=N*k^(-1) mod T`;
2. compute the two square roots of `z` modulo `T`;
3. for each root `a=q mod T`, set `b=k*a mod T`;
4. solve the paper's quotient quadratic with the supplied sum `C`;
5. multiply the lifted factors and retain the exact factorization.

The generator sampled the primes first, formed `N` afterward, and used the
deterministic seven-base Miller--Rabin theorem below `2^64`; it never factored
an instance to discover its certificate.  The checker did not read the plant:
it checked only bit range, exact divisibility, smaller-factor orientation, and
exact multiplication.

At the rejected three-row rung, the reference algorithm solved 8/8 instances
in a median **193** counted exact operations and **0.00001018 s**; the maximum
observed route was **214 operations**.  Its complexity is `O(n log T)` exact
arithmetic for the specialized input.  The answer at seed 0 was 27 characters,
about 7 tokens, and 3 atomic integers, so G9(c)'s size and 300-operation caps
passed.  This was an honest Track B claim, not a hidden efficient algorithm.

## Local gates that passed

| gate | measured result at the rejected three-row rung |
|---|---:|
| G1 planted/JSON checks | 12/12 across all four presets |
| G2 corruptions | 5/5 rejected with five distinct reasons |
| G3 model-style round trip | passed |
| G4 structure-aware guesses | 0/200,000 |
| bounded candidate language | 4,165,532,828,972,443,027 candidates |
| demo exact valid-answer count | 1 |
| bounded Fermat baseline | failed after 12,288 total nodes; 0.000853 s |
| six non-reference attacks | 0/8 successes each |
| Track B reference recovery | 8/8; median 193, maximum 214 operations |
| doubled-size construction | verified at 6 rows; 370 reference operations |
| canonical-key invariance | 60/60 transformations and carried witnesses |
| unrelated canonical keys | 20/20 distinct |

The six failed attacks were nearest-square guessing, a no-modular-wrap greedy
estimate, treating `N mod T` as a factor residue, 512-step Fermat search,
trial division through 10,000, and 256 structure-aware random restarts.  These
results establish correctness and rule out obvious planting artifacts; they
cannot override G9(b).

## Oracle evidence

The first candidate had two rows of 24-bit factors.  Its bare level hardened
0/3, but the first completed structural-hint oracle solved it:

| level / arm | model | seed | result | elapsed |
|---|---|---:|---|---:|
| two rows, hinted | `x-ai/grok-4.6` | 137339705 | **solved**, verifier `ok` | 338.37 s |

Grok returned `<answer>[12174011, 12173159]</answer>`.  This triggered the
single permitted move to three rows.

At the promoted three-row level, the replacement bare STEP 4 run hardened:

| arm | model | seed | result | verifier detail | elapsed |
|---|---|---:|---|---|---:|
| bare | `openai/gpt-5.6-terra` | 1264367748 | failed | entry 1 is not a divisor | 138.25 s |
| bare | `anthropic/claude-sonnet-5` | 837857929 | failed | empty length-limited response | 257.62 s |
| bare | `x-ai/grok-4.6` | 224568642 | error, redrawn | 900-second hard deadline | 900.00 s |
| bare | `google/gemini-3.1-pro-preview` | 1547479316 | failed | empty length-limited response | 221.03 s |

The errored Grok call did not consume an attempt; the three normal failures
were from three distinct vendors.  The promoted structural-hint run then
failed immediately:

| arm | model | seed | result | elapsed |
|---|---|---:|---|---:|
| structural hint | `x-ai/grok-4.6` | 127383734 | **solved**, verifier `ok` | 421.70 s |

Grok explicitly followed the modular-root and quotient-sum route and returned
`<answer>[9477019, 13894511, 10080649]</answer>`.  This is a genuine solve of
the intended compact route, not a parser accident, leaked plant, or lucky
guess.

## Final gate outcome

| requirement | outcome | reason |
|---|---:|---|
| G — generatable | pass | factors sampled before each semiprime |
| V — exact witness checking | pass | exact divisibility and product checks |
| H — Track A | disallowed | Section 4.3 gives polynomial recovery when `T` is supplied |
| H — Track B | locally plausible | 193 median exact operations; non-reference attacks failed |
| STEP 4 bare | pass at promoted rung | three distinct normal oracle failures |
| G9(c) caps | pass | 27 characters, 3 atoms, 214 maximum observed operations |
| G9(b) structural hint | **fail** | verified Grok solve at both the initial and one-retry rungs |
| overall | **rejected** | the hinted gate failed after the only allowed escalation |

The mechanical/compact gap was real enough to test: the full paper algorithm
is polynomial and includes searches over `k` and up to `2^(2c)` high-level
values, while the specialized compact route costs at most 214 measured exact
operations here.  The rejection is not merely that an efficient method exists;
it is that a no-tool oracle executed the compact method twice, including after
the only permitted increase in workload.
