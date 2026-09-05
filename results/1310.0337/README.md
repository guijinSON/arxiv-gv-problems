# Gaussian-period coefficients for binomial permutation polynomials

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | polynomial over GF(2), serialized by its support |
| Intended intuition | symmetry: Frobenius swaps the quadratic-residue and nonresidue period sums |
| Domain essentiality | native; no reduction |

This is a native finite-field family from Tu, Zeng, Hu, and Li, [*A Class of Binomial Permutation Polynomials*](https://arxiv.org/abs/1310.0337). The solver receives the cyclotomic presentation
`F = GF(2)[beta]/Phi_p(beta)`, a public cube `W` on the unit circle, and must give the support of a polynomial `z` satisfying `z^2+z+1=0`. The resulting `u=Wz` is checked exactly to be a noncube on the unit circle. Theorem 1 and Proposition 3(3) then certify that `X^d+uX`, with `d=6(2^m-1)+1`, permutes `F`. Verification uses only carryless polynomial arithmetic, Frobenius squaring, and exact exponentiation; it never reads the planted answer.

## Why Track B

Track A would be false. Section 3 gives efficiently checkable power conditions, and a generic algorithm can obtain `z` by exponentiating trial field elements to `(2^(2m)-1)/3`; equivalently, one can solve `(Frobenius+I)z=1` by Gaussian elimination over GF(2). At the provisional shipping preset `m=89`, binary exponentiation succeeds on 8/8 audited instances in about 0.006 seconds and accounts for 712,467 schoolbook coefficient products plus Frobenius coordinate moves. The packed linear solve also succeeds 8/8, using 246,662 bit-XOR operations.

The compact route is different. Because `p=2m+1`, `2` is primitive modulo `p`, and `p` is 3 modulo 4, the sum of `beta^a` over the nonzero quadratic residues `a mod p` is a root: squaring changes its support to the nonresidues, while `Phi_p(beta)=0` makes the two period sums add to `1`. Listing the `m` residues costs `m` modular squarings—89 at the provisional shipping preset—and no finite-field root extraction. Proposition 3's easy regime is exactly why `m` is restricted to odd values with `5` not dividing `m`; the additional `3`-avoidance keeps the order-three period outside the cube subgroup.

## Worked demo

With `make_instance(n=1, seed=4)`, the complete rendered mathematical data are:

```text
F = GF(2)[beta] / (1 + beta + beta^2),  p=3, m=1, q=2.
U = {y in F : y^3=1}; W=1; d=7.
Find nonconstant z with z^2+z+1=0 and output its increasing support.
The checker also requires u=Wz to satisfy u^3=1 and u!=1.
```

Since `beta^2+beta+1=0`, a person can solve this demo on paper:

```python
>>> inst = make_instance(n=1, seed=4)
>>> inst["answer"]
[1]
>>> verify(inst, [1])
(True, 'ok')
>>> verify(inst, [])
(False, 'support must not be empty')
```

The full renderer additionally defines the canonical support encoding, inclusive exponent bounds, the two accepted roots, and the exact `<answer>...</answer>` wire format.

## Difficulty

| Preset | Requested `n` | Actual `m` | `p` | Field degree | Planted support atoms |
|---|---:|---:|---:|---:|---:|
| demo | 1 | 1 | 3 | 2 | 1 |
| easy | 29 | 29 | 59 | 58 | 29 |
| medium | 89 | 89 | 179 | 178 | 89 |
| hard | 173 | 173 | 347 | 346 | 173 |

`medium` is provisionally selected. The oracle ladder has not produced a hardness verdict because the configured OpenRouter key returned HTTP 403 “Key limit exceeded” on every redraw; this is an infrastructure block, not a passed or failed oracle gate. If all named presets are solved, escalation tries `m=209`, `221`, and `233`; the next admissible `m=329` exceeds the 256-atom answer cap and correctly returns `cap_bound`.

## Local gates

| Gate | Result | Measurement at provisional shipping preset |
|---|---|---|
| G1 planted | pass | 12/12; prime/order, unit-circle, cube/noncube checks; demo binomial exhaustively bijective |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round trip | pass | tagged JSON recovered from prose and fences |
| G4 guessing | pass | 0/200,000; exact density `2/(2^178-2)` = 5.22e-54 |
| G5 cost | pass | random restart: 256 trials, about 0.011 s; reference cost 712,467 primitive operations |
| G6 attacks | pass | each of 5 attacks: 0/8; both reference algorithms: 8/8 as expected |
| G7 scaling | pass | doubling request gives `m=209`, a 418-bit candidate space, and verifies |
| G8 canonical key | pass | 120/120 Frobenius/composed relabellings invariant; 20/20 unrelated keys distinct |
| G9 caps | pass | 300 worst-case characters, 90 atoms, 75 estimated tokens, 89 intended operations |

The failing attack panel comprises support statistics of the random public cube, a diagonal-only Frobenius solve, monomial/binomial guesses, regular support patterns available by hand, and 256 uniform restarts.

## Oracle loop and G9 diagnostics

The script-owned bare run is currently incomplete:

| Arm / preset | Calls | Solved | Outcome |
|---|---:|---:|---|
| bare / easy | 4 redraws | n/a | every call was HTTP 403; harness aborted without a claim |
| structural hint | 0 | 0 | not run: same exhausted key |
| placebo hint | 0 | 0 | not run: same exhausted key |

Consequently `hinted - placebo` is not yet meaningful. The checked size figures are 300 worst-case characters, 90 atoms, about 75 tokens, and 89 exact modular squarings after the insight. The oracle and G9 rows must be updated from script-produced transcripts before submission.

## Use

From this directory:

```python
from gen_1310_0337 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
print(render(inst))
answer = parse_answer("<answer>...</answer>")
print(verify(inst, answer))
```

From the repository root, after a successful oracle run:

```bash
bash scripts/emit.sh 1310.0337 20 medium
```

The module uses only the Python standard library; `gvlib` has no finite-field helper needed by this representation.

## Caveats

The exact guessing probability is for a uniform prior over all canonical nonzero, nonconstant field polynomials. It does **not** model a solver that already knows Gaussian periods; such a solver goes straight to the short route. The random `W` diversifies the actual permutation-polynomial coefficient but does not make the quadratic root equation harder, so this family deliberately measures recognition of the residue symmetry, not generic finite-field cryptanalysis. The audit did not run a CAS implementation, a normal-basis conversion, or a vendor oracle because the external quota was exhausted; two exact in-module reference algorithms cover their core algebraic routes, but the required multi-vendor evidence remains missing.
