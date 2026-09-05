# arXiv 2107.14126 — verified graph-growth generator

> **Current status:** all locally executable gates pass, but the result is **not
> yet shippable**. The mandatory OpenRouter hardening and G9 diagnostic arms
> could not obtain a scoreable call because the supplied key returned HTTP 403
> `Key limit exceeded (total limit)` for every vendor. No oracle failure has
> been inferred from those API errors.

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `csp_sat` |
| Certificate form | `integer_tuple` (a set partition of vertex indices) |
| Intended intuition | `constraint propagation`: after the universal-clique join exposes a six-color CSP, neighbor-color saturation is the useful pruning invariant |
| Domain essentiality | `licensed_reduction` |
| Reduction | `paper_licensed`, Section 3, theorem labelled `thm:NP-HARD` |

## The problem

The source is Mertzios et al., [*The Complexity of Growing a
Graph*](https://arxiv.org/abs/2107.14126). A solver receives a graph (H) and
the paper's target (T=H+K_n): an (n)-vertex universal clique joined to all
of (H). It must partition (H) into the requested number of independent
birth slots. The partition expands deterministically into a concrete
zero-excess, distance-2 growth schedule: grow the universal clique first, then
use different universal vertices as parents for the vertices in each final
slot.

`verify` checks the partition, every base edge, every parent/birth constraint,
the distance-2 activation rule, and exact equality of the replayed final graph
with (T). It accepts any valid partition and never reads `inst["answer"]`.
The generator samples a balanced coloring first and only then draws edges
between different classes, so its certificate is known by inverse generation.

## Why Track A is plausible

Section 3's NP-completeness theorem proves that the universal-clique join
encodes graph coloring: the clique consumes one singleton slot per universal
vertex and the remaining slots are precisely color classes of (H). The
generator uses the theorem's (d=2), zero-excess, variable-slot regime. It
deliberately avoids the paper's polynomial regimes: optimal trimming for
(d=1), candidate elimination for unrestricted (n-1)-slot zero-excess
schedules, constant excess, and the perfect-matching-plus-2-SAT algorithm for
exactly (log n) zero-excess slots.

Worst-case NP-completeness does not establish hardness of a planted
distribution. The measured evidence is distribution-specific: at the
candidate shipping preset (`easy`, `n=192`, `k=6`, `p=25/192`), exact DSATUR exhausted
100,001 nodes on all eight seeds (800,008 nodes, 33.635 s total). Degree,
greedy, 256-restart, and bottom-eigenspace spectral attacks also solved 0/8.
The mandatory multi-vendor oracle evidence is still missing because of the
quota failure above.

## Worked demo

For `make_instance(n=9, colors=3, density=5, seed=3)`, the
complete rendered instance is:

```text
Zero-excess growth schedule for a universal-join graph

There are two named groups of vertices:

* U0,...,U8 form a clique, and every Ui is adjacent to every other
  vertex. Thus all U-vertices are universal.
* H0,...,H8 induce the graph H whose complete edge list is printed below.
  There are no other H-H edges.

The target graph T is exactly this 18-vertex graph. Vertex indices are
0-based. Every edge [a,b] below is undirected; endpoint order and edge-list
order carry no information.

H_EDGES=[[4,7],[4,5],[4,6],[6,7],[3,5],[1,7],[5,7],[0,7],[1,8],[0,2],[0,3],[0,6],[1,3]]

Growth rule (edge-activation distance d=2): initially only U0 exists. In one
update slot, each already existing vertex may create at most one new child.
A new child must connect to its parent and may also connect to any already
existing neighbor of that parent. Two children created in the same slot
cannot be connected to each other. A zero-excess schedule never deletes an
edge.

Find exactly 3 nonempty sets partitioning all H-vertex indices 0,...,8 such
that no H-edge has both endpoints in one set. Such a partition is a concrete
certificate for this normal-form zero-excess schedule: first create U1,...,U8
one per slot from U0, connecting each to all older U-vertices; then use your 3
sets as the next 3 birth slots. Within each set, increasing H-index order
assigns distinct parents U0,U1,..., and every child activates exactly its
target edges to older vertices. The verifier performs this replay and compares
the final graph with T. The schedule has at most 11 update slots. Set order and
order inside a set do not matter, repeats are forbidden, and every H-index
must occur exactly once.

Give your final answer inside <answer></answer> tags as a JSON list of exactly
3 nonempty integer lists.
Example format: <answer>[[0,3],[1,4],[2,5]]</answer>
Output nothing else inside the tags.
```

One valid answer is `[[0,4,8],[1,5,6],[2,3,7]]`:

```text
verify(inst, inst["answer"]) -> (True, "ok")
verify(inst, [[0,4,8,1],[1,5,6],[2,3,7]])
    -> (False, "duplicate vertex: 1")
```

This demo has 8 valid partitions among 3,025 shape-valid partitions and is
small enough to solve and check on paper.

## Presets

| Preset | Base vertices | Slots/colors | Cross-edge probability | Target vertices | Status |
|---|---:|---:|---:|---:|---|
| `demo` | 9 | 3 | 5/9 | 18 | hand-scale illustration |
| `easy` | 192 | 6 | 25/192 | 384 | candidate shipping preset |
| `medium` | 208 | 6 | 25/208 | 416 | harder ladder rung |
| `hard` | 224 | 6 | 25/224 | 448 | hardest named rung |

The production rungs keep expected degree roughly stable while increasing the
ground set. `SHIPPING_DIFFICULTY` is provisionally `easy`; the oracle loop did
not produce a verdict that could justify changing it.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify and round-trip through JSON |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced model-style response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; language size (3.529\times10^{146}) |
| G5 | pass | shipping density 0/200,000; DSATUR 100,001 nodes/instance, 4.204 s mean |
| G6 | pass | all five attacks 0/8, including spectral and exact DSATUR |
| G7 | pass | all preset spaces grow; a doubled (n=384) instance verifies |
| G8 | pass | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | gated caps pass (671 chars, 168 tokens, 192 atoms, 198 route operations); non-gating oracle arms unavailable |

## Oracle loop and G9

The bare `harden.py` run made no scoreable call. Each row below is an API error,
not a model failure; the script correctly aborted without a hardness verdict.

| Preset | Seed | Model | Outcome | Reason |
|---|---:|---|---|---|
| easy | 1395028560 | xAI Grok 4.6 | error | HTTP 403 key total limit |
| easy | 1428985238 | xAI Grok 4.6 | error | HTTP 403 key total limit |
| easy | 2003315332 | xAI Grok 4.6 | error | HTTP 403 key total limit |
| easy | 870302759 | Anthropic Claude Sonnet 5 | error | HTTP 403 key total limit |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 0 | unavailable |
| structural hint | 0 / 0 | unavailable |
| placebo hint | 0 / 0 | unavailable |

`hinted - placebo` is therefore not estimable. These arms are diagnostics, not
gates; the gated answer-size and intended-route limits pass. After restoring
OpenRouter quota, rerun bare, hinted, and placebo in separate directories as
prescribed; do not treat the zero-attempt placeholders as evidence.

## Use

```python
from gen_2107_14126 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=3, **DIFFICULTY["demo"])
candidate = parse_answer("<answer>[[0,4,8],[1,5,6],[2,3,7]]</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, after completing the oracle arms:

```bash
scripts/emit.sh 2107.14126 20 easy
```

The module is standard-library-only; `gvlib` is imported opportunistically but
is not required.

## Caveats

The strongest caveat is empirical hardness: the paper proves worst-case
NP-completeness, not hardness of balanced planted colorings. A more powerful
belief-propagation, SDP, SAT/ILP, or spectral-plus-local-repair attack was not
run; any of those could invalidate Track A. The preset keeps expected degree
fixed as `n` grows rather than drifting into known dense planted-coloring
regimes, but that is not an average-case hardness proof. The observed G4 rate is only for a
uniform prior over exactly six nonempty unlabeled blocks—it does not model a
solver's learned prior. The canonical key uses 1-WL plus cell-edge counts and
is not a complete graph-isomorphism canonical form. Finally, the current
OpenRouter transcript proves only that the key was exhausted; it supplies no
LLM-hardness or G9 evidence, so this directory must not be submitted as a
finished family until those runs succeed.
