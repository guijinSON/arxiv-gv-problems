# arXiv:1804.11172 — determinant orbits of fat subspaces

Status: the generator passes every local G1–G9 gate, but it is **not yet
submission-ready**. The required bare and G9 oracle runs were attempted and
OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw, so no model
response was scored and no Step 4 hardness verdict can honestly be claimed.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | polynomial over GF(2) |
| Intuition | invariant — recognize the determinant-one even rank-one perturbation beneath the constant-column term, so paired backgrounds cancel |
| Domain essentiality | native |
| Reduction | none |

## The problem

The paper [$q$-analogs of group divisible designs](https://arxiv.org/abs/1804.11172)
works with subspaces of `GF(q^g)^s`. Section 5 calls an `s`-dimensional
`GF(q)`-subspace *fat* when an ordered `GF(q)`-basis is linearly independent
over `GF(q^g)`. Lemma 8 classifies the `SL(s,q^g)/GF(q)*` orbits of fat
`s`-subspaces by `det(A) GF(q)*`, where the rows of `A` are such a basis.
Theorem 4 uses unions of these orbits as blocks of a q-GDD.

An instance gives a fat subspace by a square matrix over `GF(2^128)` and asks
for its determinant orbit. Since `GF(2)*={1}`, the answer is the determinant,
written as the support of a degree-below-128 binary polynomial. Verification is
exact Gaussian elimination followed by canonical polynomial comparison.

## Why Track B

This is not a structural-hardness claim. Lemma 8 itself supplies the polynomial-
time method: compute a determinant by Gaussian elimination, in `O(s^3)` field
operations. At shipping order `s=41`, eight fixed seeds averaged 16,267 field
operations, 418,229 inner shift/XOR steps, and 0.061 seconds on this host.

Generation samples the invariant `z` first. It makes paired column backgrounds
plus the residual `z+1`, and adds a determinant-one rank-one perturbation `L`
with `L·1=1`. Thus `det(L+1·v^T)=1+sum(v)=z`; independent row and column
permutations hide the presentation but preserve the determinant in
characteristic two. A solver who recognizes the modal-column and even-weight
rank-one invariants needs at most 41 field additions. Lemma 8's `k<s` single-
orbit case and exposed diagonal/triangular bases are the easy regimes avoided.

## Worked demo (`n=1`, seed 7)

This is the complete rendered instance (without a hint):

```text
Determinant orbit of a fat subspace over GF(2^128)

Work in the finite field F = GF(2)[x]/(x^128+x^7+x^2+x+1). A field element is
written as exactly 32 hexadecimal digits: bit e is the coefficient of x^e,
for 0 <= e <= 127. Addition is bitwise XOR. Multiplication is ordinary
polynomial multiplication over GF(2), reduced by x^128=x^7+x^2+x+1.

The 3 rows of the matrix A below are an ordered GF(2)-basis of a
GF(2)-subspace U of F^3. They are promised to be linearly independent
over F, so U is a fat 3-subspace in the terminology of the paper.
For q=2, the determinant orbit invariant of U is simply det_F(A), because
GF(2)^*={1}. Compute that nonzero field element exactly.

Matrix A (3 rows and 3 columns; spaces separate entries):
d23f0824128b2f330c5c7fd0a6a3a450 6513270e269e0d37f2a74de452e6b439 d23f0824128b2f330c5c7fd0a6a3a451
d23f0824128b2f330c5c7fd0a6a3a451 6513270e269e0d37f2a74de452e6b439 d23f0824128b2f330c5c7fd0a6a3a450
d23f0824128b2f330c5c7fd0a6a3a450 6513270e269e0d37f2a74de452e6b438 d23f0824128b2f330c5c7fd0a6a3a450

Output the invariant in its canonical sparse polynomial form: a JSON list
of every exponent e whose coefficient is 1, in strictly increasing order.
The list must be nonempty; exponents are 0-indexed integers in 0..127, with no
repeats. For example, 1+x^7+x^91 is written [0,7,91].

Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>[0,7,91]</answer>
Output nothing else inside the tags.
```

The answer is:

```json
[3,4,5,10,12,13,15,17,18,21,22,23,25,28,30,34,37,38,39,40,42,43,46,48,49,50,53,55,57,60,61,62,63,64,65,66,68,69,72,74,75,81,82,83,84,87,89,90,93,97,98,99,104,105,106,109,112,113,116,120,122,125,126]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last
exponent returns `(False, "polynomial is not the determinant orbit invariant")`.
A person can solve this three-row demo on paper by noticing the repeated field
values and applying the rank-one determinant identity; the hexadecimal XOR is
only one bit flip after paired terms cancel.

## Difficulty presets

The matrix order is `s=2n+1`; the 128-bit answer language stays fixed.

| Preset | n | Matrix order s | Ships? |
|---|---:|---:|---|
| demo | 1 | 3 | no — hand example |
| easy | 6 | 13 | no |
| medium | 12 | 25 | no |
| hard | 20 | 41 | configured shipping preset; oracle verdict pending |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; modulus passed Rabin irreducibility test |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced model-style response round-trips; JSON-native |
| G4 | pass | 0/200,000 uniform nonzero polynomials; exact probability `1/(2^128-1)` |
| G5 | pass | shipping density 0/200,000; one exact valid answer; reference seed cost 17,091 field ops and 0.084 s |
| G6 | pass | five attacks at 0/8; Gaussian reference 8/8 |
| G7 | pass | doubled `n=40`, order 81 verifies; reference cost grows 17,091 → 41,685 field ops |
| G8 | pass | 20/20 composed relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | pass | 245 chars, 77 atoms, about 62 tokens, 41 intended field additions |

## Oracle loop and G9 arms

No row below is a model failure: every call failed before inference. The raw
script-owned transcripts are retained.

| Arm/preset | Seeds | Scored solved/attempts | Outcome |
|---|---|---:|---|
| bare / easy | 775365020, 1794220179, 1580483517, 540271021 | 0/0 | four HTTP 403 key-limit errors across both vendors |
| structural / hard | 1632019373, 407409344, 699640744, 1027446289 | 0/0 | four HTTP 403 key-limit errors |
| placebo / hard | 9846271, 437194013, 236977860, 1375582099 | 0/0 | four HTTP 403 key-limit errors |

The hinted-minus-placebo statistic is undefined with zero scored attempts (the
JSON records `0.0` only as a neutral placeholder). No conclusion about the
claimed invariant intuition can be drawn until these arms are rerun with quota.

## Use

```python
from gen_1804_11172 import make_instance, verify

inst = make_instance(n=20, seed=123)
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, after a successful oracle rerun:

```bash
scripts/emit.sh 1804.11172 20 hard
```

## Caveats

- The decisive caveat is missing Step 4 evidence. Do not interpret the retained
  error transcripts as hardness, and do not emit this family into the corpus
  until `scripts/harden.py` records a real verdict.
- A CAS or the reference elimination solves shipping instances in about 0.06 s.
  The family is only a no-tool structure-recognition benchmark, never Track A.
- The G4 prior is uniform over all syntactically valid nonzero field elements.
  It measures blind guessing, not an informed solver exploiting matrix structure.
- The attack panel includes the modal-background near miss, frequency, trace,
  displayed-diagonal product, and random restarts. It does not include a complete
  automated rank-two decomposition, because that is effectively the intended
  compact algorithm; exact elimination already supplies the successful reference.
- `canonical_key` is proved invariant for independent row/column permutations,
  transposition, and their compositions. It is not a complete invariant under
  every semilinear change of ambient basis and may over-collapse rare instances.
