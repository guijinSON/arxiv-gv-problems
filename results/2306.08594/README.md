# arXiv:2306.08594 — directed resolving sets in DAGs

> **Build status:** the generator and all local gates G1–G9(c) pass. The required external hardening verdict is incomplete: OpenRouter returned HTTP 403 “Key limit exceeded (total limit)” on every bare, hinted, and placebo redraw. Those errors are preserved in the script-owned transcripts and are not counted as oracle failures.

| Profile field | Value |
|---|---|
| Track | **A** — structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple: a normal-form directed resolving set |
| Intuition | reduction recognition: all unresolved information is concentrated in same-layer sink pairs |
| Domain essentiality | licensed reduction |
| Reduction | DAG-section NP-completeness proof, Hitting Set → Directed Metric Dimension |

## What the family is

Schmitz and Wanke’s [*The directed metric dimension of directed co-graphs*](https://arxiv.org/abs/2306.08594) defines a directed resolving set using distances **from** selected vertices. Its final section proves that Directed Metric Dimension is NP-complete even for directed acyclic graphs by transforming a Hitting Set family into a layered DAG.

This module uses that construction with one explicit strengthening needed to make its intended equivalence exact: the first vertex in the `b`-chain is a dummy ground vertex that belongs to no set and is not an answer choice. Without it, `b` can itself distinguish `P_j,Q_j` whenever the first ground vertex lies in `F_j`. The generator first samples one value from each choice group, then creates balanced NAE-style set pairs that the sample hits. For every set `F_j`, the DAG contains vertices `P_j,Q_j`; a selected ground vertex separates that pair exactly when it lies in `F_j`. Thus `a,b,c` plus the planted transversal is known before the DAG exists. `verify` reconstructs every exact directed-distance signature and compares them; it never reads `inst["answer"]`. A separate self-test materializes all arcs and runs literal BFS on every demo candidate to cross-check the symbolic verifier.

## Why Track A, and the easy regime avoided

Section 3, Theorem 2 gives the relevant worst-case result: the reduction preserves a Hitting Set of size `k` as a resolving set of size `k+3`. The shipping preset has 36 growing choice groups, ten values per group, one non-candidate dummy, 264 balanced NAE rows, 564 Hitting Set members, and a normal-form space of `10^36`. Candidate plants and decoys have exactly equal incidence frequency because every row is paired with its complement and every group appears once per regular round.

The strongest implemented baseline is q-ary DPLL with MRV and NAE unit propagation. Its worst case is `O(q^groups)`. At shipping size it exhausted 20,000 nodes in **9.127 s** on the final G5 run without solving; across eight G6 seeds it exhausted 160,000 nodes in **107.312 s** and solved 0/8. Incidence outlier, one-pass greedy, and 64 min-conflicts restarts of 720 steps each also solved 0/8.

The paper’s main positive result is deliberately not used: Section 2, Theorem 1 computes a minimum resolving set for a strongly connected directed co-graph in linear time. Such a family would fail Track A. The number of choice groups grows through the named ladder to 36; beyond `hard`, `escalate` enlarges each group’s value haystack while keeping the 39-atom answer and the at-most-300-check route fixed.

The Track-A qualification matters: the paper proves worst-case NP-completeness, not average-case hardness for this planted distribution. The measured attacks support the distributional claim but do not prove it; see Caveats.

## Worked demo

This is the complete rendering of `make_instance(n=2, groups=3, rounds=3, dpll_node_budget=500, seed=0)`:

```text
DIRECTED RESOLVING SET IN A RULE-DEFINED DAG

For vertices u,v in a directed graph, d(u,v) is the number of arcs in a shortest directed path from u to v. If no such path exists, d(u,v) is undefined. An undefined distance is not equal to, and cannot be compared with, any distance. A vertex w resolves distinct u,v when w is u or v, or when both d(w,u) and d(w,v) are defined and unequal. A set R is resolving when every pair of graph vertices is resolved by some w in R.

There are 7 integer-labelled ground vertices. Exactly 6 of them are partitioned into 3 displayed choice groups G_0,...,G_2, each of size 2. The remaining dummy ground vertex is 7; it belongs to no set F_j and is not an allowed answer entry. Group order and the order inside a group are significant only for the required answer format:
G_0: 5 3
G_1: 2 1
G_2: 6 4

Define a family F_0,...,F_8 of 9 subsets of the ground vertices. For 0 <= i < 3, F_i=G_i. Each row t below has three group indices i,j,k and three displayed half-groups A,B,C. It defines F_(g+2t)=A union B union C and F_(g+2t+1)=(G_i\A) union (G_j\B) union (G_k\C). Complements are within the named group; no other ground vertex belongs to either set.

t | i:A | j:B | k:C
0 | 2:6 | 0:3 | 1:2
1 | 2:6 | 1:1 | 0:5
2 | 1:1 | 0:3 | 2:6

The directed graph has source vertices a,b,c; every integer ground vertex; and two vertices P_j,Q_j for each set F_j. Its arcs are exactly these:
1. a has an arc to every ground vertex.
2. In the ground order printed below, b has an arc to the first vertex and each ground vertex has an arc to the next one.
3. c has arcs to P_0 and Q_0.
4. P_j has an arc to Q_j for every j.
5. For every j before the last layer, each of P_j,Q_j has arcs to both P_(j+1),Q_(j+1).
6. Every ground vertex x has an arc to every P_j.
7. A ground vertex x has an arc to Q_j exactly when x is not in F_j.
There are no other arcs. All arcs point forward in the displayed construction, so this graph is acyclic.
Ground order: 7 3 5 6 4 1 2

Find a resolving set in the required normal form R=["a","b","c",r_0,...,r_2]. For every i, r_i must be exactly one integer label from G_i. The prefix and group order are mandatory, repetitions are forbidden, and the list therefore has exactly 6 entries. Other resolving sets are outside this certificate language.

Give your final answer inside <answer></answer> tags as one JSON list. Strings must be quoted and integers must be decimal.
<answer>["a","b","c",1,2,3]</answer> is a format example only; it is not the answer to this instance.
Output nothing else inside the tags.
```

The planted answer is `<answer>["a","b","c",3,1,4]</answer>`, and `verify` returns `(True, "ok")`. Replacing the last entry by `6` returns `(False, "unresolved layer pair P_8,Q_8: the selected vertices miss F_8")`. A person can solve this demo by checking only `2^3=8` normal-form candidates.

## Difficulty presets

| Preset | Values/group | Groups | Rounds | Ground vertices | Set layers | DAG vertices | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 3 | 3 | 7 | 9 | 28 | 6 | hand example |
| easy | 4 | 18 | 9 | 73 | 126 | 328 | 21 | oracle not reached: key limit |
| medium | 6 | 24 | 12 | 145 | 216 | 580 | 27 | locally available |
| hard | 10 | 36 | 22 | 361 | 564 | 1,492 | 39 | provisional shipping preset |

No current preset was rejected by a local gate. An earlier candidate for `hard` (30 groups, 18 rounds) was discarded after uncapped DPLL found a witness in 13,729 nodes and about 3.8 seconds; the former 1,000-node panel had hidden that break. A later eight-values/21-rounds candidate was also discarded when the optimized min-conflicts attack solved 1/8 seeds. The present hard rung grows the fixed-length value haystack to ten and raises density to the 300-operation G9 ceiling. It remains provisional because STEP 4 did not obtain a model response.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verify; every answer JSON-round-trips; symbolic verification is cross-checked against explicit BFS on every demo candidate |
| G2 | pass | required five corruptions rejected with five distinct reasons; an additional same-group substitution also rejected |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses from `10^36` candidates |
| G5 | pass | shipping observed density 0/200,000; DPLL 20,000 nodes, 9.127 s, unsolved; demo has exactly 4/8 answers |
| G6 | pass | frequency, greedy, 64-restart min-conflicts, and 20,000-node exact DPLL all 0/8; DPLL aggregate 160,000 nodes / 107.312 s |
| G7 | pass | all named work sizes grow; doubling `n` to 20 builds 2,284 vertices and verifies |
| G8 | pass | 60/60 relabelling invariance checks and 60/60 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 152 chars, 38 estimated tokens, 39 atoms, 300 intended operations |

## Oracle loop

The bare transcript was written only by `scripts/harden.py`. These are API errors, not failed solving attempts, so there is no hardness verdict.

| Preset | Model | Seed | Result | Why |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 2083052671 | error | OpenRouter HTTP 403 total key limit |
| easy | GPT-5.6 Terra | 1438899362 | error | redraw; same HTTP 403 |
| easy | GPT-5.6 Terra | 1689553496 | error | redraw; same HTTP 403 |
| easy | Gemini 3.8 Flash | 637055552 | error | redraw; same HTTP 403; harness stopped |

## G9 arms

| Arm | Solved / attempts | Script calls | Status |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | all HTTP 403; unavailable |
| structural hint | 0 / 0 | 4 | all HTTP 403; unavailable |
| placebo hint | 0 / 0 | 4 | all HTTP 403; unavailable |

The hinted-minus-placebo diagnostic is unavailable; the numeric `0.0` in `selftest_report.json` is only the zero-attempt sentinel and supports no conclusion about the stated intuition. The structural hint names only the same-layer signature invariant. The size/effort arm passes at 152 characters, 39 atoms, and 300 operations.

## Use

The module is standard-library-only; this finite-discrete family does not require `gvlib`.

```python
from gen_2306_08594 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
raw = "Reasoning omitted. <answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
assert parse_answer(raw) == inst["answer"]
```

From the repository root, after obtaining a valid hardening verdict:

```bash
bash scripts/emit.sh 2306.08594 20 hard
```

## Caveats

Theorem 2 proves worst-case NP-completeness for DAGs; it does **not** prove this balanced planted distribution hard. The 0/200,000 result is an observed rate under the precise prior “uniformly choose one displayed value per group”; it is not a confidence proof that every informed strategy has probability below `1e-6`. The exact baseline is node-capped, so it shows that this particular search prefix is costly, not that uncapped DPLL never finishes.

The theorem proof’s claim that only ground vertices in `F_j` can resolve `P_j,Q_j` is sensitive to the ground-chain order: source `b` would also resolve the pair if the first ground vertex belonged to `F_j`. Generated instances avoid that case constructively by putting a single unused ground vertex first and making it a member of no set. The explicit-BFS cross-check tests this repaired regime, but this module should not be read as validating the proof for arbitrary Hitting Set instances without that condition.

No external SAT/SMT/ILP package, LP relaxation, SDP, or planted-CSP spectral/tensor recovery was available or run. A successful one would invalidate Track A and require redesign or an honest Track-B relabelling. The canonical key is a strong multiset of complementary-clause intersection statistics, not a complete hypergraph-isomorphism canonizer. Finally, the mandatory multi-vendor oracle evidence is missing because of the external key limit; this directory is reproducible and locally verified but must not be submitted as hardened until all three arms are rerun successfully.
