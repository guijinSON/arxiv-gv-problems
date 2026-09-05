# Verified moment subset sums for arXiv:2401.06964

> Status: the generator and every local gate pass, but this result is **not yet
> shippable**.  The required bare, structural-hint, and placebo oracle runs made
> no scored attempt because OpenRouter returned HTTP 403 `Key limit exceeded
> (total limit)` across OpenAI, Anthropic, Google, and xAI.  The harness-written
> error
> transcripts are retained; they are not hardness evidence.

| Profile field | Value |
|---|---|
| Track | **B** — an efficient algorithm exists and is disclosed |
| Native domain | `number_theory` |
| Object regime | `finite_field` |
| Computational core | `subset_sum` |
| Certificate | `integer_tuple`, the paper's native subset |
| Intuition | invariant: centered second/third moments reveal translated multiplicative-subgroup orbits |
| Domain essentiality | `native`; no reduction |

## Problem and trust model

The source is Gottig, Pérez, and Privitelli, [*An approach to the moments
subset sum problem through systems of diagonal equations over finite
fields*](https://arxiv.org/abs/2401.06964).  Given a prime field, a cardinality
`k`, and target power sums `b_1,...,b_k`, the solver must return `k` distinct
field elements whose moments equal those targets.  `verify` checks size,
range, distinctness, and every congruence directly, without reading the planted
answer.  Since `k<p`, Newton identities determine one monic root polynomial;
there is exactly one valid subset.

Generation is inverse, not search.  It first selects a union of translated
multiplicative subgroups, then evaluates that subset's moments.  For a subgroup
`H` of order `h`, `sum(x^r for x in H)=0` when `h` does not divide `r`; these
identities compose to certify the construction.

## Why this is Track B

Section 1 of the paper says that Lai--Marino--Robinson--Wan [25] give a
deterministic polynomial-time algorithm for fixed `m`, for monomial/Dickson
image sets, when `k<3m+1`.  Here `D=F_p` is the image of `f(x)=x` and `k=m`, so
the family deliberately lies in that easy regime.  The module's independent
reference algorithm applies Newton identities and evaluates the resulting
degree-`k` polynomial on all `p` residues: `O(k^2+p*k)`, 590,496 counted field
operations and 0.139 seconds mean in the final G6 audit on the provisional
shipping preset.

The compact route is different.  If `c=b_1/k`, centered moments have
`t_2=C_2 a^2` and `t_3=C_3 a^3`; their ratio reveals `a`.  Repeated
multiplication by the supplied primitive root then generates the subgroup
cosets in at most 146 exact field operations.  Without recognizing this
decomposition, a no-tool solver faces hundreds of thousands of modular
operations.  Theorems 4.6, 4.7, and 4.10 cover existence when the number of
moments is much smaller relative to `k`; this generator does not misuse those
results as a hardness theorem.

## Worked demo

For `make_instance(n=97, template="demo", seed=3)`, the complete rendered data
are:

```text
Moment subset sum over a prime field

Let F_p be the field of residues modulo the prime p=97.  Every field
element is written as its unique integer representative in 0,...,96.
The nonzero field elements are generated multiplicatively by g=5.

Find a subset S of F_p containing exactly k=12 DISTINCT elements such that

    sum(a^i for a in S) = b_i (mod p)

for every exponent i listed below.  Exponentiation and addition are in F_p.
The subset is unordered: any ordering of its elements is accepted.  Repeated
elements are forbidden, and every submitted integer must lie in the inclusive
range 0 through 96.

Moment targets:
  i=1: b_i=69
  i=2: b_i=95
  i=3: b_i=73
  i=4: b_i=68
  i=5: b_i=78
  i=6: b_i=65
  i=7: b_i=86
  i=8: b_i=68
  i=9: b_i=21
  i=10: b_i=94
  i=11: b_i=16
  i=12: b_i=78

Give your final answer inside <answer></answer> tags, as exactly 12
comma-separated base-10 integers.  Do not use ellipses.
Example format: <answer>0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11</answer>
Output nothing else inside the tags.
```

Here `c=69/12=30 (mod 97)`, the centered moments are `t_2=62` and
`t_3=2`, and the scale is `a=25`.  The order-8 subgroup is
`[1,64,22,50,96,33,75,47]`; the order-4 subgroup is
`[1,22,96,75]`.  Translating them by `c+a` and `c-2a` gives

```text
<answer>2, 5, 8, 22, 33, 54, 55, 56, 76, 77, 78, 88</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the last
entry returns `(False, "expected exactly 12 elements")`.  A person can solve
and check this demo on paper using the displayed centered-moment calculation;
blind Newton reconstruction is intentionally not the hand route.

## Difficulty presets

| Preset | Lower bound `n` | Chosen `p` | Orbit template | `k` | Reference operations |
|---|---:|---:|---|---:|---:|
| demo | 97 | 97 | 2 cosets (orders 8,4) | 12 | 2,496 |
| easy — provisional ship | 12,289 | 12,289 | 2 cosets (orders 16,8) | 24 | 590,496 |
| medium | 65,537 | 65,537 | 3 order-8 cosets | 24 | 3,146,400 |
| hard | 786,433 | 786,433 | 6 order-4 cosets | 24 | 37,749,408 |

The ladder enlarges the field and interleaves more cosets without lengthening
the 24-element answer.  No preset has been rejected; the oracle could not score
even `easy` because of the external account limit.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses, JSON round-trips, and deterministic rebuilds |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose/fence round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 uniform distinct `k`-subsets already satisfying `b_1`; exact probability about `5.54e-71` |
| G5 | pass | unique answer; reference solver 8/8, 590,496 operations, 0.082 s mean (0.119 s max) |
| G6 | pass | four attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | pass | doubled `n` selects `p=65,537`; answer remains 24 atoms |
| G8 | pass | 120/120 affine/equation-order/answer-order checks, carried witnesses 120/120, distinct keys 20/20 |
| G9(c) | pass | 124 chars, 31 estimated tokens, 24 atoms, 146 intended operations for the measured seed |

## Oracle loop and G9 arms

The bare harness was attempted twice.  The retained latest transcript contains
four harness retries at `easy`; all are `solved="error"`, not model failures.

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 714948800 | OpenAI GPT-5.6 Terra | error | OpenRouter HTTP 403 total key limit |
| easy | 1417058147 | Gemini 3.1 Pro Preview | error | OpenRouter HTTP 403 total key limit |
| easy | 1288400847 | Gemini 3.1 Pro Preview | error | OpenRouter HTTP 403 total key limit |
| easy | 377801317 | OpenAI GPT-5.6 Terra | error | OpenRouter HTTP 403 total key limit |

| Arm | Scored solved/attempts | Harness retries | Result |
|---|---:|---:|---|
| bare | 0/0 | 4 | blocked: OpenRouter HTTP 403 total key limit |
| structural hint | 0/0 | 4 | blocked: same external limit |
| placebo hint | 0/0 | 4 | blocked: same external limit |

Thus `hinted - placebo` is undefined, and no conclusion about the usefulness
of the invariant hint is possible.  Once the key limit is repaired, rerun all
three arms in separate directories and replace these transcripts and the
`G9_RESULTS` values.  The answer cap itself is comfortably satisfied.

## Use

From the repository root:

```python
import importlib.util

path = "results/2401.06964/gen_2401_06964.py"
spec = importlib.util.spec_from_file_location("moment_gen", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
inst = mod.make_instance(seed=7, **mod.DIFFICULTY["easy"])
question = mod.render(inst)
assert mod.verify(inst, inst["answer"]) == (True, "ok")
```

After a successful oracle run, emit with:

```bash
bash scripts/emit.sh 2401.06964 20
```

The module adds the repository root to `sys.path` and attempts the requested
`gvlib` imports, but this finite-field family remains standard-library-only if
those helpers are unavailable.

## Caveats

This is a structured Track-B distribution, not evidence that random or general
moment subset sum is hard.  Its guessing prior is uniform over distinct
`k`-subsets already conditioned on the freely enforced first moment; it does
not model a solver that notices subgroup
orbits, which is precisely the intended shortcut.  Publishing a primitive root
may make subgroup recognition easier.  The panel tested magnitude/mean,
one-moment greedy, random restart, and a ratio-aware additive ansatz; it did not
test LLL, Gröbner-basis software, SAT/SMT encodings, or every possible sparse
polynomial-factor ansatz.  The successful Newton/root scan is fully disclosed.
Most importantly, the four-vendor no-tool hardness claim remains unverified
until OpenRouter can produce scored attempts.
