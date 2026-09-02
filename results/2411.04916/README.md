# Planted spherical subcodes from arXiv:2411.04916

## What the problem is

This generator turns the compatibility-selection step in Cohn and Li's [*Improved kissing numbers in seventeen through twenty-one dimensions*](https://arxiv.org/html/2411.04916v2) into a scalable witness problem. Section 1 defines a kissing configuration as unit vectors whose distinct pairwise inner products are at most `1/2`. In Section 3, immediately before Lemma 3.1, the paper has a pool of candidate deep-hole vectors that cannot all be added together, so it must select a large pairwise-compatible subcode.

An instance here supplies three candidate centers per graph vertex and asks for exactly one from every triple. The centers are exact normalized binary vectors. Two selected centers have inner product `8/14 > 1/2` exactly when their choices give the same colour to adjacent graph vertices; every other pair has inner product `7/14`. A witness is therefore a strictly increasing list of candidate IDs encoding a proper 3-colouring. `verify` checks its shape and all graph edges using integers only, and accepts any valid colouring.

## Why it is hard—and what was avoided

The paper itself proves geometric lower bounds, not a complexity theorem. The scalable hardness statement comes from Cavallaro and Fluschnik, [Section 3.2, Theorem 2](https://arxiv.org/html/2104.08470#S3.SS2): 3-colouring remains NP-hard even for 5-regular planar Hamiltonian graphs. Our hidden core is likewise 5-regular, the number of vertices grows, and the witness space is `3^n`; there is no optimum or nonexistence claim.

Two easy regimes were excluded. First, graphs of maximum degree at most three are polynomial-time 3-colourable, as reviewed in Section 1 of that complexity paper. Second, the original paper's fixed `C_10`, distance-6 problem is completely solved by Lemma 3.1: its LP bound is 192 and the proof explicitly classifies the six cosets used in a solution. Replaying Sections 2–4 at fixed dimensions would be a coordinate lookup, not an unlimited hard family.

The inverse generator samples a balanced colouring first, builds only cross-colour edges, and then applies many degree-preserving switches. Every planted and decoy center has norm 1, conflict degree 7, and the same neighbour-degree profile. Thus the answer is known before the instance is built without creating a degree or width outlier.

## Worked example

For readability this is the complete rendering of `make_instance(n=12, seed=424242, degree=5, mix_factor=20)`. It is below the gate-qualified presets; the smallest retained preset has 108 vertices because smaller proposed presets failed the restart attack.

<details>
<summary>Complete rendered instance</summary>

```text
Find a kissing subconfiguration in the following finite pool.

A kissing configuration is a set of unit vectors in Euclidean space such that
the inner product of every two distinct selected vectors is at most 1/2.

There are 12 vertex groups, numbered 0 through 11.  Group v contains the
three candidate centers with IDs 3*v, 3*v+1, and 3*v+2; their local colours are
0, 1, and 2 respectively.  IDs and vertices are 0-indexed.  You must select
exactly one candidate from every group, hence exactly 12 distinct candidates.
The output IDs must be in strictly increasing order.  Order otherwise has no
mathematical significance, and repetitions are forbidden.

Here is the exact coordinate definition.  Make a conflict graph on all 36
candidate IDs.  Two candidates conflict exactly when either:
  (a) they are different candidates in the same vertex group; or
  (b) they have the same local colour and their vertex pair is in BASE_EDGES.
Every candidate has conflict degree D=7.  Give the ambient space D common
coordinates C_0,...,C_(D-1), followed by one coordinate Q_e for every unordered
conflict-graph edge e.  For candidate i, let z_i be the 0/1 vector that is 1 in
all D common coordinates and in Q_e exactly when e is incident with i, and 0
elsewhere.  Define the actual center x_i = z_i/sqrt(2*D).

Thus ||x_i||=1 exactly.  For distinct candidates i,j, direct substitution gives
<x_i,x_j>=(D+1)/(2*D)>1/2 if they conflict, and exactly 1/2 otherwise.  Therefore
the requested IDs are precisely a pairwise nonconflicting selection.  You may
use either this inner-product definition or the equivalent conflict rules.

All unordered base-graph edges follow, one "u v" pair per line.  Edges are
inclusive data; a pair not listed is not a base edge.
BASE_EDGES
0 2
0 5
0 8
0 10
0 11
1 3
1 4
1 5
1 6
1 10
2 4
2 5
2 6
2 7
3 4
3 6
3 8
3 10
4 7
4 9
5 9
5 11
6 8
6 11
7 8
7 10
7 11
8 9
9 10
9 11
END_BASE_EDGES

Give your final answer inside <answer></answer> tags, as exactly 12
comma-separated integer candidate IDs in strictly increasing order.
Example of the required syntax: <answer>0, 4, 8</answer>
Output nothing else inside the tags.
```

</details>

The planted answer is `<answer>1, 5, 8, 10, 12, 15, 18, 22, 26, 28, 30, 35</answer>`. `verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last ID returns `(False, "expected exactly 12 candidate indices, got 11")`.

## Difficulty presets

| Setting | `n` | Degree | Mix factor | Structure-aware space | Status |
|---|---:|---:|---:|---:|---|
| Retired easy | 48 | 5 | 30 | `3^48` | Rejected: min-conflicts solved 8/8 |
| Retired medium | 84 | 5 | 40 | `3^84` | Rejected: min-conflicts solved 1/8 |
| **medium** | **108** | **5** | **40** | **`3^108` (52 digits)** | **Ships; hardened** |
| hard | 162 | 5 | 50 | `3^162` (78 digits) | Available; all local gates pass |

`SHIPPING_DIFFICULTY` is `medium`. Retired settings are documented here but deliberately absent from `DIFFICULTY`, so the official hardener cannot stop on a level that fails G6.

## Gate results

| Gate | Measured result | Pass |
|---|---|:---:|
| G1 planted verifies | 16/16 (2 presets × 8 seeds) | yes |
| G2 corruptions | 5/5 rejected with 5 distinct reasons | yes |
| G3 round-trip | 48 IDs recovered through prose/fence; garbage → `None` | yes |
| G4 structure-aware guesses | 0/200,000 from uniform one-of-three choices; space `3^108` | yes |
| G5 exact sparse count | 6/531,441 at `n=12` = `1.1290058539e-5` | yes |
| G6 degree / greedy / restart | 0/8, 0/8, 0/8 solved at shipping level | yes |
| G7 scaling | `n=216` built and verified; space grew from 52 to 104 digits | yes |
| G8 canonical key | 20/20 composed invariances, 20/20 carried witnesses, 20/20 unrelated keys distinct | yes |

The machine-readable measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The script-owned final run used medium reasoning and returned `verdict: hardened` at the shipping preset with zero escalations.

| Preset | Model | Seed | Solved? | Recorded reason |
|---|---|---:|:---:|---|
| medium | `anthropic/claude-sonnet-5` | 1904816646 | no | Empty length-limited response after 32,000 completion tokens |
| medium | `openai/gpt-5.6-terra` | 170055947 | no | Parsed list; centers 5 and 155 conflict (`8 > 7`) |
| medium | `google/gemini-3.1-pro-preview` | 1109199946 | no | Parsed list; centers 1 and 118 conflict (`8 > 7`) |

See [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) and [`.meta.json`](.meta.json) for the exact replies, timings, pool, master seed, and verdict.

## How to use it

```python
from gen_2411_04916 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    render, parse_answer, verify,
)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=7, **params)
question = render(inst)
answer = parse_answer(model_reply)  # raw model text
ok, reason = verify(inst, answer)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2411.04916 20 medium
```

## Caveats

- Theorem 2 is worst-case NP-hardness for 5-regular graphs; it does **not** prove that this planted random distribution is hard. The oracle and attack panels are empirical evidence, not an average-case reduction.
- G4 samples uniformly from the exact obvious search space—one of three centers per group. Its observed rate is 0/200,000, but that does not statistically prove a probability below `1e-6`; it also does not model a sophisticated graph-colouring prior.
- The attacks tried were degree/outlier selection, deterministic left-to-right greedy, and 32-restart min-conflicts. Exact SAT/ILP, DSATUR with backtracking, belief propagation, spectral/community recovery, and large compute budgets were not tested.
- One of three oracle failures was an empty length-limited response, which is weaker evidence than the two parsed invalid witnesses. The harness records it explicitly rather than treating it as an API error.
- `canonical_key` uses all rooted colour-refinement quotient codes. It was invariant and collision-free in the required tests, and refinement was discrete on spot-checked generated graphs, but it is not a proven complete graph-isomorphism canonical form; rare nonisomorphic graphs could share a key.
- `make_instance` rounds `n` up to at least 12 and to a multiple of six. Raising degree would enter a more statistically detectable planted-colouring regime, while lowering it toward maximum degree three enters a known easy regime; the presets therefore scale by `n` at fixed degree five.
