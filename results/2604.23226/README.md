# arXiv:2604.23226 — temporally connected subgraph generator

This is a verified **Track B** family built from Casteigts, Komusiewicz, and
Morawietz, [*On the Hardness of Finding Temporally Connected Subgraphs of Any
Size*](https://arxiv.org/abs/2604.23226). All local correctness gates pass. The
required external oracle run was attempted but produced **no scored attempt**:
the configured OpenRouter key returned HTTP 403 “total limit exceeded” on every
vendor/redraw. The script-owned error transcripts are retained; there is no
`hardened` verdict and this result must not be treated as ready to submit until
the bare loop is rerun with working quota.

## Profile

| field | value |
|---|---|
| Track | B — an efficient reference algorithm is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: 80 Boolean bits succinctly specifying a temporal vertex set |
| Intended intuition | reduction recognition: repeated pairs expose an involutive parity operator |
| Domain essentiality | licensed reduction (representational) |
| Reduction | Section 2, Theorem 2.1, MCC to happy directed Nontrivial TC Subgraph at lifetime 11 |

The solver is handed the paper’s directed temporal graph through a complete,
exact vertex-and-arc schema, not an adjacency matrix with the temporal structure
discarded. The search is nevertheless carried by the Multicolored Clique (MCC)
instance inside the paper’s reduction, so the profile honestly says
`licensed_reduction`, not `native`.

## Problem and construction

A temporal path follows directed arcs in nondecreasing time order. A vertex set
is temporally connected (TC) when its induced subgraph contains a temporal path
for every ordered vertex pair. The solver must return a succinctly represented
TC set in a happy directed temporal graph of lifetime 11. The submitted bits
select one local vertex in each MCC color; the complete witness is those vertices
plus the paper’s mandatory connector gadget. Verification evaluates the parity
rows, checks every selected MCC pair, and validates the exact temporal-path
template. On the demo it also materializes the whole induced graph and recomputes
all-pairs temporal closure with integer bitsets.

Generation samples the bit witness first. For `n=2m`, a random directed cycle
`p` defines

```text
(Ax)_i     = x_i     XOR x_p(i) XOR x_(m+p(i))
(Ax)_(m+i) = x_(m+i) XOR x_p(i) XOR x_(m+p(i)).
```

Writing `A=I+N` gives `N^2=0`, hence `A^2=I` over GF(2). The generator evaluates
`r=Ax`, adds parity decoys satisfied by `x`, and randomly relabels everything.
Each parity row becomes an MCC color whose four vertices are its satisfying local
assignments; two vertices are adjacent exactly when shared variables agree. The
paper’s Section 2 reduction then supplies the temporal graph and carries the
known clique to a TC subgraph. No SAT, clique, linear, or temporal solver runs in
`make_instance`.

## Why Track B

Section 1 fixes the closed-component definition and identifies the easy borders:
nontrivial **open** components are hereditary and polynomial-time detectable;
the introduction also records FPT results for parameter combinations such as
`k+L`, and non-strict undirected existence is FPT in lifetime `L`. This family
instead uses closed components and the directed lifetime-11 regime of Theorem
2.1. That theorem proves worst-case NP-hardness, with a `2^{o(N)}` ETH lower bound
for the reduction, but it says nothing about this generated distribution; this
README does not make a Track-A claim.

For this distribution, extracting the printed parity rows and running exact
GF(2) Gaussian elimination solves every instance in `O(R+n^3)`. At the shipping
preset it solved 8/8, using 351,415 counted scalar operations on average and
385,329 at most (about 0.0014–0.0017 seconds here). The compact route recognizes
`A^2=I` and evaluates `x=Ar` using exactly 160 XORs. It must first inspect 840 row
entries. The gap between roughly 350,000 mechanical operations and 160 exact
operations—not computational intractability—is the Track B hardness claim.

## Worked demo (`seed=7`)

A person can solve this smallest instance on paper: recover the six parity bits,
then check the temporal path families. This is the complete rendered statement.

```text
Find a temporally connected induced subgraph in the happy directed
temporal graph defined below. All definitions and all graph data are inline.

A directed temporal arc (u,v,t) may be traversed from u to v at integer
time t. A temporal path has nondecreasing traversal times. A vertex set
is temporally connected (TC) when, inside its vertex-induced subgraph,
every ordered pair of vertices is joined by a temporal path. This graph
is happy: every arc has one time and no in-arc and out-arc at one vertex
share a time, so allowing equal consecutive times changes no reachability.

First define an auxiliary 7-color Multicolored Clique graph G.
There are Boolean variables x1,...,x6. Each row below is one color
class. If its variables are [xa,xb,xc] and RHS is r, its four local
vertices are the listed 3-bit strings abc satisfying xa XOR xb XOR xc=r.
Two local vertices from different row colors are adjacent in G exactly
when they assign the same bit to every variable their rows share.
Vertices of one color are never adjacent. Row, variable, and option order
are presentation only. Variable indices are 1-based.

Parity color classes:
R001: vars=[x2,x3,x4] rhs=1 vertices=[111,001,100,010]
R002: vars=[x2,x5,x3] rhs=0 vertices=[011,000,110,101]
R003: vars=[x3,x6,x1] rhs=1 vertices=[010,100,111,001]
R004: vars=[x5,x6,x4] rhs=1 vertices=[100,111,001,010]
R005: vars=[x4,x1,x5] rhs=0 vertices=[110,000,011,101]
R006: vars=[x6,x2,x1] rhs=0 vertices=[101,011,110,000]
U: one additional vertex adjacent in G to every vertex of every R color.
It is the final color class and makes the number of colors odd.

Now define the directed temporal graph T (this is the instance to solve).
Let V be all local vertices of G, including U when present. Color indices
are 1,...,k in the displayed order. Besides V, T has alpha and omega;
for every v in V it has out(v) and in(v); and it has four special vertices
preout(omega), out(omega), in(alpha), postin(alpha). No arcs exist except
those in the following exhaustive rules (a product means all such arcs):

Selector arcs:
  alpha -> V_1 at time 4; alpha -> V_i at time 8 for every i>1.
  V_i -> omega at time 6 for odd i; omega -> V_i at time 5 for even i.
  For even i: V_i -> V_(i-1) at time 7 and, when i<k,
  V_i -> V_(i+1) at time 4.
Connector arcs, for every v in V:
  omega -> out(v), in(v) at time 10; out(v), in(v) -> alpha at time 2.
Special connector arcs:
  omega -> preout(omega) at 10; preout(omega) -> out(omega) at 11;
  preout(omega), out(omega) -> alpha at 2;
  omega -> in(alpha), postin(alpha) at 10; in(alpha) -> postin(alpha) at 1;
  postin(alpha) -> alpha at 2.
Validation arcs:
  v -> out(v) at 3 for every v in V; omega -> out(omega) at 3;
  in(v) -> v at 9 for every v in V; in(alpha) -> alpha at 9;
  out(v) -> in(alpha) at 4 for every v in V;
  out(omega) -> in(v) at 4 for every v in the final color V_k;
  out(omega) -> in(alpha) at 4;
  out(v) -> in(w) at 4 for every ordered pair v!=w with {v,w} an edge of G.
The lifetime is therefore 11.

Your answer is a succinct vertex-set witness: give n bits b1,...,bn.
For every row color R_i, the bits select its unique listed local vertex
whose three entries equal the bits on that row's variables; U is selected
when present. Expand the claimed set S by adding alpha, omega, every
out(v) and in(v) for every v in V, and all four special connector vertices.
The bits are valid exactly when every selected row vertex exists and the
expanded induced subgraph T[S] is TC. The checker expands this convention
and checks exact directed temporal reachability; it does not compare with
a stored answer. Repetitions are not meaningful, and order is x1 through xn.

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 6 bits (each exactly 0 or 1) in order [x1,...,x6].
Example format: <answer>[0,1,0,1]</answer>
The example only illustrates syntax; it does not have the required length.
Output nothing else inside the tags.
```

The answer is `<answer>[1,1,0,0,1,0]</answer>`.
`verify(inst, [1,1,0,0,1,0])` returns `(True, "ok")`. Flipping its first
bit returns `(False, "row 3 has parity 0 instead of 1, so its selected color
vertex does not exist")`.

## Difficulty presets

| preset | Boolean bits | parity rows | pair-aware space | status |
|---|---:|---:|---:|---|
| demo | 6 | 6 | `2^3` | hand-solvable illustration |
| easy | 24 | 36 | `2^12` | oracle run unavailable |
| medium | 48 | 120 | `2^24` | oracle run unavailable |
| hard | 80 | 280 | `2^40` | configured shipping preset; local gates pass |

`escalate()` first increases decoy crowding at fixed 80-bit answer length, then
increases `n` only while the `2n` compact route stays under 300 operations. It
returns `cap_bound` at the real operation limit.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | fenced tagged JSON round-trips; answer is JSON-native |
| G4 | 0/200,000 pair-aware candidates valid; language size `2^40` |
| G5 | exactly one witness by construction; demo enumeration = 1; reference 382,679 operations and 0.001549 s |
| G6 | seven attacks each 0/8; Gaussian reference 8/8 |
| G7 | doubled `n=160`, 560-row instance builds and verifies; space grows to `2^80` |
| G8 | 20/20 composed relabellings and paired complements invariant; 20 carried witnesses valid; 20 unrelated keys distinct |
| G9(c) | 161 characters, about 41 tokens, 80 atoms, 160 XORs; within every cap |

The seven failures are occurrence-median outlier detection, public alternation,
label-based pair orientation, first-listed-local-vertex voting, `2n` greedy
parity repair, 512 pair-aware random restarts, and local RHS voting.

## Oracle loop and G9 arms

No row below is a model failure. Every call failed at the API boundary and was
correctly recorded as `solved="error"`; the harness then refused to make a claim.

| arm/preset | vendors attempted | scored solved/attempts | API errors | conclusion |
|---|---|---:|---:|---|
| bare / easy | OpenAI Terra, Gemini 3.8 Flash | 0/0 | 4 | no hardening verdict |
| structural / hard | OpenAI Terra | 0/0 | 4 | unavailable |
| placebo / hard | OpenAI Terra | 0/0 | 4 | unavailable |

`hinted − placebo` is undefined; the machine-readable report uses neutral `0.0`
only because both denominators are zero. Nothing can be concluded about hint
sensitivity. The answer-size and 160-operation G9(c) result is independent of
the failed API calls.

## Use

From the repository root:

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "g", "results/2604.23226/gen_2604_23226.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=123, **g.DIFFICULTY["hard"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

After rerunning the oracle loop successfully, emit with
`scripts/emit.sh 2604.23226 20 hard`.

## Caveats

The family becomes easy for code that recognizes the repeated-pair parity core
or simply applies Gaussian elimination; that is intentional and is why this is
Track B. The measured `P(guess)` uses a stricter prior than uniform bits: every
candidate already obeys the opposite-value rule for all recovered pairs. It
still does not model a solver that recognizes the full involution.

The hard-instance verifier uses the paper proof’s executable symbolic path
template rather than materializing roughly millions of redundant connector
arcs. The demo independently materializes the graph and checks all ordered pairs,
but full explicit closure was not repeated at shipping size. The temporal graph
is specified succinctly by exhaustive arc products, which preserves the paper’s
object but is not an explicit edge-list benchmark. Full temporal-graph
isomorphism is not solved by `canonical_key`; its strong generated-family
invariant passed the required transformation and diversity checks.

No industrial SAT/SMT, ILP, dedicated maximum-clique package, or specialized
temporal-component solver was run. Exact Gaussian elimination is stronger on
this distribution than those generic tools are expected to be, but that is not
an empirical substitute for testing them. Most importantly, the external
two-vendor hardening evidence is absent because of quota exhaustion. A working
OpenRouter run is required before this family can support any model-hardness
claim or pass `submit.sh`.
