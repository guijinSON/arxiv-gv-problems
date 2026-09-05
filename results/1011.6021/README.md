# Triangular-polynomial certificates for arXiv:1011.6021

> **Evidence status:** complete. All local gates pass. A fresh script-owned bare
> ladder held at `hard` (`n=1024`), and fresh isolated structural-hint and
> placebo arms each held 0/3 at that same shipping preset.

## Profile

| field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | CSP/SAT |
| certificate form | polynomial |
| intuition | invariant: rowwise XOR exposes a triangular quadratic permutation |
| domain essentiality | licensed reduction |
| reduction | paper-licensed; Section 3's central 3,4-SAT → BBD reduction |

## Problem and trust model

The source is Ananth and Dukkipati, [*Border basis detection is
NP-complete*](https://arxiv.org/abs/1011.6021). A solver receives a 3-regular
bipartite incidence table on two copies of `GF(2)^d`, the induced bounded-
occurrence 3,4-SAT formula, and a schematic specification of the sparse rational
polynomial system in the paper's reduction. The requested witness is the
coefficient tensor of a triangular quadratic Boolean permutation whose graph is
contained in the table. It is a succinct selector for the border terms produced
by the paper's proof.

Generation is inverse. The module first samples a triangular quadratic
permutation and three distinct nonzero XOR masks whose XOR is zero. The three
masked maps are perfect matchings and are all valid—there is no distinguished
plant. Their union is the table. Every edge variable occurs in exactly four
clauses, twice with each sign, so it meets every promise stated immediately
before the Section 3 reduction. The correctness theorem then carries any selected
matching to the paper's border-term set.

Verification does not read `inst["answer"]`. It checks the tensor shape and every
coefficient, evaluates the proposed polynomial on all sources, checks membership
in every table row, checks bijectivity and cubic target degrees, and substitutes
the selected edges in every endpoint clause. Thus validity of the requested map
is decided by exact `GF(2)` operations on the instance and answer; no search or
numeric approximation occurs.

## Why Track B

This is not a Track A claim. Section 3 proves worst-case NP-completeness for BBD,
not average-case hardness for this generated distribution. An exact algorithm is
known here: XOR the three targets in every row, interpolate the triangular
quadratic map, select one row-zero offset, and validate the result. It costs
`O(N (log N)^3)` exact operations. At shipping `N=1024`, the measured reference
count is 474,258 primitives and it solves 8/8 instances; the final local timing is
reported in `selftest_report.json`.

The compressed route uses only source zero, the ten unit vectors, and their 45
pair sums. It takes 112 row-center XORs, 145 cached interpolation XORs, and one
offset XOR: 258 exact `GF(2)^10` vector operations. That fits the formal no-tool cap but
is close to it, so the caveats below distinguish structural discovery from
arithmetic endurance.

## Worked demo

This is the complete output of `render(make_instance(n=8, seed=0))` with no hint:

```text
TRIANGULAR-POLYNOMIAL BORDER-BASIS CERTIFICATE

All bit positions below are 0-indexed from the least significant bit. Integers
0 through 7 represent the vectors GF(2)^3; vector addition is bitwise
XOR. The order of table rows and the order of the three targets in a row have no
mathematical meaning.

INSTANCE TABLE. Each row `x: y0 y1 y2` gives three distinct edges from a left
vertex x to right vertices y0,y1,y2. Every right vertex also has degree three.
Thus this is a 3-regular bipartite graph on two copies of GF(2)^3.
  0: 4 6 1
  1: 4 1 3
  2: 3 6 4
  3: 1 6 3
  4: 5 2 0
  5: 0 7 5
  6: 2 7 0
  7: 5 7 2

THE 3,4-SAT INSTANCE. Introduce one Boolean variable E_(x,y) for every displayed
edge. At each left vertex and at each right vertex, let its three incident edge
variables be e1,e2,e3 and include the two clauses

  (e1 OR e2 OR e3)  and  ((NOT e1) OR (NOT e2) OR (NOT e3)).

There are 24 variables and 32
clauses. Every clause has three distinct variables. Every edge variable occurs
exactly four times, twice positively and twice negatively; both signs occur and
no clause contains a variable and its negation. Selecting exactly one edge at
each left and right vertex therefore satisfies all clauses.

THE PAPER'S POLYNOMIAL SYSTEM. The following is a finite schematic specification
of the sparse rational polynomials in Section 3 of Ananth--Dukkipati; expanding
the forced degree-eight family is unnecessary. For each Boolean edge variable e
introduce x_e and xb_e. For each clause C_j introduce c_j and xc_j, and introduce
X. There are 113 indeterminates over Q. Let tC_e be the
product of the four c_j for clauses containing e or NOT e (the exponent of X is
zero), and define

  tE_e  = x_e * xb_e^2 * tC_e,
  tEb_e = x_e^2 * xb_e * tC_e.

The variable polynomial for e is tE_e+tEb_e. In clause C_j, replace a positive
literal e by tE_e*xc_j/c_j and a negative literal by tEb_e*xc_j/c_j, and sum the
three monomials. F1 contains every total-degree-eight monomial. For an edge e,
P_e contains tE_e*xc_j for its positive occurrences and tEb_e*xc_j for its
negative occurrences; R_e contains every monomial obtained by dividing a member
of P_e by one indeterminate of positive exponent. K_e contains tE_e, tEb_e, and
the four clause-polynomial monomials belonging to e. F2 contains each monomial
in (union R_e) minus (union K_e) as a singleton polynomial. The BBD instance is
the union of the variable, clause, F1, and F2 polynomials.

YOUR WITNESS. Give a triangular quadratic polynomial permutation H on d=3
bits. For each output bit i, its value is, in GF(2),

  H_i(x) = x_i + constant[i]
           + sum_{0<=j<i} linear[i][j] * x_j
           + sum_{0<=j<k<i} quadratic[i][pair(j,k)] * x_j*x_k.

The quadratic coefficients in row i are ordered lexicographically by pairs
(0,1),(0,2),...,(0,i-1),(1,2),...,(i-2,i-1). Empty rows are required. Because
the coefficient of x_i is fixed to one and no later input bit occurs, every
well-formed H is automatically a permutation. The checker evaluates H(x) for
all 8 sources and requires H(x) to be one of the three displayed targets.
Those edges form a perfect matching, hence a satisfying assignment.

The matching deterministically decodes to the paper's border certificate: choose
tEb_e from the variable polynomial when edge e is true and tE_e otherwise;
choose the lowest-listed satisfied literal's monomial in each clause polynomial;
choose the sole monomial of every singleton polynomial. The checker substitutes
the matching in every endpoint clause exactly. Section 3's reduction then gives
the corresponding border of an order ideal.

OUTPUT. Supply exactly three labeled JSON arrays in the order constant, linear,
quadratic. Every coefficient is the integer 0 or 1; strings and JSON booleans are
invalid. The constant block has 3 entries. Linear row i has i entries and
quadratic row i has C(i,2) entries. Here is a well-formed format example (not a
claim that the all-zero coefficients solve this instance):

  [["constant",[0,0,0]],["linear",[[],[0],[0,0]]],["quadratic",[[],[],[0]]]]

Give your final answer inside <answer></answer> tags as that exact JSON value.
Example: <answer>[["constant",[0,0,0]],["linear",[[],[0],[0,0]]],["quadratic",[[],[],[0]]]]</answer>
Output nothing else inside the tags.
```

One valid answer is:

```json
[["constant",[0,1,1]],["linear",[[],[0],[1,0]]],["quadratic",[[],[],[0]]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Changing the first
coefficient to `2` returns `(False, "every coefficient must be the integer 0 or
1")`. This smallest setting is hand-solvable: only seven coefficients are free,
the row-zero condition leaves 48 structured candidates, and exact enumeration
finds five valid tensors.

## Difficulty presets

| preset | points/side | dimension | free coefficients | evidence/status |
|---|---:|---:|---:|---|
| demo | 8 | 3 | 7 | hand example; skipped by hardener |
| easy | 256 | 8 | 92 | fresh bare run solved 1/3; rejected rung |
| medium | 512 | 9 | 129 | fresh bare run solved 1/3; rejected rung |
| **hard** | **1024** | **10** | **175** | **shipping rung; fresh bare run held 0/3** |

The next rung (`n=2048`, `d=11`) builds and verifies, but its compressed route
takes 311 operations and exceeds G9(c); `escalate()` therefore returns
`"cap_bound"`.

## Local gates

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify and JSON-round-trip |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged prose round-trips; garbage returns `None` |
| G4 | 0/200,000 structured guesses; bound `3^56 / (3·2^165) = 3.7301e-24` |
| G5 | demo exact count 5; shipping reference 474,258 operations, 0.013638 s |
| G6 | five attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | doubled instance has 2048 points and verifies |
| G8 | 80/80 invariant/carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 438 chars, 178 atoms, about 110 tokens, 258 operations |

The five failing attacks are minimum-target outlier selection, target-rank
greedy selection, a domain-standard bipartite matching followed by quadratic
force-fitting, 256 structure-aware random restarts, and the in-context
unshifted-center ansatz.

## Oracle evidence and G9 diagnostics

The completed bare ladder used the script's two-provider pool at medium reasoning
effort. Easy and medium were defeated; all three hard attempts failed, giving
`hardened` at the configured shipping preset. The raw records are preserved in
`llm_loop_transcript.jsonl`.

| bare call | seed | result |
|---|---:|---|
| easy, `openai/gpt-5.6-terra` | 1747539972 | failed; tensor missed source 2 |
| easy, `google/gemini-3.8-flash` | 989371968 | failed; no tagged answer parsed |
| easy, `google/gemini-3.8-flash` | 306855090 | solved |
| medium, `google/gemini-3.8-flash` | 893457495 | solved |
| medium, `openai/gpt-5.6-terra` | 1494885447 | failed; tensor missed source 1 |
| medium, `openai/gpt-5.6-terra` | 520280750 | failed; tensor missed source 0 |
| hard, `google/gemini-3.8-flash` | 1254707174 | failed; no tagged answer parsed |
| hard, `openai/gpt-5.6-terra` | 753348424 | failed; tensor missed source 0 |
| hard, `openai/gpt-5.6-terra` | 847432449 | failed; tensor missed source 2 |

| hard G9 arm | solved/attempts | interpretation |
|---|---:|---|
| bare | 0/3 | shipping rung of the fresh bare ladder |
| structural hint | 0/3 | the XOR invariant did not yield a valid tensor |
| placebo hint | 0/3 | matched control |

Hinted minus placebo is `0.0`. Naming the XOR invariant bought no measured
improvement at hard. This indicates that exact interpolation and writing the
coefficient tensor contribute materially alongside discovery of the invariant.
The arms are diagnostic under the current rules; the answer and route caps are
the gated part of G9.

## Use

```python
import json
import gen_1011_6021 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=7)
text = g.render(inst)
answer = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"], separators=(",", ":")) + "</answer>"
)
assert g.verify(inst, answer) == (True, "ok")
```

To reproduce the local gates and emit from the repository root:

```bash
python3 results/1011.6021/gen_1011_6021.py
bash scripts/emit.sh 1011.6021
```

## Caveats

- The family is easy with a sandbox: the disclosed XOR/interpolation algorithm
  solves it in milliseconds to fractions of a second. This is exactly why it is
  Track B.
- The paper's forced `F1` family contains every degree-eight monomial and is
  astronomically large at shipping size. It is specified schematically, not
  expanded. Accordingly this is `licensed_reduction`, not a native explicit-
  sparse-input BBD benchmark; the solver's search is the finite-field CSP.
- The output is a deliberately succinct border selector. A generic bipartite
  matching finds a satisfying assignment, but usually cannot be represented in
  the bounded triangular-quadratic language; matching-then-fit failed 0/8.
- The G4 prior already enforces the obvious row-zero constant and all tensor
  shape constraints. It does not model a solver that has discovered partial
  interpolation constraints, so 0/200,000 is not an average-case hardness proof.
  The analytic number is an upper bound, not an exact shipping solution count.
- The compact route is 258 operations against a 300-operation cap. Because the
  fresh structural hint did not help, this family may measure careful exact
  arithmetic as much as invariant discovery.
- The canonical key covers row/target reorderings and global source/target XOR
  translations. It does not solve equivalence under every lower-triangular
  change of Boolean coordinates.
- A generic SAT solver was not separately benchmarked because its arbitrary SAT
  assignment is not necessarily an admissible polynomial witness. The stronger
  polynomial-time matching relaxation and the exact list-recovery solver were
  measured. The current hardener pool contains two providers, so this evidence
  should not be read as a four-vendor comparison.
- The current repository hardener is configured for two providers rather than
  the four-vendor pool described by the original task text; the evidence therefore
  supports cross-provider, not four-vendor, robustness.
