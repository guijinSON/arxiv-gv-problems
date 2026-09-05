# Kingdomino reduction packing generator (parked)

This build is **not shipped**.  All local correctness gates pass, but the required
oracle loop ended `budget_bound`: every tested rung had at least one verified solve.
The module and transcripts are retained for a future run with a larger hardening
budget; there is deliberately no `REJECTED.md`.

| profile field | value |
|---|---|
| Track | B — an efficient algorithm exists and is reported |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | `m × 4` exact integer packing matrix |
| Intuition | invariant: synchronize four signed residue rows by their cyclic gap word |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 5, Theorem 1 |

This is not coordinate-level native Kingdomino coverage.  It preserves the complete
run-length encoded domino gadget, colors, crowns, order, and target-score formula,
but the solver returns the 4-Partition packing consumed by the theorem's forward
construction.  The enormous list of grid coordinates produced afterward is omitted.

## Problem and trust boundary

[Nguyen, Perrot, and Vallet, *NP-completeness of the game Kingdomino*
(arXiv:1909.02849)](https://arxiv.org/abs/1909.02849) defines K-tilings in Section 3.
Dominoes arrive in order on an unbounded integer grid, must be placed exactly when a
same-color/tower-adjacent placement exists, and score region area times crown count.
A chronological placement list is polynomial-time checkable.

Theorem 1 in Section 5 reduces strongly NP-complete 4-Partition to this K-tiling
problem.  It multiplies every item and bin size by 28 and builds guardians, square,
contour, guide, arm, anchor, item, and zipper gadgets.  Its forward proof constructs a
target-score tiling from any partition into four-item groups of equal sum.  This
generator samples those groups first, then shuffles the item labels, so it knows the
certificate without solving the generated instance.  `verify` reads no planted
answer: it checks matrix shape, exact item coverage, one member of each forced
magnitude band, every integer sum, and the theorem's score formula.

The paper explicitly omits the official 5×5/7×7 board bound, and its conclusion
leaves bounded-color hardness open.  This family therefore uses exactly the theorem's
unbounded board and growing-color regime.

## Why Track B

Track A would be false for this distribution.  The reference algorithm indexes all
A+B and C+D pair sums, then runs exact-cover backtracking on the matching quartets.
At the provisional hard preset it solves 8/8 instances in an average 0.004932 seconds,
with 7,200 pair additions/lookups, 166 candidate quartets, and 61 search nodes.

The compact route is different: a concealed power-of-ten modulus turns the four
magnitude bands, with signs `+,+,-,-`, into rotations of one cyclic gap word.  The
unique long gap synchronizes the rows, after which corresponding ids are zipped.  At
`n=240` this uses at most 243 exact gap/rotation operations.  The gap is between a
small structural route and thousands of mechanical operations, not a claim that the
instances resist software.

Section 4's brute-force counts motivate the combinatorial explosion but do not prove
this distribution hard.  The actual oracle evidence below controls that claim—and it
did not harden.

## Worked demo (`seed=3`)

A person can solve this two-bin packing on paper by checking the eight possible
balanced matchings.  This is the complete rendered statement:

```text
KINGDOMINO REDUCTION — COMPRESSED PACKING WITNESS

A domino has two unit cells.  A cell is (color,crowns), where crowns is
a nonnegative integer.  Dominoes arrive in the listed order on the
unbounded integer grid.  Starting from a tower at (0,0), an arriving
domino must occupy two unused edge-adjacent cells iff some placement has
one cell edge-adjacent to the tower or to an earlier cell of the same
color; otherwise it is discarded.  A monochromatic edge-connected region
scores (number of cells) times (crowns in the region), and total score is
the sum over regions.

This instance is the exact run-length gadget of Theorem 1 of the cited
paper.  It encodes a 4-Partition instance: all n items must be split into
m=n/4 unordered groups of exactly four, each summing to K.  The theorem's
forward construction turns such a packing into a K-tiling of score S.
Your answer is that packing as an exact integer matrix; you do not output
the enormous coordinate-by-coordinate placement list.

n = 8
m = 2
K = 261200
The theorem uses scaled item sizes x_i=28*a_i and scaled bin size 7313600.
Its target Kingdomino score is S = 25597997.

Compressed domino sequence (R^q means q consecutive copies of R):
  guardians: (1*,1),(2,2),(3,3),(4,4)
  square: (1,1)^66
  contour: (1,5*),(5,6*),(6,7*),(7,8*),(8,1),(8,1),
           (8,2),(8,9*),(9,9)^10,(9,10*), then
           (c,(c+1)*) for c=10,...,17, then (18,5)
  guide: (6,7)^96
  arms: for j=0,...,2, (10+3j,11+3j)^1828402
  anchors: for j=0,...,1, two copies of (12+3j,19)
  items: for item i of scaled size x_i, one
         (19,(19+i)*) followed by x_i/2-1 copies
         of (19+i,19+i)
  zippers: for j=0,...,1, (11+3j,(28+j)*) then
           (28+j,13+3j)
Here * means one crown on that cell; an unstarred cell has zero crowns.

The original item sizes a_i are below as id:size.  The four displayed
magnitude bands A,B,C,D are forced by the separated size ranges: every
four-item group summing to K contains exactly one item from each band.
Item ids are 1-based and distinct.  The order within a displayed band has
no semantic force and is not part of the certificate.

Band A:
  5:11130  3:10547
Band B:
  6:20967  4:21584
Band C:
  8:52086  7:52269
Band D:
  1:176800  2:177017

Return an m-by-4 integer matrix whose rows are the groups.  Every id
1,...,n must occur exactly once; each row must contain four distinct
ids, one from each displayed band, whose sizes sum exactly to K.
Within every row write ids in strictly increasing order, then sort the
rows lexicographically.  Any packing satisfying these checks is
accepted; no hidden planted answer is compared.

Give your final answer inside <answer></answer> tags, as a JSON object
with exactly the key "groups". Example for n=8:
<answer>{"groups":[[1,3,5,8],[2,4,6,7]]}</answer>
Output nothing else inside the tags.
```

The actual answer is
`{"groups":[[1,3,4,7],[2,5,6,8]]}`.  `verify` returns `(True, "ok")`.
Swapping the first two ids without restoring canonical order returns
`(False, "ids inside every group must be distinct and strictly increasing")`.

## Difficulty and status

| preset/rung | n | hidden modulus | answer atoms | bare oracle solves |
|---|---:|---:|---:|---:|
| demo | 8 | 100 | 8 | skipped by harness |
| easy | 96 | 10,000 | 96 | 1/3 |
| medium | 160 | 1,000,000 | 160 | 1/3 |
| hard (provisional `SHIPPING_DIFFICULTY`) | 240 | 100,000,000 | 240 | 1/3 |
| escalated | 252 | 100,000,000 | 252 | 1/3 |
| escalated | 252 | 10,000,000,000 | 252 | 2/3 |
| escalated | 252 | 1,000,000,000,000 | 252 | 1/3 |
| escalated | 252 | 100,000,000,000,000 | 252 | 1/3 |

No preset ships.  The `.meta.json` verdict is `budget_bound`; the next harness rung
would keep 252 atoms and raise the modulus again.  `SHIPPING_DIFFICULTY="hard"` is
retained solely as the provisional local-gate preset, not as a release claim.

## Gate measurements

| gate | result |
|---|---|
| G1 | 12/12 planted witnesses verify; all answers JSON round-trip |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic prose/fence/tag response round-trips |
| G4 | 0/200,000 balanced guesses; candidate space `(60!)^3` |
| G5 | demo has exactly 1 solution; hard density sample 0/200,000; reference cost 7,200 pairs + 61 nodes |
| G6 | all five attacks 0/8; reference and compact solvers 8/8 as Track B requires |
| G7 | `n=480` builds and verifies; pair-index work grows 7,200→28,800 |
| G8 | 80/80 relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | 984 chars, 246 estimated tokens, 240 atoms, 243 intended operations |

The five failing attacks are same displayed rank, reversed non-anchor ranks,
magnitude rank, greedy residual-pair matching, and 256 balanced random restarts.

## Oracle loop

| rung | solved/3 | failed replies |
|---|---:|---|
| easy | 1 | wrong row count; wrong sum |
| medium | 1 | two wrong row counts |
| hard | 1 | two empty length-limited replies |
| n=252, M=10^8 | 1 | wrong row count; empty length-limited reply |
| n=252, M=10^10 | 2 | noncanonical/duplicate ids |
| n=252, M=10^12 | 1 | wrong row count; empty length-limited reply |
| n=252, M=10^14 | 1 | wrong row count; noncanonical/duplicate ids |

Every solve parsed and passed `verify`.  There were no API errors.  The formal verdict
is `budget_bound`, so it would be dishonest to call the family hardened.

## G9 diagnostic arms

| arm | solved/attempts | status |
|---|---:|---|
| bare | 1/3 | provisional hard preset, from the main loop |
| structural hint | 0/0 | not run: no shipping level exists |
| placebo hint | 0/0 | not run: no shipping level exists |

`hinted − placebo` is therefore undefined.  Running paid hint arms against a level
already defeated by the bare pool would not establish shipping suitability.  The
measured provisional-hard size is 984 characters / 246 estimated tokens / 240 atoms;
the compact route is bounded by 243 exact operations.

## Use

From this result directory:

```python
import gen_1909_02849 as g

params = g.DIFFICULTY["demo"]
inst = g.make_instance(seed=3, **params)
text = g.render(inst)
answer = g.parse_answer('<answer>{"groups":[[1,3,4,7],[2,5,6,8]]}</answer>')
assert g.verify(inst, answer) == (True, "ok")
```

Local validation is `python3 gen_1909_02849.py`.  If a future hardening run produces
`hardened`, emission from the repository root is:

```bash
scripts/emit.sh 1909.02849 20 hard
```

Do not emit the current parked build as corpus data.

## Caveats

- The answer is a packing surrogate licensed by the paper's central reduction, not a
  coordinate placement sequence; this row must not count as native grid-geometry
  coverage.
- The 0/200,000 figure uses the strongest freely deducible balanced prior—one item
  from each magnitude band—but it measures random guessing only.  It emphatically
  does not imply model hardness; the oracle loop supplies contrary evidence.
- The reference exact-cover implementation is standard-library code, not an external
  ILP/CP-SAT package.  Pair sums make this generated distribution easy for software,
  as Track B declares.
- No spectral or lattice attack is relevant to the stated packing core.  No external
  ILP relaxation was run.  The exact pair-sum attack is stronger for the generated
  equality structure.
- The provisional hard answer is close to both the 256-atom and 300-operation caps.
  Increasing `n` further would become a transcription test; later escalations only
  enlarged the numeric range, and that axis still did not hold consistently.
- The official finite Kingdomino board and bounded-color cases are not covered; the
  paper itself does not prove hardness there.
