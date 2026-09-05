# Rejected: arXiv:2008.00775

This paper is rejected for this benchmark after a completed Track B build.  The
candidate family passes generation and exact verification, and it defeats the
bare oracle pool, but it fails mandatory G9(b): once the permitted one-sentence
structural hint names the invariant, the no-tool solver can execute the compact
route.  In the final three-arm run at the identical shipping preset, bare was
0/3 solved, structural hint was **2/3 solved**, and placebo was 0/3 solved.
Thus H fails in the operational Track B sense required here; G and V pass.

## Paper result and Step-0 triage

The source is Wanless and Wood, [*A general framework for hypergraph
colouring*](https://arxiv.org/abs/2008.00775).  Section 1 defines proper list
colouring, Theorem 3 supplies the general counting framework, and Section 3.1
specializes it to proper graph colouring.  For graphs of maximum degree
`Delta`, Section 3.1 explicitly gives `(Delta+1)`-choosability and says the fact
is easily proved by a greedy algorithm.  Section 4 further notes that entropy
compression often supplies explicit algorithms with polynomial expected time.
Those statements rule out an honest Track A claim; they motivated Track B.

The retained generator uses the paper's native objects.  Each component is
`K_p`, every vertex has a list of `p = Delta+1` finite-field-labelled colours,
and a short vertical parameter represents a concrete proper list colouring.
The parameter is sampled first.  Public lists are built from a composition of
bijective affine and coprime-power maps, so the planted colouring is known by
construction.  Verification expands the represented colouring and performs an
exact collision scan; it never reads `inst["answer"]`.

## Mechanical cost versus compact route

The domain-standard reference algorithm scans all `p` vertical parameters and
checks up to `p` slopes per component: `O(blocks*p^2)` exact modular checks.  At
the final preset (`p=1009`, 5 components, 7 layers), seed 314159 required
**208,243 collision checks and 0.024 seconds**; across eight adversary seeds it
required **1,670,827 checks** and solved 8/8, as expected.  This is easy for a
computer but far beyond a by-hand context.

The compact route is genuinely shorter: the intercept table differs from its
displayed permutation circuit by a linear shear, so one circuit evaluation per
component recovers the five parameters.  The final instance measured **232
exact modular operations**, under the 300-operation cap.  The gap is real; this
is not a rejection merely because an efficient algorithm exists.

## Why it still fails

The admissible structural hint was exactly one sentence and named only the
invariant:

> Across each component, the displayed intercept table differs from its
> permutation circuit by one linear function of the slope.

It contains no chained step, procedure, or derived numerical answer.  At the
first held bare rung (`p=257`), the hint already solved 2/3 attempts.  Following
the rule, the ladder was shifted once and STEP 4 was rerun.  The rerun's bare
loop found `p=521` solved by 1/3 and automatically escalated to `p=1009`, where
bare held 0/3.  At that final held preset, the hint again solved 2/3 while the
same-register placebo solved 0/3.  The hinted-minus-placebo rate is therefore
`+2/3`, isolating useful structural information rather than generic prompt
leakage.  No further G9 move or hand tuning is permitted.

The retained module is `rejected_gen_2008_00775.py`.  Local gates G1--G8 all
pass; G4 observed 0/200,000 structure-aware random hits, G5 found exactly one
valid certificate among 1,045,817,322,864,049 candidates at seed 314159, and
all four no-tool attacks failed on 8/8 seeds.  `selftest_report.json` records
G9 as failed.  The bare, hinted, and placebo transcripts and `.meta.json` are
kept so this decision can be audited or revisited under a different G9 policy.
