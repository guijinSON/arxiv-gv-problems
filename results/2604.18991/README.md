# Polynomial Bézout witness generator for arXiv:2604.18991

Status: all local gates pass, but the required oracle hardening is **not complete**. The configured OpenRouter key reports usage 603.30 against a 600 limit and zero remaining; OpenRouter therefore returned HTTP 403 (`Key limit exceeded (total limit)`) on every bare, hinted, and placebo redraw. The error-only transcripts are retained; they are not counted as model failures and establish no hardness verdict.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | polynomial |
| Intended intuition | invariant: recognize that `L` is an `E`-th root of unity modulo `A` |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Miyazaki, Scott, and Styer, [“Handling some Diophantine equation via Euclidean algorithm and its application to purely exponential equations”](https://arxiv.org/abs/2604.18991). Section 11, especially Proposition 11.1 and Remark 11.1(ii), uses the Euclidean algorithm over `Q[t]` to construct a Bézout identity for the geometric-sum polynomial `A_E` and a polynomial containing `(t-1)I_{E,N}`. The proof of Lemma 5.11 works out the `E=3` case by two divisions.

An instance gives succinct polynomials `A` and `F` in an affine linear form `L`. The solver returns a bounded integer-coefficient polynomial `W` such that `A*P + F*W = H` for some `P in Q[t]`. The checker does not need `P`: it reduces `F*W` modulo `A` with exact rational arithmetic and compares the remainder with `H`. The planted `W` is obtained by composing a closed roots-of-unity identity with `L -> L^k`, a monomial shift, scaling, an affine variable change, and addition of a known multiple of `A`; the generator never runs Euclid to discover its answer.

This is native coverage of the paper’s rational-polynomial machinery, but it is not a generator for solutions of the paper’s original exponential Diophantine equations. Accordingly, the solver-facing domain is honestly labelled `algebra`, not the paper’s arXiv category `math.NT`.

## Why Track B

Track A would be false. Remark 11.1(ii) explicitly says the polynomial Euclidean algorithm constructs the certificate, and Section 11 notes that the `m=2` Diophantine case is completely solved. The reference implementation performs generic binary modular powers, a geometric sum, and polynomial extended Euclid in `O(E^2(log s + log N) + E^3)` exact rational operations. At the designated shipping preset it solved 8/8 instances, averaging 2,029,486 operations (maximum 2,048,442) and 1.079347 seconds in the latest recorded run (wall time is machine-load dependent; the exact operation count is stable).

The compressed route uses `A(L)(L-1)=L^E-1`. Thus `L^E=1` modulo `A`; the huge geometric sum collapses, and the inverse of `L-1` is carried through the exponent automorphism and shift by a cyclic coefficient permutation. The audited implementation uses at most 288 exact operations. Recognizing this quotient-ring invariant—not mechanically executing two million operations—is the intended task.

## Worked demo

`make_instance(n=4, order=3, scalar_max=1, seed=3)` renders, without a hint:

```text
Find a rational-polynomial Bezout witness.

All polynomials are in Q[t], with exact rational coefficients.  Define the
distinguished linear polynomial

  L(t) = 9*t - 1.

Its coefficient of t is nonzero, so powers of L form a valid polynomial basis.
Let E=3, N=11, S=13,
r=2, s=E*S+r, k=2,
c=1, and g=2.  Thus s is specified exactly
without requiring its decimal expansion.  The integers satisfy gcd(k,E)=1.
Define

  A(t) = sum of L^j for all integers j from 0 through E-1,
  I(t) = sum of L^(jE) for all integers j from 0 through N-1,
  R(t) = sum(r_j L^j),
  F(t) = c*L^s*(L^k - 1)*I(t) + R(t).

The coefficients r_j of R, listed from degree 0 upward, are

  [9,7,7,-2]

The high-degree polynomial I is specified by the finite geometric-sum formula
above; it is not an ellipsis standing for unknown data.  All exponents are
ordinary nonnegative integer exponents.

Find an integer-coefficient polynomial

  W(t) = sum of w_j L^j for all integers j from 0 through 1

such that there exists some P(t) in Q[t] satisfying the exact identity

  A(t)*P(t) + F(t)*W(t) = H,

where H=E*c*N*g (all four factors are displayed above).

Equivalently, the exact remainder of FW after division by A must be H.  The
checker performs that rational-polynomial reduction; P is not part of the
answer.  The requested representative has degree strictly below deg(A)=
2, so it is unique.

Bounded answer language: put C=4.  Every degree
j=0,...,1 must occur exactly once, in increasing order, and w_j must
equal g*z_j for a nonzero integer z_j in the inclusive range
-(E-1),...,-1,1,...,E-1 (equivalently, w_j is a nonzero multiple of g with
|w_j|<=C).  Use the polynomial rational encoding [w_j,1] for each integer, and
serialize a polynomial term as [[w_j,1],[j]].  Order matters, no degree may
repeat, and the indexing is 0-based.

Give your final answer inside <answer></answer> tags, as one JSON array of the
2 polynomial terms just described.
Example of the exact required shape: <answer>[[[2,1],[0]],[[2,1],[1]]]</answer>
Output nothing else inside the tags.
```

The answer is `[[[-2,1],[0]],[[-4,1],[1]]]`; `verify` returns `(True, "ok")`. Changing the constant coefficient from `-2` to `2` returns `(False, "candidate does not satisfy the Bezout identity modulo A")`. This two-coefficient demo is hand-solvable.

## Difficulty presets

| Preset | `n`-bit exponents | `E` | Scale bits | Coefficients written | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 3 | 2 | 2 | hand example; not shipped |
| easy | 256 | 11 | 4 | 10 | local gates pass; oracle not scored |
| medium | 1024 | 17 | 16 | 16 | local gates pass; oracle not scored |
| hard | 2048 | 29 | 32 | 28 | designated by `SHIPPING_DIFFICULTY`; oracle validation pending |

Raising `n` doubles generic modular-power work without increasing the number of output coefficients. Raising `E` enlarges the structured answer search; order 29 nearly exhausts the 300-operation intended-route cap, so `escalate()` reports `cap_bound` beyond it.

## Gate results

| Gate | Result |
|---|---|
| G1 | 12/12 planted answers verify; 12/12 match independent Euclid; JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | model-style fenced response round-trips; garbage returns `None` |
| G4 | 0/200,000 scale-aware guesses; exact density `1.1239195971453354e-49` |
| G5 | shipping density above; reference algorithm 2,029,486 mean operations, 1.079347 s; demo exact count 1/16 |
| G6 | five attacks, each 0/8; reference Euclid 8/8 as expected; compact route 8/8 |
| G7 | doubling `n` to 4096 bits raises reference work to 4,062,080 operations; G1 still passes with 84 answer atoms |
| G8 | 160/160 affine, quotient-period, common-scale, and `A`-multiple transformations invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | 647 chars (666 worst case), 309 tokens measured with both `o200k_base` and `cl100k_base`, 84 atoms, 288 intended operations: within caps |

## Oracle loop and G9 diagnostics

The required bare loop made no scored attempts because every redraw was an API error:

| Preset | Seed | Model | Outcome | Why |
|---|---:|---|---|---|
| easy | 916408000 | Gemini 3.8 Flash | error | HTTP 403 key total limit |
| easy | 355937719 | GPT-5.6 Terra | error | HTTP 403 key total limit |
| easy | 1238163907 | GPT-5.6 Terra | error | HTTP 403 key total limit |
| easy | 1314863610 | GPT-5.6 Terra | error | HTTP 403 key total limit |

| G9 arm | Solved / scored attempts | Error rows | Verdict |
|---|---:|---:|---|
| bare | 0/0 | 4 | unavailable |
| structural hint | 0/0 | 4 | unavailable |
| placebo hint | 0/0 | 4 | unavailable |

`hinted - placebo` is therefore unavailable, and no conclusion about hint responsiveness is warranted. The structural hint only names the quotient-ring invariant; it does not give the coefficient construction.

The token figure is not the `chars/4` rule of thumb: it is the maximum observed in an exhaustive check of all 756 order-29 shift/automorphism patterns at maximal 32-bit scale under both tokenizers. The larger of their counts is reported.

## Use

```python
from gen_2604_18991 import DIFFICULTY, SHIPPING_DIFFICULTY, make_instance, verify

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=42, **params)
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2604.18991 20
```

After restoring OpenRouter quota, rerun the bare loop from this directory with `python3 ../../scripts/harden.py gen_2604_18991.py`, then run the two G9 copies in their separate scratch directories as documented in the task.

## Caveats

This family is easy for a CAS or any implementation of extended Euclid; that is the declared Track B reference route. It may also be easy for a no-tool solver that immediately recognizes and accurately executes the roots-of-unity coefficient permutation. The guess probability measures only the explicitly bounded, scale-aware prior `w_j=g*z_j` with nonzero `|z_j|<=E-1`; it does not imply computational or model hardness. Wall time is machine-dependent, and the operation count treats an exact rational coefficient operation as one operation even when operands contain thousands of bits.

The attack panel covers magnitude/sign outliers, a left-to-right greedy rule, flat and untransformed ansätze, and 256 scale-aware random restarts. It does not test every symbolic simplifier, Gröbner-basis implementation, or language model. The canonical key normalizes affine coordinates, additions of `A`-multiples, whole-period exponent shifts, and common equation scaling; it does not quotient by every abstract automorphism of the rational polynomial quotient. Most importantly, the current two-vendor hardening pool and the G9 comparison remain unmeasured because of the external 403 quota failure; this directory is ready for a rerun but is not yet valid evidence for a shipped hard instance.
