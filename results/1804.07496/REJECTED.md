# Rejection: arXiv:1804.07496

## Decision

The attempted family fails **H on both tracks**.  Its construction and checker
clear G and V, but it is not a defensible hard distribution.  The retained
prototype is therefore `rejected_gen_1804_07496.py`; it must not be emitted as a
shipping generator.

This decision comes from the full paper, not its abstract.  Section 1 defines
Steiner Orientation as choosing a direction for every undirected edge of a
mixed graph so that every ordered terminal pair has a directed path.  Theorem 1
and Section 2 prove worst-case NP-completeness for planar mixed graphs by a
reduction from Planar Monotone 3-SAT.  The same section's Figure 1(a) proves the
flip identity used by the prototype, and the variable/edge-gadget lemmas state
that a flip forces opposite outer directions while two stacked flips force
equal outer directions.

## Step-0 triage and the certificate algorithm

The paper itself identifies the easy regimes in Section 1: the all-undirected
case has a polynomial-time algorithm, the case of two terminal pairs has an
efficient algorithm, and the general problem has an `n^{O(k)}` XP algorithm in
the number `k` of terminal pairs.  Theorem 1 is only a worst-case result; it
does not make an inverse-planted distribution hard.

The attempted generator samples an answer first, wraps each undirected edge in
an external GF(2) tag, and composes the paper's flip identities.  Its witness is
a JSON-native coefficient vector.  The checker expands that vector to a full
orientation and performs exact directed reachability, without reading the
planted answer.  Thus G and V pass by inverse generation and executable graph
verification.

However, the certificate is produced by generic GF(2) Gauss-Jordan
elimination.  At the candidate shipping size `n=96`, the measured mechanical
cost was 83,678 packed-row-equivalent bit operations and 0.00115 seconds for
seed 314159; over the eight adversary seeds the maximum was 119,459 operations
and all 8/8 were solved.  The compact route notices that the rows are the
complements of the coordinate basis and takes 288 counted inspections/XORs.
Those numbers justified trying **Track B**—the family is not rejected merely
because a polynomial-time algorithm exists—but the oracle evidence below shows
that the shortcut is too exposed to create no-tool difficulty.

## Why neither hardness track survives

- **Track A fails:** the generated complement-basis distribution is in P, and
  the paper supplies no average-case or distributional theorem for it.  Citing
  Theorem 1 would confuse worst-case NP-completeness with hardness of this
  planted distribution.
- **Track B fails:** in the official bare hardening transcript, valid calls
  solved 3/3 `easy` instances (`n=48`), 3/3 `medium` instances (`n=72`), and
  2/3 `hard` instances (`n=96`).  After the named ladder was exhausted, a
  model also solved 1 of the 2 valid calls at `n=96, copies=2`.  The other
  escalated call failed; four later calls were HTTP 403 quota errors and are
  not counted either way.

The fourth result matters because `copies=2` only duplicates each equation.
It increases prompt length and generic elimination work but adds no information
and does not lengthen the 288-operation compact route.  Further copy-based
escalation would therefore grow transcription/context burden rather than the
mathematical haystack.  Raising `n` can reach only 100 before the compact route
hits the required 300-operation cap, and the answer is already 192 atomic
elements at `n=96`.  There is no honest remaining axis on this construction.

The harness did not write a final `too_easy` verdict because the OpenRouter
account reached its total limit mid-run.  This is not being treated as oracle
failure: the eleven completed calls are preserved in
`llm_loop_transcript.jsonl`, and the solved calls already refute every tested
rung, including the permitted fixed-answer-length escalation.

## Scope correction

The prototype is also not native coverage of the paper.  Section 2 licenses
the flip-gadget identities, but the paper does not introduce GF(2)-tagged edges,
a redundant linear-system synopsis, or a restriction to orientations induced
by a symbolic key.  Those are a benchmark-convenience wrapper.  The retained
module now declares `native_domain="algebra"`,
`computational_core="linear_algebra"`,
`domain_essentiality="discretised_analogue"`, and
`reduction_kind="convenience"` so a later audit cannot mistake it for native
Planar Steiner Orientation coverage.

An unrestricted orientation family made only from the paper's flip identities
does not rescue the attempt: its constraints are pairwise parity relations, so
component propagation produces an orientation in linear time and the compact
route is no shorter than that mechanical method.  A future attempt would need
to implement the paper's full Planar Monotone 3-SAT reduction on a separately
justified hard generated distribution; neither Theorem 1 nor simple planting
provides that missing distributional claim.
