# Red–blue chord separation on a rational circle

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate | matrix certificate (rational chord endpoints) |
| Intuition | symmetry: the colour polynomial's distinct roots form a centred arithmetic progression |
| Domain essentiality | native |
| Reduction | none |

This is a self-contained generator for the strict Red–Blue Separation problem in
[Misra, Mittal, and Sethia, *Red-Blue Point Separation for Points on a Circle*](https://arxiv.org/abs/2005.06046).
The solver receives an exact, succinctly specified set of rational points on the unit circle and an
integer polynomial that colours them.  It must return straight chord lines whose induced cells are
monochromatic.  The checker substitutes every input parameter into the displayed polynomial and every
chord equation using integers only; it accepts any canonical chord witness that really separates the
colours, not just the planted one.

## Why this is Track B

Proposition 3.1 says every colour switch must be stabbed.  Section 3.1 pairs switches around chunks to
obtain an optimal set of general lines, and Theorem 3.8 concludes that circle instances are
polynomial-time solvable.  That explicitly rules out a Track A claim.  For the succinct polynomial
input, the strongest instrumented reference is exact Sturm-sequence isolation: on this promised
integer-root family it uses `O(d^3 log N)` rational operations and, across eight shipping seeds, averages
**87,876 operations** and about **0.08 s**.  The paper's cyclic scan is also measured: Horner evaluation
makes it `O(Nd)`, or **4,320,396 integer operations** at shipping size.

The compact route uses the top three coefficients.  Vieta's identities expose the centre and squared
spacing of the repeated root progression; its 18 distinct roots are the switch midpoints, and any
matching of those switches yields separating chord signs.  The measured route uses at most **66 exact
operations**.  It is short once the symmetry is seen but is not the 4.3-million-operation scan a model
can mechanically execute without tools.

## Worked demo (seed 0)

The complete rendered instance is:

```text
Strictly separate red and blue rational points on a circle.

For every integer j with 0 <= j < N=13, the input contains the exact
point

    P(j) = ((1-j^2)/(1+j^2), 2j/(1+j^2))

on the unit circle.  These are N distinct points, encountered in increasing j
order along one arc.  Let Q(z)=a_0+a_1*z+...+a_d*z^d be the integer polynomial
whose coefficients [a_0,a_1,...,a_d] (ascending-power order) are

    [21945, -7748, 974, -52, 1]

A point P(j) is red when 1*Q(2j)>0 and blue when
1*Q(2j)<0.  The supplied data guarantee Q(2j) is never zero.

A chord endpoint parameter u means the rational point
P(u)=((1-u^2)/(1+u^2),2u/(1+u^2)).  A chord row [u,v] denotes the entire straight
line through P(u) and P(v).  A collection of lines strictly separates the input
when no input point lies on a line and every cell induced by the lines contains
points of at most one colour (equivalently, every red-blue segment meets a line).

Find exactly k=2 separating chord lines.  Every endpoint must be the midpoint
of a gap between consecutive input parameters: write it as the normalized
rational [r,2], where r is odd and 1 <= r <= 23.  All 4
endpoints must be distinct.  In each chord put the smaller rational first, and
sort the k chord rows lexicographically.  Thus the answer is a JSON matrix of
shape k by 2 by 2; order is only a required canonical serialization, not a
geometric orientation.  Fractions are exact [numerator,denominator] pairs.

Give your final answer inside <answer></answer> tags, as that JSON matrix.
Example: <answer>[[[1,2],[3,2]],[[5,2],[7,2]]]</answer>
Output nothing else inside the tags.
```

Here `Q(z)=(z-7)(z-11)(z-15)(z-19)`, so one answer is
`<answer>[[[7,2],[11,2]],[[15,2],[19,2]]]</answer>`.
`verify` returns `(True, "ok")`.  Dropping the second chord returns
`(False, "expected 2 chord rows, got 1")`.  This demo is genuinely hand-solvable; its candidate space
has 1,485 canonical matchings and exactly 3 valid ones.

## Difficulty presets

| Preset | N | Chords | Odd root multiplicity | Polynomial degree | Candidate bits | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 13 | 2 | 1 | 4 | 11 | hand example; hardening skips it |
| easy | 120,011 | 9 | 1 | 18 | 277 | candidate shipping preset; defeated 2/3 by the oracle pool |
| medium | 180,013 | 9 | 3 | 54 | 287 | defeated by the first scored oracle call; remaining calls blocked by quota |
| hard | 260,003 | 9 | 5 | 90 | 297 | internal gates pass; oracle not reached |

Both fixed-length axes grow: `N` enlarges the gap haystack, while odd root multiplicity raises blind
colour-evaluation cost without changing any colour or adding answer rows.

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified; JSON round trips |
| G2 | pass | drop, row swap, duplicate, empty, and out-of-range corruptions all rejected for 5 distinct reasons |
| G3 | pass | tagged JSON recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; 277-bit bounded candidate language |
| G5 | pass | exact shipping density 34,459,425 / 1.433×10^83 = 2.404×10^-76; sampled 0/200,000; Sturm 87,876 operations and paper scan 4,320,396 operations |
| G6 | pass | five attacks, each 0/8; Sturm reference 8/8; paper scan 8/8; compact route 8/8 |
| G7 | pass | doubled `N=240,022` builds and verifies; candidate space grows from 277 to 295 bits |
| G8 | pass | 140/140 invariant transformations are real; 20/20 unrelated keys are distinct |
| G9(c) | pass | 217 chars, 55 estimated tokens, 36 atoms, 66 intended-route operations |

## Oracle loop and G9 diagnostics

The required script was run and produced real negative evidence before the configured OpenRouter key
exhausted its total limit.  At `easy`, OpenAI and Gemini solved two of three independently seeded
instances; the third answer parsed but failed exact verification.  The first `medium` call, to Gemini,
also solved.  Four redraws then returned HTTP 403, and `harden.py` correctly aborted instead of scoring
an API error as a model failure.  Consequently there is **no hardened verdict** and the result is not
submission-ready.  The successful replies show that the arithmetic-progression invariant is often
recoverable without a hint at the first two rungs.

| Arm | Preset | Script records | Scored solved/attempts | Result |
|---|---|---:|---:|---|
| bare | easy | 3 scored calls | 2/3 | level defeated; harness escalated |
| bare | medium | 1 scored call, then 4 failed redraws | 1/1 | level already defeated; run aborted on quota |
| structural hint | easy | 4 failed redraws | 0/0 | all HTTP 403; unrun diagnostic |
| placebo hint | easy | 4 failed redraws | 0/0 | all HTTP 403; unrun diagnostic |

`hinted - placebo` is therefore undefined, not evidence of zero effect.  The JSON report stores the
completed bare result as 2/3, both diagnostic arms as 0/0, and `hinted_verdict="unrun"`; the three
script-owned transcripts preserve the scored calls and failures.  Once quota is restored, rerun the
bare loop to a terminal verdict, then rerun both G9 arms and replace those records before submission.

## Use

```python
import random
import gen_2005_06046 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) > 2**276
```

From the repository root, after a successful oracle rerun reaches `hardened` and the reports are
regenerated:

```bash
bash scripts/emit.sh 2005.06046 20
```

## Caveats

- This is intentionally **not** a structural-hardness claim.  The counted Sturm implementation solves
  shipping instances in roughly 0.07–0.08 seconds without host contention (0.47 seconds in the final
  throttled rerun), and an external SymPy `factor_list` audit took about 0.013 seconds at degree 18.
  These tool routes are the reason the module declares Track B.
- The paper's input model lists coloured points.  Here the same finite point/colour set is given
  intensionally by an exact circle parametrization and colour polynomial rather than as 120,011 printed
  coordinate pairs.  This succinct representation is not introduced in the paper and is essential to
  the mechanical/no-tool gap; the checker nevertheless performs the paper's geometric chord-side test.
- The 0/200,000 figure samples uniformly after imposing every stated syntactic constraint: exactly nine
  canonical chords matching 18 distinct half-gap endpoints.  It does not describe a prior over all real
  lines.  If the true switch gaps are already known, all 34,459,425 matchings of them are valid.
- The panel includes a counted exact Sturm-isolation reference and an external audit confirmed that CAS
  factorization succeeds.  The failing no-tool attacks cover edge outliers, leftmost greediness, unit
  and 32 small spacings, and 256 structure-aware random restarts over eight seeds; no SMT/SDP attack was
  attempted because neither matches this promised univariate-polynomial core.
- `canonical_key` handles all representation symmetries generated here—positive polynomial scaling,
  simultaneous sign-convention changes, global colour exchange, and their compositions.  It does not
  attempt canonicalization under arbitrary projective automorphisms of the circle.
- Most importantly, the candidate shipping rung is already known to be too easy for two vendors, and
  external hardness evidence is incomplete because quota failed before the harness could test the full
  ladder.  The module, internal report, successful/failed transcripts, and exact verifier reasons are
  retained so this is resumable; they must not be presented as a successful STEP 4 run.
