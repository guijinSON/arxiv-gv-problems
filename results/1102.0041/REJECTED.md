# Rejected: arXiv:1102.0041

This paper was read in full before the decision.  The exact object is the Full
Multiset Ordering problem in Section 2, Problem 1 of Battaglia, Grossi, and
Scutellà, [“Consecutive Ones Property and PQ-Trees for Multisets: Hardness of
Counting Their Orderings”](https://arxiv.org/abs/1102.0041).  A multiset occurs
only when it is exactly the multiset of a contiguous substring.  Theorem 16
proves #FMO #P-complete and Corollary 17 proves the general decision problem
NP-complete, through the Section 4 reduction from Hamiltonian path.

## Decision

The attempted family passes G and V but fails **H on both tracks**.

- **G passes.**  The retained prototype inverse-generates a word `pi + pi`
  and takes certified contiguous substring-multisets from it.  It never solves
  its own instance.
- **V passes.**  A candidate word is checked exactly by multiplicity counting
  and rolling exact window comparisons.
- **H fails on Track A.**  Every displayed requirement in the prototype is one
  copy of every alphabet symbol plus an “excess” set `E_i`.  Solving ordinary
  set-C1P for the family `{E_i}` produces an ordering `pi`; doubling it produces
  a valid #FMO witness.  Section 1.2 explicitly states that Booth–Lueker
  PQ-trees find such a set ordering in linear time.  Theorem 16 and Corollary
  17 concern the unrestricted multiset problem and do not make this generated
  distribution hard.
- **H also fails on Track B.**  At the attempted shipping preset `p=83,
  m=56`, set-C1P sees only `56 * 3 = 168` incidences and 83 symbols.  The
  theorem-backed mechanical route is linear in these 251 input items, followed
  by 166 output writes.  The retained compact cubic route was instrumented at
  285–292 exact arithmetic operations, also followed by the same 166 output
  writes.  These routes are the same scale; the compact route is not a
  compression of a by-hand-infeasible mechanical computation.  This is exactly
  the “compact route no shorter than the mechanical one” rejection condition.

The earlier adversary panel was therefore invalid: it tested frequency,
greedy, overlap, restart, and modular-step probes but omitted the paper's own
domain-standard set-C1P/PQ-tree algorithm.  Adding that algorithm gives a
successful attack by construction.  As an empirical cross-check, the
script-owned hardener made three independent scored calls at the `easy` preset;
all three returned valid witnesses (28.76 s, 159.95 s, and 115.85 s).  The run
was stopped before further escalation because the STEP-0 algorithmic test had
already disproved the claimed Track-B gap.  Those partial records are retained
as `rejection_easy_oracle_transcript.jsonl`.

## Why another paper object was not substituted

The other direct options do not clear all three gates:

- Asking for an arbitrary frontier of one PQ-tree is trivial: read any current
  child order in linear time.  Asking for the *number* of distinct frontiers is
  the paper's #P-complete problem, but the numeric count has no finite exact
  witness that this checker can validate cheaply without redoing the count.
- Lemma 11 in Section 4 can transport a known Hamiltonian path to an #FMO word,
  so it supplies G.  The paper supplies only worst-case NP/#P hardness, however;
  it gives no inverse-generatable average-case-hard distribution of Hamiltonian
  graphs.  Planting a path does not establish Track A, and inventing an unrelated
  structured graph promise merely to obtain a Track-B puzzle would move the
  hardness source outside this paper.

The prototype is preserved as `rejected_gen_1102_0041.py`, together with its
local reports and oracle records, so this decision can be audited or reopened.
