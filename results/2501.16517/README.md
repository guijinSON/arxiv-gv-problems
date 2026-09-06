# 2501.16517 — planted balanced number partitioning

Neekon Vafa and Vinod Vaikuntanathan, *Symmetric Perceptrons, Number Partitioning and
Lattices*, [arXiv:2501.16517](https://arxiv.org/abs/2501.16517) (math.ST, cs.CC, math-ph).

| field | value |
|---|---|
| `TRACK` | **A** — structural hardness |
| native domain | combinatorics |
| object regime | integer_lattice |
| computational core | subset_sum |
| certificate form | integer_tuple |
| intended intuition | search pruning |
| `domain_essentiality` | **native** (`reduction_kind: none`) |
| shipping preset | `hard` — `m = 144`, `b = 156` |

---

## What the family is

The solver is handed **144 positive integers** `a[0] … a[143]`, each about 156 bits
(≈ 47 decimal digits), printed in nondecreasing order, and asked for a set `S` of
**exactly 72 indices** such that

```
    sum of a[i] over i in S   =   sum of a[i] over i not in S      (exact integer equality)
```

This is Definition 2.19 of the paper — *find `x ∈ {−1,1}^m` with `|a^T x| ≤ κ(m)·√m`* — at
`κ = 0`, in the integer form the classical literature (Karmarkar–Karp, Garey–Johnson,
both cited by the paper) uses. Checking an answer is one pass of big-integer addition:
72 additions, one comparison. The answer is 72 numbers, 305 characters.

**Why the generator never searches.** The partition is sampled *first*: a uniformly
random balanced half `S` of the index set. Then 143 of the weights are drawn i.i.d.
uniform from `{1 … 2^156}` and the single remaining one — at a uniformly random position
— is *solved for* so that the two blocks balance exactly. If that weight lands outside
the range the whole draw is discarded and retried (≈ 9 retries at `m = 144`), so the
accepted law is exactly "i.i.d. uniform weights conditioned on `S` being a perfect
balanced partition". Inverse generation, no search, unlimited supply.

---

## Why it is hard (Track A)

### The regime, from the paper's own criterion

Section 1, paragraph *"Number Partitioning (or Number Balancing)"*, states the
statistical threshold:

> solutions exist … for `κ_stat(m) = 2^−m`

Rescaling the paper's `a_i ~ N(0,1)` to `b`-bit integers `a_i ~ U{1 … 2^b}`, the smallest
achievable `|a^T x|` over all `2^m` sign vectors is about `2^b · κ_stat(m) · √m =
2^{b−m}·√m`. That number is an integer, so **`b ≈ m` is the phase transition**, and it
cuts both ways:

| regime | what happens | consequence for the family |
|---|---|---|
| `b < m` | ≈ `2^{m−b}` perfect partitions exist by accident | **broken** — `verify` accepts anything |
| `b ≳ m` | whp none exist at random, so the planted one is essentially unique | the window |
| `b ≫ m` | density `m/b` drops under the Coster–Joux–LaMacchia–Odlyzko–Schnorr bound 0.9408 and lattice reduction wins | **broken** — LLL solves it |

We ship at `b = m + max(6, ⌈m/12⌉)`, i.e. `b/m = 1.083` at `m = 144`. Both edges are
*measured*, not assumed.

### Edge 1 — uniqueness. Measured, exactly

`enumerate_all` is a complete Horowitz–Sahni meet-in-the-middle count of *all* balanced
solutions. Below, three seeds per row; the count includes the planted `S` **and** its
complement, so `2` means "the plant and nothing else". The estimate is
`2 + 2^{m−b}·2.205/m`, derived in `expected_valid_count`.

| m | b | b/m | exact counts | estimate |
|---|---|---|---|---|
| 24 | 20 | 0.833 | 4, 2, 2 | 3.47 |
| 24 | 24 | 1.000 | 2, 2, 2 | 2.09 |
| 24 | 30 | 1.250 | 2, 2, 2 | 2.0014 |
| 32 | 28 | 0.875 | 4, 2, 2 | 3.10 |
| 32 | 32 | 1.000 | 2, 2, 2 | 2.07 |
| 32 | 38 | 1.188 | 2, 2, 2 | 2.0011 |
| 40 | 36 | 0.900 | 4, 2, 2 | 2.88 |
| 40 | 46 | 1.150 | 2, 2, 2 | 2.0009 |

Every instance at `b ≥ m` counted exactly **2**. At the shipping preset the calibrated
estimate is **2.0000037** valid answers out of `C(144,72) = 1.48·10^42`, a density of
**1.35·10^−42**.

### Edge 2 — the lattice. Measured, and the margin covers more than LLL

The domain-standard attack is implemented in the module (`attack_lattice_lll`): exact
all-integer LLL (de Weger / Cohen Alg. 2.6.7 — no floats, no `Fraction`s) on the
rank-`m` CJLOSS partition lattice, `δ = 0.99`. The planted `±1` vector sits in it with
norm `√m`. **The attack is real: it solves the same family at small `m`** —

| m | b | b/m | LLL recovers the plant | uSVP gap | sec |
|---|---|---|---|---|---|
| 16 | 22 | 1.375 | **8/8** | 2.035 | 0.00 |
| 24 | 30 | 1.250 | **8/8** | 1.671 | 0.04 |
| 32 | 38 | 1.188 | **8/8** | 1.497 | 0.12 |
| 36 | 42 | 1.167 | 6/8 | 1.442 | 0.18 |
| 40 | 46 | 1.150 | 3/8 | 1.395 | 0.22 |
| 44 | 50 | 1.136 | 2/8 | 1.360 | 0.30 |
| 48 | 54 | 1.125 | **0/8** | 1.329 | 0.35 |
| 64 | 70 | 1.094 | **0/8** | 1.244 | 0.86 |
| 96 | 104 | 1.083 | **0/8** | 1.176 | 3.12 |
| **144** | **156** | **1.083** | **0/8** | **1.133** | **11.0** |

and in the other direction, holding `m = 64` and paying more bits:

| b at m = 64 | 70 | 80 | 96 | 112 | 128 | 160 |
|---|---|---|---|---|---|---|
| LLL solves | 0/6 | 0/6 | 0/6 | 5/6 | 4/6 | 6/6 |

So at this bit-ratio LLL dies between `m = 44` and `m = 48`; shipping at `m = 144` is
**3.3× past the boundary**, and at `m = 64` LLL needs `b ≥ 112` against the `70` we
would ship — a **1.6× bit-length margin** that grows with `m` (extrapolating the
measured `δ₀`, at `m = 144` LLL would need `b ≈ 330` against `156`: **2.1×**).

**The margin is not specific to LLL.** The reason is one number. In the shipping
lattice (rank 144, `log₂ det = 320.8`), the Gaussian heuristic puts `λ₁` at `1.133 ×`
the planted vector's norm. Recovering a unique shortest vector with a gap that small
needs a root-Hermite factor

```
    δ₀  ≤  1.133^(1/144)  =  1.00086
```

LLL measured on these instances achieves `δ₀ = 1.0126–1.0137` (already BKZ-20 quality,
because the basis is structured). BKZ-100 achieves ≈ 1.0093; `δ₀ = 1.00086` corresponds
to a block size in the *thousands*, far past the rank of the lattice itself. So the only
lattice algorithm that recovers this plant is **exact SVP in dimension 144**, whose best
known cost is `2^{0.292·144} = 2^42` with a sieve — which is precisely the assumption
Corollary 5.4 (`sivp-to-npp`, informal Theorem 1.3) rests on: `NPP_κ` is hard at
`κ(m) = 2^{−log^{3+ε} m}` given subexponential hardness of approximating SIVP/GapCRP/GDD
(Assumption 2.14). We sit at `κ = 0`, far inside that range.

### Costs at the shipping preset

| route | cost |
|---|---|
| brute force `C(144,72)` | `2^140.1` |
| meet-in-the-middle (Horowitz–Sahni) | `2^78.2` ops — measured throughput 2.3·10⁶ ops/s ⇒ **4.7·10⁹ CPU-years** |
| Schroeppel–Shamir | `2^72` time, `2^36` space |
| Becker–Coron–Joux (best known for random subset sum) | `2^41.9` |
| sieve SVP in dim 144 (the only lattice route) | `2^42.0` |
| LLL on the CJLOSS lattice | 3.3·10⁷ exact integer ops, 11 s — **fails** |
| **verify an answer** | **215 big-integer operations** |

### The easy regimes we had to avoid

* `b < m` — abundance (measured above). This is the single failure mode that would make
  the family worthless, and it is the one the paper's `κ_stat = 2^{−m}` line pins down.
* `m` small — LLL solves it outright, 8/8 at `m ≤ 32` (measured above). Any preset below
  `m ≈ 48` is broken by the lattice attack, so `demo` (m = 8) is *deliberately* easy and
  `easy` starts at `m = 80`.
* `b ≫ m` — the CJLOSS low-density attack. Measured at `m = 64`: `b ≥ 112` breaks it.
* `b ≈ log²m` — Karmarkar–Karp's regime. KK reaches discrepancy `2^{−O(log²m)}` relative
  to the largest weight (`κ_comp`, Section 1); at `m = 144, b = 156` it lands on a
  **128–133-bit residue**, i.e. `κ ≈ 2^−23` where we require `2^−156`. That gap *is* the
  paper's statistical–computational gap.
* Unbalanced planting — if `|S| ≠ m/2` the two blocks have different mean weights and the
  plant is readable off a per-element statistic. `|S| = m/2` is required by the statement
  and by the construction.

---

## Worked example (`demo`, m = 8, b = 14)

`make_instance(seed=3, m=8, b=14)` renders (abridged — the real statement also defines
every term and the output format):

```
a[0] = 630     a[1] = 1174    a[2] = 1288    a[3] = 4608
a[4] = 7765    a[5] = 8319    a[6] = 10968   a[7] = 14298

TASK. Find a set S of 4 distinct indices in 0..7 with
      sum of a[i] over i in S = sum of a[i] over i not in S.
```

Total `= 49050`, so each block must total `24525`.
Answer `[0, 3, 5, 6]`: `630 + 4608 + 8319 + 10968 = 24525`. ✓

```python
verify(inst, [0, 3, 5, 6])   -> (True,  'ok')
verify(inst, [0, 3, 5, 7])   -> (False, 'sums_differ (difference 6660)')
verify(inst, [0, 3, 5])      -> (False, 'too_few_indices (3 < 4)')
enumerate_all(inst)          -> 2          # the plant and its complement, nothing else
```

**A person can solve `demo` on paper** — 70 candidate subsets, one target sum. That is
the whole point of `demo`; it is an illustration, not a difficulty level, and LLL and
Karmarkar–Karp both crack it (KK 4/8). The smallest setting that is *not* hand-scale is
`easy`: 80 numbers of 87 bits and `C(80,40) = 10^23` candidates.

---

## Difficulty presets

| preset | m | b | b/m | answer atoms | answer chars | LLL | KK | ships |
|---|---|---|---|---|---|---|---|---|
| demo | 8 | 14 | 1.75 | 4 | 10 | solves | 4/8 | no — hand-scale by design |
| easy | 80 | 87 | 1.088 | 40 | 152 | 0/8 | 0/8 | |
| medium | 112 | 122 | 1.089 | 56 | 223 | 0/8 | 0/8 | |
| **hard** | **144** | **156** | **1.083** | **72** | **305** | **0/8** | **0/8** | **yes** |

(answer chars are the mean over 8 seeds; the G9 figure below, 305, is the measured
value at the seed the gate uses, and the max seen over 8 seeds is 308.)

`escalate()` moves **two** parameters together — `m` (the ground set, hence the haystack
`C(m,m/2)` *and* the rank of the lattice the domain attack must reduce) and `b` (the
weight bit-length, which must track `m` to keep the plant unique). The answer stays one
bit per item:

| rung | m | b | answer atoms | answer chars | builds + verifies |
|---|---|---|---|---|---|
| ship | 144 | 156 | 72 | 305 | ✓ |
| +1 | 176 | 191 | 88 | 379 | ✓ |
| +2 | 208 | 226 | 104 | 455 | ✓ |
| +3 | 240 | 260 | 120 | 545 | ✓ |
| +4 | 256 | 278 | 128 | 579 | ✓ |
| +5 | — | — | — | — | `"cap_bound"` |

At `m = 256` the certificate is 128 atoms and 579 characters — the answer *is* 256 bits,
which is the atom cap read as one bit per item, so `escalate` stops there and says
`cap_bound` rather than `None`. Every rung stays under the 1000-operation route cap
(`m − 1 + m/2 = 383` at `m = 256`).

---

## Gate results (`selftest_report.json`)

| gate | measured | pass |
|---|---|---|
| G1 planted verifies | 32/32 (4 presets × 8 seeds) | ✓ |
| G2 rejects corruption | 60/60 corruptions rejected, **10 distinct reasons** | ✓ |
| G3 round-trip | prose + fence + bracket forms all recovered; garbage → `None` | ✓ |
| G4 guess resistance | **0 hits / 200 000**; analytic `P = 1.35·10^−42`; space `C(144,72) = 1.48·10^42` | ✓ |
| G5 density + cost | valid answers at shipping **2.0000037** (exact 2 wherever countable); density `1.35·10^−42`; strongest attack (LLL) **11.0 s / 3.3·10^7 ops, fails** | ✓ |
| G6 adversary panel | 5 attacks, **0/8 each** | ✓ |
| G7 scales | `m 144→176`, `b 156→191`, builds and verifies; 5-rung ladder to `cap_bound` | ✓ |
| G8 canonical_key | invariance **96/96**, answer carried through the transform **48/48**, distinct keys **24/24** | ✓ |
| G9 caps | 305 chars ≤ 2000, 72 atoms ≤ 256, 144 tokens, **215 route ops ≤ 1000** | ✓ |

### The adversary panel

| attack | successes | what it measured at m = 144 |
|---|---|---|
| `lattice_lll_cjloss` — **the domain-standard attack** | **0/8** | exact integer LLL, rank-144 CJLOSS lattice, 3.3·10⁷ ops, 11 s; shortest vector found is **2.4–2.7× longer** than the plant |
| `meet_in_the_middle_horowitz_sahni` | **0/8** | budgeted to 2·2^15 masks per side; coverage `4.8·10^−35` of the `2^72 × 2^72` product |
| `karmarkar_karp_differencing` — the paper's own algorithm | **0/8** | residue 128–133 bits (needs 0); blocks of size 71–74 |
| `random_restart_local_search` | **0/8** | 32 restarts × best-improvement 1-swaps, 1.6·10⁵ steps; best abs discrepancy ≈ `2.9·10^42` |
| `outlier_statistics` | **0/8** | 8 per-element rules (largest/smallest half, rank parity, value parity, mod 3, top bit, prefix) |

`attack_sanity_on_small_instances` records that LLL **and** meet-in-the-middle both solve
`m = 16` instances of the same family — the panel fails at `m = 144` because the family is
hard there, not because the attacks are no-ops.

**Outlier diagnostics** (24 instances, 72 planted indices each, chance baseline 36):
planted indices in the top half by value **35.7**, in the bottom half **36.3**,
odd-valued **37.0**. The planted block is statistically invisible, as it must be — both
blocks are drawn from the same uniform law and the partition is balanced.

### `canonical_key`

Keyed on the multiset of weights after the normalisation `a ↦ (sorted(a) − min) / gcd`.
That is invariant under the family's real symmetry group: permutation of the published
order, and the affine maps `a ↦ λa + c` (`λ > 0`), which preserve the valid-answer set
*exactly* because every answer is balanced — `Σ(λa_i + c)x_i = λ Σ a_i x_i` when
`Σ x_i = 0`. The selftest applies all four transformations (and their composition) over
24 seeds, checks the key is unchanged 96/96, and checks the *transformed instance still
verifies against the carried answer* 48/48, so the key is not collapsing genuinely
different problems.

---

## The oracle loop and the G9 arms

`llm_loop_transcript.jsonl` and `.meta.json` are produced by `scripts/harden.py`
(STEP 4), which needs `OPENROUTER_API_KEY`; that run was **not** performed in this build
and the transcripts are therefore absent from this directory. The three-arm G9
diagnostic (bare / hinted / placebo) is likewise unrun; `selftest_report.json` records
`0/0` attempts for each arm and `hinted_minus_placebo: null` rather than a fabricated
number. Nothing in the ship decision turns on those numbers — G9's only gated part is
(c), the size and effort caps, all three of which are measured above.

What the hint *would* test, if it is run: `STRUCTURAL_HINT` names one invariant and stops —

> "Both blocks must sum to the same value, so every valid answer hits one target that is
> fixed before any search: half of the total."

It names the fixed target and says nothing about what to do with it. My expectation is
that it buys the oracle nothing at `m = 144`, because the target is not the obstacle: a
solver who knows `T` still has to find 72 of 144 numbers that sum to a specific 157-bit
value, and the fastest known way to do that is `2^42` operations. If the hinted arm does
move, that is evidence against `intuition_type: "search pruning"` and should be recorded.

---

## How to use it

```python
import gen_2501_16517 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))                      # the statement; no answer anywhere in it
ans = g.parse_answer(model_reply)          # tolerates prose, fences, brackets
ok, why = g.verify(inst, ans)              # exact; never reads inst["answer"]
```

```bash
python3 gen_2501_16517.py --demo           # a hand-scale instance, rendered
python3 gen_2501_16517.py                  # full selftest (~4 min; LLL at m=144 is 11 s × 8)
scripts/emit.sh 2501.16517
```

Standard library only. `gvlib` is not imported: every object here is an integer and
every operation in `verify` is exact integer arithmetic, so there is nothing for the
rational/matrix helpers to do.

---

## What is in this directory

| file | what it is |
|---|---|
| `gen_2501_16517.py` | the module (generator, output contract, five attacks, `selftest`) |
| `selftest_report.json` | the dict `selftest()` returns — every gate with its measured number |
| `README.md` | this file |
| `boundary.log` | the LLL-vs-`m` and LLL-vs-`b` sweeps behind the two tables above (`boundary.py`) |
| `evidence.log` | exact solution counts, Karmarkar-Karp residues, MITM timing, the lattice table (`evidence.py`) |
| `count.log`, `sweep1.log`, `sweep2.log` | the earlier regime-finding runs that located the window |
| `selftest_final.log` | the console trace of the run that produced `selftest_report.json` |
| *missing* | `llm_loop_transcript.jsonl`, `.meta.json`, `g9_*_transcript.jsonl` — STEP 4 was not run here |

`boundary.py`, `evidence.py`, `count.py`, `sweep1.py`, `sweep2.py`, `exp.py` and
`lll.py` are the scratch scripts that produced those logs; they are not part of the
module and nothing imports them.

---

## Caveats — read these

1. **The hardness claim is an SVP claim, and that is deliberate.** The uSVP gap in the
   shipping lattice is `1.133`, so the planted vector *is* the unique shortest vector:
   an exact-SVP oracle in dimension 144 would recover it. That is not a hidden weakness,
   it is the paper's own hypothesis (Assumption 2.14 / Corollary 5.4) restated as a
   measured number, and `2^42` is the best known cost for it. What is *runnable* —
   LLL, and by the `δ₀` argument any BKZ block size that fits in the rank — is measured
   to fail with a factor-6 margin in the Hermite factor.
2. **I could not run BKZ.** No lattice library is available and implementing a sieve or a
   pruned-enumeration BKZ in pure Python was out of scope. The BKZ claim in this README is
   the standard `δ₀(β)` estimate applied to a *measured* gap and a *measured* LLL `δ₀`,
   not a run. If someone has fplll, BKZ-40 at `m = 144, b = 156` is the single
   experiment most worth doing; the prediction is that it fails.
3. **I could not run Becker–Coron–Joux.** `2^41.9` at the shipping preset is its published
   asymptotic complexity, not a measurement. It is the reason `m` is 144 and not 96 —
   at `m = 96` the same bound is `2^27.9`, which a determined attacker with a real
   implementation could actually pay.
4. **`P(guess) = 1.35·10^−42` is a uniform-over-balanced-subsets number.** It is the
   right prior — the statement gives away the cardinality and nothing else, and the
   outlier panel confirms no per-element statistic narrows it — but it is *not* a
   statement that no clever heuristic exists. G6 is the evidence for that, and G6 is five
   attacks, not a proof.
5. **The valid-answer count at the shipping preset is an estimate, not an exhaustive
   count.** Exhaustive counting stops at `m ≈ 40` (`2^20` per side). The estimate is the
   closed form `2 + 2^{m−b}·2.205/m`, calibrated against exact counts at `m = 16…40` on
   both sides of the transition (table above), where it tracks the observed counts. At
   `b − m = 12` it predicts `3.7·10^−6` extra solutions; a rare instance with a second
   partition would be *accepted* by `verify`, which is correct behaviour, not a bug.
6. **One weight per instance is solved for, not sampled.** Its conditional density over
   `{1 … 2^b}` is flat only to within `exp(−6/m)` — about 4% at `m = 144` — and its index
   is uniform over all `m` positions, so per-element it is a 0.03% perturbation. I checked
   this cannot be read off (`outlier_statistics`, 0/8; outlier diagnostics at chance), but
   it is the one place where the shipped law differs from the exact planted conditional.
7. **`demo` is broken on purpose.** LLL solves it, Karmarkar–Karp solves it half the time,
   and a person can solve it on paper. `SHIPPING_DIFFICULTY` is `hard`; do not ship `demo`
   or anything below `m ≈ 48`.
8. **`certificate_form` is `integer_tuple`,** which the corpus already has too much of.
   It is the honest form here: the paper's certificate is a sign vector, and a sign
   vector is a subset. I did not dress it up as something richer.
