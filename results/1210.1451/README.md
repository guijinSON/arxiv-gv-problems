# arXiv 1210.1451 — verified resultant-root generator

**Status:** the module is complete and every local gate passes, but it is **not an accepted shipping family**. The required bare oracle run proved that the configured `hard` preset is too easy (3/3 verified solves) and then stopped during later escalation when the OpenRouter account reached its total limit. No `hardened`, `too_easy`, or bound verdict was produced. The script-owned partial transcript and both current G9 error transcripts are retained; none is being presented as a hardness pass.

| profile field | value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | subset sum |
| Certificate | normalized rational projective vector |
| Intuition | invariant: residue buckets contain equal-sum complementary pairs |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 2, Theorem 1 |

## Problem and provenance

The module turns the central construction in Grenet, Koiran, and Portier, [“On the Complexity of the Multivariate Resultant”](https://arxiv.org/abs/1210.1451), into a search problem. An instance is the paper's square homogeneous system

\[
F_0=\sum_{i=1}^{n}c_i x_i=0,\qquad F_i=x_0^2-x_i^2=0\quad(1\le i\le n).
\]

The solver must return one nonzero common root, normalized by \(x_0=1\), as exact rationals. `verify` substitutes the vector into every equation using exact arithmetic and accepts any valid normalized root.

Generation never solves its output. In each four-variable block it samples magnitudes of the form \(M(C+a)+r, M(C-a)+r, M(C+b)+r, M(C-b)+r\). The identity

\[
(M(C+a)+r)+(M(C-a)+r)=(M(C+b)+r)+(M(C-b)+r)
\]

gives the signs first. Independent variable sign changes and a permutation then carry that known root to the displayed system. This is a native algebraic object under the paper's own Partition reduction, not a graph or finite-field analogue.

Definition 1 fixes the resultant/common-root equivalence. Section 2, Theorem 1 proves worst-case NP-hardness via exactly these equations, even at degree at most two, but it does **not** prove this generated distribution hard. Section 2 also identifies the easy dense-bivariate regime, where the Sylvester matrix is polynomial-size. Section 4 describes Canny's polynomial-space Macaulay method and the exponential size of the general Macaulay matrix.

The family therefore declares Track B. Its disclosed reference solver is bitset subset-sum dynamic programming, with complexity \(O(nS/w)\) word operations. At the configured hard preset it solved 8/8 instances at a median 26,710,154 counted 64-bit word transitions and 0.084 s on this host. Once the modular invariant is noticed, grouping 48 magnitudes and orienting their equal-sum pairs takes at most 276 exact operations. The intended compression gap is real, but the oracle run showed that the invariant is exposed enough for current models to exploit, so the present parameters do not clear H.

## Worked demo

For `seed=11`, the complete demo data are:

```text
Variables: x_0,...,x_8.
F_0 = 168*x_1 + 139*x_2 - 188*x_3 + 159*x_4
      - 119*x_5 - 179*x_6 + 208*x_7 - 148*x_8 = 0.
F_i = x_0^2 - x_i^2 = 0 for i=1,...,8.
Return a rational vector in x_0,...,x_8 order, normalized by x_0=1.
```

One answer is:

```text
<answer>1/1, 1/1, -1/1, -1/1, -1/1, -1/1, -1/1, -1/1, 1/1</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing `x_1` by `2/1` returns `(False, "quadratic equation F_1 is nonzero")`. A person can solve this smallest setting on paper by grouping magnitudes with the same final digit and matching the two equal pair sums.

## Presets and local gates

| preset | n | modulus | center range | log2 candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 10 | 10–24 | 8 | hand-scale example |
| easy | 24 | 100 | 80–140 | 24 | oracle solved 3/3 |
| medium | 36 | 1000 | 140–240 | 36 | oracle solved 3/3 |
| hard | 48 | 1000 | 800–1200 | 48 | configured candidate; oracle solved 3/3, so it cannot ship |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; all answers JSON-round-trip |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | a 49-coordinate fenced response surrounded by prose round-trips |
| G4 | 0/200,000 structure-aware random sign vectors valid |
| G5 | hard density estimate 0/200,000; demo exactly 8/256 valid; DP median 26,710,154 word transitions |
| G6 | four no-tool attacks each 0/8; disclosed reference DP 8/8 |
| G7 | candidate-space exponents 8, 24, 36, 48; doubled `n=96` builds and verifies |
| G8 | 80/80 relabelling checks pass; 20/20 unrelated keys are distinct |
| G9(c) | 317 characters, 80 estimated tokens, 98 scalar JSON atoms, 276 intended operations; compact route 8/8 |

The first version of this construction failed G6 because Karmarkar–Karp found roots on 2/8 seeds. The current generator deterministically resamples presentations hit by that heuristic without searching for or modifying the planted witness. Variable permutation and sign switching address position/sign outliers; smallest-half, sorted alternation, 256 random restarts, and Karmarkar–Karp each scored 0/8 in the final panel.

## Oracle loop and G9 diagnostics

The bare transcript contains 17 scored calls and four final quota errors. A single verified solve defeats a level.

| round / parameters | seeds | scored result | conclusion |
|---|---|---:|---|
| easy | 1690162424, 177701301, 48298298 | 3 solved / 3 | defeated |
| medium | 98556768, 1009112574, 1977972665 | 3 solved / 3 | defeated |
| hard | 1139120026, 979795453, 1882818227 | 3 solved / 3 | defeated |
| escalated centers 3200–4800 | 502466635, 63232861, 425345199 | 2 solved, 1 invalid / 3 | defeated |
| escalated centers 12800–19200 | 251186798, 211678816, 1759963365 | 2 solved, 1 invalid / 3 | defeated |
| escalated centers 51200–76800 | 1454509121, 1819783527 | 1 solved, 1 invalid / 2 | defeated, then quota exhausted during redraws |

All non-solves parsed correctly; exact verification found nonzero `F_0` residuals. Thus there is no hidden output-contract false negative. The run has no final harness verdict because the third slot at the last tested scale exhausted all error retries.

| G9 arm at hard | solved / scored attempts | errors | conclusion |
|---|---:|---:|---|
| bare | 3/3 | 0 | too easy at the configured hard preset |
| hinted | unavailable | 4 | OpenRouter total-limit error |
| placebo | unavailable | 4 | OpenRouter total-limit error |

`hinted − placebo` is unavailable, not zero. The structural hint names only the invariant: “Modulo 1000, each four-coefficient residue bucket contains two complementary pairs with identical sums.”

## Use

```python
import gen_1210_1451 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + g._answer_text(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

If a future funded rerun produces a genuine hardened verdict and the ladder is updated to its held level, emit with `../../scripts/emit.sh 1210.1451 20 hard`. Do not emit the present candidate as a hardened family.

## Caveats

The decimal-residue structure is deliberately visible, and the bare oracle evidence shows that current models discover it reliably. Raising coefficient height alone did not cure that weakness. The 0/200,000 density is only an observed rate under uniform normalized sign vectors—every quadratic constraint is already enforced—and says nothing about structured guesses. Bitset DP is fast in wall time despite its large counted word workload, so no claim of computational hardness with tools is intended. Karmarkar–Karp, smallest-half, sorted alternation, random restarts, and exact DP were tested; a full LLL/CJLOSS attack and exhaustive meet-in-the-middle at `n=48` were not. The current result should remain parked until either a structurally less exposed construction is tested from a fresh oracle budget or the paper is formally rejected after a complete script verdict.
