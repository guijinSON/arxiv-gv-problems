# Rejected: arXiv 2601.05272

Paper: Erik Mårtensson, Paul Stankovski Wagner, and Joshua Stapleton,
[*A Rank 23 Algorithm for Multiplying 3 x 3 Matrices with an Arithmetic
Complexity of 59*](https://arxiv.org/abs/2601.05272), arXiv:2601.05272v1
(18 December 2025).

## Decision

No generator is shipped. I read the complete six-page paper and its LaTeX
source, audited both hardness tracks, built the strongest defensible Track B
family, and ran the required four-vendor hardening loop. The result was
`too_easy` after all three permitted escalations. Valid answers were recovered
at every rung, so **H fails empirically on Track B**. Track A is unavailable
because the paper proves no computational or distributional hardness theorem.

The failed module was removed rather than left looking shippable. The harness-
owned `llm_loop_transcript.jsonl` and `.meta.json` are retained as evidence.
No `selftest_report.json` or G9 arms are claimed: the bare STEP 4 gate failed
before a shipping preset existed.

## Exact paper objects and the Step-0 audit

Section 1 fixes row-major coordinates `A_0,...,A_8`, `B_0,...,B_8`, and
`C_0,...,C_8` for `C=AB`. Table 1 gives 23 products

```text
M_r = (integer linear form in A) * (integer linear form in B)
```

and nine linear combinations of the `M_r` that recover `C`. Table 2 replaces
repeated subexpressions with `t`, `u`, and `v` registers and gives an executable
59-addition straight-line program. Appendix A (Table 3) encodes the same rank-23
decomposition as three `9 x 23` coefficient matrices over `{-1,0,1}`.

These are displayed constructions, not existence or hardness theorems. The
paper has no numbered theorem. Section 1 expressly defers the technical search
method, tools, and implications to a future publication. It says that
Stapleton's neural scheme generation was combined with Mårtensson--Stankovski
Wagner addition reduction; Table 2's caption says **Greedy Vanilla** reaches 59
additions and Greedy Potential gives no improvement.

For the one scheme actually published, the certificate-producing algorithm is
therefore lookup/transcription:

- Appendix A contains exactly `3*9*23 = 621` scalar coefficients: 165 nonzero,
  including 84 entries equal to `-1`.
- The natural compact nested-JSON rendering is 1,387 characters but 621 atomic
  elements. A signed sparse-support format can fit under 256 elements, but it
  remains the same lookup task.
- Table 2 contains exactly 59 binary additions/subtractions.

| fixed native task | mechanical cost | compact route | result |
|---|---:|---:|---|
| emit the rank-23 decomposition | copy 621 displayed coefficients | copy the same 621 coefficients | 1:1, no insight |
| emit the optimized schedule | copy/rename 59 displayed gates | the same 59 gates must be written | 1:1, no insight |
| report the arithmetic complexity | one lookup of `59` | the same one lookup | tiny answer space |

Thus the fixed paper object fails H on both tracks: Track A has no applicable
hardness result, and Track B has no mechanical/compact gap. Renaming inputs,
changing signs, permuting the 23 products, or applying a basis-equivalent map
does not create diversity: G8 must canonicalize those transformations to the
same tensor problem.

## The prior-triage tensor proposal

The suggested inverse generator was to sample a hidden rank-one bilinear
decomposition and form its tensor. This establishes G and V for an arbitrary
planted tensor, but the paper studies the fixed `3 x 3` multiplication tensor
and proves nothing about recovering random planted decompositions. Calling that
new distribution Track A would be unsupported; replacing multiplication by a
generic tensor would also discard the paper's defining object.

A more faithful missing-column variant does not help:

- If the other 22 columns keep their paper labels, the task is set difference
  among 23 labels followed by copying 27 coefficients.
- Without labels, direct dense coefficient subtraction costs at most
  `729*22*(2 multiplications + 1 subtraction) = 48,114` exact operations.
  Even restricting work to the 25 entries on three pivot fibres costs about
  `25*22*3 = 1,650` operations before normalization, over G9's 300-operation
  intended-route cap. On the paper's actual sparse table, support matching is
  easier still.
- Tensoring the scheme with itself gives 529 terms in 81-dimensional factor
  spaces. A dense missing term has 243 entries, but recovering its pivot fibres
  from 528 terms costs hundreds of thousands of exact operations. A short macro
  such as “tensor the published scheme with itself” works only if the statement
  supplies the fixed scheme as a template, in which case the requested macro is
  immediate and H fails.

Hiding a random basis or an expansion history merely adds a new equivalence or
obfuscation problem for which this paper supplies no theorem. Asking for fewer
than 59 additions also fails the witness rule: the paper claims a record, not
optimality, and gives no executable lower-bound certificate.

## Track B family that was actually built

I did not stop at “an algorithm exists.” The paper's native optimization object
is a collection of expanded integer linear forms plus a shared-addition
straight-line program (Table 1 to Table 2). I therefore built an inverse-
generated family of exactly those objects:

1. Sample a balanced binary interval tree and independent input signs.
2. Make every internal register a requested expanded integer linear form.
3. Shuffle target names; retain the tree as the certificate.
4. Ask for one binary addition/subtraction per target. Verify by expanding every
   submitted gate coefficientwise over the integers, without reading the plant.

This passed the local construction and verifier checks. The bounded answer used
three integers per gate. At `n=64` it had 63 gates, 189 atomic elements, and 738
characters for the measured seed. A doubled `n=128` instance still built and
verified. The canonical key was the unordered tree shape and was invariant
under input and target permutations and independent sign changes.

The structure-aware candidate space at `n=64`, seed 424242, had

```text
720730441099481238634833569669998561948514805350400000000
```

candidates after enforcing proper containment, disjoint operand supports,
topological gate order, and canonical commutative order. Sampling 200,000 such
candidates produced 0 valid answers.

### Mechanical and compact costs

The disclosed reference algorithm was an exact contained pair-sum/subset-DAG
scan: for each target, enumerate proper contained disjoint forms and compare
their coefficientwise sum. Its complexity is `O(n^3)` coefficient inspections
plus candidate-pair tests.

At the proposed shipping rung `n=64`, across eight deterministic seeds:

- reference algorithm: 8/8 solved as expected;
- maximum measured scalar-operation count: **842,204**;
- total measured scalar operations: **6,212,670**;
- measured wall clock for all eight: **0.174715 s** on this runner.

The compact route noticed that supports are a laminar family of intervals and
used each interval's two maximal proper subintervals. At `n=64`, seed 424242,
it used **63 exact additions** plus **260 endpoint probes**, verified exactly,
and stayed within every G9(c) cap. This is a genuine Track B mechanical/compact
gap, not the reason for rejection.

Five construction-aware attacks nevertheless failed 0/8 as intended:

| attack | successes |
|---|---:|
| smallest-support outlier rule | 0/8 |
| most-balanced greedy pair | 0/8 |
| left-to-right register pairing | 0/8 |
| obvious chain ansatz | 0/8 |
| 256 structure-aware random restarts | 0/8 |

The four-vendor oracle pool exposed what those heuristics missed: current models
can recognize and execute the laminar decomposition directly.

## Required hardening-loop result

The bare, no-hint harness ran the complete ladder and the sole permitted
post-ladder escalation. A level is defeated when any oracle solves it; here
every level had at least one exact verifier success.

| round | preset / parameters | exact solves | result |
|---:|---|---:|---|
| 0 | `easy`, `n=64` | 2/3 (Grok, Claude) | defeated |
| 1 | `medium`, `n=72` | 2/3 (Gemini, Claude) | defeated |
| 2 | `hard`, `n=80` | 2/3 (Claude, Grok) | defeated |
| 3 | escalated, `n=84` | 1/3 (Grok) | defeated; `escalate()` then returned `None` |

The successful rows had `parsed=true`, `verify_ok=true`, and reason `ok`; they
were not output-contract false negatives. OpenAI also produced malformed or
dependency-invalid programs on some attempts, while other vendors solved the
same levels. The harness metadata records:

```text
verdict: too_easy
escalations_used: 3
reason: escalate() returned None -- the family cannot be made harder,
        and the oracle pool still solves it
```

No hinted or placebo arm was run because G9 is reached only after a bare level
holds. The family already failed the weaker bare requirement.

## Final gate outcome

| requirement | outcome | evidence |
|---|---:|---|
| G -- construct while holding a witness | pass for the attempted family | hidden signed addition tree is sampled first |
| H -- Track A | **fail** | the paper gives no theorem or hard parameter regime for a planted distribution |
| H -- Track B, fixed paper scheme | **fail** | 621 vs 621 coefficients or 59 vs 59 gates |
| H -- Track B, inverse-generated addition family | **fail** | bare oracle pool solved every rung through `n=84`; final verdict `too_easy` |
| V -- exact cheap verification | pass | expand integer coefficient vectors and compare exactly |
| G4 local guess resistance | pass diagnostically | 0/200,000 in the structure-aware prior at `n=64` |
| G6 local heuristic panel | pass diagnostically | all five attacks 0/8; reference algorithm 8/8 as Track B requires |
| G9 | not reached | no bare preset held, so there is no shipping level to hint-test |

The prior triage correctly identified inverse construction and exact tensor
verification as routes through G and V. Full-paper review and the required live
test show why that is not enough for H: the published object is a fixed lookup,
and the strongest native scalable Track B formulation was reliably solved by
the oracle pool.
