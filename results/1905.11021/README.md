# 1905.11021 — a spread plane meeting every codeword of a lifted MRD code

Paper: **A. Cossidente, F. Pavese, "Subspace code constructions"**, arXiv:1905.11021
(math.CO, cs.IT). The paper improves the lower bound on `A_q(9,4;3)` — planes of
PG(8,q) pairwise meeting in at most one point — and in Section 3 builds
`(6,(q^3-1)(q^2+q+1),4;3)_q` orbit codes of planes of PG(5,q).

## Profile

| field | value |
|---|---|
| `TRACK` | **B** |
| native domain | geometry |
| object regime | finite_field |
| computational core | linear_algebra |
| certificate form | exact_symbolic (one element of GF(q³)) |
| intended intuition | change of variables |
| `domain_essentiality` | **native** (`reduction_kind = none`) |

The solver is handed planes of PG(5,q) and `verify` intersects actual subspaces over
GF(q) — no graph, no CSP, no surrogate. Nothing was compiled away.

## What the family is

Let `K = GF(q)` and `L = GF(q³) = K[t]/(t³ − r)`. Inside `V = L × L = K⁶`, whose
3-dimensional K-subspaces are the planes of PG(5,q), put

```
W(b,c) = { (y, b·y + c·y^q) : y ∈ L }        U(a) = { (y, a·y) : y ∈ L }
```

The q⁶ planes `W(b,c)` are the lifting of the Gabidulin MRD code `{b·x + c·x^q}`;
they pairwise meet in at most one point, which is the `A_q(6,4;3) ≥ q^6` bound the
paper's introduction cites from [SKK] and builds on. The `U(a)` are the Desarguesian
spread: q³ pairwise disjoint planes.

**Task.** Given `m` planes `W(b_i,c_i)`, find `a ∈ L` such that `U(a)` meets *every*
one of them in exactly one point — a spread plane that can be adjoined to the given
code with every pairwise intersection a single point.

**Answer.** One element of GF(q³): three integers. **3 atoms, 11 characters** at the
shipping preset, and it stays 3 atoms all the way up the escalation ladder.

**Checking is cheap.** Build the two 3×6 generator matrices over GF(q), stack them,
one Gaussian elimination, `dim(U ∩ W) = 6 − rank`. Exact integer arithmetic mod q
throughout; no floats anywhere.

**Generation plants the answer first.** Sample `a`. Then for each plane sample `c`,
sample `z` *uniformly from the norm fibre* `N⁻¹(N(c))` (by rescaling a random
direction by a cube root — no rejection loop over the whole field), and set
`b = a − z`. `U(a)` then meets `W(b,c)` by construction. `make_instance` never
searches for `a`; the only rejection test is a well-formedness check that the
published planes carry full linear rank, which does not look at `a`.

## Why it is hard — Track B, honestly

The efficient algorithm **exists and is named**:

1. `U(a)` meets `W(b,c)` iff `(a−b)y − c·y^q` has a nonzero root, iff
   `y^{q−1} = (a−b)/c` is solvable, iff **`N(a−b) = N(c)`** (`N` = norm to GF(q)).
2. With `t³ = r` the norm is `N(x) = x₀³ + r x₁³ + r² x₂³ − 3r x₀x₁x₂`, and

   `N(a−b) = N(a) − 3[b₀P(a) + r b₂Q(a) + r b₁R(a)] + 3[P(b)a₀ + rR(b)a₁ + rQ(b)a₂] − N(b)`

   with `P(x)=x₀²−rx₁x₂`, `Q(x)=rx₂²−x₀x₁`, `R(x)=x₁²−x₀x₂` — the coordinates of
   `x^{q+1}`. So every constraint is **K-linear** in `(N(a),P(a),Q(a),R(a),a₀,a₁,a₂)`.
3. Translate so `b₁ = 0`; then `N(a′) = c₁` is known and a 6×6 solve returns `a`.

Measured at the shipping preset (q=1009, m=7):

| route | what it needs | operations | wall clock | result |
|---|---|---|---|---|
| **compact (steps 1–3)** | the norm criterion *and* the linearisation | **343** | 3.0e-4 s | 30/30 |
| norm-fibre decode | step 1 only, then walk the q²+q+1 fibre | 7.24e6 | 2.03 s | solves |
| CP / backtracking, MRV | nothing; cubic in the last coordinate | 4.13e9 | ~168 s | solves |
| exhaustive over GF(q³) | nothing | 1.13e10 (1.03e9 candidates) | ~559 s | solves |

The gap the family tests is **343 versus 1.1e10** — seven orders of magnitude. A
solver who sees the norm criterion but stops there still faces 7.2 million operations;
only the full three-step chain is writable by hand. Nothing in the statement mentions
norms, linearised polynomials, or Gabidulin codes.

**The easy regimes that had to be avoided**, and this is the part only the build knows:

* **m ≤ 3 is free.** `U(a)` meets `W(b_i,c_i)` iff some nonzero `y_i` has
  `y_i·X = y_i·B_i` in the matrix picture. With three planes you may choose the three
  `y_i` to be the standard basis and simply take row *i* of the answer from row *i* of
  `B_i` — zero arithmetic. `m` must exceed 3 by a wide margin; it is 7–8 here.
* **Rank-one perturbations are fatal.** The first design tried (and the one the brief
  proposed) published `B_i = A + R_i` with `rank(R_i) = 1`. Then
  `B_i − B_j = u_i v_iᵀ − u_j v_jᵀ` has column space `⟨u_i,u_1⟩`, so intersecting two
  column spaces returns `⟨u_1⟩`, the row spaces return `⟨v_1⟩`, and `A` follows after
  trying q−1 scalars. **Measured: this recovers a valid witness on 18/20 (q=13),
  20/20 (q=127) and 19/20 (q=307) instances in 684–2149 field operations** — the same
  order as the compact route, so that variant fails H and is rejected. The shipped
  design uses rank-**two** perturbations (forced by the code structure), where
  `rank(A−B_i) = 2` for every *i* and `rank(B_i−B_j) = 3` for 21/21 pairs, and the same
  attack scores **0/12** at every preset.
* **q ≢ 1 (mod 3)** would lose the pure cubic `t³ − r` and with it the cheap norm form;
  q is constrained to primes ≡ 1 (mod 3), q > 3.
* **m < 7** leaves the linearisation underdetermined — deliberately used as the last
  rung of `escalate`, not at the shipping preset.

## Worked example (`demo`, q=13, m=8)

`render` prints the field, the eight planes, and the output contract. Seed 0 gives
planes `b=(12,0,6) c=(5,1,3)`, `b=(4,2,6) c=(7,5,9)`, … and the answer `a = (0,8,8)`.

* `verify(inst, [0,8,8])` → `(True, 'ok')`.
* `verify(inst, [1,8,8])` → `(False, 'plane 1 meets U(a) in dimension 0, not 1')`.

**Can a person do the demo by hand?** Yes. q³ = 2197 is small enough to brute-force,
and the 7×7 linearisation mod 13 is a paper-and-pencil exercise. That is what `demo`
is for; it is not a difficulty rung and never ships.

## Presets

| preset | q | m | search space q³ | exact valid answers (12 seeds) | P(guess) |
|---|---|---|---|---|---|
| demo | 13 | 8 | 2,197 | 1 every time | 4.55e-4 |
| easy | 127 | 8 | 2,048,383 | 1 every time | 4.88e-7 |
| medium | 307 | 8 | 28,934,443 | 1 every time | 3.46e-8 |
| **hard (ships)** | **1009** | **7** | **1,027,243,729** | **1 every time** | **9.73e-10** |

`easy` was measured and kept as a rung, not as a shipping candidate: 200k random
restarts solved it 2/12, because 200k samples cover 10% of a 2.05e6 space. It fails
nothing at `medium` or `hard`.

`escalate` moves **two** parameters — q up and m down to a floor of 6 — and the answer
stays 3 atoms:

| step | q | m | q³ | answer atoms / chars | moved |
|---|---|---|---|---|---|
| 1 | 3,229 | 6 | 3.37e10 | 3 / 12 | q, m |
| 2 | 10,333 | 6 | 1.10e12 | 3 / 14 | q |
| 3 | 33,073 | 6 | 3.62e13 | 3 / 15 | q |
| 4 | 105,871 | 6 | 1.19e15 | 3 / 17 | q |
| 5 | 338,791 | 6 | 3.89e16 | 3 / 19 | q |
| 6 | 1,084,147 | 6 | 1.27e18 | 3 / 20 | q |

Every escalated level was built and verified. `cap_bound` is returned only past
q = 10⁷ — the answer never approaches the size cap, the arithmetic width does.

## Gate results

| gate | measured |
|---|---|
| G1 planted verifies | **80/80** (4 presets × 20 seeds) |
| G2 rejects corruption | 7/7 corruptions rejected, 4 distinct reasons |
| G3 round trip | recovers the answer from model-style prose; `None` on garbage |
| G4 guess resistance | 0 hits / 200,000 structure-aware samples; exact P = **9.73e-10** |
| G5 density + baseline | exactly **1** valid answer at the shipping preset; strongest attack 1.13e10 ops / ~559 s |
| G6 adversary panel | 4 attacks, **0/12 successes each** (see below) |
| G7 scales | builds and verifies for n = 0..4, q = 13 → 193 |
| G8 canonical_key | invariance **96/96**, reality **96/96**, distinctness **40/40** |
| G9(c) answer cap | 3 atoms, 11 chars — passes with room to spare |
| G9(c) route cap | **343 operations — over the 300 cap.** See caveats. |

G6 panel, all at the shipping preset, 12 seeds each:

| attack | successes |
|---|---|
| outlier: every published `b_i`, its negation, the sum, the centroid, reflections | 0/12 |
| greedy hill-climb seeded on the first constraint's norm fibre | 0/12 |
| random restart, 200,000 samples | 0/12 |
| in-context small combinations (±3·b_i, pairwise sums/differences/midpoints, triple sums, coordinatewise median — 176 candidates) | 0/12 |

`reference_algorithm` (Track B, expected to succeed, reported outside `attacks`):
norm criterion + linearisation, O(m + k³), 343 operations, 7.0e-5 s, 30/30.

**Difference-leak test (the thing most likely to kill this family).** Column/row-space
intersection 0/12; pairwise difference-and-sum lattice 0/12; ratio test on differences
0/12 — at easy, medium and hard. The same code recovers the rank-1 variant 57/60.

## G9 arms and the oracle loop

**Not run.** `OPENROUTER_API_KEY` is not set in this environment, so
`scripts/harden.py` could not be invoked and there is **no oracle evidence** for this
family: no `llm_loop_transcript.jsonl`, no bare/hinted/placebo arms, no `hardened`
verdict. Every number above is a static measurement. The hardness claim rests on the
measured 343-vs-1.1e10 gap, not on any model having failed.

`STRUCTURAL_HINT` names the invariant and stops — "Whether U(a) meets W(b,c) depends
on a − b only through its norm to GF(q)." It does not chain a second step and does not
state the linearisation, so it leaves steps 2 and 3 to the solver.

## How to use it

```python
import gen_1905_11021 as G
inst = G.make_instance(seed=7, **G.DIFFICULTY[G.SHIPPING_DIFFICULTY])
print(G.render(inst))
print(G.verify(inst, inst["answer"]))          # (True, 'ok')
print(G.compact_route(inst))                   # ((a0,a1,a2), 343)
```

`make_instance` also accepts `n=` (a q-ladder index) for harness compatibility.

## Caveats — read these

* **The intended route is 343 GF(q) operations, not ≤ 300.** Counting every field
  multiplication, division, addition and subtraction: ~117 to build six rows plus ~221
  for the 6×6 elimination and back substitution. Every module in the corpus keeps this
  at or under 300, and this one does not. It is a 14% overshoot, it is measured rather
  than rounded down, and it is the single reason not to ship this as-is without
  argument. Shrinking it means shrinking the linear system, and 6 unknowns is the
  floor for a cubic norm form over a degree-3 extension.
* **No oracle evidence exists** (see above). "Hard" here means "measured to have a
  seven-order gap", not "four vendors failed it".
* **P(guess) = 9.73e-10 is exact, not sampled** — `enumerate_all` counts every valid
  `a` by walking the first constraint's norm fibre, which provably contains all of
  them. 48 of 48 instances tested had exactly one valid answer, so `verify` accepting
  "any witness" is not a loophole here; there is only one.
* **The compact route occasionally needs a different 6-subset.** At q=13 the chosen
  six planes gave a singular system on 4/30 seeds (0/30 at q ≥ 127); a solver falls
  back to the 7×7 form or another subset. Not a correctness problem, but it means
  "one 6×6 solve" is the typical, not the guaranteed, cost.
* **What I did not try:** a real Gröbner engine (no CAS available — the linearisation
  is the algebraic route and it already succeeds, so a Gröbner run would only confirm
  Track B), and any lattice/LLL attack (there is no integer-relation structure to
  attack — everything lives in GF(q)).
* **What would make this easy:** dropping m below 4 (multiple answers), letting q be
  small enough to brute-force by hand, or presenting the instance already in the
  linearised coordinates. All three are avoided at the shipping preset.
* **Presentation choice worth knowing:** the field is given as `K[t]/(t³−r)` with
  q ≡ 1 (mod 3). That basis is what makes the norm a four-term form and the compact
  route short. With a general irreducible cubic the mathematics is identical but the
  compact route costs roughly three times more arithmetic.
