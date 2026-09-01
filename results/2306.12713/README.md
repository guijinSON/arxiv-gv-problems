# Verified graceful-zillion problem generator

## What the family is

This module extracts the graceful-labeling subproblem used in Section 2.2 of
Tommaso Traetta’s [*A constructive solution to the Oberwolfach problem with a
large cycle*](https://arxiv.org/abs/2306.12713) (arXiv:2306.12713v2). A *zillion
graph* `[k | l1,...,lu]` is the disjoint union of one `k`-edge path and cycles
of lengths `l1,...,lu`. The solver must bijectively label its `a+1` vertices by
`0,...,a`, where `a=k+sum(li)`, so that the absolute differences across its `a`
edges are exactly `1,...,a`. The witness lists labels in path order and cyclic
order. Verification is a linear-time recomputation of labels and differences.

The generator samples one edge of every difference first, enforces degrees one
or two, extracts the resulting path/cycles, and only then publishes their
lengths. It therefore knows a witness without putting that witness in the
rendered problem. Any valid graceful labeling is accepted.

## Why this regime is hard

Section 2.2 fixes the exact definition. Its Theorem 2.4 is also the important
easy-case warning: it constructs a graceful `[k | L]` whenever
`k >= B(L) = 6 b0 + 7 b1 + 29`. Every generated instance checks `k < B(L)` and
requires at least three cycles with at least three distinct lengths. Thus this
is not the paper’s constructive long-path regime. It also avoids the simplest
one-cycle profiles and the two-cycle Oberwolfach cases called out in Section 1.

There is no known polynomial-time or closed-form construction for this general
short-path, multi-cycle graceful-labeling search family. This is not a formal
NP-hardness claim: trust rests on steering outside the known sufficient theorem,
the measured gates below, and the independent oracle run. The paper’s main
Theorem 1.1 explicitly solves a large-cycle **Oberwolfach factorization** regime;
that tempting initial family was rejected because the theorem itself would make
it directly constructible. The witness family shipped here is the graceful
labeling problem used as an ingredient in that proof.

## Worked `easy` example

For `make_instance(seed=123, **DIFFICULTY["easy"])`, the complete instance data
in the rendered statement is:

```text
Graceful labeling problem (one path plus disjoint cycles)

The graph has one path with 27 edges (therefore 28 vertices) and
3 vertex-disjoint cycles.  In the input order, the cycle lengths are:
[11, 9, 17]

These components are mutually vertex-disjoint.  A cycle of length ell has ell
vertices and ell edges.  Thus the whole graph has 65 vertices and 64 edges.

Assign every integer label from 0 through 64, inclusive, to exactly one vertex.
For an edge whose endpoint labels are x and y, its edge difference is |x-y|.
Your labeling is valid exactly when the 64 edge differences are all distinct;
equivalently, they must be precisely 1 through 64, inclusive.

Represent the path by listing its 28 labels in traversal order.  Represent
each cycle by listing its labels in cyclic order; the last entry is adjacent to
the first.  Reversing the path, rotating or reversing a cycle, and reordering
cycles are allowed.  The multiset of submitted cycle lengths must equal the
input multiset.  Labels are 0-indexed integers, repetitions are forbidden, and
no edges exist between different listed components.

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "path" and "cycles", each mapped to arrays of integers.
Format-only example: <answer>{"path":[0,1],"cycles":[[2,3,4]]}</answer>
The example numbers are not an answer to this instance.  Output nothing else
inside the tags.
```

A valid answer (cycle order need not match input order) is:

```json
{"path":[24,42,21,46,26,30,49,17,50,5,59,1,62,7,54,12,51,16,47,19,43,32,38,25,37,28,35,34],"cycles":[[9,52,15,44,29,31,39,13,53],[6,56,20,36,33,23,40,18,48,10,58],[0,63,3,60,4,55,14,41,27,22,45,11,57,8,61,2,64]]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the first path
label by the second returns `(False, "labels are not distinct")`.

## Difficulty presets

| preset | edges `n` | minimum cycles | distinct lengths | allowed path fraction | status |
|---|---:|---:|---:|---:|---|
| easy | 64 | 3 | 3 | 0.10–0.65 | **ships; oracle held** |
| medium | 96 | 3 | 3 | 0.10–0.60 | gates pass; oracle not reached |
| hard | 144 | 4 | 3 | 0.08–0.55 | gates pass; oracle not reached |

No preset was rejected. The harness stopped at `easy` because all three models
failed, as its protocol requires. `escalate()` grows the edge count and tightens
the component profile if a future run defeats every named preset.

## Gate results

| gate | measured result |
|---|---|
| G1 | 9/9 plants verify: 3 presets × seeds 0, 1, 2 |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | realistic prose/fence round-trip passed; 4/4 garbage cases returned `None` |
| G4 | 0/200,000 structure-aware guesses; sampled structural space has 87 digits |
| G5 | tiny `n=8` audit: 60/181,440 valid = 0.0003306878 |
| G6 | outlier 0/8; greedy 0/8; 128-restart attack 0/8 (1,024 guesses) |
| G7 | `n=128` builds and verifies; space grows from 87 to 213 digits |
| G8 | 20 reorder invariance checks, 20 carried witnesses, 40 answer symmetries, 20/20 unrelated keys distinct |

G8 uses a complete invariant here, not a seed or rendered-text hash: one path
length plus the sorted cycle-length multiset completely classifies a disjoint
union of one path and cycles up to graph isomorphism.

## Oracle loop

All calls used reasoning effort `medium` at the shipping `easy` preset. Every
reply parsed successfully, then failed exact difference verification.

| model | seed | solved | verifier result |
|---|---:|---|---|
| `openai/gpt-5.6-terra` | 1731208459 | no | differences not exactly `1..64` |
| `x-ai/grok-4.6` | 1259241641 | no | differences not exactly `1..64` |
| `google/gemini-3.1-pro-preview` | 207639336 | no | differences not exactly `1..64` |

The harness verdict is `hardened`, with zero escalations. Full replies and timing
are preserved in `llm_loop_transcript.jsonl`; seeds and pool are in `.meta.json`.

## How to use it

```python
import gen_2306_12713 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit twenty checked, nonisomorphic samples with:

```bash
bash scripts/emit.sh 2306.12713 20 easy
```

Run the local gates with `python3 results/2306.12713/gen_2306_12713.py`.

## Caveats

- The short-path inequalities avoid Theorem 2.4’s sufficient construction, but
  failing that sufficient condition does not prove that no other specialized
  construction applies to a particular sampled cycle profile.
- Graceful labeling of this restricted graph class is not claimed NP-hard. A
  future algorithm for short-path zillion graphs would invalidate H even though
  all present tests still passed.
- `0/200,000` is the observed frequency, not a statistical proof that the true
  probability is below one in a million. The prior is uniform over label
  permutations that already satisfy every stated shape, size, range, and
  bijection constraint; it is not the distribution produced by a SAT/CSP solver.
- The adversary panel tests endpoint/outlier placement, a largest-difference
  greedy rule, and shallow uniform restarts. It does not test industrial SAT,
  integer programming, constraint programming, or long local search.
- The exact G5 enumeration intentionally uses an easy path-only toy instance so
  it can terminate. It audits counting code and sparsity, not shipping hardness.
- Generation conditions on component profiles found by randomized exact search,
  so the profile distribution is not uniform over all feasible zillion graphs.
