# Rejected: arXiv 2304.13478

Paper: Andreas Klingler, Tim Netzer, and Gemma De les Coves, “Border Ranks of
Positive and Invariant Tensor Decompositions: Applications to Correlations”
([arXiv:2304.13478v3](https://arxiv.org/abs/2304.13478)).

## Decision

No problem generator is shipped because no witness-search family supported by
this paper can be justified as satisfying gate **H (hard)**. This is a Step 0
rejection, before the module, self-tests, or LLM hardening loop. Consequently,
there is deliberately no `gen_2304_13478.py`, `selftest_report.json`, or
`llm_loop_transcript.jsonl`.

## What the paper actually proves

Section 2 and Appendix A define standard, cyclic, tree, symmetric, and
translationally invariant tensor decompositions, with unconstrained,
entrywise-nonnegative, positive-semidefinite, separable, and purification
variants. Section 3 studies a topological question: whether rank can exceed
border rank. It establishes its results using explicit tensors and explicit
degenerating families:

- Section 3.1 uses the explicitly defined `W_n` tensor. Its ordinary rank is
  proved to be `n` (Appendix B.1), while an explicit two-term family converges
  to it. Explicit PSD matrices also give a border-PSD-rank upper bound.
- Sections 3.2 and 3.3 use the explicit two-domain tensor and `W_n` again for
  cyclic and translationally invariant decompositions.
- Section 3.5 and Appendices G–H prove absence of border-rank gaps for standard
  nonnegative/separable decompositions and for tree tensor networks.
- Section 4 and Appendices E–F prove correspondences between bounded positive
  ranks and classical/quantum correlation sets, then infer non-closedness.

The sentence that membership is “impossible to test ... with a finite number
of measurements” in Section 4.1 is an information/topology statement: a limit
distribution outside a non-closed correlation set is arbitrarily close to
members of it. It is not a computational lower bound for exact decomposition
recovery from a fully specified tensor.

The paper contains no NP-hardness, search-hardness, FPT lower-bound, or other
complexity theorem for finding a decomposition of a promised decomposable
tensor. The one bibliography item whose title mentions NP-hardness and
undecidability is cited in the introduction for global positivity limitations;
none of that referenced paper's hardness reductions is stated or used here to
define a planted witness-search family.

## Why the triaged generator does not meet G/H/V

The proposed inverse construction was: sample nonnegative invariant factors,
sum their tensor products, and ask the solver to recover factors.

| Requirement | Assessment | Reason |
|---|---|---|
| G — generatable | possible | Sampling rational factors first gives a known decomposition. |
| H — hard | **fails** | The paper proves no hardness for recovering planted factors. A rank/border-rank separation does not imply recovery hardness, and arbitrary inverse-generated tensors are not in the paper's lower-bound examples. Generic low-rank tensor decompositions may also expose their factors through ordinary algebraic/linear-algebraic recovery, so hardness cannot be inferred from a large raw coefficient space. |
| V — verifiable | possible only after restriction | A rational nonnegative decomposition can be expanded and compared exactly. General PSD/quantum decompositions use real or complex entries and do not automatically provide the bounded exact textual witness required by this task. |

The explicit `W_n` construction cannot repair H: its support itself reveals the
standard `n`-term decomposition, and the paper prints the low-border-rank
families. Randomly changing basis is not allowed for the nonnegative problem in
general and, where allowed, would merely hide an explicit answer behind an
invertible relabelling rather than establish hardness.

## Why nearby formulations are disallowed

- Asking for the rank or minimum bond dimension makes the answer an optimum,
  whose optimality is the claim rather than a cheaply checked witness.
- Asking a solver to certify that no rank-`r` decomposition exists asks for an
  absence, which the task expressly forbids.
- Asking for a border-rank witness naturally requires a convergent family or an
  asymptotic argument, not a fixed bounded witness that can be checked by finite
  exact substitution.
- Turning the paper's non-closed correlation-set result into a finite-sample
  membership task would contradict requirement V rather than satisfy it.

Because H fails at paper triage, running `scripts/harden.py` would not cure the
missing mathematical justification and would risk mistaking oracle failures for
evidence of computational hardness.
