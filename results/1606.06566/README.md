# Affine band-graph path decompositions

**Status:** the generator and all local gates pass, but this result is **not yet
shippable**.  The required bare oracle loop exhausted the OpenRouter key's total
limit after 11 completed calls, before producing a verdict; the two G9 diagnostic
arms could not be run.  The partial transcript is preserved unedited.

| Profile field | Value |
|---|---|
| Track | B — an efficient certificate-producing algorithm is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | matrix certificate |
| Native objects | undirected graph; nice path decomposition |
| Intuition | change of variables: modular differences expose a banded order |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

The source is Martin Fürer's [*Faster Computation of
Path-Width*](https://arxiv.org/abs/1606.06566).  Section 2 defines a nice path
decomposition as one introduction and one later forgetting event per vertex,
with every edge's endpoints sharing a bag; width is maximum bag size minus one.
An instance gives a residue-labelled undirected graph.  The solver returns an
`n × 2` integer matrix containing each vertex's introduction and forgetting
ranks.  `verify` checks the rank permutation, bag sizes, and edge overlap using
integers only, and accepts any valid decomposition.

Generation is inverse: it first samples an affine vertex order, adds edges only
within distance `k` of that order, and writes a FIFO width-`k` decomposition.
No path-width computation or decomposition search occurs during generation.

## Why this is Track B

Section 4, Theorem 1 reduces width from an available width-`ell`
decomposition in `2^{O(ell*k)} n` time.  Section 5 and its corollary compute
path-width and an accompanying decomposition in `2^{O(k^2)} n` time.  Thus
small fixed `k` is explicitly FPT and cannot support an honest Track-A claim.

The executable reference here is exact subset dynamic programming over
vertex-separation prefixes, `O(n 2^n)`.  At the provisional shipping preset it
solved 8/8 instances in an average 2.63 seconds and 6,456,295 transitions.  The
compact route counts modular edge differences: one difference class is a
spanning path, after which FIFO bags give the certificate.  Its conservative
bound is 225 integer operations.  The benchmark tests whether a no-tool solver
notices that affine coordinate change rather than carrying out generic DP.

## Worked demo

For `make_instance(n=5, seed=0, width=2, density_num=3,
density_den=5, modulus=59)`, the vertices are `20 23 48 51 54` and the edges
are:

```text
(20,23) (20,48) (20,51) (23,51) (23,54) (48,51) (51,54)
```

One answer is:

```json
[[1,5],[4,8],[0,3],[2,7],[6,9]]
```

`verify(inst, answer)` returns `(True, "ok")`.  Reversing the first row to
`[5,1]` returns `(False, "row 0 is not introduced before it is forgotten")`.
The demo is hand-solvable: the repeated modular edge difference reveals the
five-vertex path, and only ten event ranks must be written.

## Difficulty presets

| Preset | n | k | Optional-edge density | Status |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 60% | hand example; skipped by hardener |
| easy | 17 | 5 | 75% | oracle solved 3/3 |
| medium | 20 | 6 | 80% | oracle solved 1/3 |
| hard | 23 | 7 | 86% | provisional shipping; oracle solved 1/3 |
| first escalation | 23 | 7 | 91% | 1/2 solved before API exhaustion |

`SHIPPING_DIFFICULTY` remains `hard` provisionally.  It must be changed only
after a complete script-owned verdict.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | planted certificate verified on 12 preset/seed pairs |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced, prose-surrounded answer round-tripped |
| G4 | pass | 0/200,000 uniform width-bounded event sequences valid; 161-bit language |
| G5 | pass | shipping sampled density 0; demo exact count 72/52,920; strongest restart 256 iterations |
| G6 | pass | four attacks 0/8 each; reference DP and compact route 8/8 |
| G7 | pass | doubled `n=46` builds and verifies; candidate space grows |
| G8 | pass | 60/60 invariant relabellings, 60/60 carried witnesses, 20/20 distinct seeds |
| G9(c) | pass | 175 chars, 46 atoms, 225 intended operations (limits 2000/256/300) |

The G4 prior is structure-aware: it samples uniformly from labelled event
sequences that already satisfy introduction-before-forgetting and the width
bound.  It does not sample malformed matrices.  Zero observed hits is an upper
sampling observation, not proof that the exact solution density is zero.

## Oracle loop and G9 diagnostics

| Arm / level | Solved | Attempts | Conclusion |
|---|---:|---:|---|
| bare easy | 3 | 3 | defeated |
| bare medium | 1 | 3 | defeated |
| bare hard | 1 | 3 | defeated |
| bare escalation (91%) | 1 | 2 | incomplete; key limit reached |
| G9 bare at final shipping params | 0 | 0 | not run |
| G9 structural hint | 0 | 0 | not run |
| G9 placebo hint | 0 | 0 | not run |

There is no valid hinted-minus-placebo estimate yet.  The preliminary bare
evidence is unfavorable: multiple vendors found the affine structure.  It
would be wrong either to call the family hardened or to reject the paper before
the harness finishes its permitted escalation sequence.

## Use

```python
import gen_1606_06566 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emission (after a valid hardened verdict) is:

```bash
bash scripts/emit.sh 1606.06566
```

## Caveats

The complete distance-one edge class is a deliberate detectable signature; a
solver that tallies modular differences gets the answer cheaply.  This is the
intended insight, but the partial oracle results show it may be too accessible
at the current sizes.  No SAT/ILP encoding, path-width-specific skeleton-DP
implementation, or sophisticated interval-graph recognition attack was run.
The reference subset DP uses the standard vertex-separation characterization,
not the paper's skeleton implementation.  The 1-WL canonical key is complete on
the 20 tested asymmetric instances; if a future instance leaves tied color
classes, the safe quotient fallback may collide across non-isomorphic graphs.
Finally, a complete bare verdict and both G9 arms remain mandatory after the
OpenRouter limit is raised.
