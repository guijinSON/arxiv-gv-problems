# Verified generator for arXiv:2307.10607

This module turns *[Parameterized Complexity of Biclique Contraction and Balanced Biclique Contraction](https://arxiv.org/abs/2307.10607)* into planted, automatically graded instances of bipartite `K1,*`-Contraction. The solver receives the paper's Section 3.1 gadget in a complete compact encoding and must name `q` set vertices. Those IDs expand deterministically into `k=4q` original graph edges; the checker unions their endpoints, rebuilds the quotient graph, and accepts exactly when it is a star. The checker never reads the planted `inst["answer"]`.

## Why this is a hard regime

Definition 7 and Lemma 8 in Section 2.1 give the exact witness semantics. Lemma 12 in Section 3.1 reduces Red-Blue Dominating Set (equivalently Set Cover) to a connected bipartite graph: a selected cover makes one connected witness set and all other vertices become singleton leaves. Here there are `3q` elements and every set is a triple, so any cover of at most `q` sets is an Exact Cover by 3-Sets. The forward construction contracts to a star, while Lemma 12's converse recovers a cover from any biclique contraction; thus the gadget remains equivalent when the requested target is `K1,*`. Theorem 1 proves the parent contraction problem NP-complete even on bipartite inputs, and Section 6.1 records NP-completeness of `Kp,*`-Contraction for every fixed positive `p`, including `p=1`.

The easy regimes matter just as much. Theorem 2 in Section 4 gives an `O*(25.904^k)` FPT algorithm, and Lemma 20/Theorem 5 in Section 6.2 improve this to `O*(2^k)` for `K1,*`. Consequently `k` grows linearly here rather than staying small. The fixed-`Kp,q` enumeration after Lemma 10 is avoided because the number of star leaves also grows with `q`. No polynomial-time or closed-form method is known; worst-case hardness does not, by itself, prove hardness of this planted distribution, so the adversary tests and oracle loop below are separate evidence.

## Worked `demo` instance (`seed=0`)

This is the complete output of `render` for the smallest preset:

```text
Find an edge-contraction witness that turns the graph below into a star.
A star is a complete bipartite graph K_{1,t}: one centre adjacent to every
other vertex, with no edges among the other vertices.

The graph is specified compactly but completely.
There are 12 element vertices B0,...,B11; matching pendant vertices
P0,...,P11; 12 set vertices S0,...,S11; one vertex x; and
17 guard leaves C0,...,C16.
Its undirected edges are exactly these (there are no other edges):
  * x--Sj for every set ID j from 0 through 11;
  * x--Ch for every guard index h from 0 through 16;
  * Bi--Pi for every element index i from 0 through 11;
  * Sj--Bi exactly when element i occurs in the triple listed for Sj.
The contraction budget is k=16. Contracting an edge merges its endpoints;
the merged vertex is adjacent to the union of their former neighbours, and
self-loops and parallel copies are discarded.

Return a compact witness consisting of exactly
q=4 distinct set IDs. The checker expands it into these contractions:
  1. contract x--Sj for every returned set ID j;
  2. for every element i, contract Bi--Sj where j is the unique returned
     set whose listed triple contains i.
Thus the expanded witness has exactly q+12=16 edges. It is accepted only
if every element has exactly one such selected set and replaying the
contractions produces a star. The order of returned IDs does not matter.
Set IDs and element IDs are 0-indexed; repeated IDs are forbidden.

Candidate triples (format: set ID: three element IDs):
S0: 3 5 11
S1: 3 6 10
S2: 6 7 9
S3: 1 4 8
S4: 0 4 7
S5: 1 2 8
S6: 0 3 9
S7: 5 6 11
S8: 0 3 7
S9: 4 9 10
S10: 2 5 9
S11: 3 10 11

Give your final answer inside <answer></answer> tags, as exactly q
comma-separated set IDs, with no S prefix.
Example: <answer>3, 17, 42, 8</answer>
Output nothing else inside the tags.
```

The planted witness is `<answer>5, 7, 8, 9</answer>`. `verify(inst, [5,7,8,9])` returns `(True, "ok")`. Replacing the last ID gives `verify(inst, [5,7,8,0]) == (False, "not an exact cover: element 4 is uncovered")`.

## Difficulty presets

| preset | `q=n` | triples | elements | `k` | gadget vertices | status |
|---|---:|---:|---:|---:|---:|---|
| `demo` | 4 | 12 | 12 | 16 | 54 | Oracle-solved; retained only for examples/enumeration |
| `easy` | 18 | 108 | 54 | 72 | 290 | **Ships; held all three scored oracle attempts** |
| `medium` | 28 | 168 | 84 | 112 | 450 | Local gates pass; not reached by oracle loop |
| `hard` | 42 | 252 | 126 | 168 | 674 | Local gates pass; not reached by oracle loop |

All planted triples and decoys are distinct 3-subsets with shuffled set and element labels. A whole decoy sample is accepted only if every element receives a decoy occurrence, meeting Lemma 12's minimum-degree assumption without adding recognizable repair sets.

## Gate results at shipping difficulty

| gate | measured result |
|---|---|
| G1 | 20/20 planted witnesses verified: four presets × five seeds |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 18 IDs recovered through prose plus a Markdown fence; garbage returned `None` |
| G4 | **0/200,000** valid uniform size-18 distinct-ID guesses; candidate space `139258480300974996780` |
| G5 | Exact demo counts: 2/495, 1/495, 1/495 solutions (0.404%, 0.202%, 0.202%) |
| G6 | Degree-outlier 0/8; rarest-first greedy 0/8; 256-restart random packing 0/8 |
| G7 | `n=18,k=72` and doubled `n=36,k=144` both build and verify; search space strictly grows |
| G8 | 60/60 key-invariance checks and 80/80 transformed-witness checks; 20/20 unrelated keys distinct |

`random_candidate` is structure-aware: it samples uniformly from exactly `q` distinct, in-range set IDs, so answer length, uniqueness, range, and the forced cardinality from 3-uniformity are already enforced. Its 0/200,000 rate is empirical under that prior, not a confidence bound for every heuristic or a claim that all candidate subsets are equally plausible to a solver.

## Required oracle loop

The repository-owned harness used reasoning effort `medium`; all nonempty responses parsed, so no visible answer was lost to a G3 bug.

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| demo | OpenAI GPT-5.6 Terra | 959737321 | solved | Valid cover |
| demo | xAI Grok 4.6 | 1773098575 | solved | Valid cover |
| demo | Anthropic Claude Sonnet 5 | 1500754253 | solved | Valid cover |
| easy | OpenAI GPT-5.6 Terra | 1320872136 | failed | Parsed 18 IDs; element 0 uncovered |
| easy | xAI Grok 4.6 | 955324403 | error | 900-second total deadline; not scored |
| easy | xAI Grok 4.6 | 1700012479 | error | 900-second total deadline; not scored |
| easy | Google Gemini 3.1 Pro Preview | 982170438 | failed | Parsed answer; element 2 uncovered |
| easy | Anthropic Claude Sonnet 5 | 522738086 | failed | Used all 32,000 completion tokens in reasoning and emitted no answer |

The harness verdict is `hardened`, with one escalation and shipping parameters `{"n":18,"set_factor":6}`. The Claude outcome is weaker evidence than an incorrect witness and is preserved as such in the transcript; the harness specification nevertheless scores an empty length-limited response as an unsolved attempt.

## Use

From this directory:

```python
import random
import gen_2307_10607 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=2026, **params)
question = gen.render(inst)
candidate = gen.parse_answer("<answer>1, 2, 3</answer>")
ok, reason = gen.verify(inst, candidate)
guess = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2307.10607 20 easy
```

Run all local gates with `python3 results/2307.10607/gen_2307_10607.py`.

## Caveats

The NP-completeness results are worst-case results for the problem class, not an average-case proof for this inverse-generated distribution. A dedicated Algorithm X/DLX, SAT, ILP, or branch-and-bound exact-cover implementation was not benchmarked; those are the most important attacks still missing. The rendered gadget deliberately exposes its exact-cover core, so a solver can ignore contraction mechanics after understanding the reduction. Small `q` (especially `demo`) is easy, small `k` is covered by the paper's FPT algorithms, and raising the set density may create many alternative covers and make search easier; `escalate` therefore holds density fixed and raises `q` only.

The G4 prior is uniform over correctly shaped selectors, while the restart attack is a separate biased disjoint-packing heuristic; neither models a full exact-cover solver. Only one random instance per scored vendor was used at the shipping rung, and one of the three failures emitted no answer because of the token cap. Finally, `canonical_key` is 12-round color refinement of the incidence graph, not an exact hypergraph-isomorphism canonizer. It is invariant under every tested element/set relabelling and strong enough to separate 20 unrelated samples, but specially constructed non-isomorphic systems can collide.
