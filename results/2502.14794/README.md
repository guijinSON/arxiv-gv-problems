# Square-Hamilton-cycle witness generator

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (intrinsically a cyclic permutation) |
| Intended intuition | constraint propagation through common neighborhoods |
| Domain essentiality | native |
| Reduction | none |

## What the family is

This module turns Maksim Zhukovskii's [*Sharp thresholds for spanning regular
subgraphs*](https://arxiv.org/abs/2502.14794) into an exact search problem.  The
solver receives a simple host graph and must return a cyclic ordering of all
vertices such that every pair at cyclic distance one or two is a host edge.
Those `2n` edges are the square of a Hamilton cycle.  The answer is a canonical
ordering (vertex 0 first, forward orientation lexically smaller than reverse),
so rotation and reversal do not create encoding ambiguity.  Verification is an
exact permutation check followed by `2n` integer bit-mask membership checks.

Generation is inverse, not solver-based: it samples the cyclic ordering first,
plants its `2n` edges, randomly relabels the vertices, and samples all remaining
edges without replacement to a near-threshold `G(n,m)` budget.  The planted
answer is carried through the relabelling.  `verify` never reads it.

## Why Track A is the honest claim

Section 1.2 defines the paper's native family as all isomorphic spanning copies
of a fixed regular graph.  Section 1.4, Theorem 1.7 proves that the square of an
`n`-cycle has sharp threshold `(1+o(1))*sqrt(e/n)`.  The shipping instance uses
`n=96`, 783 edges, and density `0.171711`, a factor `1.02` over that scale.

The theorem is an existence result, not a recovery algorithm.  Sections 1.5
and 6 use fragmentation, sampling among isomorphic copies, and counting; their
proof distributions do not give a polynomial-time finder for a presented host.
The related Nenadov--Skoric result cited in Section 1.2 gives a randomized
quasi-polynomial algorithm only when `p^2 >= C log^8(n)/n`, a much denser regime
([arXiv:1601.04034](https://arxiv.org/abs/1601.04034)).  I found no efficient
general method for the planted sharp-threshold distribution used here.

This is not a worst-case-to-average-case theorem.  The distributional evidence
is the measured panel: the natural exact DFS, which extends a partial ordering
through the common neighborhood of its last two vertices, exhausted 250,001
nodes on each of eight shipping seeds.  Five cheaper construction-aware probes
also failed on all eight.  The post-insight straight-line budget is 288 exact
operations for one proposed path (96 common-neighborhood intersections and 192
required-edge checks).  This is an exact-arithmetic/transcription budget, not a
claim that branch discovery is free: selecting the correct branches is the
combinatorial search being benchmarked, and no compact recovery algorithm is
claimed on Track A.

The easy regimes deliberately avoided are: a plant with almost no noise, whose
4-regular support exposes the answer; and a substantially denser host, where
large common neighborhoods and known above-threshold algorithms make recovery
easier.  The near-threshold budget keeps the local branching close to constant
without giving the planted edges a label or degree marginal unavailable to
decoys.

## Worked demo

For `make_instance(n=8, noise_factor_num=100, seed=731)`, the complete rendered
edge list is:

```text
vertices: 0 1 2 3 4 5 6 7
edges: 3-5 1-5 0-5 1-3 6-7 0-4 0-6 4-6
       4-5 1-2 2-6 1-4 2-3 3-7 2-7 0-7
```

The required definition is: for every position `i` modulo 8, both the edges
from `v[i]` to `v[i+1]` and to `v[i+2]` must occur.  A valid answer is:

```python
[0, 4, 5, 1, 3, 2, 7, 6]
```

`verify(inst, answer)` returns `(True, "ok")`.  Swapping the next two vertices
gives `[0, 5, 4, 1, 3, 2, 7, 6]`, which returns
`(False, "missing_square_edge:4-3_at_2+2")`.  This smallest setting is genuinely
hand-solvable: it has only 16 edges and exactly one canonical valid ordering.

## Difficulty presets

| preset | n | threshold factor | host edges | status |
|---|---:|---:|---:|---|
| demo | 8 | 1.00 | 16 | hand example; skipped by hardener |
| easy | 48 | 1.00 | 268 | exact DFS 0/8; oracle run blocked before scoring |
| medium | 72 | 1.01 | 502 | exact DFS 0/8; oracle not reached |
| hard | 96 | 1.02 | 783 | **proposed shipping preset; local gates pass** |

The earlier `n=12` draft was correctly solved by both available oracle vendors
on three out of three calls.  Before the harness could test the next rung, the
OpenRouter key reached its total limit.  A separate exact-search sweep also
solved 6/8 instances at `n=32` and 1/8 at `n=40`, but 0/8 at `n=48`; those
measurements are why the scored ladder now starts at 48.  No current preset has
a valid oracle verdict, so the proposed shipping label remains local-only and
must be confirmed by rerunning the hardener after quota is restored.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified; all JSON-native |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reason codes |
| G3 | pass | model-style fenced/prose response round-tripped; garbage -> `None` |
| G4 | pass | 0/200,000 uniform canonical-cycle guesses; required rate `<1e-6` |
| G5 | pass locally | shipping density 0/200,000; demo exact count 1/2,520; strongest attack 2,000,008 nodes, 3.001 s total |
| G6 | pass | six attacks, each 0/8 |
| G7 | pass | `n=192` built and verified in 0.007 s |
| G8 | pass | 60/60 invariance and witness-transport checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 374 chars, about 94 tokens, 96 atoms, 288 intended intersection/edge checks |

Attack details: degree/triangle ordering 0/8; greedy common-neighborhood
propagation 0/8; 256 randomized restarts 0/8; common-neighbor edge-outlier
scoring 0/8; centered-adjacency spectral seriation 0/8; exact
common-neighborhood DFS capped at 250,000 nodes 0/8.

## Oracle loop and G9 diagnostics

The current script-owned bare run made four draws at the revised easy preset.
Every request failed with HTTP 403 `Key limit exceeded (total limit)`, so the
harness correctly stopped without a verdict.  These are infrastructure errors,
not model failures:

| preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 664072979 | Gemini 3.8 Flash | error | OpenRouter HTTP 403 total key limit |
| easy | 1915909019 | GPT-5.6 Terra | error | OpenRouter HTTP 403 total key limit |
| easy | 1967415861 | GPT-5.6 Terra | error | OpenRouter HTTP 403 total key limit |
| easy | 477676674 | GPT-5.6 Terra | error | OpenRouter HTTP 403 total key limit |

| arm | valid solved/attempts | infrastructure errors | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | no hardness observation |
| structural hint | 0/0 | 4 | not run successfully |
| placebo hint | 0/0 | 4 | not run successfully |

The recorded `hinted_minus_placebo` placeholder is `0.0`, but with zero valid
attempts it has no experimental interpretation.  The structural hint names
only the invariant: each new ordering vertex lies in the common neighborhood
of the preceding two.  The answer and intended route remain within G9(c)'s
caps.  To complete the release evidence, restore OpenRouter quota and rerun the
three commands described below in separate directories.

## Use

```python
import random
import gen_2502_14794 as g

inst = g.make_instance(**g.DIFFICULTY["hard"], seed=7)
problem_for_solver = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == __import__("math").factorial(95) // 2
_ = g.random_candidate(inst, random.Random(1))
```

From the repository root, after a successful hardening run:

```bash
python3 scripts/harden.py results/2502.14794/gen_2502_14794.py
bash scripts/emit.sh 2502.14794 20
```

## Caveats

- The paper's theorem concerns unconditioned asymptotic `G(n,p)`.  The generator
  uses fixed-size noise conditioned to contain one randomly labelled copy.  The
  theorem motivates the parameter window but does not prove this planted
  distribution hard.
- `P(guess)=0/200,000` is for the exact uniform prior over canonical cyclic
  permutations.  It rules out blind guessing; it does not model a learned or
  construction-aware prior.
- The exact DFS is node-capped.  I did not run a commercial SAT/CP solver, an
  SDP, or every possible spectral embedding.  The spectral probe is a centered
  two-vector power iteration, not a completeness guarantee.  An additional
  score-based simulated-annealing probe made 400,000 swaps on each of four
  shipping instances and reached at most 158/192 required edges, but it is not
  counted in G6 because four seeds do not meet that gate's eight-seed minimum.
- The canonical key is a strong four-round Weisfeiler--Leman/edge-profile
  invariant, not a complete graph-isomorphism canonical form.  It is proven
  invariant under vertex and input-edge relabelling and separated all 20 audit
  seeds, but rare non-isomorphic collisions remain possible.
- Most importantly, no valid script-owned oracle or G9 attempt was obtained
  because the external key quota was exhausted.  The module is locally
  verified but is not release-complete until those script-owned runs succeed.
