# arXiv 2304.08749 — k-normality certificate recovery

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | polynomial, expanded and factored |
| Intuition | symmetry: Frobenius permutes a cyclotomic power basis, exposing a sparse cyclic inverse |
| Domain essentiality | native |
| Reduction | none |

## What the family is and why it is trustworthy

The source is Choudhary and Sharma, [*On pairs of r-primitive and k-normal elements with prescribed traces over finite fields*](https://arxiv.org/abs/2304.08749).  The solver receives a cyclotomic field `F_q[Z]/(Phi_ell)`, a normal element `sigma`, and `epsilon`.  It must return the unique monic degree-`k` divisor `f` of `X^n-1` satisfying `epsilon = f circle sigma`, where `circle` is the paper's Frobenius action.  The answer contains both coefficients and the indices of its linear factors.  The checker reconstructs the factors, applies exact modular probes, and finally compares the full cyclic-convolution identity.  It never reads `inst["answer"]`.

This is the paper's native construction, not a graph or finite-field analogue of something else.  Remark 2.5 states that a normal `sigma` and a degree-`k` divisor `f` produce the `k`-normal element `f circle sigma`.  Generation samples `f` first, constructs `epsilon`, and retains `f` as the certificate.  The cyclotomic hypotheses `ell=n+1` prime, `ord_ell(q)=n`, and `q=1 mod n` make `Phi_ell` irreducible, make the nontrivial `ell`-th roots a normal basis, and split `X^n-1` over `F_q`.

## Why Track B

There is an efficient algorithm, so this is not a Track A claim.  Reordering into the Frobenius orbit turns recovery into cyclic deconvolution.  The implemented exact finite-field DFT solves it in `O(n^2)` base-field operations and succeeded 8/8; at shipping `n=58` it averaged **24,652 operations and about 0.001 s** (the exact run time is recorded in `selftest_report.json`).  The compact route notices that the public normal-basis transform has a four-term inverse supported at shifts derived from `q mod (n+1)`.  It computes only the seven requested coefficients in **103 exact operations**.  The benchmark tests whether that symmetry is found and executed without a CAS.

The Introduction supplies the exact `k`-normal definition, and Remark 2.5 is also the result that identifies the easy construction.  The paper's Theorem 1.2 concerns the much broader simultaneous `3`-primitive/`2`-normal, rational-image, and prescribed-trace existence question; this generator deliberately does **not** claim coverage of those extra constraints.

## Worked demo (`seed=7`)

The complete rendered mathematical data are:

```text
Recover a k-normality certificate over a finite field

Let q=13, n=4, ell=n+1=5, and work in
    F = F_q[Z] / (1 + Z + Z^2 + Z^3 + Z^4).

Coordinates [a_1,...,a_4] mean sum(a_j Z^j, j=1..4), modulo 13.
For h(X)=sum h_i X^i, define h circle u = sum h_i u^(13^i).
The supplied normal element and target are
    sigma   = [6, 1, 4, 11]
    epsilon = [7, 12, 10, 2]
The element g=2 generates F_13^*, and omega=8 has order n=4.

Find the unique monic degree-1 divisor f of X^4-1 such that
f circle sigma = epsilon.  Return coefficients [f_0,f_1] and the one
sorted root index s in {0,1,2,3}, where f=X-omega^s.

Give the JSON object inside <answer></answer> tags and nothing else there.
```

The answer is:

```text
<answer>{"coefficients":[1,1],"roots":[2]}</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Replacing the coefficients by `[2,1]` while retaining root index `2` returns `(False, "coefficients do not match the claimed linear factors")`.  A person can solve this demo by trying its four possible linear divisors and applying the displayed Frobenius action.

## Difficulty presets

| Preset | n | k | minimum q | actual q | candidate divisors | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 1 | 0 | 13 | 4 | hand example |
| easy | 58 | 6 | 1,000,000 | 1,009,781 | 40,475,358 | **ships; bare oracle held** |
| medium | 126 | 6 | 100,000,000 | 100,030,897 | 4,925,156,775 | reserve |
| hard | 250 | 6 | 1,000,000,000,000 | 1,000,000,004,501 | 319,195,444,750 | reserve |

Difficulty grows by enlarging the field degree and coefficient height while keeping the answer at degree six.  `escalate()` continues those fixed-answer-length axes.

## Gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed planted checks |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; 40,475,358 candidates |
| G5 | pass | exact valid count 1; 0/200,000 observed; 4,096-restart baseline failed in 0.134 s |
| G6 | pass | four attacks each 0/8; DFT reference 8/8 |
| G7 | pass | `n=520` built and verified; `k=6` stayed fixed |
| G8 | pass | 60/60 relabelling checks; 20/20 unrelated keys distinct |
| G9 | pass | hint still hardened; 88 chars, 13 atoms, 103 intended operations |

## Oracle hardening loop

| Preset | Model | Seed | Solved | Reason |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 2,045,328,130 | no | factor coefficients mismatched |
| easy | xAI Grok 4.6 | 1,201,120,202 | no | Frobenius identity failed |
| easy | Google Gemini 3.1 Pro Preview | 299,695,968 | no | factor coefficients mismatched |

The script-owned verdict is `hardened` at `easy` with zero escalations.

## G9 diagnostic arms

| Arm | Solved / attempts | Notes |
|---|---:|---|
| bare | 0 / 3 | three parsed but invalid witnesses |
| structural hint | 0 / 3 | two parsed invalid witnesses; one length-limited empty response |
| placebo hint | 0 / 3 | two parsed invalid witnesses; one length-limited empty response |

`hinted - placebo = 0.0`.  The structural sentence bought no measured advantage on this sample.  That may mean the remaining exact modular bookkeeping dominates after the symmetry is named, so this run does not isolate intuition as cleanly as a positive hint effect would.  The shipping answer measured 88 characters (conservatively 88 tokens), 13 atomic integers, and the compact route measured 103 exact arithmetic operations.

## Use

```python
from gen_2304_08749 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit fresh shipping instances with:

```bash
bash scripts/emit.sh 2304.08749 20 easy
```

## Caveats

- This is a deliberately honest Track B family: exact DFT, generic linear algebra, or a specialized extended-gcd/circulant solver makes it easy with tools.  The latter faster specialization was not separately benchmarked.
- The `0/200,000` guess result samples uniformly from all monic degree-six divisors, exactly the bounded language.  It measures that prior, not resistance to algebraic recovery; the exact density is `1 / 40,475,358`.
- The four failing attacks cover root-value outliers, first/last-root greed, 256 uniform restarts, and the obvious but wrong power-basis ansatz.  They do not cover every possible side channel, timing attack, or symbolic-algebra strategy.
- The cyclotomic representation and supplied normal anchor are special.  If a solver recognizes the sparse inverse, the problem compresses to 103 operations by design.
- The family covers Remark 2.5's native `k`-normal construction only.  It does not test `r`-primitivity, rational images, prescribed traces, or the numerical sieve of Theorem 1.2.
