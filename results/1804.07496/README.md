# Planar tagged Steiner orientation generator (arXiv:1804.07496)

> Status: **rejected on Track B hardness**. In the later valid bare run, every
> `easy` and `medium` attempt was solved, two of three `hard` attempts were
> solved, and an escalated duplicate-constraint instance was also solved. The
> run then exhausted OpenRouter quota before a formal harness verdict was
> written; the valid solved calls remain decisive evidence against this family.

## Profile

| Field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite discrete |
| Computational core | linear algebra (with graph reachability verification) |
| Certificate form | exact symbolic |
| Intuition | symmetry: complement-basis rows collapse to one global parity |
| Domain essentiality | discretised analogue |
| Reduction | benchmark convenience wrapper around Section 2's flip identities |

This is **not native coverage** of Planar Steiner Orientation. The paper licenses
the flip and stacked-flip identities, but it does not introduce GF(2)-tagged
edges or restrict orientations to those induced by a symbolic key. Those are a
benchmark-convenience layer that discards the paper's unrestricted orientation
search. The solver receives the complete planar mixed graph and a redundant
GF(2) synopsis. The checker ignores that synopsis: it expands the submitted
symbolic key into directions and checks directed reachability in the graph.

## Problem and trust model

[Beck, Blum, Kryven, Löffler, and Zink, *Planar Steiner Orientation is
NP-complete*](https://arxiv.org/abs/1804.07496) asks whether the undirected edges
of a mixed graph can be oriented so every ordered terminal pair has a directed
path. Section 2's flip gadget forces two edge directions to be opposite; two
stacked flips force the outer directions to agree. This generator samples a
96-bit key first, assigns independent tags and endpoint biases, and constructs
each gadget around that key. This is inverse generation: no generated instance
is solved to obtain its planted certificate.

The answer is `[[0,c0],...,[95,c95]]`. Edge tags turn that key into a concrete
orientation by an exact GF(2) inner product. Verification then runs ordinary
graph reachability for every terminal pair and never reads `inst["answer"]`.

## Why Track B, not Track A

The paper's Theorem 1 is worst-case NP-completeness. It says nothing about this
generated distribution. Section 1 also records polynomial algorithms when the
input has no pre-directed arcs and when there are only two terminal pairs, plus
an `n^{O(k)}` XP algorithm in the number of terminal pairs. Those facts rule out
using the paper title as a distributional-hardness claim.

For this special gadget family, generic GF(2) Gauss-Jordan elimination is an
efficient `O(m n^2)` algorithm (`O(n^3)` here). At shipping seed 314159 it used
83,678 counted bit operations and about 0.00096 seconds. Across the eight G6
seeds the largest count was 119,459; all eight were solved, as Track B expects.
The compact route notices that every distinct row is `J+I`: each row contains
all coordinates except one. One global parity followed by coordinatewise XORs
recovers the key in 288 counted exact operations. The benchmark tests whether a
no-tool solver finds that collapse before attempting mechanical elimination.

## Worked demo (seed 9)

This is the complete `demo` rendering. It is genuinely hand-solvable: align the
four complement rows and solve the four XOR equations.

```text
Planar tagged Steiner orientation

A mixed graph has directed arcs and undirected edges.  Choose a symbolic
orientation key c=(c_0,...,c_3) over GF(2), meaning every c_i is 0 or 1.
For an undirected edge printed as

    e: u-v tag=h bias=b

read hexadecimal h as an 4-bit integer whose least-significant bit is bit 0.
Compute q = b XOR (the XOR of c_i over all set bits i of h).  If q=0, orient
the edge u->v; if q=1, orient it v->u.  Endpoint order u-v is therefore part of
the input convention.  Repeated vertices and repeated tag values are allowed.

Your key is valid when, after orienting every undirected edge by this rule, each
ordered terminal pair s>t has a directed path from s to t.  A path may use both
the fixed directed arcs and the newly oriented edges.

The graph below is a disjoint union of planar flip or stacked-flip components.
For auditability, a redundant GF(2) synopsis is also supplied.  Each line
mask=m, rhs=b is the equation XOR_{i: bit i of m is 1} c_i = b enforced by
one component.  The graph, not this synopsis, is used to grade your answer.

Dimensions: n=4; vertices are exactly 0..43.

Directed arcs (u>v):
5>27 21>40 9>16 35>29 36>27 29>25 7>6 33>36 30>1 0>17 4>6 31>42 17>43 3>18 11>9 36>16 24>32 11>36 6>8 26>30 37>24 7>13 34>25 20>43 0>20 24>15 2>39 6>10 28>1 26>28 12>38 33>5 41>21 3>24 14>32 35>34 42>19 2>12 22>40 13>10 39>38 23>8 18>15 4>23 31>22 37>14 41>22 22>19

Undirected edges:
  e0: 23-14 tag=2 bias=1
  e1: 17-30 tag=7 bias=0
  e2: 6-24 tag=2 bias=0
  e3: 42-9 tag=2 bias=0
  e4: 34-39 tag=5 bias=1
  e5: 13-18 tag=9 bias=1
  e6: 22-36 tag=8 bias=0
  e7: 21-5 tag=5 bias=1
  e8: 29-12 tag=8 bias=0
  e9: 20-28 tag=9 bias=1

Ordered terminal pairs (s>t):
41>27 2>25 0>1 11>19 4>32 3>10 7>15 26>43 35>38 31>16 37>8 33>40

Redundant GF(2) constraint synopsis:
  r0: mask=b rhs=0
  r1: mask=d rhs=0
  r2: mask=e rhs=0
  r3: mask=7 rhs=1

Give your final answer inside <answer></answer> tags as JSON: a list of exactly
4 pairs [[0,c_0],[1,c_1],...,[3,c_3]], in that increasing index
order, with every c_i written as the integer 0 or 1.  No index may be omitted or
repeated.  Example format: <answer>[[0,0],[1,1],[2,0],[3,1]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[0,1],[1,1],[2,1],[3,0]]</answer>`.
`verify` returns `(True, "ok")`. Dropping the final pair returns
`(False, "wrong coefficient count: expected 4")`.

## Difficulty presets

| Preset | n | Copies/row | Answer atoms | Typical rendered chars | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 1 | 8 | 2,216 | hand example; never ships |
| easy | 48 | 1 | 96 | 13,633 | rejected: solved 3/3 |
| medium | 72 | 1 | 144 | 21,181 | rejected: solved 3/3 |
| hard | 96 | 1 | 192 | 30,620 | rejected: solved 2/3 |

The first escalation, `n=96, copies=2`, was solved by one of two completed
calls. Four subsequent retry calls hit the account's total quota. Duplicating
rows did not change the compact problem, so further copies would increase only
prompt length. Raising `n` can reach only 100 before the intended route meets
the 300-operation cap.

## Deterministic gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12 planted checks, 12 compact-route cross-checks |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose/fences; garbage rejected |
| G4 | pass | 0 / 200,000 uniform canonical-key guesses |
| G5 | pass | shipping sampled density 0 / 200,000; demo exactly 1 / 16; baseline 83,678 bit ops |
| G6 | pass | four attacks at 0 / 8 each; reference elimination 8 / 8 |
| G7 | pass | doubled from n=96, 1,002 vertices to n=192, 2,076 vertices |
| G8 | pass | 100 invariance and 100 real-transform checks; 20 / 20 unrelated keys distinct |
| G9(c) | pass | 663 chars, 166 estimated tokens, 192 atoms, 288 operations |

G6 tried per-coordinate majority, one-pass lowest-bit repair, 256 random
restarts per seed, and low-period/all-constant/direct-RHS ansatzes. The domain
reference algorithm is reported separately because this is Track B.

## Bare oracle loop

The official harness wrote the transcript. “Failed” below means the model
returned a parsed but invalid key; “solved” means exact verification passed.

| Preset | Seed | Model | Result | Why |
|---|---:|---|---|---|
| easy | 1955334147 | OpenAI GPT-5.6 Terra | solved | verified key |
| easy | 2142923921 | Google Gemini 3.8 Flash | solved | verified key |
| easy | 1274458308 | Google Gemini 3.8 Flash | solved | verified key |
| medium | 1677342289 | Google Gemini 3.8 Flash | solved | verified key |
| medium | 1125368393 | OpenAI GPT-5.6 Terra | solved | verified key |
| medium | 1723487548 | OpenAI GPT-5.6 Terra | solved | verified key |
| hard | 433445935 | OpenAI GPT-5.6 Terra | solved | verified key |
| hard | 215108208 | Google Gemini 3.8 Flash | solved | verified key |
| hard | 921693252 | OpenAI GPT-5.6 Terra | failed | terminal pair unreachable |
| escalated | 660228603 | OpenAI GPT-5.6 Terra | failed | terminal pair unreachable |
| escalated | 2069074810 | Google Gemini 3.8 Flash | solved | verified key |

Four later escalated calls were HTTP 403 quota errors and do not count as
model failures. Consequently no formal final harness verdict was written, but
every tested rung had a successful valid call and therefore was defeated.

## G9 arms

| Arm | Solved / valid attempts | Error calls | Result |
|---|---:|---:|---|
| bare | 2 / 3 | 0 | shipping rung defeated |
| structural hint | 0 / 0 | 4 | unmeasured: total key limit |
| placebo hint | 0 / 0 | 4 | unmeasured: total key limit |

`hinted - placebo` is undefined, so there is no conclusion yet about whether
the symmetry hint provides real help. The bare number comes from the later
official run at the candidate shipping rung; the two diagnostic scratch runs
predate it and contain quota errors only. The hint only names the invariant:
“The GF(2) row masks are the complements of the coordinate basis.” It does not
give the recovery steps. Size/effort remains within caps as shown above.

## Use

The rejected prototype remains importable for audit from this directory:

```python
import rejected_gen_1804_07496 as g

inst = g.make_instance(**g.DIFFICULTY["demo"], seed=9)
statement = g.render(inst)
answer = g.parse_answer("<answer>[[0,1],[1,1],[2,1],[3,0]]</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Do not run `emit.sh` on this prototype. Its filename deliberately starts with
`rejected_gen_` so submission tooling cannot mistake it for a shipping module.

## Caveats

- The certificate language is a succinct tagged linear orientation rule, not an
  arbitrary explicit direction for every edge. The tags and redundant synopsis
  are a benchmark wrapper; the profile therefore says `discretised_analogue`
  and `convenience`, not native or paper-licensed coverage.
- This distribution is intentionally in P. The paper's NP-completeness theorem
  cannot be used as evidence that these inverse-generated instances are hard.
- The 0 / 200,000 guess estimate is only for a uniform prior over all canonical
  96-bit keys. A solver that detects complement-basis symmetry does vastly
  better; that gap is the point of Track B.
- Full SAT/SMT search over the expanded reachability instance was not run.
  Generic exact GF(2) elimination is the more direct standard algorithm for the
  supplied gadget synopsis, but a future audit should still try a graph-native
  SAT encoding.
- `canonical_key` is complete for this generator's component templates and is
  invariant under vertex/input reordering, endpoint-order/bias transport, and
  outer-role reflection. It is not a general mixed-graph isomorphism
  canonicalizer.
- More copies increase crowding and reference cost without adding answer
  entropy. Escalation beyond the tested range could become a prompt-length test,
  so it is capped before that failure mode dominates.
- The old G9 hinted/placebo files contain quota errors only, so the diagnostic
  remains unmeasured. This is not the deciding rejection: the valid bare calls
  already refute Track B hardness.
