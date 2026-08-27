# Binary-lamp quotient-sum witnesses

This is a concrete witness family from [*Orientable quadratic equations in wreath products*](https://arxiv.org/abs/2503.01929). A solver receives labelled interval lengths and separated target blocks on the integer line. It must give one distinct integer shift per interval so that their pointwise XOR is exactly the target. Verification does not read the planted answer: because total interval length equals target support, it sorts the translated intervals by block and checks exact, disjoint coverage. Finding a witness is an exact-cover problem; checking one is cheap.

## Why this is the hard regime

Section 3.2 defines the quotient-sum problem. This module fixes the paper's binary lamps and integer translations, \(A=\mathbb Z_2\), \(B=\mathbb Z\), and quotient-rank bound \(h=0\), with the target translation normalized away. In Section 4.1, Proposition 4.2 reduces 3-PARTITION to exactly this construction: interval lamps must tile equal blocks separated by one unlit coordinate. Theorem 4.3 then proves \(\mathsf{QSP}(A,B,\cdot,0)\) NP-hard for nontrivial finitely generated abelian \(A\) and infinite finitely generated abelian \(B\).

The exclusions matter. Theorem 4.4 puts finite \(B\) in P; Theorem 4.20 puts \(h\geq\operatorname{rank}(B)\) in P; Theorems 4.23 and 4.24 put one function and any fixed bound on the function count in P. Here \(B=\mathbb Z\) is infinite, \(h=0<\operatorname{rank}(B)\), and the function count grows with \(n\). Section 5 gives the corresponding equation-side easy regimes: genus \(g\geq\operatorname{rank}(B)/2\) (Corollary 5.4) and bounded conjugate count (Corollary 5.6).

## Worked example

<details>
<summary>Smallest preset: <code>easy</code>, seed <code>8101</code> (full rendered instance)</summary>

```text
Binary-lamp quotient-sum witness problem

All coordinates below are integers.  A binary lamp configuration is a function
from the integers to {0,1} with only finitely many 1s.  Configurations are
added pointwise modulo 2 (XOR): at every coordinate, an even number of 1s sums
to 0 and an odd number sums to 1.

There are 30 labelled interval configurations.  Item i has the
positive length shown below and initially has value 1 exactly at coordinates
0, 1, ..., length_i-1.  Choosing its integer shift s_i translates those 1s to
the CLOSED interval [s_i, s_i + length_i - 1].

The target configuration is 1 exactly on these 10 CLOSED blocks:
[0, 199], [201, 400], [402, 601], [603, 802], [804, 1003], [1005, 1204], [1206, 1405], [1407, 1606], [1608, 1807], [1809, 2008]
It is 0 at every other integer coordinate.  Consecutive target blocks are
separated by exactly the one-coordinate gap visible in their endpoints.

Find one shift for every item such that the XOR sum of all shifted interval
configurations equals the target at every integer coordinate.

Conventions and constraints:
- Items are labelled 1 through 30 in the order listed below.
- The answer is an ordered JSON list [s_1, ..., s_30]; list position
  i corresponds to labelled item i.  Reordering entries changes the answer.
- Every shift is an integer in the inclusive range 0 through 2008.
- All shifts must be distinct; repeated shifts are forbidden.
- Intervals are closed at both ends.  Coordinates and shifts are 0-based.
- Every item is used exactly once.  No item may be omitted or repeated.

Target block length T: 200
Item lengths (label: length):
1: 95
2: 53
3: 51
4: 67
5: 64
6: 52
7: 51
8: 56
9: 83
10: 67
11: 90
12: 54
13: 57
14: 56
15: 94
16: 54
17: 59
18: 94
19: 58
20: 79
21: 87
22: 79
23: 65
24: 79
25: 59
26: 54
27: 80
28: 51
29: 55
30: 57

Give your final answer inside <answer></answer> tags, as one JSON list of exactly
30 distinct integers in item-label order.
Example format: <answer>[0, 17, 42]</answer>
Output nothing else inside the tags.
```

</details>

```python
from gen_2503_01929 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=8101, **DIFFICULTY["easy"])
answer = [0, 1286, 95, 1084, 682, 295, 496, 948, 1809, 1339,
          1407, 146, 746, 1695, 201, 347, 1548, 402, 1892, 603,
          1608, 804, 883, 1005, 1950, 1151, 1206, 1497, 547, 1751]
verify(inst, answer)
# (True, "ok")

verify(inst, answer[:-1])
# (False, "wrong_length_expected_30_got_29")
```

## Difficulty presets

| Preset | Blocks \(n\) | Items | `width_factor` | Oracle | Cheap-attack gate | Disposition |
|---|---:|---:|---:|---:|---|---|
| `easy` | 10 | 30 | 0.5 | solved 3/3 | not needed after oracle failure | rejected by oracle gate |
| `medium` | 20 | 60 | 0.5 | solved 0/3 | degree 0/8; largest-first 0/8; 256-restart 1/8 (seed 6) | rejected by G6 |
| `hard` | 32 | 96 | 0.5 | solved 0/3 | all three attacks 0/8 | **ships** |

## Measured gates

| Gate | Result | Measurement from `selftest_report.json` |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset-seed cases |
| G2 rejects corruption | pass | 5/5 rejected: `wrong_length_expected_96_got_95`, `overlap_in_block_24_at_coordinate_50323`, `duplicate_shift_at_items_1_and_2`, `empty_answer`, `shift_out_of_range_at_item_1` |
| G3 round trip | pass | parsed length 96 |
| G4 guess resistance | pass | 0/200000 hits; empirical probability 0.0; shipping syntactic space has bit length 1536 |
| G5 sparse | pass | at \(n=4\): 1119744 valid / 2140156846430076578936832000 syntactic candidates = 5.232065125823872e-22 |
| G6 adversary panel | pass | degree 0/8; largest-first 0/8; 256-restart 0/8 |
| G7 scales | pass | \(n\) 32→64, items 96→192, search-space bits 1536→3648; doubled verify `(True, "ok")` |
| Overall | **pass** | `all_pass: true` |

## Oracle loop

The oracle was `openai/gpt-5.6-terra` at medium reasoning effort through OpenRouter; all replies parsed. Verifier reasons, and the verbatim replies, are in [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl).

| Preset | Seed | Solved | Why |
|---|---:|---:|---|
| `easy` | 8101 | yes | `ok` |
| `easy` | 8102 | yes | `ok` |
| `easy` | 8103 | yes | `ok` |
| `medium` | 8201 | no | `empty_answer` |
| `medium` | 8202 | no | `wrong_length_expected_60_got_59` |
| `medium` | 8203 | no | `empty_answer` |
| `hard` | 8301 | no | `wrong_length_expected_96_got_97` |
| `hard` | 8302 | no | `interval_crosses_block_boundary_at_item_4` |
| `hard` | 8303 | no | `wrong_length_expected_96_got_94` |

## How to use it

```python
import gen_2503_01929 as family

inst = family.make_instance(**family.DIFFICULTY[family.SHIPPING_DIFFICULTY])
question = family.render(inst)            # give only this to the solver
candidate = family.parse_answer(solver_reply)
ok, reason = family.verify(inst, candidate)
```

From the repository root, emit the shipping preset with:

```bash
bash scripts/emit.sh 2503.01929
```

## Caveats

The theorem is worst-case hardness for QSP, not a proof that this inverse-generated satisfiable distribution is hard. The public interval lengths expose a sum-to-target hypergraph, so a strong exact-cover/SAT/ILP solver may succeed. Instances also become easy if `inst["answer"]` is leaked (only `render(inst)` is solver-safe), if planting makes the intended triples statistically identifiable, if the sum-triple graph is greedily peelable, or if the function count is fixed. The symmetric sampler and label shuffle address obvious plant/decoy leakage, but do not prove its absence.

`P(guess) = 0.0` means only that none of the 200000 candidates drawn uniformly from ordered vectors of distinct in-range shifts verified. That prior puts almost all mass on geometrically impossible placements; it says nothing about an informed prior over block-respecting triples, and zero hits is not a zero true probability. G5's exact fraction is only for \(n=4\), not the shipping instance.

Attacks tried were per-item sum-triple degree propagation, largest-first greedy packing, and 256 compatible-triple random restarts. I did **not** try Algorithm X/backtracking, SAT/SMT/ILP, meet-in-the-middle or dynamic programming, stronger local search, solver-assisted or tool-using LLMs, or a distributional leakage classifier. The oracle's 0/3 hard solves and these 0/8 cheap-attack results are useful smoke tests, not cryptographic or average-case evidence.
