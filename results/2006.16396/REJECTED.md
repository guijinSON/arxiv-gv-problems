# Rejected at STEP 0 — arXiv:2006.16396

Paper: Ahmad H. Alkasasbeh, Danny Dyer, and Nabil Shalaby,
[*Applying Skolem Sequences to Gracefully Label New Families of Triangular
Windmills*](https://arxiv.org/abs/2006.16396) (v2).

## Decision

The proposed family passes **G** and **V**, but fails **H on both tracks**.  I
therefore stopped before writing a generator, as STEP 0 requires.

The native search problem would hand the solver a triangular cactus (in
particular, a Dutch windmill with three pendant triangles) and ask for an
injective vertex labelling whose absolute edge differences are all distinct.
For a graph with `m` edges, Section 2.2 requires labels in `0..m` and edge
differences `1..m` in the graceful cases; the near-graceful cases use vertex
labels in `0..m+1` and one of the two exact edge-difference sets stated there.
A proposed labelling is a genuine witness: injectivity, bounds, and the edge
differences can all be checked exactly in linear time.

Generation is also sound.  Theorems 3.1 and 3.2 map the position pairs of a
(hooked) Skolem sequence directly to labelled triples.  Lemma 3.3 preserves
their differences under translation (“pivoting”), the eleven constructions in
Sections 3.1–3.11 place the three pendant triangles, and Lemma 3.4 extends every
finite seed by concatenating/interlacing a Langford sequence as in Lemma 2.5.
Thus a builder can carry a certificate through the construction without solving
the graph it just made.

## Why Track A is not supportable

No theorem in the paper gives distributional hardness for recovering these
labellings.  The central result says the opposite kind of thing: Theorem 1.1
classifies every Dutch windmill with at most three pendant triangles as graceful
or near graceful, and Sections 3.1–3.11 prove this by explicit Skolem/Langford
constructions.  Theorem 2.6 supplies only the congruence obstruction; it is not a
hardness result.  Worst-case statements about unrelated graceful-labelling
instances would not establish hardness for this promised, highly structured
distribution.  Declaring `TRACK = "A"` would therefore be an unsupported
average-case claim.

## Why Track B also fails

The method that produces the certificate is already the compact structural
route: recognize the windmill type, instantiate the appropriate (hooked)
Skolem/Langford construction, turn every position pair `(a_i,b_i)` into the
paper's labelled triple, and translate the three pivot triples.  There is no
second, shorter invariant hidden in a generated instance.  A solver either
executes this displayed construction (or recalls the relevant finite table) or
runs a generic constraint search.

I quantified the comparison using the ordinary Dutch-windmill subfamily from
Theorem 3.1 and the standard six-case explicit Skolem construction cited by
Theorem 2.1.  This is the most favourable case for a compact answer; adding the
three pivot placements cannot improve the comparison.  At `n=124` blocks—the
largest multiple of four below the 256-atom cap, with 249 vertex labels—the
direct mechanical construction took **0.000242 seconds per instance** over
20,000 local repetitions and **1,287 counted integer arithmetic operations**
(formula evaluation plus the two endpoint offsets per block).  Its serialized
249-integer witness was 1,243 characters.  The **compact route is the same
six-case construction and costs the same 1,287 operations**; describing the
formula in six rows does not remove the arithmetic needed to instantiate the
witness.

The G9(c) operation cap makes the absence of a usable Track B window clearer.
Under the same accounting, `n=28` has 57 vertex-label atoms and costs **280
operations**; `n=32` has 65 atoms and costs **322 operations**.  Thus the largest
case inside the 300-operation intended-route cap is mechanically generated in
exactly the same 280 operations as its alleged shortcut.  For the paper's new
three-pendant types, the orders through 21 are literal table lookups followed by
the same linear triple conversion, while larger orders use Lemma 3.4 and remain
the same construction rather than creating a compression gap.

In the terminology requested by the task:

| candidate size | mechanical cost | compact route |
|---|---:|---:|
| 28 blocks / 57 labels | 280 integer operations | the identical 280-operation Skolem-to-triples construction |
| 124 blocks / 249 labels | 1,287 integer operations, 0.000242 s | the identical 1,287-operation construction |

The two costs are comparable because they are the same algorithm.  The larger
case also exceeds the no-tool arithmetic cap; the smaller one does not create a
mechanical-versus-insight gap.  This is therefore not a Track B no-tool
compression task.

## Alternatives considered

- Randomly renumbering vertices creates arbitrarily many files but not new
  problems: a correct `canonical_key` collapses them to the same windmill type.
- Hiding entries of a planted Skolem sequence would turn the task into a partial
  sequence-completion benchmark.  That distribution and its hardness are not
  studied in this paper, so its H claim would be imported rather than supported.
- Adding colours, anchors, decoys, or an external SAT/graph reduction would be a
  convenience discretisation.  It would discard rather than preserve the
  paper's construction and could not count as native coverage.

The rejection is therefore specifically **H**, not witness validity or exact
verification: G is supplied by Theorems 3.1–3.2 and Lemmas 2.5, 3.3, and 3.4;
V is a direct exact edge-difference check; Track A lacks a hard generated
regime, and Track B has no compression between the best specialized mechanical
method and the intended structural route.
