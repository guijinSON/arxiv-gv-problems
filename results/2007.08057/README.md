# arXiv:2007.08057 — verified Cluster Vertex Deletion generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `combinatorics` |
| Object regime | `finite_field` |
| Computational core | `graph` (succinct bipartite two-colouring is executed by finite-field linear algebra) |
| Certificate form | `exact_symbolic` |
| Intended intuition | `invariant` — the XOR of all displayed Cayley generators is the hidden parity functional |
| Domain essentiality | `licensed_reduction` |
| Reduction | `paper_licensed`, Proposition 18's pendant-edge reduction from Vertex Cover to Cluster Vertex Deletion |

## What this family asks

The source is Aprile, Drescher, Fiorini, and Huynh, [*A Tight Approximation Algorithm for the Cluster Vertex Deletion Problem*](https://arxiv.org/abs/2007.08057). Section 1 defines a cluster graph as a disjoint union of cliques and a CVD hitting set as a vertex set whose deletion leaves a cluster graph, equivalently a set meeting every induced three-vertex path.

An instance gives a succinct Cayley graph on `GF(2)^d`: its original vertices are all `d`-bit vectors, and each displayed nonzero mask `s` adds all edges `x--(x XOR s)`. One pendant vertex is then attached to every original vertex, exactly as in Proposition 18. The requested witness `[w,b]` denotes one parity hyperplane of original vertices. The checker accepts any nonzero `w` that has inner product one with every generator; either side `b` is valid.

Generation is inverse, not search: it samples `w` first, samples every generator from the affine hyperplane `<w,s>=1`, forces their total XOR to equal `w`, and requires full rank. Alternation makes the chosen parity side a vertex cover. Any one generator supplies a perfect matching of size `2^(d-1)`, proving the cover is minimum. Proposition 18 makes original-only CVD sets exactly the vertex covers; a CVD set using a pendant can replace it by its parent without increasing its size, so unrestricted CVD has the same optimum. Verification is just exact hexadecimal decoding and GF(2) inner products; it never reads `inst["answer"]`.

## Why Track B, and what is easy

This is not a Track A claim. The exact reference method two-colours the succinct Cayley graph by solving the `m` equations `<w,s>=1` with Gaussian elimination over `GF(2)`, taking `O(m d^2)` scalar-bit operations. At the shipping preset `d=72,m=216`, eight seeds averaged 474,459 counted scalar-bit operations (6,375 row XORs) and 0.0009 seconds. The compact route notices the planted global invariant and XORs the 216 displayed words, taking 215 word-XOR operations. The gap—dense elimination versus one accumulator—is the claimed no-tool compression.

The paper itself gives several warnings against an overbroad hardness claim. Theorem 1 and Section 3 give an `O(N^4)` 2-approximation on an explicit `N`-vertex graph. Section 1.3 records exact `1.811^k N^O(1)` and `O(1.488^N)` algorithms. Lemma 13 solves paths and cycles exactly in polynomial time, while the conclusion leaves chordal and chordal-`2P3`-free exact complexity open. The paper's UGC and LP lower bounds are worst-case results; they do not prove this generated distribution hard.

## Worked demo

For `make_instance(n=4, m=4, seed=3)`, `render(inst)` is:

```text
Minimum Cluster Vertex Deletion in a succinct graph

All arithmetic on bit-vectors below is over GF(2). A d-bit vector is written as
exactly 1 lowercase hexadecimal digits, including leading zeroes. XOR is
bitwise exclusive-or. For vectors a and z, <a,z> is the parity (0 for even, 1
for odd) of the number of 1-bits in a AND z.

A cluster graph is an undirected simple graph whose connected components are
complete graphs. A cluster vertex-deletion hitting set is a set of vertices
whose deletion leaves a cluster graph.

Here d=4. Define an undirected simple graph H as follows. For every d-bit
vector x there are two vertices O_x (an original vertex) and P_x (its pendant).
There is an edge O_x--P_x for every x. There is also an edge O_x--O_(x XOR s)
for every x and every generator mask s in the list below. These are all edges;
repeated descriptions of the same undirected edge count only once.

Generator masks (4 total, indices are only labels):
  000: 2
  001: 9
  002: 5
  003: d

Your answer must be a pair [w,b]. Here w is a nonzero d-bit vector in exactly
1 lowercase hexadecimal digits, and b is the integer 0 or 1. The pair
symbolically denotes the deletion set

    X(w,b) = { O_x : <w,x> = b }.

No pendant P_x is deleted. Find any [w,b] for which X(w,b) is a minimum-cardinality
cluster vertex-deletion hitting set of H. Both b choices are allowed if valid.
The minimum deletion size is promised to be 8; you do not write out those
vertices. Order in the two-element pair matters.

Give your final answer inside <answer></answer> tags as a JSON pair
["w",b], with the hexadecimal mask quoted and b unquoted.
Example of format only: <answer>["1",0]</answer>
Output nothing else inside the tags.
```

XOR gives `2 XOR 9 XOR 5 XOR d = 3`, so a hand-solvable answer is `["3", 0]`:

```text
verify(inst, ["3", 0]) -> (True, "ok")
verify(inst, ["1", 0]) -> (False, "w does not alternate across every generator edge")
```

The demo is genuinely hand-scale: it needs three one-digit hexadecimal XORs and four parity checks.

## Difficulty presets

| Preset | `d=n` | `m` | Succinct graph vertices | Candidate language | Compact operations | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 4 | `2^5` | `2(2^4-1)` | 3 | hand demo |
| easy | 72 | 216 | `2^73` | `2(2^72-1)` | 215 | **shipping** |
| medium | 80 | 240 | `2^81` | `2(2^80-1)` | 239 | locally passes |
| hard | 96 | 288 | `2^97` | `2(2^96-1)` | 287 | locally passes |

No named preset was rejected by a local gate. `SHIPPING_DIFFICULTY` remains `easy` because the required oracle ladder could not obtain a valid attempt.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified; all answers JSON-round-trip |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged model-style prose parsed and verified |
| G4 | pass | 0 hits / 200,000 structure-aware samples; exact density `1/(2^72-1) = 2.117582368135751e-22` |
| G5 | pass | exactly 2 shipping-language witnesses; demo enumeration also found 2; reference cost 474,459 scalar-bit operations |
| G6 | pass | four no-tool attacks each 0/8; Gaussian elimination 8/8 as expected |
| G7 | pass | doubled dimension 144 built and verified; candidate-space bits rose 73 to 145 |
| G8 | pass | 140/140 composed relabellings invariant and valid; 20/20 unrelated seeds had distinct keys |
| G9(c) | pass | 24 characters, about 6 tokens, 2 atoms, 215 word-XOR operations |

The four failing G6 attacks are: treating each generator as the answer, greedy pivots without elimination, 256 random restarts, and the all-ones/unit-vector/partial-XOR ansatz. Generator order is shuffled, and no displayed row has a privileged marginal role.

## Oracle loop and G9 arms

The official `harden.py` run was attempted, but the configured OpenRouter key returned HTTP 403 `Key limit exceeded (total limit)` before any valid oracle attempt. Errors do not count as model failures, so this is **not** hardness evidence and there is no `hardened` verdict.

| Bare call | Preset | Seed | Model result | Reason |
|---:|---|---:|---|---|
| 1 | easy | 252589817 | error | OpenRouter HTTP 403 key limit |
| 2 | easy | 1513711886 | error | OpenRouter HTTP 403 key limit |
| 3 | easy | 1028463441 | error | OpenRouter HTTP 403 key limit |
| 4 | easy | 110744654 | error | OpenRouter HTTP 403 key limit |

| G9 arm | Solved / valid attempts | Diagnostic conclusion |
|---|---:|---|
| bare | 0 / 0 | unavailable; error-only transcript |
| structural hint | 0 / 0 | unavailable; error-only transcript |
| placebo hint | 0 / 0 | unavailable; error-only transcript |

`hinted - placebo` is therefore undefined. The script-owned error transcripts are retained as evidence of the external blocker. After the key is replenished, rerun all three arms in separate directories and update `G9_ORACLE_RESULTS`; do not infer `0/3` from these errors.

## Use

```python
import json
import gen_2007_08057 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)  # replace wire with a solver's raw response
ok, reason = g.verify(inst, candidate)
assert ok, reason
```

From the repository root, after a successful official hardening run:

```bash
bash scripts/emit.sh 2007.08057 20 easy
```

## Caveats

- The result is locally verified but **not ready to submit** until STEP 4 produces a valid multi-vendor `hardened` transcript. The current API-key failure is the binding blocker.
- The solver is restricted to succinct parity-hyperplane witnesses, not arbitrary explicit deletion sets. This is faithful to the paper's graph objects through its own Proposition 18 reduction, but it tests recognition inside a deliberately structured subclass, not general CVD.
- G4 samples uniformly from the stated nonzero-functional/side language. Its tiny density says nothing about priors over arbitrary vertex subsets, nor about a solver that recognizes the XOR invariant.
- The 215-operation G9 count treats one XOR of two 72-bit words as one exact vector operation. Counting bit or hexadecimal-digit work would be much larger; this is the main no-tool-suitability uncertainty and is why the missing oracle diagnostic matters.
- A full SAT/ILP encoding, Walsh-Fourier recovery, and spectral analysis of the exponentially expanded graph were not run. Gaussian elimination is the directly relevant standard exact attack on the stated certificate language; it succeeds by design.
- `canonical_key` is a strong cheap invariant of four-circuit structure under generator reordering and affine `GF(2)` relabelling, not a complete Cayley-graph isomorphism test. Non-isomorphic instances can theoretically collide even though none of 20 unrelated seeds did.
