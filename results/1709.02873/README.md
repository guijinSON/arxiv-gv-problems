# Exact determinant certificates from recursive quaternary Hadamard matrices

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | continuous analytic, represented exactly in `Q(s)`, `s²=-3` |
| Computational core | linear algebra |
| Certificate | algebraic number: primitive linear minimal polynomial plus rational isolating interval |
| Intended intuition | symmetry — character eigenvalues split into zero, quadratic-residue, and nonresidue types |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

The source is Fender, Kharaghani, and Suda, [*On a class of quaternary complex Hadamard matrices*](https://arxiv.org/abs/1709.02873).  Section 3, equation (3.1), recursively defines the paper's matrices `J_m,A_m`; Section 3.1 proves that the Paley/Jacobsthal instance is multicirculant; and Proposition 4.1 places it in a tensor association scheme.  An instance applies exact norm-one diagonal phases and affine row/column relabellings to `K=J_m+sA_m`, where `s²=-q`, and asks for the integer `T=S Re(det M)`, with `S` clearing the displayed phase denominators.  The answer is `[-T,1]` plus the canonical open interval `(T-1/2,T+1/2)`.  Verification recomputes `T` in exact integer arithmetic, checks polynomial vanishing, primitivity, the bound, and the rational endpoints; it never reads `inst["answer"]`.

## Why this is Track B

This paper does **not** support a Track A claim: equation (3.1) explicitly constructs the Hadamard matrix, and Section 4 gives a mechanical tensor eigenspace description.  The reference algorithm evaluates all `3^m` characters, performs `m` recurrence updates for each, and multiplies their eigenvalues.  It is `O(m3^m)` and, at the shipping order 243, takes 1,703 exact quadratic-ring steps; one measured base evaluation took about 0.0005 seconds on this machine.  It therefore succeeds 8/8, as expected, but is not a realistic unaided hand calculation.

The compact route pairs the equally numerous residue and nonresidue character types.  For `N=q^m` it gives

```text
det(K) = (-1)^ceil(m/2) q^floor(mN/2) (q+1)^((N-1)/2)
         * (q+s)  if m is odd, or * (1+s) if m is even.
```

Affine permutation parity and the short product of phase numerators finish the calculation.  The shipping route is estimated at 71 exact operations.  The easy regimes deliberately avoided as benchmark claims are individual-entry construction by equation (3.1) and complete spectral evaluation by Section 4.  This family tests recognition of the spectrum symmetry, not asymptotic intractability.

## Worked demo (`seed=9`)

Here is `render(make_instance(seed=9, **DIFFICULTY["demo"]))` in full:

```text
Exact determinant certificate for a recursive quaternary matrix

All arithmetic is exact.  Let q=3, m=1, N=q^m=3, and let s denote
the complex number i*sqrt(q), so s^2=-q and conjugation sends s to -s.

Rows and columns are indexed by vectors in F_q^m, represented as length-m
lists with entries 0,...,q-1.  Define the q by q Jacobsthal matrix Q by
Q[u,v]=chi(u-v), where chi(0)=0, chi(t)=1 when nonzero t is a square modulo q,
and chi(t)=-1 otherwise.  Let J_q be the all-ones q by q matrix and I_q the
identity.  Starting with the 1 by 1 matrices J_0=A_0=[1], recursively define

  J_r = J_q tensor A_(r-1)
  A_r = I_q tensor J_(r-1) + Q tensor A_(r-1).

Set K=J_m+s*A_m.  (The paper's unit Hadamard matrix is K/sqrt(q+1).)

An affine coordinate map f below means
  f(x)[j] = scale[j]*x[perm[j]] + shift[j] (mod q),
with 0-based j and 0-based coordinates.  The row and column maps are

  row map:    {"perm":[0],"scale":[2],"shift":[2]}
  column map: {"perm":[0],"scale":[2],"shift":[1]}

Begin with row multipliers r(x)=1 and column multipliers c(y)=1.  Apply every
listed phase: multiply r(position) or c(position), according to its side, by
the displayed exact number.  Repeated positions are allowed and their factors
multiply.  Every displayed phase (a+b*s)/d has norm one.

Phase list:
  1. row [0]: (1 + (-4)*s)/7

The exact N by N matrix in this problem is

  M[x,y] = r(x) * K[row_map(x), column_map(y)] * c(y).

Let S be the product of the positive denominators d in the phase list.  Your
target is the integer

  T = S * Re(det(M)).

Return an algebraic-number certificate for T.  The certificate language is:

* `minpoly` is the primitive degree-one integer polynomial [c0,c1], in
  ascending coefficient order, with c1>0 and root T.  Thus c0+c1*T=0.
* `interval` is the canonical OPEN isolating interval
  [[2*T-1,2],[2*T+1,2]], with each rational encoded [numerator,denominator].
* The promised bound is -B <= T <= B, inclusively, for
  B=936.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys `minpoly` and `interval`.
Example: <answer>{"minpoly":[0,1],"interval":[[-1,2],[1,2]]}</answer>
Output nothing else inside the tags.
```

The planted answer is

```json
{"minpoly":[180,1],"interval":[[-361,2],[-359,2]]}
```

`verify(inst, answer)` returns `(True, "ok")`.  Changing the minpoly to `[181,1]` returns `(False, "minimal polynomial does not vanish at the target")`.  This order-3 demo is genuinely hand-solvable: write the two 3×3 matrices, take one determinant, and apply the two permutation signs and one phase.

## Difficulty ladder

| Preset | Depth `m` | Matrix order | Phase terms | Phase parameter bound | Status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 3 | 1 | 5 | hand example; skipped by hardener |
| easy | 5 | 243 | 2 | 20 | **ships; bare and hinted both hardened** |
| medium | 5 | 243 | 4 | 35 | not reached |
| hard | 5 | 243 | 6 | 50 | not reached |

The latter rungs grow phase entropy and exact work without changing the six-atom answer shape.  Increasing `n` still grows the matrix order exponentially; the G7 check doubles depth 5 to 10 (order 59,049).  Depth 6 would exceed the repeated-integer answer-character budget, so `escalate()` reports `cap_bound` after the fixed-shape phase axes have been used.

## Gate results

| Gate | Result |
|---|---|
| G1 | 14/14 planted answers and independent tensor-spectrum cross-checks pass; includes `q=7,11` checks |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered from prose and Markdown |
| G4 | 0/200,000 structure-aware bounded-language guesses; shipping language has more than 2^1200 candidates |
| G5 | shipping sampled density 0/200,000; demo exact count 1/1,873; reference base run about 0.0005 s / 1,703 steps |
| G6 | five attacks, each 0/8; reference tensor-character algorithm 8/8 as expected |
| G7 | depth 10/order 59,049 builds and verifies |
| G8 | 60/60 affine/reordering invariance checks, 60/60 carried-witness checks, 20/20 unrelated keys distinct |
| G9(b,c) | hinted verdict hardened; 1,141 chars, about 286 tokens, 6 atoms, 71 intended operations |

## Oracle loop

| Arm | Model | Seed | Outcome | Reason |
|---|---|---:|---|---|
| bare | OpenAI GPT-5.6 Terra | 14,256,185 | failed | polynomial did not vanish at target |
| bare | Gemini 3.1 Pro Preview | 1,114,354,087 | failed | polynomial did not vanish at target |
| bare | Claude Sonnet 5 | 1,648,906,412 | failed | exhausted 32k response budget with no answer |
| hinted | Claude Sonnet 5 | 1,874,949,160 | failed | exhausted 32k response budget with no answer |
| hinted | Gemini 3.1 Pro Preview | 918,365,142 | failed | non-integer minpoly coefficients |
| hinted | OpenAI GPT-5.6 Terra | 1,465,299,392 | failed | non-integer minpoly coefficients |

The bare hardener verdict is `hardened` at `easy`.  The hinted arm is also `hardened`.  Its transcript additionally records one Grok timeout as an error and redraw; that error is not counted as a failed solve.

## G9 arms

| Arm | Solved / completed attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping prompt held |
| structural hint | 0/3 | polarity-flipped gate passes |
| placebo | 0/0 | unmeasured: one Grok timeout exhausted the remaining OpenRouter key limit; subsequent redraws returned HTTP 403 |

Because the placebo arm has no completed attempts, `hinted - placebo` is recorded as `null`; no diagnostic conclusion about the hint's incremental value is claimed.  The error-only transcript is retained in `g9_placebo_transcript.jsonl` rather than misreported as oracle failure.  This does not alter G9(b), which has its own completed 0/3 hinted run, or G9(c), whose measured caps are 1,141 characters, about 286 tokens, six atoms, and 71 operations.

## Use

```python
from gen_1709_02873 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=9, **DIFFICULTY["demo"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
assert parse_answer("prose <answer>" + __import__("json").dumps(inst["answer"])
                    + "</answer>") == inst["answer"]
```

From the repository root, emit examples with `bash scripts/emit.sh 1709.02873 20`.

## Caveats

This is a no-tool compression benchmark, not a hardness result: a CAS, an FFT/character implementation, or the included reference algorithm makes it easy in milliseconds.  The random-guess result samples integers uniformly from the explicitly bounded certificate language; it establishes sparsity under that prior, not resistance to an informed algebraic guess.  The panel did not test a general-purpose CAS or arbitrary symbolic determinant simplifiers, because those are precisely the out-of-context tools Track B permits to succeed.  Two of the three completed bare failures and two of the three hinted failures produced substantive but invalid certificates; the other completed attempt in each arm exhausted its response budget, so the oracle evidence is weaker than six substantive wrong answers.  The placebo comparison is unavailable because the external key limit was exhausted, as documented above.  Finally, `canonical_key` is the strongest cheap task invariant—`q,m`, total affine sign, and normalized phase-numerator product—so it intentionally identifies differently positioned matrices that ask the same determinant computation.
