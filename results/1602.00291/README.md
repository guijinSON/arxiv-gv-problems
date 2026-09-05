# Encoded torus edge-metric bases (arXiv:1602.00291)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple: three vertex labels |
| Intended intuition | symmetry |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

The solver receives a succinct, exactly labelled Cartesian torus graph
`C_(4r) square C_(4t)`, a designated anchor vertex, and the complete public
map from torus coordinates to integer vertex labels. It must return three
vertices, including the anchor, whose distance triples distinguish every pair
of graph edges. This is the edge metric basis introduced in Kelenc, Tratnik,
and Yero, [*Uniquely identifying the edges of a graph: the edge metric
dimension*](https://arxiv.org/abs/1602.00291).

The family is generated without solving an instance. Section 2, Theorem 7
proves `edim(C_(4r) square C_(4t)) = 3` and constructs the coordinate basis
`{(0,0), (0,2t), (r,t)}`. The generator first samples an anchor and a bijective
affine relabelling, then translates that theorem basis and carries it through
the relabelling. Verification does not consult the planted answer: it computes
exact cyclic distances and rejects as soon as two of the `2LM` edges have the
same candidate distance triple.

## Why Track B, and why it is hard here

This is deliberately **not** a Track A claim. Theorem 12 proves EDIM
NP-complete for arbitrary connected graphs via 3-SAT, but that worst-case
result says nothing about these tori. The paper also identifies easy regimes:
Section 2 gives direct formulae or constructions for paths, cycles, complete
and complete bipartite graphs, trees (linear time), ordinary grids, wheels,
fans, these tori, and hypercubes; Section 3.1 gives a polynomial set-cover
formulation and logarithmic approximation.

The Track B reference algorithm is an exact, symmetry-reduced edge-signature
scan based on that Section 3.1 representation. It uses `O(N^2)` exact distance
evaluations and `O(N)` memory. At the measured shipping instance (`N=10,000`)
it succeeded after **102,500,000 exact distance evaluations**, taking about
16--24 seconds across repeated self-tests (**23.71 seconds** in the saved
report). A person without tools cannot execute that scan. Once Theorem 7's
symmetry is noticed, the compact route is to decode
the anchor, apply the half-cycle and simultaneous quarter-cycle offsets, and
re-encode three coordinates; the conservative count is **168 exact arithmetic
operations**. Seven public affine encoding layers prevent merely reading the
coordinate answer off the labels.

## Worked demo

The `demo` preset with seed 7 renders in full as follows:

```text
Find an anchored edge metric basis of an encoded Cartesian torus.

Let L=4, M=4, and N=L*M=16. Coordinates are pairs
(x,y) with 0 <= x < L and 0 <= y < M. Addition to x is modulo L and
addition to y is modulo M.

Each coordinate has a public vertex label enc(x,y) in 0,...,N-1. Compute it
by the following exact rules, in the displayed order:
  q := y*L + x
  layer 1: q := (3*q + 3) mod N
  enc(x,y) is the final q.
Every displayed multiplier is coprime to N, so enc is a bijection.

The undirected graph has vertex labels 0,...,N-1. For every coordinate (x,y)
it has the two edges
  {enc(x,y), enc(x+1 mod L,y)}
  {enc(x,y), enc(x,y+1 mod M)}.
These are all its edges; duplicate endpoint order does not create new edges.

For vertices u,v, d(u,v) is the number of edges in a shortest graph path.
For a vertex s and an edge e={u,v}, define d(s,e)=min(d(s,u),d(s,v)).
A set S of vertices is an edge metric generator when all distinct edges e
have distinct ordered triples (d(s,e) for s in S), using S in increasing
numeric-label order. In this graph no two-vertex set is an edge metric
generator, so a three-vertex generator is an edge metric basis.

Return exactly three distinct vertex labels forming an edge metric basis and
including the designated anchor A=9. The three labels must be written in
strictly increasing numeric order; order otherwise has no meaning.

Give your final answer inside <answer></answer> tags as three comma-separated
base-10 integers.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

The answer is `<answer>1, 8, 9</answer>`. In Python,
`verify(inst, [1, 8, 9])` returns `(True, "ok")`, while dropping one label gives
`verify(inst, [1, 8]) == (False, "expected exactly three labels")`. This demo
is genuinely hand-solvable: the modulus is 16, there is one affine layer, and
only 32 edges need checking.

## Difficulty presets

| Preset | Quarter lengths | Encoding layers | Possible vertex count `N` | Ships? |
|---|---:|---:|---:|---|
| demo | `r=t=1` | 1 | 16 | no; illustration |
| easy | `r=24..39`, `t=r..r+3` | 7 | 9,216..26,208 | **yes** |
| medium | `r=36..55`, `t=r..r+4` | 8 | 20,736..51,920 | no |
| hard | `r=54..77`, `t=r..r+5` | 9 | 46,656..101,024 | no |

The bare oracle pool already failed all three attempts at `easy`, so the
harness did not escalate. The three-label answer stays fixed while the
anchored pair haystack grows as `binomial(N-1, 2)`.

## Gate results

| Gate | Result |
|---|---|
| G1 planted verifies | pass: 12/12 preset-seed cases; answers JSON-native |
| G2 corruption | pass: five corruptions rejected with five distinct reasons |
| G3 parse round-trip | pass, including surrounding prose and fences |
| G4 guess resistance | pass: 0/200,000 anchored triples; 49,985,001 candidates at measured shipping seed |
| G5 density/cost | shipping sample 0/200,000; demo exactly 12/105; reference 102,500,000 distance evaluations |
| G6 attacks | pass: each of four attacks succeeded 0/8; reference scan solved 1/1 as expected |
| G7 scaling | pass: doubled instance verifies; candidate space grows from 49,985,001 to 935,129,881 |
| G8 canonical key | pass: 100/100 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 caps | pass: 18 characters, 5 estimated tokens, 3 atoms, 168 intended operations |

The four failing attacks are degree/outlier tie-breaking, farthest-first,
256 anchored random restarts per instance, and the obvious pair of axis
antipodes. Every torus vertex has degree four; the geometric heuristics leave
reflection ambiguities. The successful reference algorithm is reported
separately, as Track B requires.

## Oracle loop

| Preset | Seed | Model | Solved? | Outcome |
|---|---:|---|---|---|
| easy | 1256714223 | openai/gpt-5.6-terra | no | parsed triple had an edge-signature collision |
| easy | 188525372 | google/gemini-3.8-flash | no | reasoning budget exhausted before an answer was emitted |
| easy | 988732433 | openai/gpt-5.6-terra | no | parsed triple had an edge-signature collision |

The script-owned verdict is `hardened`, with zero escalations. The empty
Gemini response is explicitly preserved in the transcript; it was not an API
error, and the other two attempts emitted concrete but invalid witnesses.

## G9 diagnostic arms

| Arm | Solved / attempts |
|---|---:|
| bare | 0 / 3 |
| structural hint | 2 / 3 |
| placebo hint | 0 / 3 |

The hinted-minus-placebo rate is `2/3`. The structural hint names the
half-cycle antipode and simultaneous quarter offsets without giving a
procedure. Its large effect is evidence that the benchmark difficulty lies in
finding the symmetry: when the invariant is named, two solvers can execute the
compact route. This diagnostic does not gate shipping. The answer and route
remain within G9(c): 18 characters, 3 atomic elements, and 168 operations.

## Use

From this directory:

```python
from gen_1602_00291 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=1234, **DIFFICULTY["easy"])
prompt = render(inst)
wire = "Work omitted. <answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = parse_answer(wire)
ok, reason = verify(inst, candidate)  # (True, "ok")
```

From the repository root, emit deterministic samples with:

```bash
bash scripts/emit.sh 1602.00291 20
```

## Caveats

This family becomes easy if the solver remembers Theorem 7 or recognizes the
half/quarter-cycle pattern; the hinted arm confirms that, and that is the
intended Track B distinction. The affine layers are public obfuscation, not a
cryptographic claim. The 0/200,000 guess result samples uniformly from sorted,
distinct, anchored triples; it does not model a solver with a strong geometric
prior and is not an exact count of shipping solutions. Only the demo solution
count is exact.

No external ILP, CP-SAT, or optimized set-cover package was run because the
module is standard-library-only. Instead, the stronger construction-aware
exact signature scan was implemented and succeeded, as it should on Track B.
The canonical key is complete for generated shipping tori by the unordered
pair of cycle lengths; it intentionally collapses anchors, coordinate
translations/reflections, factor swaps, and public label changes. The self-test
checks those transformations and compositions explicitly.
