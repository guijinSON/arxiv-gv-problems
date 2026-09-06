# REJECTED — arXiv:1607.03315

**C. Herrmann, Y. Tsukamoto, M. Ziegler, "On the consistency problem for modular
lattices and related structures" (math.LO), 12 Jul 2016.**

**Verdict: REJECTED on H, on both tracks.** G and V both pass and were measured;
a working generator was built, and it is retained as `rejected_gen_1607_03315.py`.
The family dies on hardness, and it dies for a reason that is a property of the
paper, not of the construction.

---

## 1. What the paper actually proves

| result | number in the paper | statement |
|---|---|---|
| group consistency unsolvable | **Theorem 3** (`\lab{p0}`) | Adyan (1955), Rabin (1958), Bridson–Wilton (2015) |
| frame coordinatisation | **Lemma 6** (`\lab{fex}`), Section 3 | `G(L,ābar)` is a group under a fixed lattice term `t`; `Γ_ā : GL(a_1) → G(L,ā)` is an isomorphism; fixed-point-freeness ⇔ `a_12 ∩ ⋂ g_i = a_⊥` |
| the reduction | **Lemma 7** (`\lab{5}`), Section 4 | `π ↦ π^#`; part (iv): the resulting sets **are not recursive** |
| main lattice result | **Theorem 8** (`\lab{5c}`), Section 4 | consistency problem **unsolvable** for classes of modular lattices satisfying (I) or (II) |
| 5 variables suffice | **Corollary 9** (`\lab{five}`) | unsolvable already for conjunctions in 5 variables |
| dimension blow-up | **Corollary 10** (`\lab{fast}`) | `ψ_n`, bit length `O(log n)`, satisfiable in `L(V_F)` iff `dim V ≥ 4(n−1)` |
| rings / relation algebras / databases | Theorems 13, 19 | unsolvable, by transfer |

Every hardness statement in the paper is **unsolvability**. There is no
complexity class, no NP-hardness, no parameterised bound — the words "NP",
"polynomial" and "complexity" appear nowhere in a hardness claim (checked by
grep over the LaTeX source).

**The decisive sentence is the paper's own.** Section 4, in the paragraph
between Corollary 9 and Corollary 10, states that for `V = {F^d : d < ℵ₀}`,
if satisfiability of conjunctions of ring equations is decidable for `F`, then
the consistency problem for `L(V)` is solvable **if and only if** there is a
recursive function `δ` bounding the dimension needed by a satisfiable
`ψ` of binary length `n`. **All of the paper's hardness is the unboundedness of
the dimension.** At any fixed `d` the problem is finite-dimensional linear
algebra over `F_q`. Every instance whose witness fits the 256-atom / 2000-char
answer cap has a fixed, small `d`. So the theorem cannot be made to bite inside
the cap — this is a Track A impossibility, not a construction failure.

## 2. The family that was built (so the rejection is measured, not asserted)

Native objects, straight out of Section 3, Lemma 6:

* a von Neumann 4-frame `ā = (a_1..a_4, a_ij)` of `L(F_q^{4d})`, published as ten
  basis matrices in a random `GL(4d,q)`-scrambled basis;
* two published subspaces `C_1 = t(g_1,g_2,ā)`, `C_2 = t(g_2,g_1,ā)`, where `t` is
  the paper's own group-multiplication lattice term;
* the solver must find subspaces `X_1, X_2` satisfying the seven displayed
  lattice equations, including `a_12 ∩ X_1 ∩ X_2 = 0` — Lemma 6(iii)(c)'s
  fixed-point-freeness, which is exactly the paper's non-triviality condition.

**G passes.** Generation is inverse: `f_1, f_2 ∈ GL(d,q)` are sampled first,
`g_i = Γ_ā(f_i)`, the constants are derived. `make_instance` never searches.
The frame axioms of Section 3 and the identity `t(Γ(f),Γ(g)) = Γ(f·g)` were
verified computationally for `(d,q) ∈ {(1,5),(2,5),(2,7),(3,5)}`.

**V passes.** Exact `F_q` RREF, row-space join, Zassenhaus intersection,
canonical-form equality. No floats anywhere.
`verify(inst, inst["answer"])` is True on **24 / 24** (4 presets × 6 seeds).
0 / 7 corruptions accepted, 6 distinct rejection reasons. Round-trip OK.

**Answer cap passes** at every preset:

| preset | d, q | atoms | chars | tokens |
|---|---|---|---|---|
| demo | 1, 5 | 8 | 32 | 9 |
| easy | 2, 5 | 32 | 108 | 28 |
| medium | 2, 11 | 32 | 111 | 28 |
| **hard (shipping)** | **3, 7** | **72** | **232** | **59** |

Exact valid-answer counts: 3 of 16 at demo, 20 of 230,400 at easy (full
enumeration, 72 s). At the shipping preset, exactly **216–342 valid answers**
(measured over 10 seeds) out of `|GL(3,7)|² = 1.141e15` — density **1.9e-13**.
Structure-aware `random_candidate`: **0 hits in 8,000** at shipping.

## 3. H — the two numbers

The domain-standard attack for a system of lattice equations over a subspace
lattice is **coordinatisation** — it is literally Section 3 of this paper —
followed by solving the resulting matrix system. Concretely: equations (1)–(4)
force each `X_i ∈ G(L,ā)`, so reading it through the frame basis gives a matrix
in `GL(d,q)`; `t` is the *opposite* multiplication (paper, proof of Lemma 6(iii)),
so with `u = φ(X_1)`, `v = φ(X_2)`, `M_1 = φ(C_1)`, `M_2 = φ(C_2)`:

```
v u = M_1 ,  u v = M_2   ⟹   v = M_1 u^{-1}  and  M_2 u = u M_1
```

— a homogeneous linear system in the `d²` unknowns `u[i][j]`. Take any invertible
`u` in its null space.

| | measured at the shipping preset (d=3, q=7) |
|---|---|
| **compact route** (the insight the family claims to test) | **8,910 exact F₇ operations**, median over 20 seeds; max 9,435 |
| **mechanical route** (what a solver without the insight runs) | **the same Gaussian elimination** — the propagation step that shrinks the domain *is* the insight |
| domain-standard attack success | **20 / 20 seeds**, median **0.0020 s** |
| constraint propagation + MRV backtracking, measured | solves **demo** (9 nodes, 0.00 s) and **easy** (2,532 nodes, 0.50 s) |
| blind Grassmannian search, projected | `[12 choose 3]_7 = 7.85e22` subspaces; even post-propagation `|GL|²/#sols = 5.28e12` term evaluations at 1,959 evals/s ⇒ **85.6 years** |

**The two numbers are the same number.** The compact route and the mechanical
route are both "row-reduce the published matrices". The 5.28e12 figure is not a
mechanical route anybody would run: it is what you get by *refusing* to do the
Gaussian elimination that both routes begin with.

Three further measurements make this decisive:

1. **The attack cost is independent of the search space.** Along the escalation
   ladder the nominal space grows from `1.14e15` to `1.17e36` — 21 orders of
   magnitude — while the attack cost moves from **8,835 to 9,888 operations**
   (+12 %) and stays at 0.002 s. A family whose best attack does not notice a
   10²¹ growth in its haystack has no hardness to measure.

2. **`escalate()` can move only one axis.** Raising `q` keeps the answer at 72
   atoms; raising `d` is the only other axis and it lengthens the answer
   (`4kd²` atoms). So the required "≥2 parameters at fixed answer length" is
   **not met** — and the one axis that does move buys nothing (point 1).

3. **The compact route is 8.9× over the G9(c) cap.** The 1,000-operation limit
   is exceeded by the *intended* route at the smallest preset where the family
   is not hand-solvable. A solver in context cannot execute 8,910 exact modular
   multiply-adds, and neither can it execute the mechanical route. The family
   would measure arithmetic stamina, which is the exact failure G9 exists to
   catch.

## 4. Why no reparameterisation rescues it

The witness size at which the paper's own hardness would begin to bite is fixed
by Lemma 7(ii): a non-trivial assignment in a finite modular lattice transfers
to `L(V)` with `dim V = 4d`, `d = |G| − 1`. The tamest concrete family the paper
offers is Corollary 10, `ψ_n` from the alternating group `A_n`, `n > 7`:

* `n = 8` ⇒ `dim V = 28`, witness = 5 subspaces of `F^28` of dimension up to 14
  ⇒ up to **1,960 field atoms**, already **7.7× over the 256-atom cap**;
* `n = 9` ⇒ **2,560 atoms**;
* and Corollary 10 requires **characteristic 0**, so the entries are rationals,
  not small integers.

Worse for H: the witness for `ψ_n` is the deleted permutation representation of
`A_n` — an explicit, textbook formula. That is the contract's discriminating
test failing outright: the certificate is the output of a closed-form
construction, so it is a fine *witness* and a disqualifying *family*.

For genuinely undecidable instances (Theorem 3 via Adyan–Rabin) `|G|` is
unbounded and the yes-witness is unbounded with it; the undecidability lives on
the **non-r.e. side** (the no-instances), which by definition has no plantable
finite witness at all.

## 5. What would change this verdict

A theorem — from some other paper — giving NP-hardness or a cryptographic
assumption for solving lattice/matrix equation systems at *fixed* dimension over
a finite field. This paper supplies none, and importing one would make the
family an `external_standard` reduction: not coverage of this paper's
mathematics, and excluded from the native release.

## Files

* `rejected_gen_1607_03315.py` — the retained generator (G and V pass; contract
  API complete: `TRACK`, `PROBLEM_PROFILE`, `NATIVE`, `DIFFICULTY`,
  `make_instance`, `render`, `parse_answer`, `verify`, `random_candidate`,
  `search_space`, `enumerate_all`, `canonical_key`, `escalate`, hints, `NOTES`).
* `attacks.py` — the four attacks, including the domain-standard one.
* `measurements.json` — every number quoted above.
* `paper.tex` — the arXiv LaTeX source the section/theorem numbers refer to.

No oracle loop was run: no `OPENROUTER_API_KEY` in this environment, and none is
needed — the rejection is on a measured attack, not on oracle behaviour.
