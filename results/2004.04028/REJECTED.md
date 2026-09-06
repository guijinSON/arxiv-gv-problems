# REJECTED — arXiv:2004.04028, "Set-theoretic solutions of the Pentagon Equation"

**Verdict: REJECT. The family fails H, on BOTH tracks.** G and V both hold; the
generator and the checker are correct and are retained as
`rejected_gen_2004_04028.py` with `selftest_report.json`.

Family built: plant a genuine set-theoretic solution `s(x,y) = (x·y, θ_x(y))` of the
Pentagon Equation on a finite set `S`, display the multiplication table `M` and the
theta table `T` with `holes` cells erased, and ask the solver to restore them.
`verify` rebuilds `s` and checks `s_23 s_13 s_12 = s_12 s_23` on all `|S|^3` triples.

---

## Which gate fails, and on which track

| gate | status |
|---|---|
| **G — generatable** | **PASSES.** Theorem-backed: the plant is the product `(E,s_E) × (G,s_G)` of a solution on a left zero semigroup with the unique bijective solution on a group (Proposition 3.1, Kashaev–Sergeev); products of solutions are solutions (Section 1, after Definition 1.4). Nothing is searched. `verify(inst, inst["answer"])` is **True 24/24** over 4 presets × 6 seeds. |
| **V — verifiable** | **PASSES.** Exact, purely combinatorial: `|S|^3` tuple comparisons; at the shipping preset `40^3 = 64,000` triples, < 0.2 s, no arithmetic beyond table lookup. Corrupted answers rejected 6/6 with 6 distinct reasons. |
| **H — hard** | **FAILS. Track A fails** because the domain-standard algorithm succeeds on 8/8 instances at every preset. **Track B fails** because the mechanical route and the compact route are the same order: 8,000 vs 303 exact operations, a ratio of **26**. |

---

## The two numbers the contract asks for

Shipping preset `hard`: `|S| = 40`, `holes = 100` (100 atoms, 369 chars — inside the cap).

| route | cost |
|---|---|
| **mechanical** — scan the `\|S\|` candidate values per hole and test one instance of (P3)/(P1) for each | **8,000 exact operations** (2·40·100) |
| **compact** — notice every θ-row is a group-torsor row `y ↦ y·x⁻¹`, read the group off three known cells, then one lookup per hole | **303 exact operations** (3 + 3·100) |
| ratio | **26.4** |

A factor of 26 is not a generator–verifier gap. The contract's own Track B benchmark
is 16.7 million enumerations against a fifteen-step shortcut. Here **both** routes are
executable in context by hand, and the compact one (303 ops) is itself already at the
G9(c) 300-operation cap.

## The measured attack numbers (this is what actually kills it)

At the **shipping** preset, 8 seeds each:

| attack | successes |
|---|---|
| frequency / outlier | 0 / 8 |
| **greedy left-to-right, no lookahead, no backtracking** | **8 / 8** |
| random restart ×256 | 0 / 8 |
| in-context row-copy heuristic | 0 / 8 |

`G6_adversary_panel.pass = false`. A recorded solved attack is by itself disqualifying.

The domain-standard algorithm — constraint propagation over (P1)–(P3) — is not merely
efficient, it needs **no search at all**:

| preset | \|S\| | holes | unit propagation, ZERO backtracks | nodes |
|---|---|---|---|---|
| demo | 6 | 5 | solves 8/8, 0.001 s | 1 |
| easy | 12 | 24 | solves 8/8, 0.032 s | 1 |
| medium | 24 | 60 | solves 8/8, 0.60 s | 1 |
| **hard (shipping)** | **40** | **100** | **solves 8/8, 5.10 s, 1.0·10⁷ lookups** | **1** |
| escalated (`escalate()`) | 70 | 100 | solves 100/100 cells, 21.1 s | 1 |

Full propagation + MRV backtracking at the shipping preset: **2 nodes, 4.15 s**.
For contrast, the reference family cited in the brief needed 82 MRV calls after a naive
search blew a 2,000,000-node budget. Here MRV never branches.

## Why no parameter setting rescues it

The obvious escalation axis — grow `|S|` at fixed answer length — makes the family
**easier**, because the hole *density* falls. Measured with `holes` fixed at 100:

| \|S\| | hole density | unit propagation alone |
|---|---|---|
| 16 | 39 % | restores 100/100 |
| 24 | 17 % | restores 100/100 |
| 32 | 10 % | restores 100/100 |
| 40 | 6 % | restores 100/100 |
| 70 | 1 % | restores 100/100 |

Pushing the other way — raise the hole density and shorten `|S|` — was swept finely at
`|S| = 12` (288 cells across both tables):

| holes (= answer atoms) | unit propagation solves | greedy solves | MRV nodes |
|---|---|---|---|
| 172 (60 %) | 4/4 | **4/4** | 3 |
| 201 (70 %) | 4/4 | 0/4 | 4 |
| 216 (75 %) | 4/4 | 0/4 | 5 |
| 230 (80 %) | 4/4 | 0/4 | 6 |
| 244 (85 %) | 4/4 | 0/4 | 8 |
| 259 (90 %) — **over the 256-atom cap** | 1/4 | 0/4 | 25 |

Propagation only begins to fail at 90 % holes, which is **already past the 256-atom
answer cap**, and even there MRV closes the instance in 25 nodes. There is no window
inside the cap where any search is required. This is not a `cap_bound`: the family is
not hard just beyond the cap either.

Beyond that point the *opposite* failure appears. On the pure θ-table variant with
`|S| = 8`: 54 holes of 64 → **8 valid completions**; 60 holes of 64 → **6,534 valid
completions** found in 15,864 nodes. `verify` accepts any of them, so a random or
greedy completion succeeds. The family is squeezed between "unique and forced by
propagation" and "so many answers that guessing works", with nothing in between.

The **general-semigroup** variant (blank cells in the multiplication table too, so the
search includes semigroup/associativity completion) behaves identically: unit
propagation with zero backtracks recovered the planted solution **exactly** with 70 %
of *both* tables blanked at `|S| = 9, 16, 24`.

## The mathematics behind the collapse — the results relied on

1. **Section 1, identities (P1)–(P3).** `s(x,y) = (x·y, θ_x(y))` solves the PE iff
   `(x·y)·z = x·(y·z)`, `θ_x(y)·θ_{x·y}(z) = θ_x(y·z)`, and
   `θ_{θ_x(y)} θ_{x·y} = θ_y`. The last one is an **element constraint**: the unknown
   value of a blanked cell `θ_x(y)` is itself the *row index* of the equation it sits
   in. One known column of `T` therefore collapses that cell's domain to a singleton.
   This is the whole reason propagation needs no search, and it is a property of the
   Pentagon Equation itself, not of how the instance was blanked.

2. **Lemma 2.5 and the left-zero reduction of Section 3.** On a left zero semigroup
   (`x·y = x`) (P1) and (P2) are automatic and the PE collapses to the single identity
   `(x∘y)∘(x∘z) = y∘z` where `x∘y := θ_x(y)`. Enumerating all such magmas gives
   **1, 5, 31, 249, 3096** solutions for `|S| = 1..5` — against `5^25 ≈ 3·10^17`
   candidate tables at `|S| = 5`. The solution set is so thin that any constant
   fraction of the table pins the rest.

3. **The bijective case is a classification.** An easy argument (matching Lemma 2.5)
   shows every bijective solution on a left zero semigroup is `S = T × Z` for a group
   `T` and a set `Z`, with `θ_{(a,z)}(b,w) = (c_z a^{-1} b, w)` — i.e. a group torsor.
   Recovering `T` from the displayed table costs three lookups. That is the compact
   route, and it is why it costs 3 operations per hole.

4. **Theorem 5.6, Theorem 5.7 and Corollary 5.8.** All **involutive** solutions are
   classified up to isomorphism by the three cardinalities `|X|, |A|, |G|`: on a set of
   size `2^n(2m+1)` there are exactly `binom(n+2,2)` of them. Any question restricted
   to the involutive case is a lookup from a decomposition of `|S|`, so that branch was
   never available.

5. **Proposition 3.1 (Kashaev–Sergeev).** On a group there is a *unique* bijective
   solution, `s(x,y) = (xy, y)`. The group factor contributes no freedom either.

6. **Section 6 (Theorem 6.1, Proposition 6.2, Corollary 6.4)** answers structural
   questions about the structure monoid/algebra by explicit formula
   (`clK = GK = rk = |X|`), so the remaining content of the paper produces certificates
   that are direct evaluations, not searches.

## What was NOT tried

- No LLM oracle loop (`scripts/harden.py`) was run. It would be spending four-vendor
  budget on a family that a fifteen-line greedy loop solves 8/8 at the shipping preset.
- No SAT/SMT encoding was tried; it is strictly stronger than the propagation that
  already succeeds with zero backtracks, so it cannot change the verdict.
- The `|S| = 16` and `|S| = 16` (m=4,q=2,g=2) rows of the density sweep were still
  running when the sweep was cut; the `|S| = 12` rows already cover the whole
  answer-length range inside the 256-atom cap.
