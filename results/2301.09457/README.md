# Common trifference coordinates (arXiv:2301.09457)

> **External-hardening status:** blocked, not passed. Two genuine oracle calls
> both solved `easy`; the OpenRouter account then reached its total-spend limit
> before the third slot or any higher rung ran. The refreshed structural-hint and
> placebo runs also contain only HTTP 403 quota errors. API errors are not solver
> failures, so this directory is not submission-ready until all three runs are
> repeated with a funded key.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | integer tuple: one normalized projective vector over `F_3` |
| Intended intuition | invariant — all translated triple differences but one form a sign-masked ternary Walsh basis |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Bishnoi, D'haeseleer, Gijswijt, and Potukuchi,
[*Blocking sets, minimal codes and trifferent codes*](https://arxiv.org/abs/2301.09457).
Section 6 defines a ternary trifferent code and Theorem 6.1 identifies its
generator columns with a symmetric affine 2-blocking set; Theorem 6.2 identifies
the same codes as minimal codes. An instance uses the full ternary simplex code,
whose coordinates are exactly the normalized projective points of `F_3^n`, and
supplies a batch of three-codeword tests in the paper's message/dot-product
notation. The solver returns one projective coordinate that makes every triple's
three symbols equal to `{0,1,2}`. Verification is exact finite-field substitution.

Generation chooses a Walsh row first, removes it from an orthogonal basis, and
turns every remaining row into a translated message triple. Orthogonality proves
the planted row separates all triples. The generator therefore knows its
certificate by inverse construction; it never solves the published instance.

## Why this is Track B

This paper does **not** support a Track A claim for this distribution. The proof
of Theorem 6.1 already rewrites trifference using exact dot products. For the
batch problem, translating each triple and imposing all separator conditions
gives a one-dimensional nullspace. Generic Gauss–Jordan elimination over `F_3`
solves 8/8 shipping instances, as expected, in `O(n^3)` time: the measured mean
at `n=128` is 833,553 exact operations and 0.593 seconds (maximum 919,446 and
1.029 seconds) in the final recorded self-test.

Step 0 also ruled out the paper's more literal alternatives. Theorem 1.1 is a
positive-probability existence argument, so sampling its random planes does not
give a known blocking-set certificate. The Section 5 tetrahedron has a direct
scan plus a 2-by-2 finite-field solve. Section 6.3 explicitly reduces the small
optima to an ILP: Gurobi 10.0 handled dimensions at most five in minutes, while
the dimension-six optimum remained unknown. Finally, the Conclusion proves
that the analogous linear perfect `q`-hash problem is trivial for `q>3` and
dimension at least two. These are easy or uncertified regimes, not hardness
evidence for this generator.

The compact route notices more. The constraints are every row but one of an
affinely relabelled Walsh basis. XOR of the distinct public labels identifies
the omitted label. At the shipping preset, the displayed XOR checksum removes
the otherwise-unbounded repeated-label scan; the eight affine twists and row
mask identify the character, and cyclic Gray order writes its 128 signs with one
update per component. The conservative bound is 147 exact
XOR/multiply/add/transition operations, about 5,670 times fewer than measured
generic elimination. This
recognition gap—not computational intractability—is the Track B claim.

## Worked demo

`make_instance(seed=0, n=4, multiplicity_max=2, twist_rounds=1,
publish_checksum=False)` renders in full as follows:

```text
Find one code coordinate that makes every listed ternary codeword triple trifferent.

All arithmetic on vector entries and dot products is in the finite field F_3={0,1,2}.
Vector component indices and row labels are 0-based.  Bitwise operations on row
labels are ordinary nonnegative-integer XOR, AND, and bit count operations.

Let n=4.  The ternary simplex code has one coordinate for each projective
point of F_3^n.  We represent a projective point by the unique vector
b=[b_0,...,b_(n-1)] in {0,1,2}^n whose first nonzero entry is 1.  Thus the
code has (3^n-1)/2 = 40 coordinates.  The codeword belonging to a
message vector m in F_3^n has symbol

    c(m)[b] = sum_j m[j]*b[j] modulo 3

at coordinate b.  Three codewords are trifferent at b when their three symbols
there are exactly {0,1,2}.

The message triples below are given succinctly.  Starting from a row label r,
apply each displayed affine operation (a,b) as r <- (a*r+b) modulo n, in the
displayed left-to-right order.  Every a is odd, so these are permutations.
Call the resulting label twist(r).  Then define gray(x)=x XOR (x>>1),
and let parity(z) be the number of 1-bits of z modulo 2.  For row label r define
the length-n vector H_r by

    H_r[j] = scale[j] * sign(parity((twist(r) XOR row_mask) AND gray(perm[j]))) modulo 3,

where sign(0)=1 and sign(1)=2.  The public data are:

    row_mask = 3
    row-label affine operations (a,b): (3,3)
    perm (a permutation of 0,...,n-1):
  2 3 0 1
    scale (each entry is 1 or 2):
  2 2 2 2

Define U to be zero except U[1]=2.
Each displayed pair (r,o) specifies the following three DISTINCT messages:

    M0 = H_o
    M1 = H_o + U
    M2 = H_o + H_r - U                 (componentwise modulo 3).

Repeated row labels are intentional; order is irrelevant.  The 15
listed (r,o) pairs are:
  (1,0) (0,0) (0,2) (2,3) (0,3) (1,1) (2,0) (1,3)
  (2,0) (0,3) (2,0) (0,2) (0,2) (1,3) (1,2)

Return ONE normalized projective vector b of exactly 4 integers.  It must make
{c(M0)[b],c(M1)[b],c(M2)[b]}={0,1,2} for every listed pair.  Entries must be
0, 1, or 2; the vector must be nonzero; its first nonzero entry must be 1.

Give your final answer inside <answer></answer> tags, as one JSON list of 4 integers.
Example: <answer>[1,0,2,1]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[1,2,1,2]</answer>`. A person can solve this demo by
expanding the four Walsh rows or by finding the omitted label and using
orthogonality.

```python
>>> verify(inst, [1, 2, 1, 2])
(True, "ok")
>>> verify(inst, [1, 2, 1])
(False, "answer is missing coordinates: expected 4")
```

## Difficulty presets

| Preset | `n` | Max base multiplicity | Affine twists | Candidate space | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 2 | 1 | 40 | hand-solvable; never ships |
| easy | 32 | 3 | 2 | 926,510,094,425,920 | solved by both completed oracle calls; third slot blocked |
| medium | 64 | 3 | 4 | 1,716,841,910,146,256,242,328,924,544,640 | local gates pass; oracle not reached |
| hard | 128 | 4 | 8 | 5.895×10^60 | provisional shipping preset; local gates pass; oracle not reached; checksum shown |

`SHIPPING_DIFFICULTY` is `hard`. If an oracle later solves it, `escalate()` first
adds row-label twists at fixed 128-element answer length, then uses `n=256` with
an input checksum so the compact route remains below 300 operations. Only after
the 256-atom rung is exhausted does it return `cap_bound`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses across four presets and three seeds |
| G2 | pass | 5/5 corruption classes rejected with five distinct reasons |
| G3 | pass | fenced tagged JSON round-trips; answer is JSON-native |
| G4 | pass | 0/200,000 uniform normalized-projective guesses |
| G5 | pass | exactly 1 answer among `(3^128-1)/2`; density 1.6963×10^-61; 2,048 attack iterations took 2.582 s in the final recorded run |
| G6 | pass | all-ones, component-majority, sparse-`U`, unmasked-Walsh, and 256-restart attacks each 0/8; reference elimination 8/8 |
| G7 | pass | doubled `n=256` instance builds, verifies, and enlarges the space |
| G8 | pass | 140/140 invariant keys, 140/140 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 384 characters, 96 estimated tokens, 128 atoms, 147 intended operations |

## Oracle loop

The first two rows below are genuine solves at `easy`. The remaining four calls
are API errors, not completed attempts; the script correctly refused to issue a
verdict before the third required slot or any higher rung.

| Arm | Preset | Seeds | Completed attempts | API errors | Reason |
|---|---|---|---:|---:|---|
| bare Step 4 | easy | 1770084249, 1187509681 | 2 solved / 2 completed | 0 | both exact 32-entry answers verified |
| bare retry failures | easy | 1039429703, 73289651, 1545551629, 722602076 | 0 | 4 | HTTP 403 total key limit exceeded |
| structural hint | hard | 1182636789, 606551478, 834548956, 1791705456 | 0 | 4 | HTTP 403 total key limit exceeded |
| placebo hint | hard | 2042032289, 1363077528, 470650656, 75945470 | 0 | 4 | HTTP 403 total key limit exceeded |

The G9 rates and `hinted - placebo` effect are undefined because neither
shipping-preset diagnostic arm completed. The JSON uses `0.0` only as a
serialization-safe placeholder and marks the verdict `not_run_api_unreachable`.
Nothing can yet be concluded about whether the hint carries useful structural
information.

## Use

```python
from gen_2301_09457 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>[1,0,2]</answer>")
ok, reason = verify(inst, candidate)
```

After obtaining a funded OpenRouter run and a `hardened` verdict, emit from the
repository root with:

```bash
bash scripts/emit.sh 2301.09457 20 hard
```

## Caveats

- This is emphatically Track B. Exact Gaussian elimination solves every instance
  in about a second locally; the family is not evidence of cryptographic or
  complexity-theoretic hardness of codes, blocking sets, or nullspaces.
- The family covers the paper's generator-column/trifference equivalence, not its
  extremal bounds, random small blocking sets, expander construction, or explicit
  algebraic-geometric concatenation. It asks for one coordinate common to a batch
  of triples, a native finite-field extension of the paper's per-triple witness.
- G4 is uniform over all normalized projective points and includes every stated
  shape constraint. Its tiny density does not model a solver that detects Walsh
  orthogonality; that route is deliberately disclosed as the intended solution.
- The five failed attacks are construction-aware but not exhaustive. No SAT/SMT
  encoding, learned pattern detector, or optimized Walsh recognizer was tested.
- `canonical_key` deliberately quotients triple order, common triple translations,
  and monomial message-basis changes. It keys on the structural multiset of
  constraint multiplicities; it is not a complete invariant under arbitrary
  `GL(n,3)` equivalence.
- Distinct seeds get their canonical diversity from different repeated-constraint
  multiplicity profiles. Those repetitions change the presented batch and its
  crowding but not the unique feasible projective point, so this is input-level
  diversity rather than diversity of answer geometry.
- The external oracle evidence is incomplete because of account quota, not because
  of the family. Do not interpret either the error rows or the untested higher rungs
  as hardness evidence.
