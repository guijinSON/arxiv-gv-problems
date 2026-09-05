# Rejected PGL block-stabilizer candidate (arXiv:2408.14714)

Status: **rejected at H/G6 after a construction-aware audit**. The retained generator passes generation and exact verification, but its correct modular-barycenter attack constructs a valid certificate on 8/8 shipping instances. The earlier report tested an ordinary integer average instead of the average in `F_p`; that was the decisive error. `REJECTED.md` contains the reviewed cost comparison.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | matrix certificate |
| Intuition | invariant: the finite-field barycenter reveals the affine translation |
| Domain essentiality | native |
| Reduction | none |

## Problem family and provenance

[Paul Tricot, *On 3-designs from PGL(2,q)*](https://arxiv.org/abs/2408.14714) studies the action of fractional-linear transformations on subsets of the projective line. Section 2 supplies the exact native objects and the orbit–stabilizer relation. Lemma 12 proves that, for the multiplicative-subgroup block `B=<theta^r>` in the non-subfield regime, its full stabilizer is dihedral; Theorem 13 derives the resulting 3-design parameter.

An instance gives a prime `p` and an unordered affine image `S=sH+t` of the unique order-`k` subgroup `H` of `F_p*`. The solver must return a concrete nonidentity involution in `PGL(2,p)` that preserves `S`, as a normalized 2-by-2 matrix `[[a,b],[1,d]]`. Verification checks the shape, finite-field trace and determinant, applies the fractional-linear map to every point, and compares exact sets. It never reads the planted answer.

Generation is by transformation of a known instance. The generator first constructs `H`, samples `s,t`, and carries an inversion of `H` through `x -> sx+t`; it does not search for a stabilizer.

## Why the Track B claim fails

The initial Track B rationale used a generic exact algorithm that fixes three source points, enumerates ordered image triples, constructs the unique projective map, and tests block preservation. That is not the strongest algorithm for the generated distribution.

The exact distribution-specific algorithm uses the missing coefficient of `x^(k-1)` in `x^k-1`: the elements of `H` sum to zero, hence `t = k^(-1) sum(S)` in `F_p`. With any displayed point `x0`, it returns the conjugated inversion `[[t,(x0-t)^2-t^2],[1,-t]]`. At shipping `k=127` this is 135 high-level field operations. Measured over seeds 1000--1007, it verified on 8/8 instances in 0.0000205 seconds mean wall clock. The alleged compact route is exactly this same 135-operation algorithm, so the required mechanical-versus-compact gap is 1:1. Track A also fails because this is an exact `O(k)` method for the generated distribution.

The paper's other direct outputs do not rescue a family. Theorem 13 and Theorem 15 display `lambda` in closed form, while Lemma 12 and Lemma 14 explicitly identify the canonical stabilizers and exhibit their generators. Those native certificates have comparable mechanical and compact costs. H therefore fails even though G and V hold.

## Worked demo

For `make_instance(seed=0, **DIFFICULTY["demo"])`, the full mathematical data are:

```text
p = 31, k = 5
block = 17 16 21 8 6
Find a nonidentity involution [[a,b],[1,d]] over F_31, with d=-a,
nonzero determinant, whose fractional-linear action preserves the block.
```

The answer is `[[26,25],[1,5]]`. The barycenter is `(17+16+21+8+6)/5 = 26 (mod 31)`, and exact checking gives `verify(inst, [[26,25],[1,5]]) == (True, "ok")`. Corrupting the chart to `[[26,25],[0,5]]` gives `(False, "bottom-left entry c must equal 1")`. This demo is hand-solvable; the displayed sum and one modular inverse are small.

## Difficulty presets

| Preset | requested `k` (`n`) | field lower bound | seed spread | Status |
|---|---:|---:|---:|---|
| demo | 5 | 31 | 0 | hand example |
| easy | 23 | 100,003 | 20,000 | locally verified; oracle unavailable |
| medium | 61 | 10,000,019 | 100,000 | locally verified |
| hard | 127 | 1,000,000,007 | 1,000,000 | proposed shipping preset; oracle validation pending |

The actual prime is the first prime congruent to 1 modulo `k` after a seed-selected target. `escalate()` grows both the subgroup and ambient field while retaining a four-entry witness, and returns `cap_bound` before the 300-operation route cap is exceeded.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted certificates verified (four presets × four seeds) |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced, tagged model-style JSON round-tripped; answer is JSON-native |
| G4 | pass | 0/200,000 uniform candidates valid; candidate space 1,430,363,497,277,780,550 |
| G5 | pass | shipping theorem count 127, density `8.8789e-17`; demo brute-force count 5; reference baseline measured above |
| G6 | **fail** | the corrected modular-barycenter attack succeeds 8/8; 135 operations and 0.0000205 s mean |
| G7 | pass | doubling `n` raised `k` 127→257 and candidate space to 4,258,319,818,024,593,362; four answer atoms unchanged |
| G8 | pass | 80 invariance and 80 carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 37 characters, about 10 tokens, four atoms, 135 intended-route operations |

The five failing attacks were: smallest value as translation outlier, ordinary-integer barycenter, swapping the first pair while fixing the third, reversing the first triple, and 256 random involution restarts. Display order, affine scale, translation, and field prime are randomized from the local seeded RNG.

## Oracle and G9 diagnostics

The harness produced no scoreable attempt. These are infrastructure errors, not evidence of hardness.

| Run | Preset | Recorded seeds | Solved / attempts | Result |
|---|---|---|---:|---|
| bare | easy | 313930867, 1278933911, 644964914, 51841799 | 0 / 0 | four HTTP 403 key-limit errors |
| structural hint | hard | 1197173652, 1459216028, 652573907, 1914319200 | 0 / 0 | four HTTP 403 key-limit errors |
| placebo hint | hard | 661022520, 874962627, 299704307, 1952433845 | 0 / 0 | four HTTP 403 key-limit errors |

Thus `hinted - placebo` is undefined, and no conclusion can be drawn about whether the barycenter hint supplies useful structural information. The structural sentence only names the invariant; it does not give the subsequent matrix construction. The bare transcript was written by `harden.py`, and the two arm transcripts were produced in separate scratch directories as required.

## Use

```python
from gen_2408_14714 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, after a successful oracle rerun:

```bash
bash scripts/emit.sh 2408.14714 20 hard
```

## Caveats

The tiny uniform-guess density is not evidence of hardness: it ignores the deterministic modular-barycenter prior forced by the generation promise. This is precisely why the family is rejected despite passing G4. The generic three-point search remains useful as a historical measurement, but it is not the honest baseline for this distribution.

No external CAS, specialized permutation-group package, or alternative symbolic stabilizer algorithm was benchmarked. The inexpensive attacks are construction-aware but not exhaustive. Canonicalization relies on the proved fact that all generated blocks with fixed `(p,k)` lie in one `PGL` orbit; it is not a general projective-set isomorphism algorithm. Finally, the required model-hardness and hint-sensitivity evidence remains absent until OpenRouter quota is restored, so this result must not be submitted as hardened yet.
