# arXiv 1603.04180 — simultaneous loose-path connectors

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP/SAT-style constraint search |
| certificate form | integer tuple (five labelled reservoir pairs) |
| intuition | change of variables: reverse permutation layers instead of scanning colours |
| domain essentiality | native |
| reduction | none |

This generator turns Section 2.2 of Bastos, Mota, Schacht, Schnitzer, and
Schulenburg, [*Loose Hamiltonian cycles forced by large \((k-2)\)-degree —
approximate version*](https://arxiv.org/abs/1603.04180), into an exact witness
problem. The solver receives an implicitly represented 4-uniform hypergraph, a
reservoir, and five pairs of singleton ends. It must give five mutually
disjoint one-edge loose 1-paths. Checking a witness requires only index checks
and exact fixed-width add, rotate, and XOR operations.

Trust status: all local gates G1–G9(c) pass, and the script-owned bare oracle
loop returned **hardened** at the medium preset: easy was solved on 1/3 attempts,
then medium held on 0/3. The two G9 hint diagnostics were attempted separately
but became incomplete when the OpenRouter key reached its total limit;
structural was 0/2 and placebo 0/1 before the 403 errors. Those errors are
retained and are not counted as model failures.

## Construction and paper basis

Section 1 defines an \(\ell\)-path and its ends. Connecting Lemma 5 in Section
2.2 says that prescribed pairs of ends can be joined by mutually disjoint paths
of at most four edges when every \((k-2)\)-set has sufficiently many completing
reservoir pairs. In its first proof case, \(k-2\ge 2\ell\), the certificate is
produced by finding a completing pair outside the forbidden vertices. This
module takes \(k=4,\ell=1,m=5\), where each connector can be a single edge.

Reservoir vertex `R_j` has a fixed-width colour word. Every add/rotate/XOR
layer is a permutation. There are `B` copies of every colour, and four distinct
vertices form an edge exactly when their colours XOR to zero. For every two-set,
at least `eta=1/(2q)` of all reservoir pairs complete it after pairs touching
that two-set are excluded. The named difficulty presets use
`B=2048*m*q^2`, so `r=Bq` is twice Lemma 5's required
`32*k*m/eta^3` bound. The generator independently knows a certificate by
inverse generation: it samples all ten reservoir vertices first and chooses
terminal colours around them.

Theorem 3's Hamilton-cycle threshold is an existence theorem, not a hardness
result. A random dense planted-cycle generator would have many cycles and would
not justify Track A. This family instead makes its efficient mechanical method
explicit, as Track B requires.

## Why Track B is hard in context

The reference algorithm fixes one reservoir colour for each terminal pair and
scans all `2^width` colours until it finds the complement. Its complexity is
`O(m*2^width*layers)`. Across eight medium shipping instances it solved 8/8 and
averaged 708,490 colour tests, 11,335,851 counted exact operations, and 2.326
seconds in an unloaded measurement. The final shared-machine self-test recorded
10.110 seconds (maximum 14.149 seconds); the operation count is deterministic.

The compact route notices that every layer is bijective and reverses its XOR,
rotation, and addition in the opposite order. At the medium preset this takes
90 simple exact word operations for all five paths. The gap between 11.3 million
mechanical operations and 90 structured operations is the Track B claim; no
average-case or complexity-theoretic hardness is claimed.

## Worked demo (`width=3`, `m=3`, `layers=1`, `blocks=1`, `seed=7`)

The complete rendered instance is:

```text
Find simultaneous one-edge loose paths in the following 4-uniform hypergraph.

Definitions.
A 4-uniform hypergraph has vertices and unordered edges, each edge containing exactly four distinct vertices.
A loose 1-path is an ordered sequence of such edges in which consecutive edges share exactly one vertex; a one-edge path has any chosen singleton at each end.
There are 6 terminal vertices X0,Y0,...,X2,Y2 and reservoir vertices R_j for every integer 0 <= j < r.
Colours are 3-bit unsigned words, so q = 2^3 = 8; XOR is bitwise exclusive-or.
A left rotation moves bits falling off the most-significant end back into the least-significant end, keeping exactly the stated width.
The reservoir has B = 1 complete colour blocks and r = B*q = 8.

Reservoir colours.
For R_j start with the 3-bit word z = j mod 8. Apply these layers from top to bottom:
  layer 1: add 5 modulo 2^3; rotate the 3-bit word left by 2; XOR with 2
The final word is col(R_j), represented as an integer in 0,...,7.
Terminal colours are:
  X0: 4    Y0: 1
  X1: 5    Y1: 2
  X2: 5    Y2: 3

Four distinct vertices form a hyperedge exactly when the bitwise XOR of their four colours is 0.
For each i, connect Xi to Yi by one hyperedge {Xi,Yi,R_ai,R_bi}.
The m paths must be mutually vertex-disjoint, so every reservoir index used anywhere must be different.

Return exactly 3 pairs in terminal order i=0,...,2.
Within every pair require 0 <= a_i < b_i < 8; indices are 0-based, the outer list order is fixed by i, and repeats are forbidden.
Use a JSON list of two-integer lists.
Give your final answer inside <answer></answer> tags, as [[a_0,b_0],[a_1,b_1],...].
Example: <answer>[[0,1],[2,3],[4,5]]</answer>
Output nothing else inside the tags.
```

One answer is `[[0,1],[2,3],[4,7]]`, for which `verify` returns
`(True, "ok")`. Replacing the first pair by `[0,0]` returns
`(False, "path_0_repeated_vertex")`. A person can solve this demo on paper by
tabulating eight colours. It is intentionally below Lemma 5's quantitative
reservoir bound; every named difficulty preset above it satisfies the bound.

## Difficulty presets

| preset | width | colours q | layers | reservoir size r | answer atoms | compact ops | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 8 | 1 | 8 | 6 | 18 | hand-scale; hardener skips it |
| easy | 17 | 131,072 | 4 | 23,058,430,092,136,939,520 | 10 | 75 | solved on 1/3 bare attempts |
| medium | 18 | 262,144 | 5 | 184,467,440,737,095,516,160 | 10 | 90 | **shipping; held on 0/3 bare attempts** |
| hard | 19 | 524,288 | 6 | 1,475,739,525,896,764,129,280 | 10 | 105 | unused reserve rung |

## Gate results

| gate | measured result |
|---|---|
| G1 | pass; 12/12 witnesses verify, with 9 theorem-condition checks |
| G2 | pass; drop/swap/duplicate/empty/out-of-range give five distinct failures |
| G3 | pass; realistic fenced prose round-trips; garbage returns `None` |
| G4 | pass; 0/200,000 uniform structured candidates verify |
| G5 | pass; shipping density 0/200,000; demo exact count 8/2,520; reference mean 708,490 iterations and 10.110 s |
| G6 | pass; four in-context attacks each 0/8; reference scan 8/8 as expected |
| G7 | pass; doubling the colour space raises q from 262,144 to 524,288 while the answer stays at ten atoms |
| G8 | pass; 100/100 relabelling/composition checks preserve key and witness; 20/20 unrelated keys distinct |
| G9(c) | pass; 237 characters, 60 estimated tokens, 10 atoms, 90 intended operations |

The failed attacks were extreme-index outliers, a 32-colour greedy shortlist,
256 uniform random restarts, and the plausible by-hand mistake of reversing
only the outer mixing layer.

## Oracle loop and G9 diagnostic

The bare loop used the current two-vendor pool. Empty length-limited responses
count as failed attempts under `harden.py`; API errors never do.

| preset | seed | model | solved | verification result |
|---|---:|---|---|---|
| easy | 2,096,960,634 | Gemini 3.8 Flash | yes | valid witness |
| easy | 1,319,057,793 | GPT-5.6 Terra | no | first four-set was not an edge |
| easy | 1,642,496,140 | GPT-5.6 Terra | no | first four-set was not an edge |
| medium | 395,608,683 | GPT-5.6 Terra | no | first four-set was not an edge |
| medium | 981,471,978 | Gemini 3.8 Flash | no | empty at the 32,000-token limit |
| medium | 449,324,083 | Gemini 3.8 Flash | no | empty at the 32,000-token limit |

| G9 arm at medium | solved / scorable attempts | API-error rows | status |
|---|---:|---:|---|
| bare | 0/3 | 0 | complete; hardened |
| structural | 0/2 | 4 | incomplete after quota exhaustion |
| placebo | 0/1 | 4 | incomplete after quota exhaustion |

The observed hinted-minus-placebo difference is `0.0`, but the unequal,
incomplete denominators make it inconclusive: the run does not establish
whether naming the permutation invariant gives real help. G9(c) is unaffected:
the answer is 237 characters (60 estimated tokens), ten atoms, and the intended
route is 90 exact word operations.

## Use

```python
import json
import gen_1603_04180 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
problem = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

After a successful hardening run, emit examples from the repository root with:

```bash
bash scripts/emit.sh 1603.04180 20
```

## Caveats

- The word colouring is a benchmark construction, not a structure asserted by
  the paper. The hypergraph, reservoir, ends, and path certificate are native,
  and the named presets satisfy Connecting Lemma 5, but the compact decoder is
  generator-specific.
- `0/200000` concerns uniformly sampled labelled, globally disjoint, unordered
  reservoir pairs. It says nothing about a solver that recognizes the reversible
  layers; that solver has the 90-operation route.
- The reference scan exploits the colour period. No industrial SAT/SMT or
  CP-SAT implementation, general hypergraph path solver, or alternative
  algebraic attack was run.
- The canonical key covers affine GF(2) colour maps, colour-coordinate
  relabelling, block rotation, pair reorder, endpoint swap, and tested
  compositions. It is not a general hypergraph-isomorphism canonical form.
- The demo is inverse-generated but not theorem-scale. Easy, medium, and hard
  satisfy the lemma's numerical hypotheses exactly as recorded in each instance.
- The bare multi-vendor hardness run is complete. The G9 structural/placebo
  diagnostic is not: quota exhaustion left only 2 and 1 scorable attempts,
  respectively, so its `0.0` difference must not be over-interpreted.
