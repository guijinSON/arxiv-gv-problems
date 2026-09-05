# Affine-hidden subtrace coefficients

| profile | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | polynomial identity |
| certificate form | polynomial |
| intended intuition | change of variables |
| domain essentiality | native |
| reduction | none |

This generator uses Section 1 and Lemma 1.1 of Chatterjee, Kapetanakis,
Sharma, and Tiwari, [“Existence of primitive normal pairs over finite fields
with prescribed subtrace”](https://arxiv.org/abs/2405.11463). It hands the
solver a native finite extension, an irreducible binomial for a generator
`eta`, and a chain of invertible affine coordinate changes from `epsilon` to
`eta`. The solver must return the three leading terms of the monic minimal
polynomial of `epsilon`; its degree-`n-2` coefficient is exactly the paper's
subtrace. The checker recomposes the maps and compares both free coefficients
with exact arithmetic modulo `q`.

Trust status: **shipping-ready at `easy`**. All local gates pass, and the
script-owned bare oracle loop held `easy` at 0/3. This is native coverage of the
paper's subtrace/minimal-polynomial machinery, not of its headline search for a
primitive-normal pair.

## Construction and Track B claim

Section 1 defines subtrace as the sum of pairwise products of distinct
Frobenius conjugates and identifies it with the `X^(n-2)` minimal-polynomial
coefficient. Lemma 1.1 gives the equivalent trace identity. Theorem 3.1 and the
Section 4 sieves prove positivity of a character-sum count; they do not output a
pair or prove search hardness. Section 5 says SageMath performed the significant
computations, and Theorem 5.7 leaves eleven possible `(q,n)` exceptions.

The generator fixes the prime `q=7,340,033=7*2^20+1`. Since `3` has order
`q-1`, the executable binomial criterion proves `Y^n-3` irreducible for each
supported power of two `8 <= n <= 2^20`. If the displayed affine chain composes
to `eta=U*epsilon+V`, then

```text
M(X) = U^(-n) ((U X + V)^n - 3),
c1   = n (V/U),
c2   = binom(n,2) (V/U)^2  in F_q.
```

These identities manufacture the witness; the generator never expands or
solves its instance. The Track B reference algorithm densely expands all
`n+1` binomial coefficients in `O(n+k)` exact operations. At shipping
`n=4096,k=8`, it materialized 4,097 coefficients in 20,508 counted operations,
averaging 0.000754 seconds over eight runs. The compact route composes the eight
maps first and uses at most 60 exact operations. A tool can run either route;
the benchmark tests whether a no-tool solver recognizes and executes the
compressed one.

The easy regime to avoid is explicit in Section 1: if `M(X)` itself were
supplied, subtrace would be a coefficient lookup. The affine chain keeps the
field object exact while withholding that already-expanded polynomial.

## Worked demo

For `make_instance(n=8, chain_length=2, coefficient_cap=1, seed=0)`, the full
rendered problem is:

```text
Leading minimal-polynomial terms after finite-field coordinate changes

All scalar arithmetic is in the prime field F_q with q=7340033; write
field elements as their unique integer residues from 0 through 7340032.
Let n=8.  The polynomial Y^8-3 is irreducible over F_q,
and eta denotes its residue class in the extension F_q[Y]/(Y^8-3).

Starting with z=epsilon, apply the following affine maps in the exact
listed order.  A row `a b` means replace z by a*z+b in the extension.
After the last row, the resulting z equals eta.

AFFINE_MAPS (a b):
1 1
1 1
END_AFFINE_MAPS

Let M(X) be the monic minimal polynomial of epsilon over F_q:

  M(X) = X^n + c1*X^(n-1) + c2*X^(n-2) + lower-degree terms.

Find its three displayed leading terms.  In the paper's notation,
Tr(epsilon)=-c1 and STr(epsilon)=c2, where the subtrace is the sum
of the products of every two distinct Frobenius conjugates.

Return exactly three terms in descending degree as JSON.  Each term is
[coefficient,[exponent]]; coefficients must be canonical residues in
0..q-1, exponents are ordinary integers, order matters, and no term may
be repeated.  Thus the required shape is
[[1,[n]],[c1,[n-1]],[c2,[n-2]]].

Give your final answer inside <answer></answer> tags in that exact JSON format.
Format-only example: <answer>[[1,[8]],[0,[7]],[0,[6]]]</answer>
Output nothing else inside the tags.
```

The maps give `eta=epsilon+2`, hence the answer is
`<answer>[[1,[8]],[16,[7]],[112,[6]]]</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the last term
returns `(False, "too few terms: expected 3, got 2")`. This demo is genuinely
hand-solvable: it needs one affine composition and two small binomial
coefficients.

## Difficulty and gates

| preset | degree `n` | maps | dense operations | compact operations | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 2 | 50 | 42 | hand example; skipped by hardening |
| easy | 4,096 | 8 | 20,508 | 60 | **ships; bare oracle held 0/3** |
| medium | 65,536 | 16 | 327,732 | 84 | available, not reached |
| hard | 262,144 | 32 | 1,310,820 | 132 | available, not reached |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 tagged prose/fenced answers round-trip; garbage returns `None` |
| G4 | 0/200,000; exact structure-aware probability `1/7,340,033` |
| G5 | unique answer; 4,097 coefficients and 20,508 operations in 0.000800 s |
| G6 | six attacks all 0/8; dense reference solves 8/8 as Track B expects |
| G7 | doubled degree 8,192 verifies; answer remains six atoms |
| G8 | 20/20 symmetry invariance, 20/20 carried witnesses, 20 distinct keys |
| G9(c) | 46 characters, about 12 tokens, six atoms, 60 intended operations |

## Oracle loop and G9 diagnostics

The bare loop was run by `scripts/harden.py` with its configured two-vendor
pool. Every reply parsed; each failure below is an exact coefficient mismatch.

| arm | model | seed | solved |
|---|---|---:|---:|
| bare | GPT-5.6 Terra | 292818736 | no |
| bare | Gemini 3.8 Flash | 1508853251 | no |
| bare | Gemini 3.8 Flash | 1467290579 | no |
| structural | Gemini 3.8 Flash | 707587406 | yes |
| structural | GPT-5.6 Terra | 872868003 | no |
| structural | GPT-5.6 Terra | 294570871 | no |
| placebo | GPT-5.6 Terra | 292818736 | no |
| placebo | Gemini 3.8 Flash | 1508853251 | no |
| placebo | Gemini 3.8 Flash | 1467290579 | no |

The arm totals are bare `0/3`, hinted `1/3`, and placebo `0/3`, so
`hinted - placebo = 1/3`. At this small sample size, the result is consistent
with the declared change-of-variables insight helping, but it is not a precise
effect estimate. The hint names only the invariant; it does not give the
coefficient formulas.

## Use

```python
from gen_2405_11463 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2405.11463 20 easy
```

## Caveats

- This family intentionally does not claim coverage of finding primitive-normal
  pairs. The paper's character-sum argument proves abundance rather than a hard
  witness-search distribution, and a structure-aware sampler would undermine
  the proposed planted-search family.
- The exact G4 probability grants monicity, term count, exponent order,
  coefficient ranges, and the freely deducible relation
  `c2=((n-1)/(2n))*c1^2`, then samples the one remaining `F_q` coefficient
  uniformly. It does not model a solver that has partially composed the chain.
- Dense expansion is a transparent mechanical baseline, not the fastest
  specialized implementation for this exact prompt. Truncated symbolic
  substitution or affine-pair composition is the intended compact attack and
  will solve the family with tools.
- The failing attacks cover commutative collapse, ignored scalings, last-map and
  largest-translation guesses, reverse composition, and 256 random restarts.
  They do not cover every CAS simplifier or arithmetic-language-model strategy.
- The field modulus is fixed and supported degrees are powers of two through
  `2^20`; diversity comes from the affine presentation. The canonical key is
  complete for generated chain refactorings and root scalings, not for every
  possible presentation isomorphism of an arbitrary finite field.
- The current repository harness used two configured vendors, despite the older
  task prose describing four. The transcripts preserve the actual model pool.
