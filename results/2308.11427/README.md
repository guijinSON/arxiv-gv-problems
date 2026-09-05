# arXiv 2308.11427 problem generator

> Status: **hardened** at the `hard` preset. Easy and medium were solved 3/3;
> hard held 0/3. All local gates pass, and both G9 diagnostic arms are recorded.

| profile field | value |
|---|---|
| track | B — no-tool compression |
| native domain | algebra |
| object regime | finite field |
| computational core | polynomial identity |
| certificate form | polynomial |
| native objects | a permutation-idempotent map, its YB algebra over `GF(p)`, a factored noncommutative polynomial, and its PBW normal form |
| intuition | invariant: balance on the 2-cycles of the displayed permutation |
| domain essentiality | native; no reduction |

## The problem and why the construction is sound

The source is Gateva-Ivanova and Majid, [*Quadratic algebras associated to
permutation idempotent solutions of the YBE*](https://arxiv.org/abs/2308.11427).
Definition 2.6 fixes the Yang–Baxter algebra, Proposition 3.1 gives
`r_f(x,y)=(f(y),y)`, Theorem 3.4 gives the reduced relations
`x_i x_j = x_1 x_j`, and Corollary 3.6 proves that every degree-`d` word has
unique normal form `x_1^(d-1) x_j`, determined by its final generator. The
module randomly relabels the distinguished `x_1` but otherwise works directly
with these native objects.

An instance is a sum of three products of dense linear factors followed by a
two-term terminal factor. If a dense row has coefficient sum `s`, Corollary 3.6
makes it contribute only the scalar `s`. Thus a branch normalizes by multiplying
all its dense row sums into its terminal coefficients.

Generation knows those sums without solving. It samples a fixed-point-free
involution `f`; in branch `b` it samples a center `c_b`, and independently fills
every row so that coefficients at `i` and `f[i]` add to `2*c_b`. Every row then
has certified sum `n*c_b`. The six answer coefficients are composed directly
from `(n*c_b)^(degree-1)` and the three terminal pairs. Verification performs the
ordinary exact PBW scan and never reads `inst["answer"]`.

## Why Track B, not Track A

There is an efficient algorithm and the family says so. Theorem 3.4 and
Corollary 3.6 reduce a displayed instance to summing every dense row and
multiplying the sums. This takes
`O(branches * factors * n)` exact field operations. At the configured hard
preset the reference scan uses exactly **36,771 operations per instance**, solves
8/8, and took **0.019093 s total** (**0.002387 s mean**) in the recorded run.
Consequently, a Track A claim would be false.

The prior-triage idea—recover or merely check `r_f`—was discarded as an easy
regime: Proposition 3.1 writes `r_f(x,y)=(f(y),y)`, so `f` is read directly from
any row of the map table and the identities are checked by routine substitution.
The factored PBW task keeps the paper's algebraic objects while creating the
measured mechanical-versus-structural gap.

The compact route is to notice that `f` consists of 2-cycles and that each
branch is balanced on them. One paired coefficient sum gives `2*c_b`, so the
whole row sum is `(n/2)*(2*c_b)`. Three binary powers and six terminal scalings
finish the answer in at most **51 exact operations**. The task tests discovery of
that invariant; the reference scan is easy for software but far too long to
execute unaided in context.

The first implementation used literal permutations of one repeated coefficient
row. The bare hardening loop solved easy, medium, and hard 9/9. That construction
was abandoned: adding more repeated rows enlarged only redundant text, not the
real difficulty. The current version uses independently sampled, marginally
uniform rows and retains only the subtler `f`-cycle invariant. On the final run,
easy and medium were still solved, but the hard preset held all three bare calls.

## Worked demo

This is `make_instance(seed=0, **DIFFICULTY["demo"])` in full:

```text
PBW normal form in a permutation-idempotent Yang--Baxter algebra

Work over the prime field GF(11); reduce every coefficient modulo 11.
The displayed list f is a permutation: f[i]=j means f(x_i)=x_j.
It defines the permutation-idempotent Yang--Baxter map
r_f(x_i,x_j)=(x_k,x_j), where k=f[j].
f: [6,3,4,1,2,7,0,5]
Let A be the associative noncommutative algebra on generators x_0,...,x_7
with relations x_i x_j = x_6 x_j for every 0 <= i,j < 8.
Use a generator order with the distinguished x_6 first; thus the degree-4
PBW basis is x_6^3 x_j (0 <= j < 8).
A coefficient row [c_0,...,c_(n-1)] denotes the linear form sum_i c_i x_i.
Multiplication is in the printed left-to-right order; the three branch products are added.
All indices are 0-based, all intervals are inclusive, and repeated generators in a linear form are combined modulo p.

The polynomial F is the sum of these three products.  Each D-row is one dense linear factor; T is the final sparse factor.
BRANCH 0
D0: [4,1,1,9,9,8,6,2]
D1: [4,9,8,1,2,2,6,8]
D2: [5,1,0,9,10,9,5,1]
T: [(8,x_0),(9,x_7)]
BRANCH 1
D0: [9,6,10,9,5,10,6,5]
D1: [7,3,7,1,8,5,8,10]
D2: [0,8,0,7,4,8,4,7]
T: [(9,x_1),(1,x_5)]
BRANCH 2
D0: [3,7,8,6,5,4,10,9]
D1: [9,1,10,1,3,8,4,5]
D2: [8,3,0,10,2,10,5,3]
T: [(8,x_2),(2,x_4)]

Find the unique PBW normal form F = sum_j a_j x_6^3 x_j.
The three terminal supports are [[0,7],[1,5],[2,4]]; they are disjoint.
The answer is guaranteed to have exactly two nonzero terms on each terminal support.
Within each support, its two coefficients must be one common nonzero GF(p) scalar multiple of the displayed T coefficients.
That common scalar has the form s^3 for some nonzero s in GF(p).

Give your final answer inside <answer></answer> tags as compact JSON
[[coefficient,generator],...] with exactly six terms, ordered by strictly increasing generator.
Use canonical coefficients 1,...,10; do not include zero terms.
Example of the syntax: <answer>[[1,0],[2,1],[3,2],[4,3],[5,4],[6,5]]</answer>
Output nothing else inside the tags.
```

The answer is `[[5,0],[3,1],[4,2],[1,4],[4,5],[7,7]]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; changing the first
coefficient to 6 returns `(False, "coefficient mismatch at generator 0")`.
A person can solve this demo on paper: the 2-cycles are visible in `f`, one pair
per branch determines the row sum, and only three small cubes remain.

## Difficulty presets

| preset | `n` | factors/branch | field | dense coefficients | structured answer space |
|---|---:|---:|---:|---:|---:|
| demo | 8 | 4 | GF(11) | 72 | 1,000 |
| easy | 24 | 16 | GF(101) | 1,080 | 8,000 |
| medium | 64 | 48 | GF(503) | 9,024 | 126,506,008 |
| hard (**ships**) | 128 | 96 | GF(1009) | 36,480 | 1,024,192,512 |

`escalate()` first doubles the ambient dimension to 256, leaving the six-term
answer fixed, and only then increases the factor haystack. Escalation was not
needed because the named `hard` rung held.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted and JSON checks; independent demo expansion; 64/64 idempotence and 512/512 YBE checks |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | fenced/prose answer round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structured guesses; exact density `1/1008^3 = 9.7637894e-10` |
| G5 | pass | reference scan 8/8; 36,771 ops/instance; 0.019093 s total; demo exact valid count 1 |
| G6 | pass | seven attacks below all 0/8; reference algorithm intentionally 8/8 |
| G7 | pass | `n=256` builds/verifies; dense data doubles; answer remains six terms |
| G8 | pass | 80 invariance plus 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | maximum 67 chars, about 17 tokens, 12 atoms; intended route 51 operations |

The failing attacks are `outlier_modal_coefficient`,
`ignore_f_pairing_center_guess`, `adjacent_pairing_guess`,
`greedy_leading_product`, `copy_terminal_factors`,
`single_shared_scalar_ansatz`, and `random_restart_256`.

## Oracle loop and G9 arms

The script’s configured pool for this run contained two models and sampled one
of them twice per rung. The easy and medium answers verified; all hard answers
failed, producing the recorded `hardened` verdict at `hard`.

| preset | seed | model | solved | reason |
|---|---:|---|---:|---|
| easy | 305181769 | Gemini 3.8 Flash | yes | verified |
| easy | 1238998354 | GPT-5.6 Terra | yes | verified |
| easy | 1317180039 | Gemini 3.8 Flash | yes | verified |
| medium | 1930478913 | GPT-5.6 Terra | yes | verified |
| medium | 1883573819 | Gemini 3.8 Flash | yes | verified |
| medium | 635855619 | GPT-5.6 Terra | yes | verified |
| hard | 1118607241 | GPT-5.6 Terra | no | coefficient mismatch at generator 91 |
| hard | 2074615564 | Gemini 3.8 Flash | no | length-limited empty response |
| hard | 2133545134 | Gemini 3.8 Flash | no | coefficient mismatch at generator 107 |

| G9 arm | solved/valid attempts | transcript result |
|---|---:|---|
| bare | 0/3 | shipping level held |
| structural hint | 3/3 | all answers verified |
| placebo hint | 2/3 | two answers verified |

`hinted - placebo = 1/3`. Naming the cycle-balance invariant made the family
easy, consistent with a recognition task, but the placebo also produced a large
2/3 lift over bare. With only three calls per arm, prompt leakage or sampling
variance cannot be separated cleanly from structural help. The measured maximum
answer is 67 characters, about 17 tokens and 12 atoms; the intended route takes
at most 51 exact field operations.

## Use

```python
import json
import gen_2308_11427 as g

inst = g.make_instance(seed=17, **g.DIFFICULTY["hard"])
statement = g.render(inst)
candidate = g.parse_answer(
    "work... <answer>" + json.dumps(inst["answer"]) + "</answer> done"
)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit with:

```bash
bash scripts/emit.sh 2308.11427
```

## Caveats

- This is not a complexity-theoretic claim. Exact software solves it in
  milliseconds; Track B concerns discovering compression without tools.
- The 0/200,000 estimate samples the strongest freely deducible output prior:
  three independent nonzero power-image scalars, with support and proportionality
  already enforced. It measures guessing, not resistance to algebraic analysis.
- A script that tests sums along `f`-cycles exposes the invariant immediately.
  That is the intended tool-assisted route, not an omitted hardness claim.
- The hard renderer is about 146,000 characters. A bare Gemini call exhausted
  its 32,000-token completion budget without emitting an answer, so one of the
  three hard failures may reflect attention or reasoning budget rather than a
  mathematical error. A larger-budget rerun would strengthen the evidence.
- The G9 sample is small and the placebo solved 2/3; the observed difference
  does not cleanly identify the `invariant` hint as the sole causal factor.
- The canonical key preserves every row’s multiset of coefficient pairs along
  `f`-cycles, terminal coefficients, and pivot/support incidence. It is invariant
  under all tested semantic symmetries and separates 20/20 seeds, but may
  over-collapse adversarial nongenerator inputs with identical invariants.
- No external CAS or general Gröbner-basis package was run. Both should succeed;
  the exact PBW scan is the relevant standard algorithm and already solves 8/8.
- `gvlib` is imported when available but is not needed; the module remains
  standard-library-only if it is absent.
