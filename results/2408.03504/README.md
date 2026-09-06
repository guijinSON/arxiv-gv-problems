# Planted low-rank tensor completion at the rigidity threshold

**Paper:** arXiv:[2408.03504](https://arxiv.org/abs/2408.03504) — *Sample Complexity of
Low-rank Tensor Recovery from Uniformly Random Entries* (math.CO, cs.IT, math.AG, math.PR).

## Profile

| field | value |
|---|---|
| `TRACK` | **A** (structural hardness) |
| native domain | algebra (multilinear algebra / secant varieties of Segre varieties) |
| object regime | `rational_exact` — integers and exact rationals end to end, no float anywhere |
| computational core | `polynomial_identity` (a sparse system of multilinear equations over ℚ) |
| certificate form | `matrix_certificate` (a `d`-dimensional point configuration, `N×d` integers) |
| intended intuition | `constraint propagation` |
| `domain_essentiality` | **native** — `reduction_kind = none`, `reduction = None` |

The solver is handed the paper's own objects: a partially observed order-`k` tensor over
ℚ and, implicitly, the `k`-partite `k`-uniform hypergraph of revealed positions
(Section 2, *Rigidity Formulation of the Tensor Completion Problem*). `verify` operates on
those objects. Nothing was compiled away.

## What the family is

A rank-`d` order-`k` tensor is built **factors first**: sample a point configuration
`p : V₁ ⊔ … ⊔ V_k → ℤ^d` with every coordinate a nonzero integer of absolute value ≤ `B`,
form

```
T[i₁,…,i_k] = Σ_{j<d} Π_{a<k} p[off_a + i_a][j]        (the paper's eq. 1.1 / 2.1)
```

then reveal a **uniformly random** subset Ω of `m` entries. The solver sees only the
revealed entries and must produce *any* configuration reproducing all of them.

Checking is one pass over Ω: `m·(d(k−1)+(d−1)) = 420` exact integer operations at the
shipping preset. No search, no oracle, no float.

Nothing is ever solved in `make_instance`; the certificate is the configuration we started
from. The revealed pattern is resampled only until the paper's own uniqueness certificate
holds — a condition on the hypergraph alone, never on the answer (median 1 try, worst
observed 3).

## Why the answer is unique — and why that is checked, not assumed

Theorem 1.1 says `n log n + d n log log n` uniformly random entries determine a generic
rank-`d` tensor **whp**. That is asymptotic, so it is not what this module relies on.
Instead every emitted instance is certified exactly by **Theorem 3.11** (`thm:MM_test`),
whose three conditions are finite linear algebra:

| condition | what is computed | value at shipping |
|---|---|---|
| (i) `G` globally rigid in ℝ¹ — Theorem 4.1 | `rank_ℝ I_G = rank_GF(2) I_G = N−(k−1)` | 28 = 28 = 28 ✓ |
| (ii) `G` locally rigid in ℂ^{d+1} — Prop. 2.9 | `rank J f_G^{d+1}(q) = (d+1)(N−(k−1))` | 84 = 84 ✓ |
| (iii) Masaratti–Mella | `dim(⋂_{ω∈ker I_G} ker A_ω) = k` | 3 = 3 ✓ |

plus Prop. 2.9 **at the planted point itself** (`rank J f_G^d(p) = d(N−(k−1))`, 56 = 56 ✓),
which makes the plant a regular point of its own fibre. Together: `G` is globally rigid in
𝔽^d, i.e. **the completion is unique up to the stabiliser**.

Condition (ii) is the binding one and fixes the sample size:
`m = (d+1)(N−(k−1))`. At dims `[10,10,10]`, `d=2`: **m = 84 of 1000 entries, 8.4 % density**.
Below it the certificate fails and the family would be broken; the sweep confirms the cliff
is sharp (at dims `[4,4,4]`: 0/20 certified at `m=28`, 20/20 at `m=30 = (d+1)(N−k+1)`).

**Measured completion multiplicity.** One tensor. `enumerate_all` at the `demo` preset does
this *exhaustively* over all `6⁹ = 10 077 696` points of the language and finds
**exactly 4** valid answers — precisely the stabiliser orbit the theorem predicts (4 sign
scalings with `λμν = 1`, `d! = 1` term orderings). At the shipping preset the certified
count is **32** accepted answers (`[4,4]` scalings per rank-one term × `2!` orderings) out of
a language of `12⁶⁰ = 5.6e64`, i.e. density **5.7e-64**.

## Why it is hard (Track A)

Section 1.2, immediately after Theorem 1.1: *no polynomial-time algorithm is known for
recovering low-rank tensors from `O(n log n)` samples, even experimentally*, and the paper's
bound supports the **Barak–Moitra** conjecture that the information-theoretic and
computational thresholds differ for order ≥ 3 tensors. Every prior algorithmic guarantee the
paper improves on needs `O(n^{k/2} polylog n)` samples (Jain–Oh, Yuan–Zhang,
Potechin–Steurer, Liu–Moitra) and all of them are flattening/unfolding methods. This family
is placed *inside that gap by construction*: the sample count is pinned to the
information-theoretic (rigidity) threshold, which is where no algorithm is known.

The regime that had to be avoided is the dense one, and it is avoided by measurement rather
than by faith. The **same** domain-standard attack, on the **same** distribution, at the
**same** rigidity threshold:

| dims | m | density | `(d+1)`-minor elimination |
|---|---|---|---|
| `[4,4,4]` | 30 | 46.9 % | **completes 10/10**, mean 7 036 ops |
| `[8,8,8]` | 66 | 12.9 % | completes 1/15, recovers 7 % |
| `[10,10,10]` **(ships)** | 84 | 8.4 % | **completes 0/8**, recovers **0 of 916** missing entries |

The reason is structural, and it is measured: **0 of 3000 sampled `(d+1)×(d+1)` minors of the
unfoldings carry fewer than three unknown entries** at the shipping preset, so the
elimination route has nothing to linearise — not merely nothing for its greedy form.

## Worked example (`demo`, seed 11)

Rank 1, `3×3×3`, 14 of 27 entries. Rendered in full by `render(inst)`; the listed entries are

```
0 0 1 -6 | 0 0 2 -12 | 0 1 2 8 | 0 2 0 8 | 1 0 0 -18 | 1 0 2 18 | 1 1 2 -12
1 2 0 -12 | 1 2 1 6 | 1 2 2 12 | 2 1 0 -4 | 2 1 1 2 | 2 2 0 4 | 2 2 2 -4
```

Answer `2 -3 1 3 -2 2 2 -1 -2`; `verify` → `(True, 'ok')`. Flip the first sign and
`verify` → `(False, 'mismatch_at_0,0,1_got_6_expected_-6')`. **A person can solve this
one by hand**: rank 1 means every entry is a product, so ratios of entries sharing two
indices give the vectors up to the sign/scale gauge, and `enumerate_all` confirms only 4
answers exist. The shipping preset is not hand-scale, which is the point.

## Difficulty presets

| preset | dims | d | B | m | M | density | answer atoms | chars | route ops |
|---|---|---|---|---|---|---|---|---|---|
| demo | `[3,3,3]` | 1 | 3 | 14 | 27 | 51.9 % | 9 | 23 | 28 |
| easy | `[6,6,6]` | 2 | 5 | 48 | 216 | 22.2 % | 36 | 88 | 240 |
| medium | `[8,8,8]` | 2 | 5 | 66 | 512 | 12.9 % | 48 | 118 | 330 |
| **hard (ships)** | `[10,10,10]` | 2 | 6 | 84 | 1000 | **8.4 %** | 60 | 148 | 420 |

`[4,4,4]` was rejected as a shipping preset **by G6**: the domain-standard minor elimination
solves it 10/10. `easy` and `medium` are on the ladder for the oracle loop, not shipped.

## Escalation — haystack, not needle

Every rung moves **two** axes: the order `k` (with block sizes rebalanced so `N = 30`, hence
the answer length `d·N`, stays put) and the coefficient bound `B`.

| rung | dims | k | B | m | M | density | answer atoms | certified unique |
|---|---|---|---|---|---|---|---|---|
| ship | `[10,10,10]` | 3 | 6 | 84 | 1 000 | 8.40 % | 60 | yes |
| +1 | `[8,8,7,7]` | 4 | 12 | 81 | 3 136 | 2.58 % | 60 | yes |
| +2 | `[6,6,6,6,6]` | 5 | 24 | 78 | 7 776 | 1.00 % | 60 | yes |
| +3 | `[5,5,5,5,5,5]` | 6 | 48 | 75 | 15 625 | 0.48 % | 60 | yes |
| +4 | `[4,4,4,4,4,4,4]` | 7 | 96 | 66 | 16 384 | 0.40 % | 56 | yes |
| +5 | — | | | | | | | `cap_bound` |

The answer stays 56–60 atoms the whole way while the ambient space grows 16× and the
sample density falls 21×.

## Gate results

| gate | measured | pass |
|---|---|---|
| G1 planted verifies | 32/32 (4 presets × 8 seeds) | ✓ |
| G2 rejects corruption | 12 corruptions, all rejected, 10 distinct reasons | ✓ |
| G3 round trip | parses from a prose+fenced reply, rejects junk | ✓ |
| G4 guess resistance | **0 hits / 200 000** samples; analytic `P = 5.7e-64` (space `12⁶⁰ = 5.6e64`, 32 valid); naive `4.7e-66` | ✓ |
| G5 density + cost | 1 completion, 32 accepted answers, density `5.7e-64`; demo exact count **4** (exhaustive, = theorem prediction); strongest attack costs 0 recovered entries in 2.3 ms, mechanical route `1.3e26` ops / `1.1e20` s | ✓ |
| G6 adversary panel | **6 attacks, 0 successes each over 8 seeds** | ✓ |
| G7 scales | escalate moves `dims` + `B`; escalated instance builds, verifies, certifies; size-doubled `[20,20,20]` builds and verifies | ✓ |
| G8 canonical key | 120/120 invariant under relabelling, 120/120 transformed instances verify, 24/24 distinct keys | ✓ |
| G9 caps | 147 chars, 60 atoms, ~37 tokens, 420 route ops (caps 2000 / 256 / 1000) | ✓ |

### The adversary panel in detail

| attack | what it is | result |
|---|---|---|
| `minor_elimination_domain_standard` | the **domain-standard** route: every mode-`i` unfolding has rank ≤ `d`, so a `(d+1)×(d+1)` minor carrying one unknown is linear in it — solve and propagate to closure | 0/8; recovers **0 of 916** missing entries |
| `flattening_full_fiber_subspace` | the cheap flattening attack: `d` fully observed fibres span the column space | 0/8; **0** fully observed fibres exist |
| `alternating_exact_solve_restart_32` | exact ALS: random restart in the language, then exact `d×d` re-solves | 0/8 (0 of 256 restarts) |
| `greedy_gauge_propagation` | gauge-fix `d(k−1) = 4` coordinates for free, then propagate | 0/8; never gets past the 2 vectors it is given (2 of 30) |
| `outlier_divisibility_and_magnitude` | per-position statistics (gcd of incident values, magnitude) | 0/8 |
| `csp_backtracking_finite_domain` | the **in-context** attack: 144 candidate vectors per position, 84 constraints, best-first variable order, full checking | 0/8 at 3 000 000 nodes each |

**Baseline cost, the honest number.** Propagation with vectors handed over *for free* needs
a median of **11** (range 11–13) whole vectors before it closes. That is the mechanical
route: `12²·¹¹ = 5.5e23` seed guesses, `1.3e26` exact operations, `1.1e20` seconds
extrapolated from the measured per-propagation time. Grid brute force over the whole
language is `12⁶⁰ = 5.6e64`.

## The G9 arms

| arm | solved/attempts |
|---|---|
| bare | not run |
| hinted | not run |
| placebo | not run |

**Not run in this environment — there is no `OPENROUTER_API_KEY` here**, so neither STEP 4
nor the three-arm diagnostic was executed. G9(a) and G9(b) are recorded-not-gated, so this
does not block the gates, but it does mean **the oracle evidence for this family is absent
and must be supplied by STEP 4 before it is trusted**. `llm_loop_transcript.jsonl`,
`.meta.json`, `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl` are therefore
not present.

Measured G9(c): answer **147 chars / 60 atoms / ~37 tokens**; intended route **420**
operations.

## How to use it

```python
import gen_2408_03504 as g
inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))                                  # the whole problem statement
flat = [x for v in inst["answer"] for x in v]
print(g.verify(inst, flat))                            # (True, 'ok')
print(g.uniqueness_certificate(inst)["unique"])        # True, by Theorem 3.11
print(g.selftest()["all_passed"])                      # True, ~70 s
```

```bash
scripts/emit.sh 2408.03504
```

## Caveats — read these

1. **`intended_route_operations = 420` is the checking route, not a solving route.** This is
   a Track A family: *no* solving route of any length is known at this sample density, which
   is the hardness claim itself (Section 1.2). The 1000-operation cap exists to keep out
   calculator tests; this is a search test. If you read that number as "a solver needs 420
   operations", you have misread it. Argue with it — the number is stated, not rounded down.
2. **The oracle loop was not run** (no API key). Gates are not evidence of oracle hardness.
3. **Genericity.** Theorem 3.11 concludes global rigidity for all *generic* configurations —
   entries algebraically independent over ℚ. The plant is a random small-integer
   configuration, which is not generic in that sense. What *is* certified pointwise is
   Prop. 2.9 at the planted point (local rigidity, so the plant is isolated in its own fibre
   modulo the stabiliser). Global uniqueness at the specific rational point therefore rests
   on Theorem 3.11 plus the exhaustive demo count (4 = predicted 4) plus 200k sampled
   candidates and six attacks finding no second solution. It is not a pointwise proof.
   Because `verify` accepts *any* configuration reproducing Ω, grading is correct either
   way — multiplicity only affects the difficulty claim, not correctness.
4. **`P(guess) = 5.7e-64` assumes the prior `random_candidate` samples**: uniform nonzero
   integers in `[-B,B]`, which is everything the statement gives away. It says nothing about
   a solver who partially propagates and then guesses; the honest number for that is the
   min-seed measurement (11 vectors, `5.5e23`).
5. **The asymptotic gap is asymptotic.** At `n = 10`, `n log n ≈ 23` and `n^{3/2} ≈ 32` are
   not separated by anything; the shipped `m = 84` is fixed by parameter counting
   (`(d+1)(N−k+1)`), not by `n log n`. The gap this family exhibits is the *measured* one in
   the table above — the same attack going 10/10 → 0/8 as density falls from 47 % to 8.4 % —
   not a numerical instance of the asymptotic separation. Do not cite Theorem 1.1 as if it
   proved hardness at `n = 10`; it does not, and neither does this README.
6. **Attacks not tried.** No Gröbner basis / F4 on the 60-variable trilinear system (no CAS
   available here — this is the one attack a specialist would reach for that is missing, and
   it is the most likely way this family falls); no lattice reduction on a linearised
   Macaulay matrix; no SDP/nuclear-norm relaxation (all such methods are flattening-based and
   the flattening attack is already measured to have zero purchase, but the relaxation itself
   was not run); no SAT/SMT encoding of the finite-domain CSP beyond the hand-written
   backtracker.
7. **`easy` is genuinely easy** — the minor route completes 3/5 there. If the harness holds
   at `easy`, be suspicious of the harness, not of the family.
8. **A bug worth remembering.** The first ALS attack was seeded from the *same* PRNG stream
   as the generator and reported 8/8 solves; restart #0 was literally the plant. Every attack
   now salts its seed. If you add an attack, salt it.
