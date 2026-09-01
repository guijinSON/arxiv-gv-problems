# Acyclic colouring generator for arXiv:2008.09415

This directory turns Bok et al., [*Acyclic, Star and Injective Colouring: A Complexity Picture for H-Free Graphs*](https://arxiv.org/abs/2008.09415), into a verified witness problem.  The solver receives a co-bipartite graph: two cliques `A` and `B`, plus a cross-adjacency matrix.  It must pair every `A_i` with one `B_j` so that the pairs form an acyclic `n`-colouring.  The witness is just the permutation of `B` indices.  Checking it takes quadratic time: every selected pair must be a nonedge, and every two selected pairs must avoid a bichromatic four-cycle.

## Why this is a hard regime

Section 1 defines an acyclic colouring as a **proper** colouring in which every two colour classes induce a forest.  Section 3, Lemma 8 proves that Acyclic Colouring is NP-complete on co-bipartite graphs.  Its exact equivalence is what the generator uses: a balanced bipartite graph has a connected perfect matching of size `n` if and only if its complement has an acyclic colouring with `n` colours.  Co-bipartite graphs are `3P1`-free, so this also lies in Theorem 1(i)'s hard side.

The easy boundary matters.  Section 2, Theorem 4 and Corollary 5 make every fixed-`k` acyclic-colouring problem polynomial-time solvable on `H`-free graphs when `H` is a linear forest.  Here `H = 3P1` is a linear forest, so fixing `k` would destroy the hardness claim.  The generator instead sets `k = n`, which grows with the instance, exactly as in Lemma 8.  It asks for a witness, not a minimum colouring.

The answer permutation is sampled first.  For every pair of planted matching edges, the two possible connecting edges are drawn uniformly from `10`, `01`, and `11`; these are precisely the three patterns that preserve connectedness.  This symmetric maximum-entropy conditional distribution avoids a preferred direction and gives visible plant and decoy nonedges the same representation.

## Worked shipping example

This is the full `render(make_instance(n=24, seed=0))` output from the smallest preset:

```text
Acyclic colouring of a co-bipartite graph

The graph has 2n vertices, where n = 24.  They are split into
A1,...,A24 and B1,...,B24.  Every two distinct A-vertices are adjacent,
and every two distinct B-vertices are adjacent.  Cross-adjacency is given by
the matrix below: entry 1 means A_i is adjacent to B_j, and entry 0 means they
are nonadjacent.  The graph is undirected, simple, and has no loops.

    B1 B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24
A1: 0 0 1 0 1 0 1 0 0 1 1 1 0 0 0 1 0 0 1 0 0 0 0 0
A2: 0 1 0 1 1 0 0 0 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0
A3: 0 0 0 0 1 0 0 1 1 0 0 1 1 0 1 0 1 0 0 1 0 1 0 0
A4: 0 0 0 0 0 1 1 0 0 0 0 0 0 0 0 0 0 0 1 0 0 1 0 0
A5: 0 0 1 0 0 0 0 0 1 1 0 0 0 0 0 1 1 0 0 0 0 1 0 0
A6: 0 0 0 0 0 1 0 0 0 0 1 0 1 0 0 0 1 0 0 0 1 0 1 0
A7: 1 0 0 0 1 0 0 1 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0
A8: 0 0 0 0 0 0 0 0 0 0 0 1 0 0 1 0 0 0 1 1 0 0 1 0
A9: 0 0 0 0 1 0 0 1 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 0
A10: 0 1 1 1 0 0 0 1 0 1 0 0 1 0 0 0 0 0 0 0 1 1 0 0
A11: 1 0 0 0 0 0 0 1 0 0 1 1 1 0 0 0 0 0 0 1 1 0 1 0
A12: 0 0 0 0 0 0 0 1 1 1 0 0 0 1 0 0 0 1 0 1 0 0 1 0
A13: 0 0 0 0 0 1 1 0 0 1 1 0 0 0 0 0 1 0 0 0 0 1 1 1
A14: 0 1 0 0 1 1 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 1
A15: 1 0 0 0 1 0 0 0 1 1 1 0 0 0 0 1 0 0 1 0 1 1 1 0
A16: 1 1 1 0 0 0 0 0 0 0 0 1 0 0 0 1 1 1 0 0 0 0 1 0
A17: 0 1 0 0 0 0 0 1 0 0 0 1 0 0 0 0 0 0 1 1 0 1 0 0
A18: 1 1 0 0 1 0 0 1 1 1 0 1 0 0 0 0 0 0 0 0 0 1 0 0
A19: 1 0 1 0 0 0 0 0 1 0 1 0 0 1 0 0 0 0 0 0 1 0 0 1
A20: 1 1 1 0 1 0 0 1 0 1 0 0 0 0 1 0 0 0 0 1 1 1 0 0
A21: 0 0 0 1 0 0 0 1 0 0 1 1 1 0 0 0 0 0 0 0 0 1 0 0
A22: 0 0 1 0 0 0 0 1 1 0 1 0 1 0 1 1 0 1 0 0 0 1 1 0
A23: 1 1 1 0 1 0 0 1 1 1 1 1 0 0 1 0 0 0 0 1 0 0 1 0
A24: 1 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0 0 0 1 1 0 1 1 0

A proper colouring assigns one of the colours 1,...,24 to every vertex and
never gives adjacent vertices the same colour.  It is acyclic when, for every
two colours, the subgraph induced by all vertices having either colour contains
no cycle.  Find an acyclic colouring using at most 24 colours.

Because each of A and B is a clique of size 24, every such colouring must pair
each A_i with exactly one B-vertex.  Report the pairing as exactly 24 integers
p1,...,p24: p_i = j means A_i and B_j receive the same colour.  The integers
must be a permutation of 1,...,24; order is by A-index, and indices are
1-based.  Repetitions are forbidden.  Colour names do not need to be reported.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example format: <answer>3, 1, 2</answer>
Output nothing else inside the tags.
```

The planted witness is:

```text
<answer>15, 1, 18, 8, 7, 12, 23, 22, 11, 5, 3, 21, 4, 20, 6, 19, 10, 24, 16, 17, 9, 2, 14, 13</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Replacing its second entry with `15` duplicates a column, and `verify` returns `(False, "entries must be a permutation of 1..24")`.

## Difficulty presets

| Preset | `n` | Graph vertices | Naive permutation space | Status |
|---|---:|---:|---:|---|
| easy | 24 | 48 | `24! = 620448401733239439360000` | **ships; held all three oracles** |
| medium | 32 | 64 | `32!` | Local gates pass; oracle not reached |
| hard | 40 | 80 | `40!` | Local gates pass; oracle not reached |

No preset was rejected.  `escalate` increases `n` by at least eight because the permutation dimension is the genuine cost axis for this family.

## Gate results at the shipping preset

| Gate | Result |
|---|---|
| G1 planted verifies | 15/15 preset/seed checks |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | 24 entries recovered through prose and a Markdown fence |
| G4 structure-aware guessing | 0/200,000; guesses were already perfect matchings of visible nonedges |
| G5 sparse audit | 3/362,880 valid at `n=9, seed=1` (`8.2672e-6`) |
| G6 outlier attack | 0/8 seeds solved |
| G6 deterministic greedy | 0/8 seeds solved |
| G6 random MRV, 64 restarts | 0/8 seeds solved |
| G7 scaling | planted witness verifies at doubled `n=48` |
| G8 canonical key | 140/140 transforms invariant; 140/140 carried witnesses verify; 20/20 unrelated keys distinct |

## Oracle hardening loop

The harness used reasoning effort `medium` and stopped with `verdict: hardened`, `shipping_params: {"n": 24}`.

| Preset | Model | Seed | Solved? | Evidence |
|---|---|---:|---|---|
| easy | `anthropic/claude-sonnet-5` | 934859278 | No | Exhausted 32,000 completion tokens in reasoning and emitted no answer |
| easy | `openai/gpt-5.6-terra` | 367308152 | No | Parsed permutation creates a bichromatic four-cycle at rows 1 and 22 |
| easy | `google/gemini-3.1-pro-preview` | 1598628796 | No | Parsed permutation pairs A8 with adjacent B5 |

The empty Claude response is explicitly recorded as length-limited by `harden.py`; it was not a visible answer rejected by `parse_answer`.

## Use

From this directory:

```python
import random
import gen_2008_09415 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
candidate = gen.parse_answer("<answer>...</answer>")
ok, reason = gen.verify(inst, candidate)

# A structure-aware baseline candidate already pairs only visible nonedges.
baseline = gen.random_candidate(inst, random.Random(999))
```

From the repository root, emit a deduplicated JSONL sample with:

```bash
bash scripts/emit.sh 2008.09415 20 easy
```

Run the local gates with `python3 results/2008.09415/gen_2008_09415.py`.

## Caveats

Lemma 8 proves worst-case NP-completeness for the full co-bipartite family, not average-case hardness for this planted distribution.  Small `n`, fixed `k`, a distribution with too many `11` patterns, or a statistical planting leak could make instances easy.  The equal-weight `10/01/11` construction and the three attacks address obvious leakage, but they are not a cryptographic proof.

The 0/200,000 figure is empirical under a randomized algorithm that produces perfect matchings of the visible nonedges.  It is deliberately much stronger than uniform sampling from all `24!` permutations, but it is neither uniform over all perfect matchings nor a statistical upper confidence bound on every guessing strategy.  The panel did not test an industrial SAT/ILP solver, a spectral planted-clique method, or exhaustive branch-and-bound.  The oracle evidence covers three vendors, but one failure was a token-budget exhaustion rather than a wrong witness.

Finally, `canonical_key` is exact whenever bipartition-aware colour refinement makes every row and column a singleton, as it did in the tested shipping instances.  On a rare highly symmetric input it falls back to an equitable-quotient invariant; that fallback is relabelling-invariant but can over-collapse non-isomorphic graphs.  It never uses the seed, renderer, or planted answer.
