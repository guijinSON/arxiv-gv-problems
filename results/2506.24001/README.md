# Verified generator for arXiv:2506.24001

## What this family is

This module generates the one-knapsack restriction of **LS Multi Knapsack** from
[Grüttemeier, Morawietz, and Sommer, “Fantastic Flips and Where to Find Them”](https://arxiv.org/abs/2506.24001).
All ordinary items begin inside one knapsack and one special item begins outside.
A solver must name exactly `d` ordinary items to remove; the checker inserts the
special item, replays all `d+1` flips, checks the capacity, and recomputes the
integer score. Any valid witness is accepted, not just the planted one.

Generation is inverse: the `d` witness IDs are sampled first. Every ordinary item,
whether planted or a decoy, then receives a distinct uniform random offset from the
same interval. The target is the planted sum. A large common baseline makes only
size-`d` subsets capable of meeting that target, exactly as in the paper's
size-limiting construction.

## Why it is hard, and what was avoided

Section 4.5 gives the exact LS Multi Knapsack definition: improve a supplied
feasible allocation by at most `k` item flips. Section 5.1, Lemma 21 proves that
Positive `d`-Sum remains W[1]-hard on size-limiting instances. Theorem 22 reduces
that problem to LS Multi Knapsack and proves W[1]-hardness in `k` plus an ETH lower
bound excluding `n^{o(k)}` time, even with one knapsack, binary-encoded
weight-equals-value items, and an initial solution locally optimal iff globally
optimal. The generator stays inside all of those restrictions.

The easy regimes matter. Theorem 5 and Section 4.5 give algorithms exponential in
the search radius `k` or number of distinct item types `tau`; therefore the
generator makes `d`, `k=d+1`, and `tau=n+1` grow with `n`. Its numeric widths also
make pseudo-polynomial sum tables impractical while keeping density above the
classic low-density lattice-attack range.

## Worked example (smallest preset, `medium`, seed 0)

This is the complete output of `render(make_instance(seed=0, **DIFFICULTY["medium"]))`:

```text
LOCAL-SEARCH MULTI KNAPSACK (one knapsack)

There is one knapsack and a set of indivisible items.  Every item has a
nonnegative integer weight and value.  An assignment is feasible when the sum
of weights of the items inside the knapsack is at most its capacity.  Its score
is the sum of values inside.  A flip changes one item's status from inside to
outside or from outside to inside.  The flip distance is the number of items
whose final status differs from the supplied initial assignment.

Find a feasible assignment with score STRICTLY larger than the initial score
and flip distance at most 20.

This instance has 64 ordinary items and one special item.  All
ordinary items start inside; special item 65 starts outside.
Every value equals its weight.  Your witness must name exactly 19 distinct
ordinary items to remove; special item 65 is then inserted
automatically.  Order does not matter and repeated IDs are forbidden.  Item
IDs are the integers shown below and are 1-indexed.

Knapsack capacity: 1441789371732249
Initial total weight: 1441789371732248
Initial score: 1441789371732248
Required flip distance: exactly 20 (19 removals plus the special insertion)

For clarity, with these data the replay is feasible and strictly improving if
and only if the removed ordinary weights sum exactly to
427493801516644.  This equality is a derived aid; the checker still
replays the flips, checks capacity, and recomputes the score.

ITEMS (one row per item: ID WEIGHT VALUE INITIAL_STATUS)
1 22543421777313 22543421777313 in
2 22669468582697 22669468582697 in
3 23026737860126 23026737860126 in
4 22211680269086 22211680269086 in
5 22945234817415 22945234817415 in
6 23040577646852 23040577646852 in
7 22563702402714 22563702402714 in
8 22024231492937 22024231492937 in
9 22870014048209 22870014048209 in
10 21992918051813 21992918051813 in
11 23075192392093 23075192392093 in
12 22524239304738 22524239304738 in
13 22706333649274 22706333649274 in
14 22407114898636 22407114898636 in
15 22515170776622 22515170776622 in
16 22976112190401 22976112190401 in
17 22166717984195 22166717984195 in
18 22694578078878 22694578078878 in
19 22228557227522 22228557227522 in
20 22966425610254 22966425610254 in
21 22839768217633 22839768217633 in
22 22626927557640 22626927557640 in
23 22403339126100 22403339126100 in
24 22401782623460 22401782623460 in
25 23035026541363 23035026541363 in
26 22183802802749 22183802802749 in
27 22852161617931 22852161617931 in
28 22598075972176 22598075972176 in
29 22979257055041 22979257055041 in
30 22172156063898 22172156063898 in
31 23060174835615 23060174835615 in
32 22523626171150 22523626171150 in
33 22244799725183 22244799725183 in
34 22474298275336 22474298275336 in
35 22721109209472 22721109209472 in
36 22209543002181 22209543002181 in
37 22311423603811 22311423603811 in
38 22089956428615 22089956428615 in
39 22046384944639 22046384944639 in
40 22849740102870 22849740102870 in
41 22802374500785 22802374500785 in
42 22068040381236 22068040381236 in
43 22040077816388 22040077816388 in
44 22398128571389 22398128571389 in
45 22263899768443 22263899768443 in
46 22451852349065 22451852349065 in
47 22040394969780 22040394969780 in
48 22924577932061 22924577932061 in
49 22211941344218 22211941344218 in
50 22565053380458 22565053380458 in
51 22475864526153 22475864526153 in
52 22760324750975 22760324750975 in
53 22387242447337 22387242447337 in
54 22078138214790 22078138214790 in
55 22211837770862 22211837770862 in
56 22429999738184 22429999738184 in
57 22777328834501 22777328834501 in
58 22362046880239 22362046880239 in
59 22118082343143 22118082343143 in
60 22742547419769 22742547419769 in
61 22542262443883 22542262443883 in
62 22964852626280 22964852626280 in
63 22375343400107 22375343400107 in
64 23025376383564 23025376383564 in
65 427493801516645 427493801516645 out

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 19 distinct ordinary item IDs.  Do not include special item
65; it is inserted automatically.
Example: <answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19</answer>
Output nothing else inside the tags.
```

The planted answer is
`[3, 9, 14, 17, 19, 20, 23, 26, 27, 31, 32, 33, 38, 49, 50, 51, 54, 57, 58]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last ID returns
`(False, "expected exactly 19 removal IDs")`.

## Difficulty presets

| Preset | `n` | `d` | `k` | offset bits | structural candidates | Status |
|---|---:|---:|---:|---:|---:|---|
| `medium` | 64 | 19 | 20 | 40 | 8,719,878,125,622,720 | **ships; held all oracles** |
| `hard` | 96 | 30 | 31 | 48 | 6,868,096,454,739,518,200,146,192 | available; not reached |

`escalate()` raises `n`, the subset fraction, and numeric width together. No preset
was rejected by a local gate; the hard preset was unnecessary because medium held.

## Gate results

| Gate | Measured result |
|---|---|
| G1 planted replay | 12/12 preset-seed checks passed |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 parser | model-style response round-tripped; 4/4 garbage cases returned `None` |
| G4 structured guessing | **0/200,000** hits, uniform over exact-19 subsets |
| G5 sparsity | 1/38,760 valid on an exactly enumerated `n=20,d=6` probe |
| G6 attacks | outlier 0/8; greedy 0/8; random-restart swap 0/8 |
| G7 scaling | `n=128,d=38` built and verified; space 496,253,786,735,283,947,757,809,593,371,200 |
| G8 canonical key | invariance 120/120; transformed witnesses 80/80; unrelated keys 24/24 |

The canonical form ignores item IDs and row order. It also normalizes the positive
affine symmetry `w -> u*w+c`, `target -> u*target+d*c` of fixed-cardinality sums.

## Oracle loop

The required `scripts/harden.py` run used effort `medium`, a fresh seed per call,
and three distinct vendors. Every answer parsed; failures are genuine checker
failures rather than output-contract failures.

| Preset | Model | Seed | Solved? | Checker result |
|---|---|---:|---|---|
| `medium` | `google/gemini-3.1-pro-preview` | 1178502978 | no | capacity exceeded by 1,228,865,469,822 |
| `medium` | `x-ai/grok-4.6` | 2042772081 | no | capacity exceeded by 141,106,796,876 |
| `medium` | `openai/gpt-5.6-terra` | 1440516403 | no | score did not strictly improve |

Harness verdict: `hardened`, zero escalations, shipping preset `medium`.

## How to use it

```python
from gen_2506_24001 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    parse_answer, render, verify,
)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)

# `reply` is raw solver text containing <answer>...</answer>.
answer = parse_answer(reply)
ok, reason = verify(inst, answer)
```

From the repository root, emit 20 fresh, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2506.24001 20 medium
```

Run the local evidence suite with `python3 results/2506.24001/gen_2506_24001.py`.

## Caveats

- Theorem 22 is a worst-case complexity result; it does not prove this planted
  random distribution is average-case hard. The oracle panel is empirical evidence.
- The 0/200,000 result is under a uniform prior over all exact-`d` ordinary-item
  subsets. It correctly incorporates the obvious shape and cardinality constraints,
  but it does not model a sophisticated arithmetic solver or establish a statistical
  upper confidence bound of exactly zero.
- Small `n` or fixed `k`, few repeated item types, small numeric ranges, or a very
  low-density choice of much wider numbers can enable respectively enumeration, the
  paper's type/radius algorithms, pseudo-polynomial DP, or lattice attacks.
- The tested attacks were target-average outliers, remaining-average greedy choice,
  and random restarts with improving one-item swaps. Meet-in-the-middle, lattice
  reduction, SAT/SMT, and integer-programming solvers were not tested. They remain
  exponential or heuristic attacks worth evaluating for a stronger claim.
- Other exact-19 subsets can in principle hit the target. This is not a grading bug:
  `verify` accepts every improving witness, while `enumerate_all` refuses large spaces
  rather than pretending uniqueness.
