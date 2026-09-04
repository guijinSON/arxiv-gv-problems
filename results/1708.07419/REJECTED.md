# Rejected: arXiv 1708.07419

Paper: Olga Kharlampovich and Alexei Myasnikov, [*Undecidability of
Equations in Free Lie Algebras*](https://arxiv.org/abs/1708.07419).

## Decision

**H fails on both defensible tracks for the tested family.** G and V are
available: Lemma 6 in Section 4 constructs an exact Lie-polynomial witness by a
Jacobi recurrence, and a checker can differentiate it and compare Hall-basis
coefficients over `Q` exactly. The required Track B hardening run nevertheless
returned `too_easy` after the full three-escalation cap. This is not a claim that
the paper's general decision problem is easy.

Track A is not supported. Theorem 5 proves undecidability of the Diophantine
problem for free Lie algebras of rank greater than two by e-interpreting `K[t]`
(Theorem 3) and invoking Denef. That is a worst-case undecidability theorem. It
does not establish distributional hardness for an inverse-generated solvable
subclass, and the concrete Lemma 6 subclass used here is linear in its unknown
rational coefficients.

Track B was tested and failed empirically. The attempted native problem asked
for a rational Lie polynomial `S` satisfying

```text
[S,a] = H(m,2h) - H(m+2h,0),
H(p,q) = [ad_a^p(b), ad_a^q(b)].
```

The planted witness telescopes under
`[H(p,q),a] = H(p+1,q) + H(p,q+1)`, exactly the recurrence proved in
Section 4, Lemma 6. An invertible rank-one change among the displayed Hall
terms transported that witness without solving the generated instance.

## Certificate cost: mechanical versus compact

The certificate-producing mechanical method is Hall-basis coefficient matching
followed by exact rational Gaussian elimination. For `k` displayed basis
coefficients it costs `O(k^3)` exact arithmetic operations. At the final tested
parameters `n=256, h=18, k=36, mix_magnitude=113`, an implementation solved
8/8 seeds with a median of **55,026 counted exact operations and 0.0141 seconds**.

The compact route first telescopes the `2h=36` Jacobi terms, factors `M-I` as a
rank-one matrix, and applies the rank-one inverse. Conservatively counting the
factor recovery, two dot products, and the coefficient update gives at most
**288 exact operations**. Thus there is a genuine mechanical/compact gap; the
rejection is *not* based merely on the existence of a polynomial-time method or
on those costs being comparable. It is based on the compact route proving too
easy for the evaluation models.

## Hardening evidence

The script-owned run is preserved in `llm_loop_transcript.jsonl` and
`.meta.json` (master seed `6914801809439186778`). A level is defeated when any
of three vendors solves it.

| rung | parameters `(n,h,mix)` | solved / attempts | result |
|---|---:|---:|---|
| easy | `(24,12,3)` | 3 / 3 | defeated |
| medium | `(64,15,11)` | 1 / 3 | defeated |
| hard | `(128,18,37)` | 3 / 3 | defeated |
| script escalation | `(256,18,113)` | 1 / 3 | defeated |

At the final rung Claude returned no answer, GPT-5.6 Terra returned a parseable
but incorrect coefficient vector, and Grok 4.6 returned a witness that verified
exactly. There was no parser false negative: the only unparsed final reply ended
mid-reasoning and contained no answer tags.

## Why no module ships

The task requires stopping after a `too_easy` verdict and forbids manual
retuning beyond the harness's capped escalation. The experimental
`gen_1708_07419.py` and script-owned transcript are retained only as audit
evidence; they are **not a shipping generator**. No `selftest_report.json`, G9
arms, or README is produced for a rejected family.

Another Track A attempt would require a construction whose *generated
distribution*, not merely the unrestricted problem, inherits hardness from the
e-interpretation in Theorem 3. The paper supplies no such average-case result.
Rank two is explicitly listed as an open case in Section 1, so it cannot be used
as an alternative hard regime either.
