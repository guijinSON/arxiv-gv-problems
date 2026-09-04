# Verified generator for arXiv:1303.2162

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | integer lattice |
| Computational core | CSP/SAT |
| Certificate | exact symbolic decoder set |
| Intended intuition | reduction recognition |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 3 Definition 3 and Lemma 3 |

This module implements the **Min Segment Hitting** problem used as the hardness
source in Section 3 of Durocher and Mehrabi,
[“New Hardness Results for Guarding Orthogonal Polygons with Sliding
Cameras”](https://arxiv.org/abs/1303.2162). The solver receives horizontal closed
unit segments with integer endpoints and must give a compact recipe for horizontal
and vertical lines hitting all of them. The recipe expands to the exact
Hassin–Meggido variable and clause lines used by the paper's reduction. This is
licensed-reduction coverage of the paper, not a claim that the module hands the
solver the final polygon-with-holes MCSC instance.

## Why it can be trusted

Generation is inverse: sample a balanced bit vector first, compute the right-hand
sides of a full-rank XOR system, encode every XOR as four 3-CNF clauses, and map
those clauses to the cited six-segment variable and five-segment clause gadgets.
No generated instance is solved to obtain the answer.

The checker validates the answer's shape, expands it to exactly 3n+2m hitting
lines, reconstructs the clauses independently from the rendered coordinates, and
checks every closed line/segment intersection using integers. It never reads the
stored planted answer.

## Why Track B, not Track A

Section 3 Definition 3 states Min Segment Hitting, cites its NP-completeness, and
Lemma 3 carries it into MCSC with holes. That worst-case theorem does **not** make
this generated distribution hard. These instances have an efficient
construction-aware solver: group the four clauses sharing a variable triple,
recover one GF(2) equation per group, and use Gaussian elimination. Its complexity
is O(n^3); at shipping n=96, the reference implementation solved 8/8 and used a
median 65,222 counted bit operations in 0.000804 s.

The no-tool route is shorter only after recognizing more structure: peel the
scrambled chain down to its five-variable circulant core, solve that core, and
propagate back. It needs 192 XORs at shipping size. That fits the 300-operation
cap but is unpleasant to execute unaided across 96 scrambled indices. The paper's
easy results were handled explicitly: Section 2 Theorem 2 makes minimum-length
sliding cameras polynomial-time by weighted bipartite vertex cover; the
vertical-only simple-polygon case is polynomial, and the cited x-monotone MCSC
case has a 2-approximation. This family makes no Track A claim about any of them.

## Worked demo

The demo preset with seed 0 is hand-scale: there are only C(6,3)=20 permitted
decoder sets, so a person can check them on paper. This is the complete rendered
instance:

~~~text
MINIMUM HITTING OF HORIZONTAL UNIT SEGMENTS (compressed witness)

For integers a,b, the notation [a,b] below means the closed horizontal unit
segment from (a,b) to (a+1,b). A horizontal line H(y) hits [a,b] exactly when
y=b. A vertical line V(x) hits it exactly when a <= x <= a+1. Endpoints count.

The instance has n=6 variable gadgets, m=24 clause gadgets, and asks for the
following exactly specified set of 66 axis-parallel hitting lines. To keep the
witness writable, submit the decoder set T rather than listing all lines: T must
contain exactly 3 distinct indices from 1..6. Indices are 1-based and must be
written in strictly increasing order.

Coordinate frame: X(t)=0+(1)*t and Y(t)=0+(1)*t.

Decoder. For each i=1..n put r=i-1. If i is in T, include
H(Y(4r+2)), V(X(8r+3)), V(X(8r+7)); otherwise include
H(Y(4r+3)), V(X(8r+2)), V(X(8r+6)).

There are m clause gadgets numbered j=0..m-1. Put c=8n+6j. Their three
literal segments are the listed segments whose canonical left x-coordinates are
c+1,c+3,c+5 (positions 1,2,3). A position is already hit horizontally if its y
equals one of the decoded H-lines. Let p be the first such position. If no p
exists, T is invalid. Add two vertical lines for the gadget as follows:
  p=1: V(X(c+3)), V(X(c+5))
  p=2: V(X(c+2)), V(X(c+5))
  p=3: V(X(c+2)), V(X(c+4)).

The complete decoded line set must hit every listed segment. The checker expands
the recipe and tests every intersection using exact integer comparisons. Any T
whose decoded lines satisfy this condition is accepted.

Segments (input order is immaterial):
  [1,2] [2,4] [3,3] [5,2] [6,1] [7,3] [9,6] [10,8] [11,7] [13,6] [14,5] [15,7]
  [17,10] [18,12] [19,11] [21,10] [22,9] [23,11] [25,14] [26,16] [27,15] [29,14]
  [30,13] [31,15] [33,18] [34,20] [35,19] [37,18] [38,17] [39,19] [41,22] [42,24]
  [43,23] [45,22] [46,21] [47,23] [49,23] [50,-1] [51,3] [52,-2] [53,6] [55,15]
  [56,-3] [57,23] [58,-4] [59,6] [61,14] [62,-5] [63,2] [64,-6] [65,19] [67,18]
  [68,-7] [69,15] [70,-8] [71,10] [73,19] [74,-9] [75,6] [76,-10] [77,15] [79,19]
  [80,-11] [81,14] [82,-12] [83,10] [85,2] [86,-13] [87,6] [88,-14] [89,22] [91,7]
  [92,-15] [93,22] [94,-16] [95,15] [97,14] [98,-17] [99,6] [100,-18] [101,22]
  [103,15] [104,-19] [105,18] [106,-20] [107,2] [109,18] [110,-21] [111,11]
  [112,-22] [113,14] [115,18] [116,-23] [117,3] [118,-24] [119,23] [121,18]
  [122,-25] [123,3] [124,-26] [125,14] [127,7] [128,-27] [129,23] [130,-28]
  [131,14] [133,6] [134,-29] [135,14] [136,-30] [137,18] [139,23] [140,-31]
  [141,19] [142,-32] [143,2] [145,19] [146,-33] [147,3] [148,-34] [149,22]
  [151,18] [152,-35] [153,7] [154,-36] [155,15] [157,7] [158,-37] [159,2]
  [160,-38] [161,23] [163,3] [164,-39] [165,19] [166,-40] [167,15] [169,2]
  [170,-41] [171,18] [172,-42] [173,22] [175,7] [176,-43] [177,19] [178,-44]
  [179,14] [181,11] [182,-45] [183,19] [184,-46] [185,15] [187,22] [188,-47]
  [189,3] [190,-48] [191,7]

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 3 increasing 1-based indices, with no brackets.
Example format: <answer>1, 2, 3</answer>
Output nothing else inside the tags.
~~~

The answer is **<answer>1, 3, 4</answer>**.

~~~python
>>> verify(demo, [1, 3, 4])
(True, 'ok')
>>> verify(demo, [1, 3])
(False, 'wrong number of selected indices')
~~~

## Difficulty presets

| Preset | n | Segments | Decoded lines | Answer elements | Status |
|---|---:|---:|---:|---:|---|
| demo | 6 | 156 | 66 | 3 | hand-solvable illustration |
| easy | 96 | 2,496 | 1,056 | 48 | **ships; bare oracle hardened** |
| medium | 108 | 2,808 | 1,188 | 54 | available, not needed |
| hard | 120 | 3,120 | 1,320 | 60 | available, not needed |

No preset was rejected. The harness held the first tested rung, so escalating
would have replaced measured evidence with an unnecessarily larger transcription.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset–seed plants verify; 12/12 JSON round trips |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | 48-element realistic fenced response round-trips |
| G4 | pass | 0/200,000 balanced guesses; space C(96,48)=6.4350670138662989e27 |
| G5 | pass | shipping density 0/200,000; demo exactly 1; restart 4,608 iterations in 0.216859 s |
| G6 | pass | four attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | pass | doubled n=192 verifies; space grows from 92.378 to 187.880 bits |
| G8 | pass | 80/80 symmetry and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle 0/3; 145 chars, 37 tokens, 48 elements; 192 XORs |

The four failing G6 attacks were literal-frequency outlier selection,
best-improvement balanced swaps, 12 balanced stochastic restarts, and the
by-hand fixed-pattern ansatz (prefix, suffix, odd, or even indices).

## Oracle loop

| Preset | Model | Seed | Solved | Exact outcome |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 252714027 | no | parsed; missed clause gadget 11 |
| easy | Gemini 3.1 Pro Preview | 896830434 | no | parsed; missed clause gadget 32 |
| easy | Claude Sonnet 5 | 728505906 | no | empty length-limited response |

The script-owned verdict was **hardened** with zero escalations. The transcript,
including full replies and timing, is in llm_loop_transcript.jsonl.

## G9 arms

| Arm | Solved / counted attempts | Note |
|---|---:|---|
| bare | 0/3 | shipping transcript |
| structural hint | 0/3 | hardened; two parsed wrong answers and one length limit |
| placebo hint | 0/3 | two provider timeouts are recorded as errors and excluded |

Hinted minus placebo is **0.0**. In this three-attempt diagnostic the structural
hint bought no measurable success. That is consistent with the Track B claim:
execution across scrambled indices, rather than merely naming XOR structure,
appears to be the bottleneck; the sample is too small to establish that causally.

## Use

From this directory:

~~~python
from gen_1303_2162 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer("<answer>1, 2, 3</answer>")
ok, reason = verify(inst, candidate)
~~~

From the repository root, emit deterministic samples with:

~~~bash
bash scripts/emit.sh 1303.2162 20
~~~

The module uses only the Python standard library; gvlib is unnecessary because
all verification is Boolean and integer-coordinate exact.

## Caveats

- The generated distribution is efficiently solvable after parity recognition.
  It must not be cited as average-case or Track A hardness.
- The compact certificate language covers the exact Hassin–Meggido decoder
  family. It does not accept arbitrary raw lists of hitting lines, because those
  would exceed the 256-element answer cap; it does accept every valid decoder set
  (the system is unique on generated instances).
- P(guess) is conditional on the statement's strongest free constraint: a
  uniformly random sorted subset of exactly 48 indices. It says nothing about a
  solver prior informed by XOR recognition.
- The module covers the geometric source problem from Section 3, not the final
  orthogonal polygon with L-holes. Constructing the latter without directly
  checking continuous visibility would violate the witness rule, so the tempting
  “plant cameras, then shape a polygon” triage idea was not used.
- No external CDCL SAT solver or generic ILP/set-cover package was run. The exact
  XOR-aware Gaussian solver is more construction-aware and succeeds 8/8; the
  failing panel probes leakage and in-context heuristics, not tool-equipped
  hardness.
- Reflection/translation/input-order invariance is exact. Arbitrary geometric
  isomorphism is not canonicalized; the key uses the strongest cheap invariant
  tested here.
