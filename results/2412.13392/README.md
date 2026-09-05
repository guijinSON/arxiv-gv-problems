# arXiv 2412.13392 — verified twined-factorization generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate form | integer tuple (a permutation pairing) |
| Native objects | two regular permutation sets, H/T row-role constraints, and a distinguished truncation symbol |
| Intended intuition | decomposition: recover the shared construction index from the distinguished-symbol images and use the odd-even role blocks |
| Domain essentiality | native |
| Reduction | none |

## What the problem is, and whether to trust it

The source is Alice Lacaze-Masmonteil, [*Hamiltonian decompositions of the wreath product of hamiltonian decomposable digraphs*](https://arxiv.org/abs/2412.13392).  Sections 2–3 encode a directed 2-factor of `C_2 wreath empty_m` as a pair of permutations.  A product with one cycle is Hamiltonian; a pair whose truncation product has two cycles is truncated-Hamiltonian.  A solver receives two regular sets of `m` permutations and an H/T role for each row of the first set, and must return a bijection to the second set having every requested type.  The checker uses only exact permutation composition, truncation, cycle counting, and bijection checks.

The G and V claims are strong: Construction 5.3, Lemma 5.5 (with Remark 5.4), and Proposition 5.10 produce the certificate before either set is reordered, and 16/16 planted instances verified.  The local Track-B measurements also pass.  The external no-tool H claim is **not yet established**: the required OpenRouter runs were attempted, but the supplied key returned HTTP 403 “Key limit exceeded” for every vendor call.  The script-owned error transcripts are retained; no oracle failure was misreported as a solver failure.  Accordingly, this is a verified generator awaiting external hardening, not a release-ready hardness claim.

## Why this is Track B

Proposition 5.10 covers `m >= 15`, `m = 3 (mod 12)`, and even `2 <= c <= m-3`.  It explicitly gives the factorization, so claiming Track A would be false.  Given an arbitrary displayed instance, an efficient reference method tests all `m^2` pairs, constructs the exact role-compatible bipartite graph in `O(m^3)` permutation-image work, and runs Hopcroft–Karp in `O(m^(5/2))`.  At shipping `m=75`, it solved 8/8, averaging 1,190,367 counted operations and 0.569 seconds.

The compact route notices that the two regular sets are `gamma_1 F_m` and `gamma_-1 F_m`.  Both shifts fix the distinguished point, so its image identifies the same underlying `sigma_i` row in both sets.  Construction 5.3 inverts that image by a short parity formula; Proposition 5.10 then gives the mate from the H/T role and its adjacent odd-even block.  This costs at most 233 exact modular operations after the insight, versus the measured compatibility scan, stays under the 300-operation cap, and was reconstructed and verified on 8/8 shipping instances.

The generator avoids the paper's easier or irrelevant regimes: Section 4 has a simpler cyclic construction when both `m` and `c` are even; `c` in `{0,1,m-1}` is handled by Lemma 3.2 or earlier results; and even `m`, odd `c`, with the first factor a directed cycle is the possible exception in Theorem 1.5.  Every generated instance instead uses the single uniform Proposition 5.10 regime.

## Worked demo

This is the complete `demo`, seed 0.  A person can solve it on paper by tabulating each row's image of 14, recovering the Construction 5.3 indices, and applying the three Proposition 5.10 pairing cases; direct trial of all 225 pairs is unnecessary.

<details>
<summary>Full rendered instance</summary>

```text
Find a c-twined factorization pairing of two regular permutation sets.

Here m=15, the symbols are the integers 0 through 14, and the distinguished symbol is d=14.
A permutation is written as an image array [p(0),p(1),...,p(m-1)].
For permutations p and q, the product pq means: apply p first and q second, so (pq)(x)=q(p(x)).
The number of cycles counts every disjoint cycle, including fixed points.
If p(d) != d, its truncation is p followed by the transposition swapping d and p(d).
A pair (p,q) is Hamiltonian (H) exactly when pq has one cycle.
A pair (p,q) is truncated-Hamiltonian (T) exactly when neither p nor q fixes d and the product of their truncations has exactly two cycles.
The two displayed lists are regular: for each input symbol x, the m values p(x) across either list are all distinct.

There are c=4 T-labelled rows in the first list. Pair every first-list row to a different second-list row, using all second-list rows exactly once, so each pair has the first row's displayed H or T type.
Indices are zero-based. Order within the answer matters; repeats are forbidden.

FIRST SET (row_index role : image_array)
0 H : [4,5,6,7,8,9,10,11,12,13,0,1,2,14,3]
1 T : [11,12,14,0,1,2,3,4,5,6,7,8,9,10,13]
2 H : [12,13,0,1,2,3,4,5,6,14,8,9,10,11,7]
3 H : [7,8,9,10,14,12,13,0,1,2,3,4,5,6,11]
4 H : [6,7,8,9,10,11,12,13,0,1,2,3,14,5,4]
5 H : [1,2,3,4,5,6,7,8,9,10,11,12,13,0,14]
6 H : [8,9,10,11,12,13,0,1,2,3,4,14,6,7,5]
7 H : [0,1,2,3,4,5,6,7,14,9,10,11,12,13,8]
8 H : [9,10,11,14,13,0,1,2,3,4,5,6,7,8,12]
9 H : [2,0,13,12,11,10,9,14,8,7,6,5,4,3,1]
10 T : [10,11,12,13,0,1,2,3,4,5,14,7,8,9,6]
11 T : [14,3,4,5,6,7,8,9,10,11,12,13,0,1,2]
12 H : [13,14,1,2,3,4,5,6,7,8,9,10,11,12,0]
13 T : [3,4,5,6,7,8,14,10,11,12,13,0,1,2,9]
14 H : [5,6,7,8,9,14,11,12,13,0,1,2,3,4,10]

SECOND SET (row_index : image_array)
0 : [9,10,11,12,14,0,1,2,3,4,5,6,7,8,13]
1 : [4,3,2,0,13,12,11,10,9,14,8,7,6,5,1]
2 : [14,5,6,7,8,9,10,11,12,13,0,1,2,3,4]
3 : [0,1,14,3,4,5,6,7,8,9,10,11,12,13,2]
4 : [8,9,10,11,12,13,0,1,2,3,4,5,14,7,6]
5 : [1,2,3,4,5,6,7,8,14,10,11,12,13,0,9]
6 : [2,14,4,5,6,7,8,9,10,11,12,13,0,1,3]
7 : [10,11,12,13,0,1,2,3,4,5,6,14,8,9,7]
8 : [12,13,0,1,2,3,4,5,6,7,14,9,10,11,8]
9 : [6,7,8,9,10,11,12,13,0,1,2,3,4,14,5]
10 : [7,8,9,10,11,14,13,0,1,2,3,4,5,6,12]
11 : [3,4,5,6,7,8,9,14,11,12,13,0,1,2,10]
12 : [13,0,1,2,3,4,5,6,7,8,9,10,11,12,14]
13 : [5,6,7,8,9,10,14,12,13,0,1,2,3,4,11]
14 : [11,12,13,14,1,2,3,4,5,6,7,8,9,10,0]

Give your final answer inside <answer></answer> tags as one JSON array [j0,j1,...,j14] of exactly 15 zero-based integers, where first row i is paired with second row ji.
Example syntax only (not an instance solution): <answer>[2,0,1]</answer>
Output nothing else inside the tags.
```

</details>

Answer: `<answer>[8,9,2,0,7,1,4,6,10,12,13,5,11,3,14]</answer>`.

```text
verify(inst, answer)       -> (True, "ok")
verify(inst, answer[:-1])  -> (False, "pairing length must be exactly 15")
```

## Difficulty presets

The module's `n` is a requested lower bound for the paper's order `m`; it rounds upward to the next supported `m = 3 (mod 12)`.

| preset | m | c | answer atoms | status |
|---|---:|---:|---:|---|
| demo | 15 | 4 | 15 | hand example; oracle intentionally skipped |
| easy | 27 | 8 | 27 | oracle unavailable before scoring |
| medium | 51 | 18 | 51 | local gates pass |
| hard | 75 | 30 | 75 | **shipping preset**; local gates pass |

No preset was rejected.  An unconditioned display-order draft failed G6 because lexicographic greedy solved 4/8; the shipped generator samples the same row-relabeling orbit conditional on that probe failing.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted certificates; both sets regular |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered from prose and fences |
| G4 | pass | 0/250,000 uniform structure-aware bijections valid; language size `75!` |
| G5 | pass | shipping density 0/250,000; reference mean 1,190,367 operations, 0.569 s (max 1,191,592, 1.125 s) |
| G6 | pass | distinguished-image rank, lexicographic greedy, 256 restarts, and cyclic-offset ansatz each 0/8; reference algorithm 8/8 |
| G7 | pass | requested `n` doubled from 75 to 150, giving supported `m=159`; planted certificate still verifies |
| G8 | pass | 20/20 row invariances, 20/20 witness transports, 20/20 arbitrary symbol/row relabelings carrying `d`, and 20/20 unrelated keys distinct |
| G9(c) | pass | 216 characters, about 54 tokens, 75 atoms, 233 intended operations; compact route 8/8 |

## Oracle loop and G9 arms

The bare harness stopped before a scored attempt.  These are API errors, not solver failures.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 207609870 | error | HTTP 403 key total limit |
| easy | GPT-5.6 Terra | 828276601 | error | HTTP 403 key total limit |
| easy | Gemini 3.8 Flash | 531655175 | error | HTTP 403 key total limit |
| easy | Gemini 3.8 Flash | 1268919279 | error | HTTP 403 key total limit |

| G9 arm | solved / scored attempts | transcript outcome |
|---|---:|---|
| bare | 0 / 0 | four unscored HTTP 403 errors |
| structural hint | 0 / 0 | four unscored HTTP 403 errors |
| placebo hint | 0 / 0 | four unscored HTTP 403 errors |

`hinted - placebo` is therefore unavailable, not evidence of a zero effect.  The structural hint names the distinguished-image/index invariant but no procedure.  G9(c) still passes; the three-arm diagnostic must be rerun after the OpenRouter account limit is raised.

## Use

```python
import random
import gen_2412_13392 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
candidate = g.parse_answer("<answer>...</answer>")
ok, reason = g.verify(inst, candidate)
```

From the repository root, after a successful oracle rerun:

```bash
bash scripts/emit.sh 2412.13392
```

## Caveats

- The external STEP 4 hardness evidence is missing because the configured OpenRouter key was exhausted.  This directory is locally complete but not submit-ready until `harden.py` records a real verdict and all three G9 arms receive scored attempts.
- Track B openly has a fast solver.  The benchmark tests whether a no-tool model discovers and executes the short construction-index route, not computational intractability.
- Conditioning the left display order defeats the measured input-order greedy probe but does not alter the compatibility graph.  A solver can choose another ordering; minimum-degree greedy, bounded backtracking, graph automorphism, and specialized exact-matching implementations were not tested.
- The 0/250,000 estimate is for uniform random bijections, after enforcing all obvious format constraints.  It does not model a candidate distribution already exploiting the distinguished-image invariant, and it is not an exact solution count.
- `canonical_key` uses stable colour refinement of the exact role-coloured compatibility graph.  It passed all required transformations and diversity checks but is not a complete bipartite graph-isomorphism canonizer, so rare non-isomorphic collisions are possible.
- The named ladder grows `m`, which also lengthens the natural permutation witness.  Beyond `hard`, `escalate()` first raises the T-role density through four fixed-length settings, then permits `m=87`; only the following supported order exceeds the 300-operation compact-route cap and returns `"cap_bound"`.
