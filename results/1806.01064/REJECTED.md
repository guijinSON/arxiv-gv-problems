# Rejected at Step 0: arXiv 1806.01064

Paper: Aijun Dong and Jianliang Wu, [*Equitable Coloring and Equitable
Choosability of Planar Graphs without chordal 4- and 6-Cycles*](https://arxiv.org/abs/1806.01064)
(v3, 2019).

## Decision

No generator is shipped. The native witness--an equitable vertex coloring or
equitable list coloring--is easy to generate by planting and cheap to verify,
so **G** and **V** are passable. The proposed family fails **H on Track A**, and
the paper does not provide the mechanical-versus-compact gap needed for
**Track B**. This decision follows the full paper, especially the definitions
in Section 1, Lemmas 2.4--2.10, Theorems 2.11 and 2.14, and Section 3.

This is not a rejection merely because an algorithm exists. The two plausible
representations of the witness were costed below. A full coloring has no
compression gap: at the largest clean writable example, both the mechanical
route and the purported compact route require 252 color emissions. A symbolic
cycle-coloring rule is constant-size, but every candidate in its natural
bounded language is valid, so it fails guess resistance and the obvious
by-hand attack.

## What the paper actually says

Section 1 defines a chordal `r`-cycle as an `r`-cycle having an additional edge
between two of its vertices. A proper `k`-coloring is *equitable* when every two
color-class sizes differ by at most one. For list coloring, every vertex is
given a list of exactly `k` acceptable colors, and an equitable list coloring
is a proper choice from those lists in which each color is used on at most
`ceil(|V|/k)` vertices. The list-coloring definition does **not** say that the
global palette has exactly `k` colors.

The exact theorem regime is:

- Theorem 2.11: every planar graph without chordal 4- and 6-cycles is
  equitably `k`-colorable for `k >= max(7, Delta(G))`.
- Theorem 2.14: the same statement holds for every `k`-uniform list
  assignment.

These are existence/structure theorems, not hardness theorems. The proof is
recursive and certificate-producing: Lemmas 2.3 and 2.8 guarantee one of the
bounded configurations in Figures 1--2; Corollary 2.7 makes the graph
4-degenerate; the proof selects a set `S` by minimum-degree deletions, colors
`G-S` recursively, and extends the coloring with Lemma 2.4 (or Lemma 2.5 for
lists). All configuration patterns have constant size, so exhaustive local
pattern recognition and recursion give a polynomial procedure.

The paper also identifies the easy regimes that a generator would have to
avoid:

- Lemma 2.9 is the Hajnal--Szemeredi bound for every graph when
  `k >= Delta(G)+1`.
- Lemma 2.10 gives equitable list coloring for `Delta(G) <= 3` and
  `k >= Delta(G)+1`.
- Corollary 2.7 says every graph in the paper's class is 4-degenerate.
- Section 3 explicitly emphasizes the structural extension from previously
  studied 3-degenerate cases; it states no computational or distributional
  hardness result.

Thus a benchmark that uses `k=7` with `Delta <= 6` is already in the general
Hajnal--Szemeredi easy regime. Using the paper-specific boundary
`k=Delta=7` avoids that particular lemma, but Theorem 2.11's own reducible-
configuration recursion still supplies the standard mechanical route.

## Step-0 certificate question

| proposed native task | certificate producer | outcome |
|---|---|---|
| Given `G`, return an equitable `k`-coloring | Theorem 2.11: locate a bounded reducible configuration, delete `S`, recurse, and extend by Lemma 2.4 | G and V pass; Track A fails because the theorem regime has a polynomial constructive route and no generated-distribution hardness theorem. |
| Given `G,L`, return an equitable list coloring | Theorem 2.14 uses the same recursion and Lemma 2.5 | Same Track-A failure; list membership does not create a paper-backed hard distribution. |
| Plant a balanced coloring, then add planar edges between unlike colors | The generator retains the planted coloring | G and V pass, but the paper proves no average-case hardness for this planted distribution; sparse/degenerate graph algorithms and construction leakage are unaddressed. |
| Use a chordless cycle or forest to guarantee the forbidden-cycle condition | Periodic coloring along each path/cycle | The obvious in-context attack succeeds on every instance; mechanical and compact costs are identical and output-linear. |
| Ask for one of the reducible configurations in Figures 1--2 | Scan constant-radius neighborhoods and degree labels | The witness is short, but the domain-standard local scan is already the paper's method. There is no shorter paper-supplied invariant, so Track B has no compact route. |
| Ask for a symbolic rule that expands to a cycle coloring | Choose a start/direction and permute the seven colors | Every well-formed rule gives a valid coloring when the cycle length is a multiple of seven; structure-aware guess probability is 1. |

## Track A failure

Track A requires a hardness theorem for the **generated distribution**, not
worst-case coloring hardness. This paper contains no computational-hardness
theorem at all. More strongly, its main proofs describe how to obtain a
coloring throughout the stated parameter regime by repeatedly finding one of
42 fixed local configurations and extending a smaller coloring. Declaring a
planted distribution hard because its raw balanced-coloring space is large
would therefore substitute cardinality for an attack result and ignore the
paper's own constructive proof.

Random relabeling cannot repair this. It preserves the graph and hence must
preserve `canonical_key`; relabelings of one cycle, forest, or fixed gadget are
duplicates rather than an unlimited structurally diverse supply. Adding
construction-specific tags, decoy gadgets, or a hidden CSP would move the
hardness into a surrogate not studied in the paper.

## Mechanical cost versus compact route (Track B audit)

There are two relevant cost comparisons.

### Full native coloring

An honest full coloring has one color atom per vertex. The 256-atom cap
therefore limits the instance to at most 256 vertices, and using a multiple of
seven gives the representative maximum `n=252`. On the clean scalable subclass
`C_252` (planar, maximum degree 2, and with no chordal cycle), the standard
algorithm writes the periodic coloring `1,2,...,7,1,2,...`. A local Python
measurement over 200,000 constructions gave **12.98 microseconds per
coloring**. It performs exactly **252 color emissions**.

After recognizing the cycle, the compact route is the same operation: it must
still emit exactly **252 colors**. The mechanical/compact ratio is therefore
**252:252 = 1:1**, and both routes sit at the intended-route cap before any
graph traversal or parsing is counted. The raw probability that an independent
uniform 7-color sequence has unequal adjacent colors is approximately
`(6/7)^252 = 1.35e-17`; this large answer space does not make the family hard,
because “walk the cycle and repeat seven colors” succeeds deterministically.

For a generic boundary-regime graph with `k=Delta=7`, a direct
implementation of the paper's proof can scan the 42 fixed configurations at
each seven-vertex recursive deletion. Counting only pattern-anchor attempts at
`n=252` gives at most

```text
42 * (252 + 245 + ... + 7) = 195,804
```

before the 252 output writes. That is a feasible mechanical polynomial
procedure, but it is not a Track-B compact route: the paper supplies no global
invariant that replaces those local scans, so the intended route is the same
reducible-configuration computation and is far above 300 operations.

### Symbolic compressed coloring

For a cycle whose vertices are given in cyclic order, the natural executable
certificate consists of a starting position, one of two directions, and a
permutation of the seven colors. When `n` is divisible by seven, **every** such
certificate expands to a proper equitable coloring. Consequently, under the
structure-aware bounded language,

```text
valid certificates / candidates = (n * 2 * 7!) / (n * 2 * 7!) = 1.
```

This violates G4 by six orders of magnitude and makes the by-hand attack
“follow the cycle and repeat the palette” succeed on every seed. Restricting
the grammar to one canonical start or palette only shrinks numerator and
denominator together; it does not create guess resistance.

The two representations leave no valid Track-B window. The full witness is
output-linear with no compression, while the short symbolic witness is
immediately guessable. More elaborate planted graphs do not inherit a compact
decoder from Theorem 2.11 or 2.14; if the plant is hidden, the compact route is
gone, and if it is exposed, a construction-aware graph attack recovers it.

## Gate diagnosis

| requirement | result |
|---|---|
| G -- known certificate by construction | **Passable.** Inverse generation can retain a balanced coloring, and Theorems 2.11/2.14 give theorem-backed recursive existence. |
| V -- exact witness checking | **Passable.** Check shape/list membership, every edge inequality, and exact color counts in linear time. |
| H -- Track A | **Fails.** No theorem supports hardness for a generated distribution, while the paper's own theorem proof gives a polynomial recursive constructor in its full regime. |
| H -- Track B, full witness | **Fails.** At the largest clean writable instance, the mechanical and compact methods both require 252 output operations; for generic instances the local-recursion method has no shorter invariant-based replacement. |
| H -- Track B, symbolic witness | **Fails.** The natural bounded symbolic language for the scalable cycle subclass has valid-candidate density 1, and the obvious in-context attack succeeds universally. |
| G8 -- diversity of relabeled explicit examples | **Fails as a scaling substitute.** Correct canonicalization collapses all relabelings of one underlying graph. |
| Overall | **Rejected at Step 0.** No paper-native family found clears G, H, and V under either declared track. |

No `gen_1806_01064.py`, self-test report, README, or oracle transcript was
fabricated after this Step-0 failure. A future reopening would need a genuinely
different paper-native certificate with both a measured expensive reference
algorithm and a sub-300-operation structural decoder; merely planting another
equitable coloring is not sufficient.
