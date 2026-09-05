# arXiv:2209.04762 — inverting a permutation trinomial over F_{2^m}

Paper: Danyao Wu, Pingzhi Yuan, Cunsheng Ding, Yuzhen Ma,
*"Permutation trinomials over F_{2^m}: a corrected version"*,
<https://arxiv.org/abs/2209.04762> (math.CO, math.NT; Finite Fields Appl. 46 (2017)).

Module: `gen_2209_04762.py` — standard library only.

## Profile

| field | value |
|---|---|
| `TRACK` | **B** (no-tool compression; an efficient algorithm exists and is named below) |
| native domain | algebra |
| object regime | `finite_field` |
| computational core | `polynomial_identity` |
| certificate form | `integer_tuple` (a candidate index plus three field elements) |
| intended intuition | **change of variables** — substitute `y = x^(2^k)` and use `y^(2^(k-1)) = x` |
| `domain_essentiality` | `native` (`reduction_kind = none`) |
| shipping preset | `hard` (m = 35) |

The solver is handed the paper's own objects: an explicit finite field `F_{2^m}`,
trinomials over it, and field elements. `verify` operates on exactly those
objects. Nothing is reduced to a graph or a CSP.

## What the family is

An instance fixes `F_{2^m}` by an irreducible polynomial over `F_2` (elements are
integers, addition is XOR, multiplication is carry-less multiplication mod that
polynomial), lists `D` trinomials

```
T_j(x) = c1*x^d1 + c2*x^d2 + c3*x^d3        over F_{2^m}
```

exactly one of which is a **permutation polynomial** of the field, and gives `L`
target elements `c1, ..., cL`. The solver must name the permuting index `j*` and
give the (unique) preimages `x_i` with `T_{j*}(x_i) = c_i`.

Checking an answer is `L` polynomial evaluations — three modular exponentiations
each, exact integer bit arithmetic, no approximation anywhere. Building an
answer, without the structure, is a search of `F_{2^m}`.

**Construction (G).** Answer-first, never by solving.
Proposition 2.6 of the paper states that for odd `m` and `k = (m+1)/2`,
`f(x) = x + x^(2^k-1) + x^(2^k+1)` permutes `F_{2^m}`. Definition 2.2 and
Section 5 give its quasi-multiplicative orbit. The generator

1. samples a QM twist `(a, b, d)` with `gcd(d, 2^m-1) = 1` and forms the planted
   trinomial `a * f(b * x^d)`, whose three terms are
   `(d*t mod 2^m-1, a*b^t)` for `t in {1, 2^k-1, 2^k+1}`;
2. samples the preimages `x_1, ..., x_L` uniformly **first**;
3. sets the targets to `c_i = T(x_i)`;
4. adds decoys `a' * f(b' * x^e)` with `gcd(e, 2^m-1) = g > 1`. Such a map has
   image of size `(2^m-1)/g + 1`, so it is provably **not** a permutation; the
   generator additionally checks in closed form that at least one target lies
   outside each decoy's image, so no decoy index can ever produce a full valid
   answer and the answer is unique.

## Why it is hard (Track B — the honest version)

**The algorithm that solves it.** The proof of Proposition 2.6 (equations
(2-1)–(2-7) of Section 2) substitutes `y = x^(2^k)`, uses
`y^(2^(k-1)) = x^(2^(2k-1)) = x^(2^m) = x`, eliminates `y` linearly and lands on

```
(1 + c^2 + c^(2^k)) * x = c * c^(2^k),      i.e.   f^{-1}(c) = c^(2^k+1) / (1 + c^2 + c^(2^k)).
```

Undoing the twist gives `x = ( f^{-1}(c/a) / b )^(d^{-1} mod 2^m-1)`, where `d`
is read off the smallest exponent, `b` from the coefficient ratio
`c3/c1 = b^(2^k)` and `a` from `c1 = a*b`. Complexity: `O(m)` field operations
per target. **This is expected to succeed and it does, 8/8 at the shipping
preset** — it is the `hardness_basis`, not a gate failure, and it is reported
under `reference_algorithm`, not under `attacks`.

**The two numbers.**

| route | measured cost at the shipping preset (m = 35, D = 17) |
|---|---|
| **mechanical** — exhaustive preimage search | `2^35 = 3.44e10` trinomial evaluations for the one gcd-screened candidate (`5.84e11` if every candidate is swept), i.e. `5.36e12` field multiplications. Measured evaluation rate here: `8.9e2`–`1.5e3` evals/s ⇒ **`3.8e7 s` ≈ 445 days** for the screened candidate, `6.5e8 s` for the full sweep |
| mechanical — root-finding on `T(x) - c` | worse. Exponents are reduced mod `2^35-1`, so the measured `deg(T)` at the shipping preset is `3.36e10`; a Cantor–Zassenhaus / Rabin root find needs `m = 35` squarings modulo a polynomial of that degree |
| **compact** — the substitution above | **246–273 field operations** (mean **265** over 8 seeds), wall clock `6e-3`–`8e-3 s` |

Ratio ≈ **`1.3e8`**. That gap is the family. `ROUTE.md` writes the compact
route out step by step with the operation count of each step.

Note the identification subtask separately: *testing* all 17 candidates for the
permutation property by brute force costs `5.84e11` evaluations, while
Definition 2.2 turns it into **17 gcd computations**. That is a second, smaller
instance of the same generator-verifier gap, and it is why the decoy count is a
crowding dial rather than a hardness dial (see Caveats).

The compact route is not something a
model executes without seeing the structure, because the trinomial is presented
after a random QM twist: the exponent triple is **not** the paper's displayed
`(1, 2^k-1, 2^k+1)`, and the ratios `d2/d1`, `d3/d1 mod 2^m-1` have to be formed
before the family is recognisable at all.

**The easy regimes that were avoided.**
* `m` even. Proposition 2.6 needs `2k-1 = m`. For even `m` the same trinomial is
  badly non-injective — measured image sizes 35/64, 136/256, 527/1024, 2080/4096
  at `m = 6, 8, 10, 12`. Only odd `m` is generated.
* Small fields. At `m <= 20` a program tabulates the field outright; `demo`
  (m = 9) is deliberately in that regime and `easy` (m = 15) nearly so. The
  shipping preset is `m = 35`.
* Mersenne-prime exponents (`m = 13, 17, 19, 31, 61, ...`). With `2^m - 1` prime
  there is no proper subgroup of `F_{2^m}^*`, so no non-permutation decoy of the
  same shape exists. `_M_LADDER` excludes them.
* The paper's displayed form. Without the QM twist the trinomial is recognisable
  by eye (and its smallest exponent is literally 1). `medium` and `hard` twist.

## Worked example (the `demo` preset, m = 9, seed 3)

```
P(x) = x^9 + x + 1        (integer encoding 515),  F_{2^9}, 511 nonzero elements

  j = 0 : (1, 1), (31, 1), (33, 1)
  j = 1 : (28, 1), (343, 1), (413, 1)
  j = 2 : (133, 1), (224, 1), (301, 1)

  c1 = 457      c2 = 136
```

Answer: `[0, 315, 284]`. `verify` returns `(True, 'ok')`.
Corrupting one preimage by a single bit gives
`(False, 'T_0(x1) = 175, but c1 = 457')`.

Here `k = 5`, the exponents of `j = 0` are `1, 2^5-1, 2^5+1`, and
`gcd(28, 511) = 7`, `gcd(133, 511) = 7` identify the two decoys immediately.
`enumerate_all` confirms **exactly one** valid answer — and returns 1 on
8/8 `demo` seeds and 8/8 `easy` seeds, which is the empirical check that the
decoy construction really does make the answer unique.

Can a person do this by hand? The screening step and the substitution, yes.
The `F_{2^9}` arithmetic — `c^32`, one inversion, one multiplication per target —
is about 40 carry-less multiplications of 9-bit words; tedious but finishable on
paper. That is what `demo` is for. `easy` and above are not hand-scale, because
each field operation is a 15- to 35-bit carry-less multiply.

## Presets

| preset | m | targets `L` | decoys | twist | answer atoms | route ops |
|---|---|---|---|---|---|---|
| `demo` | 9 | 2 | 2 | none (`a=b=1, d=1`) | 3 | 40 |
| `easy` | 15 | 3 | 4 | coefficients only | 4 | 66 |
| `medium` | 23 | 3 | 8 | full (`a, b, d` random) | 4 | 159 |
| **`hard` (ships)** | **35** | **3** | **16** | **full** | **4** | **246** |

`escalate` moves three dials and **none of them lengthens the answer**:
`twist_level` (0/1 → 2, with `n_decoys` doubled), `m` (up `_M_LADDER`:
35 → 37 → 39 → …), and `n_decoys` (+8, capped at 64). `n_targets` is
deliberately frozen — that is the needle. Concretely:

| called on | returns | dials moved |
|---|---|---|
| `easy` (`m=15, tw=1, dec=4`) | `{m: 15, n_targets: 3, n_decoys: 8, twist_level: 2}` | `twist_level`, `n_decoys` |
| **`hard`** (`m=35, tw=2, dec=16`) | `{m: 37, n_targets: 3, n_decoys: 24, twist_level: 2}` | **`m`, `n_decoys`** |
| `m = 79` (ladder end) | `"cap_bound"` | — |

The escalated instance builds and passes G1, and its reference route still costs
260 operations (answer still 4 atoms). `"cap_bound"` is returned only when
`_M_LADDER` is exhausted; nothing here escalates by making the answer longer.

## Gate results

| gate | result |
|---|---|
| G1 planted verifies | **120/120** (4 presets × 30 seeds); 24/24 inside `selftest` (4 presets × 6 seeds) |
| G2 rejects corruption | 7/7 corruptions rejected, **7 distinct reasons** |
| G3 round-trip | recovers the answer from prose + fences; tolerates `j* = 3, x1 = …` labelling; returns `None` on garbage |
| G4 guess resistance | 0 hits / 200,000 (easy) and 0 / 25,000 (shipping); search space `6.90e32` (110 bits), analytic `P = 1.45e-33` |
| G5 density + baseline | exact solution count = **1** on 8/8 `demo` seeds **and** 8/8 `easy` seeds (`enumerate_all`); strongest failing attack = exhaustive preimage search, `5.84e11` evaluations needed, measured `1.07e3` evals/s ⇒ `5.5e8 s` projected |
| G6 adversary panel | 5 attacks, **0 successes / 8 attempts each** |
| G7 scales | escalated instance (m = 37, 24 decoys) builds and passes G1 |
| G8 canonical key | invariance 60/60 under candidate reorder × target reorder × Frobenius; 20/20 distinct keys |
| G9(c) caps | answer **40 chars / 10 tokens / 4 atoms**; intended route **246 operations** — all inside the caps (2000 / 256 / 300) |

## Attacks run

All five are run over 8 independent shipping-preset seeds.

| attack | what it does | successes |
|---|---|---|
| `outlier_candidate_statistics` | pick the candidate that is extremal under six per-candidate statistics (min/max/sum of exponents, coefficient popcount, min/max coefficient) and try four cheap guesses for the preimages | 0/8 |
| `greedy_hamming_bitflip` | screen candidates by `gcd(d1, 2^m-1)`, then hill-climb each preimage by single-bit flips minimising `popcount(T(x) XOR c)`, 8 restarts × 60 steps | 0/8 |
| `random_restart_5k` | 5,000 shape-correct random candidates per seed, biased to the gcd-screened index | 0/8 |
| `algebraic_linearised_solve` | the obvious ansatz: pretend `T` is `F_2`-linear, build its matrix on the basis and solve the linear system | 0/8 |
| `exhaustive_preimage_capped_2e4` | the domain-mechanical route, capped at 20,000 evaluations per instance | 0/8 |

Reported separately, **expected to succeed**, per the Track B rule:

| reference algorithm | result |
|---|---|
| closed-form inverse of Proposition 2.6 after undoing the QM twist | **8/8**, 265 field ops mean, 0.052 s for 8 instances |
| blind exponent-space sweep (does not know `k = (m+1)/2`; sweeps `k'` over `[1, m]`) | **8/8**, 109–158 shape tests, `1.4e-2 s` |

The blind sweep is the "exhaustive search over exponent space" and the
"classification lookup" attack in one: it shows that a solver who suspects the
family but not the parameter still wins in `O(D·m)` shape tests. That is the
Track B claim, stated openly.

## The G9 three-arm diagnostic and the LLM hardening loop

**Not run.** `scripts/harden.py` needs `OPENROUTER_API_KEY`, which is not present
in this environment. There is therefore **no** `llm_loop_transcript.jsonl`, no
`g9_hinted_transcript.jsonl` and no `g9_placebo_transcript.jsonl`, and the
bare/hinted/placebo arms are recorded as `null` in `selftest_report.json`. The
hardness claim in this README rests on the measured attack numbers above and on
the mechanical-vs-compact gap, **not** on an oracle pool. `STRUCTURAL_HINT` and
`PLACEBO_HINT` are written and exported; the module honours `GV_HINT_MODE`.

## How to use it

```python
import gen_2209_04762 as g

inst = g.make_instance(seed=42, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
print(g.render(inst))                  # the statement, no answer leaked
print(g.verify(inst, inst["answer"]))  # (True, 'ok')
print(g.parse_answer("<answer>6, 17286398602, 22763963541, 33428376098</answer>"))
```

`python3 gen_2209_04762.py` prints the full gate report.
In the repo: `scripts/emit.sh 2209.04762`.

## Caveats

* **The candidate-screening subtask is cheap and I am not claiming otherwise.**
  Because `gcd(2^k-1, 2^m-1) = gcd(2^k+1, 2^m-1) = 1`, every exponent of a
  candidate has the same gcd with `2^m-1` as its twist exponent, so one gcd per
  candidate separates the permutation from the decoys. `n_decoys` therefore buys
  crowding and forces the solver to apply Definition 2.2 — it does **not** buy
  exponential hardness. The hardness lives in `m` and in the twist.
* **At `demo` and `easy` the planted trinomial has smallest exponent 1**, because
  `twist_level < 2` means `d = 1` while decoys need `gcd(e, 2^m-1) > 1`. Those
  rungs identify the plant by inspection. Only `medium` and `hard` hide it.
* **`P(guess)` prior.** `random_candidate` already applies everything the
  statement gives away — a legal index and `L` distinct nonzero field elements.
  It does *not* model a solver who has narrowed the index to one candidate; with
  the index known, `P` is still `(2^m-1)^{-L} ≈ 2.5e-32`. The number says
  guessing is hopeless; it says nothing about the difficulty of the inversion.
* **Attacks not tried.** No Gröbner-basis run (no CAS is available here, and the
  system is a single univariate equation of degree `~2^m` — Gröbner degenerates
  to root-finding, whose cost is argued above rather than measured). No lattice
  reduction (there is no small-coefficient integer relation to find). No
  index-calculus / discrete-log attack on `F_{2^35}`: a discrete log there is
  genuinely feasible, and a solver who computed one *could* convert the equation
  into an exponential equation in `Z/(2^m-1)` — but that equation
  `c1*g^(d1 i) + c2*g^(d2 i) + c3*g^(d3 i) = c` has no known solution method
  short of enumerating `i`, so this is not a route I expect to work. I did not
  implement it, and I flag it as the largest untested attack surface.
* **Root-finding cost is argued, not measured.** I did not implement
  Cantor–Zassenhaus over a degree-`3.4e10` modulus; the claim that it is worse
  than brute force follows from the degree, which *is* measured
  (`max_trinomial_degree_at_shipping = 3.36e10` in `measure.json`).
* **No oracle evidence.** See the G9 section: the LLM hardening loop was not run.
  A family that passes every static gate and defeats five programmatic attacks
  has still not been shown to defeat a model, and this one has not been.
* **What makes it easy:** publishing the paper's displayed form without the
  twist, using even `m`, using `m <= 20`, or telling the solver `k`. All four
  are avoided at the shipping preset (which does not state k anywhere). If a future evaluator's model has
  memorised Proposition 2.6, the family collapses to arithmetic — the honest
  prediction is that the difficulty is *finding* the substitution, which is
  exactly what `intuition_type = "change of variables"` claims.
