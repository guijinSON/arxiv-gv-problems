# Rejected: arXiv:1806.08706

Paper: Feng Hu et al., [*Quantum computing cryptography: Finding cryptographic
Boolean functions with quantum annealing by a 2000 qubit D-wave quantum
computer*](https://arxiv.org/abs/1806.08706), arXiv:1806.08706v3.

## Verdict

This paper does not support a family that passes **G + H + V** under either
hardness track. The natural Track-A task, “find a bent Boolean function,” has
direct deterministic algebraic constructions. A narrower Track-B reconstruction
family was implemented and tested, but every oracle solved every admissible rung:
`9/9` verified solutions over `n = 6, 8, 10`. The script-owned final verdict was
`too_easy`.

The attempted family is therefore not shipped. There is intentionally no
`gen_1806_08706.py`, `selftest_report.json`, README, or G9 hint/placebo transcript.
Retaining those shipping-shaped files after a failed hardening run would make an
invalid result too easy to mistake for an accepted generator.

## What the paper actually defines

Section II.A defines a Boolean function `f: F_2^n -> F_2`, its truth table, the
Walsh coefficients

`W_f(a) = sum_x (-1)^(f(x) + a*x)`,

and nonlinearity

`nl(f) = 2^(n-1) - max_a |W_f(a)|/2`.

For even `n`, a function meeting the Parseval upper bound is bent. Equivalently,
all `2^n` Walsh coefficients have absolute value `2^(n/2)`. Correlation immunity
and `m`-resiliency are also specified by exact zero conditions on selected Walsh
coefficients, plus balancedness.

Section II.B expresses the Walsh transform as an exact Hadamard matrix
multiplication and maps the objective to an Ising Hamiltonian. Sections III–VI
report D-Wave experiments for 2-, 4-, and 6-variable bent functions and for
balanced/resilient 4-variable functions. Section VII is a hardware-resource
scaling discussion, not a computational-hardness theorem for a generated
distribution.

## Step-0 discriminating test

The required question is: **what algorithm produces the certificate, and what
does it cost?** There are two answers, and both disqualify a hard family.

### Natural bent-function generation: fails Track A

Section II.A explicitly lists algebraic constructions as deterministic methods
that provably construct classes of Boolean functions. In particular, the standard
Maiorana–McFarland identity gives, for any permutation `pi` and Boolean offset
`g`,

`f(x,y) = x*pi(y) XOR g(y)`.

Summing over `x` immediately yields

`W_f(a,b) = 2^m (-1)^(g(y) + b*y)`, where `y = pi^(-1)(a)`.

Thus the function is bent by construction. A solver asked for any bent function
can simply choose the identity permutation and zero offset. In compact symbolic
form this is a direct formula, not a search. Sampling a more elaborate `pi` and
`g` in the generator does not help: unless the instance constrains them, the
solver may still output the same canonical construction.

The paper also supplies empirical warnings against a hardness claim in its tested
regime. Table III reports a `95.86%` bent-output frequency for 4-variable
instances at coupler strength `0.25`. Section VI then says a basic greedy
hill-climbing search effectively improves near-optimal outputs. The paper proves
no worst-case or distributional hardness theorem for finding one valid function.

### Exact-spectrum reconstruction: fails Track B

To give the random seed something nontrivial to vary while keeping the paper's
native objects, a Track-B family was tested as follows:

1. Sample a permutation `pi` and offset bits `g` first.
2. Construct the complete exact Walsh spectrum from the identity above.
3. Give that spectrum and the promised Maiorana–McFarland form to the solver.
4. Ask for the compact witness `(pi, g)`.

This clears G and V: the answer is known before the instance is built, and a
checker can recompute every coefficient using exact integer parity arithmetic.
The answer language at the largest rung had about `1.13e45` candidates, with
exact single-answer density about `8.85e-46`.

It does not clear H. The domain-standard algorithm is an inverse fast
Walsh–Hadamard transform followed by parameter extraction. At `n=10` it used
exactly `11,424` counted arithmetic operations and averaged about `0.0004`
seconds in CPython. More decisively, the compact route is too exposed: normalize
each spectrum row, compare its entries at `b=0` and the five unit vectors, read
`pi^(-1)(a)` from the sign changes, and read `g` from the base sign. That takes
only `32 * (5+1) = 192` sign operations.

This is not merely a post-hoc observation. The oracle replies used exactly this
row-character identity, or returned the correctly recovered JSON object directly.
The promise in the problem statement makes the compression route straightforward
enough that increasing the amount of data only adds clerical indexing.

## Measured failed hardening run

The official `scripts/harden.py` ladder was run bare, with no hint. All answers
parsed and independently passed the exact verifier; there were no API errors or
false negatives.

| Preset | `n` | Model | Seed | Result | Seconds |
|---|---:|---|---:|---|---:|
| easy | 6 | x-ai/grok-4.6 | 608317817 | solved | 66.85 |
| easy | 6 | anthropic/claude-sonnet-5 | 581490512 | solved | 26.89 |
| easy | 6 | google/gemini-3.1-pro-preview | 1093345608 | solved | 24.45 |
| medium | 8 | google/gemini-3.1-pro-preview | 1817186134 | solved | 33.54 |
| medium | 8 | openai/gpt-5.6-terra | 72542795 | solved | 11.29 |
| medium | 8 | x-ai/grok-4.6 | 1919390469 | solved | 109.16 |
| hard | 10 | openai/gpt-5.6-terra | 1871687012 | solved | 29.96 |
| hard | 10 | google/gemini-3.1-pro-preview | 806438669 | solved | 76.82 |
| hard | 10 | anthropic/claude-sonnet-5 | 982518885 | solved | 110.30 |

The final script verdict was:

`too_easy: escalate() returned None — the family cannot be made harder, and the oracle pool still solves it`.

Escalation deliberately stopped at `n=10`. At `n=12`, even the compact route
requires `64 * (6+1) = 448` sign operations, exceeding G9(c)'s maximum of 300.
Continuing would turn the benchmark into a longer transcription/indexing task,
not a better test of mathematical insight.

## Local gates before rejection

The abandoned implementation passed the correctness checks before the oracle run:

| Check | Measurement |
|---|---|
| Planted witnesses | `12/12` verified across all four presets |
| Corruptions | drop, swap, duplicate, empty, and out-of-range all rejected with five distinct reasons |
| Parser | tagged JSON round-tripped through prose and markdown |
| Structure-aware guessing | `0/200,000` at `n=10`; exact density `8.85e-46` |
| Cheap adversaries | identity/outlier, row-order greedy, 256 random restarts, and affine ansatz each `0/8` |
| Reference algorithm | inverse FWHT solved `8/8`, as Track B requires reporting |
| Scaling | `n=20` built a spectrum of `1,048,576` coefficients and verified |
| Canonical key | invariant on `20/20` carried affine relabellings and distinct on `20/20` unrelated instances |
| Answer/route caps at `n=10` | 152 characters, about 38 tokens, 64 atomic elements, 192 sign operations |

These numbers illustrate why the rejection is necessary. An enormous answer
space, zero random hits, correct inverse generation, and four failed naive attacks
did not make the problem hard. The compact algebraic invariant solved it on every
oracle attempt.

## Why no alternative from the paper rescues the task

- Asking only for a bent function is solved by a fixed algebraic construction;
  the seed cannot create genuinely different constrained instances.
- Asking for a function with a supplied complete Walsh spectrum is exact and
  diverse, but the Walsh transform is efficiently invertible and the structured
  promise exposes an even shorter row-sign method.
- Asking for the physical Ising ground state under gauge/permutation changes only
  disguises the same Hamiltonian. Such changes must collapse under the canonical
  relabelling rule, so they do not provide unlimited structural diversity.
- Adding random partial truth-table constraints, arbitrary side conditions, or a
  generic SAT/finite-field encoding could create a different benchmark, but none
  of those reductions is central to this paper. They would be convenience
  constructions without a paper-backed hard distribution.
- The multi-criterion experiments are confined to small fixed cases and coupling
  sweeps. The paper gives neither an inverse generator with known optima in a hard
  growing regime nor an average-case hardness result for one.

Therefore no honest Track-A or Track-B family from this paper satisfies all three
mandatory gates, and the result is rejected.
