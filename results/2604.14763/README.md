# arXiv 2604.14763 — verified Hamiltonian-cycle generator

| profile | value |
|---|---|
| track | **B** — efficient mechanical algorithm, no-tool compression |
| native domain | combinatorics |
| object regime / core | finite discrete / graph |
| certificate | integer tuple: a cyclic ordering of all vertices |
| intuition | invariant: one modular endpoint difference has large multiplicity |
| domain essentiality | native; no reduction |

This module generates the paper’s native objects: (K_{1,4})-free split graphs. A solver receives the split partition, all cross-neighborhoods, and residue annotations on the ordinary independent vertices, and must return a Hamiltonian cycle. Verification checks vertex equality and every consecutive graph edge exactly. The source is Cai, Guo, Lai and Zhou, [“Tight spectral conditions for the Hamiltonicity of (K_{1,r})-free split graphs”](https://arxiv.org/abs/2604.14763).

## Why Track B

Track A would be false. Section 1 of the source paper cites the polynomial side of Renjith–Sadagopan’s [Hamiltonian-cycle dichotomy](https://arxiv.org/abs/1610.00855): Hamiltonian cycle is polynomial-time solvable on (K_{1,4})-free split graphs (their Section 2, Theorem 2.2), while the NP-complete boundary is (K_{1,5})-free (Section 3, Theorem 3.1). The source paper’s Theorem 1.1 makes the claw-free case easier still—Hamiltonicity is equivalent to 2-connectivity.

For these generated instances, deleting the universal independent vertex exposes a cubic graph. Edmonds’ blossom algorithm finds a perfect matching in (O(n^3)); orienting the complementary 2-factor then gives paths that clique edges splice into a Hamiltonian cycle. Across eight shipping instances this took 117,520 counted primitive operations (14,690 per instance) and 0.00515 seconds total. The no-tool route instead notices that the planted spanning cycle’s edges all have one modular difference. Computing and tallying all differences costs at most (3n=282) exact integer operations; the remaining construction is adjacency lookup and output assembly.

Generation is inverse, not search. A circulant cycle and a disjoint perfect matching are sampled first. Each core edge becomes a clique vertex adjacent to its two endpoints and to one universal independent vertex. Every clique vertex has exactly three independent neighbors sharing the universal vertex, so no induced (K_{1,4}) exists. Every ordinary independent vertex has degree three; deleting any two vertices leaves the clique-connected graph connected. Thus the graph is 3-connected, and the source paper’s Theorem 1.2 guarantees Hamiltonicity. The stored cycle is composed directly from the sampled cycle and matching before all vertex IDs and rows are shuffled. These instances use the paper’s class and Hamiltonicity theorem, but they are not claimed to meet the new spectral threshold of Theorem 1.4.

## Worked demo

The `demo` preset (`n=4, seed=3`) renders in full as:

```text
Hamiltonian cycle in a K_{1,4}-free split graph

A finite simple graph is split when its vertices are partitioned into a
clique K (every two distinct vertices of K are adjacent) and an independent
set I (no two vertices of I are adjacent). It is K_{1,4}-free when no five
vertices induce a four-leaf star. A Hamiltonian cycle is a cyclic ordering
of all vertices in which every consecutive pair, including last-to-first,
is an edge.

This graph has N=11 vertices, with IDs 0 through 10.
The residue modulus is n=4. The universal independent vertex is h=10.
The other independent vertices are listed as vertex:residue:
  5:0 1:1 7:2 3:3
Clique vertices K:
  2 9 0 8 4 6

All clique-clique edges are present. There are no independent-independent
edges. The remaining edges are exactly the following cross-neighborhoods;
a row `k: a b c` says clique vertex k is adjacent to independent vertices
a, b, and c:
  8: 10 7 1
  9: 7 10 5
  4: 10 5 3
  0: 10 3 7
  2: 1 10 5
  6: 1 3 10

Output exactly 11 distinct integer vertex IDs in cyclic order, separated by
commas. The first ID must be a clique vertex; either direction is allowed.
Every graph vertex must occur once, with no repetitions.

Give your final answer inside <answer></answer> tags, as a comma-separated
list of integer vertex IDs.
Example: <answer>7, 2, 9, 4</answer>
Output nothing else inside the tags.
```

One answer is `<answer>4, 5, 9, 7, 8, 2, 1, 6, 3, 0, 10</answer>`. `verify` returns `(True, "ok")`; deleting the last entry returns `(False, "cycle has wrong length")`. This demo is hand-solvable: pair each nonhub independent vertex with incident clique vertices and use clique edges to join the pieces.

## Presets and local gates

| preset | core `n` | graph vertices / answer atoms | status |
|---|---:|---:|---|
| demo | 4 | 11 | hand example; exact enumeration |
| easy | 22 | 56 | local gates pass |
| medium | 46 | 116 | local gates pass |
| hard | 94 | 236 | **shipping preset** |

| gate | measured result |
|---|---|
| G1 | 16/16 planted answers verify; all JSON round-trips |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | 236-entry model-style tagged response round-trips |
| G4 | 0/200,000 structure-aware random candidates valid; bounded space shown in `selftest_report.json` |
| G5 | demo: 2,304 valid of 518,400; shipping density sample 0/200,000; strongest failing attack 302,061 nodes |
| G6 | four attacks each 0/8; blossom reference 8/8 as Track B expects |
| G7 | vertex counts 11, 56, 116, 236; doubled `n=188` instance has 471 vertices and verifies |
| G8 | 20/20 composed relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | 1,070 characters, 473 conservative lexical tokens, 236 atoms, 282 exact arithmetic operations |

## Oracle loop and G9 arms

The required harness was invoked, but the configured OpenRouter account returned HTTP 403 “Key limit exceeded” on every redraw. Errors do not consume attempts and are not model failures, so there is no hardness verdict yet.

| run | preset / seeds | counted solved attempts | outcome |
|---|---|---:|---|
| bare | easy / 567135398, 2133828684, 1119171338, 275495031 | 0/0 | four error redraws; pool unreachable |
| structural hint | — | 0/0 | not run: same account limit |
| placebo hint | — | 0/0 | not run: same account limit |

Consequently `hinted - placebo` is not measurable yet. The G9 cap gate passes, but the three-arm diagnostic and Step 4 remain incomplete. `llm_loop_transcript.jsonl` is the harness-written error record, not hardness evidence. Once the account limit is restored, rerun all three arms in separate directories and replace the zero-attempt fields and this table.

## Use

```python
import gen_2604_14763 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=123)
ok, reason = g.verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
assert g.parse_answer("<answer>" + g._format_answer(inst["answer"]) + "</answer>") == inst["answer"]
```

From the repository root, after successful oracle hardening:

```bash
scripts/emit.sh 2604.14763 20 hard
```

## Caveats

- The residue annotations are benchmark structure, not part of the source theorem. Removing them leaves a valid native split-graph problem but removes the intended compact route.
- The 0/200,000 estimate uses the exact declared prior—all clique-first cyclic permutations with the obvious no-consecutive-independent constraint—but does not condition on each independent vertex’s three incident clique neighbors. It establishes guess resistance, not computational hardness.
- Blossom is extremely fast on a machine; this family claims only the no-tool compression gap, never complexity-theoretic hardness.
- The panel did not run a full SAT/ILP encoding, a commercial graph solver, or Renjith–Sadagopan’s complete path-splicing implementation. It did run exact blossom matching, the natural construction-oblivious solver for this cubic core.
- The shipping answer is close to the 256-atom and 500-token caps. `escalate()` therefore returns `"cap_bound"` after `n=94`; larger instances build and verify, but are not writable under the benchmark contract.
- Oracle evidence is presently blocked by external account state. This directory must not be submitted as hardened until the bare, structural, and placebo runs complete successfully.
