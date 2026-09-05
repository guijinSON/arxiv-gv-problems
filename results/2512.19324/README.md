# arXiv:2512.19324 — prescribed-kernel codewords

| Profile field | Value |
|---|---|
| Track | **B** — an efficient exact algorithm exists and is reported |
| Native domain / regime | algebra / finite field |
| Computational core | linear algebra |
| Certificate form | normalized integer coordinate tuple |
| Intended intuition | invariant: Frobenius fixed and minus-one eigenspaces |
| Domain essentiality | native; no reduction |

This generator uses Tang and Zhou, [*A new family of maximum linear symmetric rank-distance codes*](https://arxiv.org/abs/2512.19324).  It hands the solver sixteen symmetric (8\times8) matrices over a prime field, spanning one of the paper's (\mathcal T_{8,1,\eta}) codes, plus a two-dimensional target plane.  The solver must give normalized code coefficients for a rank-six matrix whose kernel is that plane.  Checking is exact: form the linear combination, multiply it by the two kernel vectors, and row-reduce modulo (p).

## Why the construction and grading are trustworthy

Theorem 1.2, in the (k=4,n=8,s=1) regime, says every nonzero word has rank at least six.  Section 3, Lemma 3.3 rewrites the (b_2=0) polynomial as a Frobenius power of a degree-two linearized polynomial.  The generator first chooses (b_1^{p^3}=-b_1).  With (\lambda=b_1^{p^2}), that inner polynomial is exactly

\[
\lambda(X^{p^2}-X),
\]

whose kernel is (\mathbb F_{p^2}).  Thus the planted word has rank exactly six before any displayed matrices are assembled.  The basis of (\mathbb F_{p^8}) is a randomly permuted and rescaled normal basis, so the planted coordinates vary with the seed.  Every extension modulus is tested for irreducibility; primes below (2^{64}) use deterministic Miller–Rabin, and larger supported primes are Pocklington-certified.

This cannot honestly be Track A. Multiplying every generator by the two target vectors gives a 16-by-16 homogeneous system, and modular Gaussian elimination finds its nullspace in O(16^3). Across eight shipping-preset seeds the reference implementation solved 8/8, using 31,522 counted operations (3,940 average) and 0.002–0.009 seconds total across repeated local runs. The compact route is different: Frobenius is a weighted 8-cycle in the displayed normal basis, so following its `F^3 = -I` eigenspace takes at most 40 exact operations; the target plane is the `F^2 = I` fixed space. The paper's restriction to k=3,4,5 is respected; no unproved larger code dimension is used.

## Worked demo

The `demo` preset is genuinely hand-scale.  Over (\mathbb F_3), follow the single nonzero entry in each Frobenius column around its cycle, enforce (F^3b_1=-b_1), normalize, and put (b_0=b_2=0).  For seed 0 this gives

```text
<answer>[0,0,0,0,1,1,1,1,2,1,1,2,0,0,0,0]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Dropping the last coefficient returns `(False, "answer has fewer than 16 coefficients")`.

<details>
<summary>Full rendered demo instance (seed 0)</summary>

```text
PRESCRIBED-KERNEL WORD IN A SYMMETRIC RANK-DISTANCE CODE

All arithmetic is in the prime field F_3, represented by residues
0,...,2; reduce every sum and product modulo 3.
A symmetric 8 by 8 matrix is printed by its 36 upper-triangular
entries in this fixed order:
(0,0),(0,1),...,(0,7),(1,1),(1,2),...,(1,7),...,(7,7).
Reflect these entries across the diagonal to recover the full matrix.
Vector and matrix coordinates are 0-indexed, but the answer below is
a coefficient list, not a list of indices.

The ordered symmetric matrices G0,...,G15 span a 16-dimensional
linear code C over F_p.  For c=(c0,...,c15), write
M(c)=c0*G0+...+c15*G15 (all entries reduced modulo p).
The generators are grouped as c0..c3=b0 coordinates,
c4..c11=b1 coordinates, and c12..c15=b2 coordinates in the
T_{8,1,eta} construction.  Their upper triangles are:
G00: 0 2 1 1 0 0 0 1 0 0 0 0 2 1 0 1 0 0 1 2 1 2 1 0 2 0 0 1 2 1 0 0 0 1 0 2
G01: 1 2 0 1 2 2 1 2 2 1 2 1 0 2 1 2 1 2 2 2 0 1 2 2 0 1 1 1 0 1 2 1 1 2 2 1
G02: 0 1 0 0 2 2 0 2 1 2 1 1 2 1 2 1 1 0 1 1 1 1 2 1 2 1 0 2 0 0 1 2 2 1 2 1
G03: 1 2 1 2 0 2 1 0 0 2 0 1 1 2 1 2 0 2 2 2 2 0 0 2 1 1 1 1 2 2 0 2 0 2 0 0
G04: 0 2 0 0 0 2 2 2 2 2 2 1 2 0 1 0 0 0 2 0 0 0 2 0 2 2 2 0 2 2 2 0 0 2 0 2
G05: 2 2 0 0 1 0 0 1 0 0 2 1 0 1 0 0 2 1 1 1 0 2 0 1 0 0 2 1 1 2 2 2 0 2 0 0
G06: 0 0 0 0 1 1 2 2 0 0 1 0 0 0 2 0 1 1 1 0 2 1 0 0 0 2 1 0 2 1 1 2 0 1 2 1
G07: 0 0 1 0 0 0 1 0 1 1 2 0 2 0 2 1 1 0 1 1 2 0 2 0 1 0 1 2 0 2 0 0 1 1 0 1
G08: 1 0 2 1 0 1 0 1 1 0 0 2 1 1 0 1 0 2 0 0 2 1 1 1 0 1 0 2 0 0 1 1 2 0 0 0
G09: 2 2 2 2 1 2 2 0 2 2 0 0 0 1 2 2 0 0 1 1 0 0 1 0 0 0 2 1 0 0 0 0 1 0 1 2
G10: 1 0 1 1 1 0 2 0 1 2 0 2 0 1 0 1 1 1 0 0 0 1 2 1 1 2 0 0 0 0 0 0 2 0 2 1
G11: 2 2 0 1 0 0 0 1 0 0 1 0 1 2 0 2 0 1 0 2 1 2 0 2 2 0 0 0 1 0 2 2 2 2 1 0
G12: 1 2 2 1 0 1 0 2 2 2 0 2 1 2 2 0 0 1 2 0 2 1 2 1 0 2 1 1 0 0 1 0 1 2 2 2
G13: 2 2 0 2 0 1 2 2 2 1 0 1 1 1 0 1 0 2 2 1 1 0 1 0 1 0 0 2 2 1 1 2 2 2 1 2
G14: 2 1 1 0 0 1 1 1 0 2 2 2 1 2 2 1 1 2 2 2 1 1 2 1 2 1 0 1 0 1 0 1 1 0 2 0
G15: 0 0 0 1 2 2 1 0 1 1 1 0 1 0 2 1 2 1 1 1 2 0 2 2 2 2 2 1 0 0 1 0 1 1 2 2

The target plane K is the span of the following two independent
column vectors over F_p:
K0: 0 0 1 1 0 0 1 2
K1: 1 1 2 2 2 1 2 1

For structural reference, F below is the coordinate matrix of the
p-power Frobenius map z -> z^p in the same 8-coordinate field basis
used by the b1 block and by K.  Matrix-vector convention is F*v.
F: 0 0 2 0 0 0 0 0
F: 0 0 0 0 0 0 0 1
F: 0 2 0 0 0 0 0 0
F: 2 0 0 0 0 0 0 0
F: 0 0 0 0 0 0 1 0
F: 0 0 0 2 0 0 0 0
F: 0 0 0 0 0 2 0 0
F: 0 0 0 0 2 0 0 0

Find a coefficient vector c of exactly 16 residues such that:
1. c is not the zero vector, and its first nonzero entry is exactly 1;
2. M(c) has rank exactly 6 over F_p; and
3. M(c)*K0=M(c)*K1=0, so K is exactly its two-dimensional kernel.
Other valid normalized coefficient vectors are accepted.

Give your final answer inside <answer></answer> tags as one JSON list
of exactly 16 integers.  Do not use ellipses or field-expression text.
Example: <answer>[0,0,0,0,1,2,0,1,0,2,1,2,0,0,0,0]</answer>
Output nothing else inside the tags.
```

</details>

## Difficulty and gates

`easy` is the provisional shipping preset because the paid oracle run could not complete.  The ladder grows the prime-field bit length while keeping the answer at 16 atoms.

| Preset | `n` (prime bits) | Approximate projective space |
|---|---:|---:|
| demo | 2, fixed (p=3) | 21,523,360 |
| easy (provisional ship) | 13 | (p^{15}\), about (10^{55}) in the measured shipping instance |
| medium | 19 | about (10^{85}) |
| hard | 29 | about (10^{130}) |

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 plants; 12/12 Frobenius invariant checks |
| G2 | pass | 7 corruptions rejected with 7 distinct reasons |
| G3 | pass | tagged fenced prose round-trips; garbage gives `None`; JSON-native |
| G4 | pass | 0/200,000; exact fraction (1/3.7665261522525977\times10^{54}) |
| G5 | pass | exact nullspace count 1; reference 31,522 ops / 0.008 s; strongest failing restart 2,048 candidates / 0.028 s |
| G6 | pass | five attacks at 0/8; reference elimination 8/8 |
| G7 | pass | every preset space increases; doubled `n=26` builds and verifies with 16 answer atoms |
| G8 | pass | 100/100 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 54 chars, about 14 tokens, 16 atoms, 40 intended operations |

## Oracle loop and G9 diagnostics

No oracle attempt was scored.  The installed OpenRouter key had exhausted its account-wide limit, so every call returned HTTP 403 and `harden.py` correctly stopped rather than treating API errors as failures.  Consequently there is **no oracle-backed `hardened` verdict** and the shipping choice remains provisional.

| Bare preset | Seed | Model | Scored | Outcome |
|---|---:|---|---|---|
| easy | 879606182 | anthropic/claude-sonnet-5 | no | HTTP 403 key limit |
| easy | 1211195251 | google/gemini-3.1-pro-preview | no | HTTP 403 key limit |
| easy | 469945907 | anthropic/claude-sonnet-5 | no | HTTP 403 key limit |
| easy | 116180086 | anthropic/claude-sonnet-5 | no | HTTP 403 key limit |

| G9 arm | Solved / scored attempts | Error redraws | Conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 | blocked by key limit |
| structural | 0/0 | 4 | blocked by key limit |
| placebo | 0/0 | 4 | blocked by key limit |

`hinted − placebo` is therefore undefined, not zero; these files document infrastructure failure, not model hardness.  The required rerun is `python3 ../../scripts/harden.py gen_2512_19324.py` after replenishing `OPENROUTER_API_KEY`, followed by the two isolated G9 runs.

## Use

```python
from gen_2512_19324 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
prompt = render(inst)
candidate = parse_answer("<answer>" + str(inst["answer"]).replace(" ", "") + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit examples with:

```bash
scripts/emit.sh 2512.19324 20 easy
```

## Caveats

- This is a Track B structural-recognition benchmark, not a complexity-hard decoding claim.  Any CAS or 16-variable modular eliminator solves it in milliseconds.
- The exact G4 probability is for the declared uniform projective prior.  It says random guessing is hopeless; it deliberately says nothing about the much stronger Frobenius-eigenspace prior, which is the intended shortcut.
- The cheap attacks cover single generators, one-pass greedy cancellation, all support-at-most-two (\pm1) patterns, a constant-(b_1) pattern, and random restarts.  No separate Gröbner-basis attack was run because the exact linear reference algorithm already dominates it for the supplied kernel constraints.
- `canonical_key` uses the characteristic and the basis-independent minimal polynomial of (\eta).  It was tested under generator reorderings, coordinate permutations, general (\mathrm{GL}(8,p)) congruences, target-basis swaps, and their composition, but it is not a complete canonical form for arbitrary matrix-space equivalence; it may over-collapse rare inequivalent instances sharing that invariant.
- Most importantly, the four-vendor hardness loop and the G9 comparison remain unmeasured because of the OpenRouter account limit.  The local gates are trustworthy; a release hardness claim is not yet justified.
