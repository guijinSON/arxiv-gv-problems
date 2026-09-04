# Rejected: arXiv 2110.12933

## Decision

No family is shipped. The constructed native algebra family passes G and V, but
fails the mandatory no-tool hardness gate **G9(b) on Track B**. It also cannot
be relabelled Track A: the generated distribution has an exact polynomial-time
recovery algorithm.

The retained implementation is `rejected_gen_2110_12933.py`. Its
`selftest_report.json` records G1--G8 passing and G9 failing. The bare shipping
evidence remains in `llm_loop_transcript.jsonl`; the decisive corrected hinted
evidence is `g9_hinted_transcript.jsonl`.

## Paper result used

Section 3 states the native search problem: find an element of the form
`a*x*b-c` in a noncommutative ideal. Its worked example searches a degree-5
compatible right-ideal approximation containing 263 generators (3485 without
quiver compatibility). Section 4 defines the homogeneous part of an ideal;
Theorem 4.3 identifies it with an elimination intersection and Procedure 1
enumerates its noncommutative Groebner basis. The Introduction explicitly says
these Groebner procedures need not terminate in general because free-algebra
ideal membership is undecidable. Theorem 5.4 and Procedure 2 give the analogous
monomial-part construction for right ideals, while the final paragraph leaves
the arbitrary two-sided monomial-part problem open.

Those general statements do not establish hardness for this generated
distribution. Here every generator and requested polynomial is homogeneous of
one fixed word length. Any nonempty left or right multiplier raises the degree,
so membership in the requested component reduces to exact coefficient-space
linear algebra.

## What was built

The generator first samples a binary monomial `x`, an invertible affine map over
F2, row scales, and auxiliary monomials. It forms paired homogeneous
polynomials and carries the planted relation through a scaled Walsh transform.
The answer is the monomial plus an exact rational ideal-membership decomposition
encoded by 64 signs. Verification expands the displayed linear combination
over the free algebra and compares every integer coefficient exactly. The
generator never solves its output instance.

At the attempted shipping preset (`n=64`), the bounded answer language has
`64 * 2^64 = 1,180,591,620,717,411,303,424` candidates and exactly one valid
answer. Structure-aware sampling found 0 hits in 200,000 trials. The answer is
45 serialized characters, 70 logical atoms, and about 12 tokens.

## Mechanical cost and compact route

The domain-standard fixed-degree method is exact coefficient matching followed
by Gaussian elimination, with generic complexity O(n^3). A stronger algorithm
for this particular distribution simply compares the distinguished monomial's
normalized coefficient column against every candidate column. It succeeds in
O(n^2): at `n=64` it used exactly **8,256 sign operations per instance**,
66,048 over eight successful trials. The self-test measured 0.001967 seconds
for the eight scans (and a separate build/solve/verify measurement took
0.044845 seconds total).

The compact route reads the Walsh labels of the zero and unit candidate words,
recovers and solves the hidden 6-dimensional affine change of variables, and
writes the character signs. The conservative count is **120 exact operations**.
Thus there is a real 8,256-versus-120 Track B compression gap; the rejection is
not the mere existence of an efficient algorithm and not a claim that those
costs are comparable. It fails because the evaluated oracle demonstrably
executed the compact route when given only the allowed structural invariant.

## Decisive G9 evidence

The structural hint was:

> The normalized generator columns are Walsh characters whose labels and the
> candidate words share one affine map over F2.

This names one invariant. It does not chain steps, state a derived quantity, or
give the recovery procedure.

The original bare `easy` run was hardened 0/3. The hinted `easy` arm was solved
by GPT-5.6-terra, so the rules allowed exactly one named-rung increase. At
`medium`, the bare arm was again hardened 0/3 (Claude, Gemini, and
GPT-5.6-terra; a Grok timeout was excluded), and the placebo arm was 0/3.

The first hinted-medium transcript initially exposed a parser bug: Gemini
returned visible fenced JSON without tags. `parse_answer` was fixed to recover
standalone JSON; that old answer then verified false. The hinted arm was rerun
from scratch. On the corrected decisive run, GPT-5.6-terra failed but Grok
returned

```json
{"x":"111001","signs_hex":"0FF0F00FF00F0FF0"}
```

and the exact checker returned `(True, "ok")`. The run was stopped immediately;
one solved attempt is sufficient to fail polarity-flipped G9(b), and the prompt
forbids further tuning after the single rung increase.

## Gate summary

| Gate | Result |
|---|---|
| G1 planted certificates | pass, 12/12 |
| G2 corruptions | pass, five distinct rejection reasons |
| G3 parser round-trip | pass, including untagged fenced JSON after the fix |
| G4 random guessing | pass, 0/200,000 |
| G5 density/baseline | pass, one certified answer; 8,256-op reference scan |
| G6 adversary panel | pass, four attacks at 0/8; reference algorithm 8/8 as expected |
| G7 scaling | pass, doubled `n=128` builds and verifies |
| G8 canonical key | pass, 60 invariance and witness checks; 20/20 distinct seeds |
| G9 answer/effort caps | pass, 45 chars, 70 atoms, 120 operations |
| G9(b) hinted hardness | **fail**, corrected hinted-medium oracle solved |

## Final classification

- **G:** passes by inverse generation and transformation of a known identity.
- **V:** passes by exact noncommutative coefficient expansion.
- **H, Track A:** fails because O(n^3) coefficient elimination and the O(n^2)
  antipodal scan solve every generated instance.
- **H, Track B:** the compression gap exists, but mandatory G9(b) fails after
  the one permitted escalation. Therefore this family cannot ship.

