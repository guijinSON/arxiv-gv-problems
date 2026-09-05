# Rejected at Step 0: arXiv 1512.01613

Paper: Wei-Hao Mao, Fei Gao, Yi-Jin Dong, and Wen-Ming Li,
[*A Novel Paradigm for Calculating Ramsey Number via Artificial Bee Colony
Algorithm*](https://arxiv.org/abs/1512.01613) (2015, v2).

## Decision

No module is shipped. A native Ramsey-graph witness or partial-completion
witness can be generated and checked exactly, but no family justified by this
paper clears **H on either Track A or Track B**.

- **Track A fails.** The paper proves no worst-case or distributional hardness
  result for its ABC search, much less one for an answer-first distribution.
  It studies the single fixed target `R(3,10)` and reports heuristic searches,
  not an asymptotic hard parameter regime. Planting erased edges in one of the
  appendix graphs would create a new completion distribution with no hardness
  theorem behind it.
- **Track B fails.** A hidden planted completion has no solver-visible compact
  route: the only route is the same completion search used mechanically. If
  the appendix construction or erased-edge map is exposed so that a compact
  route exists, the mechanical algorithm is already the same lookup/copy
  operation. The mechanical and compact routes therefore have equal length;
  there is no no-tool compression gap.

This is not a rejection merely because an efficient verifier exists. Exact
verification is available and generation is possible in isolation. The
failure is that **G, H, and V cannot be made to hold simultaneously for an
unlimited, canonically diverse family whose difficulty comes from the paper**.
Implementation stopped before Step 1, so no generator, self-test report, or
oracle transcripts were fabricated.

## What the paper actually defines

Section 1 defines an `r(p,q,n)` graph as a simple graph on `n` vertices with no
`p`-clique and no independent set of size `q`. Section 3.1 makes the search
objective

`f(G) = (# q-vertex independent sets) + (# p-cliques)`,

so `f(G)=0` is the required certificate property. Section 3.2 calls two graphs
adjacent when they differ in one edge.

The paper has only one theorem of its own in the relevant development.
Section 2.1, Theorem 1 gives the necessary degree interval

`n - R(p,q-1) <= deg(v) <= R(p-1,q) - 1`.

It does not construct a Ramsey graph and is not sufficient to certify one.
Section 2.2 then imports the unique 35-vertex `r(3,9,35)` graph and states that
it is 8-regular. Section 2.3 proposes extending that fixed graph by five
vertices: select one of 14 triangle-free five-vertex graphs, sample degrees in
`{4,...,9}`, and sample a permutation of the 35 old vertices. These steps
produce ABC starting points, not certified `r(3,10,40)` graphs.

Section 3.4 applies the basic Artificial Bee Colony heuristic to one-edge
neighbors. It gives no success guarantee or running-time bound. Section 4 says
the search did **not** find an `r(3,10,40)` graph: its best outputs still have
two or three triangles. The appendix prints four fixed 40-vertex adjacency
lists. Deleting selected vertices from two of them yields 39-vertex
triangle-free graphs with no independent 10-set. The paper inconsistently
calls these `r(3,9,39)` graphs in several places; under its own definition and
the displayed data they are `r(3,10,39)` graphs, since they do contain
independent 9-sets.

## Certificate-producing algorithms and measured costs

### The paper's native search

The ABC routine is the procedure that produces the reported graphs. It is a
heuristic, not a theorem-backed constructor: the paper does not report a bound
on objective evaluations and its run terminates at fitness 2 or 3 rather than
at 0. Consequently it cannot serve as a scalable generator that knows a
certificate by construction.

For fitness evaluation, Section 3.3 precomputes the independent sets of sizes
5 through 8 in the 35-vertex core:

`20,265 + 22,995 + 13,760 + 3,360 = 60,380` sets.

Each candidate extension is then checked by scanning/filtering those stored
sets against the five new vertices. Thus the paper's mechanical evaluation
cost is at least a 60,380-entry scan per candidate, before the unspecified
number of ABC candidates. The paper supplies no shorter invariant. The
compact route licensed by that section is the identical 60,380-entry scan,
so its mechanical/compact operation ratio is **1**. Merely asking a model to
perform this scan without tools would test patience, not structural insight.

### Exact verification of the fixed appendix witness

I parsed Graph A directly from the appendix. It has 176 undirected edges and
exactly the three triangles

`(3,37,38), (37,38,39), (37,38,40)`.

Deleting vertex 37 or 38 removes every triangle. An exact bit-set
branch-and-bound search in the complement found no independent 10-set after
21,395 and 18,494 recursive nodes respectively. Over 21 repeated runs, the
median wall times on this machine were **0.004954 s** and **0.003803 s**. The
same graphs do have independent 9-sets, confirming the notation issue above.

A literal verifier following Section 3.1 would inspect
`C(39,3)=9,139` triples and `C(39,10)=635,745,396` ten-subsets. At up to 3 and
45 pair queries per subset, respectively, that is at most **28,608,570,237**
edge queries. The faster exact branch-and-bound measurement shows that V is
not the obstacle; it also shows why an already printed graph is not a hard
search family.

## Mechanical cost versus compact route for every generatable option

The natural transformation-based escape is to erase `h` edge decisions from
a verified 39-vertex appendix graph and ask for a completion. At `h=24`, the
structure-aware answer space is `2^24 = 16,777,216`, so a unique completion
would be sufficiently guess-resistant.

There are only two ways to present that construction:

| Proposed family | Mechanical cost | Compact route | Result |
|---|---:|---:|---|
| Hide 24 erased decisions from a fixed appendix graph | Up to `2^24 = 16,777,216` completions, with exact Ramsey checking or SAT-style pruning for each branch | No separate shortcut is present in the instance; recovering the private plant is the same completion problem, so the available compact route is also the 24-bit search | Track B fails: private generator state is not an insight |
| Reveal the appendix template or the erase/carry map | 24 table lookups/copies | The same 24 lookups/copies | Track B fails with ratio 1: nothing is compressed |
| Output one of the four appendix graphs directly | Copy its displayed adjacency data (Graph A has 176 edges) | The same lookup and copy, with at least the output-size work | G is finite up to relabelling and H fails |
| Relabel an appendix graph | One vertex permutation plus copying the fixed graph | The identical permutation/copy | Canonical duplicates, not an unlimited supply |
| Evaluate `f(G)` on the paper's five-vertex extensions | The Section 3.3 scan of 60,380 stored core sets per candidate | The identical scan; no shorter paper-backed identity is given | Track B fails with ratio 1 |

One could manufacture a different Track B puzzle by imposing an external
circulant, cograph, or algebraic pattern on the erased edges. That pattern
would provide a shortcut, but it would be benchmark-added mathematics absent
from this paper. If exposed, its own recognition/evaluation algorithm would
be the mechanical route; if hidden, it would again be private planting rather
than a solver-visible insight. Such a puzzle would use only the generic phrase
"count cliques and independent sets," not this paper's construction.

## Why scaling and relabelling do not rescue the family

The appendix supplies four fixed labelled near-solutions, not a parameterized
construction. Relabellings are all the same problem under the required
canonical key. The paper does not prove those four graphs nonisomorphic (it
lists that question as future work), and even four canonical classes are not
an unlimited family.

Standard graph compositions also do not preserve the target property in the
needed way: disjoint union creates large independent sets, joins create
triangles, and vertex blow-ups do one or the other. More elaborate Ramsey
constructions exist outside this paper, but importing one would move both the
certificate and the hardness basis away from the assigned source.

## Gate diagnosis

| Requirement | Result |
|---|---|
| G — native Ramsey graph from `(p,q,n)` | **Fails as a scalable paper-backed construction:** Theorem 1 is only necessary, ABC is heuristic, and the appendix is finite. |
| G — partial completion of a fixed appendix graph | **Passes in isolation:** erase bits from a known verified graph and carry the bits as the certificate. |
| V — exact checking | **Passes in isolation:** complete the graph and check all forbidden cliques/independent sets exactly; the measured branch-and-bound verifier is fast on the fixed witness. |
| H — Track A | **Fails:** no hardness theorem or parameter regime applies to the planted completion distribution, and the paper studies one fixed order. |
| H — Track B | **Fails:** hidden plants have no public shortcut; exposed plants take 24 mechanical operations and the same 24 compact operations. The paper's own fitness shortcut likewise costs 60,380 scans by either route. |
| Overall | **Rejected at Step 0:** no option passes G, H, and V together. |

The rejection therefore records both Track B comparisons explicitly:
**16,777,216 versus 16,777,216** operations for a hidden 24-bit completion,
or **24 versus 24** operations when the construction is visible. In neither
case is there a mechanical-to-compact gap for an oracle to discover.
