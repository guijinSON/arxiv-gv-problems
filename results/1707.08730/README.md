# Verified problem generator for arXiv:1707.08730

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | subset sum |
| Certificate | integer tuple: six increasing indices |
| Intended intuition | invariant: a hidden common residue class |
| Domain essentiality | native; no reduction |

## What the family is

This module turns Ammar Daskin's [*A Quantum Approach to Subset-Sum and Similar
Problems*](https://arxiv.org/abs/1707.08730) into exact fixed-cardinality subset-sum
instances. The solver receives positive integers and a target, then returns six
distinct 0-based indices whose weights add to that target. Verification checks the
index syntax and performs one exact integer sum; it accepts any valid six-subset, not
just the planted one.

Generation is inverse, never a search. The generator makes equally sized residue
buckets, chooses one bucket uniformly, shuffles all weights together, and defines the
target as the chosen bucket's sum. Planted and decoy buckets use the same sampling
rule. Section I of the paper fixes the exact subset-sum definition, and Section III
represents a subset by a computational-basis index paired with its sum. The modular
invariant is generator-added structure, but the objects and verifier remain the
paper's native integers, target, and subset. Exact integer arithmetic needs only the
Python standard library, so the module has no optional `gvlib` dependency.

## Why this is Track B

This is not a structural-hardness claim. Section I describes exhaustive search and
`O(nW)` dynamic programming and cites a quantum-walk bound polynomial in `n` when the
subset size is fixed. For the fixed size six here, the disclosed exact classical
reference algorithm splits a candidate into two triples and uses meet-in-the-middle
in `Theta(n^3)` time and memory. On the final shipping gate at `n=150`, it solved 8/8
instances with a median 2,040,862 counted integer/hash operations and 0.527 seconds.
A construction-aware program can do better without being told 997: scanning every
invertible modulus from 7 through 1000 solved 8/8 in a median 101,305 operations and
0.0037 seconds after warm-up.

The compressed route is to notice that all six desired weights have the same residue
modulo 997. The target then determines that residue and one scan recovers the six
indices. The measured route is 158 exact operations. The relevant compression is
therefore about 101,000 mechanical discovery operations versus 158 once the invariant
is recognized; generic 6SUM costs about 2.04 million. A bare no-tool solver must first
discover the unannounced modulus. Sections III–IV's proposed quantum method is conditional on
Assumptions 1 and 2; it is not used to manufacture or certify these instances.

## Worked demo

For `make_instance(n=12, k=6, modulus=997, quotient_bits=5, seed=4)`, the complete
rendered instance is:

```text
EXACT 6-ELEMENT SUBSET SUM

You are given 12 positive integers called weights and the positive integer
target T=139032. Find exactly 6 distinct weights whose sum is
exactly T. A weight is selected by its 0-based index shown before the colon.

Return exactly 6 distinct indices in strictly increasing order. Indices
range from 0 through 11, inclusive; repeated indices are forbidden and
the order of addition does not matter. All arithmetic is ordinary exact integer
arithmetic, with no modular interpretation in the definition of a valid answer.

Weights (index:value):
  0:23241  1:31148  2:24238  3:19253  4:20181
  5:17259  6:18187  7:21247  8:27229  9:16193
  10:25166  11:28157

Give your final answer inside <answer></answer> tags, as exactly 6
comma-separated base-10 indices with no brackets.
Example format: <answer>0, 1, 2, 3, 4, 5</answer>
Output nothing else inside the tags.
```

The answer is `[1, 4, 6, 9, 10, 11]`.
`verify(inst, [1, 4, 6, 9, 10, 11])` returns `(True, "ok")`; dropping the final
index returns `(False, "answer has fewer than 6 indices")`. A person can solve the
demo on paper by grouping the two residue classes and checking one six-term sum.

## Difficulty presets

| preset | items `n` | chosen `k` | quotient bits | status |
|---|---:|---:|---:|---|
| demo | 12 | 6 | 5 | hand-solvable illustration |
| easy | 150 | 6 | 56 | **ships; bare oracle held** |
| medium | 210 | 6 | 72 | harder, fixed-length answer |
| hard | 270 | 6 | 88 | harder, fixed-length answer |

`escalate()` first enlarges the ground set and then raises coefficient entropy; the
witness remains six indices throughout.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON round trips |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic tagged prose round-trips; garbage returns `None` |
| G4 | 0/200,000 structure-aware guesses; `C(150,6)=14,297,000,725` candidates |
| G5 | shipping density sample 0/200,000; demo exactly 1/924; strongest construction-aware attack 101,312 operations and 0.00336 s on the recorded run |
| G6 | four attacks each 0/8; modulus scan, exact reference, and compact route each 8/8 |
| G7 | doubled `n=300` builds and verifies; search space 962,822,846,700 |
| G8 | 80/80 invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | worst case 25 answer characters, 6 atoms, about 7 tokens; intended route 158 operations |

## Oracle loop

The mandatory bare run held at `easy` without escalation. Every reply contained a
parseable six-index candidate, and every candidate failed the exact sum check.

| preset | model | seed | solved | verifier result |
|---|---|---:|---:|---|
| easy | OpenAI GPT-5.6 Terra | 1686371805 | no | wrong sum |
| easy | Google Gemini 3.8 Flash | 1922183327 | no | wrong sum |
| easy | Google Gemini 3.8 Flash | 426880961 | no | wrong sum |

## G9 diagnostic arms

| arm | solved / valid attempts | result |
|---|---:|---|
| bare | 0/3 | hardened at shipping |
| structural hint | 2/3 | the named invariant made shipping easy |
| placebo | 0/0 | four redraws hit OpenRouter HTTP 403 total-key limit |

The hinted-minus-placebo difference is undefined because no placebo model execution
was available. The structural arm alone strongly suggests that difficulty lies in
finding the invariant: two models solved once it was named. That is diagnostic, not a
gate under the current rules. The hinted transcript also contains four later 403
errors from an irrelevant post-solution escalation; its first three rows are the
shipping diagnostic. G9(c) passes with a worst-case 25-character, six-atom answer and 158
intended operations.

## Use

```python
from gen_1707_08730 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit records with:

```bash
scripts/emit.sh 1707.08730 20 easy
```

## Caveats

Knowing modulus 997 makes every instance linear-time, and the exact classical
reference algorithm already solves shipping instances in seconds; even automated
small-modulus discovery solves them in milliseconds. This is only a no-tool
compression benchmark. The 0/200,000 guess result is an observed density for
uniform increasing six-subsets, not a statistical proof that the true probability is
zero and not a model of a solver exploiting modular structure. A modulo-997 scan is
the intended successful route, not a failing adversary. The failing panel covers a
magnitude outlier, descending greedy choice, 4,096 random restarts, and a visible
decimal-suffix ansatz; the successful automated modulus scan is reported separately,
but the panel does not test LLL, ILP, or every additive-combinatorics heuristic. Exact timings vary with host load, so the
operation count is the more stable Track B cost measure. Alternative valid
six-subsets may occur and are correctly accepted. Finally, the placebo control remains
unmeasured because the external key was exhausted; the transcript records that gap.
