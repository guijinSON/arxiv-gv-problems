# Affine matching cuts for arXiv 2505.22351

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph |
| certificate form | affine polynomial over `F_2` |
| intuition | invariant: short edge-label differences span a parity kernel |
| domain essentiality | native |
| reduction | paper-licensed, Section 4, Theorem 4.3 |

**Release status:** complete. All local gates pass, and the bare multi-vendor
loop returned `hardened` at the shipping `easy` preset with 0/3 solved. The G9
diagnostic is also complete: structural hint 0/3, placebo 1/3.

## Problem and construction

The source is Dabrowski, Eagling-Vose, Johnson, Paesani, and Paulusma,
[*Finding d-Cuts in Probe H-Free Graphs*](https://arxiv.org/abs/2505.22351).
Observation 2.1 identifies a `d`-cut with a red-blue colouring that uses both
colours and gives each vertex at most `d` opposite-colour neighbours. This
family fixes `d=1`, so the cross edges must form a matching. Section 2 also
defines precoloured pairs; the rendered problem uses one red source and one
blue target to remove the irrelevant colour-complement symmetry.

The solver receives a connected bipartite graph, its probe/non-probe
partition, and distinct binary vertex labels. It must return an affine
polynomial over `F_2`; evaluating that polynomial colours the vertices. The
checker evaluates it exactly and counts opposite-colour neighbours, accepting
any polynomial whose colouring is an oriented matching cut. It never reads the
planted answer.

Theorem 4.3 is used in the paper's own graph language, not as a convenience
discretisation. Taking one bipartition class as the independent non-probes and
adding all edges inside it makes the completion split. Thus every generated
graph is a native partitioned probe split graph.

The affine labels are an added certificate encoding, not a replacement for the
graph problem. The checker evaluates the encoded colouring and then applies the
paper's exact opposite-neighbour condition to the supplied graph; labels alone
cannot make an answer valid.

Generation is inverse. A dense affine polynomial is sampled first. Its two
fibres receive degree-six bipartite graphs, each the union of three
edge-disjoint Hamiltonian cycles. One edge in the first cycle of each fibre is
replaced by two cross-fibre edges. All vertices remain degree six and the
cross-fibre edges form the planted matching cut. Within a fibre, the deletion
leaves a Hamiltonian path plus two Hamiltonian cycles, so a nontrivial internal
cut uses at least `1+2+2=5` edges; the two cross edges are the unique minimum
terminal cut. Short edge-label differences supply a systematic basis for the
planted parity kernel. The certificate is never obtained by solving the graph.

## Why Track B

The paper's worst-case result does not justify Track A for this distribution.
Theorem 4.3 proves `d`-Cut NP-complete on probe split graphs for every fixed
`d`, while Theorem 1.4 gives the easy boundary: `1`-Cut is polynomial on
partitioned probe `H`-free graphs when `H` is an induced subgraph of
`sP1+P4`; for `d>=2`, the boundary is `P1+P4`. Theorem 3.2 and its preceding
lemmas show the latter polynomial mechanism, while Theorem 3.1 handles
matching cut. Both use colour-processing and bounded branching. This generator stays in the hard probe-split class but its special
distribution is deliberately easy with tools.

The honest reference algorithm runs unit-capacity Ford–Fulkerson between the
precoloured terminals, then fits the resulting bipartition by exact Gaussian
elimination over `F_2`. Its complexity is `O(k(n+m)+n*b^2)`. At shipping
`n=68`, eight measured instances required a median **23,275 counted bit
operations** and approximately **0.0005 s**. A lazy-adjacency spectral bisection plus exact
fitting was also run as the required planted-partition audit: 92,857 median
operations and 8/8 successes in the gate panel. Both exact and spectral routes
succeeded on a further 200/200-instance audit.

The compact route notices that every Hamming-weight-one or -two difference on
an edge lies in one codimension-one parity kernel. Weight-one differences
anchor zero coefficients and weight-two differences link equal coefficients.
At shipping size, scanning those relations and choosing the remaining parity
class costs **228** counted operations. The Track B claim is only the gap
between that compact invariant and the mechanical reference calculation in a
no-tool context.

## Worked demo (`seed=0`)

This is the complete rendered demo instance:

```text
Affine matching cut in a partitioned probe split graph

The undirected simple graph G below has vertices 0 through 29.
P is the set of probes and N is the set of non-probes.  N is independent.
Adding every missing edge with both endpoints in N makes N a clique while P
is independent, so the completed graph is split; this is a partitioned probe
split graph.  The added completion edges are not edges of G and are not used
when checking your answer.

Each vertex v has a distinct 7-bit label x(v).  The LEFTMOST displayed bit
is x_0, followed by x_1, ..., with x_6 rightmost.  An affine polynomial
over F_2 has the form
  Q(x) = c_0*x_0 XOR c_1*x_1 XOR ... XOR c_6*x_6 XOR q,
where each coefficient and q is exactly 0 or 1.  Colour v red when Q(x(v))=0
and blue when Q(x(v))=1.

A red-blue 1-colouring is a matching cut when both colours occur and every
vertex has at most one neighbour of the opposite colour.  Find an affine Q
whose induced colouring is a matching cut, oriented so vertex 0
is red and vertex 13 is blue.  Vertex numbering is 0-based;
edges are unordered; loops and repeated edges are absent.

P (probes): [7, 8, 4, 2, 14, 24, 29, 3, 17, 0, 18, 15, 13, 25, 23]
N (independent non-probes): [6, 22, 11, 16, 12, 19, 9, 20, 10, 5, 27, 1, 21, 26, 28]

Vertex labels (vertex: bits x_0...x_6):
  0: 0101000
  1: 1101100
  2: 0001110
  3: 0100001
  4: 0110011
  5: 0001111
  6: 1011110
  7: 1110110
  8: 0010110
  9: 1001001
  10: 0110001
  11: 0100111
  12: 0010101
  13: 1000111
  14: 0101111
  15: 0101101
  16: 1101000
  17: 1011111
  18: 1111001
  19: 1111100
  20: 1010010
  21: 1110100
  22: 0101110
  23: 1100101
  24: 1011001
  25: 0001100
  26: 0000110
  27: 1111000
  28: 0000000
  29: 1001100

Edges of G (u-v):
  4-5 11-18 16-29 5-23 14-20 7-12 15-28 2-21 5-8 8-19 13-21 20-25
  7-20 9-15 5-29 14-22 27-29 7-10 2-6 0-22 17-28 6-8 12-25 15-19
  7-27 1-15 0-20 4-28 23-26 24-26 7-16 13-26 2-28 17-21 25-27 8-21
  19-23 3-27 10-29 3-12 15-26 9-17 6-13 3-10 11-25 1-4 5-17 2-9
  18-22 22-25 4-21 12-14 11-29 23-28 0-16 1-17 11-14 21-24 22-29 6-24
  9-13 13-19 6-17 18-20 1-8 10-14 4-26 8-9 3-16 18-27 3-20 16-18
  0-12 12-15 19-24 24-28 14-16 9-23 2-26 1-24 10-18 2-5 6-23 3-22
  1-13 0-27 7-11 4-19 10-25 0-11

Give your final answer inside <answer></answer> tags as exactly 7 coefficient
bits c_0...c_6, then a vertical bar, then the constant bit q.
Example for a 5-variable instance: <answer>01011|1</answer>
Whitespace inside the tags is allowed. Output nothing else inside the tags.
```

The answer is `<answer>0100110|1</answer>`, stored as
`[0,1,0,0,1,1,0,1]`; `verify` returns `(True, "ok")`. Flipping the constant to
`<answer>0100110|0</answer>` returns
`(False, "polynomial does not have the required terminal orientation")`.
The demo has 64 terminal-oriented affine candidates, exactly one valid answer,
and a 97-operation compact route. It is intentionally solvable on paper,
though checking the complete edge list is still somewhat tedious.

## Difficulty presets

| preset | vertices | label bits | edges | candidate space | answer atoms | compact ops | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 30 | 7 | 90 | 64 | 8 | 97 | hand example; oracle skipped |
| easy | 68 | 24 | 204 | 8,388,608 | 25 | 228 | **shipping; hardened 0/3 solved** |
| medium | 76 | 24 | 228 | 8,388,608 | 25 | 252 | denser fixed-answer rung |
| hard | 84 | 24 | 252 | 8,388,608 | 25 | 276 | denser fixed-answer rung |

`escalate()` keeps the 25-atom polynomial fixed and grows the graph to `n=92`
(276 edges, 300 compact operations), then returns `"cap_bound"`; it does not
mislabel the no-tool operation cap as the family running out of mathematics.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed plants verify; 12/12 probe-split structures and verifier-independence checks; 12/12 answers JSON-round-trip |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | fenced prose round-trip succeeds; garbage returns `None` |
| G4 | pass | 0/200,000 structured guesses in 8,388,608 terminal-oriented affine candidates |
| G5 | pass | shipping density 0/200,000; demo exact count 1/64; reference 23,224 operations and about 0.0005 s on the recorded seed |
| G6 | pass | four attacks × 8 seeds, 0 successes; exact, spectral, and compact references each 8/8 |
| G7 | pass | `n` 68→136 and edges 204→408; reference operations 23,224→47,120; answer stays 25 atoms |
| G8 | pass | 80/80 invariance, 60/60 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 51 chars, 13 estimated tokens, 25 atoms, 228 intended operations |

The four gated failing attacks are equal-degree outlier scoring, one local
coordinate sweep, 256 structured random restarts, and every one- or
two-coordinate affine ansatz. An extended 200-instance audit gave 0/200 for
each attack and 200/200 to the plant, exact reference, spectral reference, and
compact route; all 200 canonical keys were distinct.

## Oracle loop

The script-owned bare run hardened at its first tested rung. Every returned
answer was parsed; none verified, so no failure is attributable to the output
contract.

| preset | model | seed | result | verifier reason |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 1171111245 | failed | terminal orientation wrong |
| easy | GPT-5.6 Terra | 337039585 | failed | vertex 34 exceeds the bound |
| easy | GPT-5.6 Terra | 1095130652 | failed | vertex 9 exceeds the bound |

## G9 arms

| arm | solved / attempts | result detail |
|---|---:|---|
| bare | 0 / 3 | three parsed but invalid polynomials |
| hinted | 0 / 3 | two parsed invalid polynomials; one length-truncated derivation with no answer |
| placebo | 1 / 3 | one valid polynomial, one invalid, one empty length-limited reply |

`hinted - placebo = -1/3`. With only three independent seeds per arm, the
negative sign is sampling noise rather than evidence that the hint is harmful;
the supported conclusion is that this run found no benefit from naming the
parity-kernel invariant. The size/effort portion passes: 51 serialised
characters, 13 estimated tokens, 25 atomic coefficients, and 228 intended-route
operations.

## Use

```python
import gen_2505_22351 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["easy"])
statement = g.render(inst)
wire = "<answer>" + g._answer_text(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

The recorded hardening verdict is `hardened`. To emit examples from the
repository root:

```bash
bash scripts/emit.sh 2505.22351 20
```

## Caveats

- This is Track B: with a graph algorithm or CAS it is easy in milliseconds.
  Its intended difficulty is finding the compact parity invariant without
  tools, not complexity-theoretic hardness of the generated distribution.
- The 0/200,000 guess result is for a uniform prior over terminal-oriented
  affine polynomials. It does not model min-cut knowledge, spectral clustering,
  or a prior concentrated on short label differences; a zero observed count is
  not a proof that the true density is zero.
- The certificate language deliberately asks for an affine polynomial. The
  underlying graph could in principle have non-affine matching cuts; those are
  outside the explicitly rendered answer language.
- The domain-standard min-cut and spectral routes were tested. No external SAT,
  ILP, or SDP package was used, and no sophisticated coding-theory attack was
  attempted.
- `canonical_key` covers vertex renumbering, input reordering, every invertible
  `GF(2)` change of basis, global XOR translations, and their compositions.
  On a small symmetric graph where rooted colour refinement does not
  individualise all vertices, it conservatively falls back to a quotient
  invariant and can over-collapse non-equivalent labelled instances.
- The module is standard-library-only. The probe completion edges are implied
  by `N` and intentionally excluded from both the instance graph and verifier,
  exactly as in Theorem 4.3.
