# Verified binary projective-line partitions

This directory turns Sascha Kurz's [*Additive codes attaining the Griesmer
bound*](https://arxiv.org/abs/2412.14615) into a planted witness problem.  A
solver receives distinct nonzero binary vectors and must partition every vector
exactly once into triples whose XOR is zero.  Over `GF(2)`, each such triple is
exactly the three points of a projective line.  The checker verifies shape,
coverage, and every XOR in time linear in the submitted witness.  It accepts any
valid partition, not only the planted one.

## Why this is a credible hard family

Section 2 defines a point multiset to be *h-partitionable* when it is exactly the
incidence sum of h-dimensional projective subspaces, then connects these systems
to additive codes.  This module takes `q=h=2` and multiplicity one, turning that
definition into exact cover by binary projective lines.  Generation is inverse:
it samples disjoint lines first, shuffles their union, and retains the sampled
partition as a witness.

Section 4 is the important boundary.  Its incidence equation
`A^(1,h;r,q) x = b` and Smith normal form decide unrestricted *integer*
solvability, but the required fixed nonnegative decomposition remains an ILP;
the paper calls finding the smallest feasible multiplier a significant hard
challenge and gives large open partial-spread cases.  Perfect matching in an
arbitrary partial Steiner triple system is NP-complete
([Li–Toulouse, 2006](https://combinatorialpress.com/ars-articles/volume-080-ars-articles/some-np-completeness-results-on-partial-steiner-triple-systems-and-parallel-classes/)).
That worst-case theorem is supporting context, not a proof for this narrower
projective planted distribution.

The generator avoids the paper's easy regimes: `h=1`; uniform multiples of the
whole projective point set, handled by the uniform-partition theorem in Section
2; and the sufficiently large chain types constructed by Section 3's main and
asymptotic theorems.  Ambient rank grows with instance size, and shipping
instances are sparse irregular subsets with at least three candidate lines
through every point.

## Worked example (`easy`, seed 0)

```text
BINARY PROJECTIVE-LINE PARTITION WITNESS PROBLEM

Work with 7-bit vectors over GF(2). Addition in GF(2) is
coordinate-wise XOR. In the binary projective space, every nonzero
vector below represents one point (there is no nontrivial scalar
rescaling to identify). A projective line is exactly a set of three
distinct points {a,b,c} whose vectors satisfy a XOR b XOR c = 0;
equivalently c = a XOR b.

The instance contains 24 distinct nonzero points, labelled
1 through 24. Partition all of them into exactly 8
projective lines. Every label must occur exactly once. A block is an
unordered triple, the blocks are unordered, and repeats are forbidden.
All bounds are inclusive and labels are 1-indexed.

POINTS (label: fixed-width vector)
01: 0000110
02: 1011111
03: 1111101
04: 1100101
05: 0110010
06: 1110010
07: 0010000
08: 1011110
09: 1101101
10: 0110110
11: 0110000
12: 1000010
13: 1100010
14: 1001011
15: 0001110
16: 1110101
17: 1110011
18: 1101011
19: 0111000
20: 0011100
21: 1111100
22: 0111111
23: 0100010
24: 1101001

Output exactly 8 triples. Separate labels within a triple by
commas and separate triples by semicolons. Do not use brackets. Order
inside a triple and the order of triples do not matter.

Give your final answer inside <answer></answer> tags, as
semicolon-separated comma-separated triples of decimal point labels.
Example: <answer>1, 2, 3; 4, 5, 6</answer>
Output nothing else inside the tags.
```

One answer is
`<answer>1, 10, 11; 2, 5, 9; 3, 12, 22; 4, 15, 18; 6, 7, 13; 8, 21, 23; 14, 17, 19; 16, 20, 24</answer>`.
It gives `verify(inst, inst["answer"]) == (True, "ok")`.  Dropping the
last triple gives `(False, "expected exactly 8 blocks, got 7")`.

## Difficulty presets

| Preset | Lines | Points | Bits | Generation guards | Status |
|---|---:|---:|---:|---|---|
| easy | 8 | 24 | 7 | degree ≥1 | Oracle solved 3/3; intentionally a control |
| **medium** | **96** | **288** | **12** | degree ≥3; 16 restarts; 25k-node search | **Ships; oracle solved 0/3** |
| hard | 192 | 576 | 14 | same guards | Scaling/top rung; plant verified on 3 seeds |
| discarded prototype | 24 | 72 | 9 | degree ≥2 | Rejected by G6: random restarts 6/8, 25k search 8/8 |

`SHIPPING_DIFFICULTY` is `medium`.  The discarded 72-point prototype was
removed from `DIFFICULTY` before the final oracle run; the first transcript was
overwritten by the required rerun, so the checked-in transcript refers only to
the final ladder.

## Mandatory gates

| Gate | Measured result | Pass |
|---|---|:---:|
| G1 planted verifies | 9/9 preset/seed instances | yes |
| G2 corruptions | 5/5 rejected with 5 distinct reasons | yes |
| G3 round trip | fenced/prose response parsed as 96 blocks | yes |
| G4 structured guess | 0/200,000 uniform exact triple partitions | yes |
| G5 sparse | 1 solution / 1,401,400 partitions (`7.136e-7`) | yes |
| G6 attacks | five attacks each solved 0/8 shipping seeds | yes |
| G6 bounded search | 25,001 nodes and budget exhaustion on all 8 seeds | yes |
| G7 scaling | 288 → 576 points; doubled plant verifies | yes |
| G8 canonical key | 60/60 invariance, 20/20 real transforms, 20/20 distinct | yes |

G4 is structure-aware: it samples uniformly from partitions that already have
the exact number of blocks, three labels per block, no repetition, and complete
coverage.  It tests only the XOR-line constraints after granting those facts.

## Oracle hardening loop

All scoreable calls used medium reasoning effort.  A timeout is an API error and
does not vote on hardness.

| Preset | Seed | Oracle | Result | Verifier/detail |
|---|---:|---|---|---|
| easy | 167462900 | Grok 4.6 | solved | `ok` |
| easy | 1670024750 | Claude Sonnet 5 | solved | `ok` |
| easy | 1402185238 | GPT-5.6 Terra | solved | `ok` |
| medium | 236339632 | Gemini 3.1 Pro Preview | failed | parsed; block B1 was not a line |
| medium | 1524809536 | GPT-5.6 Terra | failed | parsed; returned 5 rather than 96 blocks |
| medium | 1390261777 | Grok 4.6 | excluded | 900-second API timeout; redrawn |
| medium | 1189608797 | Claude Sonnet 5 | failed | no content after 32k reasoning/completion budget |

The script verdict is `hardened` at the named `medium` preset after one
escalation.  The authoritative call records and master seed are in
`llm_loop_transcript.jsonl` and `.meta.json`.

## Use

```python
from gen_2412_14615 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    parse_answer, render, verify,
)

inst = make_instance(seed=1234, **DIFFICULTY[SHIPPING_DIFFICULTY])
question = render(inst)
candidate = parse_answer("<answer>1, 7, 12; 2, 8, 19</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh verified shipping instances with:

```bash
bash scripts/emit.sh 2412.14615 20 medium
```

## Caveats

- No theorem proves average-case hardness for this planted projective
  distribution, nor does the cited NP-completeness result cover this exact
  induced-subgeometry subclass.  Hardness evidence is empirical.
- The 0/200,000 G4 result applies only to the uniform prior over exact triple
  partitions.  It is not a runtime lower bound and says nothing about a
  targeted algebraic, SAT, ILP, or exact-cover solver.
- The adversary panel tried degree/outlier scoring, left-to-right greedy,
  global line scoring, 64 randomized MRV restarts, and a 25,000-node MRV
  backtracker.  It did not try industrial DLX/SAT/ILP solvers, belief
  propagation, spectral recovery, or much larger search budgets.
- Plants use uniformly sampled coordinates and decoys are emergent lines among
  those same coordinates, so there is no explicit per-line marker.  Rejection
  on aggregate crowding and attack failure can still leave a higher-order
  planting signature not covered by the panel.
- One of three scored shipping-level oracle failures emitted no answer after
  exhausting 32k tokens; the two parsed invalid answers are stronger evidence.
- `canonical_key` is a color-refinement invariant of the point–line incidence
  hypergraph.  It is invariant under point renumbering, every invertible
  `GF(2)` basis change, and compositions tested in G8, but it is not an exact
  isomorphism algorithm; rare nonisomorphic instances may collide.
- Uniform full projective spaces, chain-type multisets, lower crowding, and
  small instances can be easy.  The named parameter window and generation
  guards are part of the family, not decorative defaults.
