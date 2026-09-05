# Distance domination in reversibly labelled trees

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | integer tuple |
| intuition | change of variables: undo the public bit-reversal relabelling and find periodic path-block centers |
| domain essentiality | native |
| reduction | none |

**Release status:** all local gates G1–G9(c) pass. The required oracle evidence is externally blocked: all bare, structural-hint, and placebo requests returned OpenRouter HTTP 403 `Key limit exceeded`. Those are API errors, not model failures, so this family must not be submitted as hardened until the three script-owned runs obtain scored responses.

## Problem and construction

Garnero, Paul, Sau, and Thilikos's [*Explicit linear kernels via dynamic programming*](https://arxiv.org/abs/1312.6585) defines `r`-Dominating Set in Section 4: find at most `k` vertices so every graph vertex is within distance `r` of the set. The generator hands the solver exactly that native object—a finite labelled tree—and asks for `k` vertex labels. Verification performs an exact multi-source breadth-first traversal and accepts any dominating set in the declared bounded language; it never reads the planted answer.

Generation is inverse. It first chooses the centers of `k` consecutive path blocks, each of length `2r+1`. It then attaches every decoy leaf close enough to one block boundary that the block center still covers it. Finally, an invertible affine/XOR/bit-reversal map relabels all vertices and carries the witness. No domination algorithm is run during generation. The varying pendant multiplicities make unrelated seeds structurally different rather than mere relabellings.

## Why Track B

Track A would be false. Section 4's Lemma 5 gives the `(2r+1)`-state-per-boundary-vertex DP encoder, and Theorem 3 gives a constructive linear kernel for every fixed `r` on graphs excluding a fixed apex minor. More decisively, every generated instance is a tree. The implemented exact reference algorithm repeatedly takes a deepest uncovered vertex and selects its `r`-th ancestor. Its direct implementation runs in `O(k(n+m)+n)`, solves 8/8 hard instances, and at shipping used a median **19,709 counted operations / 0.0102 s**.

The compact route notices that the first `k(2r+1)` inverse-mixed coordinates induce a path. Its block centers are known immediately and are mapped back to vertex labels. At hard this takes **242 exact bit/integer operations**, within the no-tool cap but far shorter than scanning and solving the 2,048-vertex shuffled tree. Theorem 3's kernel constant depends triple-exponentially on fixed `r`; this family fixes `r=8` on every non-demo rung and does not pretend the kernel itself is a certificate-producing solver.

## Worked demo (`seed=0`)

This is the complete rendered demo (without a hint):

```text
Distance domination in a labelled tree

The vertex set is the integers 0 through 15.
Every pair [u,v] below is one undirected edge; there are no loops or
parallel edges.  The displayed graph is a tree.

Let r=3 and k=2.  A set D r-dominates the tree if
every vertex has graph distance at most r from at least one vertex in D.
Graph distance is the number of edges in a shortest path, so a selected
vertex has distance zero from D.

The labels also carry a public reversible coordinate relabelling.  For
a coordinate x in 0..15, compute
  z = ((9*x + 15) mod 16) XOR 12,
then reverse exactly 4 binary bits of z (including leading
zeros).  Call the resulting vertex label L(x).  XOR is bitwise exclusive-or.
This coordinate data is part of the labelled instance; it does not alter
the graph-distance definition above.

Edges:
  [7,10] [0,8] [3,13] [4,9] [2,12] [2,11] [7,14] [6,11] [6,15] [3,10] [0,9] [4,13]
  [0,15] [1,14] [5,13]

Find exactly 2 distinct vertex labels whose set r-dominates
the whole tree.  (Requiring exactly k is equivalent here to the usual
at-most-k question, because any smaller dominating set can be padded
with unused vertices.)  List the labels in strictly increasing x-coordinate
order, where v=L(x); numeric label order is irrelevant.  Repeats are forbidden.
Any witness satisfying these conditions is accepted.

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 2 integers.
Example of the required syntax and ordering (not a claimed witness):
<answer>[6,2]</answer>
Whitespace inside the tags is allowed. Output nothing else inside the tags.
```

The answer is `<answer>[6,10]</answer>`. `verify` returns `(True, "ok")`; dropping the last vertex returns `(False, "too few vertices: expected 2")`. A person can solve this demo on paper by undoing four-bit labels or simply tracing the 16-vertex tree. Exact enumeration confirms it has one valid answer among 120 legal pairs.

## Difficulty presets

| preset | n | r | k | decoy leaves | rendered chars (`seed=0`) | compact ops | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 16 | 3 | 2 | 2 | 1,601 | 18 | hand example |
| easy | 512 | 8 | 16 | 240 | 6,547 | 210 | local gates pass; oracle calls blocked |
| medium | 1,024 | 8 | 16 | 752 | 11,809 | 226 | local gates pass |
| hard | 2,048 | 8 | 16 | 1,776 | 24,331 | 242 | **target shipping preset; local gates pass** |

`escalate()` doubles only the decoy-leaf haystack while keeping `r`, `k`, and the 16-label answer fixed. It returns `"cap_bound"` before the compact route would exceed 300 operations.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed plants verify; 12/12 JSON round trips |
| G2 | pass | empty, dropped, swapped, duplicated, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 uniformly sampled legal `k`-sets; candidate space `4.316664142993405907323829349566015897472e39` |
| G5 | pass | hard density estimate 0/200,000; demo exact count 1/120; reference median 19,709 ops / 0.0102 s |
| G6 | pass | five attacks × 8 seeds, 0 successes; reference and compact routes both 8/8 |
| G7 | pass | 2,048 to 4,096 vertices, 1,776 to 3,824 decoy leaves; answer stays 16 labels and verifies |
| G8 | pass | 60/60 key-invariance and 60/60 carried-witness checks; 20/20 unrelated structural keys distinct |
| G9(c) | pass | 72 chars, 18 estimated tokens, 16 atoms, 242 operations; sampled hard-preset maximum was 73 chars / 19 tokens |

The G6 attacks are largest radius-neighborhood outliers, degree outliers, greedy maximum uncovered coverage, 256 legal random restarts, and the in-context but wrong coordinate-boundary phase. The successful tree algorithm is correctly reported under `reference_algorithm`, not among failing attacks.

## Oracle loop and G9 arms

No row below was scored. `harden.py` retried four times per arm and stopped when the pool was unreachable.

| arm | preset | models drawn | seeds | scored | result |
|---|---|---|---|---:|---|
| bare | easy | Gemini 3.1 Pro Preview ×2; Grok 4.6 ×2 | 1351974229, 810187158, 905089421, 1640233922 | 0 | four HTTP 403 quota errors |
| structural | hard | Grok 4.6 ×3; Claude Sonnet 5 | 797405851, 1046564067, 1219253192, 1652753125 | 0 | four HTTP 403 quota errors |
| placebo | hard | Gemini 3.1 Pro Preview ×3; Claude Sonnet 5 | 295801639, 330653917, 1627150400, 1537948243 | 0 | four HTTP 403 quota errors |

| G9 arm | solved / scored attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 | not estimable |
| hinted | 0 / 0 | not estimable; `hinted_verdict="not_run"` |
| placebo | 0 / 0 | not estimable |

`hinted - placebo` is undefined. No conclusion about the structural hint's effect is possible from provider errors.

## Use

```python
import json
import gen_1312_6585 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
statement = g.render(inst)
reply = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(reply)
assert g.verify(inst, candidate) == (True, "ok")
```

After restoring OpenRouter quota, rerun the bare loop here and both G9 loops in their isolated scratch directories. To emit examples from the repository root:

```bash
bash scripts/emit.sh 1312.6585 20
```

## Caveats

- This is a highly structured tree distribution, not a sampler of arbitrary apex-minor-free graphs. Its claim is no-tool compression, not average-case NP-hardness. A solver that recognizes the public coordinate map has found the intended shortcut.
- The arithmetic coordinate annotation is extra solver-facing structure on a labelled graph. Verification still uses only native graph distances, and removing the tree removes the problem, but the annotation deliberately makes this distribution easier than unannotated `r`-Dominating Set.
- G4 samples uniformly from all coordinate-ordered `k`-subsets. Its 0/200,000 result excludes blind legal guesses under that prior; it says nothing about a model using the coordinate invariant, tree DP, or a learned construction-specific statistic.
- Plants and ordinary path vertices are not identically distributed as rooted graph positions. The strongest tested per-vertex statistic—closed radius-`r` neighborhood size—was 0/8, as was degree ranking, but a more elaborate classifier may still expose the centers.
- SAT/ILP, the paper's full protrusion kernel, and alternative tree-DP implementations were not run. The exact polynomial tree reference already solves 8/8, so those would not change the Track B classification; they could change the measured constant.
- `canonical_key` is exact for the unlabelled tree and therefore for arbitrary vertex relabelling and edge ordering. It intentionally ignores the coordinate presentation, which is a clue/formatting structure rather than part of graph-distance validity.
- Most importantly, no oracle attempt was scored. The three transcripts prove an external quota blocker only, not LLM hardness.
