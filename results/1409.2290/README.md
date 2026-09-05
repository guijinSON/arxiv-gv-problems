# arXiv 1409.2290 — exact spectral community certificate

| profile field | value |
|---|---|
| Track | **B** — polynomial-time exact linear algebra exists |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph (exact linear algebra is the reference algorithm) |
| Certificate form | integer tuple: normalized community bits |
| Intended intuition | invariant: switching bits cancel around an odd cyclic lift |
| Domain essentiality | native; no reduction |
| Shipping preset | **hard: `n=251`, externally hardened** |

## Problem and trust model

The source is [*Computational Complexity, Phase Transitions, and Message-Passing for Community Detection*](https://arxiv.org/abs/1409.2290). Section 5.1 defines the stochastic block model (SBM): sample latent vertex types, then sample edges with probabilities determined by those types. It also explains why the prior triage cannot be used literally: a realized graph does not determine its latent sample, and inference is through posterior marginals. Comparing a submitted labeling with hidden planted labels would violate the witness rule.

The module instead uses Section 5.2's native spectral objects. An instance is an exact regular cyclic two-lift of a complete graph, a target integer adjacency eigenvalue, and one redundant row-parity checksum. The answer gives one community bit per fibre and expands to a `+1/-1` vector on the graph. `verify` reconstructs the lift and checks `A x = lambda x` with exact integer sums; it never reads `inst["answer"]`. Generation samples the switching gauge first and builds every twist around it, so the certificate is known by inverse generation rather than recovery.

For prime fibre count `n`, the normalized witness is unique. Before switching, the signed fibre matrix is circulant. Equality between its row-sum eigenvalue and another Fourier eigenvalue would force a Laurent-polynomial difference to be a multiple of the prime cyclotomic polynomial; coefficient comparison contradicts the offset-sign pattern. Consequently the exact answer density is `2^-(n-1)`.

## Why Track B

This is not a distributional-hardness claim. Section 5.2 explicitly gives spectral diagonalization as the standard method. Here the exact reference algorithm forms the signed `n x n` fibre matrix and computes the nullspace of `M-lambda I` by modular Gaussian elimination. It is `O(n^3)`, solved 8/8 shipping instances, and averaged **15,917,420 modular operations / 1.106 s** in the final self-test.

The compact route is to notice that one offset row has `t_i = a_g XOR c_i XOR c_(i+g)`. Its supplied odd-cycle parity is `a_g`; one pass then propagates all community bits in **250 XOR/XNOR operations**. The checksum is exact redundant instance data, not a witness. Without the invariant, the obvious local and extremal-eigenvector heuristics fail, while full elimination is far beyond unaided in-context arithmetic.

The paper also identifies regimes that must not be misrepresented. For two equal SBM groups, recovery is impossible below `|lambda| sqrt(c)=1` and BP-like methods work above it. For more than four groups, the hard-but-detectable interval is described as a belief based on BP fixed points. Ordinary adjacency methods work in dense graphs but localize on high-degree structures in sparse `O(1)`-degree graphs, motivating the non-backtracking matrix. This family is a dense exact specialization, not a random SBM draw and not a Track-A claim.

## Worked demo

`make_instance(n=5, negative_offsets=1, seed=2)` renders:

```text
Exact two-community certificate in a cyclic two-lift

There are 10 vertices (i,b), where i is modulo n=5 and b is 0 or 1.
The output order is (0,0),(0,1),(1,0),(1,1), and so on.
The graph is specified by the twist rows below.  In a row g: t_0...t_{n-1},
bit t_i creates the two undirected edges
  {(i,0),((i+g) mod n,t_i)} and {(i,1),((i+g) mod n,1 XOR t_i)}.
All listed offsets together cover every base pair exactly once; there are no other edges.
The graph is regular of degree 4.
Calibration datum: the XOR of all bits in offset row 1 is 1.

Find one community bit c_i in {0,1} for each fibre i, with c_0=0 to fix
the global community swap.  These bits define a sign vector on all vertices by
  x_(i,b) = +1 when c_i XOR b = 0, and -1 otherwise.
The required condition is that for every vertex u,
  sum_{v adjacent to u} x_v = 0 x_u.
Thus the two vertices in each fibre lie in opposite communities.  Equality and
all sums are exact over the integers; order matters and repeated bits are allowed.

Twist rows (the left integer is g and the bitstring is t_0 through t_{n-1}):
  1: 11001
  2: 01010

Give your final answer inside <answer></answer> tags as one JSON array of
exactly 5 bits c_0 through c_4 in fibre order.
Example format: <answer>[0,1,1,0]</answer>
Output nothing else inside the tags.
```

The answer is `[0,0,0,1,0]`. `verify(inst, answer)` returns `(True, "ok")`; dropping its final bit returns `(False, "answer dropped one vertex entry")`. A person can solve the demo on paper: use the calibration bit and propagate around offset row 1.

## Difficulty presets

| preset | fibres `n` | graph vertices | negative offsets | target eigenvalue | language size |
|---|---:|---:|---:|---:|---:|
| demo | 5 | 10 | 1 | 0 | `2^4` |
| easy | 151 | 302 | 37 | 2 | `2^150` |
| medium | 239 | 478 | 59 | 2 | `2^238` |
| hard | 251 | 502 | 62 | 2 | `2^250` |

`hard` ships. The oracle run initially labeled its tested rungs 101/151/239 as easy/medium/hard, then held at escalated `n=251`; the ladder was slid upward afterward as required. A prior dominant-eigenvalue construction was discarded because 64-restart signed-majority descent recovered 8/8 witnesses.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose/fence response round-trips; answer is JSON-native |
| G4 | pass | 0/200,000 hits; exact density `2^-250 = 5.527147875260445e-76` |
| G5 | pass | demo has exactly 1 answer; hard baseline 15,917,420 operations / 1.106 s |
| G6 | pass | four attacks 0/8 each; exact spectral reference 8/8 |
| G7 | pass | 502 vertices scaled to 1,006 and still verifies |
| G8 | pass | 80/80 invariance, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | 503 chars, 126 estimated tokens, 251 atoms, 250 intended operations |

## Oracle loop

The official bare loop used two vendors at medium reasoning effort. Any solve defeats a rung; all three attempts at the final rung failed.

| harness label / size | seeds | solved/attempts | outcome |
|---|---|---:|---|
| easy / 101 | 556133429, 435252732, 1411189270 | 2/3 | escalated |
| medium / 151 | 341942087, 1551639444, 1686745471 | 1/3 | escalated |
| hard / 239 | 985057859, 831759180, 196018761 | 1/3 | escalated |
| escalated / 251 | 1899152660, 1587828442, 259928581 | **0/3** | **hardened** |

## G9 diagnostics

The shipping preset was rerun in separate scratch directories, preserving the bare transcript.

| arm | solved/attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Hinted-minus-placebo is **0.0**. The one-sentence invariant hint bought no observed improvement over the placebo, so this pool does not provide evidence that the declared invariant alone unlocks the task. One hinted Gemini call exhausted its reasoning-token allowance and returned no answer; the harness records that as a completed failure, not an API error. The size/effort measurements are 503 characters, 251 atoms, and 250 Boolean operations.

## Use

```python
import json
import gen_1409_2290 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
raw = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(raw)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit examples with:

```bash
bash scripts/emit.sh 1409.2290 20 hard
```

## Caveats

- These exact equitable cyclic two-lifts preserve the paper's graph, community-sign, and adjacency-eigenvector objects, but they do not sample the SBM or benchmark overlap, BP, Bethe free energy, or the detectability threshold. The target is an interior eigenvalue, not necessarily the paper's usual second adjacency eigenvalue.
- The `P(guess)` figure is uniform over normalized bit vectors after all stated shape constraints. It measures blind guessing, not a parity-aware or linear-algebraic prior.
- The panel does not run BP, SDP, floating-point full eigendecomposition, or non-backtracking clustering. Exact modular nullspace elimination is the more direct standard method for this stated target-eigenvalue problem and succeeds as Track B requires.
- `canonical_key` uses degree and common-neighbour multisets plus the target eigenvalue. It is invariant under tested fibre permutations, fibre swaps, row reorderings, and compositions, but is not a complete graph-isomorphism canonical form.
- The answer is close to the 256-atom cap, and there is no legal larger prime rung: 257 fibres would require 257 atoms. The G9 hint result is also inconclusive about the claimed intuition because hinted and placebo performance were identical.
