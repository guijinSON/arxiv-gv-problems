# arXiv 2510.04418 — succinct affine-carry HISTs

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate | exact symbolic HIST |
| Intended intuition | invariant: binary carries become nested masks along an affine orbit |
| Domain essentiality | licensed reduction |
| Reduction | Section 4, Theorem 4.1; paper-central pendant lift from an `s-t` Hamiltonian path to a HIST |

## Problem and trust model

The source is Hanaka, Kiya, and Ono, [*Finding a HIST: Chordality,
Structural Parameters, and Diameter*](https://arxiv.org/abs/2510.04418). A
homeomorphically irreducible spanning tree (HIST) is a spanning tree with no
degree-two vertex (Section 2.1). The solver receives an exact, succinct Cayley
graph on all `n`-bit strings plus a closed rule for pendant vertices. It must
return a bit-position permutation that symbolically specifies a Hamiltonian
path through the core; the path and every forced pendant edge are the HIST.

Generation is inverse. The module samples an affine order of the bit positions
first, inserts all of its binary-carry prefix masks, and fills each weight row
with shuffled decoys drawn from the same affine-interval distribution. It never
solves the completed instance. `verify` does not read `inst["answer"]`: it
checks the permutation, every carry-mask edge, the exact `2^n` core count, the
pendant and total edge counts, the two endpoint roles, the handshaking identity,
and the absence of degree two. Any permutation defining a valid tree is
accepted.

The representation is paper-licensed rather than fully native. The graph and
HIST are the paper's objects, and the pendant transformation is exactly the
one in Theorem 4.1; the bit-string Cayley compression and affine distribution
are this generator's notation.

## Why Track B

Step 0 rules out an honest Track-A claim. Theorem 2.1 handles diameter at most
2 in polynomial time; Corollary 3 handles chordal diameter at most 3;
Theorems 6.1–6.3 give FPT algorithms for modular-width, treewidth, and cluster
vertex deletion number. Theorem 5.1 gives a `4^N N^O(1)` exact algorithm.
Theorem 4.1 proves worst-case NP-completeness for strongly chordal graphs of
diameter 4, but that says nothing about this inverse-generated distribution.

An efficient algorithm is therefore disclosed. Exact subset-state dynamic
programming on the displayed prefix DAG takes `O(nL)` predecessor probes for
`L` masks. Across eight hard instances it used 226,993 probes total (mean
28,374.125) and 0.0709 seconds total (mean 0.00886 seconds), solving 8/8. The
paper's explicit-graph Algorithm 1 would instead see `N=2^32` vertices at hard
and is not materialized.

The compact route recognizes that binary increments create nested carry masks
and that one valid bit order is an affine orbit modulo the prime `n`. Orienting
the displayed weight-two masks and rejecting an orbit at its first absent
prefix took at most 718 counted operations on the eight adversary seeds and
802 on the twenty G9 size seeds. That fits the 1,000-operation cap, but is
painful bookkeeping without a tool. This mechanical-versus-compact gap is the
entire Track-B claim.

## Worked demo (`seed=0`)

The complete demo statement is:

```text
Find a homeomorphically irreducible spanning tree (HIST).

A HIST of a finite simple undirected graph is a spanning tree in which every
vertex has degree 1 or degree at least 3; degree 2 is forbidden.

The graph H below is specified exactly and succinctly.  It has 64 vertices.
Its 32 core vertices are C_x for integers x=0,...,31, viewed as 5-bit strings.
For every displayed nonzero mask m and every core label x, H contains the
undirected core edge {C_x,C_(x XOR m)}.

The displayed masks are grouped by Hamming weight:
  weight  1: 8 16
  weight  2: 18 10
  weight  3: 26 14
  weight  4: 30 29
  weight  5: 31

C_2 has two private pendant neighbours, C_29 has none, and every other core
vertex has one. Each pendant is adjacent only to its named core vertex.

Return a permutation sigma=[sigma_0,...,sigma_4] of bit positions 0,...,4.
P_sigma(i) moves bit j of i to bit sigma_j. The certificate denotes every
pendant edge and the ordered core path
  C_(2 XOR P_sigma(0)), ..., C_(2 XOR P_sigma(31)).
It is valid exactly when every consecutive pair is a displayed-mask core edge.

Give your final answer inside <answer></answer> tags as one JSON list of exactly
5 integers. Output nothing else inside the tags.
```

The answer is `[3, 1, 4, 2, 0]`.

```python
>>> verify(inst, [3, 1, 4, 2, 0])
(True, 'ok')
>>> verify(inst, [3, 3, 4, 2, 0])
(False, 'bit positions must be pairwise distinct')
```

A person can solve the demo on paper: it has only `5! = 120` shaped
candidates and three valid witnesses for this seed. (The preset-table seed
below is different and has one.)

## Difficulty presets

Representative measurements use `seed=20260908`; the named hard preset ships.

| Preset | `n` | Masks | Expanded vertices | Candidate space | Exact solutions | Reference probes | Compact ops | Ships? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| demo | 5 | 9 | 64 | 120 | 1 | 22 | 14 | no; hand example |
| easy | 13 | 145 | 16,384 | 6,227,020,800 | 4 | 877 | 122 | no; oracle solved 3/3 |
| medium | 23 | 687 | 16,777,216 | 25,852,016,738,884,976,640,000 | 4 | 7,754 | 438 | no; oracle solved 2/3 |
| **hard** | **31** | **1,855** | **4,294,967,296** | **31!** | **8** | **28,328** | **68** | **yes** |

Escalation first raises mask crowding at fixed answer length, then raises the
prime dimension. It does not rely only on making the answer longer.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses across four presets; JSON-native |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON through prose and a Markdown fence round-tripped |
| G4 | pass | 0/200,000 uniform permutations verified |
| G5 | pass | exact hard count `8 / 31! = 9.7290e-34`; 512-restart baseline failed after 1,079 prefix tests in 0.0474 s |
| G6 | pass | six attacks each 0/8; exact reference DP 8/8 |
| G7 | pass | doubled to next prime `n=67`; witness verifies; entropy 112.66→314.13 bits |
| G8 | pass | 100/100 invariance and 100/100 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 114 characters, 29 estimated tokens, 31 atoms, 802 intended-route operations |

The six failed attacks were bit-frequency outlier ranking, smallest-extension
greedy, largest-extension greedy, two-level lookahead, all unit-stride starts,
and 256 uniform restarts. Every mask—including the planted one—is an affine
interval of its displayed weight, so the intended pattern is not a
plant-versus-decoy type or magnitude outlier.

## Oracle loop

| Preset | Seed | Model | Result | Exact grader result |
|---|---:|---|---|---|
| easy | 1807830277 | Gemini 3.8 Flash | solved | `ok` |
| easy | 632277673 | GPT-5.6 Terra | solved | `ok` |
| easy | 66657689 | GPT-5.6 Terra | solved | `ok` |
| medium | 605094380 | Gemini 3.8 Flash | failed | reasoned but emitted no tagged answer |
| medium | 119989090 | GPT-5.6 Terra | solved | `ok` |
| medium | 1441020261 | GPT-5.6 Terra | solved | `ok` |
| **hard** | 2095763627 | GPT-5.6 Terra | failed | forbidden weight-2 carry mask 34 |
| **hard** | 252122918 | Gemini 3.8 Flash | failed | forbidden weight-2 carry mask 262148 |
| **hard** | 655678344 | GPT-5.6 Terra | failed | forbidden weight-2 carry mask 3 |

The script-owned verdict is `hardened` at hard. The medium unparsed reply ends
mid-analysis without a final answer, so it is not a `parse_answer` bug.

## G9 diagnostic

| Arm | Solved/attempts | Conclusion |
|---|---:|---|
| bare | 0/3 | shipping evidence holds |
| structural hint | 0/3 | no solved instance |
| placebo | 0/3 | no solved instance |

`hinted − placebo = 0`. The hint bought no measurable advantage in this
three-instance sample, so the diagnostic does not independently confirm the
claimed invariant even though the local affine decoder does. This is a finding,
not a gate. One hinted call exhausted its 32,000-token response budget, another
ended mid-analysis without an answer, and the third emitted an invalid
permutation; all three placebo calls emitted invalid permutations.

## Use

```python
import gen_2510_04418 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
candidate = g.parse_answer(
    "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2510.04418 20 hard
```

## Caveats

- The expanded hard graph has over four billion vertices. It is finite and the
  checker proves the represented tree by exact symbolic identities, but this
  benchmark measures reasoning over a succinct graph, not explicit graph I/O.
- This is not a distributional use of Theorem 4.1's strongly-chordal
  diameter-four hardness. No claim is made that these Cayley graphs are
  strongly chordal or have diameter four. The hardness claim is Track B only.
- `P(guess)` is uniform over every shape-valid bit permutation. It correctly
  incorporates length, range, and distinctness, but it is not an affine-aware
  prior; the affine scan, adversary panel, and oracle runs address that prior.
- The exact compressed subset-DP was run. A generic SAT/ILP encoding and the
  paper's explicit `4^N` DP were not run; both should be mechanical solutions,
  with the latter infeasible only because it ignores the succinct structure.
- `canonical_key` is invariant under bit-coordinate permutations, XOR
  translations, mask reordering, and their compositions. It uses strong
  incidence/coincidence histograms rather than solving full Cayley-graph
  isomorphism, so rare non-obvious isomorphic instances could receive different
  keys.
