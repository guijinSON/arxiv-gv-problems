# REJECTED — arXiv:2510.11212

**Grochow & Natarajan, "Gröbner Bases Native to Term-ordered Commutative Algebras,
with Application to the Hodge Algebra of Minors"** (math.AC, cs.SC, math.AG, math.RA).

**Verdict: REJECTED on H.  G holds, V holds.  Fails H on BOTH tracks.**

Retained module: `rejected_gen_2510_11212.py` (complete: `DIFFICULTY`, `make_instance`,
`render`, `parse_answer`, `verify`, `escalate`, `canonical_key`, `random_candidate`).
Measured evidence: `selftest_report.json`, `measurements.json`.

---

## 1. The family that was built

The paper's only genuinely non-constructive object. From the authors' own conclusion
(`conclusion.tex:25`): the two subroutines of **Algorithm 7.1** —
`get-admissible-shapes` and `get-admissible-standard-bd` — are

> "naive exhaustive searches over combinatorial spaces that are easily seen to have
> exponential size"

and the paper poses as an **open question** whether a pair of standard bideterminants can
have exponentially many LCMs and whether they can be enumerated with polynomial delay.

**Family.** Given two standard bitableaux `f`, `g` over an `m x n` generic matrix, produce
one **least common standard multiple** relative to `A_gen^bd`
(Definition 5.10 `defn:lcms`; Theorem 7.19 `thm:lcm-algo`).

**Why G holds.** Pure inverse generation, no search in `make_instance`. Plant `L` first as
a random standard bitableau whose column heights are **pairwise distinct**, then cut `f`
and `g` out of it as two overlapping, covering sub-multisets of its columns. Distinct
heights force the multiset union of `shape(f)` and `shape(g)` to equal `shape(L)`, so by
Lemma 7.22 every common multiple has at least `|shape(L)|` columns; hence no proper
divisor of `L` is a common multiple and `L` is least **by construction**. 40/40 planted
answers verify at the shipping preset.

**Why V holds.** Exact integer/multiset arithmetic, no floats. Divisibility is
Theorem 7.12(II) run backwards: multiset-subtract rows and column heights (Lemma 7.22),
then *recompute* `LT(f*h)` by merge-and-sort and compare. Leastness costs a bounded
enumeration of the one-column-smaller divisors (see §4).

---

## 2. H fails — the two numbers

| | route | measured at the shipping preset (`m=n=7`, shape `(5,4,3,2,1)`) |
|---|---|---|
| **mechanical** | the paper's Algorithm 7.1 as written: enumerate every standard bitableau of every admissible shape, then filter on line 10 | **223,812,255,744** standard bitableaux (exact, hook-content formula; 2.24e11). Escalated to `m=n=9`, shape `(6,...,1)`: **8.09e17** |
| **compact** | constraint propagation on the forced row multisets | **median 35 backtracking nodes**, max 954; ≈5e2 exact operations; **median 0.22 s** |

The gap is 6.4e9 — which looks like a textbook Track B family. It is not, and this is
the whole point of the rejection:

**The compact route is itself an in-context attack, and it succeeds.**

| attack | result at the shipping preset, 40 seeds |
|---|---|
| `constraint_propagation_rows` (the compact route) | **solved 40/40**, median 35 nodes, 0.22 s |
| `union_rows_padding` — zero search: row *i* = multiplicity-wise union of row *i* of `f` and `g`, padded by repeating its largest entry | **solved 23/40 (58%)** |
| `obvious_LT_fg` — the ansatz `L = LT(f*g)` (Theorem 7.12(II)) | solved 0/40 |
| random guessing from `CERTIFICATE_LANGUAGE` | 0 / 200,000 |

- **Track A fails.** An efficient algorithm exists for the distribution generated, and it
  is not exotic: the shape is *forced* (Lemma 7.22 makes `shape(L) ⊇ shape(f) ∪ shape(g)`
  necessary, and distinct heights make it exact), the required content of each row is
  *forced* (`re_i = R(R_f,i) ∪ R(R_g,i)`), and the row tableau and the column tableau
  **decouple**, so what remains is two independent semi-standard-tableau completions with
  a handful of free boxes. 40/40 in a median of 35 nodes.
- **Track B fails.** Per the contract, a Track B family needs a fourth *failing*
  in-context attack. There is none. A no-tool solver executes the 35-node route by hand,
  and a one-line heuristic with **no search at all** is right 58% of the time. The
  four-vendor oracle pool would take this on the first attempt.

**Escalation does not save it** (`escalate()` moves `m`, `n`, `overlap` and the shape at a
fixed 30-atom answer):

| config | CP attack | median nodes | zero-search heuristic |
|---|---|---|---|
| `hard` `m=n=7`, `(5,4,3,2,1)`, overlap 2 | 8/8 | 34 | 6/8 |
| `m=n=8`, `(5,4,3,2,1)`, overlap 3 | 8/8 | 11 | 6/8 |
| `m=n=9`, `(6,5,4,3,2,1)`, overlap 4 | 8/8 | 13 | 6/8 |
| `m=n=5`, `(4,3,2,1)`, overlap 3 (crowded) | 8/8 | 23 | 4/8 |
| `m=n=6`, `(5,4,3,2,1)`, overlap 4 (crowded) | 8/8 | 11 | **8/8** |

There is a **structural squeeze**, not just bad luck with parameters. The only freedom in
the answer is the padding slack `λ'_i − |re_i|` per row. Increase the slack and there are
many valid answers, so propagation finds one immediately. Decrease it and the answer is
literally the multiset union — the zero-search heuristic reads it off. Because `R` and `C`
decouple, there is no regime in between where the search bites.

---

## 3. Valid-answer count and density (these are NOT why it was rejected)

Exact enumeration, all least common standard multiples:

| preset | valid answers | candidates scanned | density |
|---|---|---|---|
| `demo` `m=n=4` | 1, 2, 3, 19 (seeds 0–3) | 24,626 | 4.1e-5 … 7.7e-4 |
| `easy` `m=n=5` | 1, 1, 1, 2 (seeds 0–3) | 6,935,760 | **1.4e-7 … 2.9e-7** |

`search_space` at the shipping preset is 4.75e17 and structure-aware guessing scored
0/200,000. So G4 and the density half of G5 would both have passed comfortably. **The
family dies purely on H.**

---

## 4. A genuine error in the paper, and why it costs the family its cheap certificate

Theorem 7.19's **completeness** argument asserts that every least common standard multiple
of `f` and `g` has *exactly* `P = max_i max(rd_i, cd_i)` columns, and
`get-admissible-shapes` is specified to return only shapes with that many columns
(`applications.tex:289–293`). **This is false.** Minimal counterexample, verified by
exhaustive enumeration over a 3x3 matrix:

```
f = (2 | 1)        the 1x1 minor x_{2,1}
g = (2,3 | 1,2)    the 2x2 minor on rows {2,3}, cols {1,2}
paper's P = 1
columns = 1 :  common multiples = 0   least = 0
columns = 2 :  common multiples = 2   least = 2   e.g. (1,3|1,2) * (2|1)
columns = 3 :  common multiples = 32  least = 0
```

The column-count bound `P` ignores the *shape*-containment constraint
`λ ⊇ shape(f) ∪ shape(g)` (here `(2,1)`, which already needs two columns), so
`get-admissible-shapes` returns the empty set and Algorithm 7.1 returns **no LCMs at all**
for this pair. Separately, the worked example in `applications.tex` lists 12 bitableaux as
`LCM(f,g)`; three of the six listed at shape `(3,3,2)` were checked and `f` lt-divides
**none** of them — the example shows the unfiltered line-9 output and omits the line-10
divisibility filter. The correct count for that example under the algorithm as written is
**3**, all of shape `(3,2,2)`.

Consequence for this project: **there is no cheap certificate of "least".** The retained
module's `verify` therefore enumerates the one-column-smaller divisors of the claimed
answer, which is sound and complete because divisibility in `A_gen^bd` is graded by column
count (if `L' | L` then `L = LT(L'·h)` and `h`'s columns can be adjoined one at a time), but
it is a bounded search rather than a single division. Had H not already killed the family,
this would have been a V caveat worth arguing about.

---

## 5. The hidden-term-order idea — evaluated and rejected, with numbers

The proposal was: hide the term order, give the solver a reduced Gröbner basis, ask for the
weight vector. Two independent reasons it fails.

**(a) It is not this paper's mathematics.** The paper's bideterminant term order is a
*single fixed* order (Definition 7.6 `defn:order-bitab`: size, then reverse-lex on shapes,
then lex on the reading word `θ`). There is no weight-vector family to hide — pseudo-ASL
term orders are not given a Robbiano-style weight characterisation anywhere, and asking for
one is the paper's **Open Question 10.4** (`conclusion.tex:46`). Building a Gröbner-fan
family in the ordinary polynomial ring would be Mora–Robbiano's mathematics, not this
paper's — `reduction_source = external_standard`, which buys no coverage.

**(b) It collapses on the numbers.** Measured on toric ideals (which have rich Gröbner
fans, unlike random dense ideals, which collapsed to `⟨1⟩`), with a from-scratch Buchberger
over Q under weight orders tie-broken by lex, 250 random weight vectors per instance:

| n vars | distinct reduced GBs seen | largest cone fraction | **P(two random weights give the same reduced GB)** |
|---|---|---|---|
| 5 | 4 – 8 | 0.31 – 0.44 | 0.20 – 0.32 |
| 6 | 2 – 14 | 0.21 – 0.52 | 0.11 – 0.50 |
| 7 | 3 | 0.50 | 0.38 |

The valid answers form a full-dimensional **Gröbner cone** (Mora–Robbiano, *The Gröbner fan
of an ideal*, 1988), so the answer set is not a point but a cone, and the measured guess
probability is **0.11 – 0.50** against a G4 threshold of 1e-6 — five to six orders of
magnitude wrong. Worse, the intended attack is exactly the disqualifying shape the contract
names: choose a leading monomial per basis element (the reduced-basis condition prunes this
to a handful of branches; the leading term was already the unique maximum-total-degree
monomial in 229 of 625 basis elements measured, with no branching needed), then recover the
weight vector by **linear programming** on the inequalities `w·LT > w·u`. An LP dual is a
perfectly good witness and a disqualifying family.

**The user's own instinct was right: the order is read off the leading terms, modulo one
LP.** The idea is rejected.

---

## 6. Everything else in the paper, and what produces its certificate

| object | theorem | what produces it |
|---|---|---|
| leading term of a product of standard bideterminants | **Thm 7.12(II)** `thm:leading-bd` | **closed form**: merge columns, sort each row |
| the quotient `g/f` in `A_gen^bd` | **Lem 7.22** `lem:lt-div-bd` | **closed form**: multiset subtraction (I verified the inverse problem collapses to multiset subtraction — the divisor is *unique* and read off in O(size)) |
| universal bd-Gröbner basis of the ideal of `t`-minors | **Thm 7.24** `thm:t-minors-bdgb` | **lookup**: `G_r = {all minors of size ≥ r}`, written down, not searched. The paper calls its own proof "almost-trivial" and "extremely short and elementary" |
| universal bd-GB of the maximal minors | **Cor 7.26** | immediate, `r = n` |
| straightening expansion | **Thm 7.9** + Appendix C | **stated algorithm** (recursive shuffle rewriting, Lemma C.1); conjectured `#P`-hard (Open 10.2) but the certificate is its output |
| Hilbert series / Krull dim of rank-1 matrices | **Lem 9.6 / Cor 9.7** | **closed-form rational function**; `dim = n+m−1` |
| `LI^lt_sm(I)` basis | **Thm 9.5** | **row echelon form** — a linear solve |
| finite / universal pseudo-ASL Gröbner bases | **Thm 4.38, Thm 4.52** | Noetherian existence only — but the object is an unbounded-size basis, not a bounded witness, so it fails V, not H |
| Ann-closure | **Thm 6.9 / Rmk 6.10** | requires an `Is-Ann-Closed` **oracle**; the authors "have been unable to either prove it or find a counterexample" — an open termination gap, not a checkable witness |
| **LCM set** | **Thm 7.19 / Alg 7.1** | the one admitted exponential search — **this is the family above, and it fell** |

Two further framings were designed and discarded before coding, each for a stated reason:

- **"Leading term of a product"** (invert nothing, apply Thm 7.12): compact route is
  literally "sort", so the obvious in-context ansatz *is* the answer.
- **"Find `h` with `LT(f·h) = g`"** (division): collapses to row-wise multiset subtraction
  with a *unique* answer determined in O(size) — Lemma 7.22 is exactly this closed form.
- **"Recover the product of minors from its straightening"**: the answer is unique
  (minors are irreducible, `F[X]` is a UFD), but the domain-standard attack is multivariate
  factorisation, which is polynomial time — and the leading-term shortcut (Thm 7.12(I)
  gives `[sort(R) | sort(C)]`) leaves a residual un-sorting problem with no short route, so
  it is neither Track A nor Track B.

---

## 7. Summary line

Fails **H**, both tracks. Mechanical route **2.24e11**; compact route **35 nodes / ~5e2
operations**, and that compact route **solves 40/40 in context** with a zero-search
fallback at **58%**. Valid answers per instance: **1–19** (density 1.4e-7 at `easy`).
Relevant results: Definition 5.10, Definition 7.6, Theorem 7.12(II), Lemma 7.22,
Theorem 7.19 / Algorithm 7.1, Theorem 7.24, and `conclusion.tex:25`.

---

## 8. Gate results as measured (`selftest_report.json`)

| gate | pass | measured |
|---|---|---|
| G1 planted verifies | **true** | 32/32 across all four presets x 8 seeds; 40/40 at the shipping preset |
| G2 rejects corruption | **true** | 12 mutations all rejected, 6 distinct reasons |
| G3 round trip | **true** | parses out of model-style prose; returns `None` on junk |
| G4 guess resistance | **true** | 0 hits / 30,000 structure-aware trials; space 4.75e17 |
| G5 density + baseline cost | **FALSE** | density 1.4e-7 (exact) is fine — but the strongest attack **solves** it 40/40, median 35 nodes / 0.22 s |
| G6 adversary panel | **FALSE** | 2 of 4 attacks succeed (40/40 and 23/40) |
| G7 scales | **FALSE** | difficulty does not grow: 8/8 solved at every escalated setting, with **fewer** nodes as `m,n` grow (median 13 at `m=n=9` vs 34 at `m=n=7`) |
| G8 canonical_key | **true** | 24/24 distinct, invariant under the f/g swap (the family's only relabelling symmetry) |
| G9 caps | true | answer 87 chars / 30 atoms / ~32 tokens; route ~5e2 operations — all inside the caps, which is precisely the problem |

`all_passed: false`. The oracle loop (STEP 4) was **not** run: no `OPENROUTER_API_KEY`, and
the family is rejected on H before it would have been worth spending oracle calls.
