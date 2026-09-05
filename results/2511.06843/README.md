# Affine isomorphisms of split binary forms (arXiv:2511.06843)

**Status: parked, not shippable yet.** The generator and all local gates G1–G9 pass. The required multi-vendor oracle evidence is incomplete: a fresh bare run produced one scored Google reply that solved `easy`, after which every required OpenAI redraw returned HTTP 403 “Key limit exceeded.” The G9 arms likewise could not complete. API errors are retained as errors, never counted as model failures.

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate | matrix certificate |
| Intuition | invariant: centered root-moment covariance |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust boundary

The family instantiates the Polynomial Isomorphism Search Problem defined in Section 8 of Martin Kreuzer’s [Code Equivalence, Point Set Equivalence, and Polynomial Isomorphism](https://arxiv.org/abs/2511.06843). A panel gives expanded degree-`d` homogeneous binary forms `F,G` over `F_p[x,y]` and asks for an invertible matrix `A=[[1,u],[0,a]]` satisfying `F(A(x,y)^T)=G(x,y)`. The checker substitutes the proposed matrix with exact modular binomial arithmetic and compares every coefficient. It never reads the planted answer.

Generation samples `d` distinct roots `R` in `F_p`, expands `F = product_(r in R) (x-r*y)`, samples `a` uniformly from `2..p-1` and `b` uniformly from `1..p-1`, and expands `G = product_(r in R) (x-(a*r+b)*y)`. Consequently `[[1,-b],[0,a]]` is known by composition of identities before the instance exists. The roots are deliberately omitted from the rendered question.

This is not a Track A claim. The paper’s Introduction notes structural attacks on special LCE regimes and extensive cryptanalysis of cubic IP1S; Section 10 says PI is believed efficiently solvable in the vast majority of cases. Here the explicit standard route factors each form over `F_p` and aligns its two root sets. General randomized finite-field factorization is polynomial in `d` and `log(p)`; the elementary alignment used here is `O(d^3)`. The measured standard-library specialization exhaustively evaluates all `p` field elements and averaged 1,427,306 field operations at the intended hard preset. Recorded wall time ranged from 0.03 s when the host was idle to 0.67 s during the final shared-runner selftest; the operation count is the reproducible cost signal.

The compact route uses Newton’s identities on only the first three coefficients. If `m,C2,C3` are the root mean and centered power sums, then `C2'=a^2*C2`, `C3'=a^3*C3`, and `m'=a*m+b`. Thus `C3/C2` exposes the scale covariance and the means expose the translation. Counting modular inverses by square-and-multiply, four independent panels require at most 280 exact field operations—short enough after the insight, but mechanically tedious without a calculator.

## Worked demo

This is `make_instance(seed=0, n=5, prime=17, panels=1)` in full:

```text
Polynomial Isomorphism Search over a prime field (batched).

All arithmetic is in F_17: reduce every integer modulo 17.
Each panel gives two homogeneous binary forms F(x,y), G(x,y) of degree 5.
A displayed vector [c0,c1,...,cd] means exactly
  c0*x^d + c1*x^(d-1)*y + ... + cd*y^d.
Every displayed coefficient is the canonical integer in 0..p-1.

For each panel, find a normalized affine change-of-variables matrix
  A = [[1, u], [0, a]] with 0 <= u < p and 1 <= a < p
such that F(A*[x,y]^T) = F(x+u*y, a*y) equals G(x,y)
coefficient by coefficient in F_p.  A solution is guaranteed for every
panel.  The panels are ordered, and your matrices must follow Panel 1,
Panel 2, and so on in that order.  The same field element may appear more
than once inside a matrix; no floating point or integer equality is intended.

Panel 1
F: [1,7,14,16,7,16]
G: [1,3,9,2,8,11]

Output one JSON object with exactly one 2x2 matrix per panel:
{"matrices":[[[1,u1],[0,a1]],[[1,u2],[0,a2]],...]}.
Use ordinary base-10 integers in 0..p-1 and no ellipses.
Give your final answer inside <answer></answer> tags, as that exact JSON object.
Example: <answer>{"matrices":[[[1,3],[0,5]]]}</answer>
Output nothing else inside the tags.
```

The answer is `{"matrices":[[[1,5],[0,9]]]}`. `verify(inst, answer)` returns `(True, "ok")`; changing the `5` to `6` returns `(False, "panel 0 coefficient mismatch at index 1")`. The demo is hand-solvable: it has one degree-5 panel over `F_17`, so the centered-moment computation fits on paper.

## Difficulty presets

| preset | degree | prime | panels | status |
|---|---:|---:|---:|---|
| demo | 5 | 17 | 1 | hand example; skipped by hardener |
| easy | 40 | 1009 | 2 | Google solved; the second vendor was quota-blocked |
| medium | 60 | 1009 | 3 | not reached |
| hard | 80 | 1009 | 4 | intended shipping preset; local gates measured here |

`SHIPPING_DIFFICULTY` is provisionally `hard`; it is not an actual shipping claim until the bare loop reaches and holds a rung and all three G9 diagnostic arms complete.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset–seed witnesses verify; 12/12 JSON round trips |
| G2 | pass | 9/9 corruptions—including swapped and duplicated matrices—rejected with 9 distinct reasons |
| G3 | pass | tagged fenced JSON round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; language size 1,070,056,706,803,987,455,737,856 |
| G5 | pass | shipping density 0/200,000; demo exact count 1; reference 1,454,243 operations in 0.749569 s |
| G6 | pass | five attacks at 0/8; reference solves 8/8, 1,427,306 operations in 0.666953 s mean |
| G7 | pass | degree 160 verifies with the same 16 answer atoms |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 changed relative maps stay distinct; 20/20 unrelated keys distinct |
| G9 | pass | cap gate: 86 chars, 22 estimated tokens, 16 atoms, 280 operations; three-arm diagnostic incomplete |

The G6 failures are raw coefficient ratio, translation-only greedy, 256 random restarts, scale-only ansatz, and an uncentered-moment ratio. The successful factor-and-align algorithm is correctly outside `attacks` because this is Track B.

## Oracle loop and G9

The fresh harness-owned bare transcript has one scored solve followed by four failed redraws. Errors do not consume attempts, so the harness correctly stopped without a hardness verdict:

| preset | seed | model | result |
|---|---:|---|---|
| easy | 982510683 | Gemini 3.8 Flash | solved |
| easy | 551976834 | GPT-5.6 Terra | HTTP 403 key limit |
| easy | 348528051 | GPT-5.6 Terra | HTTP 403 key limit |
| easy | 1760259 | GPT-5.6 Terra | HTTP 403 key limit |
| easy | 345679849 | GPT-5.6 Terra | HTTP 403 key limit |

| G9 arm | solved / completed attempts | conclusion |
|---|---:|---|
| bare | 0/0 | blocked before scoring |
| hinted | 0/0 | attempted; blocked before scoring |
| placebo | 0/0 | attempted; blocked before scoring |

Hinted minus placebo is undefined. No claim about the usefulness of the invariant hint is possible yet. The retained G9 transcripts contain harness-authored HTTP 403 records only. After restoring OpenRouter quota, rerun bare in this directory, rerun hinted and placebo in their separate scratch directories, copy their completed harness-produced transcripts back, update `G9_RESULTS`, and regenerate `selftest_report.json`.

## Use

```python
from gen_2511_06843 import DIFFICULTY, make_instance, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

The module is standard-library-only; `gvlib` is unnecessary for this finite-field specialization. From the repository root, after G9/STEP 4 complete successfully:

```bash
bash scripts/emit.sh 2511.06843 20 hard
```

## Caveats

This promise family is much narrower than unrestricted PI: the matrix is affine and normalized, every form splits into distinct linear factors over the base field, the generator excludes identity scales and zero translations, and instances with zero second or third centered moment are resampled. A tool-enabled solver should use the moment formula directly and will solve the family quickly; that is the point of Track B, not a weakness being hidden as Track A. The 0/200,000 density estimate is under independent uniform affine matrices from the full language stated to the solver; it does not estimate a solver prior that has found the centered-moment invariant, and batching makes random guessing look far worse than one panel’s roughly one-in-`p(p-1)` chance. No Gröbner-basis, tensor, or optimized Cantor–Zassenhaus implementation was benchmarked. Most importantly, no oracle hardness evidence exists until the external quota problem is fixed.
