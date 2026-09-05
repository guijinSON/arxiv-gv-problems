# Brace-derived Yang--Baxter evaluations (arXiv:1507.02602)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | polynomial — two monic affine polynomials over `GF(p)` |
| Intended intuition | decomposition — a short quotient plus a residual factor vanishing at two characters |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Tatiana Gateva-Ivanova, [*Set-theoretic solutions of the Yang-Baxter equation, Braces, and Symmetric groups*](https://arxiv.org/abs/1507.02602). An instance hands the solver the paper's own algebraic objects: a finite radical ring, the two-sided left brace `x circle y = x+y+x*y`, its canonical Yang--Baxter map, and two vectors expressed as characters of a circulant bilinear form. The solver must return the two monic affine coordinate polynomials `P(T)=alpha+T` and `Q(T)=beta+T` describing `r(a,b)`.

The construction is theorem-backed and compositional. For the all-one vector `1`, define `x*y=(x^T C y)1`, where the circulant matrix `C` has zero row and column sums. Then every triple product is zero, so `circle` is a radical-ring brace. Section 3, Theorem 3.6 turns every left brace into a non-degenerate involutive Yang--Baxter solution. The generator composes the circulant symbol as

`f(X) = (X-1)[g(X) + X^L(X-omega)(X-omega^-1)h(X)]`.

It samples `g` and `h`, carries `f(omega)=(omega-1)g(omega)` and its inverse-root analogue through that identity, and therefore knows the answer without solving the emitted dense instance. The checker independently evaluates all 512 displayed coefficients by exact Horner arithmetic, reconstructs the brace actions, and compares the candidate constants. It never reads `inst["answer"]`.

## Why this is Track B

This paper cannot support a Track A claim for this task. Definition 3.4 and Proposition 3.5 give the brace action explicitly, and Theorem 3.6 constructs its braiding operator. For the circulant presentation, the domain-standard algorithm recognizes the two character eigenvectors and evaluates the full symbol at `omega` and `omega^-1`. That is an exact `O(n)` algorithm and succeeds on every instance, as expected.

At the shipping preset `n=512`, two full Horner evaluations take 2,057 counted modular operations and averaged roughly 0.0001 seconds over eight seeds. The compact route reconstructs the first `L=20` quotient coefficients and evaluates only those; its bound is 109 exact operations. This is a real compression, but not computational hardness: Python solves the instance immediately. Without a sandbox or CAS, however, the mechanical route requires hundreds of exact 64-bit modular multiplications, and even the compact route requires twenty-term modular evaluations. The oracle pool did not complete these correctly, including when told the vanishing-factor invariant.

The paper's easy cases also matter. Section 2's trivial solution is the flip `r(x,y)=(y,x)`; in this family that corresponds to both correction constants vanishing. Section 3 itself supplies the general efficient brace construction, and the text before Theorem 3.6 notes the direct radical-ring route. The generator uses a 64-bit field and a dense residual rather than the tiny or sparse regimes; `demo` alone uses a small field so it can be checked by hand.

## Worked demo

`make_instance(seed=0, n=8, window=2, field="toy")` renders in full as follows:

```text
Evaluate a brace-derived set-theoretic Yang--Baxter map.

All scalar arithmetic is in the finite field GF(p), represented by the least
nonnegative residues 0,...,p-1, where

  p = 17.

Vectors have n=8 coordinates indexed 0,...,7.  Vector addition and
negation are coordinatewise modulo p.  Let 1 denote the all-one vector.  The
circulant matrix C is defined, with indices reduced modulo n, by

  C[i,j] = c[(j-i) mod n].

Define a bilinear product and a second group operation on GF(p)^n by

  x * y       = (x^T C y) 1,
  x circle y  = x + y + x*y.

The displayed coefficients satisfy sum(c[k])=0 modulo p.  Consequently C1=0
and 1^T C=0, every triple product under * is zero, and circle makes this
radical ring into a two-sided left brace.

For a left brace define lambda_x(y)=x circle y-x.  Its canonical set-theoretic
Yang--Baxter map is

  r(x,y) = ( lambda_x(y), lambda_(lambda_x(y))^(-1)(x) ),

where the inverse superscript means the inverse of the additive automorphism
lambda_z, not a scalar reciprocal.  This r is bijective, non-degenerate,
involutive, and satisfies r12 r23 r12 = r23 r12 r23.

The two input vectors are given symbolically by

  a_i = 14 * omega^(-i),
  b_i = 2 * omega^i,

where

  omega          = 2,
  omega^(-1)     = 9,
  omega^n        = 1, and omega^(n/2) != 1.

The circulant symbol is f(X)=sum from k=0 to n-1 of c[k]X^k.  Its coefficients,
in increasing degree order, are:

  c[0:6] = 9 9 1 15 6 13
  c[6:8] = 6 9

A public low-degree window parameter for this instance is L=2.

There are unique monic affine polynomials P(T)=alpha+T and Q(T)=beta+T over
GF(p) such that, coordinate by coordinate,

  r(a,b) = ( (P(b_i))_i, (Q(a_i))_i ).

Find P and Q.  Encode each polynomial by its coefficient list [constant,linear]
in increasing degree order.  Thus both lists have exactly two integer entries,
their second entry must be 1, and alpha and beta must be their canonical
representatives in the inclusive range 0,...,p-1.  Order matters and no
coefficient may be omitted.

Give your final answer inside <answer></answer> tags, as exactly one JSON object
with keys "left" and "right" and no other keys.
Example: <answer>{"left":[3,1],"right":[5,1]}</answer>
Output nothing else inside the tags.
```

Here `f(2)=6`, `f(9)=9`, and `n*a_scale*b_scale=3 (mod 17)`, so the answer is `{"left":[1,1],"right":[7,1]}`. A person can do these two eight-term evaluations on paper; that is why this is the demo rather than a shipping level.

```python
>>> verify(inst, {"left": [1, 1], "right": [7, 1]})
(True, 'ok')
>>> verify(inst, {"left": [2, 1], "right": [7, 1]})
(False, 'left constant does not match the brace left action')
```

## Difficulty presets

| Preset | `n` | Low window `L` | Render chars, seed 0 | Reference ops | Compact ops | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 2 | 2,231 | 41 | 19 | hand-solvable illustration |
| easy | 512 | 20 | 13,962 | 2,057 | 109 | **shipping; bare and hinted held** |
| medium | 1,024 | 20 | 25,713 | 4,105 | 109 | available, not reached |
| hard | 2,048 | 20 | 49,441 | 8,201 | 109 | available, not reached |

No preset was rejected. The bare hardening loop held at its first evaluated rung, `easy`, so the harness did not escalate.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates; 24/24 direct involution and 24/24 braid checks on toy-field triples; both moduli prime; answers JSON-round-trip |
| G2 | pass | drop, swap, duplicate, empty, and range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact density about `2.94e-39` in a 128-bit language |
| G5 | pass | exactly one shipping answer; demo brute force also found one; 256-restart baseline averaged about 0.057 s |
| G6 | pass | five attacks each 0/8; full Horner reference and compact route each 8/8 |
| G7 | pass | doubled `n=1,024` built and verified; answer remained four atomic coefficients while reference work doubled |
| G8 | pass | 140/140 affine cyclic relabellings invariant, 140/140 carried witnesses valid, 20/20 unrelated keys distinct |
| G9 | pass | hinted verdict `hardened`; 65 answer characters, 17 estimated tokens, 4 atoms, 109 intended operations |

The five failing G6 attacks were coefficient-magnitude outlier selection, the flip-map ansatz, a constant-term-only greedy rule, an unjustified eight-coefficient Horner truncation, and 256 uniform random restarts. The successful full Horner computation is correctly reported as the Track B reference algorithm, not disguised as a failing attack.

## Bare oracle loop

| Model | Preset | Seed | Solved | Recorded outcome |
|---|---|---:|---:|---|
| OpenAI GPT-5.6 Terra | easy | 1726508035 | no | parsed flip polynomials; left constant wrong |
| Google Gemini 3.1 Pro Preview | easy | 1346558200 | no | derived the character formula but returned the flip; left constant wrong |
| Anthropic Claude Sonnet 5 | easy | 1881783991 | no | consumed the 32,000-token reasoning budget and emitted no answer |

The script-owned `.meta.json` records `verdict: hardened`, zero escalations, and `easy` as the shipping preset.

## G9 arms

| Arm | Solved / attempts | Observation |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; one model confused the vanishing residual with the whole symbol |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. In this three-sample diagnostic the structural sentence bought no solves. That does not show the decomposition is irrelevant: the hinted responses reasoned further into it, but still failed the exact modular evaluation. It does show that observed difficulty contains arithmetic execution as well as discovery of the decomposition. The shipping answer is 65 characters (about 17 tokens), has four atomic coefficients, and the intended compact route is bounded by 109 exact operations.

## Use

```python
from gen_1507_02602 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>{"left":[0,1],"right":[0,1]}</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 1507.02602 20 easy
```

## Caveats

- This is emphatically Track B. A few lines of Python, a CAS, or any exact finite-field package solve every instance in a fraction of a millisecond. It is not a complexity-theoretic hardness claim about Yang--Baxter solutions.
- The benchmark covers evaluation of the brace-derived braiding from Section 3, not the paper's later classification, retraction, solvability, or multipermutation-level theorems.
- G4 samples uniformly from exactly the two free polynomial constants after enforcing the obvious monic shape. Its `1/p^2` density says random guessing is futile; it says nothing about structured guesses. G6 and the oracle arms probe only a small selection of those.
- The hint result is based on three providers, and each arm contained one Claude call that emitted nothing after using its full reasoning budget. The transcripts preserve this; a larger token budget could change the empirical result.
- I did not test Gröbner-basis synthesis, generic brace-isomorphism software, FFT/NTT evaluation, or external CAS packages as failing attacks. They are tool-enabled methods expected to succeed; full exact Horner evaluation is the measured reference.
- `canonical_key` is complete for every affine cyclic-coordinate relabelling `i -> u*i+s` with `gcd(u,n)=1`; the audit includes translations, two nontrivial automorphisms, reflection, and their compositions. It is not a canonical form for arbitrary changes of basis of a finite radical ring.
- The dense residual is random subject to the planted factor identity. Extremely rare algebraic coincidences can make one correction constant zero, although neither the certificate's uniqueness nor exact verification is affected. The audited seeds had no such degeneracy.
- The module uses only the Python standard library. The Goldilocks modulus and the toy modulus are rechecked by deterministic 64-bit Miller--Rabin in `selftest`; no floating-point arithmetic appears in generation or verification.
