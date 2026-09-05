# arXiv 2201.08647 problem generator

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (an edge set in the paper's native graph) |
| Intended intuition | invariant: consistently orient a matching by a common modular ratio |
| Domain essentiality | native |
| Reduction | none |

## What the problem is

This generator is based on Kurita and Wasa, [“An Approximation Algorithm for
K-best Enumeration of Minimal Connected Edge Dominating Sets with Cardinality
Constraints”](https://arxiv.org/abs/2201.08647). It hands the solver an explicit
connected simple graph with a universal centre and a distinguished perfect
matching among the other vertices. The answer is a set of centre-to-leaf edges
forming a minimum connected edge dominating star.

The matching is an executable lower bound, not an appeal to an external
theorem. A valid answer selects one endpoint of every matching edge and meets
every leaf edge. The matching forces any leaf vertex cover to use at least
`n` vertices. The submitted `n` spokes attain that bound, form a connected
tree, and each has its matching edge as a private edge. Exact incidence,
disjointness, cardinality, and private-edge checks therefore certify minimum
and inclusion-minimality.

## Why Track B

Section 2 fixes the definitions, and Proposition 4 gives the private-edge
characterisation of minimality used by the checker. The paper also identifies
what is easy: Lemma 5 reduces a connected edge dominating set to a minimal one
in `O(m)`, Theorem 16 enumerates all minimal solutions with
`O(n m² Δ)` delay, and Theorem 18 gives 4-approximate K-best enumeration after
polynomial preprocessing. The Introduction cites worst-case NP-hardness of the
minimum problem, but that does not make this generated distribution Track A.

The generated special case has a successful `O(|V|+|E|)` algorithm: build the
leaf adjacency lists and BFS two-colour them. At shipping size this costs 3,840
counted adjacency insertions/examinations, roughly 0.0006 seconds averaged over
eight seeds. The compact route notices that the unordered edges of the supplied
matching can all be oriented with the same endpoint ratio modulo the prime
`p=2n+1`. One modular inverse and one multiplication per pair recover a whole
colour class in 137 counted exact operations. Generation chooses that class
first in the square/nonsquare cosets of `F_p*`, so it never solves its output.

## Worked demo

`make_instance(seed=0, n=5, degree=3)` renders in full as:

```text
MINIMUM CONNECTED EDGE DOMINATING STAR

The following data define one finite undirected simple graph G. Its vertex
labels are the integers 0 through 10. The distinguished center is 0. The other
10 displayed vertices are called leaves. The graph contains center--v for
every leaf v, plus exactly the displayed leaf edges below, and no other edges.
An item u-v denotes the unordered edge {u,v}.

Two edges dominate one another when they share an endpoint; an edge therefore
dominates itself. An edge set F is connected edge dominating when its
edge-induced subgraph is connected and every edge of G is dominated by an edge
of F. It is minimal if deleting any edge destroys connectivity or domination,
and minimum if no connected edge dominating set has fewer edges.

Your answer must be a strictly increasing JSON list of exactly n=5 distinct
leaf labels. It denotes F={center--v : v occurs in the list}. Order has no
mathematical significance, but increasing order is required for an unambiguous
serialization. Labels are 0-based integers and all stated bounds are inclusive.

The instance also supplies a lower-bound matching of n=5 pairwise-disjoint
leaf edges. Your list must contain exactly one endpoint of every displayed
matching edge and must meet every displayed leaf edge. These checks imply that
F is minimum: the matching forces every leaf vertex cover to have at least n
vertices. They also imply minimality: each retained spoke has its matching edge
as a private edge, meaning that no other edge of F touches that matching edge.

CENTER
0

LEAF VERTICES (10)
1 2 3 4 5 6 7 8 9 10

LEAF EDGES (15)
1-2 1-7 1-8 2-3 2-5 3-6 3-10 4-6
4-8 4-10 5-7 5-10 6-9 7-9 8-9

LOWER-BOUND MATCHING (5)
3-6 5-10 4-8 1-2 7-9

Give your final answer inside <answer></answer> tags, as one JSON list.
Example of syntax only (not claimed valid):
<answer>[1,3,4,5,7]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[2,6,7,8,10]</answer>`. The checker returns
`(True, "ok")`; deleting `10` returns
`(False, "answer must contain exactly 5 labels")`. A person can solve this
demo on paper by orienting its five matching pairs and checking 15 leaf edges.

## Difficulty presets

| Preset | `n` | Prime `p` | Leaf degree | Leaf edges | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 11 | 3 | 15 | 5 | hand example; hardener skips it |
| easy | 120 | 241 | 8 | 960 | 120 | **shipping; held 3/3** |
| medium | 158 | 317 | 10 | 1,580 | 158 | available, not needed |
| hard | 200 | 401 | 12 | 2,400 | 200 | available, not needed |

`escalate` first increases decoy density, then supports `n=221` and `n=243`;
the next supported size would exceed the 256-atom answer cap.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted and compact-route certificates verify; JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced JSON amid prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware hits; candidate space `2^120` |
| G5 | pass | shipping density 0/200,000; demo exact count 2; BFS 3,840 operations; compact route 137 |
| G6 | pass | six attacks × 8 seeds, zero successes; BFS reference solves 8/8 |
| G7 | pass | doubled-size supported instance builds and verifies; named spaces strictly grow |
| G8 | pass | 60/60 relabelings invariant and verifying; 20/20 unrelated keys distinct |
| G9(c) | pass | 432 characters, 108 estimated tokens, 120 atoms, 137 exact operations |

The strongest failing local attack performed 2,048 randomized greedy restarts
across eight seeds in about 3.16 seconds without finding a witness.

## Oracle loop

The repository-owned hardener held `easy` without escalation. It currently
uses the two-vendor OpenAI/Google pool recorded in `.meta.json`; this supersedes
the older four-vendor description in the task text.

| Preset | Seed | Model | Solved | Checker result |
|---|---:|---|---|---|
| easy | 880223646 | OpenAI GPT-5.6 Terra | no | uncovered leaf edge `7-75` |
| easy | 45121206 | Google Gemini 3.8 Flash | no | failed matching orientation |
| easy | 2095549732 | Google Gemini 3.8 Flash | no | uncovered leaf edge `7-182` |

## G9 diagnostic

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted − placebo = 0.0`. The structural hint bought this pool no measured
success, so these runs do not show that the models can execute the common-ratio
insight once it is named. The answer/route measurements are 432 characters,
108 estimated tokens, 120 atoms, and 137 exact arithmetic operations.

## Use

```python
import importlib.util

path = "results/2201.08647/gen_2201_08647.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
prompt = g.render(inst)
answer = g.parse_answer("<answer>[1,2,3]</answer>")
ok, reason = g.verify(inst, answer)
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2201.08647 20 easy
```

## Caveats

- This is deliberately not a complexity-theoretic hardness claim. BFS solves
  every generated instance quickly on a computer; the measured claim is the
  gap between a full 960-edge propagation and a 120-pair modular invariant in
  a no-tool context.
- G4 samples the strongest obvious prior implied by the statement: one endpoint
  independently from every matching edge. It does not model a solver using BFS
  or the hidden ratio; either such route succeeds deterministically.
- The structural key includes matching-coloured common-neighbour and closed-walk
  profiles. It passed arbitrary relabeling tests but is not a complete graph-
  isomorphism algorithm, so rare non-isomorphic collisions remain possible.
- No SAT, ILP, or commercial solver was tried. BFS is exact and strictly more
  direct for these connected bipartite leaf graphs.
- One hinted Google call returned an HTTP-200 empty length-limited response;
  the repository script records it as a failed valid call. The raw transcript
  is retained so that policy can be re-evaluated without rerunning the model.
