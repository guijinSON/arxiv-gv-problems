# Rejection: *Algebraic capsets* (arXiv:2602.05254)

**Decision:** reject at Step 0. The paper supplies explicit algebraic constructions
of capsets, but no problem family in the paper simultaneously satisfies G
(inverse-generatable), H (no known polynomial-time or closed-form solution), and V
(cheap exact witness verification). In particular, the paper contains no hardness
theorem or hard parameter regime on which a generator could honestly rely.

Paper: Cassie Grace and Jose Felipe Voloch, [*Algebraic capsets*](https://arxiv.org/abs/2602.05254).

## What the full paper actually establishes

Section 1 defines a capset as a subset of `F_3^n` containing no three distinct
collinear points. It defines a *complete* capset as an inclusion-maximal capset,
not a maximum-cardinality capset. It also distinguishes a cap over `F_q` from a
capset after identifying `F_q^d` with `F_3^(dm)`; completeness as a cap does not
in general imply completeness as a capset.

Section 2 then provides constructions rather than hard search problems:

| Result | Consequence for a proposed witness task |
|---|---|
| Theorem 2.1 | For `q = 3^m`, the union of the two explicitly given parabolas `(x,x^2)` and `(x,-x^2)`, with `x != 0`, is a capset; it is complete when `m` is odd. Asking a solver to find it is solved by the displayed formula. |
| Corollary 2.2 | Gives explicit complete capsets of size `O(sqrt(3^n))` for every `n`, including a product construction in odd dimension. Thus “find a complete capset” has a construction supplied by the paper. |
| Lemmas 2.3-2.4 and Tables 1-2 | Discuss quadratic-character conditions for unions of more parabolas and report finite computations. The paper finds examples only in bounded tested cases (one coefficient orbit for even `m <= 20`, and tabulated constructions through `m = 14`); it neither proves existence for an unlimited growing regime nor proves hardness of finding the coefficients. |
| Theorem 2.6 | The elliptic paraboloid `(x,y,x^2-lambda*y^2)` for nonsquare `lambda` is an explicitly given complete capset for every `q = 3^m`. This is another closed-form answer. |

## Why the plausible families fail

1. **Find any capset or complete capset of the constructed size:** G and V hold,
   but H fails. Theorems 2.1 and 2.6 give the witness by direct evaluation of a
   formula. Corollary 2.2 supplies complete capsets in every dimension.

2. **Extend a partial capset to any complete capset:** H fails when the finite
   universe is represented explicitly. Scan the remaining points and greedily add
   each point whenever it preserves the capset property. The result is
   inclusion-maximal, hence complete under the paper's exact definition.

3. **Find a largest or smallest capset:** this would make optimality the claim,
   which the task explicitly forbids. A bare candidate capset does not certify that
   no larger or smaller object exists.

4. **Find coefficients for a large union of parabolas:** the paper gives
   computational observations, not an unbounded hard regime. Its character
   conditions arise as a way to avoid collinear triples, and the reported examples
   are limited to small even extension degrees. Sampling a coefficient first and
   inventing a custom subset of character constraints around it would be a new
   planted CSP, not the fixed algebraic-capset family analyzed in the paper. No
   theorem in the paper would support H for that CSP.

5. **Verify completeness from a compact dimension-only input:** exact checking can
   enumerate the ambient space and secants, but that is exponential in the compact
   dimension parameter. Listing the universe explicitly makes verification
   polynomial in the representation size, but then the greedy completion argument
   above makes the unconstrained search easy.

## Required artifacts intentionally not fabricated

No `gen_2602.05254.py`, `selftest_report.json`, or
`llm_loop_transcript.jsonl` is supplied. Consequently `scripts/harden.py` was not
run. Those artifacts would imply that a G/H/V family had survived Step 0, and this
paper does not provide one. This follows the task's instruction to stop after a
correct G/H/V rejection rather than silently replace the paper's problem with a
different planted problem or report unsupported hardness.

---

## Independent audit (not the builder's self-report)

**The verdict stands, but the builder's reason for dismissing its strongest
candidate is wrong, and that matters** — anyone who later re-checks that claim
will find it false and may reopen the paper on the strength of it. See
[`audit_capset_attack.py`](audit_capset_attack.py); Theorem 2.1 was
re-implemented from scratch (`F_q = F_3[t]/(f)`, both parabolas, mapped into
`F_3^(2m)`) and independently verified.

### What was checked

Reproducing Theorem 2.1 at `m = 3` gives a capset in `F_3^6` of size
**52**, confirmed to be a capset *and* inclusion-maximal by expanding all pairs.
Lemma 1.1's bound for `F_3^6` is `N >= 38`.

### Where the builder is wrong

Its family 2 — "extend a partial capset to any complete capset" — is dismissed
because greedy extension yields an inclusion-maximal set. That is true but
answers the wrong question. No generator would ship the unconstrained form,
because a witness of *any* size is worthless; it would impose a size cap near the
paper's construction. Under that cap greedy is nowhere close:

| method | best `|C|` in `F_3^6` |
|---|---:|
| Theorem 2.1 (two conics) | **52** |
| 2000 random greedy maximal capsets | 66 (median 72, max 77) — **0/2000** reached 52 |
| destroy-and-repair local search, 35 000 iterations / 120 s | 62 |

Random greedy never once landed within 14 of the construction, and a local search
running 35 000 repair steps stalled at 62. The size-constrained task is *not*
solved by the algorithm the builder invoked to dismiss it.

### Why the family nevertheless fails — the real reason

It fails **G**, not the greedy test, and it fails **H** for a different reason
than "greedy solves it":

- **G — there is no instance to generate.** The problem input is the single
  integer `n` (plus a size cap). There is no per-instance data for a planted
  answer to hide inside, so the spec's inverse generation — *sample the answer
  first, then build the problem around it* — has nothing to build. Every instance
  at a given `n` is the same mathematical question. The only way to manufacture
  variety is to push the construction through a random affine map of `F_3^n`,
  which preserves both the capset and the completeness property — that is
  relabelling, exactly what `canonical_key` is required to collapse. The result
  is one instance per dimension, not an unlimited supply.

- **H — the closed form is the paper.** Precisely because generic search stalls
  at 62, the *only* known route to 52 is evaluating Theorem 2.1. A published
  closed-form method that answers every instance in the family is the
  disqualifier in Step 0, and here it is not incidental: it is the paper's
  contribution.

The two findings are the same coin. Generic search failing is what makes the
formula indispensable, and an indispensable published formula is a lookup.

### Scope

Rejection confirmed on **G** (no instance to generate) and **H** (the paper
supplies the closed form), not on greedy tractability. Families 1, 3 and 4 in the
builder's table are dismissed correctly: 1 and 4 by the same closed-form
argument, 3 because optimality-as-the-claim is forbidden outright.
