# Affine triangle-factor certificates from arXiv:2503.05218

> **Build status:** the module and every local gate pass. It is not yet
> shippable: the required oracle calls all returned OpenRouter HTTP 403 “Key
> limit exceeded,” so there are zero counted model attempts and no hardness
> verdict. The transcripts preserve those errors without treating them as model
> failures.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate | exact symbolic: two affine perfect-matching formulas |
| intuition | decomposition: recognize translated adjacency rows and compose one matching from each sparse pair |
| domain essentiality | native |
| reduction | none |

## Problem and construction

The source is Guo and Markström, [*Density conditions for k vertex-disjoint
triangles in tripartite graphs*](https://arxiv.org/abs/2503.05218). An instance
is a balanced tripartite graph with parts `A`, `B`, and `C`. Every `A--B` edge is
present. Each of `A--C` and `B--C` is given by adjacency lists and is an
unmarked union of affine perfect matchings on `Z/nZ`.

The answer `{"ac":[u,s],"bc":[v,t]}` represents the matchings
`a -> u*a+s (mod n)` and `b -> v*b+t (mod n)`. Section 4, Proposition 4.1
says that two such matchings compose through their common `C` endpoints into a
triangle-factor because `A--B` is complete. Generation samples the unit slopes
and offset sets first, so it knows the witness by composition and never solves
the displayed graph. Verification checks coprimality and every represented edge
with exact integer arithmetic.

## Why Track B

This is not a Track A claim. Theorem 1.3 is an extremal existence theorem for
`n >= 5k+2`, not a distributional-hardness theorem. The natural dense-random
planting at that boundary was separately audited and a lexicographic greedy
scan found all `k=16` triangles on 128/128 instances in about 82 edge lookups.
Section 4 also explicitly reduces its triangle-factor proof to matching and
Hall's theorem.

For the bounded symbolic language used here, the reference algorithm enumerates
unit slopes and the intercepts forced by row 0, rejecting each formula against
the adjacency lists. Its worst-case bound is `O(n^2 d)` membership tests. At
the hard preset it solved 8/8 instances, using at most **32,490** tests and
**0.0087 s** in the recorded self-test. The compact route notices that each row
is a translate of one offset set: the difference between the sums of rows 1 and
0 is `d*u (mod n)`. It recovers both slopes and chooses two row-0 intercepts in
**94 exact operations**. The Track B challenge is finding that invariant among
independently shuffled rows and neighbor orders; with tools, the task is easy.

## Worked demo

For `make_instance(n=7, degree=2, seed=0)`, `render` gives the following graph
(the complete `A--B` pair is stated rather than listed):

```text
A--C adjacency
A1: C4 C1
A6: C1 C5
A4: C5 C2
A3: C0 C4
A2: C2 C6
A0: C3 C6
A5: C3 C0

B--C adjacency
B0: C4 C1
B5: C5 C2
B4: C6 C2
B1: C4 C0
B6: C5 C1
B3: C6 C3
B2: C0 C3
```

The requested formulas use labels `0..6`, unit slopes modulo 7, and all their
generated edges must be listed. One answer is:

```text
<answer>{"ac":[5,6],"bc":[3,4]}</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. The dropped-entry
corruption `{"ac":[5,6],"bc":[3]}` returns
`(False, "bc must contain exactly two integers")`. A person can solve this
demo on paper by comparing the row-0 and row-1 sums modulo 7.

## Difficulty presets

| preset | n | sparse degree | rendered chars (seed 0) | structured candidate space | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 1,496 | 144 | hand-solvable illustration |
| easy | 127 | 6 | 8,980 | 571,536 | oracle not reached: quota error |
| medium | 503 | 12 | 64,912 | 36,288,576 | not reached |
| hard | 1,511 | 16 | 274,912 | 583,705,600 | designated shipping candidate; oracle evidence pending |

`escalate()` increases `n` while retaining the same four answer atoms. No
answer-length cap is being used as a hardness ceiling.

## Local gates

| gate | measured result |
|---|---|
| G1 | 16/16 planted symbolic factors verify and round-trip through JSON |
| G2 | empty, dropped, duplicated, swapped, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered from a realistic fenced response |
| G4 | 1/1,200,000 structure-aware guesses; exact probability `256/583,705,600 = 4.386e-7` |
| G5 | exactly 256 hard-preset certificates; reference maximum 32,490 tests and 0.0087 s |
| G6 | degree outlier, first-entry greedy, 256 random certificates, and small-slope ansatz each 0/8; reference algorithm 8/8 as Track B expects |
| G7 | doubled `n=3022` instance builds and verifies with the answer still four atoms |
| G8 | 80/80 affine-relabel/input-order invariance checks, 80/80 carried-witness checks, and 20/20 unrelated keys distinct |
| G9(c) | 34 characters, about 9 tokens, 4 atoms, and 94 intended-route operations |

The G4 prior already enforces everything free from the statement: unit slopes
and intercepts selected from the two row-0 neighbor lists. The exact count, not
the sampling fluctuation, is the authoritative density.

## Oracle loop

No row below is a counted attempt; every call failed before a model reply.

| arm | preset | seeds | counted solved/attempts | result |
|---|---|---|---:|---|
| bare | easy | 155080312, 1864036723, 2110848143, 1372439567 | 0/0 | four HTTP 403 key-limit errors; harness aborted |
| structural | hard | 643606190, 648460621, 1351949959, 2071032452 | 0/0 | four HTTP 403 key-limit errors; harness aborted |
| placebo | hard | 1273198993, 1925194290, 1187721167, 461998152 | 0/0 | four HTTP 403 key-limit errors; harness aborted |

Thus `hinted - placebo` is unavailable, and there is no conclusion yet about
whether naming the translate invariant helps. The answer-size and intended-route
caps pass independently.

## Use

```python
from gen_2503_05218 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

After OpenRouter quota is restored, rerun the bare harness first, update the
shipping rung from its verdict, rerun `selftest()`, and then rerun the two G9
arms in isolated directories. Only after those succeed should emission run from
the repository root:

```bash
scripts/emit.sh 2503.05218 20 hard
```

## Caveats

This generated subclass asks for an affine symbolic triangle-factor, not an
arbitrary factor; Proposition 4.1 licenses the represented factor, but the
affine promise is generator-added structure. The family becomes easy as soon as
the solver recognizes the row-sum invariant or can run enumeration code. The
G4 density measures blind guesses after the strongest immediate row-0 pruning;
it does not measure a solver's chance of inferring translations from the other
rows. The 275k-character hard prompt is large, although the answer and intended
arithmetic are small.

The adversary panel does not include SAT, SDP, or spectral relaxations because
the accepted witness is an exact affine formula and exhaustive formula search
is the relevant complete baseline. The canonical key exactly removes affine
cyclic relabelings within each sparse pair, but it canonicalizes the two offset
sets separately and can therefore over-collapse rare instances with different
cross-pair alignment. Most importantly, the Track B hardness claim remains
unverified until the required non-error oracle transcript exists.
