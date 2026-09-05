# 1402.1813 — retained Track B list-coloring generator (parked)

**Disposition: `cap_bound`; this family is not rejected, but it is not shipped.**
The largest writable preset was solved by two of three bare oracles.  The next
subdivision has 352 answer atoms, above the 256-atom cap.  The generator and
evidence are retained so the decision can be revisited under a larger output cap.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression, not a structural-hardness claim |
| Native domain | combinatorics |
| Object regime | finite_discrete |
| Computational core | csp_sat |
| Certificate form | integer_tuple |
| Intended intuition | invariant: barycentric-weight parity transports a proper base labeling |
| Domain essentiality | native; no reduction |

## Problem and construction

The source is Postle and Thomas, [*Five-list-coloring graphs on surfaces I. Two
lists of size two in planar graphs*](https://arxiv.org/abs/1402.1813).  Section 1
defines an `L`-coloring, and Theorem 1.3 proves that a plane graph is list-colorable
when two outer-cycle vertices have lists of size two, the other boundary vertices
have lists of size at least three, and interior vertices have lists of size at
least five.  The solver receives exactly those native objects and must return one
color per vertex.  `verify` checks list membership and every edge inequality using
integers only.

Generation never solves the generated instance.  It starts with a fixed proper
labeling of an icosahedron, refines every triangular face by a barycentric grid,
deletes the interior of one face to make its boundary outermost, and transports
the labeling by XOR parity.  Vertex names and three-bit labels are randomized by
an affine bijection.  Neighbor colors are used as list decoys.  Eight affine base
keys are displayed, exactly one of which expands to a list-valid coloring.

## What Track B meant here, and why it did not ship

This paper proves existence, not a hard distribution, so Track A would be false.
Theorem 1.2 gives the especially easy adjacent-precolored-edge extension regime;
Lemma 2.3 and the minimal-counterexample proof in Section 3 are extension tools,
not hardness results.  Postle's later algorithmic paper states that the
Thomassen-style proofs naturally yield quadratic-time coloring algorithms
([arXiv:1904.03723](https://arxiv.org/abs/1904.03723)).  Our executable proxy is
ordinary MRV forward-checking: it has exponential worst-case complexity, but on
every tested instance here it takes the same zero-backtrack quadratic scan—about
0.012 seconds, 246 decisions, and 151,131 exact list tests.  This distribution is
plainly easy for a machine.

The compact route first eliminates incompatible displayed base keys using about
25 membership probes on average, then expands the survivor in 114 XORs.  This is
an `O(N)` decoder and fits the 300-operation no-tool cap.  Even after fixed-length
hardening—eight colors, neighbor-color crowding, a 256-restart filter, and eight
candidate keys—the final bare oracle pool solved 2/3 instances.  Increasing the
frequency from 5 to 6 raises the mandatory coloring from 246 to 352 entries, so
the harness correctly returned `cap_bound` rather than `too_easy`.

## Worked demo (`n=1`, `seed=0`)

A person can solve this demo on paper: each tag is a single base vertex, so test
the eight key rows against the displayed lists and copy the compatible row in
vertex order.

```text
Vertices: 0..11
Outer cycle: 3 10 11
Special two-list vertices: 3 11
Key rows (row: zero | base labels 0..11):
0: 5 | 5 0 7 0 1 4 4 3 2 5 7 0
1: 4 | 4 1 5 1 3 6 6 2 0 4 5 1
2: 2 | 2 1 4 1 0 3 3 6 7 2 4 1
3: 3 | 3 5 1 5 0 6 6 2 7 3 1 5
4: 5 | 5 0 6 0 1 4 4 2 3 5 6 0
5: 7 | 7 1 4 1 0 6 6 3 2 7 4 1
6: 2 | 2 3 6 3 0 1 1 4 7 2 6 3
7: 5 | 5 1 7 1 4 0 0 6 3 5 7 1
Vertex records (v: tag | L(v)):
0: 5^1 | 1,3,4,5,6
1: 11^1 | 0,1,2,4,5
2: 7^1 | 0,1,2,5,6
3: 0^1 | 4,5
4: 9^1 | 1,3,4,5,6
5: 4^1 | 0,1,3,4,6
6: 3^1 | 0,1,2,4,5
7: 6^1 | 1,2,3,5,6
8: 8^1 | 0,1,2,3,4
9: 10^1 | 1,2,4,5,6
10: 1^1 | 1,5,6
11: 2^1 | 2,5
Edges:
0-3 0-4 0-5 0-9 0-10 1-2 1-4 1-7 1-8 1-9 2-6 2-7 2-8 2-11
3-5 3-6 3-10 3-11 4-5 4-8 4-9 5-6 5-8 6-8 6-11 7-9 7-10 7-11
9-10 10-11
Output exactly 12 colors as JSON inside <answer></answer> tags.
```

Answer: `<answer>[6,1,2,4,4,3,1,6,0,5,1,5]</answer>`.
`verify(inst, answer)` returns `(True, "ok")`; dropping the last entry returns
`(False, "wrong length: expected 12, got 11")`.

## Presets and gates

| Preset | Frequency | Vertices | Edges | Answer chars | Status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 12 | 30 | 25 | hand example |
| easy | 3 | 91 | 264 | 183 | solved 3/3 by bare oracles |
| medium | 4 | 159 | 465 | 319 | solved 1/3; one additional API timeout |
| hard | 5 | 246 | 723 | 493 | solved 2/3; maximum writable candidate |

| Gate | Result |
|---|---|
| G1 | 12/12 planted and displayed-decoder checks pass; 12/12 JSON round trips |
| G2 | five corruptions rejected for five distinct reasons |
| G3 | realistic tagged response round-trips, length 246 |
| G4 | 0 hits / 200,000 structure-aware product-of-lists samples; 558-bit space |
| G5 | demo has 57,884 exact solutions; shipping-candidate density 0/200,000; 256-restart attack cost 62,976 steps |
| G6 | six attacks each 0/8; reference MRV 8/8; compact decoder 8/8 |
| G7 | doubled size builds and verifies: 966 vertices, 2,219-bit candidate space |
| G8 | 100/100 relabeling invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | not reached for the final variant because bare hardening failed; size/effort alone were 493 chars, 246 atoms, 114 XORs |

## Final oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 2124939234 | Google | solved | verified witness |
| easy | 747516427 | xAI | solved | verified witness |
| easy | 1446990150 | OpenAI | solved | verified witness |
| medium | 1736282121 | OpenAI | failed | submitted color not in `L(59)` |
| medium | 42074406 | Google | failed | returned 151 colors, expected 159 |
| medium | 1177980046 | xAI | solved | verified witness |
| hard | 1625702536 | OpenAI | solved | verified witness |
| hard | 625101042 | Google | failed | edge conflict on `0-42` |
| hard | 315809543 | xAI | solved | verified witness |

The final G9 arms are therefore bare `2/3`, hinted `0/0`, and placebo `0/0`:
hinted and placebo were deliberately not run after the prerequisite bare gate
failed.  There is no hinted-minus-placebo conclusion for this retained variant.

## Use

```python
from gen_1402_1813 import make_instance, verify
inst = make_instance(n=5, seed=7)
ok, reason = verify(inst, inst["answer"])
```

From the repository root, `bash scripts/emit.sh 1402.1813 20` exercises emission,
but this result must not be submitted while `.meta.json` says `cap_bound`.

## Caveats

The main caveat is decisive: two vendors solved the maximum writable preset, and
the standard solver is extremely fast with zero backtracking.  G4 samples only
independent choices from the displayed lists; zero observed hits shows that blind
guessing is poor, not that structurally informed guessing has probability below a
statistical confidence bound.  The generator filters the named attacks, so other
restart seeds, a production SAT/CP solver, and theorem-specific implementations
may do better; none was run because only the standard library is allowed.  The
canonical key normalizes affine color names and uses multisets of local vertex
and edge signatures, so every vertex relabeling—including an icosahedral base-frame
automorphism—is invariant. It is a strong fingerprint rather than a complete graph
isomorphism canonizer, so collisions are possible in principle; none occurred across
the 20 unrelated seeds in G8.
