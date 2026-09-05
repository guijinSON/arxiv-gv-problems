> Superseded during the 2026-09-05 rebuild. Retained verbatim for audit history;
> the shared-relabeling Track-B construction in `gen_2409_11328.py` addresses the
> missed compact-route case.

# Rejected: arXiv 2409.11328

Paper: Nina Chiarelli, Vesna Iršič, Marko Jakovac, William B. Kinnersley,
and Mirjana Mikalački, [*Burning game*](https://arxiv.org/abs/2409.11328),
arXiv:2409.11328v1.

## Decision

No family native to this paper simultaneously clears G, H, and V. The decisive
failure is **H on both tracks**. The natural unrestricted witness—a contingent
Burner or Staller strategy—also exceeds the witness and G9(c) limits. I stopped
at STEP 0, so no generator was written and there is no oracle transcript to
retain.

This is not a rejection merely because an algorithm or an explicit construction
exists. I checked the possible Track B interpretation first and quantified both
routes below. The paper-backed cases with compact certificates have no useful
mechanical/compact gap; the cases with a large mechanical game tree have no
bounded compact certificate supplied by the paper.

## Exact paper objects and certificate source

Section 1 defines the game on a finite simple graph. At the start of each round,
fire spreads from every burned vertex to all its unburned neighbors; the player
whose turn it is then selects one unburned vertex. Burner minimizes and Staller
maximizes the first round in which the whole graph is burned. A valid general
certificate for an upper bound is therefore a Burner policy for every legal
Staller history, not merely one favorable play sequence.

The full text gives four possible certificate-producing routes:

- Proposition 1 converts an *optimal burning sequence of* `G^2` into a
  non-adaptive Burner policy. It does not produce that sequence: obtaining it is
  an instance of ordinary graph burning, whose NP-completeness is recalled in
  Section 1.
- Section 2.2, Proposition 10 characterizes `b_g(G)=3`. A first move `v` works
  precisely when the displayed first- and second-neighborhood condition holds
  (together with the maximum-degree condition). Scanning all vertices produces
  such a witness in polynomial time.
- Section 4, Theorem 23 constructs path and cycle strategies recursively.
- Section 5, Theorem 29 writes down the hypercube strategy explicitly: Burner
  selects the all-zero vector in round 1 and the all-one vector in round 3.
  Propositions 28, 30, and 31 for products either reuse an optimal strategy on a
  factor or reuse a burning sequence of `G^2`; they do not furnish a new hard
  search certificate.

These statements also identify the easy regimes that a generator would have to
avoid. Proposition 9 characterizes game burning numbers 1 and 2 by degree;
Proposition 10 gives the polynomial test for 3; Proposition 11 equates ordinary
and game burning on diameter-at-most-two graphs; Theorems 23, 24, and 29 give
direct structured strategies for paths, cycles, and hypercubes.

## Why the unrestricted game-tree family fails

Suppose a contemplated instance has 64 vertices and is certified to finish by
round 12. Staller can have six turns, so a literal strategy audit has as many as

`64^6 = 68,719,476,736`

reply histories. Even the Burner portion of a policy tree can require
`1 + 64 + ... + 64^5 = 1,090,785,345` move entries. This is far beyond the
256-atom answer cap. Memoized minimax does not repair the witness: its generic
state space contains up to `2^64 = 18,446,744,073,709,551,616` burned sets, with
up to 64 legal selections per state. The verifier could inspect a fully written
tree linearly in its size, but that is neither a cheap practical witness nor a
writable answer.

Inverse-generating one favorable play is insufficient because Staller may choose
a different reply. Inverse-generating the whole policy merely constructs the
billion-entry object that violates G9(c). The paper supplies no bounded strategy
language or locally checkable compressed policy for general instances.

## Track A disposition

Track A is not supportable. The only complexity statement in the paper is the
Section 1 citation that **ordinary** graph burning is NP-complete. There is no
hardness theorem for computing the new game burning number, much less a theorem
for an inverse-planted distribution of game instances. Sampling a burning
sequence or strategy first and surrounding it with random graph structure would
clear G, but worst-case NP-completeness of ordinary burning says nothing about
that distribution. It would therefore repeat exactly the forbidden inference
from worst-case hardness to planted-instance hardness.

## Track B mechanical cost versus compact route

I evaluated every short paper-backed witness rather than dismissing it for being
algorithmic.

| candidate | contemplated size | mechanical cost | compact route | result |
|---|---:|---:|---:|---|
| Proposition 10, one three-round first move | `n=64` | at most `64^3 = 262,144` adjacency tests to scan all `v` | up to `64^2 = 4,096` adjacency tests to validate a guessed `v` | The compact route is the same neighborhood condition and is over the 300-operation cap. |
| Batched Proposition 10 witnesses | five 17-vertex graphs | `5*17^3 = 24,565` adjacency tests | `5*17^2 = 1,445` tests | Five components are the minimum needed for the naive answer space `17^5 = 1,419,857` to cross the `10^6` guess-resistance threshold; the compact route is still too long. |
| Theorem 29 hypercube | dimension `d=128` | write/complement 128 coordinates, `Theta(d)` | the same two displayed vectors, `Theta(d)` output work | Nothing has to be discovered; the theorem's construction is already the shortest algorithm. |
| Theorem 23 path | `n` path vertices | `Theta(sqrt(n))` recursively placed sources | the same recurrence, `Theta(sqrt(n))` | Mechanical and by-hand routes are the same, and fixed-size paths give no seed diversity beyond relabeling. |

The first two rows show why Proposition 10 is not a hidden Track B family. At a
size where one proposed first move can be checked within 300 pair inspections
(`n <= 17`), a single answer is guessed with probability at least `1/17`. Batching
enough independently relabeled graphs to reduce that probability below `10^-6`
raises the intended route to at least 1,445 inspections. A specially encoded
layer marker could make the planted vertex readable in a few steps, but then the
marker—not burning-game structure—produces the answer. Hiding that marker in an
unrelated algebraic or string puzzle would be a convenience reduction absent
from the paper and would not count as native coverage.

The latter two rows have the opposite problem. Their certificates are compact
and exactly verifiable, but the paper already gives the answer by a direct
recurrence or explicit formula. The compact route is no shorter than the
mechanical one: there is nothing left for a no-tool solver to notice. Randomly
renumbering a path or hypercube does not help: it creates isomorphic copies,
fails canonical diversity, and replaces the short route with adjacency-list
processing rather than mathematical insight.

Proposition 1 does not bridge the gap. On arbitrary `G`, its certificate must be
obtained by solving graph burning on `G^2`; on paths or hypercubes it collapses
to the direct formulas just measured. An inverse-planted `G^2` sequence would
again have no paper-backed distributional hardness result.

## Gate disposition

| requirement | disposition |
|---|---|
| G | Available only for the explicit easy families or for an unsupported inverse-planted distribution. |
| H, Track A | **Fail:** no distributional hardness result for the generated game family; ordinary-burning NP-completeness is only worst case. |
| H, Track B | **Fail:** short paper-backed certificates have comparable mechanical and compact routes; the general game tree has no compact route. |
| V | Possible for Proposition 10 and the explicit path/hypercube certificates; a general policy is exact to check only after writing an exponentially large object. |
| G9(c) | **Fail for the unrestricted policy:** over 256 atoms; the Proposition 10 batching needed for G4 exceeds 300 intended operations. |
| Overall | **Rejected at STEP 0; no module built.** |

## What could reopen the decision

A later result proving hardness for the game-burning decision/search problem on
a concrete generatable distribution, or a paper-native succinct strategy
language with an exact polynomial checker, would change this conclusion. So
would a genuinely structural Proposition 10 construction whose compact
identification route stays below 300 operations without exposing a planted
label and whose distribution defeats the standard scan/attack panel. None of
those ingredients appears in this paper.
