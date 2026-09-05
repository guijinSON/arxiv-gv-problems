# Rejected: arXiv:2408.03727

**Decision:** reject the built family because **H fails on Track B**. Generation
(G) and exact verification (V) pass. The failure is empirical and terminal under
the prescribed hardening protocol: an oracle produced a verified witness at the
final `hard` preset after the one permitted retune.

## Paper result and candidate family

The paper's Definition 1.1 defines a cooperative coloring of hypergraphs on a
common vertex set as a partition \(I_1,\ldots,I_m\) with \(I_i\) independent in
\(H_i\). Theorem 2.1 and Corollary 2.2 (Section 2) give a constructive positive
result for two tight or loose \(k\)-uniform paths/cycles when \(k\geq 3\). That
result makes those objects an easy constructive family, not a Track A family.
Section 4 defines chain-structured systems and highlights 2-edges as the boundary
not covered by the Section 2 result.

The retained generator builds two succinct 2-uniform chain-structured cycles on
\(2^n\) vertices. Their cyclic orders are binary-reflected Gray orders transformed
by reversible linear circuits over GF(2). The answer is an affine parity formula
`{"mask": ..., "offset": ...}` whose two color classes form a cooperative
coloring. Generation transports the known alternating Gray-cycle coloring through
a sampled invertible circuit, so it never solves the generated instance. The
checker composes the circuits exactly over GF(2) and symbolically checks both
cycle-independence conditions without enumerating the vertices or reading the
planted answer.

This is a native use of the paper's Section 4 objects, but it is not guaranteed by
Theorem 2.1: both generated hypergraphs consist entirely of 2-edges.

## Why the Track B attempt was initially plausible

An efficient algorithm is known and was disclosed from the start. The **mechanical
route** compiles the circuits to binary matrices, powers the repeated round, and
uses Gaussian elimination over GF(2). Its complexity is
\(O(n^3\log E+nL)\), where \(E\) is the repetition count and \(L\) is the outer
circuit length. At the final preset
`n=40, outer_steps=299, round_steps=128, repeat_bits=32`, eight runs solved 8/8
with a mean of **1,527,193.625 counted bit operations** and **0.008996 seconds**
(maximum 0.009972 seconds) on this machine. The independently measured seed
314159 baseline used 1,490,869 bit operations.

The intended **compact route** notices that every repeated `FANOUT2`/`SWAP` round
preserves total bit parity, discards those repetitions, and transports one parity
mask through the 299 outer gates. It therefore costs **299 exact mask updates**,
while explicit expansion would expose \(2^{40}\) vertices. That mechanical/compact
gap is large enough to justify trying Track B; the existence of the polynomial-time
algorithm is not the rejection reason.

Local gates also supported the attempt: all 16 planted checks passed; the exact
certificate density was \(2^{-40}\) (0 hits in 200,000 structure-aware samples);
five construction-aware attacks each scored 0/8; and all 60 canonical-key
relabeling checks passed. The answer is 32 characters, 13 estimated tokens, and
two atomic elements.

## Decisive failure

The final bare hardening run sampled seed **321217416** at the `hard` preset.
`x-ai/grok-4.6` identified the parity invariant, carried the mask through the
outer circuit, and returned
`{"mask":122376207298,"offset":0}`. `parse_answer` succeeded and `verify`
returned `(True, "ok")`; the call took **733.36 seconds**. Since one successful
oracle defeats a level, the run stops at that point and the distribution fails
the required Track B hardness test.

This followed the only permitted retune: the earlier 30-bit hard rung did not
survive the hinted diagnostic, so the ladder was moved once to the present 40-bit,
299-operation rung and both required tests were rerun. Retrying or lengthening the
outer circuit beyond the 300-operation no-tool cap would be tuning past the
verdict, not evidence of hardness. A final hinted run happened to hold 0/3, but
that does not rescue a bare distribution that a sampled oracle solved. The placebo
arm was not purchased after the terminal bare failure.

`llm_loop_transcript.jsonl` is the authoritative final bare evidence. The root
`.meta.json` still contains the prior completed 30-bit verdict because the harness
stopped the final singleton run as soon as it found the solution and did not
replace that old metadata; it has deliberately not been edited by hand.

## Other paper routes considered

- A generic planted cooperative-coloring CSP would have no paper-backed hardness
  claim for the generated distribution. Solving after the structural observation
  would also require far more than 300 operations, so it would test unaided search
  or bookkeeping rather than a compact paper insight.
- Theorem 3.2's lower-bound construction concerns nonexistence in multipartite
  hypergraphs, but its proof does not supply a bounded, cheaply executable negative
  certificate for each generated instance. Its upper-bound proof is probabilistic
  and does not by itself hand construction a witness without search.

The implementation is retained as `rejected_gen_2408_03727.py`, as required, so
the decision can be reproduced or revisited under a different evaluation regime.

