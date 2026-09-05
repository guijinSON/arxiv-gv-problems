# Rejection: arXiv:2505.16105

## Decision

No family from this paper satisfies the required hardness gate.  The paper is
generatable and exactly verifiable, but the viable native task fails **H on both
tracks**:

- **Track A fails at STEP 0.**  Section 2, equations (2.3)--(2.5), is an exact
  algorithm for the required cardinalities.  Theorem 2.2 is an explicit
  construction and numerical computation, not a hardness theorem or a hard
  parameter regime.
- **Track B fails empirically at the permitted no-tool scale.**  The repository
  hardening loop returned `too_easy`.  At the hard preset, all three vendors
  returned verified exact answers.  Making the displayed set longer while
  leaving the printed radix parameters and the compact calculation unchanged
  would only pad the prompt, not grow the mathematical haystack.

The failed implementation is retained as `rejected_gen_2505_16105.py`, together
with the script-owned `.meta.json` and `llm_loop_transcript.jsonl`.

## What the paper actually gives

Section 1 defines the target using finite integer sets and the exact quantities
`|U+U|` and `|U-U|`.  Section 2 defines the bounded lattice simplex
`W(m,L,B)`, maps it to integers using a carry-free radix at least `2B+1`, and
derives exact inclusion--exclusion formulas for both cardinalities.  Thus G is
available by theorem-backed construction and V is available by exact pair
enumeration or by recomputing the formulas.

The certificate-producing algorithm is precisely equations (2.3)--(2.5).  The
proof of Theorem 2.2 says that the small search `m <= 128, L = 64, B <= 7`
finished in under one second and that exact evaluation at
`(m,L,B)=(81411,65536,5)` took about 15 hours using GMP.  This explicitly rules
out a Track-A claim for the generated distribution.

## Mechanical cost versus compact route

The rejected Track-B draft handed the solver an explicit affine image of the
paper's set and also printed its radix parameters.  Generic hash-set enumeration
costs `O(|A|^2)` exact additions/subtractions, while the compact route is the
paper's digit-vector change of variables followed by equations (2.3)--(2.5).

At the three hard-preset oracle seeds, the measured costs were:

| seed | `|A|` | generic pair operations | local wall time | compact-route operations | oracle result |
|---:|---:|---:|---:|---:|---|
| 1820651883 | 1261 | 1,590,121 | 0.123 s | 249 | solved |
| 1150925661 | 1007 | 1,014,049 | 0.094 s | 196 | solved |
| 432751540 | 1182 | 1,397,124 | 0.135 s | 182 | solved |

There is a mechanical/compact gap at this scale, but it is too small to support
Track B: the supposedly insightful route is already fully exposed by the
instance promise and was executed successfully by all three hard-preset models.
Across the whole fresh run, easy was solved by 2/3 models, medium by 3/3, and
hard by 3/3.  Every returned winning answer parsed and passed exact verification.

The paper's record scale does not rescue Track B under G9(c).  A literal
nonzero-term count for equations (2.3)--(2.5) at `(81411,65536,5)` is:

- 11,916 inclusion--exclusion terms for the sumset count;
- 65,537 outer terms for the difference count;
- 357,957,631 and 715,860,651 inner inclusion--exclusion terms;
- 1,073,830,198 inclusion--exclusion terms across the sum and difference
  formulas in total, before counting the arithmetic needed to form the binomial
  coefficients.

The author's optimized exact computation still took about 15 hours.  No second,
short route is proved in the paper; the mechanical method and the proposed
"compact" method are the same Section 2 formulas at this scale.  This is far
beyond the 300-exact-operation cap.  In addition, the exact record cardinalities
have roughly 61,229 and 75,900 decimal digits, far beyond the 2,000-character
answer cap.

## Oracle evidence

The repository-owned run ended with:

```json
{
  "verdict": "too_easy",
  "escalations_used": 2,
  "axes_moved": ["min_route_operations", "n"],
  "answer_atoms": 2,
  "reason": "escalate() returned None -- the family cannot be made harder, and the oracle pool still solves it"
}
```

This is not a parser or verifier artifact: all eight winning replies contained a
parsed two-integer answer and `verify` returned `(True, "ok")`.  The sole losing
reply was rejected specifically because its sumset cardinality was incorrect.

## Failed gate and scope

- **G:** passes for the draft, by the construction in Section 2.
- **V:** passes for the draft, by exact finite-set recomputation.
- **H / Track A:** fails because equations (2.3)--(2.5) give the exact algorithm
  and the paper proves no distributional hardness.
- **H / Track B:** fails because all three hard-preset oracle attempts solve the
  largest under-cap structural instances; moving to the paper's computationally
  expensive regime makes the route and the answer exceed G9(c), rather than
  revealing a shorter insight.

Source: [Robert Gerbicz, *Sums and differences of sets (improvement over
AlphaEvolve)*](https://arxiv.org/html/2505.16105v1), especially Section 2 and
Theorem 2.2.
