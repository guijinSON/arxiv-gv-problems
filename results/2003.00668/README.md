# Symplectic-radical generator for arXiv:2003.00668

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | normalized finite-field coefficient vector (`integer_tuple`) |
| Intended intuition | invariant: symplectic transvections preserve the canonical Gram form |
| Domain essentiality | native |
| Reduction | none |

**Status:** all exact/local gates pass, but STEP 4 is incomplete and this result
is not yet shippable: OpenRouter quota exhaustion stopped the hard oracle panel
after one scored failure.

## Problem and trust model

The solver receives an exact, factored generator of a linear code over a prime
field.  The factors are a canonical symplectic row family, several explicitly
listed symplectic transvections, and a scaled Vandermonde row-basis change.  The
solver must give the normalized coefficients of a nonzero row combination in
the symplectic radical, with X-weight one and Z-weight zero.  The checker
executes the transformations, finite-field combinations, Hamming weights, and
all symplectic inner products exactly; it neither trusts nor reads the planted
answer.

This is the native object in Section II of Matsumoto, [*Improved
Gilbert-Varshamov Bound for Entanglement-Assisted Asymmetric Quantum Error
Correction by Symplectic Orthogonality*](https://arxiv.org/abs/2003.00668).
Section II, Theorem 1 identifies the radical and the rank of
`H_X H_Z^T-H_Z H_X^T` as the quantities controlling the entanglement parameter.
The proof of Theorem 2 uses the symplectic-group action that preserves those
products.  No graph, SAT instance, or finite-field surrogate replaces the
paper's code.

The family is generatable by transformation, not by solving.  It starts with
`c` hyperbolic row pairs and one known radical row, applies transvections that
fix that radical, and carries its coefficient vector through the Vandermonde
change using the barycentric identity.  This also makes the normalized answer
unique.

## Why Track B

The paper does not prove an algorithmic hardness result.  Its Theorem 2 is an
existence-by-counting GV bound, and the Conclusion explicitly leaves explicit
construction of unrestricted spaces as future work.  Claiming Track A from
that theorem would therefore be unsupported.

An efficient algorithm does exist here: materialize `H`, form its alternating
Gram matrix, and use Gaussian elimination to find the one-dimensional kernel.
Its complexity is `O(ell^2 n + ell^3)` exact field operations.  At the hard
preset the included reference implementation solved 8/8 instances with
12,150,796 counted modular operations.  It averaged 0.31 seconds on an unloaded
run and 2.885 seconds in the latest gate rerun on a heavily shared host.  The compact route
recognizes that transvections do not alter the canonical Gram form and that the
evaluation points are a shuffled affine progression.  Signed binomial
barycentric weights, division by the row multipliers, and projective
normalization, including construction of the affine-position lookup table, take
291 exact finite-field operations.  The benchmark asks a
no-tool solver to recognize and execute that compression; it does not pretend
Gaussian elimination is unavailable in general.

## Worked demo (seed 0)

This is the complete rendered `demo` problem, and it is genuinely solvable on
paper (the candidate language has only `6^4=1296` normalized vectors, although
the invariant route is much shorter):

```text
Find a symplectic-radical row combination over a prime field.

All arithmetic is in F_7, represented by integers 0,...,6 modulo 7.
A vector is (x|z) in F_7^(2*4), with coordinates numbered 0 through 3.
Its symplectic product with (x'|z') is
  <(x|z),(x'|z')> = sum_r (x_r z'_r - z_r x'_r) mod 7.
The X-weight (respectively Z-weight) is the number of nonzero x (respectively z) coordinates.

There are ell=5=2*2+1 canonical rows b^0_0,...,b^0_4.
For k=0,...,c-1, b^0_(2k) is the X-unit vector and b^0_(2k+1) is the Z-unit vector at the listed physical coordinate:
  pair positions k:coordinate = 0:3, 1:1
The final row b^0_4 is the X-unit vector at coordinate 0.
All unmentioned coordinates are zero.

Apply the following symplectic transvections in the displayed order to every canonical row.  A line 'alpha ; v' means replace b by
  b <- b + alpha*<b,v>*v mod 7.
Each v is written sparsely as Xindex:value or Zindex:value; omitted entries are zero.
  T0: 3 ; X0:2 X1:4 X2:3 X3:3 Z1:6 Z2:2 Z3:3
Call the resulting rows b_0,...,b_(ell-1).

Define the displayed generator rows H_i by the exact factorization
  H_i = d_i * sum_{j=0}^{ell-1} x_i^j b_j mod 7.
The evaluation points form x_i = 4 + 2*k_i mod 7, with k_i a permutation of 0,...,4.
The row data are 0-indexed and listed as i : x_i, d_i:
  0: 1, 1
  1: 4, 5
  2: 3, 3
  3: 6, 5
  4: 5, 6

Let C be the F_7 row span of H_0,...,H_(ell-1).  Find coefficients
a=[a_0,...,a_(ell-1)] such that w=sum_i a_i H_i is nonzero,
has X-weight exactly 1 and Z-weight exactly 0, and satisfies
<w,H_i>=0 for every i.  Thus w is in C intersect C^{perp_s}.
Your answer must contain exactly 5 integers, every one in 1,...,6;
the first coefficient must be a_0=1.  Order matters and repetitions are allowed.

Give your final answer inside <answer></answer> tags, as one JSON array of integers.
Example format only: <answer>[1, 1, 1, 1, 1]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>[1, 4, 6, 5, 1]</answer>`.
`verify(inst, [1, 4, 6, 5, 1])` returns `(True, "ok")`; deleting its last
coefficient returns `(False, "too few coefficients: expected 5")`.

## Difficulty presets

| preset | code length `n` | rows `ell` | field | transvections | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 5 | F_7 | 1 | exhaustive count and hand example |
| easy | 32 | 31 | F_37 | 3 | first oracle rung |
| medium | 128 | 59 | F_61 | 5 | local gates pass |
| hard | 512 | 59 | F_61 | 8 | shipping preset; one scored failure, full oracle verdict blocked by quota |

The answer stays at 59 elements between medium and hard; the haystack grows
through physical coordinates and transvection clutter.  `escalate()` continues
that fixed-witness growth and also raises the field and transvection count.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify across all presets |
| G2 | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | prose/fence/JSON round trip passes; answer is JSON-native |
| G4 | 0 hits in 200,000 full-support normalized samples; space size `60^58` |
| G5 | demo has exactly 1 answer; hard sampled density 0/200,000; baseline 2.885 s in the latest shared-host run / 12,150,796 operations |
| G6 | six attacks at 0/8 each; reference Gaussian algorithm 8/8 |
| G7 | `n=1024` builds and verifies with the same 59-element answer length |
| G8 | 140/140 invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9 | caps pass: 226 characters, 119 conservative tokens, 59 atoms, 291 intended operations; oracle arms are incomplete diagnostics |

## Oracle loop and G9 arms

The current bare harness reached both vendors before the OpenRouter account hit
its total limit.  Easy was solved 3/3 and medium 2/3.  The first hard response
failed exact verification; four retries for the next slot then received HTTP
403 `Key limit exceeded (total limit)`, so the harness correctly stopped
without a hardness verdict.  Earlier structural-hint and placebo runs likewise
contain only quota errors.  The partial, script-owned transcripts are retained
as evidence of the infrastructure block; they are **not** a completed hardness
claim.

| preset | seed | model | result |
|---|---:|---|---|
| easy | 520178297 | Gemini 3.8 Flash | solved, witness verified |
| easy | 1435535110 | GPT-5.6 Terra | solved, witness verified |
| easy | 1879625487 | Gemini 3.8 Flash | solved, witness verified |
| medium | 390178917 | GPT-5.6 Terra | solved, witness verified |
| medium | 935952029 | Gemini 3.8 Flash | solved, witness verified |
| medium | 1896505395 | GPT-5.6 Terra | failed degree-0 moment |
| hard | 934364292 | GPT-5.6 Terra | failed degree-0 moment |
| hard | four further seeds | Gemini 3.8 Flash | API errors; unscored |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/1 scored | first hard answer failed; remaining calls blocked by quota |
| structural hint | 0/0 scored | all retries errored; diagnostic unavailable |
| placebo | 0/0 scored | all retries errored; diagnostic unavailable |

Consequently hinted-minus-placebo is recorded as `null`, not as a fabricated
zero.  These arms are diagnostic under the current contract; G9's actual gate
is the size/effort cap, which passes.  A funded OpenRouter key is still required
to complete STEP 4 and the three diagnostics, then update `G9_RESULTS` and
regenerate `selftest_report.json`.

## Use

```python
from gen_2003_00668 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, after completing the interrupted oracle runs:

```bash
bash scripts/emit.sh 2003.00668 20 hard
```

## Caveats

The family is easy with exact linear-algebra software, by design and as Track B
declares.  The 0/200,000 guess result samples uniformly from the explicitly
required full-support normalized vectors; it is not a claim about arbitrary
model priors or about average-case coding-theory hardness.  The adversary panel
tests a multiplier outlier, first-moment greedy repair, constant, alternating,
and linear progression ansatzes, and 256 random restarts, but not every possible
symbolic interpolation heuristic.  In particular, a solver that recognizes
the barycentric/binomial identity has found the intended route.

`canonical_key` exactly handles input-row permutations and nonzero row scalings,
physical-qudit and canonical-hyperbolic-pair permutations, affine changes of the
evaluation variable, equivalent rescalings of transvection vectors, and their composition.
Full equivalence of linear codes under arbitrary row operations and monomial
symplectic maps is not canonicalized; computing that equivalence is outside the
cheap duplicate check, so the key uses the strongest exact normal form for the
generator's own relabellings.  Finally, no shipping claim should be trusted
until the currently blocked bare run has a `hardened` verdict.  The hinted and
placebo arms are informative diagnostics rather than gates, but they also remain
unmeasured because of the same quota exhaustion.
