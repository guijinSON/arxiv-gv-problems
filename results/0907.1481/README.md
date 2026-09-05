# Anchored Latin intercalates — arXiv:0907.1481

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | linear algebra |
| Certificate | integer tuple: the native four-cell trade support |
| Intended intuition | invariant: half-order differences survive every trade switch |
| Domain essentiality | native |
| Reduction | none |

This generator turns Carlo Hämäläinen’s [*Latin trades and simplicial
complexes*](https://arxiv.org/abs/0907.1481) into an anchored-intercalate
problem.  The solver receives an exact, compactly represented Latin square: a
back-circulant square, changed by cell-disjoint intercalate switches and
independently relabelled by reversible xorshift chains.  It must return the four
cells of the size-four trade through a stated anchor.  The checker evaluates
the four Latin-square entries and compares the two diagonals exactly; it never
reads the planted answer.

## Why this is Track B

Definition 1.1 fixes Latin squares, Definitions 1.2–1.3 fix bitrades, Example
1.4 licenses replacement of a trade by its mate, Section 2 defines the
back-circulant square `B_n`, and Section 2.1 defines intercalates.  The paper has
no hardness theorem or hard distribution, so Track A would be false.  Its Sage
source uses DLX for mate-finding and four nested loops for its intercalate scan.

An efficient algorithm for this generated distribution is stated openly.
Treat each public xorshift chain as a binary linear map and solve its
half-order preimage with bit-packed Gaussian elimination over GF(2).  The
implementation uses `O(n^2)` bit-packed row operations, or `O(n^3)` bit
complexity when the row widths are charged.  At the
shipping preset (`n=64`, seed 271828), it took **0.001983 s and 23,327 counted
operations**; across eight seeds it solved 8/8 at 23,115 operations per
instance.  That is easy for a machine but not executable in context by hand.

The compact route notices that adding `q/2` to both hidden cyclic coordinates
survives every listed switch.  Each map factor is `I+S` for a nilpotent bit
shift, so `(I+S)^-1 = I+S+S^2+...`; grouping powers by doubling the shift
distance reverses the chain directly.  At shipping seed 271828 this needs **107
exact operations**, versus the elimination route’s 23,327.  The generator uses
that identity by construction; it does not solve its own instance.

## Worked demo

The `demo` preset at seed 0 is hand-solvable.  Its complete rendered statement
is:

```text
Find the anchored intercalate in an implicitly represented Latin square.

Rows, columns, and symbols are integers 0 through 15, inclusive.
The order is q=16=2^4.  Values are exact nonnegative 4-bit
integers; XOR means bitwise exclusive-or.

Map chains.  A direction=left component with shift=s sends
  v to v XOR ((v left-shift s) modulo q).
A direction=right component sends v to v XOR (v right-shift s).
A chain applies its displayed components from left to right:
  rho   (public row -> internal row) = [{"type":"xorshift","direction":"right","shift":1},{"type":"xorshift","direction":"left","shift":1}]
  kappa (public column -> internal column) = [{"type":"xorshift","direction":"right","shift":1},{"type":"xorshift","direction":"left","shift":1}]
  sigma (internal symbol -> public symbol) = [{"type":"xorshift","direction":"right","shift":1},{"type":"xorshift","direction":"left","shift":1}]

Let h=q/2=8.  Given r,c, set x=rho(r), y=kappa(c),
and z=(x+y) modulo q.  If [x modulo h,y modulo h] belongs to
this switch set, replace z by (z+h) modulo q:
  [[1,1],[1,5]]
Then L(r,c)=sigma(z).  The switch list is a set; order is irrelevant.

An intercalate is a complete 2-by-2 rectangle on distinct rows r0,r1
and columns c0,c1 such that L(r0,c0)=L(r1,c1),
L(r0,c1)=L(r1,c0), and these two symbols are distinct.  Its four
entries are a partial Latin square; swapping the two symbols gives the
disjoint mate, so this is exactly a size-four Latin trade.

The rectangle must contain anchor [8,4].
Return its occupied cells as a JSON list of four [row,column] pairs.
They must be distinct and form the complete rectangle.  Pair order is
irrelevant; repeats are forbidden; all stated bounds are inclusive.

Give your final answer inside <answer></answer> tags, as that JSON list.
Example format: <answer>[[0,0],[0,7],[5,0],[5,7]]</answer>
Output nothing else inside the tags.
```

One answer is `[[8,4],[8,11],[7,4],[7,11]]`.
`verify(inst, answer)` returns `(True, "ok")`; deleting the final cell returns
`(False, "support must contain exactly four cells")`.

## Difficulty presets

| preset | bit dimension `n` | xorshift factors per map | switch pairs | status |
|---|---:|---:|---:|---|
| demo | 4 | 2 | 1 | hand-scale illustration |
| easy | 32 | 4 | 8 | oracle solved 1/3; rejected as shipping rung |
| medium | 64 | 5 | 16 | **ships; oracle solved 0/3** |
| hard | 96 | 6 | 24 | unused escalation |

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; direct demo Latin-square check |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | prose-tagged and fenced JSON both round-trip |
| G4 | pass | 0/200,000 guesses; exact probability `2.938735877055719e-39` |
| G5 | pass | exactly 1 valid shipping witness; Gaussian baseline 0.001983 s / 23,327 operations |
| G6 | pass | five attacks at 0/8; Gaussian reference 8/8 |
| G7 | pass | `n` doubled 64→128 while the answer stayed at 8 atoms |
| G8 | pass | 100/100 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 173 characters, 44 estimated tokens, 8 atoms, 107 intended operations |

## Oracle loop

| preset | seed | model | result | checker outcome |
|---|---:|---|---|---|
| easy | 2032813690 | GPT-5.6 Terra | failed | claimed no solution |
| easy | 505761526 | Gemini 3.8 Flash | failed | no final answer |
| easy | 194274635 | GPT-5.6 Terra | solved | `ok` |
| medium | 531284175 | GPT-5.6 Terra | failed | main diagonal mismatch |
| medium | 1788014130 | Gemini 3.8 Flash | failed | no final answer |
| medium | 703914612 | GPT-5.6 Terra | failed | main diagonal mismatch |

The script-issued verdict is `hardened` at `medium` after one escalation.  The
repository’s current harness intentionally uses two vendors and three attempts
per rung; the repeated vendor receives a distinct seed.

## G9 diagnostic arms

| arm | solved / attempts | result |
|---|---:|---|
| bare shipping calls | 0 / 3 | held |
| structural hint | 0 / 3 | held |
| placebo hint | 0 / 3 | held |

`hinted - placebo = 0.0`.  Naming the half-order invariant alone bought no
measured success, so the remaining difficulty appears to include correctly
executing the inverse xorshift chains, not only discovering the invariant.
This is diagnostic, not a gate.  The answer and intended route remain well
inside the G9(c) caps at 173 characters, 8 atoms, and 107 exact operations.

## Use

```python
import json
import gen_0907_1481 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 0907.1481
```

## Caveats

- This is deliberately Track B.  A normal machine solves it in milliseconds;
  the claim is no-tool compression, not computational intractability.
- `P(guess)` is exact for the declared prior: choose a uniformly random
  non-anchor row and non-anchor column, then return that complete rectangle.
  It does not model a solver that has already inferred either xorshift offset.
- The hint/placebo equality means the benchmark may mix invariant discovery
  with exact bit-chain execution.  The 107-operation route is below the cap but
  is not a one-line mental calculation.
- The failed attacks were greedy adjacent labels, visible public half-shifts,
  one-factor inversion, switch-coordinate leakage, and 256 random restarts.
  No external SAT/SMT or DLX package was run; bit-packed elimination is stronger
  for this distribution and was run successfully.
- `canonical_key` is invariant under tested public isotopies, odd affine hidden
  coordinate changes, transpose, and switch ordering.  It is a strong cheap
  valuation fingerprint, not a complete Latin-square isotopy canonical form;
  exotic isomorphic switch configurations could receive different keys.
