# Rejection: arXiv 2511.20771

Paper: Sebastian Bruchhold and Mathias Weller, [*Exploiting Low Scanwidth to
Resolve Soft Polytomies*](https://arxiv.org/abs/2511.20771), v3 (2026).

## Decision

The proposed planted-embedding family passes **G** and **V**, but fails **H on
Track A**. I also considered the required **Track B** rescue; for the natural
plant, the mechanical certificate-producing algorithm and the compact route
are the same linear tree-matching computation, so their measured operation
counts are comparable. There is no no-tool compression gap to benchmark.

This is a Step-0 rejection. No generator was written, so there is no
`rejected_gen_2511_20771.py` to retain and no oracle run to perform.

## What the paper actually defines

Definition 5 says that a network softly displays a tree when binary resolutions
of the two objects admit a leaf-respecting subdivision embedding. Problem 1 is
the corresponding decision problem. For binary networks, Definition 9 gives a
finite witness in the paper's own objects: a **soft pseudo-embedding** mapping
every tree arc to a directed network path, subject to exact endpoint,
arc-disjointness, eventual-arc-disjointness, and leaf-label conditions. Lemma 1
proves that this witness is equivalent to soft display.

Thus the prior-triage proposal is sound with respect to two gates:

- **G passes in principle:** sample a resolved tree and its leaf-respecting path
  map first, construct a network containing those paths, and only then add arcs
  or resolution gadgets while carrying the map forward.
- **V passes in principle:** check every listed path against the network arcs,
  then check SPE1--SPE4 from Definition 9. This is exact finite graph work and
  never needs to solve another containment instance.

## The certificate-producing algorithm (the Step-0 question)

The paper answers this explicitly. Algorithm 1 exhaustively propagates valid
signatures along a supplied tree extension. Proposition 1 bounds its binary
network running time by

```text
O*(2^(Delta_T (sw(Gamma)+1) log2(4 sw(Gamma)+4))).
```

The paragraph immediately after Proposition 1 (Section 4.1) explains how to
store predecessor signatures and backtrace a full soft pseudo-embedding.
Theorem 1 extends the decision algorithm to arbitrary networks, with
`k = sw_N(Gamma) + Delta_N` and running time
`O*(2^O(Delta_T k log k))`.

The easy regimes cannot be ignored. Section 2 records polynomial algorithms
for constant-level binary networks, and Sections 3--4 make low supplied
scanwidth, bounded network out-degree, and bounded tree out-degree precisely
the tractable parameter regime of this paper. Consequently, a generator that
keeps these parameters small is not a Track-A family. Making `k` grow only
removes the FPT guarantee; it does not prove that a random planted distribution
is hard.

## Why Track A fails

The paper's NP-hardness statement in Section 1 is a worst-case result inherited
from earlier work. It says nothing about the distribution obtained by taking a
known tree embedding and adding random harmless arcs. On that distribution,
the plant must either remain structurally recognizable or become a generic
search problem:

1. If the plant remains recognizable enough to admit a sub-300-operation
   intended route, bottom-up descendant-leaf cluster hashes recover the same
   embedding directly. This is linear in the generated network and succeeds by
   construction, so the required domain attack would not have zero successes.
2. If enough unmarked reticulation noise is added to defeat cluster matching,
   neither the theorem nor its proof supplies a compact route through that
   noise. The only supported route is signature propagation/backtracking, whose
   cost is exactly what was made large. Such a family would fail G9(c), not
   establish structural insight.

Declaring Track A in the second case would substitute worst-case NP-hardness for
evidence about the generated distribution, which the task explicitly forbids.

## Why Track B does not rescue the natural plant

I counted the mechanical and compact routes before implementation, using the
largest direct pseudo-embedding that stays near the 256-atom answer cap.

For a rooted binary tree with 64 leaves there are 127 vertices and 126 arcs. A
path witness needs at least two vertex identifiers per tree arc, hence at least
252 atomic answer elements even when every path has length one. On a relabelled
planted copy, the standard bottom-up cluster matcher performs:

| operation | count |
|---|---:|
| inspect all arcs of both input objects | 252 |
| merge child signatures in both objects | 126 |
| look up the matching network signature | 63 |
| **mechanical total** | **441** |

The compact route is not shorter: it is the same 252 arc inspections, 126
merges, and 63 lookups, after which the solver must serialize the 252 witness
atoms. Therefore the mechanical cost is **441 primitive structural operations**
and the compact route is **441 operations plus transcription**. They are the
same order and essentially the same number, not the intended million-versus-a-
dozen Track-B gap.

At 32 leaves the comparison is equally unfavorable: the exact count is 124 arc
inspections + 62 merges + 31 lookups = **217 mechanical operations**, while the
compact route is that same **217-operation** cluster pass. Subdivision only
lengthens the witness. A switching-vector certificate shortens the output, but
on the planted construction each switch is recovered by the same local clade
comparison used by the checker, again eliminating the compression gap.

Padding the network with decoys does not repair this cleanly. A marker that lets
the compact route skip them also lets the linear matcher skip them; without a
marker, locating the plant is the search itself and no bounded compact route is
provided by the paper.

## Gate summary

| Gate | Result | Basis |
|---|---|---|
| G | pass in principle | inverse generation of a binary resolution and path map |
| H / Track A | **fail** | known linear recovery on the planted distribution; worst-case NP-hardness is insufficient |
| H / Track B | **fail** | 441 mechanical operations versus the same 441-operation compact route at the answer cap |
| V | pass in principle | executable SPE1--SPE4 checks from Definition 9 and Lemma 1 |
| G9(c) | blocks noisy alternatives | a full 64-leaf path witness already uses at least 252 of 256 atoms |

The rejected object is the prior-triage **planted embedding family**, not the
paper's mathematics. A future attempt could be reopened if it finds a native
network construction with (i) a carried soft pseudo-embedding, (ii) a tested
hard generated distribution, and (iii) a genuinely shorter structural route
than both Algorithm 1 and construction-aware cluster matching.
