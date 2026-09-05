# arXiv:2405.20263 — verified generalized tournament orientations

| profile field | value |
|---|---|
| `TRACK` | **B** — no-tool compression |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP/SAT (an affine orientation CSP) |
| certificate form | matrix certificate |
| intended intuition | invariant: vertex switching preserves cycle parity |
| domain essentiality | native |
| reduction | paper-licensed by Section 1.3 and Theorem 2 |

This is a native generalized graph-orientation problem from Roman Feller and
Michael Pinsker, [*An algebraic proof of the dichotomy for graph orientation
problems with forbidden tournaments*](https://arxiv.org/abs/2405.20263).  The
solver receives a complete undirected graph and labelled clique constraints,
then must return a full tournament adjacency matrix.  Theorem 2 explicitly
defines this input model: a labelled clique must realize one of a fixed set of
tournaments.  Nothing continuous or algebraic from the paper is discretized
away; the nonempty legacy `reduction` citation records the paper's own finite
standard-representation route (and avoids misclassifying a paper that also has
the `math.RA` arXiv category).

## What the family asks and why it is trustworthy

For every ordered triple `(a,b,c)`, the parity of the three forward-coordinate
arcs `a→b`, `a→c`, and `b→c` must be even.  Additional ordered 4-cliques fix the
parity around a displayed four-cycle.  An answer is an `n × n` 0/1 tournament
matrix.  `verify` checks its shape, diagonal, antisymmetry, every triangle, and
every four-cycle using exact integer XOR; it never reads `inst["answer"]` and
accepts any valid orientation.

Generation is inverse.  It samples a uniformly random tournament first.  For
each three-set it then chooses uniformly one of the three coordinate orders
whose parity makes the sampled tournament satisfy the fixed triangle relation.
Four-cycle parity constraints are evaluated from that same known tournament.
Thus the certificate is known before the instance exists, not recovered by
solving it.  The valid orientations are exactly one vertex-switching class, of
size `2^(n-1)`.

## Why this is Track B, not Track A

Section 6.2 defines the paper's minority operation as edgewise odd parity.
The fixed relations here are affine and are preserved by minority, so Lemma 23
and Corollary 24(3) put the problem in **P**.  That is disclosed, not hidden:
the reference algorithm is Gaussian elimination over GF(2), with `q=n(n-1)/2`
edge variables and `m` equations, costing `O(mq²)` scalar-bit operations.

At the shipping preset and seed 314159, the reference run used 230,225 counted
scalar-bit operations and about 0.001–0.007 seconds on this machine.  Across the
eight attack seeds it used 1,830,783 operations and solved 8/8, as expected.  A
no-tool solver can compress that work by noticing the switching invariant:
orient the star at vertex 0 uniformly, then read every other edge from the
unique triangle containing it and vertex 0.  The measured compact route is 110
parity/placement operations, over 2,000 times fewer than the seed-314159
mechanical count.  The benchmark tests discovery and exact execution of that
invariant; it makes no complexity-theoretic hardness claim.  The NP-complete
template in Section 6.4 is deliberately not used because the paper gives no
constructive hard distribution for a planted generator.

## Worked demo

With `DIFFICULTY["demo"]` and seed 7, the rendered instance is:

```text
GENERALIZED TOURNAMENT-ORIENTATION PROBLEM

The vertices are the integers 0 through 3. The undirected graph
is complete: every pair of distinct vertices must receive exactly one
direction. Represent the orientation by an n-by-n binary matrix A, where
A[i][j]=1 means i -> j. Require A[i][i]=0 and
A[i][j]+A[j][i]=1 for every i != j.

All XORs below are exact addition modulo 2.

TRIANGLE RELATION T:
For every listed ordered triple [a,b,c], require
    A[a][b] XOR A[a][c] XOR A[b][c] = 0.
The coordinate order is part of the constraint; do not sort a triple.
Triangle constraints:
  [3, 1, 2]
  [0, 3, 2]
  [1, 0, 2]
  [3, 0, 1]

FOUR-CYCLE RELATIONS Q0 AND Q1:
For every entry [a,b,c,d] : p, require
    A[a][b] XOR A[b][c] XOR A[c][d] XOR A[d][a] = p.
Here p is the displayed bit 0 or 1. The cyclic order is part of the
constraint; rotations or reversal describe the same four-cycle parity.
Four-cycle constraints:
  [3, 0, 2, 1] : 1
  [1, 2, 3, 0] : 1

Return exactly one 4-by-4 JSON array of integer bits satisfying all
requirements. Rows and columns use vertex order 0,1,...,n-1.
Give your final answer inside <answer></answer> tags, as the JSON matrix.
Example: <answer>[[0,1],[0,0]]</answer>
Output nothing else inside the tags.
```

One answer is:

```json
[[0,1,0,1],[0,0,0,0],[1,1,0,0],[0,1,1,0]]
```

`verify(inst, answer)` returns `(True, "ok")`.  Reversing the edge `{0,1}`
returns `(False, "triangle constraint 2 is violated")`.  A person can solve
this four-vertex demo on paper by fixing the three edges at vertex 0 and using
the remaining triangle relations.

## Difficulty presets

| preset | n | edge variables | triangle + decoy constraints | answer atoms | ships? |
|---|---:|---:|---:|---:|---|
| demo | 4 | 6 | 4 + 2 | 16 | no; hand example |
| easy | 9 | 36 | 84 + 36 | 81 | no; oracle solved 3/3 |
| medium | 12 | 66 | 220 + 160 | 144 | **yes** |
| hard | 15 | 105 | 455 + 600 | 225 | available, not needed |

`escalate` first moves to `n=16`, the largest 256-atom matrix, and then raises
the number of redundant four-cycle constraints at fixed answer length.  It
returns `cap_bound` only when those cycles are exhausted and a larger matrix
would exceed the answer cap.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted checks; all answers JSON-native |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged/fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 valid uniform tournament guesses |
| G5 | pass | sampled density 0/200,000; exact density is `1/2^55`; reference 230,225 operations |
| G6 | pass | each of 4 attacks succeeded 0/8; Gaussian reference solved 8/8 |
| G7 | pass | doubled `n=24` instance built and verified (276 edge variables) |
| G8 | pass | 20/20 for each relabelling/reordering/symmetry/composition and switched witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 313 chars, 79 estimated tokens, 144 atoms, 110 intended operations |

The four failing attacks were a marginal-RHS edge outlier test, one-pass greedy
propagation, short random-restart local repair (6,336 total iterations), and the
by-hand ansatz “orient every edge from the lower label to the higher.”  Canonical keys use the exact
characteristic polynomial of the skew-Seidel matrix plus its vertex-deleted
deck, which is invariant under both switching and vertex relabelling.

## Bare oracle loop

| preset | model | seed | solved? | verifier outcome |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 2054019872 | yes | `ok` |
| easy | Gemini 3.8 Flash | 1423317429 | yes | `ok` |
| easy | GPT-5.6 Terra | 2079651261 | yes | `ok` |
| medium | Gemini 3.8 Flash | 430119148 | no | antisymmetry failure |
| medium | GPT-5.6 Terra | 1626014175 | no | triangle 14 violated |
| medium | Gemini 3.8 Flash | 296095031 | no | returned 3 rows instead of 12 |

The script-owned verdict is `hardened` at medium after one escalation.  Every
medium response parsed, so these are verifier failures rather than output-
contract false negatives.

## G9 diagnostic arms

| arm | solved / attempts |
|---|---:|
| bare | 0 / 3 |
| structural hint | 1 / 3 |
| placebo hint | 3 / 3 |

The structural-minus-placebo difference is `-0.667`.  With only three fresh
seeds per arm, the placebo doing better than the genuine hint means this run
does **not** support a causal claim that the hint helped; seed/model variance or
generic prompt effects dominate.  The hinted arm's historical label is
`too_easy` because one solver succeeded, but this is diagnostic and does not
gate shipping.  The bare 0/3 run is the actual hardening evidence.  Answer and
route sizes remain the gated numbers: 313 characters, 144 atoms, and 110 exact
operations.

## Use

```python
from gen_2405_20263 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["medium"])
question = render(inst)
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit 20 shipping instances with:

```bash
bash scripts/emit.sh 2405.20263 20 medium
```

## Caveats

- This family is easy with tools: the supplied reference eliminator solves it
  in milliseconds.  It must never be cited as Track A evidence.
- `P(guess)` uses the strongest free syntactic prior implemented here—uniform
  over matrices already satisfying every tournament shape rule.  It measures
  blind guessing, not a solver that has recognized the affine switching class.
- The four-cycle constraints are redundant.  They increase crowding and the
  mechanical row count, but an informed solver can ignore them.
- No external SAT/SMT/XOR-SAT package was run.  Exact Gaussian elimination is
  the stronger domain-standard reference for this affine family; broader
  heuristic portfolios and more than three oracle calls per arm remain untested.
- The Seidel characteristic/deletion deck is a strong cheap isomorphism
  invariant, not a complete canonical labelling theorem.  Nonisomorphic
  switching classes can theoretically collide even though 20/20 generated
  seeds were distinct and all required relabellings were invariant.
- The G9 arm comparison is visibly noisy (placebo 3/3 versus structural 1/3),
  so it says nothing reliable about the claimed intuition beyond demonstrating
  why the placebo control is necessary.
