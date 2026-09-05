# arXiv:2510.01949 — Hamilton-compatible bipartite matching

| Profile field | Value |
|---|---|
| Track | **B** — an efficient exact algorithm exists and is reported |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | permutation |
| Certificate form | exact symbolic permutation |
| Intended intuition | symmetry: a hidden cyclic translation action |
| Domain essentiality | native; no reduction |

This generator uses Glock and Sgueglia, [*On Kotzig's conjecture in random graphs*](https://arxiv.org/abs/2510.01949). It gives the solver perfect matchings of a complete balanced bipartite graph in the paper's Section 7 permutation representation. The answer is another permutation whose union with every given matching is one alternating Hamilton cycle and which contains one required edge. Grading is exact: check the permutation and required edge, invert each given permutation, and trace one cycle.

## Why this is trustworthy, and why it is Track B

Section 7 defines the native permutation model. Theorem 7.3 gives bipartite existence under the parity and exclusivity conditions, and Theorem 7.4 counts compatible matchings as
`Theta_k(n^(1/2-k) (n/e)^n)` under small overlap. Relative to the `n!` permutations, uniform sampling therefore needs `Theta_k(n^k)` trials for fixed `k`; conditioning both the candidate sampler and solution on the published edge preserves that `n^-k` scale. Section 4's switching result (Theorem 4.2), whose arguments Section 7 says carry to the bipartite setting, is the relevant roughly-uniform-edge fact. The easy regimes avoided are `k=2`: Section 1 gives a greedy construction in the ordinary setting, and Section 7 observes that the random bipartite case is just Hamilton-cycle search.

Track A would be false. On this generated distribution, cyclic-coset permutation normal forms solve exactly in `O(n^2+k*n)`: across eight shipping seeds the implementation solved 8/8 using 72,235 counted lookups, 9,029 per instance, in 0.0025 seconds total. The compact no-tool route is shorter: take any two supplied matchings, use their relative `n`-cycle as coordinates, locate the required edge in that cycle, and write the selected coset element. It needs five length-59 passes, or 295 exact lookups. The target and given translation indices are sampled exchangeably before construction; the answer is not found by solving the emitted instance.

## Worked demo

The `demo` preset is hand-solvable: its cyclic-coordinate route takes 35 lookups. For seed 0 the complete rendered problem is:

```text
HAMILTON-COMPATIBLE BIPARTITE PERFECT MATCHING

The complete balanced bipartite graph K_{7,7} has left vertices
L_0,...,L_6 and right vertices R_0,...,R_6.  A perfect matching
is represented by a permutation P of 0,...,6: its edge incident with
L_i is (L_i,R_{P[i]}).

Below are 4 given perfect matchings.  Each row is one permutation in
left-vertex order.  The row order has no mathematical significance.

M00: 1 2 6 5 0 3 4
M01: 4 1 3 2 5 0 6
M02: 3 6 5 4 1 2 0
M03: 6 4 0 1 2 5 3

Find one more perfect matching P such that, for every displayed M_j, the union
of P and M_j is one Hamilton cycle through all 14 vertices.  Equivalently,
start at any left vertex, alternately follow its P edge to the right and the
M_j edge backwards to the left: you must return to the start only after every
left vertex has been visited.  A shared edge is a 2-cycle and is invalid.

The new matching must also contain the required edge
(L_2,R_1), meaning
P[2] = 1.

Your answer must be one JSON list of exactly 7 integers.  It must contain
each integer from 0 through 6 exactly once; entry i is P[i].  Indices are
0-based, order matters, and repeats are forbidden.

Give your final answer inside <answer></answer> tags as that JSON list.
Example shape: <answer>[2,0,3,1,...]</answer>
Do not use the ellipsis in a real answer.  Output nothing else inside the tags.
```

The answer is `<answer>[5,0,1,3,6,4,2]</answer>`. `verify` returns `(True, "ok")`; dropping its last entry returns `(False, "answer has fewer than 7 entries")`.

## Difficulty and gates

The ladder was slid upward after the oracle run. The old `n=29,k=11`, `n=43,k=13`, and `n=59,k=15` rungs were also solved and removed.

| Preset | Bipartition size `n` | Given matchings `k` | Candidate space | Oracle status |
|---|---:|---:|---:|---|
| demo | 7 | 4 | `6!` | skipped; hand-scale |
| easy | 59 | 23 | `58!` | rejected, 2/3 solved |
| medium | 59 | 27 | `58!` | rejected, 1/3 solved |
| **hard (ships)** | **59** | **31** | **`58!`** | **held, 0/3 solved** |

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 plants and 12/12 composition identities |
| G2 | pass | five required corruptions rejected with five distinct reasons |
| G3 | pass | prose + fenced tagged JSON round-trips; garbage gives `None`; JSON-native |
| G4 | pass | 0/200,000 structure-aware guesses from permutations already containing the required edge |
| G5 | pass | shipping density 0/200,000; demo exact count 1; reference 72,235 lookups / 0.0025 s |
| G6 | pass | four attacks at 0/8; reference normal-form algorithm 8/8 |
| G7 | pass | `n=29` to doubled request `n=58` (next prime 59) enlarges the space and verifies |
| G8 | pass | 80/80 invariant keys, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 168 chars, about 42 tokens, 59 atoms, 295 intended lookups |

## Bare oracle loop

`SOLVED` means the returned permutation verified. A short reason is retained here; the full replies and provider metadata are in `llm_loop_transcript.jsonl`.

| Round / parameters | Seed | Model | Result | Why |
|---|---:|---|---|---|
| 0, `n=29,k=11` | 327725086 | Gemini | solved | verified |
| 0, `n=29,k=11` | 276434375 | Terra | solved | verified |
| 0, `n=29,k=11` | 396185691 | Gemini | failed | no final answer; length limit |
| 1, `n=43,k=13` | 1418203480 | Terra | solved | verified |
| 1, `n=43,k=13` | 490762325 | Gemini | failed | no final answer; provider finish error |
| 1, `n=43,k=13` | 2009498573 | Terra | solved | verified |
| 2, `n=59,k=15` | 980682922 | Terra | failed | early cycle with M01 |
| 2, `n=59,k=15` | 837839225 | Gemini | solved | verified |
| 2, `n=59,k=15` | 1583666091 | Terra | solved | verified |
| 3, `n=59,k=19` | 1848916557 | Terra | failed | early cycle with M01 |
| 3, `n=59,k=19` | 572637363 | Gemini | failed | no final answer; length limit |
| 3, `n=59,k=19` | 1234436188 | Terra | solved | verified |
| 4, `n=59,k=23` | 658620474 | Gemini | solved | verified |
| 4, `n=59,k=23` | 1007300590 | Terra | failed | early cycle with M01 |
| 4, `n=59,k=23` | 1310097765 | Gemini | solved | verified |
| 5, `n=59,k=27` | 1619985305 | Gemini | failed | early cycle with M00 |
| 5, `n=59,k=27` | 1301630679 | Terra | failed | early cycle with M00 |
| 5, `n=59,k=27` | 2050742977 | Terra | solved | verified |
| 6, `n=59,k=31` | 591223681 | Terra | failed | early cycle with M01 |
| 6, `n=59,k=31` | 71219766 | Gemini | failed | response ended before an answer |
| 6, `n=59,k=31` | 1654678478 | Terra | failed | early cycle with M00 |

## G9 diagnostic arms

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0/3 | shipping prompt held |
| structural hint | 3/3 | naming the cyclic action unlocks the compact route |
| placebo hint | 1/3 | prompt perturbation alone occasionally helps |

The structural-minus-placebo rate is `1 - 1/3 = 0.667`. The strong effect supports the declared `symmetry` intuition: difficulty lies in finding the hidden cyclic action, not in executing an unknown long algorithm. The hinted arm is diagnostic, not a gate.

## Use

```python
from gen_2510_01949 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
prompt = render(inst)
text = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
candidate = parse_answer(text)
assert verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
scripts/emit.sh 2510.01949 20 hard
```

## Caveats

- This is a Track B recognition benchmark, not a hardness claim for the general completion problem. A permutation normal-form program solves every generated instance in fractions of a millisecond.
- G4 samples uniformly from all permutations already satisfying the obvious required-edge constraint. Its 0/200,000 result rules out blind guessing under that prior; it says nothing about the much stronger cyclic-coset prior, which is exactly the intended insight.
- Theorem 7.4 is asymptotic for fixed `k`; shipping treats `k=31` as that fixed constant. The prescribed-edge conditioning uses the Section 4 roughly-uniform-edge principle together with Section 7's statement that the arguments carry over, rather than a separately numbered bipartite prescribed-edge theorem. Correctness does not depend on that asymptotic inference because every witness is composed and checked exactly.
- The attacks cover row statistics, a paper-style no-backtracking greedy pass, 2,048 conditioned random restarts, and first-pair one-step extrapolation. No SAT/ILP encoding or large-scale general permutation-group package was run; the exact cyclic normal-form reference is stronger for this generated distribution.
- One of the three shipping failures exhausted its response before emitting tags. The other two emitted complete permutations that failed exact cycle checks, so the `hardened` verdict is not supported solely by output length.
- `canonical_key` is complete for the generated cyclic index representation up to affine renormalization and was tested under arbitrary independent vertex relabellings, matching reorderings, side swaps, and their composition. It is not advertised as a canonical form for arbitrary non-cyclic matching configurations.
