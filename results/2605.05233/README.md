# Verified generator for arXiv:2605.05233

> Status: the module and deterministic gates pass, but the result is **not yet
> shippable**. The required OpenRouter calls all returned HTTP 403 “total key
> limit,” leaving Step 4 and the three G9 oracle arms without valid attempts.
> API errors are recorded as errors, not model failures.

| Profile | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | optimization |
| Object regime | finite discrete |
| Computational core | subset sum |
| Certificate | integer tuple: four item-ID bundles |
| Intuition | invariant — residue orbits give equal-sum four-item groups |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust

The source is Chen et al., [*Near-Tight Approximation Algorithms for Bottleneck
Multiple Knapsack Problems*](https://arxiv.org/html/2605.05233v1). Following the
paper’s [Section 3 definition](https://arxiv.org/html/2605.05233v1#S3), an
instance hands the solver unit-profit weighted items and four identical-capacity
knapsacks. The solver must divide all items equally among the knapsacks without
exceeding any capacity. The returned allocation is checked using only ID counts,
integer sums, and comparisons; `verify` never reads the stored answer and accepts
every valid allocation.

Generation is by composition of identities, not search. Modulo 401,
`20^2 = -1`, so every nonzero residue lies in a four-cycle
`{r, 20r, -r, -20r}` whose least positive representatives sum to 802. Random
nonnegative multiples of 401 are added subject to a fixed total, making every
lifted cycle have the same sum. Equal numbers of complete cycles are assigned to
the four knapsacks before item IDs are shuffled. Plants and decoys are therefore
drawn from the same cycle population.

## Why Track B

This is not an average-case NP-hardness claim. [Theorem 1](https://arxiv.org/html/2605.05233v1#S1.SS1)
gives a polynomial-time `(2/3-epsilon)` approximation for identical capacities;
[Section 6](https://arxiv.org/html/2605.05233v1#S6) proves its exact hardness
gap using arbitrary capacities, not this generated distribution. The family is
Track B because a mechanical algorithm is known and measured.

The reference implementation repeatedly runs cardinality-constrained subset-sum
bitset DP. Its cost is pseudo-polynomial in general,
`O(m*N*n*B/word_size)`, and polynomial on the shipping distribution because the
number of bins and lift height are fixed. It solved 8/8 shipping instances with
a median of 9,774 bitset transitions, an estimated 6,616,998 64-bit word
operations, and 0.300 seconds. A solver that notices the residue invariant needs
at most 288 exact operations: reduce 144 weights modulo 401 and recover each
four-cycle from one representative. That fits the no-tool cap but is not a route
the prompt mechanically reveals.

## Worked demo

`make_instance(n=4, height=4, seed=3)` renders in full as:

```text
Find an exact bottleneck multiple-knapsack allocation.

Definitions and conventions.
There are 16 distinct items, with IDs 0 through 15, and four knapsacks, with IDs 0 through 3.
Item i has integer weight W[i] and profit 1. Each item may be assigned to at most one knapsack.
Knapsack j has integer capacity B[j]. Its assigned items must have total weight at most B[j].
The profit of a knapsack is the sum of its item profits. Every knapsack must receive profit at least 4.
Your witness must assign exactly 4 distinct item IDs to each knapsack and use every item exactly once.
Bundle order follows knapsack order: entry j is the bundle for knapsack j. IDs inside a bundle are unordered; any order is accepted.
All indexing is 0-based. Capacity bounds and the profit target are inclusive. Repeated item IDs are forbidden.

W = [363,1251,1905,439,854,1161,349,100,443,754,5,396,238,158,243,965]
B = [2406,2406,2406,2406]

Give your final answer inside <answer></answer> tags, as a JSON list of four integer lists of the required size.
Syntax example for four items per bundle (not an answer to this instance): <answer>[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]]</answer>
Output nothing else inside the tags.
```

One answer is:

```text
<answer>[[1,9,13,14],[0,3,5,8],[4,6,12,15],[2,7,10,11]]</answer>
verify(...) -> (True, "ok")
```

Removing item `14` from the first bundle returns
`(False, "wrong bundle size: knapsack 0 needs exactly 4 item IDs")`. The demo
has 48 labelled valid allocations and is hand-solvable: 2406 is `6*401`, and
reducing the 16 weights modulo 401 exposes four multiplication-by-20 cycles.

## Difficulty presets

| Preset | n (cycles/items per bin) | Height | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 4 | 4 | 16 | hand example |
| easy | 12 | 6 | 48 | first Step-4 rung; API blocked |
| medium | 24 | 8 | 96 | local gates pass |
| hard | 36 | 10 | 144 | shipping candidate |

`escalate()` increases height while holding `n=36`, so it grows the DP haystack
without lengthening the answer.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 plants and 12/12 JSON round trips |
| G2 | pass | five corruptions, five distinct rejection reasons |
| G3 | pass | tagged JSON recovered through prose/fences; garbage rejected |
| G4 | pass | 0/200,000 structure-aware random allocations valid (132.977 s sampling run) |
| G5 | pass | shipping density 0/200,000; reference DP 52,935,984 word ops / 2.373 s total; demo count 48 |
| G6 | pass | five attacks at 0/8; reference DP at 8/8 as Track B expects |
| G7 | pass | doubled `n=72` plant builds and verifies |
| G8 | pass | 120/120 invariance and certificate checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 475 chars, about 119 tokens, 144 atoms, 288 intended operations |

The G4 prior already enforces every free structural rule in the statement: all
144 distinct IDs are used and each labelled bin receives exactly 36. Its space
has about `2.90e83` candidates. Zero sampled hits is a density estimate, not a
proof of zero probability or resistance to informed algorithms.

### Adversary panel

| Failing attack | Successes |
|---|---:|
| smallest-weight blocks (outlier probe) | 0/8 |
| input-order blocks | 0/8 |
| largest-first to the lightest bin | 0/8 |
| 128 random balanced restarts | 0/8 |
| lightest/heaviest pairs round-robin (by-hand ansatz) | 0/8 |

## Oracle loop and G9 diagnostics

The latest script-owned bare ladder never obtained a valid attempt at `easy`:

| Preset | Seed | Result | Why |
|---|---:|---|---|
| easy (Gemini) | 2058295905 | error | OpenRouter HTTP 403 total key limit |
| easy (GPT) | 110384440 | error | OpenRouter HTTP 403 total key limit |
| easy (GPT redraw) | 719924202 | error | OpenRouter HTTP 403 total key limit |
| easy (Gemini redraw) | 1363667539 | error | OpenRouter HTTP 403 total key limit |

The three shipping-preset G9 arms were run separately, as required:

| Arm | Solved/valid attempts | API errors | Conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | no diagnostic |
| structural hint | 0/0 | 4 | no hinted verdict |
| placebo hint | 0/0 | 4 | no diagnostic |

Hinted-minus-placebo is therefore undefined. No conclusion about the claimed
invariant can be drawn until the account limit is restored. These arms are
diagnostic rather than gates, but the independent Step-4 bare hardening evidence
is still mandatory for shipping.

## Use

```python
from gen_2605_05233 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
print(render(inst))
```

From the repository root, after obtaining a valid Step-4 verdict:

```bash
python3 results/2605.05233/gen_2605_05233.py
bash scripts/emit.sh 2605.05233
```

## Caveats

The residue modulus is a deliberately planted invariant. A solver that guesses
401 (also visible as a factor of the capacity) can solve the family quickly;
that compression gap is the Track B task, not a hidden Track A claim. Conversely,
144 remainders and a 144-ID answer sit close to the 300-operation limit, so some
failures may still reflect bookkeeping.

The measured reference algorithm is sequential bitset DP. It succeeded on all
eight audited seeds but is not a completeness proof for arbitrary four-bin BMKP;
its pseudo-polynomial cost also grows with numeric height. The paper’s full
approximation scheme, commercial ILP/CP-SAT solvers, local-search exchanges, and
multidimensional fixed-bin DP were not implemented. The random-guess estimate
does not cover those informed methods. Finally, no oracle hardness evidence
exists while OpenRouter is quota-blocked, so this directory must not be submitted
on local gates alone.
