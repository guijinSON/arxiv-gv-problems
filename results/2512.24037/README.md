# Symmetry-hidden Kidney Exchange cycle cover

**Outcome: `cap_bound` (parked, not rejected, not shipped).** The family is
generatable and exactly verifiable, and every local gate passes, but the oracle
pool solved every rung through the 252-atom ceiling. A larger instance would
require more than the permitted 256 answer atoms. There is therefore no honest
`SHIPPING_DIFFICULTY` backed by a hardened oracle result; the module retains
`easy` as the preset used for local gate measurements only.

| Profile axis | Declaration |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate form | integer tuple (canonical partition into triples) |
| Native objects | directed kidney-compatibility graph; directed 3-cycles |
| Intended intuition | symmetry: recover an order-three modular block shift |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This is the cycle-only special case of Definition 1 in Banik, Bhore, Dey, and
Sahu, [*Kidney Exchange: Faster Parameterized Algorithms and Tighter Lower
Bounds*](https://arxiv.org/abs/2512.24037). Vertices are patient–donor pairs and
an arc `u -> v` says that `u`'s donor is compatible with `v`'s patient. There are
no altruists or chains. The solver must partition every vertex into directed
cycles of length three. The checker verifies JSON shape, integer bounds,
disjoint full coverage, and the three required arcs of each cycle; it accepts
any valid cover and never reads the planted answer.

Generation is inverse. Two modular offsets define a fixed-point-free
order-three permutation across three consecutive vertex blocks. Its orbits are
the answer before noise exists. Every noise arc is added with both of its
permutation images, in regular permutation layers, so the orbit triangles
remain valid and every vertex has the same in/out degree. A bounded Algorithm-X
screen discards quickly solved draws but never produces the certificate.

## Why Track B, and what the paper says is easy

An efficient algorithm exists and is disclosed: tally offsets of arcs from
block 0 to 1 and from block 1 to 2, take each unique modal offset, and list the
resulting order-three orbits. This is `O(|A| + n)`. At the local `easy`
measurement (216 vertices and 2,592 arcs), it used 4,020 counted integer/index
operations and 0.00089 s; across eight adversarial seeds it solved 8/8 in 33,564
operations and 0.00799 s. The compact route intersects the small offset sets of
four representative vertices and advances 72 orbits twice: 159 modular group
operations. A no-tool model cannot mechanically tally thousands of arcs, but it
can execute the compact route if it notices the symmetry. The oracle results
show that the current pool notices it too often, which is why this family is
parked.

Section 3, Theorem 1 gives a deterministic
`O*((4e)^t) ≈ O*(10.88^t)` color-coding/subset-DP algorithm, so the generator
does not use small `t`: it sets `t = |V| = 3n`. Section 1.1 notes FPT for the
combined structural-width and length parameters; structural width is not held
fixed here. Section 1.2 cites Abraham–Blum–Sandholm Theorem 1, which proves
NP-completeness of perfect directed cycle cover for every maximum length
`L >= 3`; this family uses `L = 3`. The worst-case theorem is context, not a
false Track-A claim; hardness here is only the measured Track-B gap.

The new constant-path result in Section 6 is deliberately not used. As written,
it conflicts with Definition 1 by counting altruists in `t`, treating path
vertex count as edge length, and calling `B' = 31B` constant. The generator
therefore rests on the paper's exact Definition 1 and its cited short-cycle
regime.

## Worked demo

The complete `demo` instance at seed 7 is hand-solvable:

```text
Kidney exchange -- perfect directed 3-cycle cover

There are 9 patient-donor pairs, numbered 0 through 8, and no altruistic donors.
An arc u -> v means u's donor is compatible with v's patient. Find 3 disjoint
directed 3-cycles covering every vertex. The complete adjacency list is:

0: 4
1: 5
2: 3
3: 7
4: 8
5: 6
6: 1
7: 2
8: 0

Return a lexicographically sorted JSON list of increasing triples inside
<answer></answer> tags.
```

The answer is
`<answer>[[0,4,8],[1,5,6],[2,3,7]]</answer>`, and `verify` returns
`(True, "ok")`. Corrupting the first row to `[0,4]` returns
`(False, "cycle 0 has 2 vertices; expected 3")`.

## Presets

| Preset | Cycles | Vertices | Regular degree | Algorithm-X screen | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 3 | 9 | 1 | none | hand illustration |
| `easy` | 72 | 216 | 12 | 50,000 nodes | solved 2/3; local measurement preset |
| `medium` | 76 | 228 | 12 | 100,000 nodes | solved 2/3 |
| `hard` | 81 | 243 | 12 | 200,000 nodes | solved 2/3 |
| escalated | 81 | 243 | 13 | 400,000 nodes | solved 2/3 |
| escalated | 81 | 243 | 14 | 800,000 nodes | solved 2/3 |
| escalated | 84 | 252 | 14 | 800,000 nodes | solved 1/3; next step exceeds cap |

## Local gates

| Gate | Measurement | Result |
|---|---|---|
| G1 | 4 presets × 4 seeds; 16/16 planted covers verified | pass |
| G2 | drop, membership swap, duplicate, empty, out-of-range; five distinct reasons | pass |
| G3 | tagged fenced JSON round-trips; garbage returns `None`; answer is JSON-native | pass |
| G4 | structure-aware full triple partitions: 0/200,000 valid | pass |
| G5 | shipping-candidate density 0/200,000; Algorithm X 50,001 nodes/0.887 s without a cover; reference decoder 4,020 ops/0.00089 s | pass |
| G6 | five attacks, each 0/8; reference decoder 8/8 | pass |
| G7 | doubled `n=144`: 432 vertices, 5,184 arcs, witness verifies | pass |
| G8 | 80/80 relabelling/carried-witness checks; 20/20 unrelated keys distinct | pass |
| G9(c) | 899 chars, about 225 tokens, 216 atoms, 159 intended modular operations | pass |

Full measurements are in `selftest_report.json`.

## Oracle loop

The bare run used master seed `5968893335857329425`, medium reasoning, and the
repository's current OpenAI/Gemini pool. “Failed” means a parsed witness was
rejected, not an API failure.

| Round/preset | Seed | Model | Solved | Verification result |
|---|---:|---|---|---|
| 0 / easy | 694896992 | Gemini 3.8 Flash | yes | ok |
| 0 / easy | 976523314 | GPT-5.6 Terra | yes | ok |
| 0 / easy | 1817139647 | GPT-5.6 Terra | no | 0 cycles, expected 72 |
| 1 / medium | 232056400 | GPT-5.6 Terra | yes | ok |
| 1 / medium | 566517542 | Gemini 3.8 Flash | yes | ok |
| 1 / medium | 402041435 | GPT-5.6 Terra | no | 21 cycles, expected 76 |
| 2 / hard | 1389480768 | Gemini 3.8 Flash | yes | ok |
| 2 / hard | 1713246083 | GPT-5.6 Terra | no | 39 cycles, expected 81 |
| 2 / hard | 735558679 | Gemini 3.8 Flash | yes | ok |
| 3 / degree 13 | 1921669163 | GPT-5.6 Terra | no | first triple not a cycle |
| 3 / degree 13 | 1319373646 | Gemini 3.8 Flash | yes | ok |
| 3 / degree 13 | 2088089835 | Gemini 3.8 Flash | yes | ok |
| 4 / degree 14 | 1657083679 | GPT-5.6 Terra | yes | ok |
| 4 / degree 14 | 75817435 | Gemini 3.8 Flash | yes | ok |
| 4 / degree 14 | 1104931460 | Gemini 3.8 Flash | no | 82 cycles, expected 81 |
| 5 / n=84 | 1866144917 | Gemini 3.8 Flash | yes | ok |
| 5 / n=84 | 2098867805 | GPT-5.6 Terra | no | 122 cycles, expected 84 |
| 5 / n=84 | 1778432322 | GPT-5.6 Terra | no | 0 cycles, expected 84 |

The script-owned verdict in `.meta.json` is `cap_bound` after five
escalations. The full replies and timings are in `llm_loop_transcript.jsonl`.

## G9 arms

| Arm | Solved/attempts | Interpretation |
|---|---:|---|
| bare (`easy`) | 2/3 | the unhinted symmetry is already recognized too often |
| structural hint | not run | terminal `cap_bound` rule says report and stop |
| placebo hint | not run | terminal `cap_bound` rule says report and stop |

Because hinted and placebo arms were not run, `hinted − placebo` is undefined;
the JSON stores `0.0` only as a neutral placeholder and labels the hinted verdict
`not_run_cap_bound`. No `g9_*_transcript.jsonl` files were fabricated.

## Use

```python
from gen_2512_24037 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

For diagnostic emission from the repository root:

```bash
bash scripts/emit.sh 2512.24037 20 easy
```

Do not submit this result as a hardened family; it is parked at the answer cap.

## Caveats

- The labels encode the Track-B offset. That is intentional and fully disclosed;
  it also explains why the oracle pool solved the family. This is not Track A.
- G4 samples uniformly from all canonical partitions into triples, already
  enforcing arity, disjointness, coverage, and order. It does not condition each
  triple on being a graph cycle, because completing such triples is the exact-cover
  task. Zero hits is an observed rate, not an exact density or confidence bound.
- The 50,000-node Algorithm-X attack is bounded and the generator conditions on
  its failure. Unbounded Algorithm X, ILP/CP-SAT, branch-and-price, SAT encodings,
  and LP relaxations were not benchmarked. The polynomial symmetry decoder makes
  those omissions irrelevant to the Track-B honesty claim but relevant to generic
  exact-cover performance.
- The canonical key uses triangle-support-seeded directed color refinement and
  is not a complete graph-isomorphism algorithm; collisions are theoretically
  possible despite the 20/20 distinctness test.
- The paper's Section 6 issues noted above may be authorial off-by-one/notation
  errors, but no correction or later version was available in the audited v1.
