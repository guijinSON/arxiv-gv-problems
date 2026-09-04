# Rejected after the Track B hardening loop

Paper: Ingo Czerwinski and Alexander Pott, [*On large Sidon
sets*](https://arxiv.org/abs/2411.12911), arXiv:2411.12911v3.

## Decision

No generator is shipped. The strongest native family found clears generation
gate **G** and exact-verification gate **V**, but fails hardness gate **H** on
Track B: the required four-vendor hardening harness returned `too_easy` after
all three permitted escalations. Track A would be false because the requested
certificate is obtained by ordinary binary Gaussian elimination in polynomial
time.

This is not a rejection merely because an efficient algorithm exists. The
mechanical and compact costs were both implemented and measured, and the large
gap made this a plausible Track B candidate. It is rejected because models in
the actual no-tool oracle pool successfully executed the compact route even at
the largest setting allowed by the 300-operation cap.

## Exact paper objects and results checked

- Definition 1.1 defines a binary Sidon set `M` in `F_2^t`: no four distinct
  members sum to zero. It also notes that every subset and every coset of a
  Sidon set is Sidon.
- Definition 1.4 defines an APN function by the at-most-two-solutions condition
  for every nonzero derivative direction.
- Proposition 1.5 states that `F` is APN if and only if its graph
  `{(x,F(x))}` is a Sidon set.
- Section 2 makes intersection with an affine subspace the paper's native
  construction, not an external discrete reduction.
- Proposition 3.3 expresses a Walsh/Fourier coefficient by the two affine
  hyperplane intersection sizes. Corollaries 3.4--3.6 turn a largest
  coefficient of an APN graph into a Sidon set in one fewer dimension.
- Section 4 identifies the easy quadratic almost-bent regime: in odd dimension
  its Walsh coefficients are `0` or `+-2^((d+1)/2)`, and the resulting Sidon
  size only matches the classical parameters. The paper explicitly names the
  cube map `x -> x^3` as APN in Section 1. The record constructions of Theorems
  4.1, 4.3, and 4.4 use special high-linearity functions or spectra; they do
  not provide an average-case hardness theorem for finding the hyperplane.

Thus the prior-triage idea "construct a Sidon set from an APN function graph"
is generatable, but the construction itself is an explicit evaluation rule.
Asking for the complete graph merely asks the solver to execute that rule; at a
writable size it is not hard, and at a larger size it violates the answer and
arithmetic caps. The more promising family below hid the affine hyperplane
rather than asking for the already displayed graph.

## The native Track B family that was tested

For odd `d`, start with the graph of the Gold APN function `x -> x^3` over
`GF(2^d)`. Intersect it with the larger level set of

```text
Tr(x^3 + x) = c.
```

This is exactly the APN-graph/hyperplane construction of Proposition 1.5 and
Corollaries 3.4--3.6. Protect an affine basis, remove a seed-dependent selection
of other points (safe by Definition 1.1), and apply a random sequence of
invertible binary coordinate swaps and shears plus a translation. The problem
asks for the nonzero affine-hyperplane equation containing the resulting
Sidon set.

Generation is inverse/theorem-backed: the trace normal is known before the
random affine map and is transported through it by the inverse-transpose rule.
No hyperplane is found by searching the completed instance. Verification pulls
a submitted normal back through the displayed map and exhaustively checks its
dot product on every retained finite-field graph point, using exact bit and
polynomial-basis arithmetic only. A protected affine basis makes the valid
answer unique. At the 30-coordinate hard preset the structure-aware exact
answer density was

```text
1 / (2 * (2^30 - 1)) = 1 / 2,147,483,646.
```

A 200,000-sample structure-aware guess test produced 0 hits. Five local attacks
(least-touched coordinate, treating a covector as a vector, reversing the
transpose update order, leaving the base normal unchanged, and 256 random
hyperplanes) had 0 successes across 8 seeds each. These facts establish G and
V and rule out naive guessing; they do not override the failed oracle gate.

## Certificate-producing algorithm and measured costs

The domain-standard algorithm enumerates the displayed points, subtracts one
origin, and row-reduces the point differences over `GF(2)`. Its nullspace is
the normal space of the affine hull. Since the protected points span a
codimension-one affine hyperplane, this gives the unique nonzero normal and its
offset. The complexity is `O(|M| d^2)` exact bit operations.

The compact route starts with the displayed trace normal. For a point operation
`coordinate[d] ^= coordinate[s]`, it instead updates the normal by
`normal[s] ^= normal[d]`; a swap swaps the same two normal bits. One final dot
product adjusts the affine offset. Its measured length is the number of
displayed coordinate operations plus one.

| tested level | native set / ambient space | mechanical cost | measured wall time | compact route |
|---|---:|---:|---:|---:|
| hard | about 16,500 points in `F_2^30` | 12,111,810 bit operations | 0.395 s average over 8 seeds | 241 operations |
| final escalation | 65,758 points in `F_2^34` on the solved seed | 59,719,418 bit operations | 1.918 s | 281 operations |

For the final measurement, the 59,719,418 operations consisted of 4,456,448
finite-field multiplication rounds, 18,412,240 coordinate-map operations, and
36,850,730 elimination operations. The compact/mechanical gap is real and
large; it simply did not defeat the evaluated models.

## Required oracle result

The unmodified `scripts/harden.py` ladder used fresh models and seeds. A rung is
defeated if any model solves it, so every row below marked with a solve forced
escalation. All `solved` entries parsed and passed the exact verifier.

| rung | parameters | oracle outcomes | decision |
|---|---|---|---|
| easy | `n=48, d=9` | OpenAI solved; Anthropic solved; xAI solved | defeated |
| medium | `n=144, d=11` | xAI failed; OpenAI solved; Google solved | defeated |
| hard | `n=240, d=15` | xAI solved; Google solved; OpenAI failed | defeated |
| escalated | `n=280, d=17` | Google solved; OpenAI failed; xAI failed | defeated; `too_easy` |

The final Google solve used seed `36988770` and returned the exact verified
witness. Its 281-operation compact route is already close to the hard cap of
300. `escalate()` then correctly returned `None`; increasing the operation list
again would turn the task into a disallowed arithmetic-stamina benchmark, not a
stronger test of the paper's structural insight. Per Step 4, no further manual
retuning, batching, hinted/placebo runs, or alternate random seed was attempted.

## Why neither track supports a release

**Track A fails:** affine-hull recovery is polynomial-time binary linear
algebra, and the paper makes no hardness claim for this generated distribution.

**Track B fails:** despite a 59.7-million-versus-281 mechanical/compact cost
gap, the four-vendor harness obtained a verified witness at every rung,
including the final allowed escalation. The family therefore does not meet the
project's empirical no-tool hardness criterion.

The paper's record-size questions themselves are not a substitute family. The
maximum size is unknown for the relevant dimensions (Section 1), and the paper
does not supply a finite exact certificate that a submitted set is globally
optimal. Asking only for any Sidon set makes explicit APN graphs immediate;
asking for a maximum set fails G/V because no executable optimality witness is
available. This exhausts the paper-backed alternatives without replacing the
native finite-field objects by a convenience graph or CSP.

## Deliverables intentionally absent

There is no `gen_2411_12911.py`, `selftest_report.json`, README, or shipping
oracle transcript. Those are release artifacts for a family that passes every
gate. Keeping the provisional module after a `too_easy` verdict would risk
shipping a known H failure. This `REJECTED.md` is the result.
