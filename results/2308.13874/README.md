# Verified generator for arXiv:2308.13874

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (a permutation encoding a 1-factor) |
| Intended intuition | invariant: modular neighborhood sums are affine |
| Domain essentiality | native |
| Reduction | none |
| Shipping preset | **hard** (`n=251`, `d=17`) |

## Problem and trust model

Ao, Liu, Yuan, Ng, and Cheng's [*Sufficient conditions for k-factors and
spanning trees of graphs*](https://arxiv.org/abs/2308.13874) defines a
`k`-factor as a `k`-regular spanning subgraph in Section 1; a 1-factor is a
perfect matching. An instance here is an explicit `d`-regular bipartite graph
with left and right vertices labelled `0,...,n-1`. The solver returns a
permutation `pi`, where edge `{L_x,R_pi[x]}` is the matching edge incident with
`L_x`.

Verification is exact and cheap: check length, integer bounds, that `pi` is a
permutation, and that each claimed pair occurs in the supplied adjacency list.
It accepts every perfect matching, not just the planted one. Generation first
samples a unit `a` modulo `n` and `d` offsets `B`, builds the graph as the union
of the affine matchings `x -> a*x+b`, and retains a uniformly chosen one. It
never solves the graph it just built, and every planted/decoy affine matching
comes from the same distribution. Generation does not run or condition on any
of the attacks used by `selftest()`.

## Why Track B

Track A would be false. A bipartite 1-factor is found in polynomial time by
Hopcroft--Karp, and the reference implementation succeeds on 8/8 hard
instances. Its measured maximum was 10,765 edge-inspection/queue operations
and 0.0009 seconds; its standard complexity is `O(E sqrt(V))`. This is the
algorithm that produces a certificate mechanically.

The compact route notices that every neighborhood has the form
`N(x)=a*x+B (mod n)`. Therefore
`sum(N(1))-sum(N(0)) = d*a (mod n)`. Since `d` is invertible modulo `n`, two
neighborhood sums recover `a`; any entry of `N(0)` supplies `b`, and repeated
addition of `a` writes a complete matching. The hard rung costs 297 counted
exact operations, versus 10,765 for the mechanical route. The paper's easy
existence regimes are also explicit: Theorem 1.2 and Corollary 1.1 use clique
or edge thresholds, while Lemma 2.4 handles minimum degree at least half the
order. This sparse bipartite construction deliberately does not pretend those
sufficient conditions confer distributional hardness.

## Worked demo

The smallest setting is genuinely hand-solvable. With seed 0 it renders:

```text
ONE-FACTOR OF AN EXPLICIT BIPARTITE GRAPH

The graph is simple and bipartite. Its left vertices are L_0,...,L_4
and its right vertices are R_0,...,R_4. There are no edges within
one side. For each left vertex x, the line below lists exactly all
2 right-vertex labels y for which {L_x,R_y} is an edge.
The order of neighbors on a line carries no meaning.

A 1-factor (perfect matching) is a set of edges in which every vertex
of the graph occurs exactly once. Find any 1-factor.

Adjacency lists (all labels and row indices are 0-based):
0: 3 0
1: 1 3
2: 4 1
3: 2 4
4: 0 2

Encode the matching as a JSON list pi of exactly 5 integers:
pi[x]=y means that L_x is paired with R_y. List order therefore
matters. Every entry must lie in 0,...,4; every right label
must occur exactly once; repetitions are forbidden.
Give your final answer inside <answer></answer> tags.
Example syntax for a four-vertex side: <answer>[2,0,3,1]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[0,3,1,4,2]</answer>`.
`verify(inst, [0,3,1,4,2])` returns `(True, "ok")`; dropping the last
entry returns `(False, "answer must have exactly 5 entries")`. A person can
also find either of the demo's two matchings by following the degree-two cycle.

## Difficulty presets

| preset | vertices per side `n` | degree `d` | status |
|---|---:|---:|---|
| demo | 5 | 2 | hand-solvable; exactly 2 answers among 120 permutations |
| easy | 181 | 11 | defeated by the bare oracle pool (1/3 solved) |
| medium | 223 | 13 | defeated by the bare oracle pool (1/3 solved) |
| hard | 251 | 17 | **ships; bare oracle pool 0/3 solved** |

After `hard`, escalation first raises `d` to 19 at fixed answer length. Further
growth is `cap_bound`: increasing `n` exceeds the 256-atom output cap, while
more adjacency clutter pushes the conservative compact route over 300 exact
operations.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified; answers JSON-round-tripped |
| G2 | empty, dropped, out-of-range, duplicate, and swapped corruptions rejected with five distinct reasons |
| G3 | realistic prose/fenced output round-tripped; malformed output returned `None` |
| G4 | 0/200,000 uniform permutations; exact elementary density upper bound `d^n/n!`, log10 below -180 |
| G5 | shipping density sample 0/200,000; demo exact count 2/120; reference maximum 10,765 operations and 0.0009 s |
| G6 | equal-degree outlier, displayed greedy, 256 randomized greedy restarts, and unit-slope ansatz: each 0/8; Hopcroft--Karp 8/8 |
| G7 | doubled `n=502` instance built and its plant verified |
| G8 | 80/80 relabelling invariance checks, 80/80 carried-witness checks, 20/20 unrelated keys distinct |
| G9(c) | 895 compact JSON characters, 224 estimated tokens, 251 atoms, 297 intended operations |

## Oracle loop and G9 arms

The mandatory bare harness escalated through the named ladder and selected
`hard`: both lower rungs were defeated, while all three hard attempts failed.
The current repository harness used its configured two-vendor pool (OpenAI and
Google), repeating a vendor with a fresh instance seed when necessary.

| preset | seed | model | result | reason |
|---|---:|---|---|---|
| easy | 879111117 | openai/gpt-5.6-terra | failed | repeated right endpoint |
| easy | 1037684497 | google/gemini-3.8-flash | solved | verified matching |
| easy | 401400301 | openai/gpt-5.6-terra | failed | repeated right endpoint |
| medium | 817703370 | google/gemini-3.8-flash | solved | verified matching |
| medium | 2038776596 | openai/gpt-5.6-terra | failed | wrong answer length |
| medium | 90797259 | openai/gpt-5.6-terra | failed | claimed a non-edge |
| hard | 1388341159 | google/gemini-3.8-flash | failed | no parseable tagged answer |
| hard | 870733459 | openai/gpt-5.6-terra | failed | claimed a non-edge |
| hard | 1037885351 | google/gemini-3.8-flash | failed | wrong answer length |

The matched-pool G9 diagnostic was run separately at the shipping preset:

| arm | solved / attempts at hard | follow-up | interpretation |
|---|---:|---|---|
| bare | 0/3 | main verdict `hardened` | shipping prompt held |
| structural | 3/3 | `d=19` also 3/3; final `cap_bound` | naming the invariant exposes the compact route |
| placebo | 1/3 | `d=19` was 0/3 and held | prompt variation alone sometimes helped, but much less |

The structural-information estimate is `1 - 1/3 = 0.667` solved-rate points.
Thus the claimed invariant is materially useful, although the placebo success
shows that this diagnostic is noisy and that some unhinted instances are still
solvable. The shipping answer is 895 characters, about 224 tokens and 251
atoms; the intended route uses 297 counted exact operations.

## Use

```python
from gen_2308_13874 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2308.13874 20
```

The module is deterministic, standard-library-only, and performs no I/O or
network access.

## Caveats

- This is not a computational-hardness claim. An ordinary computer solves the
  shipping instance in under a millisecond; Track B measures whether
  a no-tool solver finds and executes the compact invariant.
- This family uses the paper's native definition of a 1-factor, but not the
  hypotheses of Theorem 1.2 or its spectral/tree theorems. It should not be read
  as an empirical benchmark of those sufficient conditions.
- The hard answer uses 251 of the 256 allowed atoms and 297 of the 300 allowed
  operations. Although formally within bounds, failures may reflect arithmetic
  or transcription reliability as much as discovery.
- The bare run used the current script's two-vendor pool, not the four-vendor
  pool described in older task text. Also, one of three placebo attempts solved
  hard, so the `hardened` verdict should be understood as one seeded pool run,
  not a distributional impossibility claim.
- The 0/200,000 result samples uniformly from all permutations, enforcing every
  trivial shape/range/all-different constraint. It says little about an informed
  solver prior. The exact `d^n/n!` upper bound does establish sparse validity
  under that declared uniform language.
- Hopcroft--Karp and the four declared attacks were run without generator-side
  conditioning; an extra audit also found 0 successes for each attack over 100
  independently generated hard instances. Blossom, SAT/ILP encodings, spectral
  probes, and language-model code execution were not tried. Spectral methods
  are not the domain-standard algorithm for bipartite matching, but could still
  reveal the affine union.
- The canonical key is a strong exact invariant, not a complete graph
  isomorphism canonical form. It is invariant under arbitrary independent side
  relabellings, side swaps, adjacency-order changes, and compositions, but two
  nonisomorphic graphs could theoretically collide.
