# Januarial trace-parameter certificates (arXiv:1810.00203)

Status: the generator and every local gate pass, but the required multi-vendor
hardening run is **not complete**. A retry on 2026-09-05 obtained eight verified
oracle solutions—3/3 at `easy`, 3/3 at `medium`, and 2/2 completed calls at
`hard`—before OpenRouter returned HTTP 403 “Key limit exceeded” on the third
`hard` call and all redraws. Errors are not treated as model failures. The
current named ladder is therefore demonstrably too easy, but the script could
not reach a verdict or test its permitted post-`hard` escalations.

| Profile field | Value |
|---|---|
| Track | B — an efficient exact algorithm exists |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | polynomial (a canonical list of linear factors) |
| Intended intuition | invariant: trace parameters of powers obey a second-order recurrence |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The source is Mehwish and Mushtaq, [“All januarials constructed from Hecke
groups”](https://arxiv.org/abs/1810.00203). An instance gives a prime `p`,
`k=(p+1)/2`, the prime divisors of `k`, and one native `2 x 2` matrix representing
an order-`k` element of `PGL(2,p)`. The solver returns a split monic polynomial as
12 factors `T+c`. Every decoded root `theta=-c` must make

`A_theta = [[0,-1],[theta,theta]]`

have exact projective order `k`. The verifier uses only modular matrix
exponentiation: it checks that `A_theta^k` is scalar and that
`A_theta^(k/r)` is non-scalar for every prime `r|k`. It accepts any 12 distinct
valid roots and never reads the planted answer.

This is the paper’s algebra, not a graph surrogate. Section 2, Theorems 1–2,
identify `k=(p+1)/2` as the two-equal-orbit januarial regime. Section 3 defines
`theta=(tr XY)^2/det(XY)` and its Cayley–Hamilton polynomial `g_k`; Theorem 3
removes roots of the proper-divisor polynomials. The conjugacy lemma in Section 4
says every order-`k` class occurs as `z^i` or `z^-i` for a coprime exponent, and
the following count is `phi(k)/2`.

## Why Track B

There is no Track A claim: the paper itself supplies an efficient method. The
strongest literal reference implementation scans `theta` values in order,
performs the Section 3 exact-order test, and stops as soon as it has the required
12. Its worst case is `O(p * omega(k) * log k)`. On the fixed hard audit
instance (`seed=20260518`, `p=30637`) it found the twelfth root after 49 values,
using 1,249 matrix multiplications and 19,984 counted modular scalar operations
(0.0007–0.008 s across local runs). Across the eight G6 seeds its maximum was
71,872 scalar operations. A separate full-field scan used 12,499,488 operations;
that scan audits the exact density and is not presented as the task-solving
baseline.

The compact route is qualitatively different. If `w` is the eigenvalue ratio,
then `theta=w+w^-1+2`; therefore `c_e=theta_e-2` satisfies
`c_(e+1)=(theta-2)c_e-c_(e-1)`. Small exponents coprime to `k` produce the
needed parameters. The audited route is bounded at 108 exact operations (190
over all 256 hard seed slots). Seeing that invariant is the intended step; a
literal field scan is far beyond unaided in-context execution.

## Worked demo

Here is the full rendered mathematical instance for
`make_instance(n=31, seed=0, factor_count=3, seed_slots=1, seed_stride=2)`:

```text
Januarial trace-parameter certificate over a prime field

Work in the field F_p of integers modulo the prime p=31. A 2-by-2 matrix is
viewed projectively: two invertible matrices represent the same element of
PGL(2,p) when one is a nonzero scalar multiple of the other. Consequently a
matrix has projective order k when its kth power is a nonzero scalar matrix and
no smaller positive power is scalar.

Here k=(p+1)/2=16, whose distinct prime divisors are [2]. The supplied
reference matrix

  Z = [[0, 30],
       [28, 28]]  (entries modulo p)

is promised to have projective order k. For a nonzero residue theta in F_p,
define

  A_theta = [[0, -1], [theta, theta]] modulo p.

Its determinant and trace are both theta, so its conjugacy invariant
(trace(A_theta)^2 / determinant(A_theta)) modulo p is theta. Call theta
admissible exactly when A_theta has projective order k. Equivalently, because
the prime divisors of k are listed above, A_theta^k must be scalar and
A_theta^(k/r) must be non-scalar for every listed prime r.

Return one split monic polynomial H(T) as exactly 3 linear factors over F_p.
Encode a factor T+c as the JSON pair [1,c], with c the canonical integer in
0..p-1. The decoded roots (-c modulo p) must be nonzero, pairwise distinct,
and the factors must be ordered by increasing decoded root. Every decoded
root must be admissible. Any 3 roots satisfying these rules are accepted;
repeats are forbidden.

Give your final answer inside <answer></answer> tags as a JSON list of exactly
3 pairs [[1,c1],[1,c2],...,[1,c3]].
Example shape and ordering (not claimed admissible):
<answer>[[1,30],[1,29],[1,28]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[1,15],[1,12],[1,3]]</answer>`, with roots
`16,19,28`. `verify` returns `(True, "ok")`. Replacing the first factor by
`[1,0]` returns `(False, "decoded roots must be nonzero")`. This demo is
hand-solvable: the reference invariant is 28 and only the exponents 1, 3, and 5
are needed in the recurrence.

## Difficulty presets

| Preset | Lower bound for `p` | Factors | Seed stride | Status |
|---|---:|---:|---:|---|
| demo | 31 | 3 | 2 | hand example; skipped by hardener |
| easy | 1,009 | 12 | 4 | rejected by oracle: 3/3 solved |
| medium | 5,003 | 12 | 16 | rejected by oracle: 3/3 solved |
| hard | 20,011 | 12 | 64 | 2/2 completed calls solved; third call blocked by account limit |

Seed slots vary the prime while holding the answer length fixed. `escalate()`
quadruples the field floor and doubles the spacing, again leaving 12 factors.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 preset-seed certificates verify and JSON-round-trip |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with 5 reasons |
| G3 | pass | tagged, fenced model-style response round-trips |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `5.9220e-8` |
| G5 | pass | 0/200,000 sampled guesses; 7,659 roots confirmed by the density audit; early-stop baseline 49 parameters / 19,984 operations |
| G6 | pass | four attacks at 0/8; early-stop reference scan solves 8/8, at most 71,872 operations |
| G7 | pass | named spaces increase; doubled size builds at `p=42209` and verifies |
| G8 | pass | 80/80 conjugation/scaling/inversion checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst of all 256 hard seed slots: 121 chars, 31 estimated tokens, 24 atoms, 190 intended operations |

The certificate sampler is structure-aware: it draws a uniformly random
12-subset of the nonzero field and automatically emits monic factors in the
required root order. Its space is not the looser space of arbitrary JSON or
arbitrary coefficients.

## Oracle and G9 diagnostics

| Run | Valid solved/attempts | Script-owned calls | Result |
|---|---:|---:|---|
| bare ladder, easy | 3/3 | 3 valid calls | solved; escalated |
| bare ladder, medium | 3/3 | 3 valid calls | solved; escalated |
| bare ladder, hard | 2/2 completed | 2 valid calls, then 4 errors | incomplete; all completed calls solved |
| structural hint | 0/0 | 4 errors | unavailable: OpenRouter HTTP 403 key limit |
| placebo hint | 0/0 | 4 errors | unavailable: OpenRouter HTTP 403 key limit |

At the configured hard preset the bare arm is 2/2 solved, but it remains
incomplete because the required third call could not be made. `hinted - placebo`
is undefined because neither auxiliary arm obtained a valid attempt; the module
records 0.0 only as a serialization fallback and marks
`diagnostic_complete=false`. No conclusion about hint responsiveness is
justified yet. Replenish the OpenRouter allowance and rerun the bare loop and
both G9 arms; a successful bare run must continue through the script's allowed
post-`hard` escalations. The structural hint names only the trace recurrence,
not a procedure.

## Use

From this directory:

```python
import random
import gen_1810_00203 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
candidate = g.random_candidate(inst, random.Random(1))
```

From the repository root, once a valid hardened transcript exists:

```bash
bash scripts/emit.sh 1810.00203 20
```

## Caveats

- The required oracle evidence is missing because of an account limit. This
  directory is not submission-ready until `harden.py` records a real verdict.
  Moreover, all eight completed calls solved, so none of the three named
  presets can presently support the hardness claim.
- A solver that immediately recognizes the Section 4 coprime-power recurrence
  has found the intended short route; the pending oracle run is needed to show
  whether the bare statement makes that too obvious.
- The observed guess probability is for uniform valid-shape factor sets. It
  says nothing about a model prior conditioned on the displayed reference
  matrix. The exact density uses the paper’s `phi(k)/2` count.
- The panel tried small parameters, numerical neighbours, 256 uniform restarts,
  and ordinary field powers. It did not run a CAS polynomial factorizer or a
  discrete-log package. The early-stopping exact-order scan is the successful
  Track B reference algorithm; the full scan is reported only as a density
  cross-check.
- Generation rejection-samples one certified reference parameter before
  exposing the instance, then transports the answer through group powers. The
  sampling is fast on tested primes but has a defensive 100,000-trial cap.
- `canonical_key` deliberately discards the displayed reference matrix: PGL
  conjugation, scalar representatives, inversion, and choosing another
  order-`k` reference do not alter the accepted polynomial set. At the hard
  preset 255 of 256 seed slots produced distinct primes in the audit.
- `gvlib` is optional here; all finite-field operations have a standard-library
  implementation, so missing it does not change the object regime or checker.
