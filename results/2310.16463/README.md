# arXiv 2310.16463 — verified symbolic Steiner-tree packings

**Outcome: shipped at `medium`; every gate passes.**

| profile field | value |
|---|---|
| track | B — the paper gives an efficient constructive algorithm |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate form | exact symbolic |
| intuition | decomposition: terminal-free prefix atoms carry recursive spanning trees |
| domain essentiality | native |
| reduction | none |

## Problem and trust boundary

This family comes directly from Yang, Li, Mao, Cheng, and Klasing,
[*Constructing disjoint Steiner trees in Sierpiński graphs*](https://arxiv.org/abs/2310.16463),
v3. An instance gives a native Sierpiński word graph `S(depth, alphabet)` and a
set of terminals. The answer is a packing of the number of internally disjoint
terminal Steiner trees guaranteed by Theorem 2.1, represented by exact edge strings and
exact prefix-atom spanning-tree macros.

Definition 1 supplies the word adjacency relation. Theorem 2.1 guarantees
`alphabet - ceil(terminals/2)` internally disjoint trees for
`3 <= terminals <= alphabet`, and Section 2, Algorithm 1 supplies the local
star/Hamilton-path construction. The generator executes those proof choices;
when it reaches a terminal-free atom, it records the paper-licensed spanning
tree as a fixed recursive macro rather than searching or enumerating the atom.

Verification never reads `inst["answer"]`. It checks every literal edge, every
prefix bound, terminal incidence, and component budget. It then contracts the
fixed atom trees and checks connectivity, acyclicity, edge-disjointness, and
exactly-terminal vertex intersections. Six small cases were also expanded to
ordinary edge sets and rechecked independently.

## Why this is Track B

Track A would be false: Algorithm 1 constructs every instance in this
distribution. Its explicit level-by-level loop takes
`O(c * alphabet^depth)` tree/atom visits. At the shipping preset it makes
10,922 visits; the measured Python loop skeleton averaged 0.000839 seconds over
eight seeds and solved 8/8 as expected. The symbolic prefix decomposition used
by the intended route averaged 143 exact local/component operations and had a
measured 1,000-seed maximum of 166. The benchmark is the no-tool compression
gap between carrying out the displayed expanded construction and recognizing
whole terminal-free atoms as one exact object.

The Introduction notes polynomial algorithms when both generalized
edge-connectivity parameters are fixed and NP-completeness for several general
internally-disjoint variants. Neither supports Track A here: the paper's own
structured Algorithm 1 is decisive. The family stays in the theorem's
`k <= alphabet` internally-disjoint regime; for `k > alphabet`, Theorem 1.5 only
fixes the edge-disjoint value and does not give the same internal packing claim.

## Worked demo

For `make_instance(n=2, alphabet=3, terminals=3, seed=3)`, `render()` returns:

```text
Construct internally disjoint Steiner trees in a Sierpinski graph.

The graph S(2,3) has as vertices all length-2 words over the
digits 0,...,2.  Vertex ID x is the base-3 value of its word,
including leading zeroes; thus IDs are the decimal integers 0,...,8.
For example, write every ID with 2 base-3 digits when testing edges.

Two distinct words u=(u_0,...,u_1) and v=(v_0,...,v_1)
are adjacent exactly when, at their first differing coordinate d, they have the
same prefix before d and every later coordinate is swapped: u_j=v_d and
v_j=u_d for every j>d.  The graph is undirected and has no loops.

Terminals (decimal vertex IDs): 2, 3, 7

An S-Steiner tree is a connected acyclic subgraph containing every terminal;
it may contain other vertices.  Two such trees are internally disjoint when
they share no edge and their common vertices are exactly the terminals.

Write each tree as [ports,parts].  Every component is a JSON string containing
two comma-separated decimal integers, with no spaces.  Ports is a list of 3
nonempty edge lists, in the displayed terminal order: port i contains every
explicit edge of this tree incident with terminal i, and each such edge must
have no other terminal endpoint.  Parts contains every other component.  A
nonnegative component "u,v", with 0<=u<v<9, is the single graph
edge {u,v}.  A negative component "-q,p", with 1<=q<2 and
0<=p<3^q, is the following fixed spanning tree of prefix atom A(q,p):
A(q,p) contains every length-2 word whose first q digits have base-3
value p.  Recursively, if r=2-q=1, join child digit 0 to every child digit
1,...,2.  If r>1, take that same spanning tree inside every child
atom and add, for each j=1,...,2, the bridge between prefix 0 j^(r-1)
and prefix j 0^(r-1).  Thus "-q,p" denotes a concrete tree, not permission to
choose one.  No atom component may contain a terminal.

After expanding these definitions, each [ports,parts] must be an S-Steiner tree and the
1 trees must be internally disjoint.  Use at most
15 components in total.  Sort the edges within every
port and sort each parts list lexicographically; all components are distinct
within a tree and no explicit edge may repeat between trees.
All IDs and p are decimal, every bound is inclusive except an upper bound written
with '<', and tree order matters only as output syntax.

Give your final answer inside <answer></answer> tags, as a JSON list of exactly
1 [ports,parts] trees.
Format-only example (the numbers are not a solution): <answer>[[[["0,1"],["2,3"],["4,5"]],["-1,0"]]]</answer>
Output nothing else inside the tags.
```

The planted answer is:

```text
<answer>[[[["1,2"],["1,3","3,5"],["5,7"]],[]]]</answer>
```

`verify` returns `(True, "ok")`. Replacing the first port by `[]` returns
`(False, "tree 1 terminal port 1 is empty")`. A person can solve this nine-vertex
demo and check the four edges on paper. Its normalized language has 2,744
candidates, of which exactly 432 are valid; the demo illustrates syntax and is
not a hardness claim.

## Difficulty presets

| preset | depth | alphabet | terminals | trees | vertices | component bound | result |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 3 | 3 | 1 | 9 | 15 | hand-solvable; skipped by hardener |
| easy | 5 | 4 | 4 | 2 | 1,024 | 70 | defeated: Grok solved 1/3 |
| **medium** | **7** | **4** | **4** | **2** | **16,384** | **98** | **ships: bare 0/3** |
| hard | 10 | 4 | 4 | 2 | 1,048,576 | 140 | locally valid; not needed after medium held |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted checks; 6/6 explicit macro expansions |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose/fence/tag round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; 1,016-bit language |
| G5 | pass | shipping density sample 0/200,000; demo 432/2,744; 256-restart cost 0.043734 s |
| G6 | pass | five attacks each 0/8; reference Algorithm 1 solves 8/8 in 10,922 visits |
| G7 | pass | depth doubled 7→14, vertices 16,384→268,435,456, witness still verifies |
| G8 | pass | 60/60 relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9 | pass | hinted pool 0/3; worst answer 1,046 chars/262 estimated tokens/94 atoms; route 166 ops |

## Bare oracle loop

| preset | model | seed | solved | score/reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1964852464 | no | parts not sorted |
| easy | Claude Sonnet 5 | 409795859 | no | empty length-limited reply |
| easy | Grok 4.6 | 730690378 | yes | verified `ok` |
| medium | Gemini 3.1 Pro | 1477276344 | no | parts not sorted |
| medium | Claude Sonnet 5 | 820021218 | no | empty length-limited reply |
| medium | GPT-5.6 Terra | 205507839 | no | returned zero trees |

## G9 arms

| arm | solved/attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; polarity-flipped gate passes |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `0.0`: naming the repeated terminal-free atom pattern
bought this oracle sample no measurable advantage. One placebo Grok call ended
with a transport error and was correctly redrawn; it is preserved in the arm
transcript and is not one of the three scored attempts. For seed 19 the answer
is 812 characters, 73 atomic strings, and 134 intended operations. The
1,000-seed maxima are 1,046 characters, 94 atoms, and 166 operations.

## Use

```python
from gen_2310_16463 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=19, **DIFFICULTY["medium"])
assert verify(inst, inst["answer"]) == (True, "ok")
prompt = render(inst)
```

From the repository root:

```bash
bash scripts/emit.sh 2310.16463 20 medium
```

## Caveats

This family is easy with ordinary tools: Section 2's Algorithm 1 is a complete
constructor, which is why the claim is Track B. The measured reference wall
time is the exact Python loop skeleton for its 10,922 tree/atom visits, not a
benchmark of allocating every expanded edge; full materialization can only add
work. The 0/200,000 figure is empirical, not a proof of zero density. Its prior
is nevertheless structure-aware and exact: every sampled candidate already
has genuine, globally distinct terminal-port edges, valid terminal-free macros,
and the public bound; it does not model a learned solver's correlated choices.

No ILP, multicommodity-flow relaxation, dedicated Steiner-packing package, or
construction-specific learned search was run. The reference algorithm is kept
outside the failing attacks, as Track B requires. The canonical key handles
terminal order and coordinatewise alphabet permutations, but not every possible
automorphism of a Sierpiński graph. Pairwise-nonadjacent terminals are a stated
normalization used to make terminal ports unique; removing it would require a
different answer grammar, not a different theorem.
