# Rejected: arXiv 2507.21656

This paper does not yield an acceptable generator under the required hardness
test.  The rejection is for **H**, not G or V.

## Step 0 finding

The paper's native problem is an `n`-colouring of `[N]` and a monochromatic
solution of

`x1 + x2 + x3 = y1 + y2`.

Section 1 defines the Schur-like number `S_2(n)` this way.  Repeated variables
are allowed; Section 3, Lemma 5 explicitly constructs longer solutions by
repeating entries.  Theorem 4 proves the extremal upper bound
`N = O(sqrt(n!))`, but it is not a computational-hardness theorem and its hidden
constant does not give a concrete generator threshold.  Section 1 also gives
an explicit easy avoidance colouring by geometric intervals of ratio `1.5`.

For a materialised colouring, a witness is produced in polynomial time by
pair/triple-sum bucketing.  Therefore Track A was ruled out before coding.  The
only plausible route was Track B: use a compressed colouring with many
valuation levels, disclose the polynomial scan, and provide a compact
change-of-variables route.

## Family tested

The attempted native Track B family coloured the interval
`[1, 2^(p+1)-1]` by the exact 2-adic valuation of each integer.  A random
projective Möbius map `M` sent valuation levels to `T` in `P^1(F_p)`, and the
colour was an affine relabelling of `T + T^(-1)`.  Reciprocal values therefore
have the same colour.  Conjugating reciprocal inversion by `M` gives the
involution `J = M^(-1) R M` on valuation levels.

Every non-fixed orbit `u < v` yields the exact symbolic witness

`(2^u, 2^v-2^u, 2^v, 2^v, 2^v)`,

because both sides equal `2^(v+1)` and the valuations are `u,u,v,v,v`.
This cleared generation and verification without solving an instance.  It also
had no planted/decoy distinction: every non-fixed orbit was a valid source.

At the attempted hard preset (`p = 50021`, 12 disjoint orbit pairs):

| measurement | result |
|---|---:|
| structure-aware random guesses | 0 / 200,000 |
| exact valid-certificate fraction | `4.0842e-57` |
| reference full scan | 8 / 8 solved, as expected for Track B |
| reference scan cost | about 1,459,812 counted modular steps, 0.24 s |
| compact route | 216 counted exact-arithmetic steps |
| endpoint / adjacent / random-restart / affine-ansatz attacks | all 0 / 8 |
| serialized answer | 165 characters, 24 atomic integers |

These measurements establish that the implementation was valid and sparse;
they do not establish model difficulty.

## Terminal oracle result

The script-owned four-vendor hardening run used master seed
`194812199383356901`.  At least one oracle solved every permitted rung:

| round | parameters | solved / attempts | solvers |
|---:|---|---:|---|
| 0 | `p=5003`, 8 pairs | 2 / 3 | Claude Sonnet 5, GPT-5.6 Terra |
| 1 | `p=20011`, 10 pairs | 2 / 3 | Claude Sonnet 5, GPT-5.6 Terra |
| 2 | `p=50021`, 12 pairs | 1 / 3 | GPT-5.6 Terra |
| 3 | `p=100043`, 12 pairs | 1 / 3 | Grok 4.6 |

The final Grok witness verified exactly.  The harness verdict in `.meta.json`
is `too_easy`: "the oracle pool solved every level through 3 escalations".
Under Step 4 this is terminal and forbids further hand escalation or retuning.
The structural G9 arms were not run because the bare family had already failed
the stronger prerequisite.

The attempted module and the harness-owned bare transcript are retained as
reproducible rejection evidence.  No `selftest_report.json`, release README, or
G9 transcripts are produced because this family must not ship.

Paper: [Tomasz Kosciuszko, *Schur-like numbers and a lemma of Shearer*](https://arxiv.org/abs/2507.21656).
