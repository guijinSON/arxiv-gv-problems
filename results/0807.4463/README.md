# Dense tripartite triangle factors (arXiv:0807.4463)

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer tuple: two permutations encoding a triangle factor |
| Intuition | invariant — align the common tag residue coordinate |
| Domain essentiality | native |
| Reduction | none |

## What the family is

Csaba and Mydlarz's [Approximate Multipartite Version of the Hajnal--Szemerédi Theorem](https://arxiv.org/abs/0807.4463) studies clique factors in dense balanced multipartite graphs. This module hands the solver a balanced tripartite graph as three exact adjacency-bit matrices. The answer is two permutations `B` and `C`; row `a` represents the triangle `(A[a], B[B[a]], C[C[a]])`. Verification checks both permutations and performs three adjacency lookups per row, so every valid factor—not just the planted one—is accepted.

Generation is inverse. Each bipartite graph is a regular cyclic-difference graph whose difference set contains zero. Independently shuffled public tags encode the hidden cyclic coordinate. Matching equal coordinates therefore gives a triangle factor by construction. At `q=3`, Theorem 3's constant is `(29/12)/(41/12) = 29/41`; every generated vertex has at least `ceil(29n/41)` neighbours in each other part.

## Why Track B, not Track A

Section 3 explicitly describes a randomized embedding algorithm. Section 3.1's Factor Finder reduces the `q=3` cluster problem to regular bipartite subgraphs (Theorem 6) and perfect matchings (Lemma 5), while Lemma 16 licenses the recursion for larger `q`; the final stage uses the Blow-up Lemma, whose algorithmic version is reference [5]. Thus claiming unknown algorithmic hardness would be false. The easy `q=2` case is just perfect matching, and the paper also notes sharper special results for `q=3,4`.

For this generated distribution, the measured graph-only reference enumerates triangles and runs exact-cover backtracking. On the shipping instance it used 1,836,548 operations and 122 search nodes in 0.163 s; over eight seeds it solved 8/8. A graph-aware randomized valid-triangle greedy also solved 8/8, using 22,704,267 edge probes and 39 restarts in aggregate. These are computer routes, not Track-A failures. The compact route is to discover that all three tag lists share residues modulo 997, align equal residues, and write the two permutations. It needs 249 exact modular reductions at shipping size—under the 300-operation cap, but not a realistic unaided mechanical calculation over 83 rows.

## Worked demo

This is `make_instance(n=5, tag_bits=3, degree_extra=0, seed=7)` in full:

```text
Triangle factor in a dense balanced tripartite graph

The graph has three disjoint parts A, B, and C, each with 5 vertices.
Within each part the vertices are indexed 0 through 4.
Edges occur only between different parts. Every vertex has an integer tag.

Tags:
A: 3990 6982 6983 3989 4985
B: 3991 4987 6983 3989 3988
C: 3991 4987 5982 6980 5986

AB:
0: 11101
1: 10111
2: 01111
3: 11110
4: 11011

AC:
0: 11110
1: 11011
2: 11101
3: 01111
4: 10111

BC:
0: 11011
1: 11110
2: 11101
3: 01111
4: 10111
```

The answer is:

```json
{"B":[1,0,2,3,4],"C":[1,0,4,3,2]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the first B entry by the second produces `{"B":[0,0,2,3,4],"C":[1,0,4,3,2]}` and returns `(False, "B must be a permutation with no repeated or omitted vertex")`. A person can solve this demo on paper either by inspecting the five-bit matrices or by reducing the fifteen small tags modulo 997.

## Difficulty presets

| preset | class size `n` | tag bits | degree above `ceil(29n/41)` | status |
|---|---:|---:|---:|---|
| demo | 5 | 3 | 0 | hand-scale illustration; not hardened |
| easy | 83 | 48 | 4 | **shipping; bare and hinted hardened** |
| medium | 89 | 72 | 2 | available; not needed by the oracle ladder |
| hard | 97 | 96 | 0 | available; exact paper threshold |

No preset was rejected: the first evaluated rung held all three bare oracles.

## Gate results

| gate | result |
|---|---|
| G1 | 16/16 planted certificates verified; all answers JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | fenced tagged model-style response round-tripped |
| G4 | 0/200,000 valid structure-aware random candidates; observed fraction 0.0 |
| G5 | shipping baseline: 1,836,548 operations, 122 nodes, 0.163 s; demo has exactly 758 certificate strings |
| G6 | four attacks each 0/8; Algorithm X and graph-aware random greedy each 8/8 as Track-B references |
| G7 | doubled class size 166 built and verified; search-space bit length grew 828 to 1,980 |
| G8 | 40/40 relabelling invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 491 chars, 341 estimated tokens, 166 atoms; compact route 249 exact operations; hinted verdict hardened |

## Bare oracle loop

| preset | seed | model | solved | verifier result |
|---|---:|---|---|---|
| easy | 137498641 | x-ai/grok-4.6 | no | missing B-C edge in row 2 |
| easy | 102934326 | anthropic/claude-sonnet-5 | no | missing A-C edge in row 1 |
| easy | 321798748 | google/gemini-3.1-pro-preview | no | missing A-C edge in row 0 |

The harness verdict is `hardened` with zero escalations. Every nonempty reply contained parseable tagged JSON; these are verifier failures, not parser failures.

## G9 arms

| arm | solved/attempts | verdict/diagnostic |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; one empty length-limited response, two wrong factors |
| placebo hint | 0/3 | hardened; three wrong factors |

Hinted minus placebo is `0.0`. The named invariant did not improve the solve rate, suggesting that discovering the residue pattern is not the only obstacle: executing 249 exact reductions and transcribing 166 indices also matters. One Grok hinted call timed out at 900 s and was correctly redrawn; the error row remains in the transcript and does not count among the three attempts.

## Use

```python
import json

from gen_0807_4463 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
print(render(inst))
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = parse_answer(wire)
ok, reason = verify(inst, candidate)
```

From the repository root, emit corpus instances with:

```bash
bash scripts/emit.sh 0807.4463
```

## Caveats

This is deliberately easy with arithmetic or solver tools: the modulo-997 decoder is linear in the number of tags, graph-aware randomized greedy solved all eight measured seeds, and exact cover took fractions of a second. That is the Track-B premise. Theorem 3 has an unspecified asymptotic `n0`; finite correctness here comes from the planted factor, not from claiming that `n=83` exceeds `n0`.

The G4 prior is uniform over two complete permutations, incorporating all shape and cover constraints but no adjacency bias. Its 0/200,000 result is a sampled density observation, not a proof of uniqueness or a bound against informed graph search; the demo's 758 accepted certificates illustrates that factors need not be unique. The generator conditions public ordering against one lexicographic greedy rule. Tests did not include an external SAT/ILP solver or every possible randomized repair scheme; Algorithm X and graph-aware greedy are the principal domain baselines actually run.

Public tags are construction metadata rather than a concept in the paper, although the object being certified and exactly verified is still the paper's native tripartite graph and triangle factor. `canonical_key` treats tags as vertex attributes, normalizes arbitrary storage reorderings within each part, and keys on the resulting graph matrices; it is not a general untagged tripartite graph-isomorphism canonizer and does not identify instances whose tag values themselves are rewritten.
