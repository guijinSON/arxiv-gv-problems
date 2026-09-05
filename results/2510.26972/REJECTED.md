# Rejected: arXiv 2510.26972

Paper: [Existence of primitive k-normal elements for critical values over finite fields](https://arxiv.org/abs/2510.26972).

## Decision

No family from this attempt is shippable. The retained native finite-field
generator passes G and V, but it fails **H on Track B**. Track A is not claimed:
the relevant certificate is produced by an efficient polynomial gcd/minimal-
polynomial algorithm. The script-owned no-tool hardening loop then solved every
admissible Track-B level.

The prior-triage proposal—choose field parameters and retain a primitive
`k`-normal element found by computation—also fails **G**. Appendix Algorithm 2
chooses a normal element, enumerates translates `beta+u`, and tests
multiplicative order (and then normality). Retaining the first success would be
solving the instance inside the generator, precisely the forbidden route.
Theorem 3.4 proves existence through character-sum bounds but does not identify
the successful translate, so it does not repair G.

## The built candidate

The retained module uses the paper's native objects rather than a graph or
finite-field surrogate. Definition 2.3 defines the `F_q`-order of `beta` as the
least monic polynomial `g` for which the linearized polynomial `L_g(beta)`
vanishes. Theorem 2.4 says its degree is `n-k` for a `k`-normal element.
Following Proposition 3.1 and the explicit factor identity in Lemma 3.6(i), the
generator constructs complementary factors `f*g=x^N-1`, forms
`beta=L_f(alpha)` in normal-basis coordinates, and applies a certified invertible
circulant transformation. Its polynomial witness is therefore carried by
construction, not recovered by a solve. Verification is an exact sparse cyclic
convolution over `F_q`.

All local gates pass. At the shipping preset the unique witness occupies 115
characters / 20 atoms, the intended route is bounded by 218 exact operations,
the fully constrained answer space has
`375948542378408874295835214839507208411550493014220583282974120987985046016635`
candidates, and 200,000 structure-aware random samples produced 0 successes.
Four attacks each failed on 8/8 seeds, and 60 canonical-invariance/carried-
witness checks passed.

## Why H fails

The **mechanical cost** is real but irrelevant to this rejection. The standard
algorithm computes

`Ord(beta) = (x^N-1) / gcd(x^N-1, B_beta)`.

The final measured run used 105,980,792 exact coefficient operations and 3.293
wall-clock seconds across eight shipping instances (maximum 14,422,715
operations for one), with the expected `O(N^2)` schoolbook complexity.

The **compact route** is at most 218 operations: infer the common cyclic block
stride, substitute `y=x^A`, and use the two complementary geometric factors.
This is a large mechanical/compact gap, so the mere existence of the gcd
algorithm is not the rejection reason. The failure is that the compact route is
too exposed: public `k`, the required term count, and the repeated block pattern
fix the same alternating coefficient formula on every seed. Increasing the
field size, extension degree, and number of disguise coordinates changes none
of it.

The bare hardening run returned a valid, exactly verified witness on **12/12**
calls:

| level | parameters (abridged) | solved |
|---|---|---:|
| easy | `A=32, t=5, degree N=320` | 3/3 |
| medium | `A=128, t=7, degree N=1792` | 3/3 |
| hard | `A=256, t=9, degree N=4608` | 3/3 |
| escalated | `A=512, t=9, degree N=9216` | 3/3 |

The escalated compact route used 298 operations and was the last level below
the 300-operation cap. A further disguise increase would test prompt scanning
rather than mathematical insight, while increasing only `N` or `q` had already
proved ineffective. Accordingly `escalate()` returned `None`, and
`scripts/harden.py` recorded `verdict: too_easy` after three escalations.

## Other native choices checked at STEP 0

- Asking directly for a primitive `k`-normal element has exact verification, but
  the paper's certificate-producing Appendix algorithm is a translate search;
  it fails G for a scalable generator.
- Asking only for a polynomial with property (A) is generatable from Lemmas 3.5
  and 3.6, but those lemmas give the short factor explicitly. Mechanical cost
  and compact route are then comparable, so that variant fails H even before an
  oracle run.
- Theorem 4.2 is a complete `n=6, k=3` existence classification. Turning its
  exceptional cases into questions would be a classification lookup, not an
  unlimited hard witness family.

The failed implementation is retained as
`rejected_gen_2510.26972.py`, together with `selftest_report.json`, the
script-owned `llm_loop_transcript.jsonl`, and `.meta.json`, so this decision can
be replayed or reopened.
