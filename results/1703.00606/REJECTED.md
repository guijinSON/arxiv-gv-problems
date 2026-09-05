# Rejected at Step 0: the coloring proof is already the certificate algorithm

Paper: T. Karthick and Suchismita Mishra, [*Coloring
\((P_6,\text{diamond},K_4)\)-free graphs*](https://arxiv.org/abs/1703.00606),
arXiv:1703.00606v1.

## Decision

No generator is shipped. The native witness problem—given a
\((P_6,\text{diamond},K_4)\)-free graph, output a proper coloring with at most
six colors—can pass **G** and **V** in isolation. The paper's proofs construct
such a coloring from constant-size graph anchors, and a checker can inspect all
edges exactly. It fails **H on Track A**, because the same structural proof is a
polynomial certificate-producing procedure and the paper proves no hard
distribution. It also fails **H on Track B**: on every paper-backed scalable
construction, either the compact route is the same partition procedure as the
mechanical route, or hiding the required anchor also hides the alleged shortcut.

This decision was made after reading the complete 13-page paper and its LaTeX
source, not the abstract. Steps 1--4 were intentionally not run after the Step-0
failure. There is no `gen_1703_00606.py`, self-test report, README, or oracle
transcript, and no gate result has been fabricated.

## Exact definition and results

Section 1 works with finite simple undirected graphs. A `k`-coloring is a map
from the vertices to `{1,...,k}` whose endpoints have different colors on every
edge. Here `P6` means an **induced** six-vertex path, and a diamond is `K4` with
one edge removed. Thus the main theorem concerns graphs containing none of an
induced `P6`, an induced diamond, or a `K4`.

The numbered results that control the possible family are:

- Theorems 1--3: every `(P2 union P3, diamond, K4)`-free graph is
  six-colorable, with a four-color subcase for a non-dominating triangle.
- Theorem 4: every `(P6, diamond, bull, K4)`-free graph is four-colorable.
- Theorem 5: every connected `(P6, diamond, K4)`-free graph containing an
  induced bull is six-colorable.
- Theorem 6: combining Theorems 4 and 5, every `(P6, diamond, K4)`-free graph
  is six-colorable.

The paper explicitly says in Section 1 that the complexity of `k`-Coloring on
the broader `(P6, diamond)`-free class was open. It also lists polynomial cases:
perfect diamond-free graphs (`O(k n^2)` in the cited result), even-hole- and
diamond-free graphs, and `(H, diamond)`-free graphs for a linear forest `H` on
at most five vertices. These statements do not supply hardness for the
K4-free, six-color witness distribution required here.

## Why the prior triage construction is invalid

The proposed recipe—plant six color classes and add arbitrary edges only
between different classes—guarantees a six-coloring but does **not** generate
the paper's promised class. Four vertices in four classes may form a `K4`; five
of their six possible edges may form a diamond; and six differently colored
vertices with only consecutive edges may form an induced `P6`. Checking for and
rejecting these obstructions would preserve the planted coloring, but the paper
gives no acceptance probability or distributional-hardness theorem for that
new rejection-sampled model. Sparse samples quickly acquire induced paths, and
dense samples acquire diamonds and `K4`s.

Consequently, worst-case NP-completeness of fixed-`k` coloring quoted in the
introduction cannot justify Track A for the proposed planted distribution.

## What produces the certificate

The proofs themselves answer the Step-0 discriminating question.

In Theorem 4, a non-perfect bull-free graph is anchored at a five-hole. Every
remaining vertex is classified by its adjacency to the five anchor vertices
into the sets `W_i`, `Y_i`, and `N_2`. The only internal subgraphs that need
coloring are unions of isolated vertices and edges. The proof bipartitions
those and explicitly writes down the four independent color classes in three
cases.

In Theorem 5, an induced bull is the five-vertex anchor. Again each remaining
vertex is put into one of a constant number of `A_i`, `A_jk`, `A_p14`, or
`N_2` sets by its five adjacency bits. Results (R1)--(R4) make the relevant
parts independent or unions of edges and isolated vertices. The displayed
sets `S_1,...,S_6` are the certificate. The perfect branch of Theorem 4 is
three-colorable because the graph is perfect and `K4`-free.

Given an anchor, classification takes at most `5n` anchor-adjacency checks,
ordinary graph traversal bipartitions the matching-like parts, and emitting the
certificate necessarily takes `n` color assignments. Without an anchor, a
literal implementation can enumerate five-vertex subsets for a bull or
five-hole and then apply exactly the same construction. This is polynomial
because the patterns have fixed size. More importantly, it is the construction
that a theorem-backed generator would itself have to expose or emulate.

Combining fixed-pattern detection, the displayed partitions, and the
`O(k n^2)` perfect diamond-free coloring result cited in Section 1 gives a
direct (naively `O(n^5)`) algorithm for producing a coloring with at most six
colors on the entire promise class. This does not settle the harder decision
problem for smaller `k` on all `(P6, diamond)`-free graphs, which is the open
problem the paper mentions.

Verification is cheaper still: check that the answer contains exactly one
color in `{1,...,6}` for each vertex and compare the two colors on every edge,
in `O(n+m)` exact integer operations.

## Mechanical cost versus compact route

I measured the most favorable paper-native candidate rather than rejecting it
merely because an algorithm exists. After Theorems 2 and 5 the paper gives its
tight example: the complement of the 16-regular Schlaefli graph on 27 vertices,
which is 10-regular and has chromatic number six.

For reproducibility, I used the standard 27-line realization with vertices
`a_i`, `b_i` (`i=0,...,5`) and `c_ij` (`0<=i<j<6`). Adjacency is intersection:
`a_i` meets `b_j` exactly when `i != j`; `a_i` and `b_i` meet `c_jk`
exactly when `i` is in `{j,k}`; and two `c` vertices meet exactly when their
index pairs are disjoint. The resulting graph has strongly regular parameters
`(27,10,1,5)`, as expected for the complement of the Schlaefli graph.

A standard recursive DSATUR six-coloring implementation was run on 20 random
vertex relabelings. It always produced a verified coloring. Median cost was
**82.5 candidate-color trials, 27 assignments, zero backtracks, and 0.000225
seconds**. The median selection scan count of the deliberately simple
implementation was 378.

There is also a compact coordinate coloring, but it is not meaningfully shorter:
give all `a_i` one color, all `b_i` a second, and color `c_ij` by the first of
the pivots `0,1,2` that belongs to `{i,j}`, using the sixth color for the three
pairs contained in `{3,4,5}`. That is 27 output assignments plus at most a few
dozen index tests. Thus the mechanical and compact routes are both comfortably
below 300 operations on the tight connected example.

Disjoint union is the only immediate way to scale this fixed tight example
without leaving the hereditary forbidden-subgraph class. I also measured nine
randomly relabeled copies, `n=243`, just below the 256-atom answer cap. Across
eight seeds, DSATUR succeeded 8/8 with median **757 candidate-color trials,
244.5 assignments, 1.5 backtracks, and 0.0492 seconds**. A compact route must
already emit 243 colors, so its minimum work is 243 assignments before it maps
any relabeled component to coordinates. The roughly three color trials per
output symbol are not a no-tool compression gap; both routes scale linearly in
the answer that must be written.

| candidate representation | mechanical cost | compact route | Track-B result |
|---|---:|---:|---|
| one tight 27-vertex example | median 82.5 color trials, 0.000225 s | about 27 assignments plus coordinate tests | both are by-hand scale |
| nine disjoint copies, 243 vertices | median 757 color trials, 0.0492 s | at least 243 assignments | same linear work; output nearly saturates cap |
| graph with a supplied bull or five-hole | at most `5n` classification checks plus traversal/output | the same partition and bipartition | no distinct shortcut |
| unlabeled graph with no supplied anchor | up to `C(n,5)` fixed-pattern candidates | no shorter route is supplied | alleged compact route is the same search |

For the last row, `C(243,5) = 6,774,333,588`. That large number does not rescue
Track B: the paper gives no invariant that locates the anchor in a dozen steps.
If a generator plants and visibly marks one, both routes become linear; if it
hides the anchor, the solver must perform the same detection work as the
mechanical procedure. Calling the hidden-anchor search a “compact route” would
confuse possession of the generator's secret with an insight available from
the instance.

## Why neither hardness track applies

### Track A

The main result is a chromatic bound proved by an explicit constant-anchor
decomposition, not an average-case hardness theorem. For theorem-backed
instances containing the anchor, the proof directly returns the coloring.
For the paper's hardest named example, the domain-standard coloring algorithm
above succeeds essentially without search. The paper's general statement that
fixed-`k` coloring is NP-complete concerns arbitrary graphs, while its open
complexity statement concerns the broader class with no `K4` exclusion. Neither
is a theorem about the generated distribution.

### Track B

The natural compact insight is precisely the executable partition algorithm.
When the anchor or Schlaefli coordinates are present, the ordinary method is
already a few dozen to a few hundred operations. When labels are randomly
hidden, recovering the anchor, twin quotient, or Schlaefli coordinates is the
same graph-search/isomorphism work the shortcut was supposed to replace. The
paper supplies no separate short invariant.

Scaling by disjoint union or duplication does not create compression.
Components and false-twin modules are recognized by standard traversal or
modular/twin reduction, and every additional vertex still contributes one
required answer atom. At the largest writable union, the reference algorithm
takes 0.0492 seconds and the compact route is already at 243 unavoidable output
assignments. A fourth genuinely failing in-context attack cannot be defended
for the tight example when DSATUR itself performs only 82.5 trials.

## Other native witness tasks considered

| candidate task | G | H | V | outcome |
|---|---:|---:|---:|---|
| Output a six-coloring of a promised graph | Can pass from Theorems 4--6 | **Fails A:** constructive partition; **fails B:** same route or no shortcut | Edge scan is exact | Reject |
| Color the tight Schlaefli-complement example | Pass by transforming a known colored graph | **Fails:** DSATUR takes 82.5 trials median; relabelings are not diverse instances | Edge scan is exact | Reject |
| Scale tight examples by disjoint union | Pass by composition | **Fails:** componentwise coloring is linear and answer length grows one-for-one | Exact | Reject |
| Duplicate vertices as in (R5) | Pass only at vertices with independent neighborhoods | **Fails:** fixed quotient and false-twin compression expose the template | Exact | Reject |
| Find an induced bull or five-hole | Easy to plant | No paper-backed hard distribution or compact route; fixed-pattern detection is polynomial | Five indices are checkable | Reject |
| Certify that the chromatic number is exactly six | Only one fixed example is cited as well known | No scalable executable lower-bound certificate is supplied | A coloring alone does not certify optimality | Fails G/V as an optimum family |
| Certify absence of `P6`, diamond, and `K4` | The input may be generated with the property | The paper supplies no separate bounded negative witness; exhaustive fixed-pattern checking is the verifier itself | Exact but not a hard answer search | Reject |
| Encode a hidden affine map or encrypted color labels | Plantable | Difficulty would come from a convenience wrapper absent from the paper | Exact | Not native paper coverage |

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G -- generatable | Passes in isolation | Theorems 4 and 5 explicitly assemble independent color classes; known examples can be relabeled or composed. |
| H -- Track A | **Fail** | The proof is a polynomial certificate-producing decomposition, and no generated-distribution hardness theorem is stated. |
| H -- Track B | **Fail** | 82.5 mechanical color trials versus about 27 coordinate assignments on the tight example; at 243 vertices, 757 trials versus at least 243 emitted colors. |
| V -- verifiable | Passes in isolation | One exact range check per vertex and one exact inequality per edge. |
| G6 standard algorithm | **Fail** | DSATUR solved 20/20 relabelings of the tight connected graph and 8/8 maximum-writable disjoint unions. |
| G9(c) scaling | Blocks the only easy scaling axis | Nine copies already require 243 of the allowed 256 answer atoms; both algorithms remain linear. |
| Overall | **Rejected at Step 0** | No paper-native family makes G, H, and V hold simultaneously under either track. |
