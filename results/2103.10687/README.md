# Differential witnesses for the piecewise Dobbertin permutation

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | exact symbolic (a finite-field coefficient mask) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This generator is based on Wang, Zhang, and Zha, [“Low differentially
uniform permutations from Dobbertin APN function over
`GF(2^n)`”](https://arxiv.org/abs/2103.10687).  It hands the solver the paper's
native objects: a subfield `K=GF(2^k)`, its degree-five extension
`L=GF(2^(5k))`, the paper's piecewise permutation, and one exact differential
target.  The solver must return a nonzero trace-zero `z` for which `x=Uz`
has the displayed derivative.  The checker reduces binary polynomials exactly;
there are no floats, lookup tables, or calls to a solver.

The local correctness and adversary gates pass. The mandatory bare external
hardening also passed: all three calls at `easy` failed to produce a verified
witness, so `harden.py` recorded `verdict: hardened`. The account limit was
exhausted immediately afterward, so the hinted and placebo G9 diagnostics have
authentic error transcripts but no valid attempts. Those diagnostics are not
gates; they should be rerun when quota is restored.

## Why this is Track B

Section 1 defines the derivative and differential uniformity.  Lemma 3.1 is the
subfield-exclusion result, while Theorem 3.2 constructs the permutation for odd
`k`, ambient degree `5k`, and a suitable subfield permutation `g`.  Corollary
3.4 supplies the `g(x)=x^3` APN case used here.  The remark after Theorem 3.2
also gives the regimes to avoid: even `k` or nonpermutation `g` loses the
permutation property.  The paper's `k=2` tables are experimental
nonpermutations and are not used.

An efficient solver exists and is disclosed here. Substitute `x=Uz`; on `K`, the
Dobbertin exponent is congruent to 3.  Since `U^d=U^29=1+U^3`, the differential
equation becomes

```text
z^2 + z = c + 1.
```

For odd `k`, the half-trace
`H(t)=sum(i=0..(k-1)/2, t^(2^(2i)))` is the unique trace-zero solution.
This takes `O(k)` field squarings, or `O(k^3)` scalar `GF(2)` work with the
module's schoolbook accounting.  At the shipping candidate `k=151`, eight
runs averaged 880,088 counted scalar operations (maximum 888,166), 150 field
squarings, 77 additions, and 0.01604 seconds (maximum 0.03651 seconds).  The
compact description has 227 field operations.  It is impossible to carry out
comfortably without tools, but trivial for the reference implementation; that
is exactly the narrower Track B claim.

The paper itself reports after its Section 3 tables that MAGMA's full
differential-spectrum computation terminated prematurely already for `k>=3`;
the shipping field uses `k=151`. That ambient computation is not hidden as a
hardness claim here—the successful half-trace method above is the reference.

## Construction and verification

Generation samples a nonzero trace-zero `z` first, uniformly from the same
language used by `random_candidate`, and then sets `c=z^2+z+1` and
`B=c(1+U^3)`.  Thus the certificate is known by inverse generation.  The
trace-zero condition selects exactly one of the two Artin–Schreier roots.
`verify` checks the answer grammar, exact trace, the reduced differential
identity, and the original full-extension-field equation without reading
`inst["answer"]`. G1 exercises that native equation at every preset.

## Worked demo

For `make_instance(n=1, seed=0)`, `k=11` and the complete rendered question is:

```text
Find a normalized differential witness for a piecewise Dobbertin permutation.

Binary polynomials are encoded as hexadecimal coefficient masks: bit i is the
coefficient of X^i.  All hexadecimal strings are lowercase and include leading
zeroes to their stated width.

Let k=11 and let

  K = GF(2)[X]/(M),   M mask = 0xfcd.

M is monic irreducible of degree k.  Addition in K is bitwise XOR and
multiplication is carryless polynomial multiplication reduced modulo M.  For
q in K, its absolute trace is

  Tr(q) = q + q^2 + q^(2^2) + ... + q^(2^(k-1)),

which is either 0 or 1.

Let L=K[U]/(U^5+U^2+1), so every element of L has a unique coordinate vector
(q0,q1,q2,q3,q4) meaning q0+q1*U+...+q4*U^4.  Put

  d = 2^(4k)+2^(3k)+2^(2k)+2^k-1.

Define F:L->L by

  F(y) = y^3  if y lies in K (coordinates q1=q2=q3=q4=0),
  F(y) = y^d  otherwise.

This is the g(y)=y^3 case of the paper's piecewise permutation.  Set a=U.
The target B, written as five K-coordinate masks of exactly 3 hex digits,
is

  B = ["0x1f5","0x000","0x000","0x1f5","0x000"].

Find a NONZERO z in K such that Tr(z)=0 and

  F(U*z + a) + F(U*z) = B.

All additions are in characteristic two.  Equality means exact equality of all
five K coordinates.  The trace-zero condition chooses one of the two roots;
there is exactly one admissible answer.  Encode z as exactly 3 lowercase
hexadecimal digits after 0x.  The JSON field named trace is the integer 0, not a
string.  No approximation is permitted.

Give your final answer inside <answer></answer> tags as the JSON object
{"z":"0x...","trace":0} with exactly those two fields.
Example of the required syntax: <answer>{"z":"0x002","trace":0}</answer>
Output nothing else inside the tags.
```

The answer is `{"z":"0x628","trace":0}` and verifies as `(True, "ok")`.
Changing it to `{"z":"0x000","trace":0}` gives
`(False, "z must be nonzero")`.  A person can solve this smallest setting on
paper: the half-trace needs only ten squarings and seven additions in an 11-bit
field, although the bookkeeping is intentionally nontrivial.

## Difficulty presets

| preset | scale `n` | subfield `k=10n+1` | ambient degree | compact field operations | status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 11 | 55 | 17 | hand-scale; skipped by hardener |
| easy | 15 | 151 | 755 | 227 | **ships; bare oracle held 0/3** |
| medium | 17 | 171 | 855 | 257 | locally verified |
| hard | 19 | 191 | 955 | 287 | locally verified |

Escalation increases `k` while the answer remains a two-field JSON object.  The
next level after `k=191` would cross the 300-operation intended-route cap and is
reported as `cap_bound`.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses; 4/4 full-extension cross-checks |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown; duplicate keys rejected |
| G4 | pass | 0/250,000 hits; exact density `1/(2^150-1)` ≈ `7.0065e-46` |
| G5 | pass | demo has exactly 1/1023 answer; reference cost measured at shipping |
| G6 | pass | five attacks, 0/8 successes each; half-trace reference 8/8 |
| G7 | pass | doubled scale `n=30`, `k=301`, still builds and verifies |
| G8 | pass | 20/20 Frobenius invariance, carried-witness, and composition checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 61 characters, about 16 tokens, 2 atoms, 227 field operations |

The exact timing values from the latest machine run are in
`selftest_report.json`; wall-clock timing naturally varies slightly.

## Oracle loop

The repository's current two-vendor pool drew a model afresh for each call.
Two replies parsed as correctly shaped JSON but failed the exact identity; the
Gemini call returned no content and was scored by the harness as a failed valid
attempt under its empty-response rule.

| preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 766553072 | `openai/gpt-5.6-terra` | no | parsed; exact differential identity failed |
| easy | 870737987 | `google/gemini-3.8-flash` | no | empty response, `content_filter` finish reason |
| easy | 1914887055 | `openai/gpt-5.6-terra` | no | parsed; exact differential identity failed |

The resulting bare verdict is `hardened` at `easy`, with zero escalations.

## G9 arms

| arm | solved/valid attempts | error calls |
|---|---:|---:|
| bare | 0/3 | 0 |
| hinted | 0/0 | 4 |
| placebo | 0/0 | 4 |

`hinted - placebo` is undefined because neither of those two diagnostic arms
obtained a valid oracle attempt. Consequently nothing can yet be concluded
about whether the stated change-of-variables hint helps. The answer-size and effort measurements are
61 characters, approximately 16 tokens, 2 atoms, and 227 exact field
operations.

## Usage

```python
import random
import gen_2103_10687 as g

inst = g.make_instance(**g.DIFFICULTY["easy"], seed=12345)
question = g.render(inst)
candidate = g.parse_answer(
    "result: <answer>" + __import__("json").dumps(inst["answer"]) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** 150 - 1
```

From the repository root, emit instances with:

```bash
./scripts/emit.sh 2103.10687 20 easy
```

## Caveats

- This is deliberately not a computational hardness claim.  Any finite-field
  package, CAS, or short implementation of half-trace solves every instance in
  milliseconds.  The benchmark measures recognition and exact execution
  without tools.
- The `0/250,000` guessing result is for the uniform nonzero trace-zero prior
  declared by `CERTIFICATE_LANGUAGE`.  It measures guessing, not resistance to
  algebraic solving; the latter is easy and separately disclosed.
- The attack panel does not try general Gaussian elimination, optimized normal-
  basis arithmetic, or a CAS.  Those are successful reference-class methods,
  not failing attacks under Track B.
- `canonical_key` quotients the Frobenius automorphisms of the fixed field
  presentation.  It does not canonicalize arbitrary changes to a different
  irreducible polynomial; the generator fixes one deterministic modulus for
  every `k`, so those presentations are outside its sampled distribution.
- Full differential uniformity at large `k` is theorem-backed rather than
  exhaustively recomputed.  The witness equation itself is checked directly,
  and G1 cross-checks it in the full extension field.
- The bare hardening evidence is complete for the current two-vendor repository
  pool, but the structural/placebo comparison is missing because the external
  quota failed after that run. This limits conclusions about which prompt hint
  carries useful information, not the gated hardness verdict.
