# Rejected: hinted pseudo-moment rank-one search is too easy

Paper: Venkatesan Guruswami, Xuandi Ren, and Shaoxuan Tang,
[*Strong Inapproximability for a Promise Rank Problem*](https://arxiv.org/abs/2605.11545),
arXiv:2605.11545v1.

## Decision

The attempted family fails the gated G9(b) no-tool test. The bare instance at
the permitted one-rung retry, `medium` with `n=71`, defeated all three oracle
vendors, but the same instance family with its one-sentence structural hint was
solved by **2 of 3** vendors. The hint says that the dense coefficient matrix is
circulant and that its inverse is identity plus 3 times one cyclic shift. This
is exactly the compact route the family claimed to test. Because naming it
dissolves the problem, G9(b) requires rejection.

The first shipping candidate, `easy` with `n=47`, likewise hardened bare but
was solved by the first hinted vendor. The task permits moving up one named
rung and rerunning bare and hinted exactly once. I did that at `n=71`; the hint
still broke the family, so no further escalation or parameter tuning is
allowed. The placebo arm was not run after the decisive gated failure.

## Step-0 audit and track choice

The paper's native problem is: given a linear subspace
`L <= F_q^(N x N)`, distinguish a YES instance with a nonzero rank-one matrix
from a NO instance in which every nonzero matrix has rank above a stated gap.
Theorem 1.2 gives this hardness for every fixed finite field. Section 4 and
Theorem 4.1 reduce Boolean quadratic equations to a pseudo-moment subspace. At
degree `d`, rows and columns are indexed by squarefree monomials of degree at
most `d`; equal-union constraints impose

`H_d(y)[S,T] = y_(S union T)`,

and localizing constraints impose the moment versions of
`x^W f_l(x)=0` for every `|W| <= 2d-2`.

The prior Track-A hypothesis—put a planted rank-one matrix in a random-looking
subspace—does not follow from these theorems. They prove worst-case hardness for
subspaces output by reductions from arbitrary SAT or QuadEq instances, not
average-case hardness for an inverse-generated planted distribution. Claiming
Track A for that distribution would therefore confuse worst-case hardness with
the generated regime, exactly what the task forbids.

I instead tested an honest Track-B construction. It used the paper's exact
degree-2 pseudo-moment subspace over the fixed field `GF(257)`, but specialized
the source equations to a uniquely solvable linear system. Dense Gaussian
elimination is the reference algorithm: `O(n^3)` exact field operations. At
`n=71`, eight runs solved 8/8 instances in 0.011647 seconds total and 479,922
counted field operations total (59,990 per instance on average). Thus the
certificate-producing algorithm was identified and reported before hardening;
this was never a Track-A claim.

## Generation and verification that did work

For a uniformly sampled Boolean vector `x`, choose a coprime cyclic shift `s`,
let `P_s z` have coordinate `i` equal to `z_(i+s mod n)`, and put

`G = I + 3 P_s`, `A = G^(-1)`, and `b = A x` over `GF(257)`.

The inverse `A` is constructed by a finite geometric-series identity, so the
answer is known before the public right-hand side is made. Section 4's
completeness construction maps `x` to the exact nonzero rank-one matrix
`H_2(x)=v_2(x)v_2(x)^T`. The submitted bit string is a succinct factor rather
than thousands of matrix entries.

The checker does not read the planted answer. It checks that the candidate is
an `n`-bit Boolean vector and recomputes `A x=b` modulo 257. This is also an
exact executable check of every localizing equation because its left side on
an honest factor is `x^W f_l(x)`. The empty moment is 1, so the outer product is
automatically nonzero and rank one. G and V therefore passed.

Because `A` is invertible, the answer is unique. At `n=71` the exact structured
candidate density is `2^-71 = 4.235164736271502e-22`; uniform sampling found
0 valid answers in 200,000. Four non-reference attacks each failed on 8/8
instances: column-correlation outlier guessing, greedy improvement in the
number of exactly satisfied rows, 256 uniform restarts, and simple projections
of the right-hand side. This did not rescue G9(b).

## Oracle evidence at the decisive rung

The bare transcript was produced by `harden.py` in an isolated directory and
copied to `llm_loop_transcript.jsonl`. The hinted transcript is
`g9_hinted_transcript.jsonl`.

| arm | model | seed | result | verifier detail | elapsed |
|---|---|---:|---|---|---:|
| bare | `anthropic/claude-sonnet-5` | 183333967 | failed | empty length-limited reply | 301.84 s |
| bare | `x-ai/grok-4.6` | 513834210 | failed | constraint 0 violated | 336.65 s |
| bare | `openai/gpt-5.6-terra` | 2069463375 | failed | constraint 0 violated | 88.40 s |
| structural hint | `anthropic/claude-sonnet-5` | 645765112 | failed | constraint 0 violated | 48.36 s |
| structural hint | `x-ai/grok-4.6` | 1612268363 | **solved** | `ok` | 97.25 s |
| structural hint | `openai/gpt-5.6-terra` | 426157315 | **solved** | `ok` | 42.33 s |

The compact route needs 143 exact field operations at `n=71`: after locating
the unique shift from the first coefficient row, compute
`x_i=b_i+3 b_(i+s) mod 257` using one multiplication and one addition per bit,
plus one multiplication to identify the shift. The serialized answer is 73
characters, approximately 19 tokens, and 71 atomic elements, so G9(c)'s size
and effort caps passed. The failure is specifically G9(b), not transcription
size or unchecked arithmetic.

## Why another paper-derived variant was not substituted

| candidate | reason it does not supply an acceptable replacement |
|---|---|
| Random planted sparse Boolean QuadEq followed by Section 4 | G and V hold, but Theorem 4.1 is worst-case and supplies no distributional hardness theorem for planted random equations; there is also no compact sub-300-operation intended route. |
| Section 3's full 3SAT-to-moment reduction on planted satisfiable formulas | Theorem 3.1 again gives worst-case, not planted-distribution hardness; implementing the reduction does not cure that gap. |
| A random matrix subspace with one planted rank-one element | This is not the paper's central reduction, and neither theorem establishes hardness for that planted ensemble. |
| Raise `n` again after the hinted solve | Explicitly forbidden: G9(b) allows only the one move from `easy` to `medium`, already used. |

## Gate outcome

| requirement | result |
|---|---|
| G — certificate by construction | Pass: inverse generation plus Section 4's completeness identity. |
| H — Track-B no-tool compression | **Fail in the required hinted test:** 2/3 vendors executed the compact route at the one allowed retry rung. |
| V — cheap exact verification | Pass: exact modular substitution and the localizing identity. |
| G1–G8 local gates | Passed in the attempted module at `n=71`; these cannot override G9(b). |
| G9(c) caps | Passed: 73 characters, 71 atoms, about 19 tokens, 143 field operations. |
| G9(b) hinted oracle | **Failed:** verdict `too_easy`, with 2/3 valid witnesses. |

Accordingly there is no `selftest_report.json`, placebo transcript, or accepted
generator deliverable. Keeping a locally correct module cannot turn a failed
mandatory hardness gate into a shippable family.
