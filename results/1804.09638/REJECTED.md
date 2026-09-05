# Rejected at STEP 0: arXiv 1804.09638

Paper: Caleb Davis, Jeffry Hirst, Jake Pardo, and Timothy Ransom,
[*Reverse mathematics and colorings of hypergraphs*](https://arxiv.org/abs/1804.09638)
(2018, revised 2018).

## Decision

No family in the paper clears **G + H + V**.  The prior-triage proposal—sample a
valid finite coloring and then add only compatible hyperedges—does clear G by
inverse generation and V by an exact edge scan.  It fails **H on Track A** because
the paper proves logical compactness/reversal results, not a finite-instance or
average-case hardness theorem for that planted distribution.  Its cleanest
paper-native special case also fails **H on Track B**: ordinary propagation is
both the standard algorithm and the shortest route, so there is no mechanical/
compact compression gap.

Implementation stopped before STEP 1, as the prompt requires after a STEP 0
rejection.  Consequently there is no generator, self-test report, README, or LLM
transcript to ship.

## What the paper actually defines

The unnumbered definition in **“Vertex colorings and finite edges”** distinguishes
three notions that the triage summary conflated:

- a coloring is **proper** when it is nonconstant on every edge having more than
  one vertex;
- it is **strong** when it is injective on every edge; and
- it is **conflict-free** when every edge contains a vertex whose color occurs
  exactly once in that edge.

The paper permits empty, singleton, finite, and infinite edges.  Its finite-edge
compactness theorem (**Theorem 5**, source label `pcffA`) says, for fixed
`k >= 2`, that the assertion “every finite partial hypergraph is properly (or
conflict-freely) `k`-colorable, hence the whole countable hypergraph is” is
equivalent over `RCA_0` to `WKL_0`.  **Theorem 6** (label `conj2`) changes the
edge representation to characteristic functions and obtains `ACA_0`.
**Theorem 7** (label `sfcA`) gives the corresponding strong-coloring reversals.
These are statements about existence of colorings of countably infinite
hypergraphs and the set-existence axioms needed to prove them.  They are not
complexity results for finite hypergraphs, and they specify no random or planted
finite parameter regime.

For infinite edges, **Theorem 9** reduces the existence of a proper or
conflict-free coloring to the existence of an infinite path through a tree.  The
proof constructs an infinite coloring from an infinite path and conversely traces
an infinite path from a coloring.  The output is an infinite function/path, not a
bounded witness that this task's checker can inspect.  Restricting the tree to a
finite depth removes the theorem's equivalence; requiring an ultimately periodic
path would add a special representation and a new promise not supplied by the
paper.

Finally, the unnumbered **Matryoshka definition and Lemma 10** (labels `Mdefn`
and `ert`) treat the
Matryoshka hypergraph with suffix edges `E_j = {k : j <= k}`.  The claim that it
has no finite conflict-free coloring uses the eventually-repeating-tails
principle.  That proof is not a finite Nullstellensatz-style or bounded
refutation certificate.  Conversely, the paper explicitly makes every finite
partial instance easy: color its largest numbered vertex red and every other
vertex blue.

## The certificate-producing method

For the proposed finite planted family, the certificate is produced by sampling
the color vector first and retaining only hyperedges on which it meets the chosen
definition.  This is valid inverse generation; no instance is solved by the
generator.  Verification checks the candidate's length/range and then counts
colors on every displayed edge, in `Theta(sum_e |e|)` exact integer operations.

That observation establishes G and V only.  None of Theorems 5–7 supplies a
finite hard distribution.  Theorems 5 and 6 even use ordinary finite colorings as
nodes of a finitely branching tree; their strength lies in extracting one
coherent *infinite* path, not in asserting that a sampled finite node is hard to
find.

## Mechanical cost versus compact route

The strongest honest Track B candidate is the graph subcase already used in the
proof of Theorem 5.  On 2-element edges, proper and conflict-free 2-coloring are
the same problem.  Generate a balanced planted bipartition, include a connected
alternating backbone, add random cross-edges, and randomly relabel the vertices.
The graph is connected, so exactly two of the `2^n` color vectors are valid.  At
`n = 256` this gives a structure-aware guess probability of `2 / 2^256`, well
below `10^-6`, while the answer has exactly 256 atomic elements.

The standard certificate-producing algorithm is breadth-first or depth-first
color propagation, with complexity `Theta(n + m)`.  I instrumented a
standard-library Python BFS on 20 deterministic instances at each of three sizes;
one counted operation was an adjacency insertion, adjacency examination, queue
pop, or first color assignment:

| `n` | `m` | operations (every seed) | mean wall time | maximum wall time |
|---:|---:|---:|---:|---:|
| 64 | 512 | 2,175 | 0.0000487 s | 0.0000579 s |
| 128 | 2,048 | 8,447 | 0.000196 s | 0.000302 s |
| 256 | 4,096 | 16,895 | 0.000382 s | 0.000449 s |

The **compact route is the same propagation**.  Random relabeling deliberately
removes a positional formula, and the instance contains no further invariant
from which the partition can be read.  Thus its measured length is also 16,895
under the same convention (and at least `n + m = 4,352` vertex/edge inspections
even when bookkeeping is free).  The mechanical-to-compact ratio is 1.

Shrinking does not create a Track B gap.  A connected 22-vertex tree is already
just below the G4 threshold (`2 / 2^22 < 10^-6`), but both the mechanical and
by-hand routes are the same roughly 127 primitive propagation actions.  Enlarging
the graph makes both routes longer together and eventually violates the
300-operation intended-route cap.  Adding a visible algebraic or indexing pattern
would make a shortcut, but that pattern is not a result of this paper; in the
obvious Matryoshka case the paper itself states the one-step shortcut (“choose the
largest vertex”), so the no-tool task is immediately guessable.

These are the two requested Track B numbers at the plausible maximum answer-size
shipping point:

- **Mechanical cost:** 16,895 counted operations, mean 0.000382 seconds, for BFS
  at `n = 256, m = 4,096`.
- **Compact route:** the same 16,895 operations (at least 4,352 indispensable
  input examinations); there is no shorter invariant-based route.

The rejection therefore does not rest merely on the existence of an efficient
algorithm.  It rests on the measured absence of the compression gap Track B
requires.

## Why the apparently harder alternatives do not rescue the paper

| Paper-native candidate | G | H | V | reason |
|---|---|---|---|---|
| planted proper/conflict-free 2-coloring of a graph | pass | **fails A and B** | pass | linear propagation solves every generated instance; compact route is identical |
| planted proper 2-coloring of 3-uniform hyperedges | pass | **unsupported on A** | pass | this is planted NAE-3-SAT, but the paper gives no finite or distributional hardness theorem; worst-case hardness would not establish hardness of the planting |
| strong finite coloring | pass | **unsupported on A** | pass | clique-expanding each edge exposes ordinary graph coloring, but the paper gives no hard generated regime |
| Theorem 9 tree/hypergraph construction | possible only with an infinite path | not reached | **fails** | the native witness is an infinite path/coloring, not a bounded inspectable object |
| classify colorable hypergraphs as in Theorem 9 | no scalable certified negatives | not reached | **fails** | well-foundedness/non-colorability has no bounded certificate supplied by the paper |
| finite Matryoshka truncation | pass | **fails A and B** | pass | the paper gives the coloring directly: largest vertex red, all others blue |
| infinite Matryoshka non-colorability | theorem-backed claim only | not reached | **fails** | ERT/induction is not a finite executable negative certificate |

Using an external SAT gadget, cryptographic commitment, or succinct-circuit tree
could manufacture hardness, but it would be a convenience reduction rather than
this paper's coloring mathematics.  The paper itself licenses no such reduction,
so that route was not used to claim native coverage.

## Gate diagnosis

| requirement | result |
|---|---|
| G — generatable | passes for the prior finite planting by inverse generation |
| V — verifiable | passes for a finite coloring by exact edge/color counting; fails for the paper's genuinely infinite negative/existence statements because no bounded certificate is provided |
| H — Track A | **fails** for the tractable graph and Matryoshka cases; unsupported for planted higher-arity cases because no theorem or parameter regime covers their distribution |
| H — Track B | **fails**: the best finite candidate has mechanical and compact costs 16,895 versus 16,895 operations; the explicit Matryoshka shortcut is one step in both views |
| overall | **rejected at STEP 0** |
