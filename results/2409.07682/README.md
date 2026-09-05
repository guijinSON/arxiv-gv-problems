# Sparse Walsh spectracone certificates (arXiv:2409.07682)

> **Status: rejected on H/Track B.**  The local construction and verification gates
> pass, but the required bare oracle loop solved every admissible rung.  The complete
> implementation is retained as `rejected_gen_2409_07682.py`; no generator ships.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate form | exact symbolic (a sparse rational row-cone decomposition) |
| Intended intuition | change of variables — undo two relabellings and inspect Walsh characters at binary unit columns |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Johnson and Paparella, [*Perron similarities and the nonnegative
inverse eigenvalue problem*](https://arxiv.org/abs/2409.07682).  Section 4.4,
Theorem 4.29 proves that a Walsh matrix is an ideal Perron similarity: its
spectracone is exactly the conical hull of its rows.  Equation (4.7) identifies
the associated nonnegative Klein matrices.  An instance supplies a Walsh matrix
implicitly, after exact row and column permutations, and a rational spectral
vector.  The solver returns seven rows and their published positive rational
coefficients whose exact sum is that vector.

Generation samples the sparse coefficient vector first and expands it, so it
never solves the published inverse problem.  `verify` validates the bounded
rational syntax, expands every claimed Walsh row using integer parity, and
compares all spectral coordinates exactly.  It never reads `inst["answer"]`.

## Why this is Track B

This paper does not support a Track A claim for this distribution.  Section 7,
Theorem 7.4 gives an explicit Fourier feasibility test for circulant spectra;
the Walsh analogue in Section 4.4 likewise yields the coefficients by a fast
Walsh–Hadamard inversion.  The reference implementation is
`O(n(log n + rounds))`, solves 8/8 local shipping instances as expected, and at
`n=1024` averaged 0.013314 seconds and 13,319 counted exact operations.

The compressed route exploits characters rather than transforming the whole
vector.  After inverting the displayed affine row and column permutations, the
value at canonical column `2^i` is the published signed-weight sum whose signs
are precisely bit `i` of the seven hidden row codes.  The supplied exact
signed-sum table decodes those bits.  This takes at most 161 exact arithmetic
operations at the provisional shipping preset.  The 83-fold operation gap is
the Track B claim; Python still solves the instance essentially instantly.

## Worked demo

`make_instance(seed=0, n=16, terms=3, rounds=1, weight_bits=6)` renders in full
as follows:

```text
Find a sparse certificate for a spectrum in a Walsh Perron spectracone.

All indices are 0-based.  Let d=4 and n=16=2^4.  For integers u,v in
0,...,n-1, define the Walsh entry

    H[u,v] = (-1)^parity(u AND v),

where AND is bitwise AND on the 4-bit binary expansions and parity is 0 for an
even number of 1-bits and 1 for an odd number.

An affine relabelling operation (a,b) sends z to (a*z+b) modulo n.  Apply the
operations in the displayed left-to-right order.  Every multiplier a is odd,
so every operation is a permutation.

Row-code operations R: (13,13)
Column-code operations C: (1,8)

The relabelled Walsh matrix S has

    S[r,c] = H[R(r), C(c)].

For an invertible matrix S, its spectracone is the set of vectors lambda for
which S*diag(lambda)*S^(-1) is a real matrix whose entries are all nonnegative;
diag(lambda) means the diagonal matrix with diagonal lambda.  A Perron
similarity is an invertible matrix that diagonalizes at least one irreducible
entrywise-nonnegative matrix.  Every relabelled Walsh matrix used here is a
Perron similarity, and its spectracone is exactly the conical hull of its rows.

A row-cone certificate for a spectral vector lambda is a list of positive
rational coefficients alpha_j and distinct row indices r_j satisfying, for
every c=0,...,n-1,

    lambda[c] = sum_j alpha_j*S[r_j,c].

Thus such a certificate proves that lambda lies in the spectracone and is the
spectrum of the entrywise-nonnegative matrix S*diag(lambda)*S^(-1).

This instance has exactly k=3 nonzero terms.  Their coefficients, in the
required answer order, are the following positive integers (integers are
rationals with denominator 1):

    22 28 31

For exact sign decoding, the next table lists every possible signed sum.  Each
entry is value:bits.  In the bit string, bit j is 0 when coefficient j has a
plus sign and 1 when it has a minus sign; j runs left-to-right in the published
coefficient order.

  -81:111  -37:011  -25:101  -19:110
  19:001  25:010  37:100  81:000

The complete target spectrum is below as coordinate:value pairs.  The pairs
are deliberately unordered; each coordinate 0,...,n-1 occurs exactly once.

  3:19  14:19  10:25  15:-19  5:81  0:37  7:25  11:-25
  12:-37  9:-81  1:-37  13:37  4:-81  2:-19  8:81  6:-25

Return exactly k terms in increasing published-coefficient order.  Term j is
[r_j,[num_j,den_j]], where 0 <= r_j < n, all r_j are distinct, and the reduced
rational num_j/den_j must equal coefficient j above.  Order therefore matters,
repeated rows are forbidden, denominators must be positive, and all equalities
are exact.

Give your final answer inside <answer></answer> tags, as one JSON list of the k terms.
Example: <answer>[[0,[2,1]],[3,[5,1]]]</answer>
Output nothing else inside the tags.
```

The answer is `[[12,[22,1]],[2,[28,1]],[8,[31,1]]]`.  A person can solve the
demo by inverting the one affine operation at each of the four unit columns and
using the eight-entry sign table.

```python
>>> verify(inst, [[12,[22,1]],[2,[28,1]],[8,[31,1]]])
(True, 'ok')
>>> verify(inst, [[13,[22,1]],[2,[28,1]],[8,[31,1]]])
(False, 'decomposition mismatch at spectral coordinate 0')
```

## Difficulty presets

| Preset | `n` | Terms | Relabelling rounds | Weight bits | Reference ops | Compact bound | Render chars (seed 0) | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| demo | 16 | 3 | 1 | 6 | 115 | 49 | 2,762 | hand-solvable; never ships |
| easy | 1,024 | 7 | 1 | 32 | 13,319 | 161 | 22,180 | defeated: 3/3 oracle solves |
| medium | 2,048 | 7 | 1 | 40 | 28,679 | 175 | 45,656 | defeated: 1/3 oracle solves |
| hard | 4,096 | 7 | 2 | 48 | 73,735 | 294 | 96,720 | defeated: 2/3 oracle solves |

There is no shipping preset.  The retained module's `SHIPPING_DIFFICULTY="easy"`
only identifies the preset on which its local self-test measurements were taken.
No preset was rejected by a local gate, but every non-demo rung was defeated by
the oracle criterion.  After `hard`, `escalate()` cannot double the Walsh ground
set without taking the compact route above the 300-operation G9(c) cap, so it
returns `None` rather than pretending that larger published numerators add
hardness.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses over four presets and three seeds |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON round-trips through realistic prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; exact space `1,156,576,495,205,226,332,160` |
| G5 | pass | unique answer, exact density `1/1,156,576,495,205,226,332,160`; demo enumeration found one; strongest failing attack averaged 0.031762 s |
| G6 | pass | five attacks each 0/8; reference and compact algorithms each 8/8 |
| G7 | pass | doubled `n=2048` built and verified; candidate space increased |
| G8 | pass | 140/140 keys invariant, 140/140 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 148 actual / 155 worst-case answer chars, 21 atoms, 39 worst-case tokens, 161 intended operations |

The five failing attacks are low-Hamming Walsh-row outliers, spectral-position
outliers, greedy largest-weight sign peeling, the direct unit-column method
without undoing the relabellings, and 256 structure-aware random restarts.

## Oracle loop

The unedited script-owned transcript has verdict `too_easy`.  A preset is
defeated if any attempt solves it.

| Preset | Seed | Model | Result | Verification |
|---|---:|---|---|---|
| easy | 801,170,481 | Gemini 3.8 Flash | solved | ok |
| easy | 32,708,128 | GPT-5.6 Terra | solved | ok |
| easy | 1,100,091,516 | Gemini 3.8 Flash | solved | ok |
| medium | 115,525,305 | Gemini 3.8 Flash | solved | ok |
| medium | 1,525,975,502 | GPT-5.6 Terra | failed | decomposition mismatch at coordinate 0 |
| medium | 473,092,680 | GPT-5.6 Terra | failed | decomposition mismatch at coordinate 1 |
| hard | 1,106,963,356 | Gemini 3.8 Flash | solved | ok |
| hard | 234,995,438 | GPT-5.6 Terra | failed | decomposition mismatch at coordinate 0 |
| hard | 1,448,072,323 | Gemini 3.8 Flash | solved | ok |

## G9 arms

| Arm | Solved / completed attempts | API errors | Conclusion |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | no diagnostic available |
| structural hint | 0 / 0 | 4 | no diagnostic available |
| placebo hint | 0 / 0 | 4 | no diagnostic available |

`hinted - placebo` is undefined with zero completed attempts; the module records
`0.0` only as a serialization-safe placeholder and labels the verdict
`not_run`.  The answer/route caps still pass: 155 worst-case characters, 21
atomic elements, and 161 intended exact operations.

## Use

```python
from rejected_gen_2409_07682 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>[[0,[1,1]]]</answer>")
ok, reason = verify(inst, candidate)
```

This retained module is for audit and possible future redesign only.  Do not run
`emit.sh` for this paper while `REJECTED.md` is present.

## Caveats

- This is emphatically Track B.  A fast Walsh transform recovers every answer
  in milliseconds; the family is not evidence for computational hardness of the
  NIEP.
- The family covers the paper's Walsh/Klein slice of the DNIEP, not arbitrary
  Perron similarities, complex DFT cones, K-arcs, or the general NIEP.
- G4 samples uniformly from injective assignments of the seven already-published
  weights to seven rows.  It accounts for every stated shape constraint but says
  nothing about algebraically informed guesses; G6 only samples five such ideas.
- The signed-sum table deliberately makes post-insight decoding writable.  It may
  also make the unit-character route easy for a model that recognizes Walsh
  characters; that is exactly what the missing bare/hinted/placebo runs must
  measure.
- Optimized sparse Walsh-transform recovery, learned spectral priors, and broader
  symbolic-algebra attacks were not counted as failing attacks.  The full exact
  FWHT is instead disclosed as the successful reference algorithm.
- `canonical_key` is proven against affine row relabelling, affine column
  relabelling, input reordering, and all their compositions.  It is not a complete
  canonical form under every automorphism of a Walsh matrix.
- `gvlib.rationals` is used when present for exact rational boundary helpers; the
  verifier retains a standard-library-only exact fallback.  No floating-point
  arithmetic is used.
- Most importantly, the bare STEP 4 run showed that the intended Walsh-character
  insight is accessible to the oracle pool.  The large formal candidate space and
  the five failed scripted attacks therefore do not establish no-tool hardness.
