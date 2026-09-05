# arXiv 1303.2263 — compact Hamilton-cycle certificates

Status: **locally verified but not release-ready**. All executable gates G1–G9(c)
pass. The required oracle hardening and both G9 diagnostic arms were attempted
with the repository harness, but OpenRouter returned HTTP 403 `Key limit
exceeded (total limit)` on every redraw. Those script-owned error transcripts
are retained; no API error is counted as a model failure and no oracle hardness
claim is made.

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple: two labelled cross-edges |
| intended intuition | change of variables into a common hidden coordinate |
| domain essentiality | native |
| reduction | none |

## What the family is

The source is Bo Ning, [*Fan-type degree condition restricted to triples of
induced subgraphs ensuring Hamiltonicity*](https://arxiv.org/abs/1303.2263).
An instance is a finite simple graph with two cliques of size `q=2^n`. Two
perfect matchings cross between them, hidden by independently chosen reversible
fixed-width word maps. The solver returns two disjoint cross-edges. The statement
specifies how those edges expand to a path through every vertex of the left
clique and a path through every vertex of the right clique, yielding a Hamilton
cycle.

Checking needs four range/distinctness tests and two exact evaluations of the
cross-edge predicate. It never reads the planted answer. Every accepted pair of
cross-edges certifies the deterministic full cycle described in the problem.

## Paper basis and why this is Track B

Section 1 defines heavy vertices and induced `f`-heavy subgraphs. Theorem 5 says
that a 2-connected graph is Hamiltonian if it is
`{K_1,3,P_7,D}`-`f`-heavy or `{K_1,3,P_7,H}`-`f`-heavy. Here the graph has order
`2q`, while every vertex has `q-1` neighbours in its own clique and two across
the cut, hence degree `q+1 >= (2q)/2`. Every vertex is heavy, so every induced
copy in either theorem alternative is automatically `f`-heavy. The graph is
2-connected because deleting one vertex leaves two nonempty connected cliques
with cross-edges between them.

The paper does **not** prove hardness for these promised graphs. Indeed, Theorem
1 and Remark 1 identify the global Fan condition as an easier sufficient regime,
and this construction deliberately lies inside it. Track A would therefore be
false.

The honest Track B reference algorithm scans right-clique labels until it finds
two disjoint cross-edges, then splices the two clique paths. For graph order
`N=2^(n+1)`, it runs in `O(N * layers) = O(2^n * layers)` exact word operations
and solves 8/8 shipping instances. The
final gate run measured a median 69,409 edge tests, 1,388,222 counted operations,
and 0.077866 seconds. The compact route chooses left labels 0 and 1, evaluates
their left coordinates, and reverses the right word map to obtain matching
right labels. That route uses 80 counted word operations at the proposed shipping
preset. The benchmark is the gap between those routes, not complexity-theoretic
or average-case Hamiltonicity hardness.

## Worked demo

For `demo` and `seed=7`, the complete rendered instance is:

```text
Find a compact Hamilton-cycle certificate in the graph below.

Definitions.
A finite simple graph has undirected edges, no loops, and no repeated edges.
A Hamilton cycle is a cyclic ordering that visits every vertex exactly once and uses a graph edge at every step, including the last-to-first step.
A vertex in an N-vertex graph is heavy when its degree is at least N/2.
An induced subgraph is f-heavy when, for each two vertices at distance exactly 2 inside that subgraph, at least one is heavy in the whole graph.

Graph.
Set q = 2^4 = 16.  The 2q vertices are L_x and R_y for integers 0 <= x,y < q.
Every two distinct L-vertices are adjacent, and every two distinct R-vertices are adjacent.
Cross-edges L_x--R_y are defined by the exact word maps and block rotation below.
All word operations retain exactly 4 bits. XOR is bitwise exclusive-or.
A left rotation moves bits falling off the most-significant end back into the least-significant end.

Left word map A(x):
For A(x), start with z equal to its raw index.
  layer 1: add 2 modulo 2^4; rotate the 4-bit word left by 2; XOR with 3
The resulting integer is A(x).

Right word map B(y):
For B(y), start with z equal to its raw index.
  layer 1: add 1 modulo 2^4; rotate the 4-bit word left by 1; XOR with 6
The resulting integer is B(y).

Block rotation rho.
Partition 0,...,q-1 into consecutive intervals having these lengths, in this order:
  8, 4, 4
Within each interval, rho moves one position forward, wrapping at that interval's end.
There are no one-element intervals.

The cross-edge rule is:
  L_x--R_y is an edge exactly when B(y) = A(x) or B(y) = rho(A(x)).
No other cross-edges exist.
Every vertex has q-1 neighbours in its own side and two across the cut, hence degree q+1 >= (2q)/2; in particular every vertex is heavy.

Certificate and its Hamilton cycle.
Return two cross-edges [[x0,y0],[x1,y1]]. They denote the following cyclic order:
  L_x0; every L_z with z not in {x0,x1}, in increasing raw index; L_x1;
  R_y1; every R_z with z not in {y0,y1}, in increasing raw index; R_y0; back to L_x0.
Because each side is a clique, this is a Hamilton cycle exactly when the two displayed cross pairs are edges and have four distinct endpoints.

Require 0 <= x0 < x1 < 16, 0 <= y0,y1 < 16, and y0 != y1.
Indices are 0-based. The outer order is fixed by x0 < x1; repeats are forbidden; each pair is [left_index,right_index].
Use a JSON list containing exactly two two-integer lists.
Give your final answer inside <answer></answer> tags, as [[x0,y0],[x1,y1]].
Example: <answer>[[0,1],[2,3]]</answer>
Output nothing else inside the tags.
```

One answer is `[[2,1],[3,15]]`; `verify` returns `(True, "ok")`.
Swapping the two pairs gives `[[3,15],[2,1]]`, which returns
`(False, "left_endpoints_not_in_strictly_increasing_order")`. A person can solve
this demo by tabulating the sixteen values of each one-layer map.

## Difficulty presets

| preset | width `n` | vertices `2q` | layers | cross components | answer atoms | compact ops | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 4 | 32 | 1 | 3 | 4 | 20 | hand-scale; skipped by hardener |
| easy | 16 | 131,072 | 6 | 12 | 4 | 80 | proposed shipping preset; oracle unavailable |
| medium | 17 | 262,144 | 8 | 14 | 4 | 104 | reserve rung |
| hard | 18 | 524,288 | 10 | 16 | 4 | 128 | reserve rung |

`SHIPPING_DIFFICULTY` is provisionally `easy`. It must not be treated as an
oracle-validated shipping choice until the bare harness run completes.

## Gate results

| gate | measured result |
|---|---|
| G1 | pass; 12/12 planted witnesses and 12/12 theorem-hypothesis checks |
| G2 | pass; empty/drop/swap/duplicate/out-of-range all rejected for distinct reasons |
| G3 | pass; fenced prose round-trips and garbage returns `None` |
| G4 | pass; 0/200,000 structure-aware guesses; exact density `9.313296800428345e-10` |
| G5 | pass; 8,589,737,984 exact valid answers among 9,223,090,564,025,548,800 certificate words; reference median 69,409 tests / 1,388,222 operations / 0.077866 s; demo brute-force count 464 |
| G6 | pass; four attacks each 0/8; successful Track B reference 8/8 is separate |
| G7 | pass; doubling vertices 131,072 to 262,144 leaves the answer at four atoms |
| G8 | pass; 80/80 relabelling/composition invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass; 32 characters, 8 estimated tokens, 4 atoms, 80 intended operations |

The four failing attacks were the all-degrees-tied smallest-label choice,
nearest raw labels, 256 structure-aware random restarts, and undoing only the
last right-map layer.

## Oracle loop and G9 diagnostic

The bare harness produced no scorable calls. These are errors, not failures:

| preset | seed | model | result | reason |
|---|---:|---|---|---|
| easy | 1,255,676,080 | `openai/gpt-5.6-terra` | error | HTTP 403 key total limit |
| easy | 652,808,318 | `openai/gpt-5.6-terra` | error | HTTP 403 key total limit |
| easy | 1,368,714,543 | `google/gemini-3.8-flash` | error | HTTP 403 key total limit |
| easy | 1,854,676,522 | `google/gemini-3.8-flash` | error | HTTP 403 key total limit |

| G9 arm at easy | solved / scorable attempts | API-error rows | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | unavailable |
| structural | 0/0 | 4 | unavailable |
| placebo | 0/0 | 4 | unavailable |

The hinted-minus-placebo difference is undefined with zero scorable attempts;
the report stores `0.0` only as the zero-denominator convention. It says nothing
about whether the change-of-variables hint helps. The structural and placebo
transcripts were generated in separate scratch directories, so the bare
transcript was not overwritten.

## Use

```python
import json
import gen_1303_2263 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
problem = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

After a successful bare hardening run, emit examples from the repository root:

```bash
bash scripts/emit.sh 1303.2263 20
```

## Caveats

- This is a native Hamilton-cycle problem, but it uses the paper's easy global
  heavy-vertex subregime. It does not exercise the sharp distinction between
  Theorem 5 and Fan's Theorem 1.
- The two hidden matching layers are a benchmark construction, not a graph
  family proposed by the paper. The paper supplies the Hamiltonicity condition;
  transformation of a known two-clique instance supplies the certificate.
- `0/200000` samples labelled pairs with the explicit shape, ordering, range,
  and distinctness constraints already enforced. The exact density corroborates
  it. Neither number measures a solver that recognizes and reverses the public
  word maps.
- The successful reference algorithm is tailored to this two-clique family. No
  general Dirac/Fan constructive algorithm, generic Hamiltonian backtracker,
  SAT/ILP encoding, or alternative algebraic decoder was run.
- The graph is represented by an exact adjacency predicate rather than an
  explicit 131,072-vertex adjacency table. Verification is exact, but input
  succinctness is part of the benchmark.
- The canonical key is complete for this represented two-matching family via
  its cross-component half-length multiset. It is not a general graph
  isomorphism canonicalizer.
- Most importantly, STEP 4 remains externally blocked. Restore the OpenRouter
  quota and rerun the bare, structural, and placebo harnesses before submission.
