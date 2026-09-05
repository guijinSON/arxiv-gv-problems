# Circular Ordering generator for arXiv:1004.1956

| Profile | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate form | integer tuple (the paper's native circular order) |
| Native objects | ternary permutation constraints and a circular ordering |
| Intended intuition | reduction recognition: each constraint is a directed 3-cycle |
| Domain essentiality | native; no reduction or discretised surrogate |

## What the problem is

The family implements the `Pi_7` **Circular Ordering** problem from Gutin,
van Iersel, Mnich, and Yeo, [*Every Ternary Permutation Constraint Satisfaction
Problem Parameterized Above Average Has a Kernel with a Quadratic Number of
Variables*](https://arxiv.org/abs/1004.1956). The solver receives variables and
oriented triples `(a,b,c)`. It must put every variable around a clockwise circle
so that, starting at `a`, it encounters `b` before `c` for every triple. A
submitted list starts with variable 0 to quotient out free cyclic rotation.

Generation is inverse: it samples the circle first, partitions all variables
into triples in independent rounds, and orients every triple by that circle.
Each variable appears once per round, and every tuple gets an independent cyclic
rotation, so variable degree and displayed tuple position do not distinguish the
plant. The checker builds an exact integer position table and tests each cyclic
orientation. It never reads `inst["answer"]` and accepts any satisfying circle.

## Why this is a Track A claim

Section 3, Table 1 reports the Guttmann–Maucher dichotomy: exact `Pi_7`
Circular Ordering is NP-complete. Section 7, Case `j=7`, replaces `(u,v,w)` by
the directed cycle `u->v->w->u`; an accepted order has exactly two forward arcs
from that cycle, while a rejected orientation has one. This is the domain
attack and the basis of the exact `O(n 2^n)` subset dynamic program.

Shipping has `n=48`, `m=160`, and the above-average parameter `k=m/2=80`, so
`k` grows with the instance. This avoids the paper's main easy regime: Theorem 5
gives an `O(k^2)`-variable kernel and hence an FPT route for small `k`. It also
avoids the trivial `Pi=empty,S_3` cases and the polynomial exact-feasibility
languages `Pi_0` through `Pi_3` in Table 1. In particular, the initial triage
idea—only `Pi_0` triples consistent with one hidden linear order—would be a
polynomial topological-order problem and was not used.

Worst-case NP-completeness does not prove this regular planted distribution
hard. The claim rests additionally on measured distribution-specific attacks:
tuple-role outliers, greedy insertion, random-restart hill climbing, a
skew-adjacency spectral method, and a width-256 execution of the exact subset-DP
recurrence all failed on 8/8 shipping seeds. The capped DP explored 1,607,727
states and performed 37,283,577 arc additions in 1.488 seconds; the full method
would have exponentially many states. The generator itself produces its
certificate in `O(n+m)` time because inverse generation is allowed; that private
construction is not a solver for a supplied instance.

## Worked demo

For `seed=123`, the complete demo rendering is:

```text
CIRCULAR ORDERING ABOVE AVERAGE (Pi_7)

The variables are the integers 0 through 5. Place every variable exactly
once around an oriented circle. Submit the circle as a linear list read
clockwise, with variable 0 first. Requiring 0 first removes only cyclic
rotation; it does not restrict which circles are allowed. Reflection is not
free: reversing a submitted list usually changes whether constraints hold.

An oriented constraint is a row (a,b,c) of three distinct variables. It is
satisfied exactly when, starting at a and moving clockwise, b is encountered
strictly before c. Equivalently, the clockwise restrictions (a,b,c), (b,c,a),
and (c,a,b) describe the same accepted orientation; the reverse orientation is
rejected. There are no repeated variables inside a row and no repeated
unordered triples. All 6 displayed constraints must be satisfied. Since a
uniformly random circular order satisfies half of the rows, this is the paper's
Pi_7 Above-Average target m/2+k with m=6 and k=3.

Constraint rows are 0-indexed; row order has no meaning:
  0: 0 3 5
  1: 0 1 3
  2: 5 2 4
  3: 2 4 1
  4: 1 5 2
  5: 4 0 3

Give your final answer inside <answer></answer> tags as exactly 6
comma-separated base-10 integers: every label 0 through 5 exactly once,
with 0 first. Do not use brackets, and do not repeat a label.
Example of the required syntax (not necessarily a solution):
<answer>0, 1, 2, 3, 4, 5</answer>
Output nothing else inside the tags.
```

The constructed answer is `<answer>0, 1, 3, 5, 2, 4</answer>` and verifies as
`(True, "ok")`. Swapping 1 and 3 gives `[0,3,1,5,2,4]`, rejected as
`(False, "constraint row 1 has the reverse cyclic orientation")`. The demo is
genuinely hand-scale: it has only `5! = 120` normalized circles, and exact
enumeration finds one valid answer.

## Difficulty presets

| Preset | `n` | regularity rounds | constraints `m` | Status |
|---|---:|---:|---:|---|
| demo | 6 | 3 | 6 | hand example; skipped by harden.py |
| easy | 48 | 10 | 160 | **ships; bare and hinted pools held** |
| medium | 48 | 11 | 176 | fixed-answer tightening fallback |
| hard | 60 | 12 | 240 | larger fallback, not reached |

`escalate()` first adds a regular constraint round at fixed answer length, then
raises `n` and retunes the round count near the random-CSP crowding threshold.
It reports `cap_bound` before exceeding 240 answer atoms.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 planted witnesses verify and JSON-round-trip |
| G2 | pass: five corruptions rejected with five distinct reasons |
| G3 | pass: prose/fence/tag response round-trips; garbage returns `None` |
| G4 | pass: 0/200,000 uniform normalized circular orders valid |
| G5 | pass: shipping sample 0/200,000; demo exact count 1/120; capped DP 1,607,727 states |
| G6 | pass: all five attacks below succeeded 0/8 |
| G7 | pass: fixed-length escalation works; doubled `n=96,rounds=15` verifies |
| G8 | pass: 80 invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass: hinted pool 0/3; 182 chars, 48 atoms, about 46 tokens, 208 post-search exact operations |

| G6 attack | Successes | Counted work across 8 seeds |
|---|---:|---:|
| tuple-position outlier | 0/8 | 4,224 operations |
| greedy directed-arc insertion | 0/8 | 285,760 operations |
| 32-restart adjacent hill climb | 0/8 | 77,764,608 operations |
| skew-adjacency spectral phase | 0/8 | 572,352 operations |
| width-256 subset-DP recurrence | 0/8 | 1,607,727 states / 37,283,577 additions |

## Oracle loop

The bare run held at its first rung; every reply contained a parseable
48-variable permutation, and exact verification rejected it, so these are not
parser failures.

| Preset | Model | Seed | Solved | Exact reason |
|---|---|---:|---|---|
| easy | Gemini 3.1 Pro Preview | 658767954 | no | row 0 reversed |
| easy | Grok 4.6 | 60241550 | no | row 1 reversed |
| easy | GPT-5.6-terra | 1924400819 | no | row 5 reversed |

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; mandatory G9(b) passes |
| placebo hint | 0/3 | hardened diagnostic |

Hinted minus placebo is `0.0`. Naming the directed-3-cycle invariant bought the
pool no observed successes, so this run does not show that the claimed
`reduction recognition` intuition helps by itself. The answer is 182 serialized
characters, 48 atoms, and about 46 tokens. The 208-operation figure counts 48
position-table assignments plus one exact cyclic comparison for each of 160
constraints once a candidate circle has been determined; the exponential
search is the hardness being measured, not hidden arithmetic work.

## Use

```python
import gen_1004_1956 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
assert g.verify(inst, inst["answer"]) == (True, "ok")

text = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = g.parse_answer(text)
print(g.verify(inst, candidate))
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1004.1956 20
```

The module uses only the Python standard library; `gvlib` is unnecessary for
this finite permutation witness.

## Caveats

- The 0/200,000 density is under the declared prior: a uniformly random
  permutation conditioned to start with 0. It is an observed zero, not an exact
  shipping solution count and not a proof that the true probability is below
  any statistical confidence bound. Candidate space size alone is not evidence
  of hardness.
- The paper proves worst-case NP-completeness, not average-case hardness for
  this degree-balanced planted distribution. A future recovery algorithm could
  exploit its regular random hypergraph structure. The attack panel is evidence,
  not a theorem about that distribution.
- No commercial SAT/SMT, ILP/CP-SAT, SDP, or untruncated `2^48` subset DP was
  run. The panel includes a spectral construction attack and a wide truncated
  execution of the exact DP recurrence, but it is not exhaustive.
- The canonical key is invariant under tested relabellings, row reorderings,
  cyclic tuple rotations, and global reflection. It is a strong directed
  two-step/common-neighborhood invariant, not complete directed-graph
  isomorphism, so rare non-isomorphic collisions or missed isomorphic duplicates
  remain possible.
- More constraints can eventually make planted recovery statistically easier.
  The preset ladder stays near the crowding/uniqueness transition; it does not
  claim monotonic hardness for arbitrarily many rounds.
