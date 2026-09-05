# Cauchy resolution completion — arXiv:1706.01800

| profile | value |
|---|---|
| Track | **B** — no-tool compression; an efficient algorithm is known |
| Native domain / regime | algebra / finite field |
| Core / certificate | linear algebra / integer tuple representing an `F_q` vector |
| Objects | partite complex, generalized Cauchy matrix, transversal resolution block |
| Intuition | change of variables to a rational-function residue vector |
| Essentiality | native; no surrogate reduction (`reduction_kind="none"`) |

## What the family asks

The paper [*Hypergraph F-designs for arbitrary F*](https://arxiv.org/abs/1706.01800) defines an `F`-decomposition as copies of `F` covering every edge exactly once. Section 8.2, Theorem 8.1 constructs a resolvable clique decomposition of the complete `f`-partite complex `K_(q×f)` from a Cauchy matrix. This generator uses its `r=2` completion problem: given one selected field-labelled vertex and a resolution-class value, return the unique transversal `f`-set containing it. A candidate is checked by exact modular matrix-vector products, so verification is deterministic and cheap.

Generation does not solve the displayed system. It samples a nonzero scale and diagonal column multipliers, evaluates the partial-fraction identity

`R(X)/D(X) = Σ_j R(y_j)/D'(y_j)/(X-y_j)`,

then permutes the rows and columns. Diagonal column scaling preserves every nonzero Cauchy minor, so Theorem 8.1 still gives uniqueness.

## Why Track B

Theorem 8.1 itself identifies the efficient method: solve a nonsingular `(f-1)×(f-1)` finite-field system. The reference Gauss–Jordan implementation is `O(f³)` and, at the shipping preset, used **116,184 exact field operations in 0.004–0.017 s** across repeated preflights (8/8 instances solved, as expected). A specialized Cauchy solver can do still better asymptotically; this family makes no Track-A claim.

The compact route is different. Absorb each public column scale into `u_j=s_j z_j`, recognize a Cauchy nullvector as a residue vector, and sort the consecutive `y` values. The fixed value and target show that the remaining numerator polynomial is constant. Consecutive residues then obey

`u_(j+1) = -u_j (f+j)(f-1-j) / ((j+2)(j+1)) mod q`.

Removing each column scale gives the answer in **239 exact field operations** (counting each field addition, multiplication or division once), versus 116,184 for elimination. The rendered problem does not state this recurrence, and `selftest()` independently executes it on 20 instances.

## Worked demo

For `make_instance(n=5, q=11, seed=0)`, the zero rows are `1,0,2`, the target row is `x=3` with value `4`, the columns `(y,s)` in part order are `(4,7),(8,9),(5,7),(6,1),(7,5)`, and part 0 is fixed to value 9. The task is to find five residues `z` for which every zero-row Cauchy sum is 0 and the target-row sum is 4.

<details><summary>Full rendered demo instance</summary>

```text
Cauchy resolution completion over F_11

The finite field F_11 is represented by the integers 0,...,10, with all
arithmetic modulo 11.  For a nonzero residue a, a^(-1) means its unique
multiplicative inverse modulo 11.

There are 5 labelled parts, numbered 0,...,4; part j has one choice for
every value z_j in F_11.  A transversal block is a vector
z=[z_0,...,z_4] selecting exactly one value from every part.

For a row generator x and the displayed column data (y_j,s_j), define

    L_x(z) = sum over j=0,...,4 of s_j*z_j*(x-y_j)^(-1)  (mod 11).

All displayed x and y values are distinct, so every inverse exists.  Find the
unique transversal block z satisfying all of the following:

  1. L_x(z)=0 for every x in the zero-row list;
  2. L_3(z)=4; and
  3. z_0=9.

The zero-row generators (their order is irrelevant) are:
  1, 0, 2

The target-row generator is x=3 and its required
value is 4.

Column data, in labelled part order:
  part 0: y=4, s=7
  part 1: y=8, s=9
  part 2: y=5, s=7
  part 3: y=6, s=1
  part 4: y=7, s=5

The fixed choice is part 0, value 9.

Give your final answer inside <answer></answer> tags as one JSON list of exactly
5 integer residues in part order.  Indices are 0-based, repetitions between
different parts are allowed, and every entry must lie in 0..10 inclusive.
Example of the syntax only: <answer>[0, 1, 2]</answer>
Output nothing else inside the tags.
```

</details>

```python
inst["answer"]                         # [9, 10, 9, 9, 10]
verify(inst, inst["answer"])           # (True, "ok")
verify(inst, inst["answer"][:-1])      # (False, "expected exactly 5 coordinates, got 4")
```

This demo can be solved on paper by four-variable elimination over `F_11`; the larger presets are deliberately not hand-elimination scale.

## Difficulty

| preset | `f=n` | `q` | candidate-space bits | status |
|---|---:|---:|---:|---|
| demo | 5 | 11 | 14 | hand example; never ships |
| easy | 32 | 257 | 249 | oracle run attempted; infrastructure error |
| medium | 36 | 4099 | 421 | not reached |
| hard | 48 | 65537 | 753 | provisional shipping preset pending oracle loop |

`escalate()` first increases `q` at fixed answer length. It returns `cap_bound` only after the field-height ladder and the 300-operation limit prevent further useful growth.

## Gates

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 JSON round-trips |
| G2 | empty, dropped, swapped, duplicated and out-of-range corruptions rejected with 5 distinct reasons |
| G3 | realistic prose + fenced tagged answer round-tripped; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses; language size `65537^47` |
| G5 | demo has exactly 1 solution among 14,641; shipping density sample 0/200,000; reference 116,184 field operations |
| G6 | scale-rank outlier, one-row greedy, 256 restarts and constant ansatz each succeeded 0/8; reference elimination solved 8/8 |
| G7 | ladder sizes strictly increase; doubled `n=96` builds and verifies |
| G8 | 100/100 relabelling invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 332 chars, 83 estimated tokens, 48 atoms, 239 intended operations; compact route verified 20/20 — within every cap |

## Oracle loop and G9 arms

The required script-owned loop was invoked twice on 2026-09-05. Both vendors returned HTTP 403, `Key limit exceeded (total limit)`, before a valid attempt. The transcript preserves those errors; they are not counted as solver failures. Consequently no hardness verdict or shipping-preset claim is made yet.

| arm | solved / valid attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 | blocked by OpenRouter quota |
| structural hint | 0 / 0 | not run |
| placebo hint | 0 / 0 | not run |

The hinted-minus-placebo diagnostic is therefore unavailable, not zero evidence. Once quota is restored, rerun the bare loop first, slide `SHIPPING_DIFFICULTY` if required, rerun `selftest()`, then run the two G9 copies in separate scratch directories.

## Use

```python
from gen_1706_01800 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer("<answer>[...]</answer>")
ok, reason = verify(inst, candidate)
```

After a valid `harden.py` verdict, emit from the repository root with:

```bash
bash scripts/emit.sh 1706.01800 20
```

## Caveats

This is an intentionally easy-for-computers Track-B family: ordinary elimination always solves it quickly, and a structured `O(f²)` Cauchy solver was not benchmarked. The 0/200,000 estimate uses candidates that already have the correct length, field range and fixed coordinate; it measures uniform density in that language, not resistance to algebraic reasoning. The attack panel does not include Gröbner-basis software or optimized coding-theory decoders because exact linear elimination already dominates the honest algorithmic story. Most importantly, the paid multi-vendor oracle and both G9 diagnostics remain uncompleted due to external quota, so this directory is **not submission-ready** despite passing the local gates.
