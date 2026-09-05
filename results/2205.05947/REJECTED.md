# Rejected at STEP 0: arXiv 2205.05947

Paper: Maria Axenovich and Michael Zheng,
[*Interval colorings of graphs -- coordinated and unstable no-wait
schedules*](https://arxiv.org/abs/2205.05947) (2022).

## Decision

No module is shipped.  The prior-triage proposal—construct one of the paper's
graphs with a planted interval edge-coloring and ask for the coloring—passes
**G** and **V**, but fails **H on both tracks**.  Section 3.1, Lemma 8 does not
merely prove that its graph is colorable: its proof writes down the color of
every edge in arithmetic progressions.  That displayed formula is the
certificate-producing algorithm for every instance in the proposed
distribution.

This is not a rejection based only on the existence of an algorithm.  The two
required costs are comparable.  At the largest native `F(b,T)` instance whose
ordinary edge-coloring witness fits the 256-atom cap, the paper's mechanical
formula performs **256 edge-color assignments**, while the alleged compact
route performs the same **256 assignments**.  The operation ratio is 1; there
is no repeated computation, hidden change of variables, or invariant that
compresses a million-step route.  A macro-encoded answer avoids writing all
256 colors, but then it is just the parameters of the very formula printed in
Lemma 8 and is recovered by one degree/neighborhood scan.  That version also
has no mechanical-versus-compact gap.

STEP 0 therefore stops the build as instructed.  No generator, self-test
report, README, or oracle transcripts are fabricated.

## Exact definitions and regimes

Section 1 defines an **interval coloring** of a finite connected graph as an
integer edge-coloring for which the colors incident with every vertex are
distinct consecutive integers.  A connected graph is `t`-interval colorable
when exactly `t` colors are used.  Its interval spectrum `S(G)` is the set of
such `t`, and its interval thickness is the minimum number of interval
colorable subgraphs whose edge sets partition `E(G)`.

The easy regimes are explicit and matter here:

- Section 1 says every tree is interval colorable.
- Section 1 says every regular bipartite graph is interval colorable by
  decomposing it into perfect matchings using Koenig's theorem.  This is a
  polynomial certificate route, not a hard Track-A family.
- Section 3.1, Lemma 8 gives an explicit coloring of the exact gadget used by
  the gap construction.
- Section 3.2, Lemma 9 composes shifted copies of that same explicit coloring;
  the proof also gives the entire spectrum by a displayed union of intervals.

Theorem 2 is an asymptotic upper bound, `theta(n)=o(n)`, obtained via the
Regularity Lemma and regular bipartite subgraphs.  It is not a hardness theorem
or a hard generated distribution.  Theorem 3 is an explicit existence
construction for spectra with gaps, again not a computational hardness
result.  No theorem in the paper establishes average-case or
planted-distribution hardness for finding an interval coloring.

## The certificate algorithm and its exact cost

For positive `b <= D`, even `D`, Section 3.1 sets `T=D+25` and builds
`F(b,T)` from five complete bipartite pieces and seven extra edges.  Direct
counting from the definition gives

```text
|V(F)| = 2D + 37
|E(F)| = 4D - b + 63.
```

Lemma 8's proof then explicitly assigns the nine distinguished edge values
and gives the remaining colors as the displayed ranges on `U_d`, `V_l`,
`V_r`, `V_0`, and `U_r`.  Evaluating those ranges is linear output work; it
does not solve a search problem.

Take `D=64` and `b=63`.  Then `F(b,T)` has 165 vertices and exactly 256
edges, so one JSON atomic color per edge is exactly at the output cap.  Both
routes have the following cost:

| route | certificate work at this size |
|---|---:|
| Lemma 8 mechanical construction | 256 edge-color assignments |
| solver who recognizes the Lemma 8 structure | 256 edge-color assignments |

The graph itself does not hide the formula behind an expensive recognition
problem.  In this example the distinguished vertices have degrees `D+26=90`,
`D+14=78`, and `D+3=67`; the two side hubs have degree 8, the pendant leaves
identify the `u` side, and the remaining sets are twin classes determined by
their neighborhoods.  An arbitrary vertex relabelling is undone by one
`O(|V|+|E|)` degree/neighborhood scan.  The residual left/right reflection
gives another valid coloring, so it is not a secret that must be recovered.

This proves the two hardness failures:

- **Track A fails.**  The generated distribution has a direct linear-time
  certificate algorithm printed in the proof, including after relabelling.
- **Track B fails.**  The compact public route is the same formula evaluation
  as the mechanical route: 256 assignments versus 256.  With a symbolic macro
  certificate, both costs collapse to the same linear graph scan plus a
  constant number of range parameters.  There is no shorter insight separated
  from the algorithm.

## Why the central gap construction does not rescue the paper

The smallest nontrivial instance of the paper's main spectrum construction is
already too large for an explicit positive witness.  In Section 3.2 take
`k=1,d=24`, the minimum stated construction regime.  Then

```text
F_0 = F(1, 3*k^2*d + 1) = F(1,73), so D_0=48 and |E(F_0)|=254;
F_1 = F(1, 2*1*d*k + 1) = F(1,49), so D_1=24 and |E(F_1)|=158.
```

The construction identifies their pendant edges, leaving
`254 + 158 - 1 = 411` edges.  A concrete interval coloring therefore needs
411 edge colors, already above the 256-atom cap before `k` or `d` grows.

This alone would be an answer-format limitation, not a reason to condemn the
paper.  The decisive problem is that the available compression is also easy:
Lemma 9 says to shift each explicit Lemma 8 coloring until the identified
pendant colors agree.  A macro certificate consisting of orientations and
shifts is obtained by direct evaluation in `O(k)` and checked by expanding the
same formulas.  Its mechanical and compact routes are again identical, so the
compressed version fails H rather than reaching `cap_bound`.

Asking for the exact spectrum or for a missing color count does not satisfy the
witness rule.  Colorings certify the positive members of `S(F)`, but a list of
interval endpoints is not an executable certificate that no omitted coloring
exists.  Encoding the rigidity proof as a bounded refutation could make the
negative claim verifiable, but for these named gadgets the refutation is the
same displayed classification from Lemmas 8 and 9; selecting or reproducing it
is a direct formula evaluation and still fails H.

## Other native candidates considered

| paper object | possible witness | outcome |
|---|---|---|
| `F(b,T)` from Lemma 8 | one integer color per edge | G and V pass; H-A and H-B fail because the proof prints the complete linear-time coloring |
| `F(k,d)` from Lemma 9 | shifted colorings of all component gadgets | smallest explicit witness has 411 atoms; macro shifts are a direct `O(k)` formula and fail H |
| exact spectrum/gap | positive colorings plus a negative certificate | the paper supplies a mathematical rigidity proof, not a separately searchable finite witness; compiling it merely turns the answer into its explicit classification table |
| regular bipartite subgraphs in Theorem 7 | perfect-matching decompositions | polynomial by Koenig's theorem; inverse-planted decompositions have no paper-backed hard distribution |
| interval-thickness decomposition | edge partition plus a coloring of every part | exact checking is possible, but the theorem is an upper-bound existence proof and supplies no hard generated regime; a private planted partition is not a solver-visible Track-B shortcut |
| Class-2 non-colorability examples | certified negative | the triangle is the fixed easy example; the paper gives no scalable bounded refutation family with a hardness regime |

Adding a finite-field encoding, SAT gadget, planted subgraph problem, or hidden
arithmetic coordinatization could manufacture a different hard benchmark, but
none is central to this paper.  It would be a convenience reduction that
discards the interval-spectrum mathematics and cannot rescue native coverage.

## Final gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G — certificate known without solving | passes in isolation | Lemma 8's explicit coloring and Lemma 9's shifted composition |
| V — exact witness verification | passes in isolation | check properness and consecutive incident colors by integer comparison |
| H — Track A | **fails** | the exact generated gadget distribution has the paper's direct `O(|E|)` formula |
| H — Track B | **fails** | 256 mechanical assignments versus the same 256-assignment compact route; macro encoding collapses both equally |
| central Theorem-3 witness size | over cap explicitly | 411 colors already at `k=1,d=24`, while its only paper-native compression is the easy Lemma-9 formula |
| overall | **rejected at STEP 0** | no paper-supported family makes G, H, and V hold simultaneously |

