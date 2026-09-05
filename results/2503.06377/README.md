# Affine equiangular 12-sets in the `X_5` lattice slice

| Profile | Value |
|---|---|
| Track | **B** — efficient coded searches exist and are reported |
| Native domain | geometry |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate | 12-by-10 signed coordinate matrix |
| Intended intuition | symmetry: recognize a conjugated `S_4` orbit |
| Domain essentiality | native; no reduction |

## Problem and trust model

This module turns Lin–Munemasa–Taniguchi–Yoshino, [*Sets of equiangular
lines in dimension 18 constructed from A9 + A9 + A1*](https://arxiv.org/abs/2503.06377),
into an exact witness task. The solver receives signed coordinates for vectors
in the paper's `X_5` slice and must return twelve displayed vectors. A sign row
`s` represents `(s/2, 0^10, (1/2,-1/2))`; `verify` checks row shape, displayed
candidate membership, and every integer dot product. It accepts any valid
twelve-row witness and never reads the planted answer.

Generation is theorem-backed. Definition 5.2 gives twelve five-subsets;
Lemma 4.3 turns intersection sizes two or three into affine inner products zero
or one; and Lemma 5.3 proves the set is maximum. The generator carries this
certificate through a uniform coordinate permutation and independent switching,
then adds candidates with the same marginal distribution. It never finds the
certificate by solving the generated instance.

## Why Track B

This is not a Track-A claim. Section 5 and Lemma 5.4 construct a compatibility
graph on 126 switching classes in Magma and enumerate all **151,200** maximum
12-sets. The local exact branch-and-bound has conservative worst-case cost
`O(m^2 d + m^12)` for target size 12. On eight prospective shipping instances
it solved 8/8, averaging 1,819.5 search nodes, 161,138 counted operations, and
0.0413 seconds in the final local audit. A randomized top-two-degree clique
heuristic also solved 8/8;
it still begins by computing the full graph, at least 157,500 scalar
multiply/add operations per instance (1,260,000 across the eight tests).

The compact route instead uses the two conjugated `S_4` generators supplied in
the instance. A transitive 12-orbit need only have one representative compared
with its other eleven members, because compatibility is invariant under the
group action. The adversary sample needed at most 235 permutation, lookup, and
set-intersection steps and no exact arithmetic; the fixed size-audit instance
needed 47 such steps. This is the no-tool compression gap claimed by Track B.

## Worked demo

For `make_instance(n=16, crowding=0, seed=0)`, `render` returns this complete
statement:

```text
Exact affine equiangular vectors in the A9+A9+A1 lattice

There are 16 displayed candidate sign rows s. Every row has length 10,
has exactly five -1 entries and five +1 entries, and encodes

    v(s) = (s_0/2,...,s_9/2, 0,...,0, 1/2,-1/2) in Q^22,

where the middle block contains ten zeros. The switching root is
r=(0,...,0,1,-1). Thus v(s) has squared norm 3 and v(s) dot r = 1.

Find exactly 12 DISTINCT displayed rows such that every two distinct returned
rows a,b satisfy a dot b = -2 or +2. Equivalently, their encoded rational
vectors have inner product 0 or 1. A solution is guaranteed.

In a permutation p below, source position i moves to p[i]. A row and its
entrywise negative are switching mates.

Coordinate symmetries:
  g1: 3 1 6 0 9 5 2 8 7 4
  g2: 4 5 9 3 2 7 6 8 1 0

Candidate rows (return rows, not labels):
  000: -1 -1 +1 +1 +1 +1 +1 -1 -1 -1
  001: -1 -1 +1 -1 -1 +1 -1 +1 +1 +1
  002: -1 -1 +1 +1 +1 -1 +1 -1 -1 +1
  003: +1 -1 -1 +1 -1 +1 -1 +1 +1 -1
  004: -1 +1 +1 -1 -1 -1 +1 +1 +1 -1
  005: +1 -1 +1 -1 -1 +1 +1 -1 -1 +1
  006: +1 +1 +1 +1 -1 -1 -1 -1 -1 +1
  007: +1 -1 -1 +1 -1 -1 +1 -1 +1 +1
  008: +1 +1 -1 -1 -1 +1 +1 +1 -1 -1
  009: -1 +1 -1 -1 +1 -1 -1 +1 +1 +1
  010: +1 -1 +1 +1 +1 -1 -1 +1 -1 -1
  011: -1 -1 +1 +1 -1 -1 +1 +1 -1 +1
  012: -1 -1 +1 +1 +1 +1 -1 -1 +1 -1
  013: -1 +1 +1 +1 -1 +1 -1 -1 +1 -1
  014: +1 -1 +1 -1 +1 -1 +1 -1 +1 -1
  015: -1 -1 +1 +1 -1 -1 +1 +1 +1 -1

Return a lexicographically sorted JSON matrix of 12 distinct length-10 rows.
Give it inside <answer></answer> tags and put nothing else inside the tags.
```

Its answer is:

```json
[[-1,-1,1,-1,-1,1,-1,1,1,1],[-1,-1,1,1,-1,-1,1,1,-1,1],[-1,-1,1,1,1,1,1,-1,-1,-1],[-1,1,1,-1,-1,-1,1,1,1,-1],[-1,1,1,1,-1,1,-1,-1,1,-1],[1,-1,-1,1,-1,-1,1,-1,1,1],[1,-1,-1,1,-1,1,-1,1,1,-1],[1,-1,1,-1,-1,1,1,-1,-1,1],[1,-1,1,-1,1,-1,1,-1,1,-1],[1,-1,1,1,1,-1,-1,1,-1,-1],[1,1,-1,-1,-1,1,1,1,-1,-1],[1,1,1,1,-1,-1,-1,-1,-1,1]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the final row
returns `(False, "wrong_row_count:11")`. A person can solve this demo on paper:
only sixteen rows are present, and applying the two small permutations exposes
the compatible orbit.

## Difficulty presets

| Preset | Candidates | Distinct switching classes | Extra switching mates | Status |
|---|---:|---:|---:|---|
| demo | 16 | 16 | 0 | hand example; hardener skips it |
| easy | 126 | 125 | 1 | **prospective shipping preset**; local gates pass |
| medium | 180 | 126 | 54 | available only if the oracle escalates |
| hard | 240 | 126 | 114 | available only if the oracle escalates |

`n` grows the displayed haystack while the certificate stays at twelve rows.
The G7 construction doubles `n` from 126 to 252 and preserves the 120-atom
answer. No preset has yet received a valid oracle verdict because of the
external key failure below.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted certificates verify and JSON-round-trip |
| G2 | 5/5 corruptions rejected with five distinct reason classes |
| G3 | tagged JSON recovered through prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; `C(126,12)=19,470,069,317,824,125` candidates |
| G5 | demo exact count 1; shipping density 0/200,000; exact reference mean 1,819.5 nodes / 161,138 operations / 0.0413 s, and strongest failing attack 2,048 restarts / 2.86 s total |
| G6 | four attacks each 0/8; two coded reference methods each 8/8 as expected |
| G7 | doubled `n=252` verifies; answer remains 120 atoms |
| G8 | 20/20 relabelling/switching checks and 20/20 unrelated keys |
| G9(c) | **pass**: 444 characters, about 111 tokens, 120 atoms; 0 exact arithmetic and 47 discrete steps |
| G9(a,b), diagnostic | OpenRouter HTTP 403 key-limit error, zero scored attempts; unscored and not a local gate |

## Oracle loop and G9 arms

The required `harden.py` runs were invoked in three isolated directories. In
each arm all four redraws returned `403 Key limit exceeded` before any model
answer was scored. The scripts correctly aborted rather than manufacturing
hardness from provider errors. The transcript files are therefore execution
records, not hardness evidence.

| Arm | Solved / scored attempts | API-error calls | Verdict |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | externally blocked |
| structural hint | 0 / 0 | 4 | externally blocked |
| placebo hint | 0 / 0 | 4 | externally blocked |

The hinted-minus-placebo diagnostic is undefined. In accordance with the
2026-09-05 contract, those arms are recorded but are not gates; the local G9(c)
size/effort gate passes. The directory is nevertheless not submission-ready:
STEP 4 separately requires a scored bare `harden.py` verdict, and no such
verdict can be obtained until the OpenRouter key limit is lifted.

## Use

```python
from gen_2503_06377 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
assert verify(inst, inst["answer"]) == (True, "ok")
```

After obtaining a valid hardened verdict, emit examples from the repository root:

```bash
scripts/emit.sh 2503.06377 20 easy
```

## Caveats

This distribution is intentionally easy for code that constructs the full
compatibility graph; that is the disclosed Track-B baseline. G4 samples uniform
12-subsets of already balanced, displayed rows. It accounts for the obvious
shape constraints but not for a solver that exploits the supplied group action
or compatibility degrees. The extra switching mates beyond 126 candidates can
be canonicalized away by a tool, so those higher rungs mainly increase no-tool
crowding and should not be mistaken for asymptotic complexity evidence.

No external Magma or nauty implementation was run; the local exact search is
the substitute. The canonical key uses stable color refinement and group-orbit
profiles rather than complete isometry testing, so rare nonisomorphic collisions
remain possible. Finally, the current arXiv v3 HTML still prints
`(gamma,r)=1/2` once in the definition of `X`; its displayed `v_5(I)` formula,
the following proof, and Definition 2.1 all give `(gamma,r)=1`, which is the
exact convention checked here.
