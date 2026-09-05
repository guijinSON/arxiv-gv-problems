# Verified generator for arXiv:2409.18758

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | polynomial coefficient table |
| Intended intuition | decomposition through the fibre coordinate `x^p+x` |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Wu and Yuan, [*Permutation polynomials over finite fields by the local criterion*](https://arxiv.org/abs/2409.18758). An instance gives a polynomial `P` over the native field `GF(p^2)=GF(p)[i]/(i^2+1)` and a promised support for its inverse. The solver must return the complete coefficient table of the compositional inverse. The checker reconstructs the local form, expands the inverse identity with exact field arithmetic, and compares every coefficient; it never reads `inst["answer"]`.

Generation uses Theorem 3.1(ii) with `a=1` and `b_1=0`. It samples `u=(u0,s)`, `v=(v0,s)`, and trace-zero `b_k=(0,t_k)` first, ensuring `u0-v0` and `c=u0+v0` are nonzero. It then expands

`P(x)=u*x^p+v*x+sum b_k*(x^p+x)^k`

and plants the paper's exact inverse

`(v-u)^(-1) * (x-g(c^(-1)*(x^p+x))-u*c^(-1)*(x^p+x))`.

Thus G follows from the theorem-backed construction, while V is an executable coefficient identity over a finite field.

## Why this is Track B

Track A would be false: Theorem 3.1 explicitly displays the inverse, and Theorem 3.3/Remark 3.4 gives a Dickson-matrix adjugate method for the paper's linearized regime. The disclosed generic reference algorithm evaluates `P`, forms the 33-unknown inverse interpolation system, and solves it by exact RREF. Its final measured shipping mean is **129,567 field operations and 0.0376 s** over eight successful runs; its stated bound is `O(m^3+r*m*log(p*m))` after `r<=p^2` rows.

The compact route recognizes that each nonlinear exponent block is a binomial expansion of `(x^p+x)^k`, recovers the local scalars, and applies Theorem 3.1 in **119 exact operations**. This is short enough after the insight, but executing 33 large modular coefficient calculations reliably without tools is not mechanical in context. Smaller primes were solved by the oracle pool, which is why the shipping field is `p=131071`.

## Worked demo (`p=3`, seed 0)

The complete rendered instance is:

```text
Recover a compositional inverse over a quadratic finite field

Let F = GF(3^2) = GF(3)[i]/(i^2+1). The prime 3 is 3 modulo 4, so
i^2+1 is irreducible. Encode r+s*i as [r,s], with 0 <= r,s <= 2.
Addition is coordinatewise modulo 3 and
    [r,s]*[t,w] = [(r*t-s*w) mod 3, (r*w+s*t) mod 3].
Composition is reduced modulo x^9-x.

P has this complete coefficient table on its fixed basis:
    exponent 1: [0,0]
    exponent 2: [0,2]
    exponent 3: [1,0]
    exponent 4: [0,1]
    exponent 6: [0,2]

Its inverse has coefficients only on [1,2,3,4,6]. Return exactly five
rows [[r,s],[e]] in increasing e order, including zero coefficients.

Give your final answer inside <answer></answer> tags as the JSON table.
Output nothing else inside the tags.
```

The answer is:

```text
<answer>[[[0,0],[1]],[[0,2],[2]],[[1,0],[3]],[[0,1],[4]],[[0,2],[6]]]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Changing the first coefficient to `[1,0]` returns `(False, "inverse coefficient mismatch at exponent 1")`. A person can solve this demo by recognizing the one `(x^3+x)^2` block or by checking the nine field elements on paper.

## Difficulty presets

| Preset | Prime `p` (`n` argument) | Terms | Status |
|---|---:|---:|---|
| demo | 3 | 5 | hand-scale; not hardened |
| easy | 127 | 33 | available; oracle solved 2/3 in the original ladder |
| medium | 8191 | 33 | available; oracle solved 2/3 in the original ladder |
| hard | 131071 | 33 | **shipping; held 0/3** |

The removed original easy rung `p=43` was solved 3/3. Escalation raises `p` while leaving the 33-term/99-atom witness fixed, so it grows the coefficient space rather than the answer length.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed witnesses; JSON round-trip |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware random candidates |
| G5 | pass | shipping density sample 0/200,000; unique inverse; demo exact count 1; 4,096-restart baseline failed in 0.428 s |
| G6 | pass | four attacks each 0/8; reference interpolation 8/8 |
| G7 | pass | next prime `524287 > 2*131071` builds and verifies with 33 terms |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | 690 chars, 173 estimated tokens, 99 atoms, 119 intended operations |

The G6 failures were an extreme conjugation/sign-orbit representative, coefficientwise inversion, 256 uniform fixed-support restarts, and the plausible by-hand ansatz that inverts only `u*x^p+v*x` and discards `g`.

## Bare oracle loop

| Tested `p` | Attempts solved | Outcome / recorded failures |
|---:|---:|---|
| 43 | 3/3 | defeated |
| 127 | 2/3 | one wrong exponent-1 coefficient; defeated |
| 8191 | 2/3 | one wrong exponent-9 coefficient; defeated |
| 131071 | 0/3 | wrong coefficient at exponent 2, 2, and 1; **hardened** |

The script-owned verdict is `hardened` after three escalations. All replies parsed; no API error or parser failure is counted as hardness evidence.

## G9 arms

| Arm at shipping | Solved / attempts |
|---|---:|
| bare | 0/3 |
| structural hint | 1/3 |
| placebo hint | 2/3 |

`hinted - placebo = -1/3`. On this small sample the structural sentence did not outperform generic prompt perturbation, so the diagnostic does **not** establish sensitivity to the claimed decomposition insight. The one hinted success is still consistent with the intended task becoming easier once the fibre coordinate is named; this arm is recorded, not gated. The hinted transcript contains one additional, cleanly completed escalated level because its isolated harness continued after the shipping solve; the table above counts only the three shipping rows.

## Use

```python
from gen_2409_18758 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
answer = parse_answer("<answer>...</answer>")
print(verify(inst, answer))
```

From the repository root:

```bash
bash scripts/emit.sh 2409.18758
```

## Caveats

- This is not cryptographic or average-case hardness. With finite-field arithmetic, the reference solver takes about 0.05 seconds; Theorem 3.1 is faster still.
- The 0/200,000 guess rate is for uniformly random coefficients on the exact promised support. It says nothing about a solver that recognizes the visible pure-imaginary binomial blocks; smaller fields show that such solvers often succeed.
- The attack panel did not run Gröbner-basis software, dense interpolation over all `p^2` field elements, symbolic factor recovery, or learned cross-instance attacks. Tool-enabled versions are expected to solve the family and do not contradict Track B.
- `canonical_key` handles input-row reordering and the only nontrivial field automorphism in this fixed quadratic presentation (conjugation). It does not identify alternative irreducible-polynomial presentations or arbitrary set bijections that fail to preserve the displayed field operations.
- `gvlib` has no finite-field helper, so the module carries a standard-library-only exact implementation; a missing `gvlib` installation does not change behavior.
