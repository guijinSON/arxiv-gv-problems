# Mutation cycles from reddening sequences — verified generator

| Profile field | Value |
|---|---|
| Track | **B** — an efficient exact algorithm exists and is reported |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph (closed walk in an implicit weighted-quiver mutation graph) |
| Certificate | exact symbolic reduced mutation word |
| Intended intuition | change of variables: expose a conjugated acyclic source cycle |
| Domain essentiality | native; no reduction or surrogate |

## Problem and trust model

This module turns Ervin and Neville's [*Mutation Cycles from Reddening
Sequences*](https://arxiv.org/abs/2504.06573) into an exact witness task. A solver
receives a labelled 4-by-4 integer exchange matrix and must return a reduced
vertex word of a specified length whose quiver mutations return the matrix
exactly. `verify` checks the word's shape and replays Definition 2.2 using only
integers; a separate G1 check deletes `inst["answer"]` before calling it.

Generation is inverse and theorem-backed. It samples an abundant acyclic
three-vertex quiver, chooses an alternating conjugator `M`, mutates that block,
adjoins a fourth source, and carries the known word `4,M^-1,S,M` through a
uniform random relabelling. Theorem 4.21 proves closure, Theorem 4.23 proves
simplicity, and Theorem 4.27 proves uniqueness in this rank-four regime. No
search is used during generation. The module is standard-library-only; `gvlib`
is unnecessary for integer exchange-matrix replay.

## Why Track B

This is not a Track-A complexity claim. Lemma 3.11 identifies the easy core: an
abundant acyclic quiver's unique reduced reddening sequence is its source
sequence. Mechanically, the reference algorithm finds the unique decreasing
mutation of the cyclic rank-three block at every step, reaches the acyclic core,
takes its source order, and retraces the descent. It is `O(L r^3)` exact
arithmetic for `r=4`; at the shipping preset it uses 24 trial mutations and 329
counted scalar operations, taking 0.000151 s on the G5 seed, and solves 8/8 panel
instances as expected.

The compact route instead notices that the lightest and heaviest edges of the
rank-three block share its middle vertex. The light edge identifies the
alternating conjugator, its direction identifies the source order, and `L`
fixes the repetition count. This takes at most 32 sign, magnitude, set, and
length operations. Without that invariant, exact descent requires repeated
products of integers up to 39 decimal digits in the displayed shipping matrix.
That mechanical-versus-compact gap is the Track-B claim.

## Worked demo

`make_instance(n=3, repetitions=1, seed=0)` renders in full as:

```text
Find an exact mutation cycle in the following weighted quiver.

A weighted quiver on vertices 0,1,2,3 is represented by a 4 by 4 
skew-symmetric integer matrix B.  If B[i][j] > 0, it is the number 
of arrows i -> j; B[i][j] < 0 represents arrows j -> i.  There are 
no loops and opposite arrows have already been cancelled.

Mutation at vertex k replaces B by B' as follows.  If i=k or j=k, 
B'[i][j] = -B[i][j].  Otherwise
B'[i][j] = B[i][j] + max(B[i][k],0)*max(B[k][j],0) 
             - max(-B[i][k],0)*max(-B[k][j],0).
All arithmetic is exact integer arithmetic.

A mutation sequence is applied from left to right.  It is reduced 
when adjacent labels are different.  Find a reduced sequence of 
exactly L=8 labels whose mutations return exactly to the 
displayed labelled matrix B.  Labels are 0-based, repetitions are 
allowed except in adjacent positions, and order matters.
Promise: every pair of distinct vertices is joined by at least two 
arrows in one direction, and a reduced closing sequence of this exact 
length exists without revisiting an intermediate labelled matrix.

B =
  [0,-84,-7,747]
  [84,0,-10,-9]
  [7,10,0,11]
  [-747,9,-11,0]

Give your final answer inside <answer></answer> tags as one JSON 
array of exactly 8 integers in the range 0..3.
Example: <answer>[3,1,0,2]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[2,1,3,0,3,1,3,1]</answer>`.
`verify` returns `(True, "ok")`; dropping its final label returns
`(False, "wrong length: expected 8, received 7")`. This smallest preset is
hand-solvable by eight direct mutations, and the invariant gives the shorter
route.

## Difficulty presets

| Preset | `n` | Alternating repetitions | Answer length | Status |
|---|---:|---:|---:|---|
| demo | 3 | 1 | 8 | hand example; skipped by hardener |
| easy | 10,007 | 4 | 20 | **shipping; bare oracle pool held** |
| medium | 100,003 | 4 | 20 | larger coefficient height |
| hard | 1,000,003 | 4 | 20 | larger coefficient height |

`n` raises exact-integer coefficient height while the witness stays at 20
atoms. `escalate` exhausts this fixed-length axis before increasing the
conjugator length.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted witnesses verify; 16/16 still verify after deleting the hidden answer; all answers JSON-round-trip |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered through prose and a Markdown fence |
| G4 | 0/200,000 reduced-word guesses; Theorem 4.27 gives exact density `2/4,649,045,868 = 4.302e-10` |
| G5 | demo enumeration `2/8,748`; shipping 64-restart baseline: 0 hits, 28,544 operations, 0.806 s; reference: 329 operations, 0.000151 s |
| G6 | five attacks each 0/8; reference descent 8/8; compact route 8/8 |
| G7 | doubling `n` raises maximum coefficient from `2.294e37` to `1.175e40`; the 20-atom witness still verifies |
| G8 | all 48 relabelling/reversal symmetries on each of 20 seeds: 960/960 invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9 | 41 characters, about 11 tokens, 20 atoms, 32 intended operations; cap gate passes |

## Oracle loop

The preserved bare transcript was produced by `scripts/harden.py` before the
available OpenRouter key exhausted its total limit. It predates a wording-only
self-containment clarification in `render`; a fresh run of the final file was
attempted in `bare_retry` but every call received HTTP 403. Thus the preserved
run tests the same generator and answer contract, but is not a fresh final-file
run.

| Preset | Model | Seed | Solved | Reason |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 806643057 | no | parsed word failed exact replay |
| easy | Gemini 3.1 Pro Preview | 1826765562 | no | parsed word failed exact replay |
| easy | GPT-5.6 Terra | 270591961 | no | parsed word failed exact replay |

The preserved run's bare verdict is hardened at `easy`, with zero escalations;
fresh final-file confirmation remains quota-blocked.

## G9 arms

| Arm | Valid solved / attempts | Run status |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 0 | four HTTP 403 quota errors; no attempt was scored |
| placebo hint | 0 / 0 | four HTTP 403 quota errors; no attempt was scored |

The hinted-minus-placebo difference is unavailable, so no conclusion about the
hint effect is claimed. The error-only transcripts are retained rather than
misreported as model failures. These arms are diagnostic, not gates, under the
2026-09-05 rule; the gated size/effort result is 41 characters, 11 estimated
tokens, 20 atoms, and 32 intended operations.

## Use

```python
from gen_2504_06573 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root:

```bash
scripts/emit.sh 2504.06573 20 easy
```

## Caveats

The unique global source is deliberately visible: it is native
triangular-extension structure, not a hidden decoy. The outlier and source-sweep
attacks exploit it and still fail, but recognizing the light/heavy-edge invariant
solves the family quickly. Accordingly, this measures structure recognition,
not worst-case mutation-cycle hardness. The G4 prior is uniform over all reduced
words of the required length; a theorem-aware prior would put much more mass on
conjugated source words. No external cluster-algebra package was tested. Exact
replay of adversarial wrong words can grow intermediate integers sharply, though
the fixed length 20 keeps measured verification practical. Finally, the standard
descent algorithm is fast with tools, which is precisely why a Track-A label
would be false.
