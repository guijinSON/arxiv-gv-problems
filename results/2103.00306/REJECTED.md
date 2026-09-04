# Rejected after G9(b): arXiv:2103.00306

Track considered: **B (no-tool compression)**. The retained generator is
`rejected_gen_2103_00306.py`; it is not a shippable family.

## What the paper actually says

Section 1 defines an odd-vertex pairing and cut-admissibility by
`d_G(X)-d_F(X) >= R_G(X)` for every vertex set `X`. Theorems 2 and 3 prove
co-NP-completeness of checking cut- and orientation-admissibility. Their
parameter regime comes from the even-edge, even-degree AMAXCUT problem in
Section 2.1 and the reduction in Sections 3.1--3.5, especially Lemma 4's
constant-boundary-minus-cut identity. Section 4 and Theorem 4 prove only
worst-case NP-completeness for arbitrary local arc-connectivity requirements;
they do not make an orientation sampled first and encoded into its own
requirements hard. That prior-triage orientation proposal therefore could not
support Track A.

## The attempted native family

The retained module inverse-generates a balanced 3-XOR assignment, represents
each parity row twice by an exact six-vertex `K6`-minus-one-edge MAXCUT gadget,
and carries the known extremal cut into an odd-pairing violation using a
low-degree channel version of the paper's Section 3 identity. The certificate
is a 24-index symbolic assignment that expands deterministically to a concrete
cut of the actual multigraph. Exact cut counting verifies it. G and V pass:
G1--G8 all passed, the shipping language has exactly one valid answer among
`C(48,24) = 32,247,603,683,100`, and 200,000 structure-aware guesses had zero
hits.

The family is not a Track-A claim. Its certificate is produced mechanically by
GF(2) Gaussian elimination on the repeated 3-XOR rows, in
`O(r n^2)` bit operations. At the shipping preset (`n=48`, 56 base rows, 112
displayed occurrences, 256-bit tags), this reference algorithm solved 8/8 in a
median **42,635 counted bit operations** and **0.000299 seconds**. The compact
route evaluates one masked parity per variable: one word AND plus one parity,
or **96 exact word operations**. This is a real mechanical/compact gap and is
why the family was tested on Track B rather than rejected merely because an
efficient algorithm exists.

## Failing gate and measured evidence

The family fails **H for Track B via the mandatory G9(b) polarity-flipped
gate**. The bare shipping prompt hardened 0/3 solved, and the placebo arm also
hardened 0/3. With the one-sentence structural hint—"The variable tags carry a
linear invariant tied to the public audit mask."—the pool solved 1/3. The hint
names only the invariant; it contains no chained step, formula, derived count,
or output instruction.

The rules permit one move upward. At the next rung the answer and compact route
were unchanged (`n=48`, 56 base rows, 320-bit tags; 24 answer elements and 96
word operations), but the hinted pool again solved 1/3. Thus the structural
hint breaks both the shipping level and the single allowed harder rerun. The
measured hinted-minus-placebo success difference at shipping is **1/3**. More
hint-driven escalation would tune past the stipulated verdict, so it was not
performed.

Evidence is retained in:

- `llm_loop_transcript.jsonl`: bare ladder; hard held 0/3.
- `g9_hinted_transcript.jsonl`: 1/3 solved at 256 bits and 1/3 at 320 bits.
- `g9_placebo_transcript.jsonl`: 0/3 solved at 256 bits.
- `selftest_report.json`: G1--G8 pass and G9 fails, with all measurements.
- `budget_bound_bipartite_transcript.jsonl`: an earlier, discarded construction
  whose polynomial BFS shortcut was solved across the ladder; retained to make
  the redesign auditable.

This is not a `cap_bound` rejection: the answer is only 71 characters / 24
atomic elements and the intended route is 96 operations. It is also not a false
Track-A rejection based on the existence of Gaussian elimination. The specific
reason is the twice-confirmed G9(b) failure on Track B.
