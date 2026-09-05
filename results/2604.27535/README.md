# arXiv 2604.27535 — rainbow injection for a prescribed cycle

Status: all local gates pass, but this result is **not externally hardened and
must not be submitted as a hard family yet**. Every tested rung through an
80-edge answer was solved by at least one no-tool oracle. OpenRouter then
exhausted the key's total quota before the remaining escalation and G9 calls,
so the script produced no final hardness verdict. The partial, script-owned
evidence is retained verbatim.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover (bipartite matching) |
| Certificate | integer tuple: an edge-to-graph injection |
| Native objects | a family of simple graphs, a specified cycle, and its rainbow injection |
| Intuition | symmetry: align cyclic shifts of one marked binary word |
| Domain essentiality | native; no reduction |

## Problem and trust model

The solver receives a family of `n` graphs on one `n`-vertex set and a specified
cycle of length `k=n/2`. It must assign a different family member to every cycle
edge so that the edge occurs in its assigned graph. This is exactly the rainbow
subgraph witness defined in Section 1 of Li, Wang, and Yan,
[*Pancyclicity in Graph Families with the Ore-Type Condition*](https://arxiv.org/abs/2604.27535).
Checking a candidate is just distinctness plus `k` exact table lookups.

The answer is sampled first. A binary necklace with one longest run is shifted
by a permutation of the edge positions; each edge is assigned the graph at its
marker origin. Graph and vertex labels are then shuffled. The generator never
solves the finished instance. Every graph contains every edge incident with a
filler vertex. A cycle vertex therefore has degree at least `n/2` in every
family member, while a filler vertex has degree `n-1`. Consequently every
missing pair has degree sum at least `n` for every pair of graph indices, which
is precisely the paper's family Ore condition.

## Why Track B

Theorem 1.6 proves `[4,n]` rainbow vertex-pancyclicity under this Ore condition,
apart from the family consisting of identical `K_(n/2,n/2)` graphs. It is an
existence theorem, not a distributional hardness theorem, so this module makes
no Track-A claim. Its proof starts from the earlier rainbow Hamilton-cycle
theorem and performs cycle switches; it does not give a short formula for an
arbitrary edge-to-graph injection.

An efficient algorithm is disclosed: scan the `k × k` availability matrix and
run Hopcroft–Karp in `O(k² + E sqrt(2k))`. At the provisional hard preset
`k=64`, it solved 8/8 instances, averaging 6,709.875 counted bit/edge operations
and 0.00027 seconds. Once the symmetry is recognized, the longest cyclic 1-run
locates the same marker in each row; selecting those 64 columns uses 70 exact
index operations. A literal decoder still inspects up to 9,216 bits, which is
an important limitation discussed below.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders:

```text
Rainbow injection for a prescribed cycle

There are 8 simple undirected graphs G_0,...,G_7 on V={0,...,7}.
The prescribed cycle, in cyclic order, is [4, 1, 5, 2].
Every pair with at least one endpoint outside that cycle is an edge of every
graph. Among cycle vertices, only the four cycle edges may occur.

Binary-table column positions name these graph indices:
[1, 0, 4, 5]

  edge 0 = {4,1}: 0110
  edge 1 = {1,5}: 0011
  edge 2 = {5,2}: 1001
  edge 3 = {2,4}: 1100

Return one distinct graph index per edge as a JSON list inside
<answer></answer> tags.
```

The planted answer is `[0, 4, 5, 1]`.

```python
>>> verify(inst, [0, 4, 5, 1])
(True, 'ok')
>>> verify(inst, [0, 0, 5, 1])
(False, 'graph indices must be pairwise distinct')
```

A person can solve the demo on paper: it has only `4! = 24` structurally valid
candidates and exactly two witnesses.

## Difficulty presets

| Preset | Vertices/graphs `n` | Cycle edges `k` | Marker length | Answer atoms | Oracle result |
|---|---:|---:|---:|---:|---|
| demo | 8 | 4 | 2 | 4 | hand-scale; hardener skips it |
| easy | 64 | 32 | 6 | 32 | defeated, 3/3 solved |
| medium | 96 | 48 | 5 | 48 | defeated, 2/3 solved |
| hard | 128 | 64 | 4 | 64 | defeated, 1/3 solved |

`SHIPPING_DIFFICULTY` names `hard` only as the provisional local-gate preset;
there is no externally validated shipping level. The automatic ladder also
tested marker length 3 at `n=128` (2/3 solved) and `n=160` (1/2 completed
attempts solved) before quota failure. Escalation first shortens the marker at
fixed answer length, then grows the cycle up to the operation/answer cap.

## Gate results

| Gate | Result | Measurement at provisional hard unless noted |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced tagged JSON with surrounding prose round-trips |
| G4 | pass | 0/200,000 uniform permutations of the relevant graphs |
| G5 | pass | shipping density 0/200,000; demo exact count 2/24; reference mean 6,709.875 operations |
| G6 | pass | five attacks each 0/8; Hopcroft–Karp 8/8 as expected |
| G7 | pass | doubled `n=256`, `k=128` builds and verifies; search entropy 296 to 717 bits |
| G8 | pass | 100/100 symmetry and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 270 characters, 68 estimated tokens, 64 atoms, 70 exact operations |

The failed attacks were row/column-frequency ranking, smallest-ID greedy,
largest-ID greedy, 512 random permutations per instance, and every direct or
reversed constant-shift ansatz. The successful standard matching algorithm is
under `reference_algorithm`, outside `attacks`, as Track B requires.

## Oracle loop

| Rung | Parameters | Valid solved/attempts | Outcome |
|---|---|---:|---|
| easy | `n=64, marker=6` | 3/3 | defeated |
| medium | `n=96, marker=5` | 2/3 | defeated |
| hard | `n=128, marker=4` | 1/3 | defeated |
| escalated | `n=128, marker=3` | 2/3 | defeated |
| escalated | `n=160, marker=3` | 1/2 | defeated before third attempt; four redraws then returned HTTP 403 |

The transcript has 14 valid oracle attempts and four quota-error redraws. An
error is not counted as a model failure. Because the runner stopped as
unreachable, `.meta.json` intentionally has no `harden_verdict`.

## G9 arms

| Arm | Solved/valid attempts | Errors | Conclusion |
|---|---:|---:|---|
| bare at provisional hard | 1/3 | 0 | the level is not hardened |
| structural hint | 0/0 | 4 | unavailable: HTTP 403 total-limit error |
| placebo | 0/0 | 4 | unavailable: HTTP 403 total-limit error |

`hinted − placebo` is undefined, so no claim about hint efficacy is made. The
answer and route caps pass independently: 270 characters, 64 atomic elements,
and 70 exact index operations.

## Use

```python
from gen_2604_27535 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, after a future successful hardening run:

```bash
bash scripts/emit.sh 2604.27535 20
```

## Caveats

- This is not currently shippable: every completed rung was solved by at least
  one oracle, and the required final verdict and hinted/placebo diagnostics are
  missing because the OpenRouter total quota was exhausted.
- The binary rotation is especially legible to Gemini in the recorded runs.
  Merely lengthening the answer until transcription fails would not establish
  insight-based hardness.
- `P(guess)=0/200,000` samples uniform permutations of the graph indices that
  actually occur in the table; it correctly excludes obviously irrelevant
  graphs, but it says nothing about rotation-aware guesses.
- A literal marker decoder scans 9,216 bits even though only 70 exact index
  operations remain after recognizing the visual symmetry. This gap makes the
  task partly one of visual bookkeeping, not purely arithmetic insight.
- Hopcroft–Karp is the domain-standard exact attack and was tested. General
  ILP/SAT encodings and tool-assisted visual pattern discovery were not tried;
  they should also solve these matching instances.
- `canonical_key` fully quotients vertex labels, graph labels, display-column
  order, and cycle dihedral symmetry. It does not attempt isomorphisms that
  change which cycle is designated by the instance.
