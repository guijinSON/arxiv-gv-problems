# Verified generator for arXiv:1811.04560

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple |
| Intended intuition | invariant: affine holonomy around one cycle |
| Domain essentiality | licensed reduction |
| Reduction | Section 3, Theorem 2 and Claims 3.3–3.4 |

## What the problem is

[Majumdar, Neogi, Raman, and Vaishali, *Tractability of König Edge Deletion Problems*](https://arxiv.org/abs/1811.04560) asks for at most (k) edges whose removal makes maximum-matching size equal minimum-vertex-cover size. The generator uses the paper's Section 3 construction verbatim: a source Independent Set instance receives one private vertex per source vertex and (2k) independent universal vertices.

The source graph is specified succinctly by (n) blocks of (q) vertices and affine compatibility constraints. A submitted vector selects one vertex per block and therefore names the (n) private edges to delete. `verify` checks every affine constraint exactly modulo the prime (q). Those checks establish an independent set; Claim 3.3's explicit cover and matching then have the same cardinality, certifying that the deleted graph is König. The planted vector is sampled before the constraints are built, so generation never solves its output.

## Why this is Track B

Theorem 2 proves unrestricted König Edge Deletion W[1]-hard and Theorem 3 retains hardness when the graph has a perfect matching. That worst-case statement is not the hardness claim here. This structured distribution has algorithms: after fixing a spanning tree, finite-domain root enumeration costs (O(q\ell+n)), where \(\ell\) is the sole cycle length. At the shipping preset the measured eight-instance mean was **2.735864 s**, **2,662,175 root trials**, and **47,919,202 exact modular operations**; it solved 8/8 as expected.

The compact route composes the cycle maps to (x\mapsto Ax+B), solves the single fixed-point equation (x=Ax+B\pmod q), and propagates once through the tree. It is bounded at **152 exact operations**. The benchmark tests whether a no-tool solver can recognize and execute that compression accurately, not whether the instance lacks an algorithm.

Section 4, Theorem 5 is the easy regime deliberately avoided: when a compatible maximum matching is supplied and deletions must avoid it, the problem reduces to Almost-2-SAT and is FPT in (O^*(2.31^k)). No matching is supplied here. A perfect matching disjoint from the unique deletion set can be written down only after that deletion set is known.

## Worked demo

For `make_instance(n=4, q=7, cycle_length=3, seed=0)`, the complete rendered instance is:

```text
KOENIG EDGE DELETION IN A SUCCINCTLY SPECIFIED GRAPH

All graphs below are finite, simple, and undirected.  A matching is a
set of pairwise endpoint-disjoint edges.  A vertex cover is a set S
meeting every edge.  A graph is Koenig when its maximum matching and
minimum vertex cover have the same size.

Let q=7 (a prime) and let there be n=4 value blocks, numbered
0 through 3.  Arithmetic in the constraint list is modulo q.
First define a source graph H with vertices X(i,a), where
0 <= i < 4 and 0 <= a < 7.  Its edges are exactly these:
  (1) all distinct X(i,a), X(i,b) in the same block i are adjacent;
  (2) a line 'i j s t' means x_j = s*x_i+t (mod q), and for that
      line X(i,a) is adjacent to X(j,b) exactly when
      b != s*a+t (mod q).
There are no other edges in H.  The constraint-block graph is connected
and has exactly one cycle.

Constraint lines (i j s t):
  2 0 5 4
  3 2 3 4
  1 3 4 5
  2 1 4 0

Now define the actual graph K using the paper's construction.  For every
source vertex X(i,a), add a new vertex P(i,a) and the pendant edge
{X(i,a),P(i,a)}.  Add 2n new vertices C(0),...,C(2n-1), with no
edges among them.  Every C(r) is adjacent to every X(i,a) and every
P(i,a).  Keep all edges of H.  These are all vertices and edges of K.
Thus K has 64 vertices, though the rules above
specify it exactly without expanding its repetitive edge set.

Find at most n=4 edges whose deletion makes K a Koenig graph.
Return the deletion set in its required compressed form: a JSON list
[a_0,...,a_3] of exactly 4 integers, where entry a_i denotes
deleting the pendant edge {X(i,a_i),P(i,a_i)}.  Each entry must be in
the inclusive range 0..6.  Equal values in different blocks are
allowed; order is fixed by the zero-based block number.

Give your final answer inside <answer></answer> tags, as one JSON list.
Example shape: <answer>[0, 0, 0, 0]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[6, 3, 6, 3]</answer>`. A person can solve this demo on paper by composing the three cycle congruences modulo 7 and propagating the remaining tree edge.

```python
>>> verify(inst, [6, 3, 6, 3])
(True, 'ok')
>>> verify(inst, [0, 3, 6, 3])
(False, 'constraint 2->0 fails: got 0, expected 6')
```

## Difficulty presets

| Preset | Blocks (n) | Prime (q) | Cycle | Source vertices | König vertices | Answer atoms | Oracle result |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 4 | 7 | 3 | 28 | 64 | 4 | hand-scale; skipped |
| easy | 12 | 10,007 | 5 | 120,084 | 240,192 | 12 | solved 3/3 |
| medium | 18 | 200,003 | 7 | 3,600,054 | 7,200,144 | 18 | solved 1/3 |
| **hard (ships)** | **24** | **5,000,011** | **9** | **120,000,264** | **240,000,576** | **24** | **solved 0/3** |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 12/12 across all presets |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | pass | tagged fenced JSON and JSON-native answer |
| G4 guessing | pass | 0/200,000; exact density (1/5,000,011\approx2.0\times10^{-7}) |
| G5 density/baseline | pass | demo has exactly 1 answer; baseline 47,919,202 operations |
| G6 adversaries | pass | five attacks, each 0/8; reference algorithm 8/8 |
| G7 scaling | pass | 48-block/18-cycle doubled instance verifies |
| G8 canonical key | pass | 100/100 invariance, 20/20 carried witnesses, 20 distinct unrelated keys |
| G9 caps | pass | 214 chars, 54 estimated tokens, 24 atoms, 152 operations |

The five failing attacks were equal-degree/minimum-label, root-zero tree propagation, one-pass cycle repair, diagonal ansatz, and 256 uniform tree-consistent restarts.

## Bare oracle loop

| Preset | Seed | Model | Solved | Exact outcome |
|---|---:|---|---|---|
| easy | 1583111490 | Gemini 3.8 Flash | yes | ok |
| easy | 947536894 | GPT-5.6 Terra | yes | ok |
| easy | 234512307 | GPT-5.6 Terra | yes | ok |
| medium | 611366817 | GPT-5.6 Terra | yes | ok |
| medium | 1427823153 | Gemini 3.8 Flash | no | constraint 11→12 failed by 15 |
| medium | 597627168 | Gemini 3.8 Flash | no | constraint 13→2 failed |
| hard | 88264326 | GPT-5.6 Terra | no | constraint 6→3 failed by 11 |
| hard | 65171038 | Gemini 3.8 Flash | no | zero vector failed constraint 22→19 |
| hard | 2086254882 | GPT-5.6 Terra | no | partial vector failed constraint 23→11 |

The script-owned verdict is `hardened` at `hard` after two escalations.

## G9 diagnostic arms

| Arm | Solved/attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 0/3 | the affine-cycle invariant did not produce a valid answer |
| placebo hint | 1/3 | one control run solved, showing run-to-run prompt variance |

Hinted minus placebo is **−1/3**. The hint bought no measured improvement, so these runs do not support a positive causal effect for the declared invariant. This is diagnostic only. The answer/cap measurements are 214 characters, 54 estimated tokens, 24 atoms, and 152 intended exact operations.

## Use

```python
from gen_1811_04560 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
prompt = render(inst)
candidate = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 1811.04560
```

## Caveats

- This is a succinct, specially structured Track B family, not evidence that arbitrary instances from Theorem 2 are hard on average. The expanded shipping graph has over 240 million vertices; expanding it is intentionally unnecessary.
- The exact (1/q) guess probability is for the strong prior implemented by `random_candidate`: candidates already satisfy a canonical spanning tree. It does not model semantic priors that recognize and solve the cycle fixed point.
- A direct symbolic affine solver is efficient, (O(n+\log q)), once the invariant is recognized. That is the intended shortcut and the reason this is not Track A.
- The panel did not run a general SAT/SMT/ILP package on the fully expanded graph. It did run the distribution's complete root-enumeration reference algorithm and five no-tool attacks.
- `canonical_key` is exact for constraint order/orientation, block relabelling, affine value gauges, and their compositions. It does not attempt full graph isomorphism under arbitrary non-affine value permutations; it is the strongest cheap invariant used for this succinct representation.
- `gvlib` is imported when available for repository consistency, but this family needs only Python integer modular arithmetic and remains standard-library-only without it.
