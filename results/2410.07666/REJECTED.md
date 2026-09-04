# Rejected: *Computational Complexities of Folding*

Paper: David Eppstein, “Computational Complexities of Folding” (arXiv:2410.07666).

## Decision

This family must not ship as a hard generator. The run's final self-test has
`all_passed: false`: random-restart WalkSAT found a verifier-accepted witness on
all `8/8` shipping seeds.

## Family tested

The generated family is a discretised flat-folding signal-consistency CSP based
on the paper's NAE3SAT reduction. A witness assigns a Boolean state to each
variable signal, and every signed three-signal clause must be not-all-equal.
Instances are planted regular factor graphs, not full geometric crease
patterns: they omit crease coordinates, pleats, overlap order, nonintersection,
and a bounded-ply embedding.

The rejected shipping preset has `192` signals, variable degree `7`, and `448`
clauses.

## Breaking attack

The breaking attack is random-restart WalkSAT/min-conflicts with a `10%` noisy
move, capped at `32` restarts and `200n` moves per restart. It solved `8/8`
shipping instances in the adversary panel.

On the shipping instance used for the uniform-density sample (seed `314159`),
it produced a witness that passed the verifier in
`3.6501815889496356` seconds after `438,392` iterations and `12` started
restarts. Its configured iteration ceiling was `1,228,800`. A verified witness
within this budget is a direct failure of the intended hardness claim.

## Why the other signals were misleading

Uniform guessing found `0/200,000` valid complete assignments. That measures
only the hit rate of unguided samples from the `2^192` assignment space. It does
not measure whether local constraint violations provide an effective search
gradient. WalkSAT exploited exactly that structure, so low sampled density did
not imply computational hardness.

The oracle pool also gave a false sense of security. All `3` models failed on
the shipping preset: one returned no parseable answer after exhausting its
completion limit, while the other `2` returned assignments rejected at clauses
`C012` and `C001`. Those are single prompted attempts by general-purpose models,
not a domain-standard algorithmic lower bound. Their failure is outweighed by a
small conventional CSP heuristic succeeding on every tested shipping seed.

The other adversary-panel attacks—literal imbalance, left-to-right greedy,
the `5,000`-node DPLL cap, and signed spectral rounding—each scored `0/8`.
That only shows those particular attacks missed the solutions; WalkSAT's `8/8`
result is enough to reject the family.

## Defensible regime

No tested parameter regime supports presenting this planted family as hard.
It remains usable only when explicitly labelled as an easy diagnostic or
teaching CSP.

A future hardness candidate would need to implement the paper's geometric
crease-pattern construction rather than only its Boolean signal layer, operate
outside the paper's jointly small-ply/small-treewidth tractable regime, and pass
fresh local-search and SAT testing. None of those conditions rescues the family
tested in this run.
