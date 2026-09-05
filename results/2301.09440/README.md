# Connected face covers from *Splitting Plane Graphs to Outerplanarity*

> **Build status:** the generator and every local gate pass, but the required
> multi-vendor oracle evidence is **not complete**. On the fresh bare run, two
> scored `easy` attempts failed; the quota expired before the third attempt and
> all later redraws returned OpenRouter HTTP 403, “Key limit exceeded.” The
> checked-in transcript is therefore partial evidence, not a hardened verdict;
> this result must not be submitted until the bare, structural-hint, and placebo
> runs complete with a funded key.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate | integer tuple (a canonical list of face labels) |
| intended intuition | decomposition |
| domain essentiality | licensed reduction |
| reduction | paper-licensed: Section 3, Property 1 and the NP-completeness proof |

This is a native connected-face-cover instance from Gronemann, Nöllenburg, and
Villedieu, [*Splitting Plane Graphs to Outerplanarity*](https://arxiv.org/abs/2301.09440).
The solver receives a biconnected plane graph through all of its facial boundary
cycles and must name exactly `k` faces that cover every vertex and are connected
in the face-vertex incidence graph. Verification is just exact incidence lookup,
coverage, and one breadth-first search.

## Construction and trust argument

Section 2 defines connected face cover and proves that a cover of size `k+1`
produces `k` embedding-preserving vertex splits. Section 3 proves that if `G` is
a biconnected cubic plane graph, a vertex cover of `G` corresponds one-for-one to
a connected face cover in the all-1-subdivision of its dual. The generator uses
that reduction without compiling away the plane graph: the subdivided dual and
its facial cycles are exactly what the solver sees.

The source starts at `K4` with a known maximum independent set. One cubic vertex
is repeatedly replaced by a seven-vertex cube-minus-one-vertex patch. If the old
vertex was independent, it is replaced by the patch's three terminals and centre;
otherwise it is replaced by the three intermediate vertices. Either case adds
three independent vertices. Conversely, an independent set using four patch
vertices must use the terminals and centre and contracts to a set containing the
old vertex; one using at most three contracts with it absent. Thus every
replacement raises the independence number by exactly three. Complementing gives
a minimum vertex cover by construction, and the paper's reduction carries it to
the returned connected face cover. No generated instance is solved to obtain its
planted answer.

This is Track B because the generated distribution has an efficient solver.
Recover the source graph from degree-two subdivision vertices, recognize exposed
seven-vertex patches, contract them to `K4`, and unwind the choices. The included
reference implementation is a naive `O(F^2)` scan. Across eight shipping seeds it
used 4,819–5,803 counted local/update operations and averaged 0.0129 seconds. Once
the decomposition is recognized, the compact route is 50 contractions plus
writing 153 labels: 203 high-level operations. The paper's worst-case
NP-completeness theorem is not claimed as distributional hardness. The paper's
separate easy regime must also be kept straight: Section 4 makes maximal planar
inputs polynomial-time through feedback vertex set on subcubic duals; it
additionally notes a `13k` kernel and a PTAS for the general
parameterized/approximation settings.

## Worked demo

For `make_instance(n=0, nesting_bias=0, seed=7)`, the complete rendered data are:

```text
This instance has 10 graph vertices and 4 faces.
Find a connected face cover containing exactly k = 3 faces.

3: 2 7 10 3 6 8
1: 8 6 5 4 9 2
4: 1 10 7 2 9 4
2: 6 3 10 1 4 5
```

The answer is `<answer>[1, 3, 4]</answer>` and
`verify(inst, [1, 3, 4]) == (True, "ok")`. Dropping the last face gives
`verify(inst, [1, 3]) == (False, "expected exactly 3 face labels")`. A person can
solve this demo on paper: there are only four possible three-face subsets.

## Difficulty presets

| preset | expansions `n` | nesting bias | displayed faces | plane vertices | answer length |
|---|---:|---:|---:|---:|---:|
| demo | 0 | 0% | 4 | 10 | 3 |
| easy | 15 | 45% | 94 | 190 | 48 |
| medium | 30 | 65% | 184 | 370 | 93 |
| **hard (ships)** | **50** | **85%** | **304** | **610** | **153** |

No preset has yet been accepted or rejected by the oracle: two valid failures do
not complete the three-attempt `easy` level. `escalate()` first increases nesting
depth at fixed answer length, then increases the number of patches, and returns
`cap_bound` before the 256-atom or 300-operation limit would be crossed.

## Local gates

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted answers verified and JSON-round-tripped |
| G2 | pass | empty/drop/duplicate/swap/out-of-range rejected with 5 distinct reasons |
| G3 | pass | fenced, tagged model-style answer round-tripped; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 uniform structure-aware `k`-subsets |
| G5 | pass | shipping sample 0/200,000; random-greedy baseline 19,456 iterations, 0.0063 s mean |
| G6 | pass | seven attacks, each 0/8; reference contraction 8/8 |
| G7 | pass | doubled build: 604 faces, planted answer verified in 0.0099 s |
| G8 | pass | 120/120 individual/composed symmetry checks; 120/120 carried witnesses; 20/20 keys distinct |
| G9(c) | pass | sampled ship instance: 554 chars, 153 atoms, about 139 tokens; exact worst-case bound: 613 chars/about 154 tokens; 203 intended operations |

The seven G6 attacks test both boundary-incidence extremes, greedy new coverage,
64 randomized greedy independent-set restarts, the by-hand even-label ansatz,
and both local four-cycle extremes. All face and plane-vertex labels are uniformly
scrambled, and every displayed face is a 6-cycle.

## Oracle loop and G9 arms

The fresh bare harness run began on `easy` (`n=15`) and obtained two genuine
failures before the quota expired. It could not score the third slot, so
`harden.py` correctly stopped without writing a hardness verdict.

| preset / model | seed | solved | reason |
|---|---:|---:|---|
| easy / Gemini 3.8 Flash | 891631732 | no | exhausted 32,000 completion tokens and emitted no answer |
| easy / GPT-5.6 Terra | 1188101379 | no | parsed 48 labels, but graph vertex 34 was uncovered |
| easy / four redraws | four distinct seeds | unscored | HTTP 403 key limit |

The required shipping-preset G9 diagnostic remains unavailable:

| arm | solved / scored attempts | verdict |
|---|---:|---|
| bare | 0 / 0 | quota blocked before a shipping-preset run |
| hinted | 0 / 0 | HTTP 403 on every redraw |
| placebo | 0 / 0 | HTTP 403 on every redraw |

Thus hinted minus placebo is unavailable and no conclusion about hint sensitivity
is justified. The structural hint names only the nested-patch invariant; it does
not provide the contraction procedure. When quota is restored, rerun bare in this
directory and each G9 arm in a separate scratch directory so the harness cannot
overwrite the bare evidence.

## Use

```python
from gen_2301_09440 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2301.09440 20
```

## Caveats

The 0/200,000 guess result is an empirical estimate under the declared uniform
prior over sorted `k`-subsets; it is not a proof that a structure-aware solver has
that success probability, and zero observed hits does not mean literal density
zero. The shipping solution count was not enumerated. The family is deliberately
easy with tools: the disclosed reverse-contraction solver takes milliseconds, so
it must never be presented as Track A or as average-case NP-hardness.

The panel did not run a generic ILP/SAT package, a treewidth implementation, or a
full feedback-vertex-set solver; reverse contraction is stronger for this exact
generated grammar and is reported separately as the successful Track-B reference.
The canonical key is exact for the supplied combinatorial embedding and ignores
vertex/face relabelling, row order, cyclic starts, arbitrary per-face traversal
directions, and global reflection; it intentionally regards genuinely different
plane embeddings as different plane-graph instances. Finally, the incomplete
vendor runs are a hard release blocker, not evidence that the family is hardened.
