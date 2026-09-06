# REJECTED — arXiv:1810.01440

**"A Novel Algebraic Geometry Compiling Framework for Adiabatic Quantum
Computations"**, Raouf Dridi, Hedayat Alghassi, Sridhar Tayur (quant-ph, cs.IT,
cs.SC, math.AG).

**Verdict: REJECT. The family fails H — on both tracks.**
Not on G (planting is clean, no search), and not on V (verification is exact
integer arithmetic; no float is created anywhere in `verify`).

The retained module is `rejected_gen_1810_01440.py`; its measured gate report is
`selftest_report.json`. Neither of the two traps stated at the outset is what
killed it — the reason is a third one, recorded below.

---

## What was built

The paper's central object is the **fiber bundle** of §4.2.2, eq. (rep2):

    pi : Vertices(X) -> Vertices(Y) u {0},   pi(x_i) = sum_j alpha_ij y_j

with `alpha_ij` binary, `sum_j alpha_ij = beta_i`, `alpha_{ij1} alpha_{ij2} = 0`.
The fibers `pi^{-1}(y_j)` are the chains of the minor embedding of Definition
`olddef` (§4.2.1). §4.2.3 adds the size condition eq. (sc) (`|fiber| <= k`), the
Connected Fiber Condition eq. (cc) (which forces each fiber to be a *subtree*,
so a fiber of size k has exactly k−1 internal edges), and the Pullback
Condition proposition. §4.2.3 also displays the pullback of the quadratic form,

    pi^*(Q_X)(y) = sum_{j1<j2} c_{j1j2} y_{j1} y_{j2} + sum_j d_j y_j^2,

where `c_{j1j2}` is exactly the number of X-edges joining two fibers and `d_j`
the number inside fiber j.

**The family:** hand the solver the hardware graph `X = Chimera C_{L,L,t}` (the
paper's own hardware; D-Wave 2000Q is `C_{16,16,4}`) and the **exact integer
coefficients** of `pi^*(Q_X)`, and ask for a fiber bundle realising them. This
is strictly stronger than the paper's own Pullback Condition, which only asks
that `c_{j1j2}` be non-zero (it writes it as `1 + delta^2`).

* **G — clean.** `make_instance` grows m disjoint connected k-subtrees inside X
  and *then* computes `C = pi^*(Q_X)` from them. The answer exists before the
  instance does; nothing is ever searched for. Measured: **G1 24/24** planted
  instances verify across all four presets × 6 seeds.
* **V — clean and exact.** `verify` counts edges, runs a BFS, and compares
  integers. `grep` finds no float literal, no `float(`, and no division in it.
  Measured: **24/24 seeds** verify at the shipping preset; the `demo` preset has
  exactly **128** valid answers (`enumerate_all`, exhaustive).
* **H — fails.** Below.

---

## Trap 1 (floating point) did NOT fire — it was avoided by construction

The part of the paper that would have fired it is §4.3, Proposition `specGap`:
the minimum spectral gap of `H(t) = alpha(t) H_initial + beta(t) H_(P)` needs
real eigenvalues of a `2^n x 2^n` Hermitian matrix. That was never built. Note
that `H_(P)` alone *is* diagonal in the computational basis and therefore exactly
integer — but a ground state of a diagonal Ising Hamiltonian is a claim of
optimality with no witness attached, so it fails the witness rule instead.

## Trap 2 (the Groebner route is the compact route) did NOT fire either

For this family the paper's own algebraic route is *not* cheap. The ideal
`I ⊂ Q[alpha, beta, delta]` of §4.2.3 has `n·m` binary `alpha_ij` variables —
**4,096** of them at the shipping preset (n = 128, m = 32) — and its reduced
Groebner basis is the object the proposition "a Y minor exists iff 1 ∉ B" needs.
The paper's own timings are 0.122 s for its 20-variable example (§4.2.5 table)
and it states plainly in §1.2 *Goals of the paper*: "We recognize that the
(worst-case) computational complexity of our procedure is not polynomial." No
Groebner or linear-algebra computation recovers this witness cheaply. Linear
algebra is unavailable outright: the constraints eq. (rep2)/(cc) are quadratic
and cubic, not linear.

## What actually killed it: a generic CP solver, and an escalation ladder that runs backwards

### (a) The domain-standard attack succeeds — Track A fails

For a set-partition / exact-cover core the prompt's own table names Algorithm X
/ DLX or a CP solver. Implemented as `_cp_solve`: bitmask candidate sets over
all connected k-subsets, **forward checking on the exact pullback coefficients**,
**MRV** dynamic variable ordering, and Algorithm-X style coverage pruning.

| preset | params | n, m | CP+MRV solved | nodes (min…max) |
|---|---|---|---|---|
| easy | L=3, t=4, k=3 | 72, 24 | **5/5** | 30 … 65,569 |
| **medium (shipping)** | L=4, t=4, k=4 | 128, 32 | **4/8** | 32 … 4,111 |
| hard = `escalate()` destination | L=2, t=16, k=4 | 128, 32 | **5/5** | **32 … 200** |

Track A requires `successes == 0` for every entry in `attacks`, the domain
algorithm included. The measured panel is:

| attack | successes / attempts |
|---|---|
| `outlier_degree_position` | 0 / 8 |
| `greedy_chain_growth` | 0 / 8 |
| `random_restart_1k` | 0 / 8 |
| `spectral_laplacian_cut` | 0 / 8 |
| `static_backtracking_2e6` | 0 / 8 |
| **`cp_mrv_forward_checking`** (the domain standard) | **4 / 8** |

**G6 fails**, and so does G5. Every other gate passes (see the table below).

The non-solves at `medium` are *not* evidence of hardness: they are my
pure-Python wall clock (120 s cap) at node counts of only 7,686 and 16,113. A
real CP or SAT solver disposes of 10^4 nodes in well under a second. The
solved-count 4/8 is therefore a **lower bound**. The decisive number is the row
below it: at the preset `escalate()` actually sends the ladder to, the attack
wins 5/5 in 32–200 nodes.

This is the project's own documented failure mode reproduced exactly. With the
**same** search but a **static** label order and no forward checking
(`attack_static_backtrack`), the planted instance survives **2,000,000 nodes**
at every preset — 0/21 solved. Adding MRV and forward checking drops that to
**8–571 nodes** at n ≤ 72 and **32 nodes** at the `hard` preset. Compare
`AUDIT.md`: "MRV ordering cracked in 82 calls what naive backtracking could not
do in 2,000,000."

### (b) The escalation ladder makes the family EASIER

The answer is one label per physical qubit, so the answer length *is* `n =
2tL^2`; the 256-atom cap forces `n <= 256` and both fixed-length axes were
measured to move the wrong way:

| step | params | n | answer atoms | CP+MRV nodes |
|---|---|---|---|---|
| shipping | L=4, t=4, k=4 | 128 | 128 | 32 … 16,113 |
| `escalate()` #1 (raise cell density t) | L=2, t=16, k=4 | 128 | 128 | **32 … 200** (5/5 solved; 6.2 × 10^6 ops) |
| `escalate()` #2 | L=1, t=64, k=4 | 128 | 128 | not measurable — the candidate pool (connected 4-subtrees of K_{64,64}) blows past enumeration, but K_{64,64} is more symmetric still |
| `escalate()` #3 (raise chain size k) | L=1, t=64, k=8 | 128 | 128 | — |

Raising the density gives each chain more room, which multiplies the solution
count and *shortens* the search; raising k does the same (probe: n=32, k=2 took
16 nodes, k=4 took 8). Growing `n` instead — the sparse regime where `m·k << n`,
which is the planted-clique shape the prompt asks for — is worse still:
**naive static backtracking alone**, no MRV, solved 17/18 planted embeddings at
n=288, m=8, k=3 with a median of **1,722 nodes and 0.025 s**. There is no axis
on which this family gets harder.

### (c) There is no compact route — Track B fails too

Track B is rejected only when the compact route is no shorter than the
mechanical one. Here they are the *same route*:

| | route | measured cost at the shipping preset |
|---|---|---|
| **mechanical** | CP + forward checking + MRV | median **3,044 nodes**; instrumented operation counts **8.4 × 10^5** (seed 3, 32 nodes) and **6.4 × 10^7** (seed 2, 4,111 nodes); 1.3 s and 44.6 s in Python |
| **compact** | the structural hint — "a zero pullback coefficient forbids the two chains from touching" | **the same propagation rule**. Executed by hand it is the same 10^6–10^8 operations; naming it removes no work |

The "insight" this family would test *is* the propagation rule the mechanical
route already implements. Seeing it buys a solver nothing it can execute: the
answer is **128 atoms** that must each be pinned by search, and the cheapest
correct route is ~10^8 exact operations against G9(c)'s cap of **1,000**. Ratio
mechanical : compact ≈ **1**. That is the reject condition verbatim — there is
nothing to see, so the question tests nothing. It would be a search-stamina
test, not a generator–verifier gap.

---

## The paper's other candidate families, and why each was not built

| § | family | why not |
|---|---|---|
| §4.1, Prop. after eq. (idealPairs), remark (a) | **minimal quadratization via the toric ideal** `J_A = K_A ∩ Q[x]`. The Groebner basis of `K_A` w.r.t. plex `y ≻ x` is a rewriting system replacing `y_a y_b y_c` by `x_p y_.` for a pair `p ⊂ {a,b,c}`, so a reduction is valid iff every cubic monomial of `f` contains a chosen pair. Genuinely NP-hard (remark (a)). | **Dies to a statistic with no search at all.** A planted pair occurs in far more monomials than a random one. Ranking pairs by monomial-degree and taking the top t solves **8/8** at every size tried — (m,t,T) = (12,6,40), (16,8,80), (24,12,200), (32,16,400). Greedy max-coverage also solves 8/8. Mechanical route ≈ 3T integer counts ≈ 1,200 ops at m=32; compact route identical. |
| §4.2.4, staircase proposition | counting embeddings from the staircase diagram | the answer is a single integer with no witness — fails the witness rule. |
| §4.2.5 | folding X along `G ≤ Aut(X)` into invariant coordinates | if the symmetry `σ` is given, the complete set of invariants is the orbit sums and products, written down in O(n) — the paper says so in its own footnote. If `σ` is not given, the task is graph automorphism, which colour refinement settles on Chimera immediately. Cheap either way. |
| §4.3, Prop. `specGap` | spectral gap of the adiabatic Hamiltonian as a function of the embedding variety | trap 1: real eigenvalues of a `2^n × 2^n` matrix. Not exactly verifiable. |
| §5, Def. + Prop. `YminorUniversal` | design a `Y`-minor universal hardware graph X of size n and degree ≤ d | the witness must carry X **and** every embedding `π^μ` (otherwise verification is itself minor-containment), which blows the 256-atom cap; and each embedding is then attackable by exactly the CP route above. Not built — recorded here as the one family that was reasoned about rather than measured. |

---

## Measured gate report

See `selftest_report.json`. Summary:

| gate | pass | number |
|---|---|---|
| G1 planted verifies | **true** | 24/24 (4 presets × 6 seeds) |
| G2 rejects corruption | **true** | 7 distinct reasons from 7 corruptions |
| G3 round-trip | **true** | recovered from a prose-wrapped reply |
| G4 guess resistance | **true** | 0 hits / 3,000 structure-aware samples (each sample is already a partition into connected k-subtrees); naive space `128!/(4!)^32` ≈ 2^568 |
| G5 density + baseline | **false** | demo has exactly **128** valid answers (exhaustive); shipping density **0/3,000**; strongest attack solves **4/8**, median **3,044 nodes**, 6.4 × 10^7 ops |
| G6 adversary panel | **false** | 5 attacks at 0/8; `cp_mrv_forward_checking` **4/8** |
| G7 scales | true (builds) | escalated instance builds and verifies at 128 atoms — but difficulty *falls*, see (b) |
| G8 canonical_key | **true** | 60/60 invariant under logical relabelling, 20/20 distinct |
| G9 caps | **true on size only** | answer **128 atoms / 467 chars / ~116 tokens**, inside the 256-atom and 2,000-char caps. The reported `intended_route_operations` of 624 is a *verification* count; the honest *solving* count is 10^6–10^8, against a cap of 1,000. See (c). |

G4's sample count is 3,000, not the 200,000 the gate asks for: each
structure-aware sample requires a full planting run (0.046 s), so 200,000 would
be 2.5 hours. The number is reported as measured rather than rounded up.

## Caveats — attacks I did not run

* **minorminer / the Cai–Macready–Roy chain-growing heuristic** ([CaiMR14],
  [Boothby2016], cited by the paper itself at the end of §4.2.1). This is the
  domain-standard heuristic for minor embedding. It does not apply to the tight
  regime (it does not force every physical qubit to be used), but it is the
  right attack on the sparse regime — which already fell to plain backtracking,
  so running it would only widen an already-decisive result.
* **A real SAT/CP solver** (MiniSat, OR-Tools). My CP is hand-rolled Python; its
  wall clock is not the algorithm's. All hardness statements above are therefore
  quoted in **nodes**, not seconds.
* One variant resisted my Python CP: the **support-only** tight regime, i.e. the
  paper's literal Definition `olddef` with only the *support* of `pi^*(Q_X)`
  given (the logical graph Y) rather than its exact coefficients. CP+MRV solved
  0/9 there within 90 s, at 739–45,896 nodes. I do **not** claim that family is
  hard: the node counts are within easy reach of a real solver, the low counts at
  n=128 reflect ~0.1 s per node in Python, and it inherits (b) and (c) unchanged
  — the same 128-atom answer, the same inverted escalation, the same absent
  compact route. It is recorded here so the decision can be re-opened by someone
  with a real solver.
