# Rejected Track-A family for arXiv:1003.3704

## Decision

The attempted inverse-generated 5-colourable Monotone NAE-3SAT family fails
**H on Track A**.  G (inverse generation with a planted truth partition) and V
(one exact clause scan) both hold.  The failure is distributional hardness, not
the witness rule and not the paper's worst-case theorem.

Section 2.1 defines the native problem and says the 4-colourable case is in P.
Section 4, Theorem 2 proves NP-completeness for `k >= 5`, even when each
variable occurs at most seven times.  The attempted shipping distribution used
exactly that parameter regime—180 variables, 420 clauses, five hidden colours,
and exactly seven occurrences per variable—but the theorem is worst-case and
does not imply that the balanced planted distribution is hard.

## The attack that rejects it

The original 10,000-node NAE-DPLL panel reported 0/8, but that cutoff was too
weak.  On the same 180-variable shipping distribution, the same exact DPLL with
NAE unit propagation and a 50,000-node budget recovered verified witnesses on
2 of 3 audited seeds:

| seed | outcome | nodes | clause scans | wall clock |
|---:|---|---:|---:|---:|
| 800 | budget exhausted | 50,001 | 65,642,111 | 24.43 s |
| 802 | **solved** | 31,963 | 41,627,885 | 10.15 s |
| 807 | **solved** | 40,162 | 51,239,295 | 12.62 s |

Track A requires the domain-standard algorithm to have zero successes, so one
success is disqualifying.  The earlier `hardened` oracle verdict at this preset
does not rescue the claim: the prompt explicitly separates model failure from
algorithmic hardness.

## Why this is not relabelled Track B

DPLL is a worst-case exponential method, not the efficient reference algorithm
that Track B requires.  More importantly, this planting has no genuinely
compact route: after noticing the aggregate ten-role construction, the solver
still has to recover 180 randomized vertex memberships.  The only stated
post-insight route was 180 membership writes, while the actual mechanical
recovery seen above costs 31,963–40,162 search nodes and 41.6–51.2 million
clause scans.  There is no short invariant/change-of-variables procedure to
contrast with that computation, so Track B would be a false label rather than
a way around the failed Track-A claim.

## Escalation audit

A 240-variable, 560-clause variant (still exactly seven occurrences and within
the 256-atom answer cap) exhausted 50,001 DPLL nodes on all eight seeds 800–807;
the measured clause-scan counts ranged from 89,885,296 to 93,573,951.  It is not
shipped because every shipping gate must be evidenced at the shipping preset.
The OpenRouter account reached its total key limit while running the placebo
arm, so the required new bare and structural-hint oracle runs at 240 variables
could not be produced.  Rejecting the 180-variable claim is mandatory; treating
the unaudited 240-variable rung as shipped would be equally dishonest.

This is therefore a rejection of the **attempted generated distribution**, not
a claim that no future generator from Theorem 2 can work.  A future run with a
fresh oracle budget should restart at the 240-variable rung and should also test
a modern external CDCL solver, belief propagation, and a stronger planted-CSP
spectral/tensor method before making a Track-A claim.

## Retained evidence

The built module is retained as `rejected_gen_1003_3704.py` after the final
strengthened self-test, as required.  The original script-owned bare transcript,
the complete 0/3 hinted transcript, and the partial placebo transcript are also
kept.  The placebo file contains the provider timeout and HTTP 403 key-limit
records rather than invented attempts.
