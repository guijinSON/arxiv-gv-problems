# Audit: what actually solves each shipped family

**This document was rewritten on 2026-09-04. Its earlier version called 23 families
"broken" and five were withdrawn on that basis. That verdict was wrong, and the
withdrawn five have been restored.** What follows is the corrected reading.

## What was measured

A domain-standard solver was written and run against 23 shipped families at their
shipping preset, 8 seeds each, graded only by each module's own `verify()`. All 23
have a cheap mechanical route — most under a second, several under 0.02 s.

The attacks are in `audit/`, reproducible. The per-family result is in
`audit/attack_families.json`.

## Why that is not "broken"

**The evaluation is tools-free.** Models being tested cannot run a SAT solver, so
"a SAT solver cracks this in 14 ms" does not describe the conditions the question is
posed under. The relevant measurement is the oracle loop, and it says the opposite:

> Every one of the 23 held at its shipping preset against a multi-vendor pool of
> frontier models with no tools — `solved 0/3` at the shipped level in each case,
> after escalating away from any level a model did solve.

Under the conditions these questions are actually used, they work. The earlier
verdict measured against a threat model that does not exist in the eval.

Nor can "an efficient algorithm exists" be a disqualifier on its own: for essentially
every paper in the pool an algorithm exists — the algorithm **is** the paper. Applying
that rule consistently leaves cryptography and nothing else.

## What the measurement is actually good for

### 1. Aging risk

A cheap mechanical route on a small instance is a prediction about shelf life. The
adversary under a tools-free eval is not the solver — it is **a model simulating the
solver in its head**, and that is precisely the capability improving fastest. A family
a library cracks in 0.001 s on a 192-edge instance will fall before one that needs a
meet-in-the-middle over 2^32.

Recorded per family as `seconds` in `audit/attack_families.json`. Re-run the oracle
pool periodically; a family that flips from held to solved has aged out.

### 2. The honest label for what a question IS — and this is the important one

The solver that cracks a family describes it better than anything the builder declares.
`2411.04916` declares itself geometric — kissing numbers in 17 to 21 dimensions — and
is solved by constraint search. `2302.11250` is debt swapping in financial networks;
also constraint search. `2509.03064` is words and permutations; also constraint search.

Measured across the 23:

| solver family | share |
|---|---|
| constraint search (SAT/CSP/exact cover/colouring) | **57%** |
| subset-sum / knapsack | **22%** |
| dense subgraph / spectral | 9% |
| linear algebra over a finite field | 4% |
| brute force over a structured space | 4% |
| the paper's own construction | 4% |

**Top two solver families cover 78%**, and subset-sum is itself expressible as a
constraint problem. Eleven arXiv areas and nine declared "families" collapse to
essentially one or two skills.

This is the finding that survives, and it is a **diversity** result, not a hardness
one. Banning tools does not fix it: if two questions both reduce to "translate to
constraints and propagate", a model that learns that once answers both, and a
40-question benchmark is a 2-question benchmark with 38 restatements.

## The caveat on that claim

Sharing a *mechanical* route does not strictly prove sharing an *insight* route. Two
problems can both be SAT-solvable and still require different ideas to crack by hand,
and the insight route is what a tools-free eval actually tests.

The measurement that would settle it: **take the one-sentence structural hint for
family A and give it to family B.** If it helps, they are the same question. That test
is not yet run, so treat "78% is one skill" as strongly indicated and not proven.

## What we still know is a real defect

Nothing in this audit. The genuine defects found in the corpus were found elsewhere and
are fixed: a self-reported `G6.pass` that was never cross-checked against the
`successes` on disk; a graphy detector reading dict key names instead of `render()`; a
surrogate gate guarded on a self-declared field, unreachable on 7 of 7 modules.

## Method note worth keeping

The attack panel must be chosen per problem, not from a fixed list. On `2112.06333` a
spectral attack was *measured to fail*: the planted quotient eigenvalue −4 sits inside
the random-regular bulk edge −2√7 ≈ −5.29, with zero overlap on all 8 seeds. That
family fell to DSATUR, not to spectral. "Run the domain attack" has to mean the right
one.
