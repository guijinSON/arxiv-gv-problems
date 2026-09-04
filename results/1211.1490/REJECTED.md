# Rejected: arXiv:1211.1490

## Decision

This build is rejected because **H fails on Track B at G9(b)**. G and V pass:
instances are inverse-generated from a sampled selector, and the checker reconstructs
the paper's rational unit-circle polygon and verifies convexity, exact containment,
and every segment endpoint condition using `Fraction`. Track A is unavailable because
the generated distribution has a polynomial-time decoding algorithm.

The relevant source is Section 5, Theorem 1 of [*New results on stabbing segments
with a polygon*](https://arxiv.org/abs/1211.1490), together with Appendix A's exact
rational point construction. Theorem 2
identifies the polynomial pairwise-disjoint regime, and Observation 1 gives the
`O(2^k P(n))` FPT algorithm in the number of crossing segments. This generator stays
in the crossing regime and instantiates the proof's tight pattern: one of `T_i,F_i`
per variable and two of `p_j1,p_j2,p_j3` per clause.

## The required algorithm/cost comparison

The generated 3-CNF connector gadgets come in four-clause blocks encoding ternary
XOR equations. The mechanical polynomial method is block decoding followed by dense
Gaussian elimination over GF(2), complexity `O(n^3)`. At the attempted shipping
preset `n=89`, it solved 8/8 local instances and used a median **15,039 exact XOR
operations**, **8,916 pivot tests**, and **0.001882 seconds**.

The compact route reconstructs the cycle of two-variable overlaps and evaluates its
second-order GF(2) recurrence. It solved 8/8 and used a median **280 exact XORs**;
the measured maximum was **291 XORs**, within G9(c)'s 300-operation limit. Thus the
mechanical and compact costs are not comparable—the gap is real and originally made
this a legitimate Track B candidate. It is rejected because the hinted oracle
actually executed the compact insight, not because an efficient algorithm merely
exists.

## G9(b) evidence

The structural hint was deliberately only an invariant, not a procedure:

> Each four-clause block on the same variable triple is the CNF truth table of one
> ternary parity constraint.

At `n=77`, the bare pool hardened the family (0/3 solves at that rung), but the hinted
pool solved 1/3: Grok's answer parsed and verified exactly. The protocol permits one
move upward. A fresh bare run at the predeclared hard rung `n=89` hardened (0/3
counted solves; one separate Grok request timed out and was recorded as an error).
The fresh hinted run at `n=89` again solved 1/3: Grok returned a selector for seed
`1465035141` and `verify` returned `(True, "ok")`. OpenAI and Google returned parsed
but invalid selectors.

Because the structural hint breaks both the original shipping rung and the one
allowed higher rung, G9(b) says to reject and stop. The restricted hinted harness then
reported `cap_bound` because its scratch-copy `escalate()` was intentionally disabled;
that generic post-level diagnosis does not erase the preceding verified `SOLVED` record
at the shipping rung, which is the G9(b) event. No placebo run was purchased after
the gated failure; the placebo arm cannot reverse G9(b), and fabricating it would be
worse than leaving it explicitly unmeasured.

One bare-hard Anthropic call returned an empty length-limited response and the harness
classified it as `failed`; that makes the bare-hard evidence weaker than three parsed
wrong answers. The G9 rejection does not depend on that row: the hinted-hard transcript
has three completed parsed responses, including the exactly verified solve.

## Preserved artifacts

The completed implementation is retained as `rejected_gen_1211_1490.py`. The hard
bare transcript remains `llm_loop_transcript.jsonl`; the hard hinted transcript is
`g9_hinted_transcript.jsonl`; the earlier medium calibration transcripts are retained
under descriptive names. `selftest_report.json` records the local gates and the G9
failure rather than claiming `all_passed`.
