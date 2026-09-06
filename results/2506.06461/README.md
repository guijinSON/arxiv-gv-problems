# arXiv:2506.06461 — completing a strong starter of Z_n

**Paper.** Oleg Ogandzhanyants, Sergey Sadov, Margo Kondratieva, *Constructing
strong starters of orders 3p: triplication with SAT solver*, arXiv:2506.06461
(math.CO). <https://arxiv.org/abs/2506.06461>

## Profile

| field | value |
|---|---|
| `TRACK` | **B** — no-tool compression; the efficient algorithm is named below |
| native domain | combinatorics |
| object regime | finite_discrete |
| computational core | csp_sat |
| certificate form | integer_tuple (a list of residues; the object is a set of pairs of Z_n) |
| intended intuition | **symmetry** — the whole starter is one orbit of multiplication by a hidden unit |
| domain essentiality | **native**, `reduction_kind = none` |
| shipping preset | `hard` = `{n: 1259, k: 149}` |

## What the family is

A **starter** in Z_n (n odd) is a partition of Z_n \ {0} into (n−1)/2 pairs
{a,b} whose differences ±(a−b) are exactly the n−1 nonzero residues, one each.
It is **strong** when in addition the (n−1)/2 pair sums a+b are pairwise
distinct and none is 0. That is the paper's Section 1 definition, verbatim, and
it is what `verify` executes.

The solver is handed a strong starter of Z_n with **k of its pairs deleted**,
and must put them back. The k missing difference classes d₁<…<d_k are forced
(the surviving pairs use every other class), so the answer is written as one
residue per missing class: y_j names the pair {y_j, (y_j − d_j) mod n}. That
keeps the answer at k atoms while n and the search both grow.

Checking is cheap and exact: reassemble the full pairing and run the three
conditions above in integer arithmetic mod n — O(n) integer operations, no
floats anywhere. `verify` never looks at `inst["answer"]`; **any** valid
completion is accepted.

**Why this and not the paper's Sudoku.** The paper's contribution is
*triplication*: from a strong starter T of order p coprime with 3 and a key t
it builds an extension table Σ_p (Section 3) and a constraint problem mod 3
(Section 6) whose solution yields a strong starter of order 3p (Theorem
"Solution of Sudoku yields a strong starter"). That Sudoku cannot be generated
answer-first — its solution is precisely what the paper hands to z3, existence
for 3p > 1000 is open (Horton's conjecture, Section 1), and the paper's own
timings need **17,961 s of z3 at p = 499** (`time_101-499.txt` in the arXiv
source). A generator that had to solve its own instances is what rule **G**
forbids. So the family is built on the object triplication *consumes*: a strong
starter of order n coprime with 3, posed as the same shape of
constraint-satisfaction problem the paper solves with z3.

**Generation is answer-first.** The planted starter is the classical
multiplicative one. Pick u of odd multiplicative order m > 1 (so −1 ∉ H = ⟨u⟩),
let A be a union of one coset from each pair {C, −C} of H-cosets (so
A ⊔ −A = Z_n\*), and set c = −u⁻¹. Then cA = −A, hence

* {{x, cx} : x ∈ A} partitions Z_n\*;
* the differences are ±x(1−c) = (1−c)(A ⊔ −A) = Z_n\*, each exactly once;
* the sums are x(1+c), distinct, and nonzero because 1+c = 1−u⁻¹ is a unit.

Two lines, no search, and 2^((n−1)/(2m)) choices of A per (n,u). Then k pairs
are deleted uniformly at random — that set *is* the answer, known before the
instance exists. Note the construction **fails exactly when 3 | n** (a unit of
odd order is 1 mod 3, so 1+c ≡ 0 mod 3): it stops where Horton's conjecture
starts, which is why this family lives at n coprime with 3.

## Why it is hard (Track B)

**The algorithm that exists, named.** Read the ratio c = b·a⁻¹ mod n off any one
displayed pair (both orientations of that pair describe the same starter, so at
most two values of c are tried); then the removed pair with difference class d
is {x, cx} with x(1−c) = ±d, i.e. the reported endpoint is d·(1−c)⁻¹ or
−c·d·(1−c)⁻¹, and the sign is settled by which of the two candidate pairs is
still fully orphaned. Complexity O(k) modular multiplications after two modular
inversions. **Measured at the shipping preset: 504 exact modular operations
(worst case over 8 seeds), 0.34 ms, 8/8 correct.** A second polynomial route
needs no displayed pair at all — sweep λ = (1+c)/(1−c) over Z_n\* and keep the λ
carrying every missing difference class onto an admissible sum: **24,674
modular multiplications (median of 3 seeds; 93,875 worst seen)**, also 3/3
correct.

**The mechanical route, measured.** Without the multiplier, the task is an exact
cover: 298 orphaned residues to be covered by 149 pairs with prescribed
difference classes and pairwise distinct sums, **44.1 candidate pairs per
class** (17.7 if the solver additionally exploits the fact that the planted
starter is skew). Algorithm X with most-constrained-element branching, forward
checking on elements / classes / sums, and randomised restarts does not find a
completion in **1,429,720 nodes / 240 s**, and fails again on 8/8 independent
seeds at a 60 s budget (300,592–354,862 nodes each; the skew-aware variant
290,599–328,535 nodes). Dinitz–Stinson hill climbing — the method the paper
itself used to build its base starters — does not find one in **2,000,000
iterations**, on 8/8 seeds. The gap is 504 operations against >10⁶ search steps,
and the >10⁶ is not executable in context at all.

**Control — the attacks are not simply broken.** The same code solves the sparse
regime instantly: at n=4003, k=99 (1.5 skew-aware candidates per class) the
skew-aware Algorithm X finishes in **99 nodes**, at n=2003, k=99 in **99
nodes**, at n=1259, k=99 in **1,350 nodes**. Difficulty in this family is a
function of the deleted fraction, and the ladder sits above the transition.

This is a Track B claim and nothing more: an efficient algorithm exists, it is
named, and its cost is stated. The family measures whether a solver *finds* the
multiplicative symmetry, not whether the problem is intractable.

## Worked example (the `demo` preset, n = 31, k = 4)

Rendered instance (abridged only in the surrounding prose):

```
A strong starter S of Z_31 exists but 4 of its 15 pairs have been removed.
The remaining 11 pairs are:

  {2,12} {3,16} {4,24} {5,6} {9,17} {10,29} {13,28} {14,23} {15,18} {19,21} {25,30}

Missing difference classes: d_1..d_4 = 4, 6, 7, 14
```

The eight residues not shown are 1, 7, 8, 11, 20, 22, 26, 27.
Answer: `<answer>11, 1, 27, 22</answer>` — i.e. the pairs {11,7}, {1,26},
{27,20}, {22,8}. `verify` returns `(True, "ok")`; enumeration proves this
completion is **unique**. Corrupt it by repeating an entry and `verify` returns
`(False, "residue 11 is used by two of your pairs")`.

A person *can* do this rung by hand: eight residues, four forced differences,
about a dozen trial pairings. That is what `demo` is for; it is not a difficulty
level and `SHIPPING_DIFFICULTY` never names it.

## Difficulty presets

`k` — the answer length — is 149 at every shipped rung; only the haystack moves.
"cand/class" is the number of pairs a solver must consider per missing
difference class (naive / with the skew signature exploited).

| preset | n | k | deleted fraction | cand/class | answer atoms | status |
|---|---|---|---|---|---|---|
| demo | 31 | 4 | 0.27 | 1.5 / 1.3 | 4 | hand-solvable illustration |
| easy | 1601 | 149 | 0.186 | 33.1 / 11.0 | 149 | defeats the panel (skew Algorithm X: 500,001 nodes / 90 s, 3/3 seeds) |
| medium | 1409 | 149 | 0.212 | 38.8 / 14.0 | 149 | defeats the panel |
| **hard (ships)** | **1259** | **149** | **0.237** | **43.7 / 17.7** | **149** | defeats the panel (6 attacks × 8 seeds, 0 successes) |

Presets that were **rejected**, with the gate that rejected them: `n=2003,k=99`
(cand/class 11.4/2.9) and `n=1259,k=99` (18.4/5.5) both fall to the
skew-signature Algorithm X attack in **99** and **1,350** nodes respectively —
they fail G6, and they are the reason the ladder uses k = 149 and a deleted
fraction above 0.18.

`escalate` moves three parameters at fixed answer length: **n down** (the
deleted fraction f = 2k/(n−1) rises and the candidates per class, ≈ 2kf², rise
with it), **n_clustered up** (removed pairs drawn from whole orbits of the
hidden subgroup, worth another 8–15 % candidate density at fixed (n,k)), and
`show_differences` off (the missing classes are computable from the given
pairs — a redundant clue). `escalate({n:1259,k:149,…})` returns
`{n:1031, k:149, n_clustered:74, show_differences:False}` — **candidates per
class 44.1 → 56.9, answer still exactly 149 atoms.** Four
successive escalations were checked: n = 1031, 839, 683, 557 with candidates per
class 56.4, 71.5, 94.5, 120.2 and the answer at 149 atoms throughout. It returns
`"cap_bound"` only when n would drop below 2k+60.

## Gate results

See `selftest_report.json` for the machine-readable version.

| gate | result |
|---|---|
| G1 planted verifies | **24/24** — 4 presets × 6 seeds |
| G2 rejects corruption | 8 corruption modes, all rejected, **8 distinct reasons** |
| G3 round-trip | `parse_answer` recovers the answer from a prose-wrapped reply; garbage → `None` |
| G4 guess resistance | **0 hits / 200,000** structure-aware samples at the shipping preset and **0 / 200,000** at `easy`; declared language 813 bits |
| G5 density + baseline | exact completion counts where enumeration terminates: **1** at n=31 k=4, **4** at n=211 k=20, **4** at n=997 k=49; sampled density **0/200,000** at the shipping preset; strongest attack **1,429,720 nodes / 240.0 s, unsolved**; reference **504 ops / 0.13 ms, correct** |
| G6 adversary panel | **6 attacks, 0/8 successes each**; reference algorithm reported separately: **8/8, 503 ops, 0.34 ms**; λ-sweep fallback **3/3, 24,674 ops** |
| G7 scales | escalated instance builds and verifies; candidates/class **44.1 → 56.9** with the answer fixed at **149 atoms** |
| G8 canonical_key | invariant under x → v·x, pair reordering and intra-pair swaps over 20 seeds × 4 multipliers; the carried answer still verifies; 20/20 distinct keys |
| G9 caps | **149 atoms ≤ 256; 756 chars ≈ 222 tokens ≤ 2000; intended route 504 operations ≤ 1000** |

### The adversary panel

| attack | what it is | result |
|---|---|---|
| `exact_cover_algorithm_X_mrv` | Algorithm X, most-constrained-element branching, forward checking, randomised restarts — the standard method for exact cover, and the CSP the paper hands to z3 | 0/8 (≈340k nodes / 60 s each) |
| `exact_cover_skew_signature` | the same, plus the construction-aware pruning that the planted starter is skew (admissible sums drop from ~n/2 to 2k) | 0/8 (≈300k nodes / 60 s each) |
| `dinitz_stinson_hill_climbing` | the standard construction method for starters, and the one this paper used for its own base starters | 0/8 (2,000,000 iterations each) |
| `greedy_smallest_difference_first` | the in-context route: walk the missing classes in order, take the first admissible pair, no backtracking | 0/8 |
| `outlier_min_pair_sum` | per-class outlier probe: is the planted pair the extreme one on a local statistic? | 0/8 |
| `constant_shift_ansatz` | the first ansatz a reader guesses — an additive starter {x, x+e} | 0/8 |
| **reference (not an attack)** | recover the hidden multiplier from one displayed pair | **8/8, 503 ops, 0.34 ms** |

## The oracle loop and the G9 arms

Not run here: this build had no `OPENROUTER_API_KEY`, so `scripts/harden.py`
(STEP 4) and the G9 hinted/placebo arms have not been executed.
`llm_loop_transcript.jsonl`, `.meta.json`, `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl` must be produced by the harness before this result
is submitted; `G9_no_tool_suitability.arms` is `null` in the report for exactly
that reason, and its `pass` reflects the size-and-effort caps only, which are
the gated part.

Measured now, and independent of the oracle: **answer 149 elements / 756
characters / ≈222 tokens; intended route 504 exact modular operations plus 149
membership lookups against the printed instance.**

`STRUCTURAL_HINT` names only the invariant — *"Every pair of the starter, given
or missing, has the form {x, c·x} mod n for one and the same c."* — and stops
there: it does not say how to get c, does not mention (1−c)⁻¹, and does not
chain a second step.

## How to use it

```python
import gen_2506_06461 as G
inst = G.make_instance(seed=0, **G.DIFFICULTY[G.SHIPPING_DIFFICULTY])
print(G.render(inst))                 # the whole problem statement
print(G.verify(inst, inst["answer"])) # (True, 'ok')
print(G.verify(inst, G.parse_answer("<answer>1, 2, 3</answer>")))
```

```bash
scripts/emit.sh 2506.06461
```

## Caveats — read these

* **No SAT solver was run.** The module must stay standard-library-only, so
  z3/minisat/CP-SAT were unavailable. The mechanical baseline is my own
  Algorithm X (most-constrained-element ordering + forward checking + randomised
  restarts) and Dinitz–Stinson hill climbing. **A CDCL solver with clause
  learning might do materially better than either**, and the paper's own
  experience — z3 solving a *different but comparable* mod-3 constraint problem
  at p ≈ 100 in ~100 s — suggests it would at least not be hopeless. What I can
  say is bounded by what I ran: two structurally different search methods, both
  at 2·10⁶ steps, on 8 seeds, without success, while the same code solves the
  sparse regime in under 100 nodes. Nobody should read that as "no polynomial
  algorithm exists": Track B claims the opposite, and names one.
* **The planted starter is skew** (its sum set contains exactly one of {s,−s}
  for every s), which is a genuine signature of the multiplicative
  construction, and it is *not* declared in the problem statement. An attacker
  who guesses it prunes the admissible sums from ~n/2 values to 2k. That is in
  the panel as `exact_cover_skew_signature` and it fails at every shipped
  preset — but it is the single strongest structural leak in this family, and
  it is what forced the ladder up to k = 149. If a smarter use of skewness
  exists, this family is where it would bite.
* **What P(guess) means here.** `random_candidate` samples per-class from the
  pairs a solver can already see are admissible (both endpoints orphaned,
  correct difference class, sum not already used); it does not enforce the
  joint constraints. 0 hits in 200,000 says the joint constraints are what is
  hard, not that the per-class filtering is. The naive space (all k-tuples of
  residues) is ~10^460 and is not the number to quote.
* **`verify` really does accept other witnesses.** At n=997, k=49 the
  completion is 4-fold; all four were enumerated and all four verify, and only
  one of them is the planted answer.
* **Solution counts are tiny.** Where enumeration terminates, the completion is
  unique or nearly so (1, 4, 4 at the three sizes counted). At the shipping
  preset enumeration does not terminate, so the density is reported as a sampled
  0/200,000. A near-unique solution is what makes the search hard; it also means
  a solver that finds *any* completion has found essentially the planted one.
* **Attacks not tried:** an LP/SDP relaxation of the exact cover, a CDCL SAT
  encoding, and a dedicated rainbow-matching algorithm. Also untried: an
  attacker who tries to detect the H-orbit structure of the orphan set directly
  rather than through a displayed pair.
* **The paper's own algorithm is not tested by this family.** Triplication is
  context here, not the task; a solver could know nothing about Σ_p or the
  mod-3 Sudoku and still be perfect at this. What the family shares with the
  paper is the object (a strong starter of Z_n, n coprime with 3, which is
  exactly triplication's input) and the shape of the search (a
  constraint-satisfaction problem over that object). `domain_essentiality` is
  declared `native` on that basis: the solver is handed the paper's objects and
  `verify` runs the paper's definition on them.
