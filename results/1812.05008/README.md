# `gen_1812_05008` — McNie / Niederreiter syndrome decoding over F_q

Source paper: Jon-Lark Kim, Young-Sik Kim, Lucky Galvez, Myeong Jae Kim, Nari Lee,
**"McNie: A code-based public-key cryptosystem"**, [arXiv:1812.05008](https://arxiv.org/abs/1812.05008) (cs.CR, v2).

## Profile

| field | value |
|---|---|
| `TRACK` | **A** (structural hardness) |
| `native_domain` | algebra |
| `object_regime` | `finite_field` |
| `computational_core` | `linear_algebra` |
| `certificate_form` | `exact_symbolic` (support representation of a vector over F_q) |
| `intuition_type` | duality |
| `domain_essentiality` | `native` — `reduction_kind: none` |
| `SHIPPING_DIFFICULTY` | `hard` |

The solver is handed the paper's own objects: a parity-check matrix over a finite
field, a syndrome, and a weight bound. `verify` operates on exactly those objects
(one exact modular matrix–vector product). Nothing is compiled away.

**One honesty note up front.** The paper's headline instantiation is the *rank*
metric (Sections 2–3.3: LRPC codes, quasi-cyclic blocks, RSD). What ships here is
the **Hamming** metric — that is, the general McNie scheme of Section 3.1 with
m = 1, so F_{q^m} = F_q a prime field. Section 3.1 states the scheme for "a parity
check matrix H ∈ F_{q^m}^{(n-k)×n} of an r-error-correcting code with an efficient
decoding algorithm", and the abstract states that McNie's "security is reduced to
the hard problem of syndrome decoding"; Section 4.2 proves it. So this is a
faithful instantiation of the paper's general scheme and of its security
reduction, but it is *not* coverage of the rank-metric mathematics of Sections
2–3.3. See Caveats.

## What the family is

The solver is given, inline and in full:

* a prime `q`, lengths `n`, `k`, and `u = n − k`;
* a parity-check matrix `H = [ I_u | A ]` over F_q, with `A` printed row by row;
* a syndrome vector `s ∈ F_q^u`;
* a weight bound `w`.

and must return a vector `e ∈ F_q^n` with `H eᵀ = s` and Hamming weight ≤ `w`.
The answer is reported as the **support** of `e`: at most `w` pairs `index:value`.

**Why generation is honest (G).** The certificate is sampled *first*: a uniform
weight-`w` support with uniform nonzero values. `A` is then sampled independently
and uniformly, and the published syndrome is *derived*, `s = H eᵀ`. `make_instance`
performs no search of any kind — the whole build is `u·k` random draws plus
`w·u = 714` modular multiply-adds at the shipping preset. Plants and "decoys" are
drawn from literally the same distribution: every column of `A` is i.i.d. uniform,
so there is no per-column statistic that distinguishes a support position.

**Why checking is cheap and exact (V).** Verification recomputes the syndrome
sparsely from the reported support — `w·u = 714` integer multiply-adds mod `q` —
and compares. Pure integer arithmetic; no floats anywhere.

**Uniqueness.** With `w` below the unique-decoding radius the answer is unique, and
the module computes the exact expected number of *other* weight-≤`w` vectors with
the same syndrome, `(Σ_{j≤w} C(n,j)(q−1)^j − 1)/q^u`:

| preset | E[spurious solutions] | measured |
|---|---|---|
| demo | 2^−3.32 = 0.100 | 40 seeds brute-forced: 36 unique, 4 with two solutions → **0.100 observed** |
| easy | 2^−8.41 | enumeration out of budget |
| medium | 2^−32.48 | enumeration out of budget |
| **hard (ships)** | **2^−42.81** | enumeration out of budget |

The demo row is the calibration: predicted 0.100 extra solutions, observed 0.100.
That is direct empirical support for the 2^−42.81 figure at the shipping preset, so
the planted `e` is the unique valid answer except with probability ≈ 2^−43.
`verify` nevertheless accepts *any* valid witness and never reads `inst["answer"]`.

## Why it is hard (Track A)

**The theorem.** Syndrome decoding of a random linear code (equivalently, Coset
Weights) is NP-complete — Berlekamp, McEliece, van Tilborg, *IEEE Trans. IT* 1978.
McNie's own security reduction, **Section 4.2** of the paper, proves that attacking
the ciphertext `c1 = mG′ + e` *is* an instance of this problem with parameters
`(n, l, r)`. **Section 4.3.1** names the domain-standard attack in as many words:
"Combinatorial attacks … apply the Information Set Decoding".

**The parameter regime.** Worst-case NP-hardness is not the claim; the claim is
about the shipped *distribution*. The shipped distribution is the standard hard one
for code-based cryptography: uniform `H`, uniform weight-`w` error, with `w`
strictly below the unique-decoding radius of a random `[210,168]` code over F_31.
Below that radius the problem is a genuine search with a unique target and no
known sub-exponential algorithm.

**The easy regimes that had to be avoided**, and where the paper identifies them:

* **Any algebraic structure in `H`.** Goppa, GRS/Reed–Solomon, Gabidulin and LRPC
  parity-check matrices all fall to structural attacks — the paper catalogues
  Overbeck, Lau–Tan and Hauteville–Tillich in **Sections 4.3.3–4.3.5**. `H` here is
  uniformly random with no hidden structure and **no trapdoor is published at all**,
  which is the only regime where ISD is the best known attack.
* **Publishing the second ciphertext half `c2 = mF`.** **Remark 2** and
  **Section 4.3.2 (Gaborit's attack)** show that `c2` yields `n−k` linear equations
  on the message and collapses the effective dimension from `l` to `l−(n−k)`. The
  `c2` half is therefore deliberately *not* part of the instance.
* **`w` above the unique-decoding radius**, which would make the answer non-unique
  and the search easy. `w` is held below it and the margin is computed exactly.

### Measured attack costs at the shipping preset (`q=31, n=210, k=168, w=17`)

| attack | cost | result |
|---|---|---|
| **Prange ISD** (domain standard) | **1.705 × 10^13 expected iterations = 2^43.95**; measured **216.5 iter/s** (4.62 ms/iter) → **projected 7.88 × 10^10 s ≈ 2,495 CPU-years** in this pure-Python implementation; **≈ 2^58.55 F_31 operations** | **0 / 8 seeds**, 60 s each and 160 s total in the gate run |
| **Lee–Brickell ISD, p = 1** | iteration gain **110.85×** over Prange → **1.538 × 10^11 = 2^37.16 iterations**, but 21.6× more work per iteration → **2^56.19 field ops**, a net **5.14×** speedup over Prange | **0 / 8 seeds** |
| **Brute force over supports** (information-set patterns) | **1.067 × 10^48 = 2^159.55 candidates** (2^165.27 over the naive full weight-`w` sphere); measured 106,463 candidates/s → **3.18 × 10^35 years** | **0 / 8 seeds** |
| **Gaussian elimination baseline** (solve `H eᵀ = s`, ignore the weight bound) | instant (< 10^−4 s); the systematic form returns `e = (s \| 0)` | returns weight **36–42** against the bound **17** — **0 / 8 seeds** |
| outlier column-correlation ranking | 0.21 s / 8 seeds | 0 / 8 |
| greedy syndrome peeling | 2.98 s / 8 seeds | 0 / 8 |
| random restart ×256 with exact restricted solve | 2.52 s / 8 seeds | 0 / 8 |

**The ISD implementations are validated, not asserted.** Both are run to *success*
on the presets where that is feasible, and the measured iteration counts match the
combinatorial predictions:

| preset | Prange solved | mean iterations | predicted `C(n,w)/C(u,w)` | LB p=1 solved | mean iterations | predicted gain |
|---|---|---|---|---|---|---|
| demo | 10/10 | 3.1 | 4.5 | 10/10 | 1.8 | 3.5× |
| easy | 10/10 | 12,425 | 10,003 | 10/10 | 331 | 28.0× |

So the 2^43.95 figure at the shipping preset is an extrapolation of a formula that
has been checked against measurement at two smaller sizes, not a paper estimate.

**Mechanical cost vs compact route.** The generator-verifier gap here is the
cryptographic one:

| | operations |
|---|---|
| build the instance from the secret | `u·k + w·u` = **7,770** |
| **verify a proposed answer** | `w·u` = **714** modular multiply-adds |
| **find an answer without the secret** | **2^43.95 Prange iterations ≈ 2^58.55 field operations** |

That is a gap of roughly 2^48 between checking and finding. **No compact *solving*
route is claimed or known** — that is what Track A means here, and it is stated
plainly rather than dressed up as an insight the solver is supposed to find.

## Worked example (`demo` preset, `q=7, n=10, k=5, w=2`)

```
A =                              s = 1 6 6 6 5
4 2 1 5 3
3 3 0 3 3                        find e in F_7^10 with H e^T = s
6 6 2 0 3                        and Hamming weight at most 2
5 0 2 2 3
4 4 5 2 6
```

* planted answer: `[[0, 2], [9, 2]]`, i.e. `e_0 = 2`, `e_9 = 2` — check row 0:
  `e_0 + A[0][4]·e_9 = 2 + 3·2 = 8 ≡ 1 = s_0 (mod 7)`.
* `verify(inst, [[0,2],[9,2]])` → `(True, 'ok')`
* `verify(inst, [[0,3],[9,2]])` → `(False, 'syndrome mismatch in row 0')`
* `verify(inst, [[0,1],[1,1],[2,1]])` → `(False, 'support size 3 exceeds the weight bound 2')`
* `verify(inst, [[99,1]])` → `(False, 'index 99 out of range 0..9')`
* `enumerate_all(inst)` → `1` (this seed's answer is exactly unique)

**Can a person do the demo by hand?** Yes, with patience. The systematic block makes
`e_L = s − A e_Rᵀ` forced, so the search is only over `e_R`: 1 + 5·6 + C(5,2)·36 = 391
candidates, each a 5-vector subtraction mod 7. Twenty minutes with a pen, less if you
notice that `j = 0` means checking whether `s` itself has weight ≤ 2. The `easy`
preset (10^4 Prange iterations) is already past hand scale, which is the point of the
ladder.

## Difficulty presets

| preset | q | n | k | u | w | Prange iterations | E[spurious] | answer atoms | statement chars |
|---|---|---|---|---|---|---|---|---|---|
| `demo` | 7 | 10 | 5 | 5 | 2 | 2^2.17 | 2^−3.32 | 4 | 1,686 |
| `easy` | 13 | 60 | 45 | 15 | 6 | 2^13.29 | 2^−8.41 | 12 | 3,207 |
| `medium` | 31 | 150 | 120 | 30 | 12 | 2^30.89 | 2^−32.48 | 24 | 11,375 |
| **`hard` (ships)** | **31** | **210** | **168** | **42** | **17** | **2^43.95** | **2^−42.81** | **34** | **20,678** |

No preset was rejected by a gate; the ladder is monotone in Prange cost by
construction (`ladder_monotone: true`).

### `escalate()` — grow the haystack, not the needle

Two dials move together and `w` never does: **`n` doubles** with `u = n−k` held
fixed (so the rate rises and `C(n,w)/C(u,w)` grows by ≈ 2^w), and **`q` jumps to the
next prime above `4q`** (so every answer value carries 2 more bits, the certificate
language grows by 4^w, and the uniqueness margin widens). The answer stays **34
atoms forever**:

| step | q | n | k | w | Prange | search space | answer atoms | answer chars |
|---|---|---|---|---|---|---|---|---|
| `hard` | 31 | 210 | 168 | 17 | 2^43.95 | 2^165.3 | 34 | 124 |
| escalate ×1 | 127 | 420 | 378 | 17 | **2^61.44** | 2^217.9 | **34** | 137 |
| escalate ×2 | 509 | 840 | 798 | 17 | **2^78.68** | 2^269.4 | **34** | 142 |
| escalate ×3 | 2039 | 1680 | 1638 | 17 | **2^95.80** | 2^320.6 | **34** | 165 |

Every escalated preset was built and its planted answer verified. `escalate` returns
`"cap_bound"` only if the uniqueness margin would fall below 2^20, which does not
happen on this chain.

## Gate results

| gate | result |
|---|---|
| **G1 planted verifies** | **24/24** in `selftest` (4 presets × 6 seeds), **32/32** in `measure_attacks.py` (4 presets × 8 seeds) and **32/32** on a further 4 × 8 fresh seeds — **88/88 total, every preset** |
| **G2 rejects corruption** | 0 of 28 corruptions accepted; 12 distinct reasons (drop / value-perturb / index-move / duplicate / out-of-range / zero-value / empty) |
| **G3 round-trip** | prose ✓, garbage → `None` ✓, JSON form ✓, fenced form ✓, `(i, v)` bracket form ✓ |
| **G4 guess resistance** | **0 hits / 200,000** structure-aware samples; language size 5.62 × 10^49 = **2^165.27**; sharper information-set space 2^159.55 |
| **G5 density + baseline** | density 0/200,000 sampled; exact count 1 at `demo`; baseline = Prange at the shipping preset, **6,048 iterations in 25.0 s, 0 solved**, projected 2,234 CPU-years |
| **G6 adversary panel** | **7 attacks, 0/8 successes each**, including the mandatory domain attack (Prange ISD) and Lee–Brickell |
| **G7 scales** | ladder monotone (2^2.17 → 2^13.29 → 2^30.89 → 2^43.95); escalated preset builds, verifies, is harder (2^61.44), answer length unchanged (34 = 34) |
| **G8 canonical key** | invariance **80/80** under `H → UH, s → Us`, information-coordinate relabelling, and both composed in both orders; "transformation is real" **80/80**; **20/20 distinct keys** |
| **G9(c) caps** | answer **120 chars / 34 atoms / ≈30 tokens** (worst case over 60 fresh seeds: 126 chars) — cap is 2,000 chars / 256 atoms |
| **G9(a) three arms** | **not run** — no `OPENROUTER_API_KEY` in this environment |

`all_gates_pass: true`, `selftest` elapsed 374 s.

## The oracle loop

**Not run.** `scripts/harden.py` requires `OPENROUTER_API_KEY`, which is not present
in this environment, so there is no `llm_loop_transcript.jsonl` and no `hardened` /
`too_easy` verdict from the four-vendor pool. The hardness evidence in this README is
entirely the measured-attack evidence above; the no-tool-oracle evidence is missing
and should be collected before this family is counted as oracle-hardened. Likewise
the G9 bare/hinted/placebo arms carry no numbers.

## How to use it

```python
import gen_1812_05008 as G

inst = G.make_instance(seed=42, **G.DIFFICULTY[G.SHIPPING_DIFFICULTY])
print(G.render(inst))                     # the full statement, no answer leaked
print(G.verify(inst, inst["answer"]))     # (True, 'ok')
print(G.parse_answer("<answer>3:17, 45:2</answer>"))
```

Note the signature is `make_instance(n=None, seed=0, **params)`; presets are passed
as keyword arguments, as above. Emit with `scripts/emit.sh 1812.05008` from the repo
root.

Reproduce every number here:

```bash
python3 gen_1812_05008.py          # runs selftest(), ~6 minutes
python3 measure_attacks.py         # ISD / brute-force / escalation, ~9 minutes
```

`gvlib` is imported defensively but not needed: everything is exact integer
arithmetic modulo a prime, so the module is standard-library-only.

## Caveats

1. **The metric is Hamming, not rank.** This is the paper's *general* scheme
   (Section 3.1) and its *security reduction* (Section 4.2), not its rank-metric
   instantiation. A reader looking for LRPC codes, Gaussian binomials, or the
   `(n−k)³m³q^{r⌈(k+1)m/n⌉−m}` rank-ISD complexity of Section 4.3.1 will not find
   them here. Building the rank-metric version would need a rank-ISD implementation
   (support enumeration over subspaces of F_{q^m}) and a different answer encoding;
   it is a separate family, not a parameter change.
2. **The failure is not informative in the G9 sense, and I will not pretend
   otherwise.** There is no insight route. A model that fails this problem has
   demonstrated that it cannot perform 2^58 field operations in context, which we
   already knew. `STRUCTURAL_HINT` names the one real observation available (the
   identity block forces `e_L` from `e_R`), and that observation shrinks the search
   from 2^165.3 to 2^159.6 — real, and nowhere near enough. If the corpus wants
   families whose difficulty is an insight rather than raw intractability, this is
   not one, and the `hinted − placebo` difference (unmeasured here) would very
   likely be zero.
3. **The statement is large: 20,678 characters (≈ 5,200 tokens) at the shipping
   preset**, almost all of it the 7,056 entries of `A`. That is intrinsic — a
   *random* parity-check matrix has no shorter description, and giving it a shorter
   one (a circulant/quasi-cyclic form as in the paper's Sections 3.2–3.3, or a
   generating rule) would either open the folding and DOOM attacks the paper
   discusses in Section 4.3.5 or introduce algebraic structure that breaks the
   hardness claim. Escalation makes this worse: 51k chars at ×1, 308k at ×3.
4. **The work factor is 2^44 iterations / 2^58.5 field operations, which is not a
   cryptographic security level.** It is chosen so `make_instance` stays at 8 ms
   while the attack stays out of reach in context. A determined attacker with
   optimised C and the Stern/Dumer/BJMM improvements would plausibly reach the
   shipping preset in weeks of CPU time; `escalate()` ×1 (2^61.44) removes that
   possibility at the cost of a 51k-char statement.
5. **Attacks I did *not* run.** Stern's algorithm, Dumer, MMT/BJMM and the
   Both–May "nearest-neighbour" ISD variants — the modern refinements of
   Lee–Brickell. Their asymptotic gain over Prange for these parameters is a small
   number of bits (typically 2^5–2^10 for rate-4/5 codes at this length), so the
   conclusion is unaffected, but I measured Prange and Lee–Brickell only and the
   others are estimates from the literature, not measurements. I also did not run a
   Gröbner-basis / algebraic attack (Section 4.3.1's second bullet); over a prime
   field with a Hamming-weight constraint it is not competitive with ISD, but that
   too is a literature claim rather than something I measured.
6. **What `P(guess) = 0/200,000` does and does not mean.** `random_candidate` samples
   uniformly from the declared certificate language — a weight-`w` support with
   nonzero values — which is what a solver reading the statement can enforce for
   free. It does *not* model a solver who exploits the systematic block; the sharper
   information-set space (2^159.55) is reported alongside it. Neither number is
   reachable by sampling, so both are safe, but the honest difficulty signal is the
   ISD cost, not the cardinality.
7. **`canonical_key` does not quotient out code equivalence.** It is invariant under
   change of parity-check basis and under relabelling of the information
   coordinates (80/80 verified), but not under column permutations that mix the
   parity block with the information block — deciding *that* is the code equivalence
   problem, which is exactly the kind of thing this family is built on. Two
   instances related by such a permutation would receive different keys. This is
   documented rather than hidden.
8. **`demo` is not guaranteed unique** (E[spurious] = 0.10; 4 of 40 seeds have two
   solutions). It is an illustration, not a shipping rung, and `verify` accepts
   either solution. All non-demo presets have margins of 2^−8.4 or better and the
   shipping preset 2^−42.8.
