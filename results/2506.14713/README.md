# Linear literal-planar 3-SAT reconfiguration

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT reconfiguration |
| Certificate | integer tuple (a sequence of variable flips) |
| Intended intuition | invariant: assignments encode orientations satisfying a minimum-inflow rule |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 7.1, Theorem 7.1 |

This generator instantiates Desbois, Sankur, and Schwarzentruber, [*Linear
Planar 3-SAT and Its Applications in Planning*](https://arxiv.org/abs/2506.14713).
A solver receives a linear literal-planar 3-CNF and two satisfying assignments.
It must give exactly 160 single-variable flips taking the start to the goal while
every intermediate assignment still satisfies the formula. Checking is cheap and
exact: flip one bit, reevaluate the affected Boolean clauses, and compare the final
bitstring with the goal.

The certificate is known by construction. The generator first samples a legal walk
of orientations in a planar cubic nondeterministic constraint-logic (NCL) graph. It
then applies the paper's Section 7.1 encoding: one OR node gives one 3-clause, while
one AND node gives two 2-clauses sharing only its heavy-edge literal. Lemma 7.1 makes
legal orientations exactly the satisfying assignments, and the proof of Theorem 7.1
makes edge reversals exactly variable flips. Variable names, polarities, clauses, and
literal order are subsequently randomized. No solver produces the planted path.

## Why Track A is credible

Theorem 7.1 proves Linear Literal-Planar 3-SAT Reconfiguration PSPACE-complete on
exactly the planar-cubic-NCL reduction image used here. Shipping instances use an
80-vertex planar cubic base, typically about 234 Boolean variables and 270 clauses,
and a 160-flip bound. The result is worst-case, so it does not by itself prove this
generated distribution hard; the measured evidence is that four attacks all failed
on 8/8 shipping instances. The strongest, memoized A* with an admissible Hamming
bound, exhausted 100,000 states per instance: 800,000 states and 153.37 seconds in
the final panel. A separate shipping baseline exhausted 100,000 states in 23.21
seconds.

The easy result that had to be separated from certificate search is Section 5's
polynomial-time construction of a separating literal cycle for the reduction image.
That algorithm certifies literal-planarity; it does **not** find a reconfiguration
path. The original smaller `n=40`, 80-flip rung was discarded after A* solved 1/8
instances. The ladder was moved to `n=80` without exceeding the answer cap.

## Worked demo

The demo (`seed=0`) has 24 variables, 28 clauses, and six moves. A person can solve
it on paper by tracing only the clauses containing the currently flipped variable;
it is also small enough to check line by line.

```text
Find a reconfiguration path between two satisfying assignments of a Boolean formula.

Definitions and promise.
There are 24 Boolean variables x1 through x24.
A positive integer k in a clause means xk; a negative integer -k means NOT xk.
A clause is true when at least one of its listed literals is true, and the formula is the conjunction of all clauses.
The formula is a 3-CNF: every clause has at most three literals.
It is linear: each clause shares an identical signed literal with at most one other clause, and any such pair shares at most one literal.
It is promised to be literal-planar: its bipartite literal-clause graph admits a planar embedding with a cycle through every signed literal, with opposite-literal edges on one side and all clause edges on the other.
A move flips the truth value of exactly one variable. The assignment after every move must satisfy every clause.
The leftmost bit of an assignment string is x1, the next is x2, and so on.

Start assignment: 000001110010000101100110
Goal assignment:  100001110000000101100110

Clauses (one bracketed disjunction per line):
[-17, -6]
[8, -23]
[-13, 2]
[17, -3]
[3, -21]
[9, -10]
[12, -15]
[4, -9]
[-11, -3]
[14, 22, -16]
[-5, -22]
[13, 20, 6]
[1, 8]
[-12, 3]
[-15, -4]
[10, -20]
[-20, -1]
[-2, -22]
[-6, 18]
[7, 19]
[-8, -24, -7]
[7, 5]
[15, 24, -14]
[23, 9]
[-18, 16]
[-9, 21]
[-19, -13]
[11, 16]

Give a sequence of exactly 6 moves. Each move is a variable number from 1 through 24; repetitions are allowed and order matters.
The final assignment after all moves must equal the displayed goal exactly.
Give your final answer inside <answer></answer> tags, as a comma-separated list of variable numbers.
Example: <answer>3, 17, 17, 42</answer>
Output nothing else inside the tags.
```

Its answer and two checker outcomes are:

```python
>>> inst["answer"]
[19, 1, 19, 1, 11, 1]
>>> verify(inst, inst["answer"])
(True, "ok")
>>> verify(inst, inst["answer"][:-1])
(False, "too short: expected exactly 6 moves, got 5")
```

## Difficulty presets

Counts are for seed 0. The witness stays at 160 moves after `easy`; later rungs grow
the ambient formula and tighten the AND-node density rather than lengthening it.

| preset | base `n` | variables | clauses | moves | endpoint Hamming distance | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 24 | 28 | 6 | 2 | hand-scale example |
| easy | 80 | 234 | 270 | 160 | 24 | **ships; oracle 0/3** |
| medium | 100 | 288 | 330 | 160 | 24 | available, not needed |
| hard | 120 | 351 | 405 | 160 | 30 | available, not needed |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses, JSON answers, and exact linear-3-CNF checks |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five reason classes |
| G3 | pass | fenced, prose-surrounded output round-trips |
| G4 | pass | 0/200,000 endpoint-parity-aware guesses; candidate support has 1,076 bits |
| G5 | pass | shipping density 0/200,000; demo exact count 512/44,912; A* 100,000 states / 23.21 s |
| G6 | pass | outlier order, clause-slack greedy, 96 random restarts, and A* each 0/8 |
| G7 | pass | doubling base `n` gives 450 variables and still verifies with 160 answer elements |
| G8 | pass | 20/20 relabelling invariance, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 576 chars, about 144 tokens, 160 atoms, 160 intended flip operations |

## Oracle loop

The repository-owned bare harness held the shipping `easy` preset. The one unparsed
reply explicitly denied that a path existed and supplied no answer block, so it is
not a parser false negative.

| model | seed | solved | checker result |
|---|---:|---|---|
| Gemini 3.8 Flash | 1274367155 | no | clause violation at step 1 |
| GPT-5.6 Terra | 1642391403 | no | no answer; incorrectly claimed the start was unsatisfying |
| Gemini 3.8 Flash | 32418192 | no | 157 moves rather than 160 |

## G9 diagnostic arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted − placebo = 0.0`. Naming the hidden minimum-inflow interpretation bought
the oracle nothing at this preset, so the experiment does not isolate the claimed
invariant as the sole difficulty. Answer size is 576 characters / 160 atoms, and the
intended certified route is 160 exact flips, all within G9(c).

## Use

```python
from gen_2506_14713 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["easy"])
prompt = render(inst)
raw = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = parse_answer(raw)
assert verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2506.14713
```

## Caveats

The PSPACE theorem is worst-case; hardness of this sampled expanded-prism
distribution is empirical, not a theorem. The random-candidate prior enforces the
fixed length, variable range, and endpoint parity, but its pair-insertion sampler is
not uniform over that support; 0/200,000 does not describe every informed prior.
Industrial SAT/SMT model checking, BDD reachability, and a specialized bounded-width
dynamic program were not tested. The 100,000-state A* cap is substantial but finite.

The paper formally supplies a literal cycle/embedding with its literal-planar input;
the rendered benchmark states that property as a theorem-backed promise because the
cycle is irrelevant to checking a flip path. The required exact 160-move format is a
bounded witness subfamily; a valid path of another length is outside this declared
certificate language. Finally, `canonical_key` is a signed-incidence
Weisfeiler-Lehman invariant, not a complete graph-isomorphism canonizer, so rare
nonisomorphic collisions remain possible.
