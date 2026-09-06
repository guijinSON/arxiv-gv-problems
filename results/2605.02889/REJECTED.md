# REJECTED — arXiv:2605.02889

**Roman Gorazd, "Gluing diagrams part 1: A constructive solution for the
Higman–Thompson group isomorphism problem" (math.GR, math.CO), v2, 30 pp.**

Verdict: **rejected on H**, on both tracks, and additionally on instance
diversity. **G and V both pass** and are reported here with their numbers so the
decision can be re-opened. The module is kept as `rejected_gen_2605_02889.py`.

---

## 1. The family that was built

Section 4 ("Example of application") specialises the paper's machinery to the
one-vertex graph `G_n` (one vertex `v`, `n` loops) with `x_v = l·v`. Unpacking
Definition 3.3 (`sec2-def1`) in that case, a **floating gluing diagram from `G_n`
to itself with `x_v = l·v`** is exactly:

* a finite complete `n`-ary forest `F` with `l` roots. Since the basis
  `B_v = ⨆_i C_{e_i}` must satisfy `|B_v| = l + k(n−1) = n·l`, the forest has
  exactly `l` internal nodes and `n·l` leaves;
* a **bijection `Λ : Leaves(F) → {0..n−1} × {0..l−1}`** (block index from the
  partition `C_{e_i}`, state index from `γ_{e_i}`).

Task posed to the solver: **given `n`, `l` and the forest `F`, produce `Λ`.**

### The validity condition, and where it comes from (this is the one piece of
real mathematics in the build)

Lemma 3.14 (`unblock-cover-lem`) makes surjectivity equivalent to the diagram
being *unblocked*, and Theorem 3.24 (`shift-surj-thm`) plus Definition 3.20
(`defn-enable`) make shift-surjectivity equivalent to "every pair of nodes
internal in `B_v` has its shift enabled". Read `Λ` as a transducer whose
**configurations are the `l` internal nodes of `F`**: from configuration `c` on
letter `x`, go to `c.x` silently if `c.x` is internal; otherwise emit
`Λ(c.x) = (i,j)` and jump to the internal node reached from root `j` along the
blocking chain. Then, because Definition 3.20 quantifies over the **same** suffix
`r'` on both sides, "enables the shift from `p` to `q`" is equivalent to

> there is a finite antichain of inputs on each of which the two runs, started at
> `p` and at `q`, **complete a leaf at the same step and in the same state `j`**,

and Theorem 3.24 therefore reduces to: **the product automaton on ordered pairs
of internal nodes, with simultaneous-equal-state completion made absorbing, has
no directed cycle.** With the blocking-chain acyclicity this is an exact,
integer-only `O(l²n)` check.

**Cross-validation of that reduction** (it is the module's `verify`):

| check | result |
|---|---|
| the paper's own ladder (Lemmas 4.9 `easy-impl-lem`, 4.15 `hard-impl-lem`, 4.16 `reach-lem`) produces diagrams that the criterion accepts | **132 / 132** reachable `(l,n)`, `l ≤ 9`, `n ≤ 8` |
| brute-force evaluation of Definition 3.20 itself (build `C_s` from the recursion `C_{si}=C_s ∘_{γ_s} C_{e_i}`, search antichains `D_p`, `D_q` and the bijection `ν`, allowing refinements as the definition permits) vs. the criterion, at `n=4, l=2` | **27 agree / 0 disagree** (373 runs inconclusive at the search depth used) |

---

## 2. G — PASSES

The answer is built **first**, by the paper's construction, never by search:
Lemma 4.16 (`reach-lem`) descends `(l, n)` by the Euclidean algorithm on
`(l, n−1)` to the base `(1,2)`, and the module replays that descent upward with
random free choices — the expansion root at each `E`-step (Def. 3.31 `exp-defn`,
Lemma 4.9), and the bijections `ρ`, `γ₊` at each `A`-step (the `𝔊 → 𝔊⁺`
construction, Lemma 4.15). No search anywhere in `make_instance`.

`verify(inst, inst["answer"])` is **True on 100/100** instances (4 presets × 25
seeds): demo `n=4,l=2`; easy `n=5,l=3`; medium `n=6,l=4`; hard `n=7,l=5`.

## 3. V — PASSES

Exact and cheap: prefix-code check, bijection check, blocking-chain cycle
detection, cycle detection in the `l²`-state pair automaton. Integer only, no
floats, `O(l²n)`.

**How many valid answers exist** (sampled uniformly over the structure-aware
candidate space = all bijections `Leaves → {0..n−1}×{0..l−1}`):

| preset | space | valid fraction | ⇒ absolute number of valid answers |
|---|---|---|---|
| demo `n=4,l=2` | `8! = 4.0e4` | **3456/40320 = 8.57e−2** (exact, exhaustive) | 3 456 |
| easy `n=5,l=3` | `15! = 1.3e12` | 273/400 000 = 6.8e−4 | ≈ 8.9e8 |
| medium `n=6,l=4` | `24! = 6.2e23` | 3/300 000 = 1.0e−5 | ≈ 6.2e18 |
| hard `n=7,l=5` | `35! = 1.0e40` | 0/300 000 (< 3.3e−6) | ≳ 3.4e34 |

**Answer cap — passes everywhere** (limit 2 000 chars / 256 atoms):

| preset | atoms | chars |
|---|---|---|
| demo | 16 | 31 |
| easy | 30 | 59 |
| medium | 48 | 95 |
| hard | 70 | 139 |
| `n=5,l=7` (escalated, same length) | 70 | 139 |
| `n=6,l=8` | 96 | 191 |

---

## 4. H — FAILS. The two numbers.

### compact route

The paper's Euclidean ladder. Measured, counting elementary
forest/label operations, and each run checked to produce a `verify`-True answer:

| preset | ladder | moves | **compact-route operations** |
|---|---|---|---|
| demo `n=4,l=2` | `(1,2) →E (2,2) →A (2,4)` | 2 | **17** |
| easy `n=5,l=3` | `EEA` | 3 | **35** |
| medium `n=6,l=4` | `EEEA` | 4 | **58** |
| hard `n=7,l=5` | `EEEEA` | 5 | **86** |

### mechanical route

Domain-standard attack for this constraint shape: **min-conflicts / simulated
annealing over the labelling**, energy = number of ordered pairs of internal
nodes that can still reach a non-success cycle, move = swap two leaf labels
(unoptimised Python, ≈ 2.1e4 swap evaluations/s).

| preset | 45 s budget, 8 seeds | 300 s budget, 4 seeds | median steps |
|---|---|---|---|
| demo `n=4,l=2` | **8/8 solved** | — | 14 |
| easy `n=5,l=3` | **8/8 solved** | — | 2 354 (0.03 s) |
| medium `n=6,l=4` | **8/8 solved** | — | 50 785 (1.1 s) |
| hard `n=7,l=5` | 1/8 | **2/4 solved** (1 293 494 steps/110 s; 306 964 steps/22 s) | 2 102 317 |
| `n=5,l=7` | 1/8 | **1/2 solved** (739 850 steps/145 s) | — |
| `n=8,l=6` | 1/8 | — | 833 051 |
| `n=6,l=8` | 0/8 | — | 595 867 |
| `n=2,l=24` | 0/8 | — | 111 057 |

### why this is a rejection and not a Track B family

At the single preset that survives the in-context attacks (`n=7,l=5`) the two
numbers *are* far apart — 86 operations against ~1.3e6 swap evaluations — and a
Track B story could be told there. It fails anyway, on three measured grounds:

**(a) One rung down, a rule with NO SEARCH AT ALL is outright correct.**
The rule "sort the leaves lexicographically and give leaf *k* the label
`(k div l, k mod l)`" produces a `verify`-True diagram on

| preset | greedy hits (no search), 20 seeds |
|---|---|
| demo `n=4,l=2` | **20/20** (three separate rules all work) |
| easy `n=5,l=3` | 1/20 |
| medium `n=6,l=4` | **11/20** |
| hard `n=7,l=5` | 0/20 |
| `n=5,l=7`, `n=6,l=8` | 0/20 |

11/20 = 55 % with zero search is the same disqualifying signature this project
has already rejected twice ("pick the positional outlier solved 37 %", "pick the
narrowest solved 25 %"). Together with the 8.57 % *unconditional* valid fraction
at demo, the difficulty band is exactly one rung wide.

**(b) `escalate()` cannot widen it.** Holding the answer length fixed at 70
atoms and moving both parameters, `n=7,l=5 → n=5,l=7`, made the mechanical
attack **cheaper**, not dearer: first solve at 739 850 steps / 145 s instead of
1 293 494 steps / 110 s, and the lex-DFS median fell from 100 251 to 42 199
nodes. Going further, `n=6,l=8` (96 atoms) gives a *lower* median annealing step
count (595 867) than `n=7,l=5`, and `n=2,l=24` lower still (111 057). Two
parameters move and the difficulty does not rise. There is also almost no room:
the 256-atom cap bounds `n·l ≤ 128`.

**(c) The mechanical route is not a wall.** The attack above is unoptimised
Python and already recovers verified witnesses at the shipping preset in 22–110 s.

---

## 5. Additional, independent disqualifier: the family has almost no instances

The instance is the forest `F`; the answer is the labelling. The ladder's move
sequence is **forced** — Lemma 4.16 is the Euclidean algorithm on `(l, n−1)`, so
there is exactly one descent — and the only shape freedom is which unblocked root
each `E`-step expands. Measured over **300 seeds per preset**, using a shape
invariant (multiset over roots of recursively-sorted subtree shapes) that is
invariant under every symmetry of the family (`S_l` on roots, global `S_n` on
letters, `S_n` on blocks):

| preset | distinct forests over 300 seeds |
|---|---|
| demo `n=4,l=2` | **1** |
| easy `n=5,l=3` | **1** |
| medium `n=6,l=4` | **2** |
| hard `n=7,l=5` | **3** |
| `n=5,l=7` | **2** |
| `n=6,l=8` | **1** |

The prompt asks for "an unlimited supply of instances". This family supplies one
to three per preset. Every seed re-poses the same question with a different
planted answer, and since `verify` accepts any valid witness (of which there are
≳3e34), the seeds are not distinguishable problems at all.

---

## 6. What was relied on, by number

* Definition 3.3 (`sec2-def1`) — the definition of a (floating) gluing diagram.
* Definition 3.13 — blocked / unblocked, blocking chains and cycles.
* Lemma 3.14 (`unblock-cover-lem`) — unblocked ⟺ the induced homomorphism is
  surjective.
* Definition 3.20 (`defn-enable`) — "enables the shift from `p` to `q`"; the
  shared-suffix quantifier is what turns into simultaneous completion.
* Theorem 3.24 (`shift-surj-thm`) — shift-surjectivity ⟺ every pair of internal
  nodes has its shift enabled. **This is the verifier.**
* Definition 3.31 (`exp-defn`) + Lemma 4.9 (`easy-impl-lem`) — the `E` move,
  `(l,n) → (l+n−1, n)`.
* Lemmas 4.12–4.14 and 4.15 (`hard-impl-lem`) — the `𝔊 → 𝔊⁺` `A` move,
  `(l,n) → (l, n+l)`.
* **Lemma 4.16 (`reach-lem`)** — `(l,n)` is reachable whenever `gcd(l, n−1) = 1`,
  by Euclidean descent to `(1,2)`. **This is the compact route, and its being a
  forced descent is why the family has no instance diversity.**
* Lemma 4.7 (`first-impl-lem`) and Theorem 4.17 — the classification
  `V_{a,n} ≅ V_{b,m} ⟺ n=m and gcd(a,n−1)=gcd(b,m−1)`; not used, it is a lookup.

## 7. Framings that were tried and measured before this one

The brief asked specifically for a framing in which knowing the construction is
not enough. Two were built and measured first; both died faster.

1. **Completion** — reveal all but `h` labels of a valid diagram, ask for the
   rest. MRV backtracking with blocking/pair-cycle propagation finished with
   **11–35 nodes** (i.e. essentially zero backtracking) at every preset from
   `n=5,l=3` up to `n=10,l=8`, for `h = 10` and `h = 14`. Same shape as the
   `2004.04028` rejection.
2. **Random forests** — pose the labelling problem on a forest that is *not*
   ladder-shaped. Measured: **0 of 18 random forests** (`n=5,l=3`; `n=6,l=4`;
   `n=7,l=5`, 6 seeds each) admit any valid labelling at all, so the instance
   cannot be randomised away from the ladder shape. This is also the reason for
   §5: the forest is essentially determined by `(l,n)`.

## 8. Files

* `rejected_gen_2605_02889.py` — the working module (kept, per the prompt).
  `DIFFICULTY`, `make_instance`, `render`, `parse_answer`, `verify`, `escalate`,
  plus `random_candidate`, `search_space`, `enumerate_all`, `canonical_key`,
  `TRACK`, `PROBLEM_PROFILE`, `NATIVE`, `CERTIFICATE_LANGUAGE`, the two hints.
  It passes G1 100/100 and every answer-cap check; it is rejected on H and on
  instance diversity, not on correctness.
* No `llm_loop_transcript.jsonl` / `.meta.json`: `scripts/harden.py` was not run
  (no `OPENROUTER_API_KEY` in this environment, by design of the run).
