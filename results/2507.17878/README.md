# Verified planted monotone 1-in-3-SAT generator

This directory turns Bedert, Nakajima, Okrasa, and Živný's [*Strong
Sparsification for 1-in-3-SAT via Polynomial Freiman-Ruzsa*](https://arxiv.org/abs/2507.17878)
into a witness problem.  A solver receives a Boolean variable set and positive
three-variable clauses, and must list the variables set to 1 so that **exactly
one** variable in every clause is 1.  The checker substitutes the listed set and
counts to one in each clause, so verification is exact and linear in the input.

## Why this is a credible hard family

Section 1 gives the exact monotone 1-in-3 relation and treats its exact search
problem as NP-hard.  In the dual view, variables are sets of clauses and a
satisfying assignment is an exact cover.  The nearby cubic regime is formally
NP-complete: Gonzalez's RXC3 result has three-element sets and every element in
exactly three sets ([TCS 38, 1985, Appendix A](https://doi.org/10.1016/0304-3975(85)90224-5)).
Our generated instances keep clause frequency three, use sets of size two or
three, are connected, and have growing size and parity nullity.  This particular
planted random distribution does **not** come with an average-case hardness
theorem; its evidence is the gate suite and the independent oracle panel below.

The easy results in the paper were accounted for.  Section 3 turns each clause
into a GF(2) equation while finding variables safe to merge; Theorem 1.2 only
strongly sparsifies and does not find an assignment.  Accordingly G4 samples
from the *entire affine parity-solution space*, and the generator avoids a
full-rank parity system.  Theorem 4.36 is only a monotone/non-monotone
sparsification reduction.  Section 5 and Theorem 5.52 obtain an optimal strong
sparsifier by exponential solution enumeration, not a polynomial search
algorithm.  No assignment-search FPT algorithm or closed form is given.

Plants and decoys have the same occurrence distribution: 45% occur three times
at the shipping level and the rest twice.  Stubs, labels, clause order, and
within-clause positions are shuffled.  Hardness comes from scale and crowding,
not an element-level marker.

## Worked example (`easy`, seed 0)

```text
MONOTONE 1-IN-3-SAT WITNESS PROBLEM

There are 24 Boolean variables x1,...,x24.
A variable has value 0 (false) or 1 (true). Each clause below lists
three distinct variable indices and contains no negations. An assignment
satisfies a clause exactly when exactly one of its three variables has
value 1; the other two must have value 0. Find one assignment satisfying
every clause.

Clause order and the order of indices within a clause do not matter.
There are 19 clauses:
C01: 3 16 23
C02: 15 21 24
C03: 22 21 10
C04: 19 12 6
C05: 22 6 11
C06: 4 1 6
C07: 20 18 14
C08: 19 13 1
C09: 24 18 14
C10: 20 7 13
C11: 10 3 1
C12: 23 4 2
C13: 17 16 12
C14: 16 5 8
C15: 15 2 11
C16: 5 9 7
C17: 5 8 20
C18: 10 12 19
C19: 23 17 9

Output the complete set of indices whose variables have value 1. All
indices must be integers in the inclusive range 1..24. The
list must be nonempty, must contain no repeated index, and may have any
length. Variables omitted from the list are assigned 0. Index order does
not matter. Do not include brackets or explanatory text inside the tags.

Give your final answer inside <answer></answer> tags, as a comma-separated
list of variable indices.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

Witness: `<answer>1, 7, 8, 12, 15, 18, 22, 23</answer>`.
`verify(inst, inst["answer"]) == (True, "ok")`.  Dropping 23 gives
`(False, "clause C1 has zero true variables")`.

## Difficulty presets

| Preset | `n` | Variables | Clauses | Degree-3 share | Status |
|---|---:|---:|---:|---:|---|
| easy | 8 | 24 | 19 | 35% | Local gates pass; oracle solved 3/3 |
| medium | 16 | 48 | 38 | 40% | Local gates pass; oracle solved 3/3 |
| **hard** | **96** | **288** | **235** | **45%** | **Ships; oracle solved 0/3** |

The easy and medium presets were rejected by the hardening oracle, not by a
correctness gate.  `SHIPPING_DIFFICULTY` is `hard`.

## Mandatory gates

| Gate | Measured result | Pass |
|---|---|:---:|
| G1 planted verifies | 9/9 preset/seed instances | yes |
| G2 corruptions | 5/5 rejected, 5 distinct reasons | yes |
| G3 round trip | realistic fenced/prose response parsed, 96 indices | yes |
| G4 structured guess | 0/200,000 hits from uniform GF(2) solutions; dimension 53 | yes |
| G5 sparse | 2 solutions among `2^18`; fraction `7.629e-6` | yes |
| G6 attacks | outlier, greedy, parity representative, 64 random restarts: each 0/8 | yes |
| G7 scaling | 288→576 variables, 235→470 clauses; plant verifies | yes |
| G8 canonical key | 60/60 invariant, 20/20 real transforms, 20/20 unrelated distinct | yes |

## Oracle hardening loop

All calls used medium reasoning effort.  `solved` means the returned witness
passed this module's verifier.

| Preset | Seed | Oracle | Solved | Reason |
|---|---:|---|:---:|---|
| easy | 1824471406 | Gemini 3.1 Pro Preview | yes | `ok` |
| easy | 1635793508 | GPT-5.6 Terra | yes | `ok` |
| easy | 324357622 | Grok 4.6 | yes | `ok` |
| medium | 1178727728 | GPT-5.6 Terra | yes | `ok` |
| medium | 369504376 | Claude Sonnet 5 | yes | `ok` |
| medium | 1778293147 | Gemini 3.1 Pro Preview | yes | `ok` |
| hard | 588807854 | GPT-5.6 Terra | no | parsed; both empty and crowded clauses |
| hard | 681146659 | Claude Sonnet 5 | no | no content after the 32k reasoning budget |
| hard | 106364903 | Grok 4.6 | no | parsed; C5 had zero true variables |

The script verdict is `hardened`, at the named hard preset after two
escalations.  The transcript and master seed are in
`llm_loop_transcript.jsonl` and `.meta.json`.

## Use

```python
from gen_2507_17878 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=1234, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>1, 7, 12</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh verified instances with:

```bash
bash scripts/emit.sh 2507.17878 20 hard
```

## Caveats

- The hard claim for this *distribution* is empirical, not an average-case
  theorem.  RXC3 proves a closely related worst-case cubic regime hard, but it
  does not prove this planted 2/3-degree mixture hard.
- G4 is uniform over all assignments satisfying the obvious global GF(2)
  relaxation.  Its 0/200,000 result bounds that prior's observed hit rate; it is
  not a runtime lower bound and says nothing about a targeted search heuristic.
- One of the three hard oracle failures exhausted its 32k completion/reasoning
  budget without emitting text.  The harness counts this as failure, but it is
  weaker evidence than the other two parsed, invalid witnesses.
- The panel did not run a state-of-the-art SAT/XOR solver, spectral recovery,
  belief propagation, simulated annealing, or random greedy with far more than
  64 restarts.  Higher-order planting signatures may remain despite matched
  per-variable degrees.
- All-degree-2 instances risk cycle/matching structure; dense all-degree-3
  plants risk a nearly full-rank GF(2) shortcut.  The shipping mixture steers
  between these easy regimes, but no theorem identifies 45% as a threshold.
- `canonical_key` is a bipartite incidence-graph color-refinement invariant.
  It is invariant under every relevant reordering tested, but graph isomorphism
  is not solved exactly; rare nonisomorphic regular instances can collide.
  Other satisfying witnesses may exist and are deliberately accepted.
