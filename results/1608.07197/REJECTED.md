# Rejected at Step 0: inverse planting does not establish identifiability hardness

Paper: Elena Angelini, Cristiano Bocci, and Luca Chiantini,
[*Real identifiability vs complex identifiability*](https://arxiv.org/abs/1608.07197),
arXiv:1608.07197v3.  The full paper and its 24-page ancillary computation were
read before making this decision.

## Decision

No generator is shipped.  The prior-triage proposal—sample real rank-one
summands and publish their sum—does pass **G** for the weakened task “find any
decomposition,” and that answer passes **V** by exact expansion.  It does not
pass **H under Track A**: the paper proves geometric existence and generic
identifiability statements, not search hardness for an answer-first planted
distribution.  In fact, Section 5 treats decomposition recovery as a square
polynomial-system computation and explicitly uses homotopy continuation and
monodromy loops to obtain all decompositions.

The paper's actual distinguishing claim—one real decomposition but several
complex decompositions—cannot be certified merely by planting one real
decomposition.  Proving that no second real decomposition exists requires
finding or excluding the other complex solutions.  The paper does that
numerically for specific tensors; it does not provide a bounded exact witness
that a standard-library checker can inspect for arbitrary generated instances.
Thus a task that requires the paper's full real-identifiability property also
fails the proposed route at **G/V**, independently of H.

**Track B was considered before rejecting.**  The disclosed mechanical method
has no distinct, instance-visible compact route.  The private fact that the
generator sampled the summands first is not an insight available from the
rendered tensor.  If the plant is made visible through a special coefficient
pattern, reading that pattern becomes the ordinary in-context attack and the
family no longer has the required four failing attacks.  If it is hidden by a
generic change of basis, recovering it is again the same polynomial-system or
companion-matrix computation.  There is therefore no honest mechanical-versus-
compact gap on which to base Track B.

Following the task's Step-0 rule, `gen_1608_07197.py`, `selftest_report.json`,
and oracle transcripts were not fabricated after H failed.

## What the paper actually proves

Section 1 defines a real tensor to be identifiable over the reals when it has a
unique decomposition into real rank-one tensors, even though complex rank-one
decompositions may not be unique.  Table 1 lists six fixed exceptional tensor
formats and ranks.  In those formats, a general rank-`r` tensor has exactly two
complex decompositions because the planted rank-one points determine an elliptic
normal curve of degree `2r`.

The paper's main results are geometric and existential:

- Proposition 2.6 constructs Euclidean-open sets of four secant types for a
  real elliptic normal quartic.
- Lemma 3.2 and Theorem 3.3 extend the construction to real elliptic normal
  curves of degree `2r` in projective `(2r-1)`-space.  The theorem gives open
  sets where one `r`-secant space uses real points and the other contains
  non-real points.
- Theorem 3.5 is the relative version for families of elliptic curves.
- Remark 4.1 and Proposition 4.2 recall that, in the six Table 1 formats, `r`
  general rank-one points determine the relevant elliptic curve.  Theorem 4.3
  then proves the existence of open sets with one real/two real/no real
  decompositions.
- Section 5 gives further fixed-format examples and also states an easy
  obstruction: when the general tensor has a positive-dimensional family of
  complex decompositions, a smooth real point yields infinitely many real
  decompositions, so no open set can be real-identifiable in the desired way.

None of these results is a complexity theorem.  “Exactly two decompositions”
is an enumerative statement, not evidence that recovering a planted one is hard
on the generated distribution.

## The certificate-production test

### Symmetric ternary tensors in Section 5

For a degree-`d` symmetric ternary tensor, Section 5 writes

`T = lambda_1*l_1^d + ... + lambda_r*l_r^d`

with `l_i = x_0 + a_i*x_1 + b_i*x_2`.  Coefficient matching produces a square
polynomial system.  The paper generates a start tensor by choosing all
`(a_i,b_i,lambda_i)` first, exactly as the prior triage suggested.  It then uses
three-segment homotopy loops and monodromy to discover the other solutions,
restarting until their number stabilizes.

The two paper scales are numerical and fixed:

| format | variables/equations | complex decompositions | paper's finder |
|---|---:|---:|---|
| ternary septic, `d=7,r=12` | 36 / 36 | 5 | homotopy continuation plus monodromy |
| ternary octic, `d=8,r=15` | 45 / 45 | 16 | the same method, with “much more computational effort” |

The ancillary file prints floating-point approximations to all decompositions;
they are not exact rational or algebraic-number certificates.  Inverse-generating
rational summands would make the *planted* identity exact, but would not certify
that the resulting special tensor lies in the open subset with exactly one real
decomposition.

### The almost-unbalanced example

For tensors of type `3 x 5 x 10` and rank 9, Section 5 reduces decompositions to
the intersection of the Segre variety `P^2 x P^4` with an 8-plane in `P^14`.
The desired example has 15 intersection points: nine real and six non-real.
The ancillary Macaulay2 script computes a kernel, adds all `2 x 2` minors,
forms a quotient basis and eight `15 x 15` companion matrices, and calls
`eigenvectors` to recover the points.  Again, planting nine rational rank-one
matrices certifies nine points in the span; it does not certify that the six
remaining intersection points are non-real without performing the global
intersection computation.

### The elliptic-quartic side problem

Section 2 does contain a fully explicit exact search, but it is far too small
for either hardness track.  In Example 2.7, substituting the plane
`x_2 = k*x_3` into the two quadrics reduces the unknown intersection points to

`x_2 = k*x_3`,

`x_3 = -(x_0+x_1)/(1+k^2)`,

`k^2*x_0^2 - 2*x_0*x_1 + k^2*x_1^2 = 0`.

After fixing projective scale, the standard algorithm is one quadratic formula.
A direct operation accounting needs at most 16 high-level exact arithmetic
operations plus one exact square-root operation to construct both points.  The
paper's “compact” derivation is that identical substitution and quadratic
formula: at most 16 operations plus the same square root.  Increasing the bit
length of `k` enlarges integer arithmetic but never creates a structural
compression gap.  This is the concrete mechanical/compact comparison required
before rejecting Track B: **16 versus 16**, not a million-step method versus a
short invariant.

## Mechanical cost versus compact route for decomposition

The paper does not report wall-clock timings or arithmetic-operation counts for
its Bertini/Matlab runs, so inventing either would be misleading.  It does give
auditable problem sizes.  For the septic, a complete recovery starts from one
known solution and must discover four more; one monodromy triangle contains
three homotopy segments, so even the optimistic one-new-solution-per-loop lower
bound is 12 numerical path segments through a 36-equation system.  For the octic,
discovering the other fifteen solutions gives an analogous lower bound of 45
path segments through a 45-equation system.  Actual continuation uses many
predictor/corrector steps per segment and repeats until stabilization.

There is no smaller public route in the proposed planted distribution:

| candidate | mechanical route | compact route available to solver | gap |
|---|---:|---:|---:|
| septic real decomposition | at least 12 path segments on 36 equations; paper finds all 5 solutions | the same 36-variable decomposition solve | none |
| octic real decomposition | at least 45 path segments on 45 equations; paper finds all 16 solutions | the same 45-variable decomposition solve | none |
| `P^2 x P^4` rank-one points | ideal/minors, quotient algebra, eight `15 x 15` eigensystems | the same intersection computation | none |
| Section 2 quartic intersection | at most 16 exact operations plus one square root | the identical quadratic reduction | 16 versus 16 |

Counting the generator's private answer-first step as a one-step “compact
route” would hand the solver unavailable secret state.  Conversely, adding a
public marker that reveals the summands would make that marker a successful
outlier/ansatz attack.  Neither is Track B.

## Assessment of candidate problem families

| candidate task | G | H | V | outcome |
|---|---:|---:|---:|---|
| Find any real rank-`r` decomposition of an inverse-planted rational tensor | pass | **Track A unsupported; Track B has no compact route** | pass by exact expansion | reject |
| Certify that the planted decomposition is the unique real one | **fail for the proposed generator** | unsupported | **fail with only the decomposition** | absence of another real solution has no bounded exact certificate here |
| Return all complex decompositions of a Section 5 tensor | generation requires running the paper's solver | no separate compact route | floating approximations are not exact witnesses | reject |
| Find the nine real points in the almost-unbalanced Segre intersection | planting gives nine points but not the required real/non-real count | no hardness theorem or compact route | exact membership is easy; exhaustiveness is not | reject |
| Solve the explicit elliptic-quartic plane intersection | pass | **fail on both tracks** | pass | one quadratic formula |

## Why Track A cannot be claimed

The paper contains no NP-hardness, average-case hardness, parameterized lower
bound, or search lower bound.  More importantly, its key tensor formats are
fixed (`d=7,r=12`, `d=8,r=15`, and `3 x 5 x 10,r=9`).  Raising coefficient
height only increases the bit cost of a fixed algebraic system; it does not put
the generator into a theorem-backed growing hard regime.  The authors' own
method successfully recovers the decompositions of their planted start tensors.

One could instead scale arbitrary tensor dimensions and ranks, but that leaves
the parameter regimes of Theorem 4.3 and Section 5.  Worst-case hardness results
for tensor problems from other literature would still not establish hardness
for the answer-first random distribution.  Such a module would repeat precisely
the forbidden leap from worst-case problem-class hardness to planted-instance
hardness.

## Why Track B cannot be claimed

Track B requires an efficient disclosed reference algorithm, a measured
mechanical cost at the shipping preset, and a genuinely shorter route visible in
the instance after a structural insight.  The generic planted decomposition has
no such second route.  The source paper's only compact symbolic calculation is
the Section 2 quadratic elimination, whose ordinary and insightful routes are
both 16 operations.  The larger examples have expensive numerical/algebraic
finders but no public invariant that reveals the planted decomposition in under
300 exact operations.

An artificial Walsh orbit, sparse coefficient watermark, or low-rank mixing
matrix could manufacture a puzzle with a shortcut.  That shortcut would come
from the benchmark designer, not from this paper's identifiability theorem, and
would need to survive its own outlier, ansatz, and hinted-oracle attacks.  It is
not used here to claim native coverage.

## Gate outcome

| requirement | outcome | evidence |
|---|---|---|
| G—generatable | passes only for the weakened “find any decomposition” task | sample rational rank-one summands first and sum them exactly |
| H—Track A | **fail / unsupported** | no theorem for the inverse-planted distribution; fixed paper formats are explicitly attacked by algebraic/numerical decomposition methods |
| H—Track B | **fail** | no instance-visible compact route; the one explicit compact example is 16 versus 16 operations |
| V—verifiable | passes for a supplied exact decomposition | check each summand is rank one and recompute every tensor coefficient |
| paper's real-identifiability claim | **not certified by that witness** | one real decomposition does not prove that all other decompositions are non-real |
| Steps 1–4 | not run | Step 0 requires stopping once G, H, or V fails |

The rejection is therefore about H, not about the usefulness of tensor
decompositions as witnesses.  The prior-triage construction is a sound way to
know *an* answer; it is not evidence that the rendered instance is hard, and it
does not certify the real-versus-complex uniqueness property that is the paper's
main contribution.
