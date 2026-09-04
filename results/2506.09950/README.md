# Finite-field Fourier systems (arXiv:2506.09950)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | integer tuple (an ordered field assignment) |
| Intended intuition | change of variables — recognize and invert a finite-field Fourier transform |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is La Scala and Tiwari, [*Oracle-Based Multistep Strategy for Solving Polynomial Systems Over Finite Fields and Algebraic Cryptanalysis of the Aradi Cipher*](https://arxiv.org/abs/2506.09950). Section 2 defines the native MP problem: solve polynomial equations over `GF(q)`, under the paper's at-most-one-solution assumption. This generator hands the solver a uniquely solvable linear subfamily over a prime field,

`sum_j omega^(k*j) x_j = b_k (mod p)`.

The answer is the ordered vector of field residues. Generation is inverse: sample `x` with a private `random.Random(seed)`, evaluate every right-hand side, then shuffle the equation order. No instance is solved during generation. `verify` ignores `inst["answer"]`, checks the field/order data, and substitutes any submitted vector into every equation with exact modular arithmetic.

This is native finite-field polynomial-system coverage, not a graph or SAT reduction. The Fourier structure is a deliberately constructed subfamily of the paper's MP object; it is not the Aradi cipher model and is not claimed to exercise the paper's nonlinear cryptanalysis.

## Why this is Track B

This family is deliberately **not** a computational-hardness claim. Section 2 says that when the reduced Gröbner basis is linear, Algorithm 2.1 (`GBElimLin`) returns the variety; here that specializes to exact row reduction. The included Gauss–Jordan implementation solves 8/8 shipping instances in `O(n^3)`, averaging 0.000202 seconds and performing 4,728 counted field operations. Section 3 also identifies the opposite `d1=0`, all-wild extreme as brute-force enumeration; its exponential cost is not used as evidence here.

The compression is to recognize the coefficient matrix as a finite-field DFT and use its radix-2 inverse. With the supplied inverse twiddles, this takes 112 exact additions/multiplications at shipping `n=16`, versus 4,728 for dense elimination. Both algorithms are efficient on a computer. The benchmark asks whether a no-tool model can identify and accurately execute the short route on nine-digit residues. The bare oracle run confirms why `easy` was not enough: two vendors solved `n=8`; all three scored vendors failed `n=16`.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders the complete hand-scale problem:

```text
Solve an exact polynomial system over a finite field.

Let GF(17) be the field of residues modulo the prime 17; reduce every addition and multiplication modulo 17. There are exactly n=2 unknown field elements x_0,...,x_1. Indices are 0-based, and omega=16 has exact multiplicative order 2 in this field (it is obtained from generator 3).

For every equation row (k,b) below, the required equality is

  sum from j=0 to 1 of omega^(k*j) * x_j = b  (mod 17).

Thus these are 2 explicitly defined linear polynomial equations over GF(17). The row order below has no significance; k identifies a row. The system is promised to have exactly one solution.

Equation rows, each written as: k b
  1 16
  0 8

For exact arithmetic, omega^(-1) mod 17 is 16, n^(-1) mod 17 is 9, and the supplied list omega^(-r) for r=0,...,0 is:
  1

Return the ordered solution [x_0,...,x_1] as a JSON list of exactly 2 base-10 integers. Each entry must be the canonical residue in the inclusive range 0 through 16; order matters and repeated values are allowed.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the required syntax: <answer>[0,0]</answer>
Output nothing else inside the tags.
```

The answer is `[12, 13]`. A person can solve this demo on paper from `x_0+x_1=8` and `x_0-x_1=16 (mod 17)`:

```python
>>> verify(inst, [12, 13])
(True, 'ok')
>>> verify(inst, [13, 13])
(False, 'equation 0 has nonzero residual 1')
```

## Difficulty presets

| Preset | `n` | Prime `p` | Candidate-space bits | Status |
|---|---:|---:|---:|---|
| demo | 2 | 17 | 9 | hand-solvable illustration; never ships |
| easy | 8 | 65,537 | 129 | rejected as shipping: oracle solved 2/3 |
| medium | 16 | 998,244,353 | 479 | **shipping; bare and hinted runs hardened** |
| hard | 32 | 2,013,265,921 | 990 | available; not reached by the bare ladder |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers verified across four presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose + Markdown fence + answer tags round-tripped |
| G4 | pass | 0/200,000 structure-aware uniform field vectors; 479-bit space |
| G5 | pass | shipping density sample 0/200,000; unique by invertibility; demo exact count 1; 256-restart attack 0.002243 s |
| G6 | pass | four attacks each 0/8; row reduction 8/8 in 4,728 operations and 0.000202 s |
| G7 | pass | doubled `n=32` built and verified in 0.000064 s |
| G8 | pass | 2,560/2,560 full affine/order checks, 2,560/2,560 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | hinted run hardened; 160 chars, about 40 tokens, 16 elements, 112 intended operations |

The four failing attacks are: rotate the RHS around its smallest apparent outlier, solve only the matrix diagonal greedily, reverse-and-scale as a one-term hand ansatz, and 256 uniform restarts from the exact declared certificate language. The successful domain-standard algorithm is correctly reported separately because this is Track B.

## Bare oracle loop

| Preset | Model | Seed | Outcome | Why |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 1777118800 | solved | exact witness verified |
| easy | GPT-5.6 Terra | 395585160 | solved | exact witness verified |
| easy | Gemini 3.1 Pro | 556859490 | failed | equation 1 residual 3,911 |
| medium | Grok 4.6 | 2040367445 | error, excluded | 900-second total deadline |
| medium | Gemini 3.1 Pro | 1875965414 | failed | equation 1 residual 481,610,812 |
| medium | Claude Sonnet 5 | 355320861 | failed | empty length-limited response at 32,000 tokens |
| medium | GPT-5.6 Terra | 1002571868 | failed | equation 0 residual 404,550,191 |

The shipping level was decided by three distinct scored vendors. The Grok timeout is preserved in the transcript but did not consume an attempt.

## G9 arms

| Arm | Solved / attempts | Details |
|---|---:|---|
| bare | 0 / 3 | two wrong exact vectors; one length-limited empty response |
| structural hint | 0 / 3 | two wrong exact vectors; one length-limited empty response; hardened |
| placebo hint | 0 / 3 | two wrong exact vectors; one length-limited empty response |

Hinted minus placebo is `0.0`. The one-sentence Fourier/radix-2 hint bought no observed solves, although three trials per arm are too few to estimate a small effect. This suggests the measured obstacle is accurate modular execution after recognizing the change of variables, not only discovering it. Each arm also had two substantive, parsed-but-wrong outcomes, so the result is not solely an output-budget artifact. The shipping answer is 160 characters (about 40 tokens), has 16 atomic elements, and the intended route has 112 exact field operations.

## Use

```python
from gen_2506_09950 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["medium"])
question = render(inst)
candidate = parse_answer("<answer>[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 2506.09950 20 medium
```

The implementation is standard-library-only. `gvlib` is unnecessary because this family uses prime-field modular arithmetic rather than its rational polynomial primitives.

## Caveats

- A CAS, NumPy-like environment, or the included exact row-reduction/FFT code solves every instance quickly. This family must not be cited as evidence that MP, random MQ, Aradi key recovery, or this distribution is computationally hard.
- The DFT construction is an external structured choice inside the paper's native finite-field polynomial-system definition. It deliberately omits Aradi's nonlinear S-box equations and the paper's multistep oracle behavior; coverage is algebraic but narrow.
- G4 samples uniformly from all ordered vectors in `GF(p)^n`, already respecting every stated shape/range rule. Since the transform is invertible, the exact density is `1/p^n`; the observed 0/200,000 does not model a solver that recognizes the FFT, which is why G6 and the oracle runs are separate.
- The oracle evidence includes one 32,000-token empty response in each shipping arm. The other two scored vendors in each arm returned answer vectors that parsed and failed exact substitution, but a larger response budget could still change the rates.
- The attack panel did not run an external Gröbner package, optimized NTT library, or general computer-algebra system; all are expected to succeed and are represented by the successful exact reference algorithm. It also does not estimate performance for tool-enabled language models.
- `canonical_key` normalizes equation order and every affine coordinate relabelling `j -> u*j+t` of the cyclic index group. It intentionally does not quotient by arbitrary `GL(n,p)` changes of basis, which would identify essentially every nonsingular linear system and over-collapse unrelated instances.
- `escalate()` returns `None` after the named ladder because `n>32` would push the intended inverse-transform route over G9's 300-operation cap. A doubled instance still builds and verifies for G7; it is simply not eligible to ship.
