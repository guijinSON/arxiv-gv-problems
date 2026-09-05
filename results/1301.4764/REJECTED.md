# Rejected: [arXiv 1301.4764](https://arxiv.org/abs/1301.4764)

No acceptable family was found for this benchmark. The attempted native
three-design family passes **G** by composition of identities and **V** by exact
block-set intersection, but it fails **H**. Track A is not supportable, and the
implemented Track B candidate was solved throughout the required hardening
ladder.

## Paper triage

Section 1 defines an `S(2,4,v)` as a set of four-point blocks covering every
point-pair exactly once and defines the three-way intersection as the blocks
common to all three designs. The paper's decisive results are:

- Theorem 1.1(2) completely classifies the feasible intersection numbers for
  every admissible `v >= 49`. A feasibility question in that regime is a
  constant-time spectrum lookup, not a hard family.
- Theorems 3.1 and 3.2 construct triples by weighting and filling, and make the
  common-block count an explicit sum of ingredient counts.
- Lemmas 4.1 and 4.5 give the required `S(2,4,13)` and `4-GDD` ingredients as
  fixed permutation tables. Theorem 5.1 uses exactly the resulting formula
  `sum(alpha_i) + sum(beta_j)`.

Thus an explicitly expanded triple has a polynomial-time standard algorithm:
hash two block sets and scan the third. The paper supplies no hardness theorem
for finding or counting the intersection on any generated distribution, so
declaring Track A would be false.

## Attempted Track B family

The preserved prototype constructs a finite-geometry `4-GDD` of type `3^u`,
weights every point by four using Lemma 4.5, and fills every group using Lemma
4.1. Its answer is the two-component profile `(outer common blocks, filling
common blocks)`. The certificate is known by construction; `verify` independently
recomputes every fixed ingredient intersection and the two weighted sums without
reading `inst["answer"]`.

At the candidate shipping preset (`n=5`, `v=4093`), the mechanical reference
algorithm generated **4,187,139 blocks**, performed **2,791,426 hash membership
probes**, and took **25.176041 seconds** on this host: **6,978,565 recorded
operations** in total. The intended compact route used the paper's additive
decomposition and was budgeted at **195 small-block membership and integer
operations**. These numbers show why the existence of a polynomial algorithm
was not itself a rejection: there was a real mechanical/compact gap, so Track B
was tested first.

It nevertheless failed Track B. The bare `harden.py` run recorded:

| escalation round | parameters | scored oracle successes |
|---:|---|---:|
| 0 | `n=2, period_cap=15` | 2/3 |
| 1 | `n=4, period_cap=255` | 3/3 |
| 2 | `n=5, period_cap=600` | 2/3 |
| 3 | `n=6, period_cap=1200` | 2/2 before quota exhaustion |

A level is defeated when any scored oracle solves it, so all four tested levels
were defeated. The third round-3 slot was never scored: four redraws returned
HTTP 403 `Key limit exceeded`. Those errors are preserved in the transcript and
are not counted as failures.

There is no meaningful unused escalation axis in this prototype. Regardless of
`n` and `period_cap`, its run table contains at most the same five outer and
seven filling ingredients. Increasing `n` only enlarges the expanded block sets
and the decimal multipliers; it does not lengthen or conceal the compact route.
Escalating further would test large-integer bookkeeping rather than discovery of
the paper's decomposition.

Other native formulations do not repair H within the output contract. Asking
whether an intersection size exists is the Theorem 1.1 lookup. Asking for a
Theorem 5.1 decomposition exposes fixed coin sets containing unit increments and
has a direct greedy construction. Asking for all blocks of three large designs
exceeds the answer cap, while asking for their count returns to the defeated
Track B family above. The paper's nonexistence statements for trade volumes
`1,...,7` are theorem appeals rather than bounded executable certificates in
the paper, so they do not supply a witness family either.

The audited prototype is retained as
`rejected_gen_1301_4764.py`; `llm_loop_transcript.jsonl` is the unedited
script-owned evidence from the final bare run.
