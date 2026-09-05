# arXiv 2604.24325 — identification to a given linear forest

Status: the generator and every local gate pass. The required four-vendor oracle
verdict is **not available**: all bare, structural-hint, and placebo calls were
rejected by OpenRouter with HTTP 403 `Key limit exceeded (total limit)`. Those
script-owned error records are retained and are not counted as model failures.
Do not submit this result as hardened until the runs are repeated with a usable key.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer tuple: a canonical partition into four-path groups |
| Native objects | source and target linear forests represented by exact component edge-counts |
| Intuition | change of variables: invert a mixed-radix linear invariant |
| Domain essentiality | licensed reduction |
| Reduction | Section 3.1, Theorem 2 and Section 3.3, Claim 6 |

## Problem and trust model

The solver receives a source linear forest with 4t path components and a target
linear forest with t identical path components. It must partition the source
component indices into t groups of four. A group is a concrete identification
witness: orient its paths and identify consecutive endpoints, using three
identifications to form one path. Its edge-count is exactly the sum of the four
source edge-counts.

The generator samples three hidden permutations first, constructs one quartet
per target through an invertible mixed-radix identity, and only then shuffles the
source components. It never solves a completed instance. Tag magnitudes force
every valid quartet to use one component from each of four bands; the radix and
an invertible integer matrix force the hidden ranks. The unordered partition is
therefore unique. `verify` checks shape, exact coverage, canonical order, and
integer sums without reading `inst["answer"]`.

This is the component-partition formulation used centrally in [Golovach,
Morelle, and Paulusma, *Identification to Subclasses of Chordal
Graphs*](https://arxiv.org/abs/2604.24325). It is marked `paper_licensed`, rather
than pretending that the prompt expands paths containing billions of vertices.

## Why Track B

Corollary 1 puts identification to the *class* of paths or linear forests in
polynomial time. In contrast, Theorem 2 proves that identification to an
explicitly supplied linear forest is W[1]-hard in the number of target
components, and Lemma 6 gives an O(NM + N^(t+1)) XP dynamic program. That
worst-case result does not establish average hardness for this planted
distribution, so this is not a Track-A claim.

An efficient distribution-specific method exists and is disclosed. The
reference algorithm enumerates source-path pair sums, joins complementary pairs
(4SUM), and propagates the resulting unique exact cover. At hard with 128 source
paths it solved 8/8 instances, averaging 15,078.75 counted operations and about
0.005 seconds. That is easy for a tool but not executable by hand in context.
After noticing the invariant, the compact decoder sorts the bands, reads their
progression steps, and inverts the digits in 294 exact arithmetic operations; it
verified on 20/20 audit instances.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders this complete instance:

```text
Identification to a given linear forest

A path P_L has L edges (and therefore L+1 vertices).  The source graph G is the
disjoint union of 8 paths.  Source component i is P_L for the L on
line i below; indices are 0-based.

The target graph H is the disjoint union of 2 indistinguishable copies of
P_728520.

One vertex identification replaces two vertices by one vertex adjacent to the
union of their former neighbours.  Your certificate must partition all source
components into 2 groups of exactly four.  A group [i0,i1,i2,i3] means: orient
those four paths by their natural vertex order and identify the right endpoint
of path i0 with the left endpoint of i1, then i1 with i2, then i2 with i3.  This
uses three identifications and makes one path whose edge-count is the sum of the
four displayed lengths.  Across all groups the certificate uses 6
identifications and must produce H.

It is guaranteed that there is a unique unordered partition satisfying these
requirements.  No component may repeat or be omitted.  Within each group list
the four indices in strictly increasing order, and sort the list of groups
lexicographically.  Thus order carries no mathematical meaning but the output
has one canonical spelling.

Source path edge-counts:
  0: 184037
  1: 183946
  2: 211186
  3: 211358
  4: 143822
  5: 189394
  6: 189494
  7: 143803

Required edge-count of every target path: 728520

Return JSON: an outer list of exactly 2 inner lists, each containing four
integers.  Example of syntax only for a hypothetical two-target instance:
<answer>[[0, 2, 5, 7], [1, 3, 4, 6]]</answer>

Give your final answer inside <answer></answer> tags in exactly that JSON format.
Output nothing else inside the tags.
```

The answer is `[[0, 2, 6, 7], [1, 3, 4, 5]]`.

```python
>>> verify(inst, [[0, 2, 6, 7], [1, 3, 4, 5]])
(True, 'ok')
>>> verify(inst, [[2, 0, 6, 7], [1, 3, 4, 5]])
(False, 'indices inside every group must be strictly increasing')
```

A person can solve the eight-component demo on paper: there are only 35
canonical four/four partitions, and exact enumeration finds one solution.

## Difficulty presets

| Preset | Target paths `n` | Source paths | Tag base | Separation | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 8 | 4 | 5 | 8 | hand-scale; skipped by hardener |
| easy | 8 | 32 | 8 | 15 | 32 | bare oracle halted on API errors here |
| medium | 16 | 64 | 7 | 12 | 64 | not reached |
| hard | 32 | 128 | 6 | 10 | 128 | provisional shipping preset |

`SHIPPING_DIFFICULTY = "hard"` is provisional because the external hardening
loop could not produce a verdict. Escalation first crowds the bands at fixed
answer length by reducing `separation` and `tag_base`. It stops rather than
claiming `cap_bound` when the 300-operation limit leaves no honest larger `n`.

## Gate results

| Gate | Result | Measurement at hard unless noted |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; all presets × 3 seeds; JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced JSON with surrounding prose round-trips |
| G4 | pass | 0/200,000 valid uniform structure-aware equipartitions |
| G5 | pass | hard density 0/200,000; demo exact count 1/35; reference mean 15,078.75 operations |
| G6 | pass | four attacks each 0/8; reference 4SUM solver 8/8 as expected |
| G7 | pass | doubled n=64 builds and verifies; space bit length 452 to 1,095 |
| G8 | pass | 60/60 symmetry checks and carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 594 characters, 149 estimated tokens, 128 atoms, 294 operations |

The failed attacks are magnitude-band rank matching, first-fit decreasing, 512
uniform restarts per instance, and a nearest-completion by-hand heuristic. The
strongest performed 4,096 restarts across eight seeds. The successful standard
algorithm is under `reference_algorithm`, not `attacks`, as Track B requires.

## Oracle loop and G9 arms

The bare loop obtained no valid attempt and no shipping decision. These are API
errors, not failed solvers:

| Preset | Model | Seed | Solved | Why |
|---|---|---:|---|---|
| easy | google/gemini-3.1-pro-preview | 663959613 | error | HTTP 403 key total limit |
| easy | google/gemini-3.1-pro-preview | 276994328 | error | HTTP 403 key total limit |
| easy | google/gemini-3.1-pro-preview | 14243765 | error | HTTP 403 key total limit |
| easy | anthropic/claude-sonnet-5 | 900543112 | error | HTTP 403 key total limit |

| G9 arm | Valid solved/attempts | Error records | Conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | unavailable; bare ladder stopped at easy |
| structural hint | 0/0 | 4 | unavailable |
| placebo | 0/0 | 4 | unavailable |

`hinted − placebo` is undefined, so no claim about hint efficacy is made. The
structural hint names only the invariant; it does not give decoding steps. G9’s
size/effort portion is independent of the API and passes.

## Use

```python
from gen_2604_24325 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2604.24325 20
```

After restoring OpenRouter quota, rerun the bare hardener here and the hint modes
in separate scratch directories; `harden.py` overwrites transcripts on each run.

## Caveats

- The compact decoder and 4SUM solver make instances easy with a tool. That gap
  is the declared Track-B task, not a hidden complexity claim.
- `P(guess)=0/200,000` uses the stated prior: uniform canonical partitions into
  four-element groups. It says nothing about arithmetic-aware guesses.
- Component lengths are a lossless, paper-licensed representation of disjoint
  paths, but the module does not materialize their many individual vertices.
- The four heuristics and exact reference solver were tested. A general ILP/SMT
  solver and broad automated invariant discovery were not; either could solve it.
- `canonical_key` quotients source relabelling, positive scaling, global
  translation, and compositions. It may still collapse a non-equivalent instance
  with the same normalized length multiset, though unlikely here.
- Most importantly, four-vendor no-tool evidence is missing because of the HTTP
  403 quota failure. Local gates alone do not justify shipping.
