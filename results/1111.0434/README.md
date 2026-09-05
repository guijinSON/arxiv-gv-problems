# Breakpoint-tight pancake-flipping generator (arXiv:1111.0434)

> Status: complete. The generator passes every local gate, and the script-owned
> hardening run returned `hardened` at the shipping preset after three valid
> attempts across two vendors. Structural-hint and placebo diagnostics were
> also run independently and each finished at 0/3 solved.

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate form | exact symbolic prefix-reversal word |
| Intended intuition | invariant: every flip in a tight route removes one breakpoint |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

The source is Bulteau, Fertin, and Rusu, [*Pancake Flipping Is
Hard*](https://arxiv.org/abs/1111.0434). A solver receives a top-to-bottom
permutation of distinct pancake sizes and must output exactly `db(S)` prefix
lengths that sort it. Here `db(S)` is the paper's count of nonconsecutive rank
adjacencies, including a wrong bottom pancake. Property 1 proves that one flip
changes this count by at most one, so any `db(S)`-flip sorting word is optimal.
`verify` checks the grammar, reversal parity, selected pancake trajectories,
and finally replays every prefix reversal exactly. It accepts any valid word and
never reads the planted answer.

Generation is inverse, not search. Starting from the sorted permutation, the
module repeatedly chooses uniformly among all prefix flips that create exactly
one breakpoint. Reversing this word gives a sorting route in which every flip
removes exactly one breakpoint. Independent increasing integer labels replace
the ranks, preventing numerical gap size from marking the chosen cuts.

## Hardness claim and Step 0 triage

Section 2 supplies the exact definitions and the two-efficient-choice bound.
Theorem 18 proves that the reduction stack `S_phi` is efficiently sortable iff
the source 3-CNF is satisfiable; Theorem 19 proves NP-hardness even for deciding
whether the breakpoint lower bound is tight. This family stays in that exact
tight regime: the shipping preset has 245 pancakes, 240 breakpoints, and a
240-flip certificate.

The theorem is worst-case, not a distributional hardness theorem. Evidence for
this inverse-walk distribution is therefore empirical: transposition-pruned exhaustive
search over the at-most-two efficient moves explored 250,000 nodes on each of
eight shipping instances (2,000,000 total, 50.135166 seconds) and solved none.
Four construction-aware alternatives also solved 0/8. This supports, but cannot
prove, the Track A claim that no efficient general method is known for the
generated distribution.

The easy cases matter. Asking for any sorting route fails H because ordinary
largest-first pancake sorting is direct and polynomial. The introduction also
reports 2-approximations and a polynomially sortable simple-permutation class.
Small inverse tight walks fail too: the same exhaustive search solved 20/20 at
60 flips. The paper's own 3-SAT gadgets were considered, but Definition 8 uses
`31l+98k` pancakes and `16l+50k` flips. A native path under the 256-atom answer
cap can expose at most six relevant Boolean variables, so that construction is
not a hard shipping family here.

## Worked demo

For `make_instance(n=3, slack=3, seed=3)`, `render` returns the complete
hand-scale question below.

```text
Bounded pancake sorting by prefix reversals

A stack contains 6 pancakes of distinct integer sizes.  It is written
from top to bottom.  A prefix reversal of length k reverses exactly the first k
pancakes; k is an integer and 2 <= k <= 6.  The goal is the unique
increasing top-to-bottom order (smallest pancake first).

Find a sequence of exactly 3 prefix reversals that sorts this
stack.  Consecutive reversals must have different lengths; immediate duplicate
flips are forbidden.  Apply the listed lengths from left to right.  Repeated
lengths are otherwise allowed, and order matters.

For clarity, the rank of a pancake is its position after sorting, from rank 1
(smallest) through rank 6 (largest).  A rank breakpoint is either an
adjacent pair whose ranks do not differ by 1, or the bottom position when the
bottom pancake does not have rank 6.  This stack has exactly
3 rank breakpoints, so no sorting sequence can use fewer
than 3 flips.

Initial stack, top to bottom:
[920925, 920898, 920896, 920892, 920915, 920944]

Give your final answer inside <answer></answer> tags, as one JSON-style
comma-separated list of exactly 3 integer prefix lengths, in
execution order.
Example of the syntax: <answer>[2, 3, 2]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[5, 4, 3]</answer>`. A person can replay it on paper:

```python
verify(inst, [5, 4, 3])
# (True, "ok")
verify(inst, [7, 4, 3])
# (False, "a prefix length is outside 2..6")
```

## Difficulty presets

`n` is the inverse-walk depth and answer length; the physical stack has
`n + slack` pancakes. The three evaluated presets hold the answer fixed while
increasing cut-location crowding.

| Preset | `n` / flips | `slack` | Pancakes | Standard-search result | Status |
|---|---:|---:|---:|---|---|
| demo | 3 | 3 | 6 | 1 exact answer in a 36-word language | hand-solvable |
| easy | 240 | 5 | 245 | 0/8 after 2,000,000 nodes | **ships** |
| medium | 240 | 30 | 270 | 0/8 after 2,000,000 nodes | harder reserve |
| hard | 240 | 48 | 288 | 0/8 after 2,000,000 nodes | hardest named reserve |

`escalate` first uses the last writable depth (`n=248`, `slack>=50`) and then
returns `"cap_bound"`; maintaining breakpoint density beyond that point would
push the certificate past the output cap.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 plants verified; 12/12 JSON-native round trips |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged prose + Markdown fence parsed to all 240 flips |
| G4 | 0/200,000 structure-aware guesses; 135.079187 s |
| G5 | shipping density 0/200,000; demo exact count 1/36; baseline 2,000,000 nodes in 50.135166 s |
| G6 | boundary-gap, smallest-efficient greedy, 256 restarts, width-128 beam, and exhaustive DFS: each 0/8 |
| G7 | size/depth doubled from 240 to 480; the 480-flip plant still verifies |
| G8 | 60/60 invariant keys, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 1,114 chars, 481 lexical tokens, 240 atoms, 240 intended operations |

## Oracle loop and G9 arms

The bare, no-hint hardening run held at its first evaluated rung. Each reply was
parsed and checked exactly; none was counted as a failure because of an API
error.

| Preset | Seed | Solved | Why |
|---|---:|---:|---|
| easy | 919872617 | no | supplied fewer than 240 flips |
| easy | 906454163 | no | wrong total reversal parity |
| easy | 1536011832 | no | replay left rank 245 at position 6 |

| Arm | Solved / attempts | Recorded outcome |
|---|---:|---|
| bare | 0 / 3 | `hardened` |
| structural hint | 0 / 3 | `hardened` |
| placebo hint | 0 / 3 | `hardened` |

The measured `hinted - placebo` difference is 0.0. On these six diagnostic
calls the structural hint bought nothing, so the result does not show that the
claimed invariant alone is sufficient; it only shows that naming it did not
remove the branch-selection burden. The hint names the invariant without
providing the next move or a derived count. The largest measured answer was
1,114 characters, 481 lexical tokens and 240 atomic elements. The compact-route
accounting treats each of the 240 prefix reversals as one exact symbolic
operation, below the 300-operation cap.

## Use

```python
import gen_1111_0434 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
wire = "<answer>" + str(inst["answer"]) + "</answer>"
candidate = gen.parse_answer(wire)
assert gen.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1111.0434 20 easy
```

Run the local suite with
`python3 results/1111.0434/gen_1111_0434.py`.

## Caveats

- Theorem 19 is worst-case. It does not establish average-case hardness for
  inverse random tight walks; the attack panel is the distributional evidence.
- G4's zero is a point estimate, not proof of zero probability. Its prior is
  deliberately strong: 99% of samples choose only breakpoint-decreasing moves
  until deadlock, while 1% preserves full support over fixed-length, reduced,
  parity-correct words. It does not model learned backtracking.
- The standard search is capped at 250,000 states per instance. Pattern
  databases, SAT/CP encodings, bidirectional search, and specialized external
  pancake solvers were not available and were not tested.
- The 240-atom witness is intentionally near the 256-atom cap. It passes G9(c)
  but may still expose transcription failures; no claim is made otherwise.
- Increasing only the number of pancakes eventually makes breakpoints sparse
  and the instances easier. The named `slack` sweep stays inside the measured
  difficult window; further escalation must deepen the path and is cap-bound.
- G9's 240-operation count uses a prefix reversal as the natural symbolic
  primitive. An array implementation performs more individual item moves, and a
  person still has to track a long state; the 240-atom witness is therefore near
  both the formal cap and the practical edge of no-tool usability.
