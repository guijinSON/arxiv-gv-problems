# arXiv 1508.07355 — anchored Hamilton cycles in walk traces

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | exact symbolic cyclic ordering |
| intuition | invariant: constant third finite difference modulo a prime |
| domain essentiality | native |
| reduction | paper-licensed: Section 1 maps a walk to its trace graph |

This module turns Frieze, Krivelevich, Michaeli, and Peled,
[*On the trace of random walks on random graphs*](https://arxiv.org/abs/1508.07355),
into a witness problem. The solver receives the simplified edge support of a
genuine walk trace on a complete graph and four ordered anchors, and must return
a Hamilton cycle beginning with those anchors. Verification is an exact
permutation and edge-membership check.

Trust status: every local gate G1–G9(c) passes. This includes 16/16 planted
checks, exact walk realizations, five distinct corruption failures, zero valid
answers in 200,000 structure-aware guesses, five attacks at 0/8, and 60/60
canonical-key relabelling checks. The mandatory four-vendor evidence is **not
complete**: on 2026-09-05 `harden.py` received HTTP 403 “Key limit exceeded
(total limit)” on every retry. Its error-only transcripts are retained and are
not counted as model failures. The result is not submission-ready until the
bare, hinted, and placebo runs complete with genuine responses.

## Construction and hardness claim

Section 1 defines a trace as the multigraph of traversed edges. Theorem 1 says
that for suitable `C` and `beta`, a length `(1+epsilon)n ln n` walk on
`G(n,p)`, with `p >= C ln(n)/n`, has a Hamiltonian and highly connected trace
with high probability. Theorem 2 sharpens this on `K_n`: Hamiltonicity appears
at `tau_C+1` with high probability. The easy side matters: the introduction
notes that at or below the cover-time scale a sparse-base trace is typically
not connected, and at `tau_C` the last vertex still has degree one.

Neither theorem is a search-hardness statement. Section 5 proves existence by
randomly sparsifying to an expander and performing up to `n` Pósa-booster
searches; it does not expose a short Hamilton-cycle formula. A Track A claim
would therefore be unsupported.

The move from the stochastic walk to its trace graph is paper-licensed rather
than a convenience discretization: Section 1 defines exactly this graph and all
three main results state properties of it. This generator is explicitly Track
B. It samples the Hamilton cycle first,
adds a perfect matching formed by two noncrossing pages, and shuffles the
edges. Every vertex has degree three. Doubling every edge gives an Eulerian
multigraph, so an Euler tour realizes the displayed graph exactly as the
simplified support of a walk on `K_n`. No search is used in generation.

The mechanical reference is exact anchored Hamilton DFS with feasibility and
connectivity pruning. At shipping `n=88` it solves 8/8 audited instances at a
median 1,601 search nodes, 203,822 counted adjacency operations, and 0.275
seconds in the final full audit; its worst-case complexity remains exponential. The compact route
recognizes that the four anchor labels begin a constant-third-finite-difference
sequence modulo 1,000,003 and extends it in exactly 258 modular operations.

## Worked demo (`n=8`, `seed=0`)

```text
Anchored Hamilton cycle in a random-walk trace

A walk on a graph produces a trace multigraph: every traversed undirected edge
is retained, with repetitions counted.  Its simplified trace suppresses all
parallel copies.  The instance below is the simplified trace of an actual walk
on the complete graph whose vertices are the displayed labels.

A Hamilton cycle is a cyclic ordering of all vertices exactly once such that
every consecutive unordered pair, including the last/first pair, is a trace
edge.  Find a Hamilton cycle whose first four vertices are, in this exact order,
the ordered anchors shown below.  Vertex labels are integer residues modulo
1000003; they are labels, not 0-based indices.  Repetitions are not allowed,
edge endpoints are unordered, and all bounds are inclusive.

Number of vertices: 8
Vertices:
403958 479564 593144 695715 794772 885440 933488 957065
Ordered anchors:
885440, 403958, 794772, 933488
Simplified trace edges (u-v denotes the unordered edge {u,v}):
479564-593144 933488-957065 695715-933488 794772-933488
403958-794772 695715-957065 403958-885440 593144-957065
479564-885440 403958-479564 593144-885440 695715-794772

Give your final answer inside <answer></answer> tags as one JSON list of exactly
8 integer vertex labels.  Example syntax: <answer>[12, 7, 31, 5]</answer>
The example illustrates syntax only; your list must have exactly 8 entries.
Output nothing else inside the tags.
```

The answer is
`[885440, 403958, 794772, 933488, 695715, 957065, 593144, 479564]`;
`verify` returns `(True, "ok")`. Dropping its final entry returns
`(False, "wrong_length: expected 8, got 7")`. A person can solve this demo on
paper either by extending the finite differences four times or by tracing the
small cubic graph.

## Difficulty presets

| preset | n | trace edges | answer elements | status |
|---|---:|---:|---:|---|
| demo | 8 | 12 | 8 | hand-scale; skipped by hardener |
| easy | 88 | 132 | 88 | shipping candidate |
| medium | 92 | 138 | 92 | escalation rung |
| hard | 96 | 144 | 96 | escalation rung |

The ladder first exhausts the locally balanced cubic construction. Increasing
`n` then enlarges the anchored permutation space while the answer remains
under the 256-atom cap. `escalate()` reaches `n=100`; the next supported rung
would exceed the 300-operation intended-route cap and reports `cap_bound`.

## Gate results

| gate | measured result |
|---|---|
| G1 | pass; 16/16 planted witnesses, JSON round-trips, and doubled-edge Euler realizations |
| G2 | pass; drop/swap/duplicate/empty/out-of-range rejected for five distinct reasons |
| G3 | pass; tagged prose and fenced JSON both round-trip |
| G4 | pass; 0/200,000 structure-aware guesses; language size `84!` |
| G5 | pass; shipping density 0/200,000; demo has 2/24 exact answers; strongest failing restart uses median 6,400 adjacency scans |
| G6 | pass; five attacks each 0/8; reference DFS and recurrence each 8/8 |
| G7 | pass; doubled `n=176` builds and verifies; every named candidate space grows |
| G8 | pass; 60/60 relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | pass; 606 actual / 705 worst-case characters, 177 estimated tokens, 88 atoms, 258 operations |

## Oracle loop and G9 diagnostic

No bare response was scored; these are provider errors, not solver failures.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | x-ai/grok-4.6 | 197810449 | error | OpenRouter HTTP 403 total key limit |
| easy | openai/gpt-5.6-terra | 1187079249 | error | OpenRouter HTTP 403 total key limit |
| easy | openai/gpt-5.6-terra | 1908020480 | error | OpenRouter HTTP 403 total key limit |
| easy | x-ai/grok-4.6 | 1509769251 | error | OpenRouter HTTP 403 total key limit |

| G9 arm | solved / scorable attempts | diagnostic |
|---|---:|---|
| bare | 0/0 | four error retries; no verdict |
| structural hint | 0/0 | four error retries; no verdict |
| placebo hint | 0/0 | four error retries; no verdict |

`hinted - placebo` is unmeasured (`null` in the report), so nothing can yet be
concluded about how much the invariant hint helps.

## Use

```python
import gen_1508_07355 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
raw = "<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(raw)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, after successful hardening:

```bash
bash scripts/emit.sh 1508.07355 20
```

## Caveats

- These graphs are genuine simplified walk traces, but they are deliberately
  inverse-generated cubic traces—not random samples from either asymptotic law
  in Theorem 1 or Theorem 2. The finite-difference labels are a benchmark
  construction, not a phenomenon claimed by the paper.
- `0/200000` estimates density only under a uniform permutation of the
  non-anchor vertices after the forced prefix. It does not bound a solver with
  a finite-difference prior or a stronger graph-search heuristic.
- The implemented attacks are degree/label outliers, deterministic fail-first
  greedy, 64 randomized restarts, constant-first-difference extrapolation, and
  spectral circular seriation. No industrial SAT/ILP, sophisticated Pósa
  rotation-extension implementation, or book-embedding reconstruction was run.
- The ordered-anchor-colored 1-WL key is a strong cheap invariant, not a
  complete graph-isomorphism canonical form; rare collisions remain possible.
- Most importantly, oracle hardness and all three G9 arms remain unmeasured
  because the supplied OpenRouter credential exhausted its total limit. Rerun
  the three script-owned harness calls before submission.
