# PAU-VC generator for arXiv:2312.10599

**Status:** locally complete and verified; **not yet shippable**. All local gates
G1--G9 pass, but the required OpenRouter hardening calls returned HTTP 403 before
any oracle produced a scored attempt. The harness-authored error transcripts are
retained; no model failure or hardened verdict is inferred from them.

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a native vertex set) |
| Intended intuition | constraint propagation through an all-zero cross-block and closed neighborhoods |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed pendant construction, Section 3, Lemmas 4--5 and Theorem 4 |

## Problem and trust model

This module implements Horiyama, Kobayashi, Ono, Seto, and Suzuki,
[*Theoretical Aspects of Generating Instances with Unique Solutions:
Pre-assignment Models for Unique Vertex Cover*](https://arxiv.org/abs/2312.10599).

The solver receives a bipartite core graph `G` and the paper's augmented graph
`G'`, formed by attaching one private leaf to every core vertex. It must return
a nonempty Exclude pre-assignment `X` of at most `k` core vertices for which
exactly one minimum vertex cover of `G'` avoids `X`. On this promised family,
that condition is equivalent to `X` being an independent dominating set of
`G`: it contains no core edge and every core vertex is in or adjacent to `X`.
The checker executes those local conditions and also validates the entire
private-leaf structure, so it never reads the planted answer or calls a solver.

Generation is inverse. A balanced independent dominating set `D` is sampled
first. Plant-to-decoy edges certify domination, decoy-to-decoy noise hides the
plant, all labels are uniformly permuted, and private leaves are attached.
Lemma 4 then constructs the unique compatible minimum cover as the core outside
`D` together with the private leaves of `D`. The answer is known before the
instance exists; generation never solves its own output.

## Why Track A

Section 3, Theorem 4 proves Exclude/Mixed PAU-VC NP-complete even for the exact
pendant-augmented bipartite regime used here. The easy side matters: Corollary 1
makes *verification* polynomial on bipartite graphs through minimum matching,
Section 4 gives an `O(1.9181^N)` exact search algorithm, and the paper gives an
`O*(3.6791^tau)` FPT algorithm. Small vertex-cover number `tau` is therefore an
easy generation regime to avoid. The shipping graph has `N=320` vertices and
`tau=160`; `k` grows no further after the demo.

Worst-case NP-completeness does not establish hardness of this distribution.
The distribution evidence is the local panel: the strongest exact
branch-and-propagate attack exhausted 1,000,000 nodes on every one of eight
shipping seeds (8,000,000 nodes and 217.45 wall-clock seconds in the throttled
run), while degree, greedy, randomized-greedy, and centered spectral attacks
were also 0/8. For the representative G5 seed the same exact search used
1,000,000 nodes and 43.96 seconds. The compact route, once the planted
zero-block is recognized, takes 170 exact neighborhood checks.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders the following full
hand-scale problem:

```text
PRE-ASSIGNMENT FOR A UNIQUE MINIMUM VERTEX COVER

The undirected simple graph below has vertices 0 through 15.
A vertex cover is a set C such that every edge has at least one endpoint in C.
A minimum vertex cover has the smallest possible cardinality.

An Exclude pre-assignment is a set X of vertices.  It is feasible when exactly
one minimum vertex cover C satisfies C intersection X = empty.

This graph has a distinguished core W.  Every core vertex w has one private
leaf w', joined only to w; the private pairs are listed below.  For this promised
form, a set X contained in W is a feasible Exclude pre-assignment exactly when X
is an independent dominating set of the core: no edge with both endpoints in W
has both endpoints in X, and every vertex of W is either in X or has a core
neighbor in X.

Find a nonempty feasible Exclude pre-assignment X contained in W with |X| at
most 2.  Vertex labels may not repeat.  Inside the answer tags list them
as decimal integers in strictly increasing order, separated only by commas.

CORE W (8 vertices)
0 3 5 6 7 10 12 13

PRIVATE PAIRS (core leaf)
0 4
3 9
5 15
6 14
7 1
10 11
12 2
13 8

EDGES (20 edges)
0 4
0 5
0 6
0 13
1 7
2 12
3 5
3 6
3 9
3 10
5 12
5 15
6 7
6 14
7 10
7 13
8 13
10 11
10 12
12 13

Give your final answer inside <answer></answer> tags, as a comma-separated list
of 1 through 2 strictly increasing core-vertex labels.
Example of syntax only (not claimed feasible): <answer>0</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>3,13</answer>`:

```python
>>> verify(inst, [3, 13])
(True, 'ok')
>>> verify(inst, [3])
(False, 'selected vertices do not dominate core vertex 0')
```

A person can solve the demo on paper. It has four accepted witnesses; the task
asks for any feasible pre-assignment, not specifically the planted one.

## Difficulty presets

`regularity=0` balances expected degrees, `1` exactly balances planted
incidences, and `2` additionally makes the noise graph biregular. Thus the
ladder grows the haystack and removes a degree signature without lengthening
the ten-label witness.

| Preset | Core `n` | Total vertices | `k` | Regularity | Example edges | Ships? |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 16 | 2 | 0 | 20 | no; hand example |
| easy | 160 | 320 | 10 | 0 | 1,363 | **provisional shipping preset** |
| medium | 210 | 420 | 10 | 1 | 2,324 | no |
| hard | 260 | 520 | 10 | 2 | 3,510 | no |

The edge counts are seed-0 examples. No preset was rejected by a local gate;
the oracle ladder could not begin because the shared key was exhausted.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset/seed checks, including JSON round-trip |
| G2 corruption | pass | 5/5 rejected with five distinct reasons |
| G3 parser round-trip | pass | realistic tagged prose recovered; garbage returned `None` |
| G4 guess resistance | pass | 0/200,000 structure-aware guesses; language size 2,434,053,505,276,148 |
| G5 density/baseline | pass | shipping density 0/200,000; exact attack hit 1,000,000 nodes in 43.96 s; demo count 4 |
| G6 adversaries | pass | five attacks all 0/8; exact search totaled 8,000,000 nodes / 217.45 s |
| G7 scaling | pass | doubled 320-core instance built and verified; answer stayed length 10 |
| G8 canonical key | pass | 80/80 relabellings/compositions invariant and valid; 20/20 unrelated keys distinct |
| G9 no-tool caps | pass | 40 chars, 10 atoms, about 10 tokens, 170 operations |

The G4 prior is uniform over every nonempty core subset of size at most `k`, so
it enforces the stated core-membership, distinctness, ordering, and size rules.
It is not a learned prior over graph structure and does not imply an upper bound
on a competent solver's success probability.

## Oracle loop and G9 diagnostics

No row below is a model failure. Errors do not consume attempts under
`harden.py`, so all arms remain 0 scored attempts and hinted-minus-placebo is
unavailable (the report's numeric placeholder is `0.0`).

| Arm | Scored solved/attempts | Harness rows | Models reached | Outcome |
|---|---:|---:|---|---|
| bare | 0/0 | 4 | Gemini 3.8 Flash | HTTP 403 key total limit exceeded |
| structural hint | 0/0 | 4 | Gemini 3.8 Flash | HTTP 403 key total limit exceeded |
| placebo hint | 0/0 | 4 | Terra (2), Gemini (2) | HTTP 403 key total limit exceeded |

Consequently there is no conclusion yet about whether the structural hint
helps. The size/effort portion of G9 is independently satisfied: 40 serialized
characters, 10 atomic elements, and 170 intended-route operations.

## Use

```python
from gen_2312_10599 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("Reasoning omitted. <answer>1,2,3</answer>")
print(verify(inst, candidate))
```

From the repository root, after a funded key has produced a `hardened` verdict
and the G9 arms have been rerun:

```bash
bash scripts/emit.sh 2312.10599
```

## Caveats

- Theorem 4 is worst-case evidence, not an average-case theorem for this planted
  distribution. A stronger biclustering, SAT, CP-SAT, or MILP attack may break it.
- No industrial solver is permitted by the module's standard-library contract.
  The panel includes an exact exponential brancher and a centered spectral
  attack, but no LP/SDP relaxation.
- The provisional shipping rung uses expected degree balance (`regularity=0`),
  not the exact biregularity of the harder rungs. Degree probes failed 0/8, but
  higher-order construction leakage may remain.
- The generator guarantees a known witness, not a unique pre-assignment. The
  checker intentionally accepts every valid witness.
- The Weisfeiler--Lehman canonical key is a strong cheap invariant for these
  random marked cores, not a complete graph-isomorphism canonical form.
- Most importantly, STEP 4 is incomplete for an external reason. Do not submit
  this result until the bare run records three scored attempts and a hardened
  verdict, then rerun both G9 diagnostic arms with the same funded key.
