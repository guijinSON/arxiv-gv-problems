# Generalized list T-coloring generator (arXiv:1311.0603)

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: one natural-number label per vertex |
| Intended intuition | invariant: quadratic residues of least permitted labels form independent buckets |
| Domain essentiality | native; no reduction |

This module generates the exact object defined in Section 2 of Junosza-Szaniawski and Rzążewski, [“An Exact Algorithm for the Generalized List T-Coloring Problem”](https://arxiv.org/abs/1311.0603): a graph, one finite permitted-label list per vertex, and one forbidden set of absolute label differences per edge. The solver returns one permitted label per vertex. Verification uses only integer list membership, absolute differences, and forbidden-set membership.

## Trust and hardness

Generation is inverse, not search. Choose a prime `p` and `q` balanced classes. For a sampled list minimum `x`, the class is

```text
floor(q * (x*x mod p) / p).
```

The permitted list is `x, x+p, ..., x+(q-1)p`, and the planted answer uses the class position. Edges are sampled only between different classes. An edge with endpoint minima `x` and `y` forbids `{0, |x-y|}`. Because `0 < |x-y| < p`, that second value occurs between endpoint labels exactly when their list positions are equal. Thus every planted answer is certified before the graph is built. G1 also checked this identity for all 132,156 edge/position pairs arising from four seeds at every preset.

This is a Track-B family, not an average-case complexity claim. Section 3, Theorem 1 gives `Solve-GLTC` time `O*((tau+2)^n)`, and Section 3.1 improves the base using star or clique packings. The Introduction identifies the all-`t(e)={0}` list-coloring case as solvable in `O*(2^n)`; this generator avoids that case because every edge has a nonzero forbidden difference. At the shipping preset, the executable exact DSATUR reference solves 8/8 instances with a median 118 search nodes, 6,669 counted operations, and about 0.001 seconds. That is efficient with code but not mechanically executable inside the no-tool prompt. Recognizing the residue invariant reduces the intended route to 160 exact arithmetic operations. The bare oracle result is 0/3 at shipping size.

## Worked demo

This is the complete instance from `make_instance(seed=7, **DIFFICULTY["demo"])`:

```text
Find a proper generalized list T-coloring of the finite graph below.

Definitions and conventions:
- The vertices are the integers 0 through 5, inclusive; all indexing is 0-based.
- Every vertex line gives its complete increasing list of permitted natural-number labels.
- Every undirected edge line has the form 'u v: d1,d2,...' and gives its complete set of forbidden differences. There are no loops or parallel edges, and unlisted vertex pairs are nonedges.
- Choose exactly one integer label phi[i] from vertex i's permitted list. Repeats are allowed only when all constraints permit them.
- For every listed edge u v, the ordinary integer absolute difference |phi[u]-phi[v]| must not equal any displayed forbidden difference for that edge. There is no modular arithmetic in this validity check.
- Every permitted list has q=3 entries and common successive gap p=17; these are exact summaries of the displayed lists, not extra constraints.
- Return exactly 6 labels in vertex order 0,1,...,5.

VERTICES
0: 12,29,46
1: 3,20,37
2: 16,33,50
3: 4,21,38
4: 9,26,43
5: 1,18,35

EDGES AND THEIR FORBIDDEN DIFFERENCES
0 2: 0,4
0 3: 0,8
0 4: 0,3
0 5: 0,11
1 2: 0,13
1 3: 0,1
1 4: 0,6
1 5: 0,2
2 3: 0,12
2 4: 0,7
3 5: 0,3
4 5: 0,8

Give your final answer inside <answer></answer> tags, as exactly 6 comma-separated base-10 integers in vertex order.
Example syntax only: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

Squaring the six list minima modulo 17 gives bucket positions `1,1,0,2,2,0`, so a hand-solvable answer is `<answer>29, 20, 16, 38, 43, 1</answer>`. `verify` returns `(True, "ok")`. Changing the first label to 46 returns `(False, "edge 1 (0,3) has forbidden difference 8")`.

## Difficulty presets

| preset | n | q | prime floor | cross-class edge rate | status |
|---|---:|---:|---:|---:|---|
| demo | 6 | 3 | 17 | 2/3 | hand example; hardener skips it |
| easy | 24 | 4 | 43 | 2/5 | solved 3/3 by the oracle |
| medium | 40 | 5 | 67 | 1/3 | **shipping; held 0/3** |
| hard | 74 | 6 | 127 | 7/25 | locally verified; not needed after medium held |

`escalate` keeps the witness length fixed while increasing the residue modulus and gently increasing edge crowding. It therefore grows the arithmetic haystack before lengthening the answer.

## Gate results

| gate | measured result at the shipping preset unless noted |
|---|---|
| G1 | 16/16 planted witnesses; 132,156/132,156 construction-identity checks |
| G2 | 5/5 corruption classes rejected with five distinct diagnostics |
| G3 | model-style tagged prose round-tripped all 40 labels |
| G4 | 0/200,000 valid structure-aware guesses from the exact `5^40` list product |
| G5 | shipping density 0/200,000; demo exact count 6/729; strongest spectral probe failed after 80 power iterations × 12 k-means starts in 0.062 s |
| G6 | degree residue, raw magnitude buckets, left-to-right greedy, 32 greedy restarts, affine minima, and spectral clustering each solved 0/8; exact DSATUR solved 8/8 |
| G7 | doubled `n=80` instance built and verified, with 904 edges |
| G8 | 120/120 invariance and 120/120 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 149 characters, about 38 tokens, 40 atoms, and 160 intended operations |

## Oracle loop

The repository’s current hardener used its configured Google/OpenAI pool. All replies below are harness-owned evidence in `llm_loop_transcript.jsonl`.

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 2139562501 | solved | verified witness |
| easy | GPT-5.6 Terra | 1578759458 | solved | verified witness |
| easy | GPT-5.6 Terra | 872555501 | solved | verified witness |
| medium | Gemini 3.8 Flash | 1759871300 | failed | reasoning exhausted the 32k output budget; no witness |
| medium | GPT-5.6 Terra | 1329535604 | failed | edge 95 had forbidden difference 21 |
| medium | GPT-5.6 Terra | 1192020217 | failed | edge 41 had forbidden difference 6 |

## G9 diagnostic arms

| arm | usable solved/attempts | outcome |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 0/0 | four redraws failed with OpenRouter HTTP 403 key-limit errors |
| placebo hint | 0/0 | four redraws failed with the same HTTP 403 error |

The stored hinted-minus-placebo value is `0.0` only as the module’s zero-attempt sentinel; it is not an estimate. No conclusion about hint responsiveness is warranted until those two arms are rerun with restored quota. The structural hint names only the invariant, not the procedure. These arms are diagnostic and non-gating; G9(c) passes with the sizes above.

## Use

```python
from gen_1311_0603 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
prompt = render(inst)
wire = "<answer>" + ",".join(map(str, inst["answer"])) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1311.0603
```

## Caveats

The `0/200,000` estimate concerns uniform independent choices from the displayed permitted lists. It does not estimate success for a solver exploiting the graph or the residue invariant. The family is deliberately easy for exact DSATUR and for a solver that discovers the compact rule; that is the Track-B claim. The paper’s star/clique-packing refinements likely apply because these random graphs have large matchings, although they remain exponential algorithms.

The attack panel did not run an industrial SAT/CP-SAT package, semidefinite relaxations, or every spectral variant. The canonical key handles vertex/input permutation, storage reordering, global label translation and reflection, and their compositions; it does not identify every conceivable non-affine relabeling of the finite label universe. Finally, the structural and placebo oracle diagnostics have no usable attempts because quota was exhausted after the valid bare run; their transcripts preserve the errors rather than misreporting them as failures.
