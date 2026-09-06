# 2208.01442 — planted MinRank, placed outside the paper's superdetermined band

Paper: **Magali Bardet, Manon Bertin, "Improvement of algebraic attacks for solving
superdetermined MinRank instances"**, [arXiv:2208.01442](https://arxiv.org/abs/2208.01442)
(cs.CR, cs.IT, cs.SC). The paper links the Kipnis–Shamir and Support-Minors modelings
of MinRank (Proposition 1), and shows in Section 4 that **superdetermined** instances
are *easy* ones for Support Minors — solvable by plain linearisation as soon as
`m(n−r) ≥ K(r+1)`.

This family ships instances that sit **strictly on the other side of that inequality**.

## Profile

| field | value |
|---|---|
| `TRACK` | **A** |
| native domain | algebra |
| object regime | finite_field |
| computational core | linear_algebra |
| certificate form | exact_symbolic (a coefficient vector in `F_251^40`) |
| intended intuition | **duality** — the low-rank condition only becomes linear through the right kernel |
| `domain_essentiality` | **native** (`reduction_kind = none`, `reduction = None`) |

The solver is handed the paper's own objects — matrices over `F_q` and the pencil
`M(x) = M_0 + Σ x_i M_i` — and `verify` runs exact Gaussian elimination over `F_q` on
that pencil. No graph, no CSP, no surrogate; nothing was compiled away.

## What the family is

Fix the prime field `F_q`. The solver is given `k+1` matrices
`M_0, M_1, …, M_k ∈ F_q^{m×n}` and a target rank `r`, and must produce

```
x = (x_1, …, x_k) ∈ F_q^k     with     rank_{F_q}( M_0 + x_1 M_1 + … + x_k M_k ) ≤ r
```

This is Problem 1 of the paper in its affine form: the homogeneous problem with
`K = k+1` matrices under the normalisation `x_0 = 1`, which is the form the NIST
MinRank signature submissions use. MinRank is NP-complete ([BFS99], cited in Section 1).

**The answer is `k` field elements** — 40 integers, **40 atoms and 183 characters** at
the shipping preset, and it stays 40 atoms all the way up the escalation ladder while
`q`, `m`, `n` and `r` grow.

**Checking is one rank computation.** Form `M(x)` (`k·m·n = 4000` modular multiply-adds)
and eliminate until a fifth pivot appears or the rows run out (at most
`(r+1)·m·n = 400` more). Integers mod a prime end to end; there is not a float anywhere
in the module.

**Generation plants the answer first, and never searches.** `make_instance` samples
`x ∈ F_q^k` uniformly, samples `M_1…M_k` uniformly, samples `R = A·B` uniformly over
the matrices of rank *exactly* `r`, and then *defines* `M_0 := R − Σ x_i M_i`. So
`M(x) = R` by construction. The only rejection loop is on `A` and `B` having full rank
`r`, which never looks at `x`.

**The planting leaks nothing, and that is provable.** With `M_1…M_k` i.i.d. uniform,
`x` uniform and `R` uniform over rank-`r` matrices,

```
P(instance, x = z)  =  q^{-k·mn-k} · [ rank(M_0 + Σ z_i M_i) = r ] / N_r
```

so the **posterior of `x` given the whole instance is exactly uniform over the solution
set**. No statistic of the published matrices can beat solving the instance. That is
why the outlier-style probe in G6 (`gram_normal_equations`) is not merely observed to
fail — it *cannot* work, and the README says which term kills it.

## Why it is hard — Track A

### The regime, and the theorem it is steering around

Section 4 gives the criterion for the paper's own best method: the (SM) system yields
to plain linearisation exactly when the equation count reaches the monomial count,

```
m · C(n, r+1)  >=  K · C(n, r)          equivalently      m(n−r) >= K(r+1)
```

At the shipping preset `q = 251, m = n = 10, r = 3, k = 40` (`K = 41`) this reads

```
m(n−r) = 70        vs        K(r+1) = 164          -- false by a factor 2.34
```

The Macaulay matrix of the Support-Minors system at bidegree `b = 1` is
**2100 × 4920**; linearisation needs rank **4919**, and 2100 rows cannot supply it.
The measured rank is exactly 2100 — a kernel of dimension **2820**. Pushing `b` up does
not rescue it until `b = 5`:

| bidegree `b` | independent equations | monomials | verdict |
|---|---|---|---|
| 1 | 2,100 | 4,920 | short by 2,819 |
| 2 | 72,240 | 103,320 | short by 31,079 |
| 3 | 1,286,040 | 1,480,920 | short by 194,879 |
| 4 | 15,791,040 | 16,290,120 | short by 499,079 |
| **5** | **150,381,330** | **146,611,080** | first bidegree that could solve |

Note also the paper's own definition: Section 4 calls an instance *superdetermined*
when `K < r·m`, following [VBCPS19]. At the shipping preset `K = 41` against
`r·m = 30`, so these instances are **not superdetermined in the paper's sense either** —
they are outside the class the paper's improvement is about, on both the definition and
the linearisation criterion.

The `b = 5` Macaulay matrix is `1.50e8 × 1.47e8`: **2.2e16 dense entries**, and about
`2^62.6` field operations with roughly 200 GB of state even by sparse Wiedemann. The
counts are the Bardet et al. (Asiacrypt 2020) formula whose `b = 1` and `b = 2` cases
are displayed in Section 4 of this paper; the module computes them in `sm_counts`.

### The other end: the solution is unique

The second thing the regime has to buy is uniqueness, and it is the reason `k` cannot
simply be raised. For any `z ≠ x` the matrix `M(z)` is exactly uniform on `F_q^{m×n}`,
so

```
E[#spurious solutions] = (q^k − 1) · #{rank ≤ r} / q^{mn}  ≈  q^{k − (m−r)(n−r)}
```

At the shipping preset `k = 40 < (m−r)(n−r) = 49`, giving **2^−71.7 expected spurious
solutions** — the planted `x` is the answer, with overwhelming probability the only one.
That inequality and the Section 4 inequality bracket the family from both sides:

```
m(n−r)/(r+1) = 17.5   <   k+1 = 41   <   (m−r)(n−r) = 49
```

Below the left bound the paper's linearisation solves it at `b = 1`; above the right
bound the instance is dense with solutions and the answer is not a witness of anything.
The shipped preset sits in the middle of that window.

### The easy regimes that had to be avoided

Only the build knows these, so they are written down here.

* **Inside the Section 4 band** (`m(n−r) ≥ K(r+1)`) the paper's own linearisation
  returns `x` from one echelon form. That is the whole subject of the paper, and it is
  where a careless generator lands: the natural instinct is to make the matrices big and
  the answer short, and *that is exactly the wrong direction* — raising `m` and `n` at
  fixed `k` walks straight into the easy band. `escalate` refuses moves that do it.
* **`k ≥ (m−r)(n−r)`** fills the instance with solutions; the "answer" then certifies
  nothing and `verify` accepts a large fraction of random vectors.
* **`r ≥ min(m,n) − 1` is trivial.** The rank condition collapses to the single equation
  `det M(x) = 0`, and finding a root of one polynomial in 40 variables over `F_q` takes
  one univariate root-find: fix 39 coordinates, solve a degree-`n` polynomial, succeed
  with probability ≈ 1 − 1/e. This corner is closed automatically rather than by hand:
  the uniqueness requirement `(m−r)(n−r) ≥ k + 5 = 45` forces `min(m,n) − r ≥ 7` at
  every rung of the ladder, shipping included (`m − r = n − r = 7`).
* **`r = 1`** makes the (r+1)-minors quadratic and the variety a Segre product; `demo`
  uses `r = 1` deliberately, no shipping preset does.

### Every published route, costed

| route | cost at the shipping preset |
|---|---|
| **Support Minors, `b = 5`** (best known) | **2^62.6 field ops**, 1.50e8 × 1.47e8 matrix |
| hybrid: guess 1 of the `x_i` (`q^1`), then SM at `b = 5` | 2^70.3 |
| hybrid: guess 1 kernel column (`q^r`), then SM at `b = 4` | 2^75.7 |
| Goubin–Courtois kernel attack, `a = 4` (`q^{ar}`) | **2^111.8 field ops** — `P = 1.6e−29` per trial, **6.25e28 expected trials**, each a 40×40 solve over `F_251` |
| exhaustive search over `F_q^k` | `251^40 = 2^318.9` candidates x 4,400 ops = **2^331 field ops**. Measured: 132,096 candidates in 165.3 s (1.25e−3 s each), so **1.0e93 s = 3.3e85 years** in this implementation |
| **checking a proposed answer** | **4,400 field operations**, 2^12.1 |

The margin the family lives on is therefore **2^62.6 against 2^12.1** — the cheapest
published way to *find* `x` versus the cost of *checking* it, a ratio of about 2^50.

## The attacks that were actually run, and the calibration

An attack that fails because it was never able to succeed proves nothing, so both
domain attacks are **calibrated**: the same code solves the lower rungs of this very
ladder.

| attack | demo | easy | shipping |
|---|---|---|---|
| Support-Minors linearisation, `b = 1` | **solves 6/6** | fails (120 eqs vs 135 monomials) | fails; **rank 2100, 2100, 2100** on the three seeds eliminated in full (2.85e10 field ops, 380 s), against 4,919 needed |
| Support-Minors linearisation, `b = 2` | — | **solves 4/4** (1080 × 675, rank 674) | 72,240 eqs vs 103,320 monomials |
| Goubin–Courtois kernel attack | **solves** | **solves 3/3** (2.9e4 expected trials) | `P = 1.6e−29`, **6.25e28 expected trials**; measured 18.7 ms per trial, so 1.17e27 s = **3.7e19 years** |

So the failure at the shipping preset is a measurement of the parameter regime, not an
untested claim about an unimplemented algorithm.

## Worked example (`demo`: q = 5, m = n = 3, r = 1, k = 2)

`render` prints the field, three 3×3 matrices and the output contract — 1.3 KB. Seed 3:

```
M_0 = [[4,4,1],[2,2,1],[1,0,2]]   M_1 = [[3,2,1],[2,1,1],[1,0,0]]   M_2 = [[4,0,1],[2,2,0],[4,4,4]]
```

* `verify(inst, [3, 0])` → `(True, 'ok')` — `M_0 + 3·M_1` has rank 1 over `F_5`.
* `verify(inst, [3, 1])` → `(False, 'rank(M(x)) = 3, which exceeds the target 1')`.
* `verify(inst, [3])` → `(False, 'answer has 1 entries, expected 2')`.
* `enumerate_all(inst)` → `1`: exactly one of the 25 candidates works.

**Can a person do it by hand?** Yes — 25 candidates, each a 3×3 rank test mod 5, and
the 2×2 minors give a two-variable quadratic system that is quicker still. That is what
`demo` is for; `harden.py` skips it and it never ships.

## Presets

| preset | q | m | n | r | k | search space | `m(n−r)` vs `K(r+1)` | `k` vs `(m−r)(n−r)` | best known attack |
|---|---|---|---|---|---|---|---|---|---|
| demo | 5 | 3 | 3 | 1 | 2 | 25 | 6 ≥ 6 (**easy side**) | 2 < 4 | 2^7.1 |
| easy | 13 | 6 | 6 | 2 | 8 | 8.2e8 | 24 < 27 | 8 < 16 | 2^22.4 |
| medium | 61 | 8 | 8 | 3 | 20 | 2^118.6 | 40 < 84 | 20 < 25 | 2^50.5 |
| **hard (ships)** | **251** | **10** | **10** | **3** | **40** | **2^318.9** | **70 < 164** | **40 < 49** | **2^62.6** |

`demo` is deliberately on the easy side of the Section 4 criterion — that is what makes
it the calibration point for the domain attack. `easy` falls to the kernel attack in
~2.9e4 trials and to Support Minors at `b = 2` in under two seconds; it is a rung, never
a shipping candidate.

`escalate` moves **q, m, n and r together** and holds `k` — so the answer stays 40
atoms while the haystack grows:

| step | q | m | n | r | best known attack | answer atoms / chars | moved |
|---|---|---|---|---|---|---|---|
| ships | 251 | 10 | 10 | 3 | 2^62.6 | 40 / 183 | — |
| 1 | 1,021 | 10 | 14 | 5 | 2^87.9 | 40 / 193 | q, n, r |
| 2 | 4,093 | 13 | 17 | 8 | 2^117.9 | 40 / 231 | q, m, n, r |
| 3 | 16,381 | 16 | 20 | 11 | 2^142.0 | 40 / 245 | q, m, n, r |
| 4 | 65,521 | 19 | 23 | 14 | 2^162.3 | 40 / 272 | q, m, n, r |
| 5 | 262,139 | 21 | 25 | 16 | 2^217.7 | 40 / 305 | q, m, n, r |
| 6 | 1,048,573 | 22 | 26 | 17 | 2^262.0 | 40 / 317 | q, m, n, r |

Every level was built and its planted answer verified. The ladder runs **10 rungs**
before `escalate` returns `cap_bound` — the last is `q = 1,048,573, m = 29, n = 33,
r = 24`, still 40 atoms and 310 characters. What stops it is the *render* budget
(40,000 matrix entries), never the answer cap: 40 atoms against 256, 310 characters
against 2,000.

**Raising `m` and `n` alone would be a bug**, and `escalate` refuses it: more rows push
`m(n−r)` up against `K(r+1)` and walk the instance back into the easy band of Section 4.
`r` has to rise with the dimensions, and `(m−r)(n−r) − k ≥ 5` is enforced at every rung
so the answer stays unique.

## Gate results

| gate | measured | pass |
|---|---|---|
| **G1** planted verifies | **80/80** (4 presets x 20 seeds); instances deterministic given (seed, params) | True |
| **G2** rejects corruption | 0 corruptions accepted, **16 distinct reasons** across 10 corruption types x 8 instances | True |
| **G3** round trip | prose / JSON / whitespace forms all recover the answer, `None` on garbage, no answer leak in any of the three hint modes | True |
| **G4** guess resistance | **0 hits / 200,000 structure-aware samples**; exact P(guess) = ~1.031e-96 (2^-318.86) | True |
| **G5** density + baseline | **exactly one expected valid answer** at shipping (`1 + 2.54e-22`, spurious 2^-71.74); sampled 0/200,000 valid; strongest executed attack **131.43 s / 9,492,780,334 field ops**; best known route **2^62.65** | True |
| **G6** adversary panel | **7 attacks, 0 successes** out of 8 attempts each; both domain attacks calibrated on the lower rungs | True |
| **G7** scales | ladder best-attack log2 7.12 -> 22.38 -> 50.46 -> 62.65, strictly increasing; escalated level builds, verifies, and stays **40 atoms** | True |
| **G8** canonical_key | invariance **80/80**, transformation-is-real **80/80**, distinctness **20/20** | True |
| **G9(c)** size caps | **40 atoms, 183 chars, ~79 tokens** against caps of 256 and 2000; render 18,944 chars | True |
| **G9(c)** route cap | `intended_route_operations = null` (Track A: no compact solving route). Checking an answer costs **4400 field ops** - see caveats. | n/a |

The G6 panel, all eight seeds at the shipping preset:

| attack | successes | wall clock |
|---|---|---|
| exhaustive search, 20,000-candidate budget | **0/8** | 165.3 s |
| Gram / normal-equations outlier probe (the least-squares recovery that works over R) | **0/8** | 0.4 s |
| greedy coordinate descent on rank(M(x)) | **0/8** | 290.6 s |
| Goubin-Courtois kernel guessing (**the Sec. 4 hybrid**, q^{ar}) | **0/8** | 25.7 s |
| random restart, 20,000 samples | **0/8** | 159.9 s |
| sparse-support probe (every 1-sparse x, then 2,000 random 2-sparse) | **0/8** | 35.3 s |
| Support-Minors linearisation at b=1 (**the domain-standard attack**, Sec. 4) | **0/8** | 380.4 s |

Calibration - the same code on the lower rungs, which is what makes the zeros above evidence:

| calibration run | result |
|---|---|
| Support-Minors b=1 on `demo` | **6/6 solved** |
| Support-Minors b=2 on `easy` | **4/4 solved** |
| kernel attack on `easy` | **3/3 solved** |

And the solution-count estimator, checked against exact enumeration:

| preset | q, m, n, r, k | predicted valid answers | exact, mean over 20 seeds | range |
|---|---|---|---|---|
| `cal_many` | 5, 4, 4, 2, 6 | 32.94 | **32.55** | 21-40 |
| `cal_unique` | 5, 5, 5, 2, 6 | 1.01 | **1.00** | 1-1 |
| `demo` | 5, 3, 3, 1, 2 | 1.047 | **1.05** | - |
| **`hard` (ships)** | 251, 10, 10, 3, 40 | **1 + 2.54e-22** | q^k = 2^318.9, not enumerable | - |

The estimator is exact in expectation (`E[#solutions] = 1 + (q^k-1)*#{rank<=r}/q^{mn}`, because `M(z)` is uniform for every `z != x`), and the two calibration presets confirm it where the count can be done by brute force - one deliberately crowded, one unique.

## The oracle loop and the G9 arms

Not run here: this environment has no `OPENROUTER_API_KEY`. STEP 4 (`scripts/harden.py`)
and the three G9 arms are the caller's to run; `selftest_report.json` records
`arms: {bare: null, hinted: null, placebo: null}` rather than inventing numbers.

`STRUCTURAL_HINT` names one invariant and stops:

> "A matrix has rank at most r exactly when its right kernel has dimension at least
> n−r, and every single kernel vector is an equation that is linear in the unknowns."

It says *what to look at* — the kernel is the object that linearises the problem — and
nothing about what to do next: no modeling, no Macaulay matrix, no bidegree, no count.
`PLACEBO_HINT` is one sentence of the same length and register about index conventions.

## How to use it

```python
import gen_2208_01442 as g
inst = g.make_instance(seed=0, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))                       # the whole problem statement, ~19 KB
g.verify(inst, g.parse_answer(model_reply)) # (True, 'ok') or (False, reason)
```

```bash
bash scripts/emit.sh 2208.01442
python3 gen_2208_01442.py            # re-runs every gate, rewrites selftest_report.json
python3 gen_2208_01442.py --fast     # 3 seeds per attack instead of 8
```

Standard library only. `gvlib` is imported defensively at the top and is not used: the
whole family is exact arithmetic modulo a prime, and `gvlib`'s rational matrices are the
wrong ring for it.

## Caveats — read these

* **`canonical_key` is not a complete invariant, and cannot cheaply be.** It is complete
  for the group that actually relabels an instance's *coordinates* — change of
  generators `S ∈ GL_k` and translation of the origin `M_0 → M_0 + Σ t_i M_i` — via the
  RREF of the linear part plus the reduced coset representative of `M_0`. It is **not**
  invariant under `M_i → A M_i B` for `A ∈ GL_m, B ∈ GL_n`, which also preserves every
  rank and hence the problem. Deciding that equivalence is the **Matrix Code Equivalence**
  problem, which is believed hard — it is the security assumption of the NIST candidate
  MEDS. Two instances related by such a pair would receive different keys, so the
  duplicate check in `emit.sh` can *under*-count collisions. Given that instances are
  drawn from a `q^{(k+1)mn}`-sized space, an accidental `A·B`-equivalent pair is not a
  practical concern; a deliberate one is not something this key can see.
* **What `P(guess)` means.** `random_candidate` samples uniformly from `F_q^k`, which is
  the whole structure-aware space here: the statement gives a solver no deducible
  constraint on `x` beyond "40 entries, each in 0…250". There is no partition shape, no
  sum rule, no arity to exploit, so the naive and structure-aware numbers coincide. That
  is unusual for this corpus and it is why the number is believable rather than the
  eighty-orders-of-magnitude self-deception G4 warns about.
* **The `b ≥ 2` Support-Minors costs are counted, not executed.** `b = 1` was built and
  eliminated at the shipping preset on real instances (that is the measured rank 2100).
  The `b = 2 … 5` rows of the table above come from the counting formula, because the
  `b = 2` matrix alone is 72,240 × 103,320 and the `b = 5` matrix has 2.2e16 entries.
  The formula is the paper's own (Section 4 displays `b = 1, 2`); it is validated by the
  fact that its prediction of *where linearisation starts working* is exactly right at
  the two presets where it can be checked — `b = 1` for demo, `b = 2` for easy, both
  landing at rank `n_mon − 1` to the unit.
* **The best-known-attack figure `2^62.6` assumes sparse linear algebra.** Dense
  Gaussian elimination on the `b = 5` matrix is `2^76.3` and needs 2.2e16 entries of
  memory, so it is not the relevant number; sparse Wiedemann on `2.5e10` nonzeros is,
  and it still needs ~200 GB. This is roughly 63-bit security, not 128-bit: the family
  is far past anything an evaluated model or this harness can do, but it is **not** a
  cryptographic parameter set and the README does not claim to be one. Raising it
  further costs render size, which is why `escalate` exists.
* **What I did not try.** No Gröbner engine was run (no `sympy`, no Magma, no F4/F5): the
  minors modeling and the `b ≥ 2` Support-Minors systems were costed, not solved. The
  claim that the minors modeling is worse here is the paper's own — Section 1 names
  Support Minors the most efficient modeling known at the time of writing, and Table 1
  puts the SM matrices 3× to 160× smaller than the KS-based route of [VBCPS19] at every
  entry — plus the naive count: `C(10,4)² = 44,100` quartics in 40
  unknowns against `C(44,4) = 135,751` degree-≤4 monomials, i.e. underdetermined at its
  own degree, and its syzygies are what push the Gröbner degree of regularity up. I did
  not measure it. I also did not implement the `n`-puncturing variant of Section 4;
  puncturing removes columns, which *reduces* the equation count and therefore only
  helps in the overdetermined regime this family avoids.
* **The G9(c) route cap has no Track A referent.** `intended_route_operations` is
  recorded as `null`, as on 1812.05008, because there is no compact solving route to
  count — that is the Track A claim. The number that *is* recorded is the cost of
  checking an answer, **4,400 field operations** (4,000 to form `M(x)`, 400 for the
  elimination). If the caller wants the checking cost under 1,000 instead, that forces
  `k·m·n ≤ 1000`, which cannot be reconciled with `k < (m−r)(n−r)` at any usable size —
  it is a genuine tension between the answer cap and the uniqueness bound, and I chose
  uniqueness.
* **If you want to make this family easy**, do any one of: raise `m` or `n` without
  raising `r` (drives it into the Section 4 band); lower `k` below `m(n−r)/(r+1) − 1`
  (same); raise `k` past `(m−r)(n−r)` (the instance fills with solutions and `verify`
  starts accepting almost anything); or use a target rank `r ≥ min(m,n) − 1` (the rank
  condition becomes a single determinant).
