# arXiv:2205.13442 — integral points on `x^3 + x^2 y^2 + y^3 = k`

Lang & Rouse, *Rational points on x³ + x²y² + y³ = k* (math.NT).
Module: `gen_2205_13442.py`. Standard library only. **TRACK = "B"**.

**Verdict: SHIP.** G, H and V all clear with measured numbers.

---

## 1. The task

An instance publishes `m` integers `k_0 … k_{m-1}` and a bound `B`, and asserts
that at least one `k_j` is of the form `x³ + x²y² + y³` with integers
`|x|, |y| ≤ B`. The answer is the triple `[j, x, y]`.

`render()` gives the whole statement inline; nothing about the construction
(the spread of `x + y`, which entries are decoys, how they were made) appears in
it. Answer format is `<answer>j, x, y</answer>`.

Because `x³ + x²y² + y³` is symmetric, `(y, x)` is a second genuine witness and
`verify` accepts it. `verify` never reads `inst["answer"]`.

## 2. Why this is the paper's mathematics, not a surrogate

Section 3, first paragraph of the paper:

> the affine equation for `C_k` is symmetric in `x` and `y`. So letting
> `s = x + y` and `t = xy`, the equation of `C_k` becomes `s³ − 3st + t² = k`.
> Setting `X = −s` and `Y = t` the equation becomes `Y² + 3XY = X³ + k` and the
> map `(x,y) ↦ (s,t)` is a degree 2 map.

That is the introduction's morphism `φ₁(x:y:z) = (−xz−yz : xy : z²)` onto
`E_{1,k} : y² + 3xy = x³ + k`, the first of the three elliptic quotients whose
product the Jacobian of the genus-3 quartic is isogenous to.

The solver is handed the paper's own affine curve. Verification is exact integer
evaluation on that curve. `domain_essentiality = "native"`,
`reduction_kind = "none"`.

## 3. G — answer-first construction

`make_instance` samples the certificate before the instance exists:

1. draw `x₀ ∈ [H, 3H]`, draw `s₀` with `spread_min ≤ |s₀| ≤ spread_max`,
   set `y₀ = s₀ − x₀`;
2. evaluate `k_true = x₀³ + x₀²y₀² + y₀³`;
3. build `m − 1` decoys, each from an **independent draw of the same
   distribution** `(u, s_j)`, `t = −u(u − s_j)`, then pushed off the curve:
   * *near-miss*: `t ← t + δ`, `1 ≤ |δ| ≤ 50`. Then `(X,Y) = (−s_j, t)` is still
     an integral point of `E_{1,k_j}`, but the fibre discriminant `s_j² − 4t` is
     no longer a square, so `φ₁` has **no rational preimage**. This is exactly
     the degree-2 gap the paper's `C_k(Q) = φ₁⁻¹(E_{1,k}(Q))` has to respect: a
     solver who runs only the elliptic half of the reduction gets a hit on every
     one of these and must run the second square test to tell them apart.
   * *plain*: `k_j ← k_j + η`, `1 ≤ |η| ≤ 10⁶`, which kills the `E_{1,k_j}` point
     as well.
4. reject any decoy that (screened over `|s| ≤ max(4·spread_max, 400)`) actually
   carries a liftable point — a rejection test on decoys, never a search for the
   answer;
5. shuffle.

Nothing is ever solved for. Decoys are drawn from the plant's own magnitude law,
so `k_true` is not the smallest, largest or oddest entry (measured in §6).

## 4. V — exact verification

`verify` does integer evaluation of `x³ + x²y² + y³` in Python `int` and one
equality test, plus range tests. No floats anywhere in the path. Measured:

| | |
|---|---|
| `verify(inst, inst["answer"])` | **32 / 32 True** — 4 presets × 8 seeds |
| perturbations rejected | **176 / 176**, 10 distinct reasons |
| round trip `parse_answer(render-style prose)` | passes; garbage → `None` |

## 5. Answer cap

| preset | atoms | serialised chars |
|---|---|---|
| demo | 3 | 12 |
| easy | 3 | 16 |
| medium | 3 | 20 |
| **hard (shipping)** | **3** | **28** |
| escalate³(hard) | 3 | 29 |

Cap is 256 atoms / 2000 chars. Worst measured: **3 atoms, 29 chars**.
`json.loads(json.dumps(answer)) == answer` holds (plain `list[int]`).
Rendered statement at the hard preset is 1088 characters.

## 6. H — measured

Shipping preset `hard`: `height = 1e9`, `spread = (40, 220)`, `n_ks = 8`,
`near_miss_frac = 1.0`, `slack = 4` ⇒ `B = 4·10⁹`, `k_j ≈ 10³⁸` (38 digits).

### Mechanical cost — the standard route

For every integer `x ∈ [−B, B]` solve the cubic `y³ + x²y² + (x³ − k) = 0`
exactly (three monotone branches, bisected). This is how one hunts integral
points on a plane quartic with no extra structure, and it is what a solver
without `φ₁` has to do.

| | ops (cubic solves) | wall clock |
|---|---|---|
| exhaust the interval | **6.40 × 10¹⁰** | **1.7 × 10⁶ s ≈ 19 CPU-days** |
| expected-to-find (scan from `−B`) | **1.64 × 10¹⁰** | **4.3 × 10⁵ s ≈ 5 CPU-days** |
| after a mod-30030 congruence sieve | **9.36 × 10⁹** | 2.5 × 10⁵ s ≈ 2.8 CPU-days |

Per-op cost 1.75–2.6 × 10⁻⁵ s. **The extrapolation is validated by running the
scan to completion at the `medium` preset**: 3.51 × 10⁶ ops in 61.4 s measured
(1.75 × 10⁻⁵ s/op), against a 1.35 × 10² s sampled prediction for the full
9.6 × 10⁶-op interval.

### Compact route — what a solver who sees `φ₁` does

Scan `|s| = 0, 1, 2, …` across all `m` values at once; for each `s` test whether
`9s² − 4s³ + 4k_j` is a perfect square (that is the `E_{1,k_j}` half), and if so
whether `s² − 4t` is a perfect square (that is the `φ₁`-fibre half). Then
`x = (s+d)/2`, `y = (s−d)/2`.

**2 298 big-integer square-root tests, 2.8 ms** at the shipping preset
(stopped at `|s| = 143`, the planted spread). Worst case over the preset is
`m · 2 · spread_max ≈ 3 528`.

### The two numbers

| | |
|---|---|
| mechanical | **1.6 × 10¹⁰ operations** (5 CPU-days) |
| compact | **2.3 × 10³ operations** (2.8 ms) |
| **gap** | **≈ 7 × 10⁶** (2.8 × 10⁷ against full exhaustion) |

Neither is executable by brute force in context; only the compact one is
reachable at all, and only by finding the substitution. That is the Track B
claim, stated as such.

### Attacks run (all four fail at the shipping preset, 8 seeds each)

| attack | result | measured |
|---|---|---|
| `bruteforce_scan` — the mechanical route, budgeted | 0 / 8 | 4 × 10⁵ ops in 8 s; needs 6.4 × 10¹⁰ |
| `congruence_sieve` — admissible `x mod p` for `p ≤ 13`, CRT-sieved scan (the number-theorist's speed-up) | 0 / 8 | density 0.146, **speed-up 6.84×**, still 9.4 × 10⁹ ops |
| `lattice_coppersmith` — bivariate Coppersmith/Howgrave-Graham on `f(x,y) = x³+x²y²+y³−k`, shifts `f, xf, yf`, dim-12 lattice, **exact Fraction LLL implemented in-module** | 0 / 8 | shortest reduced `‖v‖₁ / N = 1.0000` (the trivial monomial row); the single monomial `X²Y² = B⁴` already exceeds `N` by a factor **11.37**, so the small-root condition is violated before reduction starts |
| `in_context_heuristics` — what a no-sandbox model can actually try: exhaustive `|x|,|y| ≤ 200`, plus `x ≈ k^{1/3}` and `x ≈ k^{1/4}, y = −x` with a ±3 window | 0 / 8 (also 0/8 at `easy` and `medium`) | 1.29 × 10⁶ candidate evaluations |

`reference_algorithm` (Track B: expected to succeed, reported separately) is the
`φ₁` reduction above: solved 8 / 8, 2 298 ops, 2.8 ms.

**Outlier diagnostic** (24 seeds, chance baseline 3.0 of 24 at `m = 8`): argmin /
argmax of magnitude, distance to nearest square, distance to nearest 4th power,
`k mod 2520` and bit length hit the planted index 1–5 times each — consistent
with chance (binomial sd ≈ 1.6). No per-`k` statistic separates the plant.

**Guess resistance.** 0 hits in 200 000 structure-aware samples; analytic
`p = 1 / (m(2B+1)²) = 2.0 × 10⁻²¹`.

## 7. `escalate` — grows the haystack, not the needle

Three parameters move; `height` does not, so the answer length is fixed:

* `spread` — doubled (both ends). This is literally the length of the compact
  route: a solver who has found `φ₁` still has to scan `s` over the whole range.
  Raising the *minimum* also deletes the "guess a tiny `s`" shortcut.
* `n_ks` — doubled (capped at 64). Every published value must be screened.
* `near_miss_frac` — driven to 1.0, so *every* decoy is a genuine
  `E_{1,k_j}(Q)` point with an irrational `φ₁`-fibre (maximum crowding).

Measured chain from `hard`, all building and verifying:

| step | spread | n_ks | compact ops | answer chars |
|---|---|---|---|---|
| hard | (40, 220) | 8 | 2 298 | 28 |
| ×1 | (80, 440) | 16 | 13 978 | 28 |
| ×2 | (160, 880) | 32 | 49 670 | 29 |
| ×3 | (320, 1760) | 64 | 149 676 | 29 |
| ×5 | (2560, 14080) | 64 | 1 367 232 | 29 |

**595× harder compact route at the same answer length** by step 5. `"cap_bound"`
is returned only when `spread_max` would exceed `height` (which would break
`|y| ≤ B`) — not reached at any shipping preset.

## 8. Presets

| preset | height | spread | n_ks | near_miss | B | k digits | mech ops | compact ops | gap |
|---|---|---|---|---|---|---|---|---|---|
| demo | 12 | (2, 6) | 2 | 1.0 | 48 | 6 | 194 | 22 | 9 |
| easy | 3 000 | (6, 40) | 4 | 0.5 | 12 000 | 16 | 9.6 × 10⁴ | 234 | 4.1 × 10² |
| medium | 200 000 | (15, 90) | 6 | 0.7 | 800 000 | 23 | 9.6 × 10⁶ | 568 | 1.7 × 10⁴ |
| hard | 10⁹ | (40, 220) | 8 | 1.0 | 4 × 10⁹ | 38 | 6.4 × 10¹⁰ | 2 298 | 2.8 × 10⁷ |

`demo` is deliberately solvable on paper: `k_0 = 145611`, `k_1 = 28359`,
`B = 48`; the compact route reaches `s = 5` in 22 square tests, and
`enumerate_all` confirms exactly 2 witnesses (the pair and its swap). The
in-context heuristic solves `demo` by design and nothing above it.

## 9. Caveats, stated rather than hidden

* **Track B, not Track A.** An efficient algorithm exists and it is the paper's
  own `φ₁`. The claim is only about the gap between it and the mechanical route,
  and both numbers are given above.
* **Insight-aware guessing.** A solver who has the substitution but cannot do
  the arithmetic still faces about `m · 2 · (spread_max − spread_min + 1) = 2 896`
  `(j, s)` pairs at the hard preset, i.e. `p ≈ 3.5 × 10⁻⁴` — far above the naive
  `2.0 × 10⁻²¹`. Both numbers are reported; the insight-aware one is the honest
  ceiling on this family's difficulty for a model that finds `φ₁`, and it is what
  `escalate` attacks by widening `spread`. Landing the guess still requires the
  4th root of a 38-digit integer to full precision.
* **`certificate_form` is `integer_tuple`.** The paper's certificate for a point
  on `C_k` genuinely is a pair of integers; nothing was flattened to make a gate
  easier. The rational-`k` case (which would give a rational certificate) is the
  case the paper's Theorem 1 explicitly does *not* cover, and the denominator of
  a rational `k` is a perfect 4th power, which hands the solver the common
  denominator for free — so it adds statement noise, not hardness.
* **Coppersmith was implemented, not merely argued.** Exact Fraction LLL on a
  dim-12 lattice, run for real. What was *not* run is a full Coron-style
  optimisation over shift sets; the reason is stated numerically above (`X²Y² >
  N` already), and the planted root sits at `|x| ≈ k^{1/4}`, which is the maximal
  root size the equation admits — precisely where the method has nothing to say.
* **Chabauty / Mordell–Weil was not run.** No CAS is available in-module, so
  neither Magma-style descent nor the paper's rank-zero argument was executed.
  The compact route does not need them: it is a bounded scan, not a proof of
  completeness. The family asks for *a* point, never for the full `C_k(Q)`.
* **`inst["params"]` carries `spread`.** It sits next to `inst["answer"]`, so it
  is answer-side metadata, but a harness that serialises the whole instance
  should not show `params` to a solver. `render()` never does.
* `make_instance(seed, **params)` is keyword-first (`seed` is the first
  positional). The repo's older `make_instance(n, seed=0, …)` convention is
  supported through an optional `n` kwarg that sets `height = 10**n`.
