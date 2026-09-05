# Total-domatic colourings for cubic graphs (arXiv:1512.04748)

> **Status:** every local gate passes, but the result is not yet shippable. The
> required OpenRouter calls were rejected before inference with HTTP 403 `Key
> limit exceeded (total limit)`. Those service errors are preserved and are not
> counted as model failures or as evidence of hardness.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | graph |
| Certificate | integer tuple: one 0/1 colour per vertex |
| Native objects | simple cubic graph, open neighborhoods, two total dominating colour classes |
| Intuition | decomposition: recognize a spanning factor of 4-cycles |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

Akbari, Motiei, Mozaffari, and Yazdanbod's [*Cubic Graphs with Total Domatic
Number at Least Two*](https://arxiv.org/abs/1512.04748) calls a vertex set total
dominating when it contains a neighbor of every vertex. The solver receives a
simple cubic graph and must colour every vertex 0 or 1 so that each open
neighborhood contains both colours. The two colour classes are then disjoint
total dominating sets. Checking a candidate is one exact pass over the adjacency
list; `verify` does not read the planted answer.

Generation is by composition, not search. It creates disjoint 4-cycles, assigns
an independently rotated cyclic `0011` pattern to each, and only then adds a
random perfect matching as the third edge at every vertex. The two internal
cycle neighbors already show both colours, so every later matching works.
Vertex names, vertex order, and neighbor order are shuffled. Every vertex lies
on a 4-cycle and therefore cannot be the center of the paper's ten-vertex
radius-two tree `L`; Theorem 2 applies directly. The construction may also be
checked without that theorem by inspecting each planted square.

## Why this is Track B

Track A would be false here. Section 2, Lemma 2 explicitly gives an iterative
algorithm for an `F`-partition of every `L`-free cubic graph, and Theorem 2
colours the pieces. With adjacency dictionaries its local updates are
polynomial (linear in this bounded-degree specialization), although the paper
does not state an asymptotic bound. Theorem 1 also makes all regular degrees
`r >= 4` easy, and the introduction records that a cycle works exactly when its
order is divisible by four.

The executable reference algorithm independently enumerates 4-cycles and runs
Algorithm X on their incidences. On this distribution its cost is
`O(V Delta^3 + 2^d V)`, where `Delta=3` and `d` is the bounded number of
non-factor squares. At the shipping preset (`V=224,d=0`) it solved 8/8 audit
instances in 0.001250 seconds on average with 7,056 counted path, incidence,
branch, and colour operations. The compact route is to see the square factor
and place one cyclic `0011` pattern on each square: 280 local selections and
assignments. That is within the no-tool cap but is not the same as mechanically
searching 224 shuffled adjacency rows.

## Worked demo

`make_instance(n=3, decoy_cycles=0, label_bound=97, seed=0)` is hand-scale: a
person can find its three disjoint squares and colour each `0011` cyclically.

```text
Find a two-colour total-domatic partition of the displayed graph.

Definitions.
The graph is finite, undirected, simple (no loops or repeated edges),
and cubic (every vertex has exactly three distinct neighbors). The open
neighborhood of a vertex consists of its three neighbors, not the vertex
itself. A set is total dominating when every vertex has at least one
neighbor in that set. A valid two-colouring assigns every vertex colour
0 or 1 so that both colour classes are total dominating. Equivalently,
the three neighbors of every vertex must include at least one 0 and at
least one 1. The two colour names may be globally exchanged.

There are 12 vertices. Vertex identifiers are arbitrary
positive integers. In the output, bit i colours the vertex in position i
of the following order; positions are 1-based in this explanation:
  7 5 40 25 42 64 1 72 97 78 54 60

Adjacency list (each undirected edge consequently appears in two rows):
  7: 54 60 97
  5: 40 54 64
  40: 5 42 60
  25: 54 60 72
  42: 1 40 64
  64: 5 42 78
  1: 42 72 97
  72: 1 25 78
  97: 1 7 78
  78: 64 72 97
  54: 5 7 25
  60: 7 25 40

Output exactly 12 comma-separated bits as one JSON list,
in the displayed vertex order. Only the integers 0 and 1 are allowed;
list order matters, no position may be omitted, and no extra position
may be inserted. Bit values themselves may of course repeat.

Give your final answer inside <answer></answer> tags, as that JSON list.
Example syntax for four slots only: <answer>[0,1,1,0]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[1,1,1,0,0,0,1,1,0,0,0,1]</answer>`.

```python
verify(inst, inst["answer"])
# (True, "ok")
verify(inst, inst["answer"][:-1])
# (False, "answer is too short: expected 12 bits")
```

There are exactly 186 valid bit lists among the demo's 4,096 candidates;
the demo illustrates the definition rather than hardness.

## Presets and local gates

The original draft used 36 squares (144 vertices); randomized one-pass greedy
solved 6/8 audit seeds, so that rung was discarded before any oracle call.
The active ladder keeps the answer at 224–232 bits and increases overlapping
decoy squares.

| Preset | Planted squares `n` | Extra 4-cycles `d` | Vertices / answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 3 | 0 | 12 | hand-solvable illustration |
| easy | 56 | 0 | 224 | **shipping preset; local gates pass** |
| medium | 58 | 3 | 232 | harder fallback |
| hard | 58 | 4 | 232 | hardest named rung |

| Gate | Measured result at shipping unless noted |
|---|---|
| G1 | 12/12 planted witnesses verified across all presets; 12/12 JSON round trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced JSON recovered exactly |
| G4 | 0/200,000 uniform structure-aware bit lists; space `2^224` |
| G5 | shipping density 0/200,000; demo exact count 186; strongest failing attack used 512 total restarts, 638,978 operations, 0.248735 s |
| G6 | seven attacks each 0/8; reference square-factor algorithm 8/8, 7,056 operations, 0.001250 s average |
| G7 | 56 -> 112 squares built; the 448-vertex planted answer verified |
| G8 | 20/20 composed relabelings preserved the key and carried witness; 20/20 unrelated keys distinct |
| G9(c) | 449 characters, about 113 tokens, 224 atoms; 280 intended-route operations |

The seven failing attacks are 4-cycle-incidence outlier colouring, label parity,
`0011` in display order, BFS parity, a centered nontrivial adjacency-eigenvector
threshold, deterministic one-pass greedy, and 64 randomized greedy restarts. The
reference square-factor algorithm is deliberately outside `attacks`, because
Track B expects it to succeed.

## Oracle loop and G9 diagnostics

No row below reached a model. The bare run has no `harden_verdict`; it is an
external blocker, not a `hardened` or `too_easy` result.

| Arm | Models attempted | Usable solved/attempts | Service errors | Result |
|---|---|---:|---:|---|
| bare | Gemini (3), Grok (1) | 0/0 | 4 | HTTP 403 before inference |
| structural hint | Grok (4) | 0/0 | 4 | HTTP 403 before inference |
| placebo hint | Gemini (2), GPT-5.6 Terra (2) | 0/0 | 4 | HTTP 403 before inference |

`hinted - placebo` is undefined because neither arm produced a usable attempt.
The structural sentence names only the spanning-square invariant; whether that
information helps an oracle remains unmeasured. The G9(c) size and effort cap
passes independently with the numbers above.

## Use

```python
import gen_1512_04748 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
question = gen.render(inst)
candidate = gen.parse_answer("work... <answer>[0,1]</answer>")
ok, reason = gen.verify(inst, candidate)
```

After a funded OpenRouter run produces `verdict: hardened`, emit from the
repository root:

```bash
bash scripts/emit.sh 1512.04748 20 easy
```

## Caveats

- The required multi-vendor test is incomplete. Do not treat the local panel as
  a substitute, and do not emit this family until the key limit is resolved.
- This is intentionally an easy-with-tools Track B distribution. The 7,056-op
  reference route is short for code; the claim is only that it is awkward to
  execute exactly inside a no-tool prompt, while the square decomposition is
  substantially shorter.
- G4 is uniform over every length-224 bit list, incorporating the answer's exact
  shape and alphabet. Zero sampled hits says little about a graph-aware solver;
  G6 is the separate evidence against such heuristics.
- Optimized SAT/CP-SAT, longer WalkSAT repairs, ILP/SDP relaxations, and learned
  message passing were not tested. The paper's own full `F`-partition procedure
  was analyzed but not separately implemented; the C4 specialization was.
- Conditioning the matching on an exact extra-cycle count is deterministic for
  `(n,seed)` but is not claimed to sample uniformly from all such cubic graphs.
- `canonical_key` uses rooted Weisfeiler–Leman refinement plus exact 4-cycle
  incidence. It passed every generated relabeling and diversity test, but
  nonisomorphic adversarial regular graphs can share that invariant.
- The paper's Theorem 2 is a sufficient condition, not a complete classification
  of all cubic graphs with total domatic number at least two.
