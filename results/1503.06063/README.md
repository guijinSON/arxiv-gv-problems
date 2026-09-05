# arXiv 1503.06063 — compressed tree 4-spanners

**Outcome: shipped at `hard`; every gate passes.**

| profile field | value |
|---|---|
| track | B — an efficient algorithm exists and is measured |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP/SAT |
| certificate form | integer tuple (Boolean variable-side choices) |
| intuition | reduction recognition: recover parity quartets and their hidden cycle |
| domain essentiality | licensed reduction |
| reduction | paper-licensed, central 3-SAT gadget in Proposition 2 |

## Problem and trust boundary

The source is Ioannis Papoutsakis, [*Tree spanners of small diameter*](https://arxiv.org/abs/1503.06063).
An instance specifies the paper's graph `f(I)` by listing the indexed 3-SAT
clauses and reproducing its complete six-row/eight-column gadget rule. The
solver returns one Boolean choice per variable. Those bits are not merely a
SAT answer: the statement defines how they expand into the concrete spanning
tree in the forward proof of Proposition 2.

The generator samples the bit vector first, builds a full-rank cyclic 3-XOR
system around it, expresses each XOR row as four 3-CNF clauses, shuffles all
clauses, and applies the paper's construction. It never solves its output.
`verify` never reads `inst["answer"]`; it expands all 12,641 vertices and both
edge sets, checks that the certificate has `|V|-1` graph edges, checks
connectivity and acyclicity, computes the exact tree diameter, and checks the
tree distance of every graph edge is at most four.

This is licensed-reduction rather than fully native graph-search coverage: the
graph is genuinely present through the paper's exact gadget specification and
verification uses it, but the solver's search is carried by the encoded Boolean
assignment.

## Why this is Track B

Definition 1 fixes the tree-spanner condition and notes that graph edges alone
need be checked. Theorem 1 gives a shortest-path representative when the
spanner diameter is at most `t+1`. Proposition 1 gives a polynomial algorithm
for `t=3`, and Theorem 2 summarizes the easy `t<=3` / NP-complete `t>=4`
split. Proposition 2 is the exact equivalence used here: `I` is satisfiable iff
`f(I)` has a tree 4-spanner of diameter at most five.

Theorem 2 does **not** justify Track A for this generated distribution. Every
four-clause group is an XOR equation, so regrouping the clauses followed by
dense Gauss-Jordan elimination over `GF(2)` solves every instance in
`O(m log m + n^3)` time. At shipping size the measured reference implementation
solved 8/8, used at most 38,950 counted Boolean operations, and averaged
0.002638 seconds per instance in the final recorded run. The compact route recognizes that pairwise
overlaps of the XOR triples form one cycle and uses its recurrence; the
executed compact solver uses 212 exact bit operations. This is the no-tool compression
gap being tested, not a claim that the instances resist software.

## Worked demo

For `make_instance(n=5, copies=1, seed=3)`, the complete rendered problem is:

```text
Find a compressed tree 4-spanner certificate for the graph below.

A tree 4-spanner of an undirected graph G is a spanning tree T contained
in G such that the distance in T between the endpoints of every edge of
G is at most 4.  The diameter of T is the largest distance in T between
any two vertices.  Here T must have diameter at most 5.

The graph G is given exactly by the following finite gadget specification.
A signed integer +k means Boolean variable X_k; -k means its negation.
Variables are 1-indexed, and each listed clause is an OR of its three
distinct literals.  Clause order and literal position are part of the
graph specification; repeated clauses create separate indexed gadgets.

Number of variables: 5
Number of indexed clauses: 20
Clauses (one JSON triple per indexed gadget):
c1: [2,-3,4]
c2: [-5,4,-1]
c3: [1,-5,2]
c4: [-5,4,3]
c5: [-2,-3,1]
c6: [2,-3,-1]
c7: [-4,5,-1]
c8: [3,-4,5]
c9: [-4,3,2]
c10: [2,1,3]
c11: [3,4,-2]
c12: [-2,5,1]
c13: [3,-2,-1]
c14: [-2,-4,-3]
c15: [5,2,-1]
c16: [-5,-4,-3]
c17: [-2,-1,-5]
c18: [1,5,4]
c19: [-3,4,5]
c20: [1,-4,-5]

Graph construction (this uniquely specifies every vertex and edge):
Create vertices u,v,h_u,h'_u,h'_v,h_v and the path
h_u--h'_u--u--v--h'_v--h_v.  Create one vertex X_k per variable and
join every X_k to both u and v.  For each indexed clause c=(l1,l2,l3),
create occurrence vertices O_c1,O_c2,O_c3 and q_c1,...,q_c8.  Join O_cj
to u when lj is positive and to v when lj is negative.  Put the q vertices
on the path q_c1--q_c2--...--q_c8.  Finally, in the row order
X_|l1|,O_c1,X_|l2|,O_c2,X_|l3|,O_c3, join a row vertex to q_ck exactly
where the following 6-by-8 matrix has a 1:
11110000
00001111
11001100
00110011
10101010
01010101
There are no other vertices or edges; all edges are undirected and there
are no loops.

Your answer is a compact certificate for T: give one bit a_k for each
X_k, in X_1,...,X_n order.  It expands as follows.  Include the fixed
six-vertex path.  Include X_k--u if a_k=1 and X_k--v if a_k=0.  Include
every occurrence-to-u/v edge.  In each clause, use the first listed literal
made true by the bits; if it is in position j, attach each q_ck through
the unique 1 in rows 2j-1 and 2j of column k.  (Those two rows are
complements.)  No q-path edge is included in T.  A certificate is valid
only if every clause has a true literal and the expanded subgraph is a
tree 4-spanner of diameter at most 5.

Give your final answer inside <answer></answer> tags, as a JSON list of exactly 5 integers, each 0 or 1.
Example format for four variables: <answer>[0,1,1,0]</answer>
Output nothing else inside the tags.
```

Its answer is `<answer>[0,0,1,1,0]</answer>`, and `verify` returns
`(True, "ok")`. Dropping the last bit returns
`(False, "answer has too few bits: expected 5, got 4")`. A person can solve
this five-variable illustration on paper by grouping its 20 clauses into five
parity quartets; the demo is deliberately not a hardness claim.

## Difficulty presets

| preset | variables | copies | clauses | graph vertices | answer atoms | compact ops | result |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 5 | 1 | 20 | 231 | 5 | 32 | hand-solvable; hardener skips it |
| easy | 31 | 1 | 124 | 1,401 | 31 | 84 | bare oracle solved it |
| medium | 47 | 2 | 376 | 4,189 | 47 | 116 | bare held, but G9(b) hint solved it |
| **hard** | **95** | **3** | **1,140** | **12,641** | **95** | **212** | **ships: bare and hinted both 0/3** |

The move from `medium` to `hard` was the single promotion permitted after a
G9(b) failure. No further hand escalation was performed.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates fully expanded and verified |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose/fence/tag round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware Boolean guesses; 95-bit language |
| G5 | pass | shipping sample 0/200,000; exact density `2^-95`; demo 1/32; 2,048-restart baseline took 0.040879 s |
| G6 | pass | four attacks each 0/8; reference Gaussian algorithm 8/8 |
| G7 | pass | doubled `n=190` instance has 25,276 vertices and verifies |
| G8 | pass | 80/80 real relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9 | pass | hinted pool 0/3; 285 chars, 143 estimated tokens, 95 atoms, 212 operations |

## Final bare oracle loop

| preset | model | seed | solved | verifier result |
|---|---|---:|---|---|
| hard | Grok 4.6 | 1689951383 | no | clause 579 false |
| hard | Claude Sonnet 5 | 1798582505 | no | empty length-limited reply |
| hard | GPT-5.6 Terra | 1091147332 | no | clause 8 false |

The empty Claude response is not the sole basis for hardening: the other two
vendors emitted assignments and both failed exact verification.

## G9 arms

| arm | solved/attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened; polarity-flipped gate passes |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `0.0`; naming the parity-cycle invariant bought this
oracle sample no measurable advantage at the shipping rung. The serialized
answer is 285 characters / 143 conservatively estimated tokens / 95 atoms, and
the intended route uses 212 exact bit operations.

## Use

```python
from gen_1503_06063 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=19, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
prompt = render(inst)
```

From the repository root:

```bash
bash scripts/emit.sh 1503.06063 20 hard
```

## Caveats

This family is easy with ordinary tools: its XOR structure makes Gaussian
elimination a complete solver, which is why the claim is Track B. The duplicate
clause copies add gadget crowding but no new logical information. The uniform
Boolean prior used by `random_candidate` already enforces every obvious shape
constraint; `0/200,000` estimates that prior and does not model correlated
choices by a learned or XOR-aware solver. Full rank proves the exact density is
`2^-95`.

No industrial CDCL/SMT solver, XOR-aware SAT package, or ILP formulation was
run; the exact quartet-recovery/Gaussian reference is the domain-specific
standard attack used instead. The answer is necessarily an integer tuple here
because Proposition 2's compressed witness is the set of variable-side choices;
the checker still expands and verifies the paper's native graph object. The
canonical key handles variable renaming, clause-gadget reordering, global
polarity, and their compositions, but it does not claim to decide every
possible isomorphism of arbitrary `f(I)` graphs.
