# arXiv:1601.03676 — verified weighted-overlap set packing

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style packing |
| Certificate | integer tuple: `n` pairs `[group, option]` |
| Native objects | bounded set system, nonnegative element weights, `alpha`-Weight overlap, set packing |
| Intended intuition | invariant: group-anchor weight residues change local options into global sheet coordinates |
| Domain essentiality | native; no reduction |

This family uses the native objects from López-Ortiz and Romero,
[*Arbitrary Overlap Constraints in Graph Packing Problems*](https://arxiv.org/abs/1601.03676).
The solver receives bounded sets, nonnegative element weights, and an overlap
threshold. It must choose one set from every group so that every pair has shared
weight at most zero. A witness is checked by exact set intersection and integer
addition.

## Trust status and construction

All local gates pass. The required four-vendor hardening is **blocked**, not
passed: all bare, structural-hint, and placebo calls returned OpenRouter HTTP 403
`Key limit exceeded (total limit)` before any model response. The script-owned
error transcripts are retained, but errors are not hardness evidence. This result
must not be submitted until a funded key produces scored runs.

Generation is inverse. It first samples a connected regular constraint graph and
a cyclic sheet offset for every candidate group. Observable option `a` in group
`i` represents sheet `(a + offset[i]) mod q`. For every forbidden option pair on
a constraint edge, the builder creates one positive-weight element shared by
exactly those two sets. Each group also has a common positive anchor, and all sets
share one zero-weight element. Any one global sheet is a certified packing; the
stored answer is sheet zero and is known before any sets are assembled.

The anchor’s weight residue modulo `q` equals its group offset. Random positive
weight quotients and arbitrary element relabelling preserve equal sizes and remove
simple magnitude/position outliers. The first two displayed groups are a nonedge
with distinct, individually uniform offsets, which prevents the no-backtracking
left-to-right greedy prefix from completing.

## Why this is Track B

Definition 1 in Section 2 says a well-conditioned overlap rule is hereditary,
conflicts only on a nonempty overlap with a removable conflicting element, and
is polynomial-time computable. Lemma 7 in Section 4.1 proves that the nonnegative
`alpha`-Weight predicate used here has those properties.

The paper’s easy-result warning is central: Theorems 1 and 2 in Section 3.1
give the BST-`alpha` algorithm with running time
`O(r^(rk) k^((r+1)k) N^(cr))`; small packing size `k` is FPT. This family therefore
makes no Track A claim, and the paper’s `k` grows with the generator’s `n`.

The measured reference algorithm indexes every candidate occurrence of each
positive universe element, constructs the local compatibility tables, and
propagates a connected component in `O(L + |E| q^2)`, where `L` is the number of
displayed set incidences. On eight hard instances it solved 8/8, averaging 13,056
incidence reads, 6,272 conflict marks, 7,168 compatibility-cell inspections,
32 component nodes, and 27,616 counted exact operations, with a recorded mean
wall time of 0.0070 seconds in CPython. The
compact route notices the anchor invariant and chooses option
`(-anchor_weight) mod q` in each group: 64 modular operations at shipping size, also
verified 8/8. The measured 27,616-versus-64 gap (431.5×) is the Track B claim.

## Worked demo (`seed=0`)

This smallest preset is hand-solvable. Reduce each listed group-anchor weight modulo
`q=3`, negate the residue modulo 3, and select that option.

```text
Weighted-overlap set packing

There are n=6 candidate groups, numbered 0 through 5.
Every group has q=3 candidate sets, with options numbered 0 through 2.
Every candidate is a set of exactly r=6 integer-labelled universe elements.
The order of elements inside a displayed set has no meaning and elements do not repeat.

Element weights are nonnegative integers.  The single element
  11
has weight 0.  The common group anchors have the positive weights listed
below; every other displayed universe element has weight 1.
For two candidate sets A and B, their overlap weight is the sum of the
weights of the elements in A intersection B.  They alpha-conflict exactly
when this overlap weight is greater than the inclusive threshold 0.
Thus sharing the weight-0 element is allowed, while sharing any positive-
weight element is forbidden.  All comparisons and sums are exact integers.

Find exactly k=6 distinct candidate sets with no alpha-conflicting pair.
You must choose exactly one option from every group.  (Candidates in the
same group share a positive-weight group element, so no valid packing can
take two of them.)  The listed constraint edges identify group pairs that
may have an additional positive-weight overlap; all validity is still
defined by the displayed sets and the alpha rule above.

For reference, [anchor element, weight] is listed in group order 0..n-1
(each anchor is also visible in every option of its group):
  [[17,209],[30,199],[10,19],[3,41],[23,205],[6,35]]

Constraint edges (undirected group pairs):
  [[0,2],[0,4],[1,3],[1,5],[2,3],[4,5]]

Candidate sets:
Group 0:
  option 0: {11,17,24,29,36,37}
  option 1: {5,7,11,17,28,35}
  option 2: {1,11,13,16,17,26}
Group 1:
  option 0: {4,11,30,32,33,39}
  option 1: {11,15,19,22,25,30}
  option 2: {8,11,18,27,30,41}
Group 2:
  option 0: {2,5,9,10,11,29}
  option 1: {10,11,13,20,35,38}
  option 2: {0,10,11,21,26,37}
Group 3:
  option 0: {3,9,11,21,33,41}
  option 1: {2,3,11,15,32,38}
  option 2: {0,3,11,18,20,22}
Group 4:
  option 0: {7,11,14,23,34,36}
  option 1: {1,11,12,23,28,40}
  option 2: {11,16,23,24,31,42}
Group 5:
  option 0: {6,8,11,14,39,42}
  option 1: {4,6,11,12,25,34}
  option 2: {6,11,19,27,31,40}

Group IDs and option IDs are 0-indexed.  Return one [group,option] pair
for every group.  Pair order is irrelevant; group IDs may not repeat.
Give your final answer inside <answer></answer> tags as one JSON array.
Example: <answer>[[0,2],[1,0],[2,1]]</answer>
That three-pair example illustrates syntax only; it is not a complete answer.
Output nothing else inside the tags.
```

The answer is `[[0,1],[1,2],[2,2],[3,1],[4,2],[5,1]]`.
`verify(inst, answer)` returns `(True, "ok")`. Dropping the last pair returns
`(False, "expected exactly 6 group-option pairs, received 5")`.

## Difficulty presets

| preset | `n` | `q` | degree | `r` | rendered chars | answer-space bits | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 6 | 3 | 2 | 6 | 2,573 | 9 | hand example; skipped by hardening |
| easy | 16 | 5 | 3 | 14 | 7,716 | 37 | bare oracle blocked before scoring |
| medium | 24 | 7 | 5 | 32 | 29,799 | 67 | not reached |
| hard | 32 | 8 | 7 | 51 | 70,019 | 96 | provisional shipping preset |

Escalation first raises regular-graph degree and then `q` at fixed witness length.
Only after those axes reach the declared `q <= 12` bound does it raise `n`; it
returns `cap_bound` at `n=128`, where the witness has exactly 256 atomic elements.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses and independent compact-route witnesses verify; JSON round-trips |
| G2 | empty/drop/duplicate/out-of-range/swap rejected with five distinct reasons |
| G3 | tagged, fenced model-style response round-trips |
| G4 | 0/200,000 structure-aware random assignments valid; space `8^32 = 2^96` |
| G5 | shipping density 0/200,000 (8 solutions known by construction); demo exact count 3/729; reference mean 27,616 operations |
| G6 | five attacks 0/8; reference algorithm 8/8; compact invariant route 8/8 in 64 operations |
| G7 | doubled `n=64` builds and verifies; first escalation keeps 64 atoms; `cap_bound` occurs at the 256-atom limit |
| G8 | 40/40 composed relabellings/weight normalizations preserve the key and carried witness; 20 unrelated keys distinct |
| G9(c) | 215 chars, 54 estimated tokens, 64 atoms, 64 intended operations — within all caps |

The failing attacks are minimum weight/element-label outlier, left-to-right greedy, 256
uniform random restarts, equal local option, and local option-zero plurality.

## Oracle loop and G9 arms

The bare harness made four redraw attempts at `easy`; the two G9 harnesses made
four redraw attempts each at `hard`. Every call returned the same key-limit 403,
so there are zero scored attempts and no oracle verdict.

| bare preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 143211184 | x-ai/grok-4.6 | error | HTTP 403 key total limit |
| easy | 2102061909 | google/gemini-3.1-pro-preview | error | HTTP 403 key total limit |
| easy | 549822069 | google/gemini-3.1-pro-preview | error | HTTP 403 key total limit |
| easy | 829100588 | x-ai/grok-4.6 | error | HTTP 403 key total limit |

| arm | scored solved/attempts | error attempts | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | pool unreachable; no hardness evidence |
| structural hint | 0/0 | 4 | no hinted diagnostic available |
| placebo | 0/0 | 4 | no placebo diagnostic available |

`hinted - placebo` is therefore undefined in substance (stored as `0.0` only
because both denominators are zero). The hint names only the invariant: a group
anchor weight’s residue modulo `q` is the coordinate offset preserved by compatibility.

## Use

```python
from gen_1601_03676 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
print(verify(inst, candidate))
```

Once scored hardening evidence exists, emit from the repository root:

```bash
bash scripts/emit.sh 1601.03676 20
```

## Caveats

- This distribution is efficiently solvable and intentionally claims only
  Track B. Both the compatibility algorithm and the 64-operation invariant route
  are explicit; there is no Track A hardness claim.
- The bounded family language uses even `6 <= n <= 128` and `3 <= q <= 12`;
  seed variation supplies instances within those bounds.
- The 0/200,000 density is under the declared uniform prior that already chooses
  exactly one option per group. It does not lower-bound informed solvers. The
  construction has exactly `q` sheet solutions.
- No external SAT/ILP solver was run, and the paper’s full generic BST-`alpha`
  implementation was not reproduced. The measured exact reference is the stronger
  incidence-index/compatibility-table algorithm specialized to this grouped distribution.
- The canonical key is a strong but incomplete isomorphism invariant (rooted
  Weisfeiler–Lehman fingerprints plus exact closed-walk traces); pathological
  nonisomorphic collisions remain theoretically possible.
- The hard prompt is 70,019 characters. The compact arithmetic and answer fit the
  caps, but prompt scanning may still contribute to failure; scored G9 arms are
  needed to distinguish that from failure to find the invariant.
- `gvlib` is imported when available as requested, but this finite set-system
  family needs only the Python standard library and falls back cleanly.
- The decisive external caveat is unresolved: replenish `OPENROUTER_API_KEY` and
  rerun bare, structural, and placebo harnesses before treating this as shipped.
