# arXiv 1301.4764 — rejected three-way intersection prototype

**Status:** rejected on hardness; see [REJECTED.md](REJECTED.md). The native
construction and exact checker are sound, but scored oracles solved every level
from `easy` through the first automatic escalation. Later HTTP 403 quota errors
were not counted as model failures.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite_discrete |
| Computational core | other (exact block-intersection counting) |
| Certificate form | integer tuple |
| Intuition | decomposition |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

Rashidi and Soltankhah’s [The 3-way intersection problem for S(2,4,v)
designs](https://arxiv.org/abs/1301.4764) studies triples of block designs in
which every point-pair occurs in exactly one four-point block. An instance here
is a succinct recipe for three genuine designs and asks for two exact counts:
their common blocks in the weighted GDD ingredients and in the fillings. The
sum is the ordinary three-way intersection number.

The recipe is native to the paper. It uses Theorem 3.1’s weighting construction,
Theorem 3.2’s filling construction, Lemma 4.5’s five 4-GDD ingredients, and
Lemma 4.1’s seven S(2,4,13) fillings. Verification intersects each small fixed
catalog exactly and evaluates two integer weighted sums. It does not read the
planted answer.

## Why Track B

This is not a Track A hardness claim. The domain-standard algorithm generates
every block and hash-intersects the three sets in
`O(v^2 n)` finite-field/block operations. At the shipping preset it generated
4,187,139 blocks, made 2,791,426 hash probes, and took 25.176041 seconds on the
audit host. It succeeds, as expected.

The compact route is the identity in the proof of Theorem 5.1:
`sum(alpha_i) + sum(beta_j)`. Residue selectors are permutations of complete
periods, so only the run multiplicities matter. Deriving all twelve small
catalog intersections and evaluating the two sums costs 195 small-block
membership/integer operations. Without noticing the disjoint-support
decomposition, the rendered recipe appears to require expanding 1,395,713
blocks per design.

The easy regime deliberately avoided is the paper’s classification question:
Theorem 1.1 gives the complete feasible spectrum for admissible `v >= 49`, so
asking only whether an intersection number exists is a constant-time lookup.
This family asks for the exact profile of a supplied construction instead.

## Worked demo (`n=1`, seed 0)

This smallest instance is hand-scale: there are no outer master blocks, and a
person can apply the two displayed permutations to the thirteen filling blocks
and find the five blocks common to all three. A representative rendering is:

```text
Three-way intersection profile for S(2,4,v) designs

An S(2,4,v) design is a set of 4-element blocks on v points in which every
unordered pair of distinct points occurs in exactly one block.  A block is
common to three designs when the identical unordered 4-set occurs in all three.

This instance succinctly defines three such designs by a weighting construction
followed by fillings.  All indexing below is 0-based; intervals are inclusive;
cycle notation maps each entry to the next and the last back to the first;
unmentioned labels are fixed.  Blocks and designs are sets, so their order is
irrelevant and no block is repeated.

1. Master 4-GDD.
Use GF(4)=F_2[z]/(z^2+z+1), encoded by 0,1,z,z+1 as 0,1,2,3.
Addition is bitwise XOR and z^2=z+1.  Points are vectors in GF(4)^1.
A direction is normalized by making its first nonzero coordinate 1.  For each
direction u, the nonzero points on its line through zero form one 3-point group.
Every affine line not through zero is a master block.  Directions are ordered by
increasing position of the first nonzero coordinate and then by lexicographic
suffix; the unique representatives whose pivot coordinate is zero are ordered
lexicographically, omitting the all-zero representative.
There are u=1 groups and m=0 master blocks.

2. Weight every nonzero master point by four copies.
There are no master blocks at this order, so this step contributes no blocks.

3. Fill every 12-point weighted group together with one shared infinity point.
The base S(2,4,13), on labels 0,...,9,a,b,c, has these 13 blocks:
{0,1,3,9} {0,2,8,c} {0,4,5,7} {0,6,a,b} {1,2,4,a} {1,5,6,8} {1,7,b,c} {2,3,5,b} {2,6,7,9} {3,4,6,c} {3,7,8,a} {4,8,9,b} {5,9,a,c}
Here label 0 maps to infinity and labels 1,...,c map in order to the twelve
weighted points of that group.  The filling-template triples are:
  L0: p2=id; p3=id
  L1: p2=(0 1 2 3 4 5); p3=(5 4 3 2 1 0)
  L2: p2=(8 5)(a b)(3 7)(1 6); p3=(8 6)(1 5)(a 3 b 7)
  L3: p2=(7 b c 6); p3=(8 5 6 7)
  L4: p2=(4 7)(9 2)(1 8); p3=(3 9 c)(1 8)
  L5: p2=(3 7)(c 0 2)(1 6)(9 b); p3=(9 4)(3 7)(0 2)(1 6)
  L6: p2=(a b)(4 5); p3=(a b)(c 8)

For group index j=0,...,0, compute
r=(0*j+0) mod 1.
Choose the template from this run table:
  0..0:L6

The union of all weighted ingredient blocks and all filling blocks is each final
design.  Finally, the three designs are presented in source-column order
[1, 2, 0].  Points are simultaneously renamed by coordinate order
[0], nonzero GF(4) scales [2], and copy
permutation [0, 2, 1, 3]; infinity remains fixed.  This last renaming
does not alter equality of blocks.

The final order is v=13; each design has 13
blocks, split into 0 weighted-ingredient blocks
and 13 filling blocks.

Find TWO exact integer counts: (i) blocks common to all three designs in the
weighted ingredients, and (ii) blocks common to all three in the fillings.

Give your final answer inside <answer></answer> tags, as outer, filling.
Example: <answer>240, 17</answer>
Output nothing else inside the tags.
```

The answer is `<answer>0, 5</answer>`.
`verify(inst, [0,5])` returns `(True, "ok")`;
`verify(inst, [0,6])` returns
`(False, "filling common-block count is incorrect")`.

## Difficulty presets

| Preset | n | v | Blocks/design | Selector cap | Status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 13 | 13 | 1 | hand-solvable illustration |
| easy | 2 | 61 | 305 | 15 | defeated, 2/3 solved |
| medium | 4 | 1,021 | 86,785 | 255 | defeated, 3/3 solved |
| hard | 5 | 4,093 | 1,395,713 | 600 | defeated, 2/3 solved |

`hard` was the candidate shipping preset, but it cannot ship. The automatic
`n=6, period_cap=1200` level was also defeated by both scored calls before quota
exhaustion stopped the remaining call.

## Gate results

| Gate | Result |
|---|---|
| G1 | 12/12 planted certificates verified; expanded S(2,4,61) pair audit passed |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose/fence/tag round-trip passed |
| G4 | 0/200,000 structure-aware guesses; exact density 1/39,804,018 |
| G5 | one valid candidate profile; reference 25.176041 s, 6,978,565 recorded operations |
| G6 | 0/8 successes for each of five in-context attacks; reference succeeds |
| G7 | next instance has v=16,381 (4.002x) with the same four answer atoms |
| G8 | 80 invariance, 80 real-transform, 20 selector-semantic, and 20 distinct-key checks passed |
| G9(c) | 13 chars, 4 estimated tokens, 2 atoms, 195 operations; caps passed |

## Oracle loop

The scored rows below are hardness evidence; the later infrastructure errors
are not. The harness aborted during round 3 after exhausting its redraw
allowance, but every tested level had already been defeated by a valid answer.

| Arm | Preset | Scored calls | Solved attempts | Result |
|---|---|---:|---:|---|
| bare | easy | 3 | 2/3 | defeated |
| bare | medium | 3 | 3/3 | defeated |
| bare | hard | 3 | 2/3 | defeated |
| bare | escalated `n=6` | 2 | 2/2 | defeated before quota abort |
| structural hint | hard | 0 | 0/0 | prior transcript contains only quota errors |
| placebo hint | hard | 0 | 0/0 | prior transcript contains only quota errors |

Thus `hinted - placebo` is unavailable. No G9 conclusion is used in the
rejection: the bare family itself was repeatedly solved.

## Use

```python
import rejected_gen_1301_4764 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=42)
print(g.render(inst))
candidate = g.parse_answer("<answer>123, 45</answer>")
print(g.verify(inst, candidate))
```

Run the preserved prototype's local gates with
`python3 results/1301.4764/rejected_gen_1301_4764.py`. Do not emit it as a
shipping family.

## Caveats

- The module is intentionally rejected: bare oracles solved all tested levels.
- G4 samples uniformly from both stated numerator ranges with denominators fixed
  to one. It measures blind profile guessing, not a solver using the residue
  multiplicities or a prior over likely intersection values.
- The successful expansion baseline uses hashing, not a specialized design
  isomorphism or symbolic-algebra package. No SAT/ILP formulation was tried
  because exact evaluation, rather than construction search, is the task.
- `canonical_key` canonicalizes the outer and filling ingredient-template
  multiplicity vectors, so final point labels, design-column order, selector
  origin, and their composition do not affect it. Full block-design isomorphism
  outside this profile semantics is not attempted.
- The compact route depends on complete selector periods. If the statement were
  changed to truncate periods irregularly, the claimed 195-operation route and
  Track B rationale would need to be remeasured.
