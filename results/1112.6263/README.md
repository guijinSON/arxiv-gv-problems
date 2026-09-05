# arXiv 1112.6263 — rejected Boolean-MQ generator audit

| Profile | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain / object regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | integer tuple: a Boolean common zero |
| Intended intuition | search pruning |
| Domain essentiality | native; no reduction |

## Problem and trust status

The source is Bardet, Faugère, Salvy, and Spaenlehauer, [*On the Complexity of Solving Quadratic Boolean Systems*](https://arxiv.org/abs/1112.6263). Section 1 defines Boolean MQ SAT: given quadratic polynomials over `F_2`, find one common Boolean zero. An instance here gives the coefficients in the paper's reduced square-free monomial basis, packed as exact hexadecimal bit vectors. The solver returns the `n` bits of any common zero. `verify` evaluates every monomial and equation by exact parity, accepts any valid zero, and never reads `inst["answer"]`.

Generation is inverse. It samples a random Boolean vector first, samples every nonconstant coefficient independently, and chooses each constant coefficient to make that vector a zero. A bounded Gray-code filter may reject a coefficient sample containing an unrelated early zero; it never supplies or changes the certificate. Thus G and V are established by construction and direct evaluation.

**This family must not ship.** G1–G8 pass, but G9(c) fails intrinsically: after the claimed Macaulay insight, finding a root is still a large algebraic search. The earlier report of 36 operations counted only writing a root after it had somehow been supplied. The measured degree-3 Macaulay probe spends 55,950 exact row XORs and still does not solve the shipping instance, already far above the 300-operation cap. The paper's successful routes are exhaustive search or the exponential BooleanSolve algorithm. OpenRouter was also unavailable (HTTP 403 `Key limit exceeded`) for all three oracle arms, but that infrastructure failure is not the rejection reason. The implementation is retained as `rejected_gen_1112_6263.py` so this conclusion can be replayed.

## Why the attempted family was Track A

The certificate-producing solver in the paper is not polynomial time. Section 2's `BooleanSolve` combines exhaustive specialization with Boolean Macaulay linear algebra. Theorem 2 gives, for square `m=n` systems satisfying the stated strong-semi-regularity condition, `O(2^(0.841n))` deterministic and expected `O(2^(0.792n))` Las Vegas bounds. At attempted shipping `n=36`, those asymptotic exponent terms are about `1.30e9` and `3.83e8`, respectively; they are context only, not measured operation counts at this small `n`.

Section 4 studies independently uniform random square systems, conjectures that the required strong semi-regularity tends to probability one, and reports it throughout the relevant `gamma<=0.55` experiments except the documented `n=23` rank accident. The generator avoids that size and uses dense square systems. The planted distribution is the random ensemble conditioned and size-biased by a held root, not exactly Section 4's unconditional ensemble, so the theorem is an upper bound rather than an average-case hardness proof. The Track A claim rests additionally on the measured attacks below and remains provisional until the oracle loop completes.

The easy regimes were deliberately avoided. Section 1 says `m<n` can be reduced by random specialization and notes separate faster algorithms for sparse constraint systems; Section 5 says structured systems of low regularity can use a smaller witness degree. The generator uses `m=n`, dense equations, and no low-regularity construction. That choice creates the rejection: it preserves the paper's hard random regime but also removes any compact invariant or change of variables a no-tool solver could exploit. Track B does not rescue this attempted distribution because its compact route is no shorter than its mechanical route.

## Worked demo (`n=4`, seed 7)

This is the complete no-hint rendering:

```text
Find a common Boolean zero of a quadratic system over F_2.

Definitions.
There are n=4 variables x0,...,x3; each variable is exactly 0 or 1.
All addition and multiplication are in F_2, so addition is XOR.
Each polynomial is reduced by x_i^2=x_i and uses this ordered basis:
  bit 0: 1 (the constant monomial);
  bits 1 through 4: x0,x1,...,x3;
  bits 5 through 10: x_i*x_j for i<j, ordered first by i=0,1,... and then by j=i+1,i+2,... .
A hexadecimal row below is a nonnegative integer coefficient bit-vector:
bit p is 1 exactly when basis monomial p occurs in that polynomial.
Leading zeroes only pad every row to the displayed common width.
A row evaluates to the XOR of its selected monomial values.

The 4 equations f_i(x)=0 are (each row has 3 hex digits):
  f_0: 795
  f_1: 134
  f_2: 329
  f_3: 534

Return any common zero; more than one may exist and every valid one is accepted.
The answer must contain exactly 4 bits in variable order x0,...,x3.
The order is fixed, indices are 0-based, and no entries may be omitted.

Give your final answer inside <answer></answer> tags as one JSON array of 0/1 integers.
Format example (not claimed to solve this instance): <answer>[0, 0, 0, 0]</answer>
Output nothing else inside the tags.
```

One answer is `[0,1,0,1]`; `verify(inst,[0,1,0,1])` returns `(True,"ok")`. Dropping its last bit returns `(False,"answer must contain exactly 4 bits (got 3)")`. Exhaustive enumeration finds two valid demo answers. A person can solve this 16-candidate illustration by hand.

## Difficulty presets

| Preset | `n=m` | Gray-filter budget | Role |
|---|---:|---:|---|
| demo | 4 | 0 | hand-solvable illustration |
| **easy** | **36** | **16,384** | attempted shipping preset; rejected by G9(c) |
| medium | 52 | 32,768 | reserve rung |
| hard | 68 | 65,536 | reserve rung |

`escalate` first doubles the bounded attack budget at fixed `n`; only after that axis is exhausted does it increase `n`, returning `"cap_bound"` at 192 bits.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed roots verified and JSON-round-tripped |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged/fenced/prose round-trip; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 uniform legal vectors; space `2^36` (7.369 s in the retained run) |
| G5 | pass | shipping sampled density 0/200,000; degree-3 baseline failed after 55,950 row XORs in 1.583 s; demo count 2 |
| G6 | pass | four attacks each 0/8; 448,671 domain-attack row XORs total in 14.691 s |
| G7 | pass | doubled `n=72` instance built and verified; fixed-length budget escalation works |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **fail** | answer size passes (73 chars, 19 estimated tokens, 36 atoms), but the measured route lower bound is 55,950 exact row XORs without a solution, over the 300-operation cap; no scored oracle calls |

The G6 attacks are constant/linear coefficient correlation, steepest bit-flip greedy search, 512 uniform restarts, and degree-3 Boolean Macaulay/XL linearization. The last is a bounded implementation of the paper's domain-standard linear-algebra route; a full higher-degree BooleanSolve, industrial SAT/SMT encoding, and Gröbner-basis package were not run. Passing this panel does not cure G9(c).

## Oracle loop and G9 arms

| Arm | Scored solved / attempts | Script outcome |
|---|---:|---|
| bare | 0 / 0 | four HTTP 403 retries; pool unreachable |
| structural hint | 0 / 0 | four HTTP 403 retries; pool unreachable |
| placebo hint | 0 / 0 | four HTTP 403 retries; pool unreachable |

There is no meaningful hinted-minus-placebo estimate. The recorded numeric difference `0.0` is only the arithmetic result of two empty denominators guarded in code, not evidence that the hint helped or failed to help. The structural sentence names the paper's Macaulay-pruning invariant without giving a procedure. The answer itself is 73 serialized characters, 19 estimated tokens, and 36 atomic elements. The honest intended-route entry is a lower bound of 55,950 exact row XORs from the failed degree-3 probe; a complete route costs more.

## Use

```python
from rejected_gen_1112_6263 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("<answer>[0, 1]</answer>")
print(verify(inst, candidate))
assert verify(inst, inst["answer"])[0]
```

This rejected module is for audit only and must not be emitted. If the family is redesigned and passes every gate, the normal command from the repository root would be:

```bash
bash scripts/emit.sh 1112.6263
```

## Caveats

- Theorem 2 is an algorithmic upper bound under strong semi-regularity, not a lower bound and not an average-case theorem for this planted distribution. Worst-case NP-completeness alone would not justify Track A.
- `0/200,000` is an observed rate under a uniform prior over all Boolean vectors. It does not upper-bound a learned, algebraic, or construction-aware prior; with zero hits it also does not statistically establish probability below `1e-6`.
- Dense hexadecimal coefficient rows are exact and compact, but unaided decoding creates additional no-tool difficulty. More importantly, the family has no known short human solution route at all. This is the decisive G9(c) failure.
- The construction excludes the first `attack_budget` Gray words as planted roots and rejects coefficient samples having an accidental root there. That is a documented, tiny bias and could support a stronger distribution-aware attack than those tested.
- The canonical key is exactly invariant under equation reordering and variable-name permutations. It is only a cheap collision-resistant invariant, not a canonical form for arbitrary affine changes of Boolean variables or invertible row combinations.
- No full BooleanSolve implementation, degree-4+ Macaulay elimination, industrial SAT/SMT solver, Gröbner package, or cross-instance statistical attack was run.
- The external evidence is incomplete for an infrastructure reason, but restoring the key would not fix the intrinsic route-cost failure. A future design would need a genuine sub-300-operation structural route, then fresh bare/hinted/placebo runs.
