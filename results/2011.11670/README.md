# Proper tree-graph compact representations (arXiv:2011.11670)

> **Status:** locally verified, but **not yet shippable**. G1–G8 pass. The bare
> oracle ladder reached `hard` and two scored hard attempts failed, but the shared
> OpenRouter key exhausted its total credit before the third attempt. G9's hinted
> and placebo arms therefore could not run. No hardness verdict is claimed.

| Profile field | Value |
|---|---|
| Track | **B** — an efficient mechanical algorithm is disclosed |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `graph` |
| Certificate form | `integer_tuple` (a clique-to-host assignment) |
| Intended intuition | `decomposition` |
| Domain essentiality | `native` |
| Reduction | none |

## What the family asks

The source is Chaplick, Golovach, Hartmann, and Knop,
[“Recognizing Proper Tree-Graphs”](https://arxiv.org/abs/2011.11670). A solver is
given a graph `G` and a host tree `T`. It must put one maximal clique of `G` on
each nonleaf of `T`; the model of graph vertex `v` is the set of host nodes whose
cliques contain `v`. The required witness is a list of simplicial graph vertices,
whose closed neighborhoods name those maximal cliques.

This is the paper's native compact representation. Section 3, Definition 4 gives
conditions (C1)–(C3): leaves are empty, nonleaves correspond bijectively to
maximal cliques, and every ordered vertex pair has an escape edge. Section 3's
compact-representation theorem (Theorem 7) proves equivalence with a proper
`T`-representation for connected graphs and `T != K1`. `verify` checks clique
maximality, every model's connectedness, the complete intersection graph, and
every escape condition exactly; it never reads `inst["answer"]`.

## Why Track B, not Track A

Theorem 1 gives a recognition-and-construction algorithm in
`2^{O(t^2 log t)} N^3` time, where `t` is the host-tree size and `N` the graph
size. The introduction also records linear-time recognition for the proper
interval and proper circular-arc special cases. Those results rule out an honest
Track A claim at fixed or small `t`.

For this generated distribution, a stronger specialization exists: enumerate
the distinct maximal closed neighborhoods of simplicial vertices, build their
nonempty-intersection tree, and run AHU rooted-tree isomorphism. Its complexity
is `O(N^2 Delta + k^2 s + k^2 log k)` with the direct exact implementation here.
Across eight shipping seeds it solved 8/8, using at most 35,723 primitive
set/adjacency operations and 0.004780 seconds. The intended compressed route is
the clique-tree decomposition itself, measured at 287 object visits. Thus the
benchmark claim is only the no-tool gap between a roughly 36k-operation
mechanical route and recognizing/executing the 287-visit decomposition.

Generation is inverse, not recognition: it samples a tree and connected
singleton/edge models first, computes their intersection graph, then carries the
witness through independent random relabellings of graph and host. It never runs
the reference solver.

Section 5, Theorem 2 does prove NP-completeness for a fixed non-tree host via
height-one interval dimension three. I did not use that to make a Track A claim:
a prototype formed from three random planted interval orders fell to incremental
cycle-pruning in roughly 300 nodes and 0.07 seconds at 20+20 elements. Worst-case
hardness did not survive that inverse distribution.

## Worked `demo` example (`seed=7`)

This smallest setting is hand-solvable. The complete rendered instance is:

```text
COMPACT PROPER-TREE REPRESENTATION

All graph and host-tree vertex identifiers are 0-based. The two kinds of
identifier are separate.

For a graph vertex v, its closed neighborhood N[v] is v together with every
graph neighbor of v. A clique is a set of pairwise adjacent graph vertices. It
is maximal if no strictly larger clique contains it. A host node is a leaf
exactly when its host-tree degree is one.

Your certificate is one graph-vertex identifier for each nonleaf host node, in
the increasing host-node order printed below. At host node x, the chosen graph
vertex v installs the clique N[v]. Every chosen N[v] must be maximal; these
cliques must be distinct and must use every distinct maximal-clique neighborhood
exactly once. Host leaves install the empty clique.

For each graph vertex u, define its model M_u as the host nodes whose installed
clique contains u. The certificate is valid exactly when:
(1) every M_u is nonempty and induces a connected host subtree;
(2) two distinct graph vertices are adjacent exactly when their models
intersect; and
(3) for every ordered pair (u,v), including u=v, some oriented host edge x->y
has u in the clique at x and v absent from the clique at y. This is the paper's
escape condition. These conditions, empty host leaves, and the maximal-clique
bijection define a compact representation. Order matters only because list
position names a host node; graph identifiers may not repeat.

Graph G has 9 vertices. Its adjacency list is:
0: 2 3 5 6
1: 6
2: 0 3
3: 0 2 4 8
4: 3 8
5: 0 6
6: 0 1 5
7: 8
8: 3 4 7

Host tree T has 7 nodes. Its adjacency list is:
0: 2
1: 2 3
2: 0 1
3: 1 4
4: 3 6
5: 6
6: 4 5

Nonleaf host nodes, in certificate order: 1 2 3 4 6
The answer must be a JSON list of exactly 5 integers.
Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[5, 1, 2, 4, 7]</answer>` and `verify` returns
`(True, "ok")`. Dropping the final entry gives `[5, 1, 2, 4]`, for which it
returns `(False, "wrong number of representatives: expected 5")`.

## Difficulty presets

| Preset | Core cliques `n` | Graph vertices | Answer atoms | Status |
|---|---:|---:|---:|---|
| `demo` | 5 | 9 | 5 | hand example; skipped by hardening |
| `easy` | 40 | 79 | 40 | oracle solved 2/3 |
| `medium` | 68 | 135 | 68 | oracle solved 1/3 |
| `hard` | 96 | 191 | 96 | provisional shipping preset; 0/2 scored before key exhaustion |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; JSON round-trip |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged/fenced prose round-trip; garbage -> `None` |
| G4 | pass | 0/200,000 structure-aware guesses |
| G5 | pass | shipping density 0/200,000; demo has 2/120 valid; reference 34,127 ops on measured seed |
| G6 | pass | four attacks each 0/8; reference algorithm 8/8 |
| G7 | pass | doubled `n=192`, 383 graph vertices, planted witness verifies |
| G8 | pass | 60 relabelling invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **blocked** | caps pass (433 chars, 109 estimated tokens, 96 atoms, 287 operations); oracle arms incomplete |

The structure-aware G4 prior already gives a hypothetical solver every distinct
simplicial maximal-clique class and samples only a random class-to-host bijection.
The bounded answer space at shipping is `96!`; it does not inflate difficulty by
sampling malformed vertex lists.

## Bare oracle loop (partial script-owned evidence)

| Preset | Model / seed | Result | Checker reason |
|---|---|---|---|
| easy | Grok 4.6 / 67213885 | solved | `ok` |
| easy | GPT-5.6 Terra / 1664824595 | solved | `ok` |
| easy | Claude Sonnet 5 / 1735519173 | failed | no tagged answer |
| medium | Claude Sonnet 5 / 1606730087 | failed | empty length-limited response |
| medium | GPT-5.6 Terra / 1867206074 | failed | disconnected model |
| medium | Grok 4.6 / 305886646 | solved | `ok` |
| hard | Grok 4.6 / 1854426834 | failed | empty provider-error response |
| hard | Gemini 3.1 Pro / 2007320662 | failed | wrong answer length |
| hard | remaining slot | **not scored** | HTTP 403 key limit on every redraw |

The partial `llm_loop_transcript.jsonl` is preserved exactly as written by
`harden.py`; `.meta.json` intentionally has no `harden_verdict`. This is not a
`hardened` result.

## G9 arms

| Arm | Solved / attempts | Status |
|---|---:|---|
| bare (`hard`) | 0/2 | incomplete; third attempt blocked |
| structural hint | 0/0 | not run |
| placebo hint | 0/0 | not run |

`hinted - placebo` is therefore undefined (stored as `null`, with
`oracle_evidence_ready=false`). No conclusion about the decomposition hint is
drawn. When credit is restored, rerun bare from scratch, then run hinted and
placebo in separate one-rung scratch directories as required.

## Use

```python
import random
import gen_2011_11670 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
text = g.render(inst)
candidate = g.parse_answer("<answer>[5, 1, 2, 4, 7]</answer>")
assert g.verify(inst, candidate) == (True, "ok")
other = g.random_candidate(inst, random.Random(1))
```

After the missing oracle evidence is completed and G9 passes, emit from the repo
root with `bash scripts/emit.sh 2011.11670 20 hard`. Do not emit the current
incomplete result.

## Caveats

- This distribution is in P and deliberately Track B. Access to a graph library,
  a script, or enough scratch space makes it easy; the reference algorithm proves
  that rather than merely suggesting it.
- The family would also become easy by exposing the generating models or matching
  graph/host labels. Neither is rendered. Small `n` is demonstrably easy: the
  oracle results reject both lower rungs.
- Zero hits in 200,000 guesses gives an empirical upper signal under the stated
  uniform-bijection prior; it is not a proof about informed or nonuniform guesses.
- The attack panel covers clique-size outliers, one-hop greedy signatures, 256
  random restarts, and two-round color refinement. It does not test every graph
  canonization package; full AHU is instead disclosed as the successful reference.
- The hard-preset and G9 oracle evidence is incomplete solely because the shared
  OpenRouter key reported zero remaining credit. A fresh complete run may still
  show that `hard` or the structural hint is too easy; if so, the family must be
  escalated or rejected rather than shipped.
