# Rejected at Step 0: arXiv 1903.10618

Paper: Andrea Lincoln and Adam Yedidia,
[*Faster Random k-CNF Satisfiability*](https://arxiv.org/abs/1903.10618).

## Decision

No family from this paper clears **G, H, and V** under either track.  The prior
triage proposal—sample an assignment and then sample clauses that it satisfies—is
exactly the paper's planted distribution, so it clears G by inverse generation and
V by direct clause evaluation.  It does **not** clear H on Track A: the paper
explicitly warns that this distribution is biased toward formulas with many
solutions and tends to be easier than the uniform satisfiable distribution.  The
paper proves an algorithmic upper bound, not distributional hardness of planted
instances.

I also audited the strongest Track B reformulation supplied by the paper: give a
formula together with a nearby assignment and ask for the short correction set.
Lemma 3.1 gives an efficient fixed-radius algorithm, but that algorithm is also the
shortest paper-backed route.  There is no mechanical/compact compression gap, and
the route requires tens of thousands of literal inspections even at the smallest
radius that can plausibly pass the random-guess gate.  It therefore fails Track B H
and mandatory gate G9(c).

This is a Step-0 rejection.  No generator, self-test report, README, or oracle
transcript was created; doing so would claim gates for a family already ruled out.

## What the full paper actually says

Section 2 fixes details hidden by the abstract.  A clause contains exactly `k`
variable draws **with replacement**, so repeated variables and tautological clauses
are allowed.  `D_replace(n,k)` is uniform over the `n^k 2^k` signed clauses.
`D_pa(m,n,k,a)` chooses every clause independently and uniformly from the
`(2^k-1)n^k` clauses satisfied by `a`.  The paper states the equivalent inverse
sampler explicitly: choose `a` first, then choose `m` clauses uniformly from the
clauses it satisfies.

The native random-SAT theorem is about `D_Phi(n,k)`, where the clause count is
Poisson with mean `d_k n` at the satisfiability threshold.  Section 2 gives only
the asymptotic enclosure

```text
2^k ln(2) - (1+ln(2))/2 - epsilon_k
    <= d_k <=
2^k ln(2) - (1+ln(2))/2 + epsilon_k,
```

with `epsilon_k -> 0`.  The large-`k` branch depends on an unknown constant `k*`.
Section 3 says explicitly that Algorithm 1 is non-constructive for this reason.

Theorem 3.3 is an **upper bound**: `alpha-SAMPLEANDTEST` solves threshold random
`k`-SAT in time
`2^(n(1-Omega(log^2(k)/k)))`, with one-sided error.  Its certificate-producing
step is not a hidden shortcut.  It samples assignments, counts their satisfied
clauses, and runs the Lemma 3.1 bounded-Hamming search near promising samples.
For small `k`, Lemma 3.2 instead invokes the exponential worst-case Dantsin local
search algorithm.  Section 8 says improved small-`k` behavior was seen in
simulations and calls a proof for `k=3,4,5` a possible future direction.

The easy regimes are also explicit:

- The Introduction says that away from the threshold, clause density alone predicts
  satisfiable versus unsatisfiable with high probability, and cites polynomial-time
  algorithms there.
- The Introduction says the planted distribution tends to be easier than the
  uniform distribution and cites statistical-query recovery of the planted
  solution when `m = Omega(n log n)`.
- Lemma 5.7 transfers sufficiently small *failure probability bounds* from the
  planted model to the uniform model.  It is an analysis reduction, not a theorem
  that a privately planted formula is hard.
- Section 3, Lemma 3.1 makes the nearby-assignment problem fixed-parameter
  tractable: radius `r=alpha*n` costs `k^r` branches.

These statements are why worst-case NP-completeness of `k`-SAT cannot be used as
the hardness basis for the proposed generated distribution.

The cited recovery result is relevant to this precise plant, not merely to some
other planted law.  If clause signs are uniform over all patterns except the one
falsified by the plant, then a literal agrees with the plant with probability
`2^(k-1)/(2^k-1) > 1/2`; the distribution already has a first-order bias.  The
paper's cited work by [Feldman, Perkins, and
Vempala](https://arxiv.org/abs/1311.4821) formalizes this as distribution
complexity one and gives exact recovery once enough samples cover every variable.
This does not prove a
polynomial solver at threshold-scale `m=Theta(n)`, but it does rule out treating
the naive plant as a quiet or high-complexity plant.  More importantly for this
task, the given paper supplies no theorem supporting hardness of the remaining
threshold-scale distribution.

## Candidate 1: recover the planted assignment

The proposed generator would be faithful to `D_pa`: choose a uniformly random bit
vector `a`, then choose each signed clause uniformly conditional on `a` satisfying
it.  The answer is JSON-native as a bit vector, and a checker can accept any
satisfying assignment by evaluating every literal without reading the plant.

That establishes only G and V.  It does not establish Track A H.  The paper says
the planted law is easier and offers no theorem or parameter regime in which this
generated distribution has no efficient recovery algorithm.  The main theorem
does not repair the gap: it concerns the uniform threshold law and gives an
exponential algorithm rather than a lower bound.  At the practically renderable
small values of `k`, the paper supplies only simulations; at its formal large-`k`
regime, `k*` and the exact threshold are not constructive, while approximately
`2^k ln(2) n` explicit clauses quickly make the prompt itself non-hand-scale.

Track B does not rescue this candidate.  The paper's certificate-producing route
is the exponential sample-and-search algorithm.  There is no shorter invariant
that recovers a complete planted assignment.  Literal-frequency recovery is an
additional algorithmic attack, not a guaranteed compact route at threshold
density.  Adding parity blocks, beacons, checksums, or a low-description assignment
would manufacture structure absent from the paper's random model and would test
that added encoding instead.

Moving to `m=Omega(n log n)` makes exact recovery polynomial, as the Introduction
notes, but still does not create a Track B family.  The mechanical method accumulates
literal statistics over the `mk` displayed occurrences; the putative compact route
must accumulate the same statistics.  Their costs are both `Theta(mk)`, so there is
no no-tool compression gap.  At threshold scale the paper instead offers the
exponential search above, which is not Track B's efficient-reference setting.

## Candidate 2: bounded-Hamming correction

The closest possible Track B task uses the exact objects of Lemma 3.1.  Give a
`k`-CNF formula and a displayed assignment promised to be within radius `r` of a
solution; ask for at most `r` variable indices to flip.  Inverse generation is
immediate: sample the solution and clauses first, then flip `r` positions.  The
checker flips a submitted set and evaluates the formula exactly.

This candidate has a large short-answer language.  For example, at `n=192` and
`r=3`, the structure-aware language contains

```text
sum(C(192,i), i=0..3) = 1,179,809
```

candidates.  Even under the optimistic assumption of one valid correction, a
uniform guess succeeds with probability about `8.476e-7`.  Radius two would have
only 18,529 candidates and fail G4 immediately.

The discriminating certificate question has a decisive answer: Lemma 3.1 produces
the correction by branching on the first falsified clause, trying each of its `k`
variables, and repeating to depth `r`.  Its complexity is `O(m k^r)` clause work
(`k^r` search leaves).  For fixed `r`, that is an efficient algorithm, so this
cannot be Track A.

I implemented the lemma directly as a disposable measurement (not as a generator)
on eight exact planted draws with `n=192`, `k=4`, `m=10n`, and `r=3`.  The `m/n=10`
scale matches the paper's displayed `k=4` experiment.  All eight instances were
solved, as expected.

| measured quantity | result |
|---|---:|
| reference solves | 8 / 8 |
| theoretical search-tree nodes `1+4+4^2+4^3` | 85 |
| observed nodes | 8--74; median 38 |
| observed literal inspections | 11,471--51,815; median **30,118** |
| observed wall time | 0.00067--0.01012 s; median **0.00261 s** |

The putative compact route is the same routine: locate a falsified clause, branch
on one of its literals, and rescan until all clauses are satisfied.  It therefore
also costs a median 38 branch nodes and 30,118 exact Boolean inspections.  Counting
only branch nodes would hide the work required to determine which clauses are
false.  Even charging a whole four-literal clause test as one operation gives at
least `30,118/4 > 7,500` inspected clauses at the median, still far above 300.  The
paper supplies no independent invariant that identifies the three correction
indices.  Thus the mechanical cost and compact-route cost are
comparable—they are the identical algorithm—and the route exceeds G9(c)'s
300-operation cap by two orders of magnitude.

At radius four, the gap gets worse rather than more informative.  In the same
regime the candidate language has 56,050,289 elements, while the direct lemma
implementation used a median 238.5 nodes and 160,317 literal inspections across
eight seeds.  Increasing `n` only lengthens the formula scan; it does not create a
compact route.

## Other native objects do not help

Algorithm 1's other central object is `NumClausesSAT(phi,a)`.  Asking for that
exact integer or fraction would have a cheap witness checker, but the certificate
is produced by the same `Theta(mk)` direct evaluation the checker performs.  On
the paper's IID random clauses there is no exact symmetry or telescoping identity
that shortens it.  Artificially inserting complete sign orbits or repeated
weighted blocks would create a Track B arithmetic puzzle from builder-added
structure, not a family supported by the paper's random distribution.

Certified unsatisfiability is no better.  Planting a satisfying assignment gives
no negative instances, and the paper does not provide a bounded refutation format
or inverse construction of random threshold formulas with a carried refutation.
Running a SAT solver to obtain such a proof would violate G.

## Gate audit

| requirement | outcome | reason |
|---|---|---|
| G | passes for planted positive instances | Section 2 gives the inverse planted sampler |
| V | passes for assignments/correction sets | exact Boolean clause evaluation |
| H, Track A | **fails** | no hardness theorem for the planted law; the paper explicitly identifies it as easier, and fixed-radius correction has the Lemma 3.1 algorithm |
| H, Track B | **fails** | the nearby-assignment algorithm is both the mechanical and shortest paper-backed route; no compression gap exists |
| G9(c) | **fails** for the only plausible Track B task | median 30,118 literal inspections at the smallest radius with a million-candidate language |
| overall | **rejected at Step 0** | no single native family satisfies all three gates under either track |

The empirical timings above do not claim a universal SAT lower bound.  They serve
only the required Track B cost comparison.  The rejection rests on the paper's
own distribution definitions, easy-regime statements, and explicit algorithms—not
on those timings alone.
