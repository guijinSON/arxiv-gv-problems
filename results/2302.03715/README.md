# arXiv:2302.03715 — Waring decompositions of cubic forms of rank n+2

*"Decompositions and Terracini loci of cubic forms of low rank"* —
<https://arxiv.org/abs/2302.03715>

## Profile

| field | value |
|---|---|
| `TRACK` | **B** — an efficient algorithm exists and is named below |
| `native_domain` | algebra |
| `object_regime` | rational_exact |
| `computational_core` | polynomial_identity |
| `certificate_form` | exact_symbolic (a Waring decomposition: r rational scalars + r rational nodes) |
| `intuition_type` | change of variables |
| `domain_essentiality` | **native** (`reduction_kind = none`) |
| ships at | `SHIPPING_DIFFICULTY = "hard"` |

The solver is handed a concise cubic form over **Q** and must return a Waring
decomposition of it; `verify` expands the returned decomposition over **Q** and
compares all C(n+3,3) coefficients. The paper's objects — the form, the linear
forms, the length-(n+2) non-redundant decomposition, its Kruskal rank — are the
objects the solver manipulates and the objects `verify` operates on. Nothing is
compiled to a graph, a finite field, or an integer tuple.

## What the family is

An instance publishes the 35 rational coefficients of a homogeneous cubic

    F = sum_{i=1}^{r} mu_i * L(t_i)^3 ,   L(t) = x0 + t*x1 + t^2*x2 + ... + t^n*xn

in n+1 = 5 variables, with r = n+2 = 6 terms. The answer is the six pairs
(mu_i, t_i) of rationals. Checking is one expansion and 35 exact rational
equalities — cheap, exact, no floats anywhere.

The points [1 : t_i : … : t_i^n] lie on the rational normal curve of degree n,
so any n+1 of them are linearly independent (Vandermonde). That is *not* a
restriction on the geometry: **any** n+2 points of P^n in linearly general
position lie on a rational normal curve, so this is exactly the linearly-general
stratum the paper calls `K_{n+1}` (Lemma 1.7).

Instances are built **answer first**: sample the pairs, expand the cube. The
generator never searches.

## Why the answer is unique — the theorem this family stands on

`Theorem 1.1` of the paper is a trichotomy for concise `F ∈ S^3 V`,
`dim V = n+1`, `R(F) ≤ n+2`:

* **(I)** the non-redundant length-(n+2) decomposition is **unique**, and then
  its Kruskal rank is ≥ 4;
* **(II)** infinitely many, every one of Kruskal rank 2;
* **(III)** infinitely many, every one of Kruskal rank ≤ 3.

Our plant has Kruskal rank n+1 = 5, so (II) and (III) are impossible and the
decomposition is **the only one** — over **C**, hence over **Q**, hence including
decompositions whose linear forms are nowhere near the rational normal curve.
`verify` may therefore accept any witness it is handed: there is only one.

`selftest` checks the hypotheses of the theorem *executably* on every shipped
instance (`uniqueness_certificate`): non-redundancy (all `mu_i ≠ 0` and the
`L_i^3` linearly independent — measured rank 6/6), conciseness (the points span
P^n — measured rank 5/5), and Kruskal rank (all 6 maximal Vandermonde minors
nonzero — 6/6). Result: `theorem_1_1_case_I` on 8/8 shipping instances.

**Measured valid-decomposition count: exactly 1.** Corroborated by brute force,
not only by the theorem: exhaustive enumeration over the *whole* declared node
grid finds exactly one valid decomposition at `demo` (792 subsets) and exactly
one at `easy` (38 760 subsets). At the shipping preset C(84,6) = 4.06e8 subsets
is past the enumeration budget, so the count there rests on Theorem 1.1 plus
0 hits in 200 000 structure-aware samples.

`Corollary 3.4` is the warning label: a concise cubic with two length-(n+2)
decompositions has a **≥ 2-dimensional family** of them. There is no
"slightly ambiguous" regime — a bad plant (Kruskal rank ≤ 3, e.g. four points on
a plane) is infinitely ambiguous. The generator cannot produce one, and the
selftest proves it did not.

## Why it is hard — Track B, honestly

**The algorithm that solves it.** Substituting `x_j -> u^{n-j} v^j` collapses F
to the binary form `sum_i mu_i (u + t_i v)^{3n}` of degree 3n = 12 with the *same*
parameters; equivalently, every published coefficient equals a multinomial
coefficient times the power sum `P_s = sum_i mu_i t_i^s`, with
`s = j1+j2+j3` read off the monomial `x_{j1} x_{j2} x_{j3}`. **Sylvester's
algorithm** then finishes it: kernel of the r×(r+1) Hankel/catalecticant block
built from `P_0 … P_{2r}` → the monic annihilator `prod_i (z − t_i)` → its
rational roots → one partial-fraction solve for `mu`. Complexity `O(r^3)` exact
rational operations. **Measured at the shipping preset: 806 operations (median
over 150 seeds), 1.4 ms.** It solves 8/8, which is why it is reported under
`G6.reference_algorithm` and not inside `attacks`.

**The mechanical route.** Without the collapse, the statement leaves n+2 unknown
points and the honest fallback is to enumerate (n+2)-subsets of the declared node
grid, forcing `mu` by a linear solve on each: C(84,6) = 4.06e8 subsets ×
332.6 operations = **1.35e11 operations, 8.6e4 s extrapolated in CPython
(~1 CPU-day)**. Gap = **1.8e8×**.

Neither number is executable in context. The compact one is — 806 exact rational
operations is a long but finite hand computation — and only if the collapse is
seen. That is the whole of the Track B claim.

**Easy regimes that had to be avoided** (see `NOTES` in the module):

* `n ≤ 2`. Kruskal rank n+1 < 4 makes Theorem 1.1 case (I) unreachable, and
  `Theorem 2.1` / `Theorem 3.5` (Sylvester's pentahedral theorem) describe the
  resulting families of decompositions. `make_instance` refuses `n < 3`.
* Length n+1 instead of n+2. `Lemma 1.9` records that uniqueness there is the
  classical Kruskal statement and the catalecticant recovers the answer directly;
  n+2 is the first length where that stops.
* Small integer nodes. A grid of 20 nodes is enumerable in 55 s. The shipping
  preset uses half-integers with |numerator| ≤ 28: 84 nodes, C(84,6) = 4.06e8.
* A dominant node. `P_{s+1}/P_s → t_max` when one modulus is strictly largest.
  Countered by *crowding*, not by making the plant look different: the sampler
  rejects plants whose largest |t_i| exceeds the second largest by more than
  `RATIO_GAP = 5/4`. Measured leak of the tail-ratio statistic over 200 seeds:
  **49.3% without the constraint, 29.0% with it, against a 7.1% chance
  baseline** (300 seeds) — and it names at most one of six nodes either way,
  with no signal about whether the name is right. Forcing the top two moduli to
  be exactly equal would drop the leak to 5.5%, but it would put a ±t pair in
  every plant and shrink the node-set space 27-fold; making plants structurally
  recognisable to buy a statistic is the wrong trade.

## Worked example (`demo`, seed 2)

4 variables, r = 5, 20 coefficients. The published form begins
`(3 0 0 0) : 7`, `(2 1 0 0) : 18`, `(2 0 1 0) : 96`, … , `(0 0 0 3) : 16841616`
(full text in `demo_example.txt`).

Answer: `-1 -6; -2 -5; 4 -4; 4 -1; 2 5`  →  `verify` returns `(True, 'ok')`.

Corrupt it and the reason is specific:

| corruption | `verify` returns |
|---|---|
| `mu = 2 → 3` on the `t = 5` term | `(False, 'coefficient mismatch at monomial (3, 0, 0, 0): decomposition gives 8, F has 7')` |
| node `−6 → −3` | `(False, 'coefficient mismatch at monomial (2, 1, 0, 0): decomposition gives 9, F has 18')` |
| drop a term | `(False, 'answer has 4 terms, expected exactly 5')` |

Is `demo` solvable by hand? Yes, and that is what it is for: 447 exact rational
operations, ten integers of at most 8 digits in the Hankel block, five integer
roots in `{±1,…,±6}`, and an exhaustive check is only C(12,5) = 792 subsets.
It is an illustration, not a difficulty level.

## Difficulty presets

| preset | n | node grid | search space C(M,6) | answer chars / atoms | route ops (seed 23) |
|---|---|---|---|---|---|
| demo | 3 | 12 (integers, \|t\| ≤ 6) | 792 | 29 / 20 | 443 |
| easy | 4 | 20 (integers, \|t\| ≤ 10) | 3.88e4 | 37 / 24 | 651 |
| medium | 4 | 54 (halves, \|num\| ≤ 18) | 2.58e7 | 49 / 24 | 814 |
| **hard (ships)** | 4 | 84 (halves, \|num\| ≤ 28) | **4.06e8** | 41 / 24 | 772 |

No preset was rejected by a gate. `hard` was chosen as the largest grid whose
reference-route cost stays under the 1000-operation cap for essentially every
seed (150 seeds: min 700, median 806, p95 940, max 1004 — one seed over).

`escalate()` moves **four to five parameters at once** — node numerator bound,
node denominator bound, scalar numerator bound, scalar denominator bound, and
occasionally `n` — and it grows the *haystack*, not the *needle*:

| rung | params | grid | search space | answer chars / atoms | mechanical ops |
|---|---|---|---|---|---|
| 0 (ships) | n=4, t≤28/2, mu≤12/3 | 84 | 4.06e8 | 54 / 24 | 1.35e11 |
| 1 | n=4, t≤56/3, mu≤18/3 | 244 | 2.75e11 | 54 / 24 | 9.15e13 |
| 2 | n=4, t≤89/5, mu≤27/4 | 622 | 7.85e13 | 57 / 24 | 2.61e16 |
| 3 | n=5, t≤142/6, mu≤40/4 | 1080 | 3.33e17 | 77 / 28 | 1.68e20 |
| 4 | n=5, t≤284/7, mu≤60/5 | 2650 | 1.81e20 | 76 / 28 | 9.10e22 |

Twelve orders of magnitude of haystack for 22 extra characters of needle.
`escalate` returns `"cap_bound"`, never `None`, when the answer would finally
exceed 2000 chars / 256 atoms.

## Gate results

| gate | measured |
|---|---|
| G1 planted verifies | **32/32** (4 presets × 8 seeds) |
| G2 rejects corruption | 10 corruptions × 8 seeds all rejected, **12 distinct reasons** |
| G3 round-trip | parses a prose-wrapped reply, rejects junk (`None`) |
| G4 guess resistance | **0 hits / 200 000** structure-aware samples, plus 0/2000 with a full `verify`; analytic P = **2.46e-9** (naive product space would say 1.24e-19 — a ten-order-of-magnitude self-deception, so the structure-aware number is the one reported) |
| G5 density + baseline | valid answers = **1** (exact at demo 1/792 and easy 1/38 760; Theorem 1.1 at shipping). Mechanical **1.35e11 ops / 8.6e4 s**; compact **770 ops / 1.2 ms**; gap **1.76e8** |
| G6 adversary panel | 4 attacks, **0 successes / 8 attempts each**; `reference_algorithm` solves 8/8 at 806 ops |
| G7 scales | escalate moves 3–5 params, escalated instance builds and verifies; doubling n (4 → 8) builds and verifies |
| G8 canonical_key | invariance **120/120** under 5 affine reparametrisations × 24 seeds; the transformed instance verifies against the carried answer **120/120**; **24/24** distinct keys |
| G9 caps | answer **41 chars / 10 tokens / 24 atoms**; intended route **806 ops** (median of 150) |

### The adversary panel in detail

| attack | what it does | result |
|---|---|---|
| `dominant_root_peeling` | estimate `t_max` from the tail ratio, round to the nearest node of bounded denominator, deflate, repeat | 0/8 — crowding kills the convergence |
| `greedy_prefix_peel` | exact rational least squares for `mu` at every grid node, take the smallest residual, subtract, recurse | 0/8 |
| `random_restart_2000` | 2000 random 6-subsets of the grid, `mu` forced by linear solve | 0/8 |
| `first_row_prony_in_context` | the in-context attack: run Prony on the n+1 power sums visible in the `x0^2*xj` row only | 0/8 — needs 2r = 12 power sums, sees 5 |
| `reference_algorithm` *(not an attack)* | Sylvester on the collapsed binary form | **8/8 in 806 ops**, as Track B requires |

`canonical_key` is keyed on the affine normal form of the planted node set (the
two smallest nodes are mapped to 0 and 1, both orientations tried, scalars
normalised by the first) — a genuine invariant, not a hash of the seed or of
`render`. The relabellings tested are real linear changes of coordinates:
`x_j -> sum_k C(k,j) alpha^j beta^{k-j} x_k` sends `L(t)` to `L(alpha*t+beta)`.

## The oracle loop and the G9 arms — NOT RUN

`llm_loop_transcript.jsonl`, `.meta.json`, `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl` are **absent**: this build ran without an
`OPENROUTER_API_KEY`, so STEP 4 was never executed. Nothing in this README
claims an oracle result. `G9.arms` is recorded as 0/0 with an explicit note, and
`hinted_verdict` is `null` rather than `"hardened"`. **The module is not
submittable until STEP 4 is run**; the hardness evidence here is the measured
mechanical/compact gap and the adversary panel, not a model failure.

`STRUCTURAL_HINT` names one invariant and stops:

> "After dividing by its multinomial coefficient, the coefficient of
> `x_{j1} x_{j2} x_{j3}` in F depends on `(j1, j2, j3)` only through
> `j1 + j2 + j3`."

It does not say to substitute `x_j -> u^{n-j} v^j`, does not mention Sylvester or
Prony, does not chain a second step, and does not state a derived quantity.
`PLACEBO_HINT` matches its length and register and carries nothing.

## How to use it

```python
import gen_2302_03715 as gen

inst = gen.make_instance(seed=17, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
print(gen.render(inst))                      # the whole problem statement
ok, why = gen.verify(inst, inst["answer"])   # (True, 'ok')
ans = gen.parse_answer(model_reply)          # tolerant of prose and fences
print(gen.canonical_key(inst))
```

Emit with `scripts/emit.sh 2302.03715` from the repo root. Gates:
`python3 gen_2302_03715.py` prints the full `selftest()` dict (about 90 s; the
exhaustive `easy` enumeration is 55 s of it).

## Caveats — read these

* **The oracle loop was not run.** See above. Every "hard" claim here is a
  measured cost, not a model failure.
* **The reference algorithm is textbook.** Sylvester's algorithm for binary
  forms is in every symmetric-tensor survey, and a model that recognises the
  power-sum structure has a genuinely short road. That is the Track B bargain,
  stated rather than hidden. If the oracle pool solves the shipping preset,
  `escalate()` has five rungs of grid growth left before the answer cap bites —
  but note that the *route* cost also grows (rung 2 ≈ 1091 ops, rung 4 ≈ 2342),
  so an escalated shipping preset would breach the G9(c) 1000-operation cap and
  should be reported as such rather than quietly shipped.
* **The route-op figure is a median.** 1 of 150 shipping seeds costs 1004
  operations, 0.4% over the cap; p95 is 940. The variance comes from how many
  candidate roots survive the rational-root filter. I did not tune the sampler
  to hide the tail.
* **What P(guess) = 2.46e-9 means.** It is the probability that a *structure-aware*
  guess — six distinct nodes drawn from the declared 84-node grid, scalars then
  forced by a linear solve — is right. It assumes the solver has read the bounds
  in the statement. It is not a claim about a solver who has partial information;
  the tail-ratio statistic above names one node about 29% of the time (chance
  7.1%), which on those instances would cut the space to C(83,5) = 3.1e7 and the
  mechanical route to ~1e10 operations. The gap over the compact route is still
  ~1.3e7. This is the largest single weakness I found and it is not hidden.
* **Uniqueness at the shipping preset is a theorem, not an enumeration.** I could
  not enumerate C(84,6) = 4.06e8 subsets in the selftest. The enumerations that
  did run (792 and 38 760 subsets, one valid answer each) test the same claim at
  smaller grids, and the theorem's hypotheses are checked exactly on every
  shipping instance.
* **Attacks I did not run.** No Gröbner-basis attack on the 35-equation
  coefficient-matching system in 12 unknowns (no CAS is importable under the
  stdlib-only rule, and a hand-rolled Buchberger over Q would not finish); no
  Koszul-flattening or vector-bundle method; no LLL attack on the power-sum
  sequence. A lattice attack on `P_s = sum mu_i t_i^s` is the gap I would probe
  first if I had more time — the sequence is short (13 terms) and the heights are
  small, so I would not be surprised if a well-chosen lattice recovered the
  annihilator faster than Sylvester. That would not break the family (it would
  be another efficient algorithm, which Track B already concedes) but it would
  shorten the "compact route" figure further.
* **`canonical_key` is invariant under the affine group only.** The full symmetry
  of the family is PGL(2) acting on the node parameter (the rational normal curve
  is PGL(2)-equivariant), and the inversion `t -> 1/t` composed with
  `x_j -> x_{n-j}` is a relabelling the key does **not** collapse. Two instances
  related by such an inversion get different keys, so the diversity check is
  conservative — it can over-count distinct instances, never under-count.
