# Mahjong Solitaire group-pairing generator (arXiv:1203.6559)

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style three-way pairing search |
| Certificate | integer tuple (one ternary pairing code per tile group) |
| Intended intuition | constraint propagation through directed precedence cycles |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This module turns Michiel de Bondt's [*Solving Mahjong Solitaire boards with
peeking*](https://arxiv.org/abs/1203.6559) into an unlimited family of isolated-stack
boards.  Every tile group has four copies.  The solver chooses one of the three
perfect pairings of those copies, for every group, so that all chosen matches can
be removed in some legal order.

The generator samples the certificate first: two removal events per group are put
in a hidden global order, their tiles are placed in distinct stacks at that order,
and then event times, tile IDs, group IDs, and stack IDs are forgotten or shuffled.
It never solves the finished board.  The checker contracts every submitted tile
pair, turns each top-to-bottom stack adjacency into a directed edge, and runs Kahn's
acyclicity check.  An acyclic graph is exactly a replayable removal order, so the
check is exact, linear-size, and accepts any valid pairing rather than only the
plant.

## Why Track A

Section 2, Theorem 3 proves NP-completeness even for isolated height-three stacks
of forms `aab` and `abb`.  The shipping distribution has 192 groups in isolated
height-eight stacks.  It deliberately avoids Theorems 5 and 7: initial layouts of
isolated stacks of heights one and two are always solvable, and the residual case
is characterized by blocked cycles.

Section 3 supplies the domain-standard search: recursively assign one of three
group pairings, run the relaxed pruning scan, and prioritize critical groups.  The
bounded implementation here exhausted 256 nodes on each of eight shipping seeds
(2,048 total, 98.79 s) without a witness.  A construction-aware depth attack is
uncomfortably informative—71.81% of individual planted codes—but a 3,000-step
cycle-score repair failed on all eight shipping seeds.  The former `n=144` hard
preset was discarded because that same repair succeeded on 3/8 seeds.

## Worked demo

The `demo` preset is hand-scale.  Its complete seed-0 instance is:

```text
There are groups G0..G5.  In each stack the first tile is on top.
S0: T7:G1 T5:G0 T18:G3 T13:G5
S1: T9:G1 T3:G0 T19:G5 T16:G2
S2: T0:G3 T10:G5 T15:G4 T23:G2
S3: T4:G0 T2:G1 T6:G4 T20:G2
S4: T12:G3 T22:G0 T11:G5 T14:G4
S5: T8:G3 T1:G2 T21:G1 T17:G4
```

For each group, sort its four tile IDs as `a<b<c<d`; code 0 means
`(a,b),(c,d)`, code 1 means `(a,c),(b,d)`, and code 2 means `(a,d),(b,c)`.
The planted answer is `[1,2,0,0,2,2]`, and `verify` returns `(True, "ok")`.
Dropping its last entry gives `(False, "too few entries: expected 6, got 5")`.
A person can solve this demo on paper by trying the three pairings and crossing out
a choice when its contracted precedence edges close a cycle.

## Difficulty presets

| preset | groups | stack height | stacks | status |
|---|---:|---:|---:|---|
| demo | 6 | 4 | 6 | hand example; not hardened |
| easy | 192 | 8 | 96 | **shipping preset**, hardened 0/3 |
| medium | 216 | 8 | 108 | reserved escalation rung |
| hard | 240 | 8 | 120 | largest writable escalation rung |

## Gate measurements

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verify; JSON round-trip checked |
| G2 | pass | drop, duplicate, empty, range error, and coordinate swap all rejected with distinct reasons |
| G3 | pass | tagged answer recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 uniform structure-aware ternary candidates; 95.40 s |
| G5 | pass | shipping density 0/200,000; demo has 96/729 valid answers; strongest repair used 48,705 evaluations in 14.26 s |
| G6 | pass | five attacks, each 0/8; paper search additionally used 2,048 capped nodes in 98.79 s |
| G7 | pass | `n=384` builds in 0.023 s and its plant verifies |
| G8 | pass | 140/140 relabel/composition checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 385 chars, 97 estimated tokens, 192 atoms, 192 intended pairing decisions |

## Oracle hardening and G9 arms

The repository-owned harness returned `hardened` at the first published rung,
`easy(n=192,height=8)`: all three bare attempts failed.  At run time the checked-in
harness was configured for two provider models (GPT-5.6 Terra and Gemini 3.8 Flash),
with one provider repeated on a distinct seed to make three attempts.

| preset | model | seed | solved | reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 84057773 | no | submitted pairing has a precedence cycle |
| easy | GPT-5.6 Terra | 2661525 | no | no parseable tagged answer |
| easy | GPT-5.6 Terra | 1448845028 | no | returned 210 entries instead of 192 |

| G9 arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0/3 - 0/3 = 0.0`.  Naming the directed-cycle invariant
bought the oracle pool no measured success, so the remaining difficulty appears to
be carrying 192 mutually constrained pairing decisions through to an exact writable
witness, not merely noticing the invariant.  The answer is 385 characters, about 97
tokens, and 192 atomic entries; the intended post-insight route is counted as 192
pairing decisions.

## Use

```python
import gen_1203_6559 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit twenty instances with:

```bash
bash scripts/emit.sh 1203.6559 20 hard
```

## Caveats

Theorem 3 is a worst-case theorem; it does not prove this inverse-generated
distribution hard.  The claim rests on the measured panel.  The current harness's
two-provider configuration is narrower than the four-vendor pool described by the
original task, although all three script-owned attempts failed.  The depth
statistic's 71.81% entry accuracy is a genuine
planting leak even though the tested repair failed at `n=192`; a stronger local,
SAT, or unbounded implementation of the paper's complete solver may exploit it.
The 0/200,000 guess result applies only to the declared uniform prior over the three
locally legal pairings per group and is an empirical upper-resolution result, not a
proof that the solution density is zero or below every nonuniform prior.  The full
unbounded paper solver, a modern SAT encoding, and parallel local search were not
run.

Finally, `canonical_key` uses ordered-incidence color refinement.  It is invariant
under every tested tile/group/stack relabeling and separated all unrelated samples,
but it is not a complete isomorphism canonicalizer and could collide on symmetric
adversarial boards outside this generator.
