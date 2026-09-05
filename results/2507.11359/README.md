# Perfect matchings in labelled sparse 3-graphs

| Profile field | Value |
|---|---|
| Paper | Jie Han and Jingwen Zhao, [*Perfect Matchings in Random Sparsifications of Dense Hypergraphs*](https://arxiv.org/abs/2507.11359), arXiv:2507.11359v4 |
| Track | **B — no-tool compression** |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `exact_cover` |
| Certificate form | `integer_tuple` (an unordered set of hyperedge labels) |
| Domain essentiality | `native` |
| Reduction | none |
| Intended intuition | invariant: one perfect matching's labels form a hidden affine progression encoded by the first two displayed labels |

## What the family asks

The solver receives an explicit labelled 3-uniform hypergraph and must return a
perfect matching. Section 1.1 of the paper defines exactly these objects: every
hyperedge has three vertices, selected hyperedges must be disjoint, and together
they must cover every vertex. The checker looks up the proposed labels and counts
each vertex's incidence, using integers only; it accepts any perfect matching and
never reads the planted answer.

Generation is inverse. A random perfect matching is sampled first. Further
perfect-matching layers are sampled from the same distribution, then only the
decoy layers undergo degree-preserving endpoint switches. Thus every vertex has
the same degree. Edge and vertex orders are randomized. Finally, an affine
permutation modulo 1,000,003 makes planted labels marginally indistinguishable
from decoy labels while leaving a compact two-anchor invariant. The planted
matching is carried through these transformations, never recovered by solving
the generated instance.

## Why this is Track B

This is not a complexity-theoretic hardness claim. Theorem 1.2 says the dense
problem above the fractional-matching threshold is in P, and Theorem 1.4 plus
Section 8's Procedure 1 gives the paper's polynomial decision route in the
dense-host random-sparsification regime. Declaring Track A while knowing those
algorithms exist would be false. The paper also notes unrestricted 3-uniform
perfect matching is NP-complete, but worst-case hardness says nothing about this
generated distribution.

Two exact reference methods solve every shipping instance. Minimum-column
Algorithm X, the domain-standard exact-cover method, solved 8/8 instances with a
mean 174,384 nodes (maximum 374,923) and 1.512 s mean wall time. A distribution-
specific ordered-pair scan is polynomial, `O((degree*n)^2*n)`: it used 394,410
modular iterations on average (maximum 1,042,240) and 0.030 s. The compact route
recognizes how the first two labels encode an affine progression and emits its 40
terms in 81 modular operations. The benchmark tests discovery of that invariant;
the mechanical routes are easy with code and unrealistic to execute unaided in
the prompt.

The discarded prototype at `n=24, degree=4, mixing=12` did fool the bare oracle
0/3, but it was not shippable: 256 randomized greedy restarts solved 6/8 and
Algorithm X averaged only 434 nodes. The ladder was therefore moved to the
attack-resistant `n=40` regime before the recorded shipping run.

## Worked demo

This is `make_instance(seed=0, **DIFFICULTY["demo"])`, small enough to solve by
hand by crossing out intersecting triples:

```text
Find a perfect matching in the labelled 3-uniform hypergraph below.

Definitions: a 3-uniform hypergraph has vertices and hyperedges, with
every hyperedge containing exactly three distinct vertices. A matching is
a set of pairwise vertex-disjoint hyperedges. It is perfect when every
vertex belongs to exactly one selected hyperedge.

The vertices are the integers 0 through 11, inclusive.
There are 12 hyperedges, each with a distinct integer label.
A perfect matching therefore contains exactly 4 hyperedges.
Hyperedge order and the order of its three vertices have no mathematical
effect. Hyperedge labels are residues modulo the displayed prime, written
as their unique integers from 0 through prime-1; labels identify edges but
only vertex incidence determines whether a proposed set is a matching.
Answer order does not matter, repeats are forbidden, and every stated range
is inclusive.

prime = 1000003
Hyperedges, one per line as `label: vertex vertex vertex`:
765284: 3 6 9
77324: 1 2 11
907343: 0 5 10
65304: 2 5 6
844132: 8 10 11
842608: 0 2 9
464197: 1 3 4
273145: 4 7 8
546678: 0 7 9
218522: 5 6 7
906482: 1 4 10
530565: 3 8 11

Give exactly 4 distinct hyperedge labels, separated by commas.
Give your final answer inside <answer></answer> tags, as a comma-separated list of integers.
Example format only: <answer>12, 47, 105</answer>
Output nothing else inside the tags.
```

The held witness is `[842608, 530565, 218522, 906482]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last label
returns `(False, "wrong number of hyperedges: expected 4")`. A person can solve
this demo directly; the shipping instance has 120 vertices and 200 hyperedges.

## Difficulty presets

| Preset | `n` selected edges | Vertex degree | Mixing passes per decoy edge | Status |
|---|---:|---:|---:|---|
| demo | 4 | 3 | 0 | hand example; never ships |
| easy | 40 | 5 | 24 | **ships; bare oracle 0/3** |
| medium | 40 | 5 | 32 | harder fixed-length fallback |
| hard | 40 | 5 | 40 | harder fixed-length fallback |

`escalate()` first raises mixing, then degree, before increasing answer length.
G7 also built and verified a doubled `n=80` instance.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verify; all answers JSON-native |
| G2 | pass | drop, decoy swap, duplicate, empty, and unknown-label corruptions all rejected with five distinct reasons |
| G3 | pass | tagged model-style prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware fixed-cardinality guesses; language size `C(200,40)` = 2,050,157,995,198,589,154,962,348,028,592,667,411,382,810 |
| G5 | pass | shipping sampled density 0/200,000; demo has exactly 5 solutions among 495 candidates; seed-17 Algorithm X cost 203,477 nodes / 2.065 s |
| G6 | pass | five attacks each 0/8; Algorithm X and affine scan each solve 8/8 as expected |
| G7 | pass | `n=80` builds and verifies; fixed-answer mixing escalation also verifies |
| G8 | pass | 40/40 relabelling invariance checks, 40/40 carried-witness checks, 20/20 unrelated keys distinct |
| G9 | pass | 318 characters, 80 estimated tokens, 40 atomic elements, 81 intended operations |

The five failing G6 attacks are local-intersection outlier, numeric-gap outlier,
deterministic MRV/min-damage greedy, 256 randomized MRV restarts, and the obvious
but wrong progression using the first two labels directly.

## Oracle loop

All replies contained parseable answers; each failed exact verification, so none
is a parser-induced false negative.

| Preset | Model | Seed | Solved | Exact checker result |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 1886362036 | no | vertex 0 coverage 0 |
| easy | GPT-5.6 Terra | 465495788 | no | vertex 4 coverage 0 |
| easy | GPT-5.6 Terra | 1977879129 | no | vertex 23 coverage 2 |

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo success rate is `0.0`. The invariant-only hint did not buy
the tested pool anything, so this diagnostic does not isolate the claimed
intuition; it may mean the hint was too weak or that exact arithmetic/search,
rather than recognition alone, remained the bottleneck. The answer and intended
route remain comfortably inside the G9 caps.

## Use

```python
import gen_2507_11359 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit fresh shipping instances with:

```bash
bash scripts/emit.sh 2507.11359 20 easy
```

Only the Python standard library is used; `gvlib` is unnecessary for this
integer-incidence checker.

## Caveats

This generator produces a synthetic random regular sparse 3-graph, not an
independent binomial sparsification of a specified dense host. It is native
coverage of the paper's hypergraph perfect-matching object, but it does not
empirically validate Theorem 1.4's asymptotic random law or degree threshold.
The affine edge labels are also an intentional benchmark side channel, not a
feature of the paper; removing or independently relabelling them destroys the
compact route and leaves ordinary exact cover.

The 0/200,000 figure is only for uniform 40-subsets of the 200 displayed edge
labels. It is not an estimate under an MRV, SAT, or learned prior, and the exact
number of shipping solutions was not enumerated. Algorithm X and the explicit
greedy/restart panel give more relevant evidence. No external ILP/SAT solver,
tensor/spectral method, or restart budget above 256 was tested. Finally,
`canonical_key` uses weighted color refinement of the edge-intersection graph;
it is invariant under all tested relabellings but is not a complete solution to
3-uniform hypergraph isomorphism.
