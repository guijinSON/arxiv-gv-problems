# Rejected at Step 0: arXiv 1403.5807

Paper: Armen S. Asratian and Carl Johan Casselgren,
[*Solution of Vizing's Problem on Interchanges for Graphs with Maximum Degree 4
and Related Results*](https://arxiv.org/abs/1403.5807).

## Decision

No generator is shipped. The proposed inverse-generated interchange family can
pass **G** and **V**, but it has no defensible **H** claim on either track.
This is a Step-0 rejection, so no module, self-test report, README, or oracle
transcripts were fabricated.

The exact candidate considered was: start with a proper edge-coloring, apply a
random legal sequence of Kempe interchanges, reveal only the two endpoint
colorings, and ask for a sequence back. The generator can retain and reverse its
sampled moves, while a checker can recompute each current bicolored component and
replay the submitted sequence. Those observations establish generatability and
exact witness verification only. A hidden generation trace is not a
solver-visible shortcut and therefore does not establish hardness.

## What the paper actually defines

Section 1 works with finite simple graphs. A proper `t`-edge-coloring assigns a
color in `1,...,t` to every edge, with distinct colors on adjacent edges. For two
colors `a,b`, their induced edge-subgraph is a disjoint union of alternating
paths and even cycles. One **interchange** swaps `a` and `b` on exactly one
connected component. A witness sequence would consequently be finite and
locally checkable: at each step a checker recomputes the selected component,
swaps its colors, checks properness, and finally compares with the requested
coloring.

Theorem 1.3 is a universal positive reachability result, not a hardness result:
if `G` is Class 1 with maximum degree 4, every proper `t`-edge-coloring for
`t >= 5` can be transformed to any supplied proper 4-edge-coloring. Corollary
1.4 similarly puts every proper 5-edge-coloring of such a graph in one Kempe
class.

The easy and exceptional regimes are explicit:

- Theorem A gives the standard Vizing algorithm when `t >= Delta(G)+2`.
- Theorem B, quoted in Section 1, gives Kempe equivalence for maximum degree at
  most 3 with `Delta+1` colors.
- Proposition 3.1 gives an explicit fan/path algorithm whenever the subgraph
  induced by maximum-degree vertices is acyclic.
- Theorem 1.6 extends equivalence to the stated higher-degree acyclic regime.
- Figure 1 shows that two proper 4-edge-colorings need not be connected even by
  transformations on two- or three-colored subgraphs. It is a fixed obstruction,
  not an unlimited hard positive-witness family.

## The certificate-producing algorithm

The paper's proof is constructive. Section 3 labels its procedure
**Algorithm**: build a maximal fan, find maximal bicolored paths, perform the
specified interchanges/downshift, and strictly reduce the number of edges using
the extra color. Section 4 does the same for Theorem 1.3. Its monotone quantity is
`|M(f,1) intersection M(h,1)|`; the proof constructs a new coloring that strictly
increases it, repeats until the target color-1 matching agrees, and then invokes
the constructive subcubic result on the remaining graph. Section 4 finally
regularizes a non-regular graph by the displayed double-copy construction and
projects the interchanges back.

For fixed maximum degree 4, every primitive operation in these proofs is a graph
scan for a maximal two-colored component plus constant-size fan/case work. The
agreement count increases at most `|E|` times. Thus the proof gives a direct
polynomial sequence-construction route (a straightforward implementation of the
Section 4 phase is `O(|E|^2)` edge inspections), even though the authors do not
state a tuned running-time bound. This rules out presenting the paper's theorem
regime as Track A. More importantly, the paper contains no average-case theorem
for endpoint colorings obtained by a random walk in the Kempe graph.

## Mechanical cost versus compact route

The prior-triage proposal has two possible versions, and neither is Track B.

1. **Expose enough of the planted trace to recover it.** Representing a move by
   `(color_a, color_b, representative_edge)` takes three atomic answer elements.
   The 256-atom cap therefore permits at most 85 moves (`255` atoms). Producing
   the certificate from an exposed trace is exactly `85` record reads/copies;
   the alleged compact route is the same `85` reversals. A local CPython
   microbenchmark of one million reversals of an 85-record trace took
   `1.620539` seconds, or **1.621 microseconds per certificate**. The
   mechanical/compact operation ratio is **1**. Any more explicit clue merely
   turns those same records into a transcription task.

2. **Hide the planted trace and reveal only the graph and endpoint colorings.**
   Reversal is then unavailable to the solver. The generic bounded method is
   search in the Kempe reconfiguration graph, while the paper's unbounded
   constructive method repeatedly performs the maximal-component/fan scans
   described above. The paper provides no invariant, symmetry, change of
   variables, or compressed program from which the particular planted short
   sequence can be reconstructed in at most 300 operations. In other words,
   this version has no compact route at all; the generator's private random
   choices are not an insight a solver can discover.

At a representative 256-edge endpoint instance, the direct Section 4 scan
accounting is on the order of `256^2 = 65,536` edge inspections, but that number
does not rescue Track B: the proposed 85-step shortcut is available only from
private generation history. If the history is made public enough to use, both
certificate production routes collapse to the same 85-copy operation above and
an in-context trace-reversal attack succeeds by construction.

This is the required mechanical-versus-compact comparison. The rejection is not
the bare statement that an efficient algorithm exists. It is that the only
paper-native algorithm is the mechanical constructive proof, whereas the only
shorter proposed route is either identical to copying an exposed answer or is
hidden information rather than structure in the instance.

## Other candidate tasks

| Candidate | Gate that fails | Reason |
|---|---|---|
| Return the reverse of a sampled interchange walk | **H, Track A** | No distributional hardness theorem; the paper instead gives constructive reachability in the exact degree/color regime. |
| Treat the retained private walk as the Track B shortcut | **H, Track B** | A private seed/history is not available to the solver and is not a compact route. |
| Publish trace clues so reversal is available | **H, Track B / G6** | Mechanical and compact costs are both 85 record copies at the largest writable witness, and the obvious in-context reversal attack succeeds. |
| Run the Section 4 proof and ask for its sequence | **H, Track A and B** | The certificate is the output of the constructive maximal-path/fan procedure; no shorter solver-visible representation is supplied. |
| Ask for a shortest interchange sequence | **G / paper support** | The paper proves reachability, not a shortest-sequence theorem, optimum certificate, or answer-first hard distribution. |
| Generalize Figure 1 and certify non-reachability | **H** | The displayed perfect-matching partition invariant is the direct certificate-producing classification for that fixed obstruction; copying disjoint relabelled copies adds length, not difficulty. |
| Encode SAT, finite-field algebra, or a hidden arithmetic root into edge labels | **domain essentiality** | Such hardness would come from a convenience surrogate absent from the paper, not from its edge-coloring mathematics. |

## Gate diagnosis

| Requirement | Result |
|---|---|
| G — answer known without solving | Passes in isolation by retaining and reversing sampled legal interchanges. |
| V — cheap exact witness checking | Passes in isolation by exact component recomputation and sequence replay. |
| H — Track A | **Fails:** no theorem supports hardness of the random-walk distribution, and Sections 3–4 are constructive in the stated regime. |
| H — Track B | **Fails:** exposed history gives 85 mechanical operations versus the same 85-operation “shortcut”; hidden history gives no solver-visible compact route. |
| Overall | **Rejected at Step 0.** |

The source was read in full, including the definitions in Section 1, all three
preliminary lemmas in Section 2, the explicit algorithm in Section 3, the full
case analysis and regularization in Section 4, and the induction in Section 5.
