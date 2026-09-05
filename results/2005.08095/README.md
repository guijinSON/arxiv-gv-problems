# General d-position sets — verified generator for arXiv:2005.08095

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (graph vertices) |
| Intended intuition | invariant: multiplicative slopes and twisted additive intercepts |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 2, Proposition 2.1 and Theorem 2.2 |

## What the family is

The source is Klavžar, Rall, and Yero, [“General d-position sets”](https://arxiv.org/abs/2005.08095). A vertex set is in general `d`-position when no three selected vertices occur on a shortest path of length at most `d`.

The solver receives the paper's graph `G'` in an exact compact representation. Its payload graph `G` has `k` colour classes over the prime field `F_p`; every colour-pair relation is a union of three affine perfect matchings. The paper's graph `H_t` is joined to `G` exactly as in Theorem 2.2. The answer contains one payload vertex per colour. The checker expands it by the fixed clique `A ∪ B`. The expanded set is in general `d`-position precisely when the submitted payload vertices form a clique: a missing payload edge puts any selected `A` vertex on a length-two geodesic, whereas the expanded set is itself a clique when every payload pair is adjacent. Verification is therefore an exact size/range check followed by modular adjacency tests.

Generation is inverse: it samples three global field roots, hidden coordinate gauges, and translations before constructing the pair relations. Each ordinary relation contains the planted affine branch, and the exceptional relation contains the three sampled roots. The generator checks only that its public cocycle branch is unambiguous; it never searches the finished instance for an answer. This guarantees at least three witnesses. It does not assert that accidental additional cliques are impossible.

## Why this is Track B

Theorem 2.2 proves NP-completeness for every `d ≥ 2` through `gp_d(G') = gp_d(H_t) + omega(G)`. This module makes no average-case Track A claim from that worst-case result.

A complete reference method exists: lexicographic multicoloured-clique CSP backtracking. Its worst-case cost is `O(p k² r^(k-1))`; for the fixed shipping values `k=20`, `r=3`, its measured cost over eight seeds was 140,973.125 scanned field values, 7,190,380.125 counted exact operations, and 0.99 seconds on average. It solved 8/8, as Track B requires.

The distribution-specific efficient algorithm is the intended compression. Ordinary pair slopes satisfy a multiplicative cocycle, and rescaled intercept sets contain a twisted additive cocycle. Those invariants expose the exceptional relation and reduce the search to one affine equation. The implementation costs `O(k²r² + k log p)` and at most 274 counted exact operations over the audit seeds. A no-tool solver must first discover both invariants among 190 displayed relations; the bare pool failed 3/3 at the shipping preset.

The easy regimes in the paper were deliberately avoided. Propositions 3.1 and 3.3 give direct formulas for paths and cycles. Proposition 5.3 identifies general 2-position with dissociation sets on triangle-free graphs, and Section 6 notes polynomial algorithms for the relevant tree cases. The displayed `H_t` construction alone is also explicit; it is used only as the paper-licensed anchor around the hard payload.

## Worked demo

The complete `demo`, at seed 0, is hand-solvable by checking six small modular relations:

```text
Find a prescribed-size general d-position set in a compactly specified graph.

Definitions.
For vertices x,y, dist(x,y) is the minimum number of edges on an x-y path.
A geodesic is a path whose length equals that distance. A set S is in
general d-position when no three distinct vertices of S occur on one
geodesic of length at most d.

Let p=17, a prime. Arithmetic below is modulo p, with residues 0,...,16.
The graph G has k=4 colour classes C1,...,C4. Class Ci (with i
1-based) contains the p integer vertex labels (i-1)*p through i*p-1.
The residue coordinate of a label in Ci is label-(i-1)*p.
There are no edges inside a colour class.

For each line PAIR Ci Cj: a ; b1,b2,b3, where i<j, a vertex with
residue x in Ci is adjacent to a vertex with residue y in Cj exactly when
y = a*x+b modulo p for at least one listed b. All three b values are
included, and there are no other G-edges.

Pair relations:
  PAIR C1 C2: 7 ; 16,14,12
  PAIR C1 C3: 3 ; 6,2,11
  PAIR C1 C4: 15 ; 16,14,7
  PAIR C2 C3: 16 ; 8,10,12
  PAIR C2 C4: 7 ; 13,9,15
  PAIR C3 C4: 10 ; 13,3,10

The full graph G' is the following Section 2 construction.
1. Make H_t for t=68. Its sets A={a1,...,a136} and
   B={b1,...,b136} together induce a complete graph K_272.
2. Add the path v1-v2-...-v67, and join every B vertex to v1.
3. For i=2,...,67, add u_i adjacent to v_i and v_(i-1).
   These are all H_t edges.
4. Join every G vertex to every vertex of A, every vertex of B, and v1.
   Add no other cross edges.
Thus G' has 473 vertices, and d=t=68.

Submit exactly one G-vertex label from each C_i, in C1,...,C4 order.
The checker expands the answer to S=A union B union those 4 vertices.
The required expanded size is exactly 276. Do not list
the A or B vertices. Order is significant; bounds are inclusive.

Output exactly 4 distinct decimal labels as a JSON list.
Give your final answer inside <answer></answer> tags, as that JSON list.
Example syntax only: <answer>[0,17,34,51]</answer>
Output nothing else inside the tags.
```

The answer `[16, 22, 37, 67]` gives `(True, "ok")`. Replacing its first label by zero gives `(False, "labels 0 and 22 are incompatible for colours 1 and 2")`.

## Difficulty presets

| Preset | Prime `p` | Colours | `t=k*p` | Vertices in `G'` | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 17 | 4 | 68 | 473 | 4 | hand example |
| easy | 200,003 | 20 | 4,000,060 | 28,000,417 | 20 | rejected: bare oracle solved 1/3 |
| **medium** | **500,009** | **20** | **10,000,180** | **70,001,257** | **20** | **ships: bare oracle failed 3/3** |
| hard | 1,000,003 | 20 | 20,000,060 | 140,000,417 | 20 | reserved escalation |

`escalate()` doubles the field size while keeping the answer at 20 vertices.

## Gate results

| Gate | Result | Measurement at shipping preset |
|---|---|---|
| G1 | pass | 4 presets × 3 seeds; all 12 planted answers verified and JSON-round-tripped |
| G2 | pass | 6 corruptions rejected with 6 distinct reasons |
| G3 | pass | fenced JSON surrounded by prose round-tripped |
| G4 | pass | 0 hits / 200,000 structure-aware guesses; language size `500009^20` |
| G5 | pass | 0/200,000 sampled density; at least 3 constructed witnesses; reference mean 7,190,380.125 operations and 0.99 s |
| G6 | pass | 4 in-context attacks × 8 seeds, all 0 successes; reference and compact algorithms both 8/8 |
| G7 | pass | field increased to prime 1,000,033; witness stayed 20 atoms and verified |
| G8 | pass | 80 invariant-key checks, 80 carried-witness checks, and 20/20 unrelated keys distinct |
| G9(c) | pass | 159 chars, 40 estimated tokens, 20 atoms, 274 intended-route operations |

## Bare oracle loop

| Preset | Model | Seed | Solved | Result |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 1664920762 | yes | valid witness; escalated |
| easy | Google Gemini 3.8 Flash | 563476580 | no | parsed pair incompatibility |
| easy | OpenAI GPT-5.6 Terra | 518114262 | no | parsed pair incompatibility |
| medium | Google Gemini 3.8 Flash | 1554455340 | no | parsed pair incompatibility |
| medium | OpenAI GPT-5.6 Terra | 766649054 | no | parsed pair incompatibility |
| medium | Google Gemini 3.8 Flash | 434892975 | no | parsed pair incompatibility |

The harness verdict is `hardened` at `medium` after one escalation.

## G9 diagnostic arms

| Arm at medium | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted − placebo = 0.0`, so this small sample shows no measurable help from merely naming the invariants. One hinted attempt exhausted its 32,000-token completion budget, and another ended without a tagged answer; neither reply visibly contained a complete witness. The writable answer is 159 characters / 20 atoms (about 40 tokens), and the intended route uses 274 exact operations.

## How to use it

The module is standard-library-only; it does not need `gvlib`.

```python
import gen_2005_08095 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2005.08095 20 medium
```

## Caveats

- Track B openly concedes algorithmic solvability. The benchmark measures discovery and execution of a 274-operation compression against a 7.19-million-operation complete scan, not complexity-theoretic average-case hardness.
- `P(guess)=0/200,000` samples uniformly from assignments containing exactly one listed vertex per colour. It is an upper-resolution empirical density measurement, not proof that only the three constructed answers exist and not evidence against a new structure-aware algorithm.
- The failed attacks are equal-degree selection, zero-first greedy propagation, 64 random restarts, and a common-coordinate ansatz. No SAT/SMT, ILP, or computer-algebra package was tested; the complete CSP scan is the standard successful baseline for this representation.
- The compact `H_t` recipe stands for a graph with 70,001,257 vertices at shipping size. This is faithful to the paper's construction and keeps the solver's actual payload finite and exact, but a checker materializing every edge would be impractical.
- `canonical_key` is invariant under colour permutations, independent affine coordinate changes, relation/intercept reordering, and their composition. It is the strongest cheap invariant used here, not a complete graph-isomorphism canonical form.
- The affine-cocycle payload is a deliberately structured distribution inside the paper's central reduction. The result should not be read as a claim about random or arbitrary General `d`-Position instances.
