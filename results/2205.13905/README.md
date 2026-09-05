# arXiv 2205.13905 — verified grid certificates

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | 3-by-3 matrix certificate |
| Native objects | regular-graph component parameters `(v,d)` and the paper's grid graph |
| Intended intuition | change of variables: `w = 2v-d` makes the grid additive |
| Domain essentiality | native; no reduction |

## What the problem is

Bluskov, de Heer, and Sidorenko's paper [*Turán numbers T(n,5,3) and graphs without induced 5-cycles*](https://arxiv.org/abs/2205.13905) builds a graph from nine smaller regular graphs placed in a 3-by-3 grid. Vertices in components sharing a row or column are joined. Section 2 gives exact equations under which the result has the desired total order and degree; Proposition 1 then turns any induced-`C5`-free result into a Turán `(n,5,3)` system.

An instance mixes the `(v,d)` cards of several independently generated valid grids. The solver must select nine distinct card IDs and arrange them so every Section 2 degree equation holds. The answer is checked with parity, nine integer additions, and exact comparisons. The generator chooses all valid grids before mixing their cards, so the certificate is known by construction and never found by solving the emitted instance.

## Why this is Track B

This paper proves existence, not computational hardness. Lemma 5 recursively constructs every needed even-order component, Lemma 6 handles odd order away from the midpoint, and Lemma 7 handles the relevant midpoint case. A Track A claim would therefore be false.

The successful reference algorithm is an exact CSP hash join. It computes `w=2v-d`, enumerates ordered card triples, and joins triples having the same pair of `w`-differences. Its expected cost is `O(p^3+B)`, where `p` is the number of cards and `B` is hash-bucket collision work. At shipping `p=63`, eight runs solved 8/8 with a mean 82,292.75 counted operations and 0.118 seconds (maximum 113,558 operations and 0.194 seconds). The compact route, once the additive invariant is noticed, is budgeted at 207 exact operations. That gap—not average-case complexity—is the Track B claim.

The easy regimes were deliberately not hidden: with only nine cards, selection is free and only their arrangement remains; a tool can solve every preset quickly; and Section 2 itself exposes the linear equations. Difficulty comes only from finding the additive organization among increasingly many same-distribution decoy grids.

## Worked demo

For `make_instance(n=9, spread=4, seed=23)`, the complete data are:

```text
Target N=2305, D=1152
ID: v d
1: 258 133
2: 264 123
3: 250 124
4: 262 126
5: 260 129
6: 254 135
7: 248 138
8: 257 116
9: 252 124
```

A valid answer is:

```text
<answer>[[8,2,1],[5,4,3],[6,9,7]]</answer>
verify(...) -> (True, "ok")
```

Swapping the first two IDs gives `[[2,8,1],[5,4,3],[6,9,7]]` and:

```text
verify(...) -> (False, "degree equation fails at row 2, column 1: got 1159, expected 1152")
```

A person can solve this smallest setting on paper: all nine cards must be used, and the task is to arrange them. Exact enumeration finds 72 spellings, precisely the row/column/transposition symmetries for this asymmetric grid.

## Difficulty presets

| Preset | Cards | Hidden valid grids | Spread | Target `(N,D)` | Status |
|---|---:|---:|---:|---:|---|
| demo | 9 | 1 | 4 | `(2305,1152)` | hand example; skipped by hardener |
| easy | 27 | 3 | 31 | `(17857,8928)` | oracle solved 2/3 |
| medium | 45 | 5 | 61 | `(35137,17568)` | oracle solved 1/3 |
| **hard** | **63** | **7** | **97** | **`(55873,27936)`** | **ships; oracle solved 0/3** |

`escalate()` adds 18 cards and raises the offset spread by 37 while the answer remains exactly nine IDs.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted certificates verified; all JSON-native |
| G2 | drop, duplicate, empty, out-of-range, and swap all rejected with 5 distinct reasons |
| G3 | direct and prose/Markdown round trips both passed |
| G4 | 0/200,000 structure-aware guesses; shipping language size `10,648,350,357,120` for seed 12345 |
| G5 | shipping density estimate 0/200,000; demo has exactly 72 valid answers in 362,880 candidates; reference solved 8/8 at mean 82,292.75 operations |
| G6 | outlier, greedy, 256-restart, and by-hand additive ansatz each solved 0/8; reference solved 8/8 |
| G7 | 126-card doubled instance verified; language grew to `3,773,441,678,952,960` |
| G8 | 40/40 invariance checks and 40/40 carried-witness checks passed; 20/20 unrelated keys distinct |
| G9(c) | 32 characters, 8 estimated tokens, 9 atoms, 207 intended operations; all within caps |

## Bare oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 1100153338 | Gemini 3.8 Flash | failed | empty length-limited response |
| easy | 228233114 | GPT-5.6 Terra | solved | valid grid |
| easy | 448121997 | GPT-5.6 Terra | solved | valid grid |
| medium | 234958329 | Gemini 3.8 Flash | failed | wrong vertex total |
| medium | 74276305 | GPT-5.6 Terra | solved | valid grid |
| medium | 65562963 | Gemini 3.8 Flash | failed | empty length-limited response |
| hard | 2053979731 | Gemini 3.8 Flash | failed | empty response (`finish_reason=error`) |
| hard | 595126729 | GPT-5.6 Terra | failed | wrong vertex total |
| hard | 1148304931 | Gemini 3.8 Flash | failed | empty length-limited response |

The script-owned verdict is `hardened` at `hard` after two escalations. Every nonempty tagged answer parsed; the shipping Terra failure was a genuinely invalid witness, not a parser miss.

## G9 diagnostic arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural | 2/3 | additive invariant named, no procedure given |
| placebo | 1/3 | prompt-only control |

The structural-minus-placebo difference is `2/3 - 1/3 = 1/3`. This small diagnostic suggests that naming the invariant helps, but one placebo solve and only three trials per arm make the estimate noisy. The hinted verdict is `too_easy`, which is recorded and does not gate. Answer size and intended-route cost are 32 characters, 9 atomic IDs, and 207 exact operations.

## Use

From this directory:

```python
import json
import gen_2205_13905 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=2026, **params)
print(g.render(inst))
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 2205.13905 20
```

## Caveats

- This is not an average-case or worst-case hardness claim. The cubic reference algorithm is fast on a computer; Track B only asserts a no-tool compression gap.
- The G4 sampler is uniform over distinct nine-card subsets whose vertex counts already sum to the target, followed by a uniform permutation. It incorporates the obvious sum constraint, but 0/200,000 is an observed frequency, not proof that the true probability is zero or a tight statistical upper bound.
- No external MILP/CP solver was run. The strongest exact test was the in-module ordered-triple hash join; stronger symmetry-aware joins may be faster.
- `canonical_key` exactly removes public card reordering and the answer verifier accepts all row, column, and transpose symmetries. It canonicalizes the parameter-card problem, not isomorphism of fully materialized component graphs.
- Two of the three bare shipping failures were empty Gemini responses, including one recorded with `finish_reason=error`; only Terra supplied a substantive wrong grid. The hardening script counts empty responses under its documented policy, so the evidence is valid for that harness but weaker than three nonempty wrong answers.
- Component graphs are represented by the `(v,d)` parameters used in the paper's proof. The checker executes the parity/range cases of Lemmas 5–7 and all Section 2 equations; it does not expand potentially large adjacency matrices or enumerate induced 5-cycles.
