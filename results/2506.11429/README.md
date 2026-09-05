# Prouhet–Tarry–Escott partition generator (arXiv:2506.11429)

| profile | value |
|---|---|
| Track | B — no-tool compression |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | subset sum |
| Certificate | exact symbolic: a 64-symbol A/B coloring |
| Intended intuition | invariant: recognize a translated weighted Boolean cube and subset parity |
| Domain essentiality | native; no reduction |

## Problem and trust model

This module instantiates Section 1.1 of Chen Shuwen, [*A survey of The Prouhet-Tarry-Escott Problem and Its Generalizations*](https://arxiv.org/abs/2506.11429). An instance gives distinct non-negative integers in a shuffled order. The solver colors every row A or B, using each color equally often, keeping each pair `x, C-x` together, and making the two colors have identical integer power sums through the stated degree. The checker validates the coloring, reflection closure, and the equivalent centered even-moment identities exactly; it never reads `inst["answer"]`.

Generation uses composition of identities, not solution search. For positive weights `w_i`, the signed exponential generating function over all subset sums is `product(1-exp(w_i*t))`; therefore even- and odd-cardinality subsets have identical moments below the cube dimension. An even dimension also makes subset complementation preserve parity, giving the reflection pairs. The paper's Equation (1.4) carries the identity through a common integer dilation and translation, and shuffling only changes row order. There are no differently distributed decoys: every displayed value is a vertex of the same cube.

## Why Track B

This is not a distributional or Track A hardness claim. Section 1.1 gives the exact PTE definition, states that no nontrivial solution exists when side size is at most the degree, and identifies the much tighter `side_size = degree + 1` ideal regime. Definition 2 defines the analogous central symmetry for ideal odd-degree solutions; this family imposes the same explicit reflection closure outside the ideal-size regime. Section 6 supplies exhaustive computer-search machinery for PTE/GPTE rather than a hardness theorem for this generated distribution.

The successful reference algorithm for the emitted problem pairs `x` with `C-x` and performs meet-in-the-middle on pair count and the centered second and fourth moments. For `P=32` reflection pairs it costs `O(degree * 2^(P/2))` exact time and `O(2^(P/2))` memory. At the 480-bit shipping preset it solved 8/8 cases, visited 65,536 half-states, used exactly 589,914 counted arithmetic operations, and took at most 0.29883 seconds locally. A solver that sees the invariant instead subtracts the minimum, reconstructs the six positive subset-sum generators, and colors by subset parity: 64 subtractions plus 63 additions, or 127 exact arithmetic operations. The roughly 4,645-fold operation-count gap and the need to discover the cube are the Track B claim.

## Worked demo

At `demo`, seed 7, the complete rendered problem is:

```text
Centrally symmetric Prouhet--Tarry--Escott witness

Below are 16 distinct non-negative integers. Their minimum plus their
maximum is C = 1427. Every displayed integer x has the unique displayed
reflection partner C-x.

Color every displayed row either A or B, subject to both requirements below.
Your answer is a 16-character word whose character in position i is
the color of displayed row i.

1. Use exactly 8 A symbols and 8 B symbols. Both members of
   each reflection pair must receive the same symbol. Thus each color consists
   of exactly 4 whole reflection pairs.
2. For every exponent k = 1, 2, ..., 3, the exact integer power sums agree:

       sum(a**k for a in A) = sum(b**k for b in B).

The labels before the colons are 1-based row numbers. The first answer symbol
colors row 1, the second colors row 2, and so on; symbols may not be reordered.
Uppercase A and B are the only allowed symbols. Arithmetic is over ordinary
integers with no rounding or modulus.

Displayed integers:
  1: 790
  2: 484
  3: 556
  4: 1123
  5: 970
  6: 889
  7: 637
  8: 709
  9: 736
  10: 538
  11: 943
  12: 718
  13: 457
  14: 304
  15: 691
  16: 871

Give your final answer inside <answer></answer> tags as exactly one unquoted
16-character word over uppercase A and B. Example syntax for a
hypothetical four-row instance: <answer>ABBA</answer>
Output nothing else inside the tags.
```

The answer is `ABBABBAAABBABAAB`. `verify(inst, answer)` returns `(True, "ok")`; deleting its last symbol returns `(False, "answer is too short: 15 symbols; expected 16")`. A person can solve this demo by subtracting 304, reconstructing the four subset-sum generators, and coloring subset sums by parity.

## Difficulty presets

| preset | weight bits `n` | scale bits | rows | answer atoms/chars | status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 4 | 16 | 16 / 18 JSON chars | hand-solvable illustration |
| easy | 160 | 160 | 64 | 64 / 66 | solved 1/3 in the bare ladder |
| medium | 240 | 240 | 64 | 64 / 66 | solved 1/3 in the bare ladder |
| hard | 480 | 480 | 64 | 64 / 66 | **shipping; held 0/3** |

An earlier 80-bit rung was also solved 1/3 and was dropped when the ladder slid upward. `escalate` can double both numeric dials while preserving the same 64-symbol answer; G7 separately verified a doubled `n=960` instance.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses over all presets and three seeds |
| G2 | pass | short, swapped, duplicated, empty, invalid-symbol, and whole-pair corruptions all rejected; five required cases have distinct reasons |
| G3 | pass | fenced A/B word surrounded by prose round-trips exactly |
| G4 | pass | 0/200,000 structure-aware guesses; each already has 32 A/32 B, reflection closure, and equal first moment |
| G5 | pass | seed 10000 has exactly 2 valid colorings among 601,080,390 (`3.3273419550419868e-09`); exact reference cost 589,914 operations / 0.29883 s |
| G6 | pass | width outlier, fourth-moment greedy, 256 random restarts, and sorted-pair alternation each scored 0/8; reference and compact algorithms scored 8/8 |
| G7 | pass | doubled `n=960` instance built and verified with unchanged answer size |
| G8 | pass | 100/100 invariance and carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 66 JSON characters, about 17 tokens, 64 atoms, 127 intended-route operations |

## Bare oracle loop

The script-owned run first tested the old 80-bit `easy`, then 160, 240, and an escalated 480-bit level. After the 480-bit level held, the ladder was slid so those last three levels are now named `easy`, `medium`, and `hard`. The current harness pool recorded two vendors.

| final level | seed | model | outcome | checker result |
|---|---:|---|---|---|
| dropped 80-bit | 956103168 | Gemini 3.8 Flash | solved | ok |
| dropped 80-bit | 1583231315 | GPT-5.6 Terra | failed | centered moment mismatch |
| dropped 80-bit | 29433254 | Gemini 3.8 Flash | failed | wrong A count |
| easy | 172266835 | Gemini 3.8 Flash | failed | 65 symbols |
| easy | 1809036836 | GPT-5.6 Terra | failed | broken reflection pair |
| easy | 814458196 | GPT-5.6 Terra | solved | ok |
| medium | 719264926 | Gemini 3.8 Flash | failed | empty length-limited reply |
| medium | 293687318 | GPT-5.6 Terra | failed | 62 symbols |
| medium | 881595053 | Gemini 3.8 Flash | solved | ok |
| hard | 1133811176 | GPT-5.6 Terra | failed | centered moment mismatch |
| hard | 142846350 | Gemini 3.8 Flash | failed | broken reflection pair |
| hard | 1317123207 | Gemini 3.8 Flash | failed | 65 symbols |

## G9 arms

| arm | solved/attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 1/3 | one verified solution |
| placebo hint | 1/3 | one verified solution |

`hinted − placebo = 0.0`, so this three-sample diagnostic gives no evidence that the structural sentence helped beyond adding a hint-like sentence. The scratch harness's stop metadata says `cap_bound` because its generic counter treats the whole string as one atom after the shipping-only copy returns no escalation; the transcript records themselves are the relevant evidence. In the module and G9 gate, the word is correctly counted as 64 semantic atoms.

## Use

```python
from gen_2506_11429 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer("<answer>ABBABBAAABBABAAB</answer>")
print(verify(inst, answer))
```

From the repository root, emit shipping records with:

```bash
bash scripts/emit.sh 2506.11429 20 hard
```

## Caveats

The density is exact for the declared prior—uniformly choosing 16 of the 32 visible reflection pairs—and says nothing about an informed construction-aware solver. Such a solver is deliberately efficient; this is why the family is Track B. The large coefficients make its 127 exact operations awkward without tools even though the output is short, so some difficulty may come from arithmetic execution as well as invariant discovery.

The attack panel did not run an external LLL, ILP, or SMT package. It instead includes a complete exact meet-in-the-middle search over the full certificate language, plus the faster construction-aware recovery. A solver that recognizes the full weighted Boolean cube can solve every instance. The G9 structural and placebo rates are only three samples each, and their equality does not prove that the invariant is irrelevant. Finally, the current script pool had two vendors rather than the four described by older task prose; `.meta.json` records the actual pool.
