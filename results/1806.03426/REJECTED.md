# Rejected family audit — arXiv:1806.03426

The attempted family fails **H on Track A**. It is not rescued by Track B.
The retained implementation is
`rejected_gen_1806_03426.py`; it is audit evidence, not a shippable generator.

## Paper result and candidate family

Király and Pálvölgyi define the degree-constrained acyclic orientation problem
in Section 1, Problem 2. Section 3.1, Theorem 10 proves NP-completeness for the
two-sided regime `k = l = 2` by reducing NAE-3-SAT to a skeleton/literal/clause
multigraph. Given a satisfying assignment, the forward direction of the proof
writes down a valid topological order in linear time.

The prototype inverse-generates a satisfying assignment, samples a connected
regular NAE-3-SAT formula around it, and applies exactly that theorem. Each
variable has equal positive and negative occurrence counts relative to the
plant, and the clauses are balanced between one and two planted-true literals.
Thus G is sound: the witness is known before the instance is built. V is also
sound: the checker expands the proof's topological order and recomputes every
predecessor/successor count with edge multiplicity, without reading the planted
answer.

The relevant easy-case warnings are Section 2, Theorems 2–4 (greedy or
polynomial algorithms for one-sided/strict regimes) and Section 3.1, Theorem 9
(`k = l = 1` via st-numbering). The prototype avoids those formal regimes, but
Theorem 10 supplies only worst-case NP-hardness; it says nothing about the
generated planted distribution.

## Failed hardness audit

The original prototype incorrectly called random-variable flips inside a
violated clause “WalkSAT.” A standard break-count version instead chooses, up
to noise, the flip leaving the fewest violated incident clauses. It solves all
8/8 shipping instances (`n=174`, 348 clauses) and all 8/8 instances at each
named tighter preset:

| preset | parameters | successes | observed wall time |
|---|---|---:|---:|
| easy (shipping) | `n=174`, degree 6 | 8/8 | 0.0040–0.1297 s |
| medium | `n=174`, degree 8 | 8/8 | 0.0073–0.0519 s |
| hard | `n=216`, degree 8 | 8/8 | 0.0123–0.0483 s |

At shipping, the median successful run used 2,118 flips and 26,874 incident
clause evaluations (median wall time about 0.0156 s). The range was 510–19,078
flips and 6,408–240,102 evaluations. The strongest G5 measurement recorded in
`selftest_report.json` also succeeds: 1,716 flips, 21,888 evaluations, about
0.010 s in the final run.
Consequently G5 and G6 are false even though 0/200,000 uniform assignment
guesses happened to work. The large answer space was not evidence of hardness.

## Why Track B does not rescue it

The successful mechanical route is a local-search heuristic, not a guaranteed
polynomial-time certificate algorithm, so it does not by itself supply the
efficient reference algorithm Track B requires. More importantly, there is no
shorter structural answer-finding route in this family. The paper's linear
174-sign/348-clause forward construction starts *after* a satisfying assignment
is known; counting those 174 sign placements as the “compact route” would assume
the witness that the solver is asked to find. The actual known route takes the
same thousands of flips and tens of thousands of clause evaluations measured
above, well over the 300-operation no-tool cap. Mechanical cost and legitimate
compact-route cost therefore have no useful compression gap.

This is not a rejection of Theorem 10 or of all possible generators from the
paper. It rejects this balanced planted distribution and the prior generic
“plant an ordering, add compatible edges” hypothesis. A future attempt would
need a theorem-backed hard distribution or a genuine Track B invariant whose
answer-finding route—not merely witness expansion—fits under 300 operations.
