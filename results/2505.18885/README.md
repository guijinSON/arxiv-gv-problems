# Compressed 2-linear-vertex-arboricity certificates

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | signed integer tuple (a source truth assignment) |
| Objects shown | bounded-occurrence CNF, maximum-degree-six graph, and the paper's gadget map |
| Intuition | symmetry: truth is constant on multiplicative square cosets of the displayed residue labels |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 2, Lemmas 1–3 and Theorem 2.1 |

This is a verified generator based on Erhardt and Wolff, [*The Parameterized
Complexity of Computing the Linear Vertex Arboricity*](https://arxiv.org/abs/2505.18885).
A solver receives a bounded-occurrence formula and the graph obtained from the
paper's variable, clause, and link gadgets. It returns the source assignment as
a compact description of a two-colouring. The checker expands that description
and directly verifies, edge by edge, that both induced colour classes have
maximum degree two and contain no cycle.

The implementation passes every local gate, including the only gated part of
G9 (the answer-size and intended-effort caps), but it is **not yet shippable**.
The mandatory bare oracle loop could not obtain a valid attempt because the
configured OpenRouter key returned HTTP 403 `Key limit exceeded (total limit)`
on every redraw. The transcript preserves those errors; no API error has been
counted as a model failure or as evidence of hardness.

## Why this is Track B

This construction does not make a Track A claim. Section 1 identifies the
essentially trivial maximum-degree-at-most-four regime, Theorem 4.2 gives an
FPT algorithm parameterized by treewidth, and Section 5 gives a compact SAT/ILP
encoding with `O(N(N+k))` variables and `O(MNk+N^3)` constraints. More
decisively for this generated distribution, the included unit-propagating DPLL
solver succeeds on 8/8 shipping candidates (`n=240`): the final selftest
averaged 0.119 seconds, 54 search nodes, and 113,246 literal checks.

The compact route uses the generator's extra symmetry: enumerate the 120
nonzero modular squares and match the displayed labels. That is 120 exact
modular squarings, versus more than 100,000 literal checks for the mechanical
route. The benchmark therefore asks whether a no-tool solver notices a short
invariant; it does **not** claim that these instances resist software.

The construction satisfies the source restriction that every variable occurs
twice positively and once negatively and that every three-literal clause is
positive. It does not enforce the source incidence graph's planarity condition
(F1), so these generated graphs are not claimed planar. This is representational
coverage of the paper's central reduction, not an unrestricted native LVA
search task: the returned object is the compact source assignment rather than a
list of thousands of graph-vertex colours.

## Worked demo

The `demo` preset with seed 0 is hand-solvable. Its three clauses are
`(-1 ∨ -2)`, `(2 ∨ 1)`, and `(1 ∨ 2)`, so exactly one variable is true. The
displayed labels modulo 3 orient the intended answer as `[1,-2]`.

```python
>>> inst = make_instance(n=2, seed=0)
>>> verify(inst, [1, -2])
(True, 'ok')
>>> verify(inst, [1, 2])
(False, 'clause 1 is false')
```

<details>
<summary>Full rendered demo instance (no hint)</summary>

```text
COMPRESSED CERTIFICATE FOR TWO LINEAR VERTEX FORESTS

An undirected graph is given below.  A linear forest is a graph whose connected
components are paths, including isolated vertices.  Equivalently it is acyclic
and every vertex has degree at most two.  A legal two-colouring assigns every
graph vertex colour 0 or 1 so that each colour's induced subgraph is a linear
forest.

This graph is written in the variable, clause, and link blocks of Section 2 of
the cited construction.  Instead of transcribing all 44
colours, submit the source truth assignment.  The following deterministic
expansion is part of the certificate definition.

For variable i, let its row be `Vi B=b0,...,b6 P=p0,p1 A=a0,a1 N=q`.
When i is FALSE, colour b0,b2,b4,b5,b6,q with 1 and the other six row vertices
with 0.  When i is TRUE, reverse all twelve colours in that row.  Colour every
Z vertex in every clause row 0.  Colour each link block's b0,b2,b4,b5,b6 with
1 and b1,b3 with 0.  The P entries of a clause row are occurrence ports already
coloured in their variable rows.  These rules assign every graph vertex once.
The checker performs this expansion and directly verifies maximum induced
degree two and absence of monochromatic cycles using the edge list; it does not
trust the claimed reduction.

The source formula has variables 1 through 2.  A positive literal +i
is true exactly when variable i is TRUE; a negative literal -i is true exactly
when variable i is FALSE.  A clause is satisfied when at least one listed
literal is true, and all clauses must be satisfied.  Clauses have two or three
distinct variables, each variable occurs exactly twice positively and once
negatively, and every three-literal clause is positive.  These conditions do
not replace the checks above: a submitted assignment must also expand to a
legal graph colouring.

Each variable additionally has a distinct LABEL in the nonzero residues modulo
p=3.  Labels are ordinary instance data; variable IDs, not labels,
are used in the answer.

VARIABLES (ID:LABEL)
1:1 2:2

CLAUSES
C1 -1 -2
C2 +2 +1
C3 +1 +2

VARIABLE BLOCKS
V1 B=27,12,42,40,41,7,5 P=35,1 A=26,39 N=0
V2 B=4,34,20,14,24,28,33 P=43,38 A=11,29 N=17

CLAUSE BLOCKS
C1 Z=15,10 P=0,17
C2 Z=21,2 P=43,35
C3 Z=23,3 P=1,38

LINK BLOCKS
L1 B=31,9,16,6,36,18,8 ATTACH=10,21
L2 B=32,13,37,22,30,19,25 ATTACH=2,23

GRAPH
Vertices are the integers 0 through 43, inclusive.
Edges are unordered, have no repeats or loops, and are listed one per line:
0 15
0 17
0 26
0 39
1 23
1 27
1 38
2 21
2 32
2 35
3 23
3 38
4 14
4 24
4 34
4 38
4 43
5 7
5 12
5 26
5 39
5 40
6 8
6 9
6 16
6 18
6 31
6 36
7 12
7 40
8 9
8 18
8 21
9 16
9 18
9 31
9 36
10 15
10 17
10 31
11 17
11 29
11 33
12 27
12 40
12 41
12 42
13 19
13 22
13 25
13 30
13 32
13 37
14 20
14 24
14 28
14 33
14 34
16 36
17 29
19 22
19 25
20 24
20 34
21 43
22 25
22 30
22 32
22 37
23 25
24 34
26 39
27 35
27 40
27 41
28 33
28 34
29 33
30 32
30 37
31 36
33 34
35 43
40 41
40 42
41 42

Give your final answer inside <answer></answer> tags as one JSON list of exactly
2 signed integers.  At position i (positions are 1-indexed), write +i
to assign variable i TRUE or -i to assign it FALSE.  Thus absolute IDs must be
1,2,...,2 in that order; repeats and zero are forbidden.
Example format for three variables only: <answer>[1,-2,3]</answer>
Output nothing else inside the tags.
```

</details>

## Difficulty presets

Counts below use seed 0. Larger `n` increases both the Boolean search space and
the number of paper gadgets. `hard` is the intended shipping candidate, pending
the external oracle gate.

| preset | variables | graph vertices | edges | rendered chars | status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 44 | 86 | 3,334 | hand-solvable; harden skips it |
| easy | 60 | 1,433 | 2,864 | 38,048 | oracle attempted; all calls errored |
| medium | 126 | 3,017 | 6,032 | 84,014 | not reached |
| hard | 240 | 5,753 | 11,504 | 163,970 | intended shipping candidate |

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown |
| G4 | pass | 0 hits / 200,000 structure-aware signed assignments |
| G5 | pass | shipping sampled density 0/200,000; demo has 2/4 solutions; DPLL cost below |
| G6 | pass | five attacks × 8 seeds, 0 successes; DPLL 8/8 as Track B reference |
| G7 | pass | literal size-double at `n=480` built and verified |
| G8 | pass | 300/300 composed relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | pass | 1,093 worst-case answer characters, 240 atoms, 120 intended operations |
| G9(a,b) | diagnostic unavailable | all oracle calls errored before a valid attempt |

The strongest mechanical baseline averaged 54 DPLL nodes and 113,246 literal
checks. The candidate space has 240 bits. The answer measured 973 characters,
244 estimated tokens, and 240 atomic elements; the worst-case signed answer is
1,093 characters/274 estimated tokens. The intended compact route takes 120
exact arithmetic operations.

## Oracle loop and G9 arms

| arm/preset | model or pool result | seed | solved |
|---|---|---:|---|
| bare/easy | Gemini 3.8 Flash: HTTP 403 key limit | 107821962 | error |
| bare/easy | GPT-5.6 Terra: HTTP 403 key limit | 97835853 | error |
| bare/easy | Gemini 3.8 Flash: HTTP 403 key limit | 1676141036 | error |
| bare/easy | GPT-5.6 Terra: HTTP 403 key limit | 660618635 | error |
| hinted/hard | GPT-5.6 Terra: HTTP 403 key limit | four distinct seeds | 0 valid attempts; 4 errors |
| placebo/hard | Gemini 3.8 Flash: HTTP 403 key limit | four distinct seeds | 0 valid attempts; 4 errors |

There is no hinted-minus-placebo conclusion: all three arms have zero valid
attempts. This does not fail G9 because the arms are diagnostic, but it also
provides no STEP 4 hardness evidence. The two G9 transcript files preserve their
four script-generated error records. Once a working OpenRouter allowance is
supplied, rerun the bare ladder, then rerun the structural and placebo copies in
separate directories as required by G9.

## Use

```python
from gen_2505_18885 import make_instance, render, parse_answer, verify

inst = make_instance(n=60, seed=42)
problem = render(inst)
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
```

After the oracle evidence is complete, emit records from the repository root:

```bash
bash scripts/emit.sh 2505.18885
```

## Caveats

- These are deliberately easy with tools: the measured DPLL implementation
  solves every shipping test. Only the no-tool compression gap is claimed.
- `0/200,000` is a sampled density under uniform signed assignments satisfying
  the answer's obvious shape. It is not an exact shipping solution count and it
  does not establish average-case complexity.
- The modular labels are generator-added structure, while the graph gadgets and
  certificate expansion are from the paper. This is why the profile says
  `licensed_reduction`, not `native`.
- The generated source incidence graph is not forced planar. Maximum degree six
  and the exact gadget verification are checked; planarity is not claimed.
- The cheap planted-path idea from initial triage was rejected before coding:
  local-max-cut found valid colourings in 2–6 sweeps at every tested size from
  80 to 240 vertices.
- Industrial SAT/ILP and the MSO/treewidth algorithm were not benchmarked. The
  included DPLL already establishes the only fact Track B needs: a fast tool
  route exists. No oracle-hardness claim is made until the 403 is resolved.
