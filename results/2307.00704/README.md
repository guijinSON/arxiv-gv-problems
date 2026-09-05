# Corridor-tree exchange separators from arXiv:2307.00704

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | ordered integer pair in a JSON object |
| Intended intuition | change of variables: mirror symmetry plus affine-map composition |
| Domain essentiality | licensed reduction |

This is not native geometry coverage. It uses the paper-central reduction in
Section 3.4 from a weak polygonal region to its weighted, rotation-ordered
corridor tree; it does not hand the solver polygon coordinates or ask for a full
ReCom sequence.

## Problem and trust model

[Akitaya et al., *Reconfiguration of Polygonal Subdivisions via
Recombination*](https://arxiv.org/abs/2307.00704) represent the topology left by
their gravity moves with a weighted corridor tree `T(P)`. Lemma 8 roots this tree
at a weighted centroid and selects a contiguous block of child subtrees. That
block becomes the region recoloured by the exchange sequence in Section 3.5.

An instance here is a path-shaped `T(P)`. Its labels follow an affine recurrence
modulo `2^n`, and its positive integer weights are symmetric about the path's
middle. The solver returns a centroid label and an adjacent label selecting one
side. `verify` composes the affine recurrence, checks adjacency, recomputes the
component sizes and weights from exact integer formulas, and accepts either
valid side. It never reads the planted answer.

Generation is by composition of identities: the Hull–Dobell conditions make the
affine recurrence a full cycle, reflection symmetry makes the middle vertex the
unique weighted centroid, and binary affine composition gives its label. No
generated instance is solved to obtain its certificate.

## Why Track B

This paper does not support Track A. Section 3.4 explicitly says a greedy
weighted-tree centroid algorithm is linear-time. Theorem 10 constructively
reconfigures three districts in `O(log n)` ReCom moves; Theorem 11 gives a
constructive recursive bound for general `k`. Theorem 22 is a lower bound on the
*number of moves*, not on finding a sequence.

At the shipping preset the represented path has 12.58–14.68 million vertices. The
paper's sequential greedy route visited 6,669,721 vertices on average over eight
audit seeds and succeeded 8/8; this is about 66.70 million exact arithmetic
operations and measured 2.22 seconds mean wall-clock on the final builder audit.
The compact route uses
weight reflection to identify the middle *index* and binary composition to jump
the affine recurrence there in at most 142 exact operations. The benchmark asks
whether a no-tool solver notices and accurately executes that compression.

## Worked demo

For `make_instance(n=5, seed=0)`, the full rendered instance is:

```text
Corridor-tree exchange separator

This is the weighted corridor-tree subproblem used by Lemma 8 of the paper's
recombination algorithm.  A corridor tree is a tree whose vertices represent
polygonal pieces and whose edges represent zero-area corridors.  A vertex's
positive integer weight is the area of its represented piece.

The instance below defines a path T with N=25 vertices by a
succinct, exact recurrence.  All arithmetic in the recurrence is modulo
M=32.

  v_0 = 26
  v_(i+1) = (29 * v_i + 25) mod 32
  indices are 0-based, and 0 <= i < N-1

The vertex labels are v_0,...,v_(N-1); the undirected edges are exactly
{v_i,v_(i+1)} for 0 <= i < N-1.  These labels are distinct.  The first
recurrence value after the path is 19 (so it is not a
tree vertex), and v_(N-1)=2.

For a vertex at path index i, put d=min(i,N-1-i).  Its weight is

  w(i) = 43469774
       + 278009743*d
       + 548977049*d^2.

The total weight is W=675737615986.

A weighted centroid c is a vertex such that, after deleting c, every connected
component has weight at most W/2.  Root T at c.  If s is a neighbor of c, define
T*(c,s) to contain c and every vertex in the component containing s after c is
deleted.  On a path this is a contiguous subtree in the rotation order of the
centroid, as required by Lemma 8.

Find any ordered pair (c,s) such that:
  1. c is a weighted centroid;
  2. s is a neighbor of c;
  3. T*(c,s) contains at least N/3 vertices; and
  4. weight(T*(c,s)) <= W/2 + w(c).

The roles are ordered: the first label is the centroid and the second selects a
side.  Labels are integers, repetitions are not allowed, and both inequalities
are inclusive.  Either side is acceptable when both sides satisfy the rules.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the integer fields "centroid" and "neighbor".
Example: <answer>{"centroid":17,"neighbor":4}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"centroid":30,"neighbor":31}</answer>` and verifies as
`(True, "ok")`. Swapping the roles gives `{"centroid":31,"neighbor":30}` and
returns `(False, "the first label is not the unique weighted centroid")`. A
person can solve this demo by writing the 25-term recurrence (or jumping 12
steps); the larger presets make that literal walk infeasible by hand.

## Difficulty

| preset | n | represented vertices N | answer atoms | status |
|---|---:|---:|---:|---|
| demo | 5 | 25–27 | 2 | hand-scale illustration |
| easy | 24 | 12,582,913–14,680,033 | 2 | shipping candidate |
| medium | 25 | 25,165,825–29,360,065 | 2 | escalation |
| hard | 26 | 50,331,649–58,720,129 | 2 | escalation |

`SHIPPING_DIFFICULTY` is `easy`. Increasing `n` essentially doubles the
haystack while leaving the witness fixed at two labels.

## Gate results

| gate | result |
|---|---|
| G1 | 12/12 planted witnesses verified; all answers JSON-round-tripped |
| G2 | 6/6 corruptions rejected with six distinct reasons |
| G3 | realistic prose plus fenced JSON parsed and verified |
| G4 | 0/200,000 guesses satisfying every non-centroid rule; exact seed-42 density `4.503e-7` |
| G5 | demo has exactly 2/12 answers in the structure-aware language; shipping reference cost measured |
| G6 | four attacks failed on 8/8 seeds; reference algorithm solved 8/8 |
| G7 | `n+1` approximately doubled `N`; witness stayed at 2 atoms |
| G8 | 60/60 affine/reversal invariance checks and 60/60 carried witnesses passed; 20/20 unrelated keys distinct |
| G9(c) | 40 characters, 13 estimated tokens, 2 atoms, at most 142 intended operations |

## Oracle loop and G9 arms

The required script-owned run was attempted, but the configured OpenRouter key
returned HTTP 403 `Key limit exceeded` for every retry before any usable oracle
attempt. The current transcript preserves those errors and makes no hardness
claim. These rows must be replaced by successful script-owned runs before
submission.

| preset | seed | solved | why |
|---|---:|---|---|
| easy | 1835745141 | error | HTTP 403 key limit |
| easy | 890403943 | error | HTTP 403 key limit |
| easy | 2106732277 | error | HTTP 403 key limit |
| easy | 1879096705 | error | HTTP 403 key limit |

| arm | solved / usable attempts | status |
|---|---:|---|
| bare | 0 / 0 | blocked by OpenRouter account limit |
| structural hint | 0 / 0 | four retries, all HTTP 403 |
| placebo hint | 0 / 0 | four retries, all HTTP 403 |

`hinted − placebo` is therefore unavailable. G9(c), the gated portion, passes;
the three-arm diagnostic remains outstanding because of the external account
limit.

## Use

```python
from gen_2307_00704 import make_instance, render, verify

inst = make_instance(n=5, seed=0)
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, after a successful hardening run:

```bash
bash scripts/emit.sh 2307.00704 20 easy
```

## Caveats

With a calculator or a few lines of code, binary affine exponentiation makes
every instance easy; that is the declared Track B reference gap, not hidden
Track A hardness. The 0/200,000 guess result samples uniformly from oriented
path edges that already satisfy adjacency and both stated subtree bounds, so
only the centroid condition remains; it says nothing about a solver already
biased toward the path's middle. The affine labels erase numeric-position
outliers, but they are not cryptographic.

The family tests the corridor-tree separator used by the proof, not continuous
polygon construction, weak-embedding perturbation, area integration, or replay
of ReCom moves. Path-shaped weighted corridor trees can be realized by a chain
of polygonal pieces and corridors, but the module does not output that
realization. I did not try spectral embedding (unnecessary for an exact centroid
problem), symbolic 2-adic simplification, or external CAS attacks. The strongest
unresolved concern is whether a model can carry out the 23-bit affine jump
reliably in prose; that is exactly what the unavailable oracle run must measure.
