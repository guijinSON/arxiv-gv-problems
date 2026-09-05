# Inverse-affine sign reconstruction for generalized Sudoku

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | permutation |
| certificate form | exact symbolic (`{"v":…, "w":…, "a":…, "b":…}`) |
| intended intuition | invariant — hidden prime-field translations and probe cross-ratios |
| domain essentiality | native |
| reduction | none; the solver receives the paper’s Section 2 objects directly |

This module is based on Thomas Fischer, [“A Necessary Solution Condition for
Sudoku”](https://arxiv.org/abs/1210.6343). It gives the solver three partitions
of `n²` cells and the exact comparison signs `sgn(A_pi x)` for one partition.
The requested four residues define every cell value by a displayed
inverse-affine formula. `verify` expands that formula, checks every sign and
given, and checks that every row, column, and region is exactly `{1,…,n}`. It
never reads `inst["answer"]`.

Trust status: all local G1–G9(c) gates pass, but the family is **not ready to
ship**. A scored bare run showed that Gemini solved `easy`, `medium`, `hard`,
and the first escalation (`n=71`); Terra failed its attempts. The next rung,
`n=73`, has one scored Terra failure, after which the OpenRouter account hit
its total key limit before Gemini could be scored. There is therefore no
script-owned verdict, and the hinted/placebo diagnostics remain unrun.

## Family and construction

Section 2 defines generalized Sudoku as `n²` integers in `1..n`, three
permutations of a block-diagonal pair-comparison matrix, and optional givens.
Lemmas 3.2 and 3.3 show that the componentwise-nonzero comparison constraints
mean exactly that each induced group contains all `n` symbols. Section 3
identifies the ordinary row, column, block, Latin-square, and gerechte-design
special cases. The module retains those native cells, groups, integer values,
and comparisons; it does not compile them into a graph, SAT instance, or
finite-field surrogate.

For prime `n`, construction gives hidden coordinates `(r,c)` to the cells and
uses the three paper partitions `r`, `c`, and `r+c`. It samples

```text
2 <= v < n,  0 <= w < n,  1 <= a < n,  4 <= b < n
x(r,c) = 1 + (a*inv(r + v*c + w) + b mod n),  inv(0)=0.
```

The inner form is bijective along all three partition directions because
`v` is neither `0` nor `1`; field inversion and the outer affine map are also
permutations. Thus the planted formula is a generalized-Sudoku solution by
construction. Cell IDs and all group IDs are independently permuted. Four
probe cells are chosen to have ranks 1, 2, 3, and 4. The coefficients and all
signs are known before emission—generation never solves its own instance.

## Why Track B

This is explicitly not a Track A hardness claim. Theorem 5.1 gives

```text
x = (A_pi^T sgn(A_pi x) + (n+1)1) / 2,
```

so full sign-rank reconstruction is `O(n³)`. At hard (`n=67`) the reference
implementation performs 148,137 sign inspections and 148,137 rank increments,
296,274 core operations total, in 0.0574 seconds in the recorded self-test; it
solves 8/8 instances, as a Track B reference should.

The compact route compares the origin and row-unit incidence rows. Their
region-label transition is one translation cycle, which fixes the hidden field
coordinates. The four probe ranks are `1,2,3,4`, and their hidden column
coordinates are `0,1,2,3`. Equality of cross-ratios cancels the quadratic term
and leaves one linear equation for `v`; two difference equations recover `w`
and `b`, then one product recovers `a`. The conservative count is 126 exact
arithmetic operations plus 264 sign reads. That is the claimed no-tool gap.

The paper itself supplies the easy-regime warning: Section 1 names brute
force, pencil-and-paper methods, branch-and-cut, and Algorithm X; Section 3
notes successful exact-cover software. The paper has no theorem establishing a
hard distribution. Those facts rule out Track A but do not erase the measured
compression gap above.

## Worked demo

This is the complete `render(make_instance(n=7, seed=0, givens=0))` output:

```text
Recover a compact exact solution of this generalized Sudoku.

Definitions and instance semantics.
There are 49 cells and 7 symbols, the integers 1 through 7.
Cell IDs and all group IDs are 0-indexed integers from 0 through 6
for groups, and 0 through 48 for cells.
Each cell belongs to one R (row), one C (column), and one B (region) group.
Every group has exactly 7 cells. A generalized-Sudoku solution assigns
each group the complete set {1,...,7}, with no repeats.

For every R group, an ORDER and exact upper-triangular comparisons are
supplied. On line i (0-indexed), the sign string compares ORDER[i] with
ORDER[i+1],...,ORDER[n-1], in that order. Thus its length is n-i-1.
'>' means ORDER[i]'s solution value is greater and '<' means smaller.
Together these are exactly the paper's comparison vector sgn(A_pi x).

The incidence data has a unique normalized coordinate system over the
field of residues modulo n. Write its labels as rlabel[R], clabel[C],
blabel[B]. The named anchors impose: the origin's R,C,B labels are 0;
the row-unit's R and B labels are 1; and the column-unit's C and B labels
are 1. Every cell then obeys blabel[B] = rlabel[R]+clabel[C] modulo n.
You may derive these labels, but you do not output them.

Your witness must be exactly one JSON object with keys v,w,a,b. They obey
2<=v<n, 0<=w<n, 1<=a<n, and 4<=b<n. For a residue z, define inv(0)=0
and inv(z) as the unique residue q in 1,...,n-1 with z*q=1 modulo n.
The represented cell value is
  1 + ((a*inv(rlabel[R] + v*clabel[C] + w) + b) modulo n).
It must satisfy every displayed comparison, every given, and all three
generalized-Sudoku partitions. Integers are written in ordinary decimal.

ANCHORS
origin=31
row_unit=26
column_unit=24
END_ANCHORS

REDUNDANT NORMALIZATION SLICE (derived from the cell partition)
The next lines only save incidence lookup; they add no constraint.
ORIGIN_GROUPS R=4 C=1 B=6
ROW_UNIT_GROUPS R=2 C=1 B=3
COLUMN_UNIT_GROUPS R=4 C=0 B=3
C_TRANSITIONS (C:B_on_origin_R:B_on_row_unit_R)
0:3:0
1:6:3
2:1:4
3:4:6
4:0:5
5:5:2
6:2:1
END_C_TRANSITIONS
R_ZERO_COLUMN (R:B_at_origin_C)
0:5
1:0
2:3
3:1
4:6
5:2
6:4
END_R_ZERO_COLUMN
END_NORMALIZATION_SLICE

DISTINGUISHED PROBES (P-index:cell; these add no constraint)
P0:26
P1:41
P2:14
P3:12
END_PROBES

REDUNDANT PROBE COMPARISON ROWS
Each SIGNS string compares the named probe with every cell in its ORDER;
'=' marks the probe itself. These rows repeat information from the upper
triangles and exist so that four ranks can be read without bulk expansion.
P0 CELL 26
ORDER 47,14,26,3,18,33,48
SIGNS <<=<<<<
P1 CELL 41
ORDER 39,0,2,41,37,12,23
SIGNS <<<=><<
P2 CELL 14
ORDER 14,18,26,3,47,48,33
SIGNS =<><<><
P3 CELL 12
ORDER 0,12,23,39,41,37,2
SIGNS <=><>><
END_PROBE_ROWS

GIVENS (cell:value; an empty block means there are none)
END_GIVENS

CELL PARTITIONS AND ROW COMPARISONS
R 0 CELLS cell:C:B 2:2:3 39:1:5 37:4:1 41:0:2 23:6:6 0:3:0 12:5:4
ORDER 2,39,37,41,23,0,12
U0 2 >>>>>>
U1 39 >>><>
U2 37 <<<<
U3 41 <<<
U4 23 <<
U5 0 >
U6 12 -
END_R 0
R 1 CELLS cell:C:B 7:4:2 15:6:4 11:1:0 44:2:6 32:0:5 10:5:1 36:3:3
ORDER 7,15,11,44,32,10,36
U0 7 <><>><
U1 15 >>>>>
U2 11 <><<
U3 44 >>>
U4 32 <<
U5 10 <
U6 36 -
END_R 1
R 2 CELLS cell:C:B 48:3:6 33:2:4 18:0:0 14:4:5 47:5:2 3:6:1 26:1:3
ORDER 48,33,18,14,47,3,26
U0 48 <<<<<>
U1 33 >><<>
U2 18 ><<>
U3 14 <<>
U4 47 >>
U5 3 >
U6 26 -
END_R 2
R 3 CELLS cell:C:B 43:5:3 22:4:6 20:1:1 21:3:2 27:0:4 30:2:5 35:6:0
ORDER 43,22,20,21,27,30,35
U0 43 <<<<<>
U1 22 <><>>
U2 20 >>>>
U3 21 <<>
U4 27 >>
U5 30 >
U6 35 -
END_R 3
R 4 CELLS cell:C:B 8:6:2 29:5:5 46:3:4 5:4:0 42:2:1 24:0:3 31:1:6
ORDER 8,29,46,5,42,24,31
U0 8 <><>>>
U1 29 ><>>>
U2 46 <<<<
U3 5 >>>
U4 42 <<
U5 24 <
U6 31 -
END_R 4
R 5 CELLS cell:C:B 1:4:4 25:0:1 13:3:5 16:5:6 28:6:3 17:1:2 40:2:0
ORDER 1,25,13,16,28,17,40
U0 1 <<><<<
U1 25 <>><>
U2 13 >>>>
U3 16 <<<
U4 28 <>
U5 17 >
U6 40 -
END_R 5
R 6 CELLS cell:C:B 34:3:1 6:0:6 45:2:2 19:4:3 4:1:4 38:6:5 9:5:0
ORDER 34,6,45,19,4,38,9
U0 34 <><>><
U1 6 >>>>>
U2 45 <<<<
U3 19 >>>
U4 4 ><
U5 38 <
U6 9 -
END_R 6
END_INSTANCE

Give your final answer inside <answer></answer> tags as the JSON object above.
Example syntax (the numbers below are only a format example):
<answer>{"v":2,"w":0,"a":1,"b":4}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"v":6,"w":3,"a":1,"b":5}</answer>`, and
`verify` returns `(True, "ok")`. Deleting `b` returns
`(False, "malformed answer keys: missing=['b'], extra=[]")`. A person can solve
this demo on paper: there are seven-step translation cycles, four seven-character
probe rows, and a small modular linear solve.

## Difficulty presets

| preset | n | candidate space | reference operations | rendered chars (seed 0) | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 630 | 294 | 4,259 | hand-solvable; hardener skips it |
| easy | 19 | 87,210 | 6,498 | 14,824 | solved by Gemini (2/3 overall) |
| medium | 43 | 2,887,794 | 77,658 | 88,269 | solved by Gemini (2/3 overall) |
| hard | 67 | 18,108,090 | 296,274 | 267,329 | solved by Gemini (1/3 overall); not shippable |
| escalated | 71 | 22,976,310 | 352,870 | not retained as a named preset | solved by Gemini (2/3 overall) |
| escalated | 73 | 25,749,144 | 383,688 | not retained as a named preset | inconclusive: Terra 0/1, then quota errors |

Increasing `n` grows the `O(n³)` sign haystack while the answer remains exactly
four residues. `escalate()` offers larger primes through 241, then returns
`None`: the next prime would exceed the 300-operation intended-route cap. It
does not misuse `cap_bound`, because the four-atom answer itself remains tiny.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 answers JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 prose/fenced/tagged answers parsed; garbage rejected |
| G4 | 0/200,000 structure-aware guesses in the exact 18,108,090-tuple language; 3.169 s |
| G5 | shipping density 0/200,000 sampled; demo exact count 1; reference 296,274 operations / 0.0574 s; 128 restarts failed in 0.00054 s |
| G6 | numeric-ID outlier fit, encounter-order fit, 128 restarts, and small-coefficient by-hand ansatz each 0/8; reference 8/8 |
| G7 | strict cost ladder; `n=137` (>2× hard) builds and verifies; first escalation `n=71` verifies |
| G8 | 80/80 genuine relabelling invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | the sole gate, G9(c), passes at 29 chars, 8 estimated tokens, 4 atoms, 126 exact operations; hint arms are diagnostic and pending |

Exact records are in `selftest_report.json`.

## Oracle loop and G9 arms

The bare script-owned run produced 13 scored calls before the key limit stopped
round 4. A level is defeated if any call solves it.

| level | scored seeds and outcomes | level result |
|---|---|---|
| easy, `n=19` | Terra 1147439122 failed; Gemini 1729789865 and 1776360952 solved | defeated |
| medium, `n=43` | Terra 1217656798 failed; Gemini 317635806 and 1434655086 solved | defeated |
| hard, `n=67` | Terra 6298249 and 689288054 failed; Gemini 1785851026 solved | defeated |
| escalated, `n=71` | Terra 1462848533 failed; Gemini 619292744 and 214608765 solved | defeated |
| escalated, `n=73` | Terra 1972586940 failed; four Gemini redraws returned HTTP 403 | inconclusive |

| G9 arm at current hard | solved / scored attempts | status |
|---|---:|---|
| bare | 1 / 3 | scored as part of the ladder; this rung is too easy |
| structural hint | 0 / 0 | not run after the quota was exhausted |
| placebo hint | 0 / 0 | not run after the quota was exhausted |

`hinted_minus_placebo` is `0.0` only because both diagnostic denominators are
zero; it supports no conclusion about the hint. The older G9 transcript files
contain only HTTP 403 responses and likewise establish no diagnostic result.

## Use

```python
from gen_1210_6343 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

Once the OpenRouter key limit is raised, rerun the bare ladder and both isolated
G9 arms. If an escalated rung holds, slide the named ladder as prescribed, copy
the G9 transcripts back, update `_ORACLE_EVIDENCE`, and regenerate the report.
Only after a rung holds should emission be attempted from the repo root:

```bash
bash scripts/emit.sh 1210.6343 20 hard
```

## Caveats

- The prime-field subfamily is highly structured and deliberately polynomial;
  it tests recognition and compression, not worst-case generalized-Sudoku
  hardness. Removing the sign data or the cycle structure creates a different
  problem.
- The four named probes are construction-specific, low-rank clues. They make
  the post-insight route writable; if their purpose is recognized together
  with the cross-ratio invariant, the instance is intended to become easy.
- `0/200,000` is a sampled frequency, not an exact hard-preset solution count.
  Its prior is honest and narrow: it samples uniformly from all and only legal
  `v,w,a,b` tuples. The demo’s exact count is one.
- No external SAT, SMT, ILP, or Algorithm-X package was run. On this exposed
  sign representation, the implemented paper-specific Theorem 5.1 route is
  strictly more direct, but other compression attacks may exist.
- The 266,004-character hard prompt can test navigation through exact data as
  well as mathematical insight. The redundant probe rows limit the intended
  route to 264 sign reads, but a future oracle failure must still be interpreted
  with that prompt-size caveat.
- `canonical_key` is complete for generated instances under input reordering
  and arbitrary cell/group relabelling. It deliberately does not collapse
  row/column transposition because the emitted signs single out R groups, and
  it is not a general isomorphism algorithm for arbitrary gerechte designs.
- Most importantly, the scored transcript proves that every completed rung is
  too easy for Gemini. The `n=73` round and both G9 diagnostic arms are blocked
  by the OpenRouter total key limit; this directory must not be submitted.
- The checked-in `scripts/harden.py` currently configures Terra and Gemini, not
  the four-vendor pool described in the task text. This run follows the
  script-owned pool; restoring a four-vendor harness would require a fresh run.
