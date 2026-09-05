# Rejected at Step 0: arXiv 1610.05406

Paper: Ilkyoo Choi, Jaehoon Kim, Alexandr V. Kostochka, and André Raspaud,
[*Strong edge-colorings of sparse graphs with large maximum degree*](https://arxiv.org/abs/1610.05406)
(v2, 2018).

## Decision

No paper-native family clears **G + H + V**. A complete strong edge-coloring is
a finite, exactly checkable witness, and it can be planted or produced by the
paper's constructive arguments, so G and V are available. The natural families
fail **H on both Track A and Track B**, however. This decision was made after
reading the complete 20-page paper and its LaTeX source, before implementing a
generator, as required by Step 0.

This is not a rejection merely because an algorithm exists. The strongest
writable native construction, the sharp graph `K_Delta(3)`, was measured below:
its mechanical certificate producer and compact route are the same 255 color
assignments, while a structure-aware candidate succeeds with probability one.

## The exact paper objects and regimes

Section 1 defines a strong `k`-edge-coloring as a map from the edges of a finite
graph to `{1,...,k}` in which two edges receive different colors whenever they
are adjacent or both adjacent to a common edge. Equivalently, every color class
is an induced matching. A submitted edge-to-color map is therefore checked
exactly by inspecting edge pairs; no theorem or search is needed in the checker.

The actual parameter regimes are:

- Theorem 1.1: every 2-degenerate graph has a strong coloring with at most
  `5 Delta + 1` colors.
- Theorem 1.2: if `Delta >= 9` and `Mad(G) < 8/3`, then `3 Delta - 3` colors
  suffice.
- Theorem 1.3: if `Delta >= 7` and `Mad(G) < 3`, then `3 Delta` colors suffice.

The paper also identifies the easy mechanisms that matter here. The Introduction
gives the ordinary greedy `2 Delta(Delta-1)+1` bound. Lemma 2.1 turns any partial
coloring with an `(f,k)`-degenerate edge sequence into a complete coloring by
greedily selecting one unused color per edge. Section 3 proves Theorem 1.1 by an
effective recursion: remove a leaf or a locally identifiable 2-degenerate-core
configuration, color the smaller graph, perform the displayed constant-size
color switches, and insert the removed edges using Lemma 2.1. The recursion
strictly reduces the number of non-leaf vertices (and then the number of edges),
so local degree/neighborhood scans make it a polynomial certificate producer.
Sections 4 and 5 use the same smaller-instance, switching, and greedy-extension
pattern, with discharging used to prove that a reducible configuration exists.

Thus asking for the theorem-guaranteed number of colors is not a Track A task:
the proof produces the witness. Asking for fewer colors can recover the general
computational coloring problem, but none of Theorems 1.1--1.3 proves hardness for
an inverse-generated distribution of such promised yes-instances.

## Step-0 certificate question

| Candidate native task | What produces the certificate | Outcome |
|---|---|---|
| Color a 2-degenerate graph with `5 Delta+1` colors | Section 3's recursive reductions, switches, and Lemma 2.1 greedy extension | G and V pass; Track A fails because the theorem proof is an effective certificate-producing procedure. |
| Color a `Mad(G)<8/3` or `Mad(G)<3` graph at the paper's bound | Sections 4 or 5 recursively color smaller graphs and extend | Same obstruction; the paper supplies no separate compact decoder for Track B. |
| Color the sharp `K_Delta(3)` examples | Give every edge a different color, as Section 1 observes | Trivial under a structure-aware prior and by the obvious in-context ansatz. |
| Sample a coloring first and add only compatible edges | The generator's retained private coloring | G and V pass, but the paper has no average-case theorem for this planted distribution; worst-case coloring hardness would not establish Track A. |
| Publish enough planting structure to decode that coloring | Replay the published structure | Track B fails: replay and the alleged shortcut do the same per-edge work; if the structure is withheld, there is no public compact route. |

## Mechanical cost versus compact route

The paper defines `K_Delta(t)` by taking `K_t` and adding
`Delta-t+1` leaves at each core vertex. For `t=3`, every pair of edges is at
strong distance at most two, so Section 1 obtains

```text
chi'_s(K_Delta(3)) = |E| = 3 Delta - 3.
```

The largest such witness below the 256-atom cap is `Delta=86`, with 255 edges.
Using colors `1,...,255` in the displayed edge-list order works for every
vertex relabeling and every edge ordering; the graph does not even need to be
inspected beyond knowing its edge count.

The direct constructor was timed in CPython over eleven batches of 100,000
certificates. Creating the 255-entry color list took a median of
**1.076e-6 seconds** per certificate (range `0.939e-6` to `1.322e-6`). The
JSON answer has **255 atoms and 1,167 characters** with ordinary
`json.dumps` formatting.

| quantity at `Delta=86` | measured value |
|---|---:|
| mechanical certificate work | 255 color assignments |
| compact route after recognizing the construction | the same 255 assignments |
| mechanical/compact operation ratio | 1 |
| median certificate-construction time | 1.076 microseconds |
| answer size | 255 atoms / 1,167 characters |

There is no no-tool compression gap. The alleged insight, "all edges need
different colors," is already the complete linear-time algorithm, and the
answer itself requires the same 255 emissions. Increasing `Delta` only crosses
the answer cap; it does not separate the two routes.

The guessing calculation is even more decisive. A naive sampler from all
`255^255` color words would see valid density
`255! / 255^255`, approximately **7.20e-110**. That is the misleading prior
forbidden by G4. Once the visibly necessary requirement that all 255 colors be
used exactly once is enforced, the bounded candidate language is the 255!
permutations, and **every one is valid**. The structure-aware valid fraction is
therefore exactly **1**, and the by-hand attack "assign a fresh color to each
edge" succeeds on every instance.

A compressed symbolic certificate does not help. On `K_Delta(3)`, an identity
rule such as "edge in output position i gets color i" is valid without search,
so an obvious ansatz again succeeds with probability one. On a general sparse
graph, a hidden planted rule is private generator state rather than a
solver-visible compact route. Adding an affine code, precoloring gadgets, or a
succinct circuit to expose that rule would make the difficulty come from an
extra benchmark encoding not studied in this paper.

## Why Track A fails

For the theorem-bound problem, Section 3 plus Lemma 2.1 gives an effective
certificate constructor, and the sharp examples have the still simpler direct
constructor measured above. For a lower-color planted problem, inverse
generation alone says nothing about recovery hardness. The paper proves
extremal upper bounds, not a distributional hardness theorem, and its parameter
regimes do not validate a randomly planted yes-distribution. Claiming Track A
would therefore substitute a worst-case coloring intuition for the required
claim about generated instances.

Randomly relabeling a sharp example also cannot create an unlimited diverse
family: at fixed `Delta`, every seed is the same graph up to isomorphism and
must have the same canonical key. Adding random supergraph structure either
leaves the fresh-color attack valid when the palette has one color per edge, or
abandons the paper's sharp construction and creates an unanalyzed planted-CSP
distribution.

## Why Track B fails

The sharp family has a measured 255-operation mechanical route and the same
255-operation compact route. It also fails G4 and the required in-context G6
attack outright. For arbitrary graphs in the theorem regimes, the recursive
proof is the available mechanical method, but the paper supplies no distinct
invariant, symmetry, or change of variables that recovers its individual edge
colors in fewer steps. Hiding a sampled coloring does not create such a route;
revealing it reduces both routes to replay.

Consequently there is neither the large mechanical-versus-compact gap required
by Track B nor a fourth failing by-hand attack. Oracle failures on a 255-entry
transcription would not repair either analytic failure.

## Gate diagnosis

| Requirement | Result |
|---|---|
| G -- generatable | **Passable.** Plant a full coloring, use the Section 3 recursion, or use the explicit sharp construction. |
| V -- exact witness verification | **Passable.** Check color bounds and every pair of edges at strong distance at most two. |
| H -- Track A | **Fails.** The theorem-bound witness is constructible, and no theorem covers hardness of a lower-color planted distribution. |
| H -- Track B | **Fails.** The best native case has 255 mechanical operations versus the same 255 compact operations, with no separate shortcut on general instances. |
| G4 on the strongest compact native case | **Fails.** Structure-aware valid fraction is exactly 1. |
| G6 in-context attack | **Fails.** Assigning a fresh color to each edge succeeds for every sharp instance. |
| G8 diversity for sharp examples | **Fails at fixed size.** Seeds only relabel one isomorphism class. |
| Overall | **Rejected at Step 0.** |

No `gen_1610_05406.py`, self-test report, or oracle transcript was created:
doing so after the analytic H/G4/G6 failures would manufacture evidence for a
family already known not to qualify.
