# Four-round two-opinion good-seed search

This generator turns Knop, Schierreich, and Suchý’s [*Balancing the Spread of Two Opinions in Sparse Social Networks*](https://arxiv.org/abs/2105.10184) into an exact witness problem. The solver receives a compressed instance of the paper’s Section 5.2 reduction: `K` vertex-selection groups and one edge-selection group for every class pair. It returns the ordered global IDs of one added opinion-`b` seed per group (`T_a` is empty). The checker decodes every selected edge and confirms that its endpoints are exactly the selected vertices. Lemma 13 proves that these incidence checks are equivalent to all gadgets balancing after four rounds, so verification is linear in the returned witness and accepts any valid seed set, not only the plant.

## Why this is the hard version

Section 1 defines balance precisely as `P_a^T = P_a^(T+1) = P_b^T = P_b^(T+1)`: the two opinion sets must be equal and already stable. Section 5 defines Partitioned Subgraph Isomorphism and notes that its Partitioned Clique special case is W[1]-complete. The Section 5.2 reduction turns such a selection into the good seed pair used here; Theorem 7 proves W[1]-hardness, with an ETH lower bound, even when every successful process stabilizes in `T=4` rounds.

The parameters that make the paper’s problem easy are not held small. Section 3 gives the immediate copy-the-seed-sets solution when `B >= |S_a|+|S_b|`; the expanded construction has six initial `a` seeds per selection gadget plus special seeds, so `B` is strictly smaller. Theorems 1–3 give FPT algorithms for vertex cover, 3-path vertex cover, and vertex integrity. Theorem 4 is FPT for rounds, maximum threshold, and treewidth together. Here the number of classes `n`, budget, structural parameters, and reduction thresholds grow; only the four-round parameter is fixed. Fixed `n` would also permit `O(Q^n)` enumeration, so `n` is the principal scaling axis.

The semantic answer is sampled first. For every class pair the generator then makes an independent simple `R`-regular bipartite graph, selects one of its ordinary edges uniformly, and relabels that edge onto the planted endpoints. Plants and decoys therefore have identical pairwise degrees, and each planted edge comes from the same edge distribution as every other available edge.

## Worked example

For readability this uses the same construction at its supported minimum (`n=3, part_size=4, degree=2, mix_steps=3, seed=0`); named presets begin at the hardness-tested medium size.

```text
FOUR-ROUND TWO-OPINION GOOD-SEED SEARCH

This is the exact selection core of a four-round 2-Opinion Target Set
Selection instance. There are K vertex-selection groups (colour classes)
and one edge-selection group for every unordered pair of classes.
A good added seed set T_b chooses exactly one selection vertex from every
group; T_a is empty. The incidence gadgets balance after round 4 exactly
when every chosen edge has the two chosen vertex labels as its endpoints.
Thus no knowledge of opinion diffusion or of the source paper is needed:
the complete, exact witness conditions are stated below.

K = 3
Q = 4
R = 2
B = 6

Vertex groups are ordered by class c = 0,1,...,K-1. Class c has local
labels x = 0,1,...,Q-1. Choosing label x in class c means choosing the
global selection-vertex ID c*Q+x.

Edge groups are ordered by (i,j) in the PAIR lines below; the lines use
lexicographic order 0<=i<j<K. ROW_MASKS contains Q hexadecimal integers.
For row u, bit v (least-significant bit is v=0) is 1 exactly when edge
(u,v) is available. Leading zeroes have no meaning. Every row has R bits.
Available edges are ordered by increasing u and then increasing v. If a
PAIR has OFFSET o, edge (u,v) has global selection-vertex ID
o + R*u + (number of set bits below v in row u).

A valid witness is an ordered JSON array of exactly B distinct global IDs:
first one ID from each of the K vertex groups, then one ID from each PAIR
group in the displayed order. For every PAIR (i,j), its chosen edge must
equal (the chosen local label in class i, the chosen local label in class
j). Order is required, IDs are 0-indexed integers, and repeats are forbidden.

PAIR_DATA_BEGIN
PAIR 0 1 OFFSET 12 ROW_MASKS a,5,5,a
PAIR 0 2 OFFSET 20 ROW_MASKS 3,c,a,5
PAIR 1 2 OFFSET 28 ROW_MASKS a,5,c,3
PAIR_DATA_END

Give your final answer inside <answer></answer> tags, as one JSON array
containing exactly 6 integer global selection-vertex IDs.
Example of the required syntax (not a solution): <answer>[0,16]</answer>
Output nothing else inside the tags.
```

The planted witness is `[3, 7, 8, 19, 26, 34]`, and `verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping its last ID returns `(False, "wrong number of IDs: expected 6, got 5")`.

## Difficulty presets

| preset | classes `n` | `Q` | regular degree `R` | selected IDs `B` | rendered bytes (seed 0) | status |
|---|---:|---:|---:|---:|---:|---|
| medium | 16 | 16 | 11 | 136 | 15,397 | **ships; local gates and oracle held** |
| hard | 20 | 18 | 13 | 210 | 28,673 | available |
| extreme | 24 | 20 | 14 | 300 | 44,166 | available |

`escalate()` raises both `n` and `Q` while retaining about 70% pair density. No named preset was rejected.

## Gate results

| gate | measured result |
|---|---|
| G1 | 15/15 plants verified (3 presets × 5 seeds) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | 3/3 tagged/fenced model-style responses round-tripped; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses; effective prior space `16^16 = 18,446,744,073,709,551,616` |
| G5 | exactly 1 solution in 78,125 structure-aware candidates for each of 3 small seeds (`1.28e-5`) |
| G6 | triangle outlier 0/8, left-to-right greedy 0/8, randomized MRV with 32 restarts 0/8; regularity 8/8 |
| G7 | doubled `n=32` instance built; its 528-ID plant verified among 87,808 selectors |
| G8 | invariance 80/80, carried witnesses 80/80, unrelated keys distinct 20/20 |

The complete measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The required `harden.py` run used reasoning effort `medium` and hardened the first named preset without escalation. The Grok call is an excluded error, not hardness evidence. Claude used its entire 32,000-token completion budget without emitting an answer; this is scored as a failed attempt by the harness’s documented policy.

| preset | model | seed | result | exact evidence |
|---|---|---:|---|---|
| medium | Gemini 3.1 Pro Preview | 214003961 | failed | parsed; pair `(0,6)` ended at label 3, expected 0 |
| medium | Grok 4.6 | 1794705887 | API error | 900-second hard deadline; redrawn |
| medium | GPT-5.6 Terra | 1436320610 | failed | parsed; position 1 was outside vertex group 1 |
| medium | Claude Sonnet 5 | 225305638 | failed | empty length-limited response after 32,000 completion tokens |

## Use

```python
from gen_2105_10184 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2105.10184 20 medium
```

Run local gates with `python3 -c 'import gen_2105_10184 as g; print(g.selftest())'` from this directory. The oracle transcript and metadata were produced only by `python3 ../../scripts/harden.py gen_2105_10184.py`.

## Caveats

- Theorem 7 is worst-case hardness; it does not prove average-case hardness of these independently conditioned regular hosts. The attack panel and multi-vendor loop are empirical evidence for this distribution, not a reduction proving it hard on average.
- The module stores the Section 5.2 selection/incidence core rather than millions of mechanically implied auxiliary gadget vertices. `verify` checks Lemma 13’s exact incidence equivalence instead of materializing and simulating that graph. A consumer needing explicit social-network vertices must expand the paper’s fixed gadgets.
- `0/200,000` is an observed rate, not proof that the true probability is zero or even a confidence bound below `1e-6`. The G4 prior chooses every class label uniformly and then uses the uniquely matching edge selector whenever available; it is far stronger than uniform sampling over the raw ID product, but it is not a learned or solver-induced prior.
- All vertices have exactly degree `R` toward every other class. The outlier attack therefore used triangle participation rather than the tied degree statistic. The panel did not try SAT/ILP, full branch-and-bound, spectral recovery, tensor methods, or learned distinguishers.
- Too-small `n` is enumerable, while excessive pair density creates many accidental cliques. Changing the preset window without re-running G4, G5, G6, and the oracle can make the family easy.
- `canonical_key` uses common-neighbor signatures associated through class profiles. It is invariant under tested class permutations, independent within-class relabellings, matrix transposition, and input reordering, but it is not a complete graph-isomorphism canonizer and rare non-isomorphic collisions are possible.
