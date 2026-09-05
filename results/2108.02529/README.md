# Switching-set recovery for arXiv:2108.02529

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph (switching-set recovery in a bipartite incidence structure) |
| Certificate | integer tuple (an unordered set of block labels) |
| Intended intuition | invariant: repeated row symmetric differences under hidden XOR translations |
| Domain essentiality | native |
| Reduction | none |

## What the problem is and why it is checkable

[Crnković and Švob, *Switching for 2-designs*](https://arxiv.org/abs/2108.02529)
define a switching set of blocks in Definition 1.  If it has `q` blocks, every
point is incident with none, half, or all of them.  Theorem 2 proves that
complementing the half-incidence columns preserves the design parameters.
Section 3.2 observes that every diagonal block group of a Bush-type Hadamard
design is such a set.

The module hands the solver the complete block-point incidence matrix of a
symmetric Menon design, with rows encoded as exact hexadecimal bitsets, and
asks for one `q`-block switching set.  `verify` checks distinct labels and
counts incidences exactly; it neither consults `inst["answer"]` nor invokes a
search algorithm.  The generator knows a row group before constructing and
relabeling the matrix, so generation is theorem-backed rather than a solve of
the finished instance.

## Why this is Track B

The paper has no hardness theorem, and Remark 4 says that every *pair* of
blocks is a switching set.  This family therefore requires the nontrivial
Section 3.2 size `q>2` and makes no Track-A claim.  The exposed Bush block order
is also easy: take one contiguous row group.  The `easy` and `medium` rungs
retain that order deliberately.

At the hard rung the same native rows are labeled as cosets of the span of
disjoint two-bit masks.  The standard exact producer hashes every pairwise row
XOR up to complement and unions the large collision buckets.  It is
`O(v^3/w)` bit-word work and solved 8/8 shipping instances.  At `v=256` it
examined 32,640 pairs, used 391,680 counted word operations, and the final
report measured 0.010 s on average (0.013 s maximum).  That is easy for a
computer and not executable by hand from the prompt.  If the intended
invariant is noticed, testing the 28 two-bit label translations and spanning
the four matches takes 211 counted XOR/comparison operations.

## Worked demo

This is `make_instance(n=4, seed=7, label_mode="contiguous")` in full:

```text
SWITCHING SET IN A 2-DESIGN

A 2-(v,k,lambda) design has v labelled points and a collection of blocks: every block contains exactly k points, and every two distinct points occur together in exactly lambda blocks.

Here v=16, k=6, lambda=2, and there are 16 blocks and 16 points, both labelled 0 through 15.

Find exactly q=4 distinct block labels forming a switching set. For this task, that means: for every point, its incidence count among your 4 selected blocks must be exactly 0, 2, or 4. The order of your labels does not matter, and repeated labels are forbidden.

The incidence matrix is listed by block label.  Each row is a fixed-width hexadecimal integer.  Bit j of that integer, counting the least-significant bit as bit 0, is 1 exactly when the block contains point j.  Leading zeroes are significant only as padding to 16 bits.

block : incidence-bitset-in-hex
0: 8163
1: 4dc0
2: 50b1
3: 9c12
4: 8685
5: 4a26
6: a8a8
7: 640b
8: 085d
9: 3b01
10: 2670
11: 152c
12: e114
13: d248
14: 30c6
15: 039a

Give your final answer inside <answer></answer> tags, as a JSON list of exactly 4 distinct integer block labels in increasing order.
JSON syntax example for a hypothetical three-label instance: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags.
```

The planted answer is `[0, 1, 2, 3]`:

```python
verify(inst, [0, 1, 2, 3])   # (True, "ok")
verify(inst, [0, 1, 2])      # (False, "too few block labels: expected 4")
```

A person can solve this smallest instance on paper: the rows are contiguous
and only 1,820 four-subsets exist (28 are valid).  It is an illustration, not
the shipping difficulty.

## Difficulty presets

| preset | `q=n` | points/blocks `v=q²` | row labels | answer atoms | status |
|---|---:|---:|---|---:|---|
| demo | 4 | 16 | contiguous Bush groups | 4 | hand-scale |
| easy | 8 | 64 | contiguous Bush groups | 8 | solved by Terra, as expected |
| medium | 16 | 256 | contiguous Bush groups | 16 | deliberately exposed |
| hard | 16 | 256 | hidden matching cosets | 16 | shipping candidate |

The hard rung has no oracle verdict yet.  Terra solved `easy`, after which the
second provider and every redraw returned HTTP 403.  The candidate must
**not** be treated as released until the bare hardening loop reaches `hard`
and returns a real verdict.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 28/28 planted witnesses verified, including public defaults; 12/12 full 2-design parameter checks |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | prose + fenced tagged answer parsed exactly |
| G4 | pass | 0/200,000 uniform structured `q`-subset guesses |
| G5 | pass | shipping space `10,078,751,602,022,313,874,633,200`; reference 8/8, 391,680 operations |
| G6 | pass | all six attacks 0/8, including exact spectral-Gram and by-hand contiguous-label probes; reference algorithm separated as Track B |
| G7 | pass | doubled `q=32`, `v=1024` instance built and verified |
| G8 | pass | 40 simple + 20 composed invariance checks, 60 carried-witness checks, 20/20 distinct seeds |
| G9(c) | pass | 72 chars, 18 estimated tokens, 16 atoms, 211 intended operations |

The G8 key is the sorted binary-rank spectrum after every zero-, one-, and
two-group paper switch.  It is invariant under independent block and point
relabelings.  It is deliberately described as a strong cheap invariant, not a
complete design-isomorphism canonizer.

## Oracle loop and G9 diagnostics

The script-owned bare loop got one valid result and then stopped because the
remaining provider was unreachable:

| preset | seed | model | solved | result |
|---|---:|---|---|---|
| easy | 1280740961 | OpenAI GPT-5.6 Terra | yes | `[0,1,2,3,4,5,6,7]` verified |
| easy | 44455279 | Google Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 1232636583 | Google Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 128275757 | Google Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 290941434 | Google Gemini 3.8 Flash | error | HTTP 403 key limit; pool unreachable |

| G9 arm at hard preset | solved / valid attempts | error calls | conclusion |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | no measurement |
| structural hint | 0 / 0 | 4 | no measurement |
| placebo hint | 0 / 0 | 4 | no measurement |

`hinted - placebo` is therefore undefined, and nothing can yet be concluded
about whether naming the invariant helps.  The transcript files are retained
as infrastructure evidence, not as evidence that a model failed the problem.

## Use

```python
import json
from gen_2108_02529 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(
    f"Result: <answer>{json.dumps(inst['answer'])}</answer>"
)
ok, reason = verify(inst, candidate)
```

After obtaining a real `hardened` verdict, emit examples from the repository
root with:

```bash
scripts/emit.sh 2108.02529 20 hard
```

## Caveats

- This is intentionally not complexity-theoretic hardness.  The reference
  producer is fast and always succeeds; the benchmark claim is only the
  no-tool compression gap.
- The 0/200,000 density estimate is relative to uniform distinct sorted
  `q`-subsets.  It does not model a solver that notices row-XOR collisions;
  the reference algorithm shows exactly why cardinality is not the hardness
  argument.
- The sampled block phases are conditioned to defeat common-zero greedy and
  coordinate-subspace ansatzes and to make the short matching invariant exact.
  This conditioning applies to the whole design, not a distinguished planted
  row; any valid switching set is accepted.  The filter is used only for
  `q>=16`; smaller supported calls do not need shipping-grade camouflage.  If
  2,048 phase draws were ever exhausted, generation deterministically falls
  back to the separately audited seed-0 hard instance rather than failing.
- A full SAT/ILP encoding and higher-order tensor methods were not tried.  The
  exact block-Gram spectral probe has no pairwise signal because every block
  has the same size and every two blocks have the same intersection, but that
  does not rule out higher-order spectral constructions.
- `canonical_key` may collide on nonisomorphic designs because full design
  isomorphism is not computed.  It passed all required relabeling and 20-seed
  distinctness checks.
- Most importantly, the OpenRouter key limit prevented STEP 4 from reaching
  `hard` and prevented the G9 arms from producing valid attempts.  Local gates
  passing is not a substitute for the required multi-vendor evidence; rerun
  those scripts before submission.
