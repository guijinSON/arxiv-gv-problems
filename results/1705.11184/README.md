# One-cop-moves safe-spoke generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | exact symbolic (a compressed canonical graph path) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This module turns Gao and Yang's [*The Cop Number of the One-Cop-Moves Game on Planar Graphs*](https://arxiv.org/abs/1705.11184) into an unlimited family of exact escape-path problems.  The solver receives an implicit finite planar subdivided wheel, the positions of three cops, and a reversible labelling of its boundary.  It must name the one spoke whose canonical hub-to-boundary path is certified safe.  `verify` decodes that path and checks three exact graph-distance inequalities; it never reads the planted answer.

The construction is native to the paper's objects.  Section 2 defines the alternating robber/one-active-cop game.  Section 5, Lemma 5.2 proves the executable certificate used here: a robber following a length-L path cannot be caught by a cop whose initial distance to the endpoint exceeds L.  This generator strengthens the sufficient check by requiring it separately for all three cops.  It samples the unique safe boundary position first, composes three closed cop-distance arcs around every other position, and only then relabels the graph.

## Why Track B

The mechanical reference algorithm is explicit: decode the three cop coordinates and exhaustively inspect the `2**n` endpoints.  This is `O(2**n)` in the succinct parameter and linear in the number of boundary endpoints (ordinary BFS on the fully expanded graph would be much larger).  At the shipping preset, the measured reference run visited 8,418,459 endpoints, made 22,046,664 cop-distance tests, and used 132,280,080 accounted integer operations in 2.627444 seconds.  The eight-seed reference panel solved 8/8 in 18.113076 seconds and 1,076,068,680 operations.

The disclosed efficient shortcut is `O(n + encoding_rounds)` and takes 160 counted operations: undo the rotations, masks, bit permutation, and reflected-Gray encoding on three labels; view each cop's forbidden endpoints as a cyclic interval; test the three points immediately after the interval ends; and encode the valid point.  The implementation checks this route on 8/8 panel instances without reading `inst["answer"]`.  That arithmetic is within the no-tool cap but is not mechanically replaceable by scanning 16,777,216 labels in context.  The paper is similarly explicit about the algorithmic side: Lemma 5.1 invokes Floyd–Warshall-style shortest-path reasoning, while Section 7 says the known full-game characterisations would require about `1.2e23` checks on the authors' 302,762-vertex graph.  Section 7's planar-separator bound concerns how many cops suffice, not a compact strategy for this position.

## Worked demo

The `demo` preset with seed 0 renders this complete instance:

```text
One-cop-moves escape certificate on a planar graph

The finite undirected graph has a hub H and 16 spokes.  A spoke is identified
by an integer label x with 0 <= x < 16.  For every label x it has vertices
(x,1),...,(x,4); H is adjacent to (x,1), consecutive depths on one spoke
are adjacent, and the boundary vertices (x,4) form one cycle in the order
defined below.  Thus the graph is a planar subdivided wheel.

Boundary order.  Number cyclic positions i=0,...,15.  All bit operations
use exactly 4 low bits, numbered from least-significant bit 0.  A left rotation
by r moves bit j to bit (j+r) mod 4.  Let gray(z)=z XOR floor(z/2).  To obtain
the spoke label B(i), start with gray((9 + 1*i) mod 16); move source bit j to
output bit p[j] for p = [0, 1, 3, 2]; XOR the result with 12; then apply these
[left-rotation, XOR-mask] pairs from left to right: twists = [].
Here left-rotation is cyclic on 4 bits.  The boundary cycle has edges between
(B(i),4) and (B((i+1) mod 16),4).

Game configuration.  The robber is at H and moves first.  In every round the
robber traverses one edge and afterward exactly one of the three cops traverses
one edge.  A cop catches the robber by ever occupying her vertex.  The cops are
on the following spokes; depth is graph distance from H:
  cop 1: (label=11, depth=2), cop 2: (label=15, depth=2),
  cop 3: (label=4, depth=2)

Your witness must select a canonical spoke path from H through
(x,1),(x,2),...,(x,4).  It is valid exactly when, for each of the three cops,
the cop's initial shortest-path distance to endpoint (x,4) is strictly greater
than 4.  This exact inequality certifies that the robber reaches the endpoint
without capture even if that cop were allowed to move after every robber step.
There is exactly one valid label.  Labels are decimal integers; indexing is
0-based; no other path kind or extra field is allowed.

Give your final answer inside <answer></answer> tags, as exactly this JSON form,
replacing x by one decimal integer:
{"path":{"kind":"spoke","label":x}}
Example: <answer>{"path":{"kind":"spoke","label":3}}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"path":{"kind":"spoke","label":3}}</answer>`, and `verify` returns `(True, "ok")`.  Changing the label to 4 returns `(False, "cop 3 can reach the endpoint in 2 steps")`.  A person can solve this 16-spoke demo by listing the boundary order and crossing out the three cop arcs.

## Difficulty presets

| Preset | `n` | Encoding twists | Candidate spokes | Status |
|---|---:|---:|---:|---|
| demo | 4 | 0 | 16 | hand-solvable illustration |
| easy | 20 | 1 | 1,048,576 | oracle unavailable |
| medium | 22 | 2 | 4,194,304 | oracle unavailable |
| hard | 24 | 3 | 16,777,216 | **shipping preset**, local gates pass |

No preset was rejected by a local gate.  The required external ladder could not grade any preset because the configured OpenRouter key returned HTTP 403 “Key limit exceeded” for every vendor draw.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset–seed plants verified |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose/fence/tag round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 hits; exact structure-aware density `1/16,777,216 = 5.96046e-8` |
| G5 | pass | exactly 1 valid answer; baseline 2.627444 s, 8,418,459 endpoints, 132,280,080 operations |
| G6 | pass | four attacks 0/8 each; reference and compact algorithms both 8/8 as expected |
| G7 | pass | doubled `n=48` instance builds and verifies |
| G8 | pass | 140/140 individual/composed relabellings and carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 42 worst-case chars, 11 estimated tokens, 2 atoms, 160 intended operations |

The four failing G6 attacks are a label-Hamming outlier, the largest numeric-label gap, 256 random restarts, and an in-context ansatz that decodes the cyclic order but incorrectly treats the three cop radii as equal.  Plants and decoys are identically distributed under the random reversible labelling; every candidate boundary endpoint also has the same graph degree.

## Oracle loop and G9 diagnostic

| Run | Preset | Valid attempts | Solved | Outcome |
|---|---|---:|---:|---|
| bare | easy | 0 | 0 | four script-recorded HTTP 403 quota errors; no verdict |
| structural hint | hard | 0 | 0 | four script-recorded HTTP 403 quota errors; no verdict |
| placebo hint | hard | 0 | 0 | four script-recorded HTTP 403 quota errors; no verdict |

Errors do not count as model failures, so `hinted - placebo` is unavailable—not zero evidence of an effect.  The three transcript files are retained exactly as written by `harden.py`.  Once quota is restored, all three runs must be repeated; until then there is no four-vendor hardness claim despite all local gates passing.  The structural hint only names the reflected-Gray cyclic order; it does not state the gap or a procedure.

## Use

From this result directory:

```python
import random
import gen_1705_11184 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
prompt = gen.render(inst)
answer = gen.parse_answer('<answer>{"path":{"kind":"spoke","label":0}}</answer>')
ok, reason = gen.verify(inst, answer)
candidate = gen.random_candidate(inst, random.Random(123))
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1705.11184 20
```

## Caveats

This is a Lemma-5.2 path-certificate family, not a certificate of the full cop number of the authors' 302,762-vertex graph.  The subdivided wheel is not the paper's graph `D`; it stays in the paper's native graph/game/path objects and instantiates the graph-generic triangle-inequality proof of Lemma 5.2.  It tests recognizing a hidden cyclic coordinate; providing decoded boundary ranks, removing the label scrambling, or using a script makes it easy.  G4 samples uniformly from every correctly shaped spoke descriptor—the exact prior implied by the statement—and proves resistance to unstructured guessing, but it says nothing about a solver that notices the Gray change of variables.  The adversary panel did not test learned Gray-code recognition, symbolic bit-vector solvers, SAT/SMT encodings, or provider models because the external quota was exhausted.  The canonical key completely handles the represented cycle automorphisms, arbitrary bit-permutation/rotate-XOR label changes, and cop-order symmetries; it does not attempt arbitrary coloured-graph isomorphism.  The module remains standard-library-only if `gvlib` is absent.
