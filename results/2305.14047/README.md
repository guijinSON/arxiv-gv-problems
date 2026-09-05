# Maximal affine-line quasi-cliques from arXiv:2305.14047

> **Status:** the module and every local gate pass. The required external oracle
> verdict is unavailable: OpenRouter returned HTTP 403 “total limit exceeded”
> on every bare, structural-hint, and placebo redraw. These script-written error
> records are retained and are not counted as failed solver attempts. This
> directory is therefore complete locally but **not submission-ready**.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph (with a linear-algebraic compact route) |
| certificate form | 2-row matrix certificate |
| intuition | invariant: constraint rows share a polynomial root |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The source is Yu and Long, [*Fast Maximal Quasi-clique Enumeration: A
Pruning and Branching Co-Design Approach*](https://arxiv.org/abs/2305.14047).
Section 2.1 defines induced `gamma`-quasi-cliques and explicitly notes that a
1-quasi-clique is a clique. The solver receives a succinct, exact Cayley graph
on all vectors of `F_q^d` and must return an affine line whose `q` points form a
maximal 1-quasi-clique. The answer is the canonical matrix `[base, direction]`.

Generation is inverse: a field root `a` is sampled first, the direction
`(1,a,...,a^(d-1))` is retained, and every displayed constraint row is built as
the coefficient list of a polynomial divisible by `X-a`. Thus the direction is
in their common kernel without solving a generated system. The graph connects
every nonzero kernel difference. For every outside vertex, its syndrome is
constant along the line while `z0` runs through all of `F_q`; one point hits the
explicit forbidden value `z0=c·s`. Therefore no outside vertex extends the
clique. `verify` executes these modular checks and never reads `inst["answer"]`.

## Why Track B

This is not an average-case hardness claim. Section 3 gives Quick+ worst-case
time `O*(2^N)` and Theorem 1 gives FastQC time `O(N d alpha_k^N)`. The paper’s
Section 6 also says larger `gamma` and `theta` reduce running time, while dense
graphs weaken degree pruning; using `gamma=1` is deliberately an easy special
case of the general QC definition.

The difficulty here is compression. At shipping size the graph has `5^96`
vertices and about `3.16e66` projective directions. The strongest obvious
mechanical solver for the displayed encoding is modular Gaussian elimination:
over 8 seeds it used 495,207 median exact field operations and took 0.0159 s.
Reading each row as polynomial coefficients exposes the short route. Fold the
first row's exponents modulo `|F_5^*|=4`, test the four nonzero field values,
and write the geometric direction. That succeeded 8/8 in 209 median operations
(209 measured maximum, 0.000231 s median); the stated worst case is 215. A
machine does either; a no-tool solver must notice the second representation.

## Worked demo

`make_instance(n=2, q=3, seed=0)` renders in full as:

```text
Find a maximal affine-line 1-quasi-clique in a succinct graph.

All arithmetic below is in the prime field F_3: reduce every integer modulo
3. The graph is finite, simple, undirected, and unweighted. Its vertices are
all 2-coordinate vectors over F_3, so it has 3^2 =
9 vertices. The subgraph induced by a vertex set contains
exactly the edges whose endpoints both belong to that set.

For two distinct vertices x and y, put delta=x-y coordinatewise modulo 3.
Compute z0 = r dot delta and s_i = m_i dot delta for i=0,...,0,
where "dot" is the ordinary dot product reduced modulo 3, and

r  = 0 1
m0 = 2 1

The 1 displayed rows m_i are promised to be linearly independent over
F_3.

Let s=(s_0,...,s_0). If every s_i is zero, x and y are adjacent.
Otherwise let j be the smallest index with s_j nonzero. They are adjacent if
and only if BOTH conditions hold:

  1. min(s_j, 3-s_j) <= h_j, where
     h = 0;
  2. z0 is not equal to c dot s modulo 3, where
     c = 0.

This rule is symmetric under delta -> -delta, so it defines an undirected
graph. A gamma-quasi-clique H is a connected induced subgraph in which every
vertex has at least ceil(gamma*(|H|-1)) neighbors in H. Here gamma=1, so a
1-quasi-clique is exactly a clique. It is maximal when no strictly larger
1-quasi-clique contains it.

An affine line is L(b,v)={b+t*v : t in F_3}, with v nonzero. Return one
affine line whose 3 vertices induce a maximal 1-quasi-clique. Encode it as
the JSON matrix [b,v], with exactly two rows of 2 integers in 0..2.
Use the unique canonical encoding: the first nonzero coordinate v[p] must be
1, and b[p] must be 0. Vector order and coordinate order are fixed as printed;
no repeated/missing coordinates are allowed.

Give your final answer inside <answer></answer> tags as that JSON matrix.
Example of the required shape: <answer>[[0,0],[1,0]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[0,1],[1,1]]</answer>`. It represents
`{(0,1),(1,2),(2,0)}`. `verify(inst, inst["answer"])` returns `(True, "ok")`;
dropping the direction row returns
`(False, "answer must contain exactly two rows: base and direction")`.
This 9-vertex demo is genuinely hand-solvable: there are four directions and
three valid affine lines.

## Difficulty presets

| preset | d (`n`) | q | graph vertices `q^d` | directions | answer atoms | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 3 | 9 | 4 | 4 | hand example; skipped by hardener |
| easy | 32 | 5 | 23,283,064,365,386,962,890,625 | 5,820,766,091,346,740,722,656 | 64 | oracle not reached: API error |
| medium | 64 | 5 | `5^64` | `1.3553e44` | 128 | not reached |
| **hard** | **96** | **5** | **`5^96`** | **`3.1554e66`** | **192** | shipping preset; local gates pass |

`escalate` raises the dimension to 112 and then 128 while keeping the
certificate at two vectors. Dimension 128 reaches both 256 answer atoms and a
279-operation compact route, so no further compliant axis remains.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 plants verify; 12/12 JSON round-trips |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged fenced prose round-trips; garbage returns `None` |
| G4 | 0/200,000 line guesses; exact density `3.1691e-67` |
| G5 | `5^95` exact valid shipping lines; 16,384-restart attack median 4.51 s |
| G6 | five attacks each 0/8; Gaussian elimination uses 495,207 median operations; compact solver uses 209 |
| G7 | doubled dimension 192 builds and verifies; search space grows 442 to 888 bits |
| G8 | 80/80 invariant keys, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 389 characters, 192 atoms, about 98 tokens, 215 intended operations |

## Oracle loop and G9 diagnostics

The bare hardener stopped before scoring `easy`. Its four redraws (seeds
486116356, 2119107815, 255490634, and 1905151158) all received HTTP 403. There
is no `hardened`/`too_easy` verdict and no model failure to report.

| arm | solved / scored attempts | error records | verdict |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | unavailable; API total limit |
| structural hint | 0 / 0 | 4 | unavailable; API total limit |
| placebo hint | 0 / 0 | 4 | unavailable; API total limit |

Hinted-minus-placebo is unavailable, not evidence of a zero effect. The module’s
numeric field is `0.0` only because both denominators are zero. The answer and
route remain within G9(c): 389 serialized characters, 192 atomic elements, and
at most 215 exact operations.

## Use

```python
import gen_2305_14047 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
raw = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(raw)
assert g.verify(inst, answer) == (True, "ok")
```

After a funded key produces a real bare verdict and both G9 arms, emit from the
repository root with `bash scripts/emit.sh 2305.14047`.

## Caveats

The family exercises the paper’s exact graph and quasi-clique definitions but
only its `gamma=1` clique boundary, not the non-hereditary `gamma<1` regime that
motivates FastQC. Its finite-field Cayley representation is a specially
structured input distribution, so it is Track B and says nothing about
distributional NP-hardness. Full FastQC/Quick+, SAT/ILP, and a full Fourier or
spectral attack were not run: materializing `5^96` vertices is outside this
module’s scope. The strongest executed failing attack samples affine lines;
its 0/200,000 result does not apply to a different prior. The canonical key uses
graph order and exact regular degree, a strong invariant but not a complete
isomorphism canonical form; distinct threshold vectors can have the same
weighted count. Most importantly, the external no-tool oracle evidence is
missing until OpenRouter’s account limit is repaired.
