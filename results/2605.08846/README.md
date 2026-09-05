# Rational-base descent corrections (arXiv:2605.08846)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `finite_discrete` |
| Computational core | `other` (integer floor descent and gcd) |
| Certificate form | `integer_tuple` |
| Intended intuition | `invariant`: the accumulated floor error is geometrically bounded |
| Domain essentiality | `native` |
| Reduction | none |

## What the problem is

This generator is based on Sam Blake, [*Rational Base Descent: A Deterministic Algorithm for Factoring Structured Semiprimes*](https://arxiv.org/abs/2605.08846). A solver receives products of two primes and the paper's exact integer recurrence

`Q_0 = N`, `Q_t = floor(b Q_(t-1) / a)`.

For every product, the solver must choose the unique correction `j` in `{-1, 0}` for which `gcd(Q_s-j, N)` is a nontrivial factor. The 24-row answer is balanced: exactly 12 corrections have each value. Verification repeats the stated floor descent and Euclidean gcd with exact integers, so it accepts any valid correction vector and never consults the planted answer.

Instances are inverse-generated. The prime factors are selected and proved prime before multiplication. The larger factor has the form `k*6^s-1` or `k*6^s+1`; the smaller prime is strictly below `6^s`. The construction therefore satisfies Theorem 1 with `Delta=-1` or `+1`, and its proof gives the requested correction. The generator never factors a completed instance to learn its answer.

## Why Track B, and what is easy

This cannot honestly be Track A. Section 2 gives Rational Base Descent itself, and Section 5 proves a cost of `O((a/(a-b)) log^3 N)` bit operations when the rational base is supplied and bounded away from one. On the shipping instance, the full depth-by-depth gcd-window reference implementation solved 8/8 trials, averaging 3,888 gcd calls, about 75,536 counted exact operations, and 0.0052 seconds. That successful algorithm is reported separately from the failing attacks, as Track B requires.

The compressed route uses the invariant from the proof of Theorem 1. Here `b=1`, so the nested floors collapse to `Q_s=floor(N/6^s)`. Reducing `N` modulo `6^s` leaves either `q` or `6^s-q`; testing those two possibilities recovers the correction. Across 24 rows this is 240 high-level exact operations, within the 300-operation cap, but it still demands exact division and gcd on 200-bit integers without a sandbox or big-integer calculator. The benchmark measures whether a model can recognize and accurately execute that compression, not cryptographic factoring hardness.

Section 4 explains the genuinely hard regime that this family does **not** claim: when `(a,b)` is unknown, naive parameter enumeration is quadratic in its bound. Section 5 estimates roughly `~sqrt(N)` base candidates for a generic balanced RSA semiprime and concludes that the method is no threat to RSA. Conversely, revealing `(a,b)` makes these structured instances mechanically easy, which is precisely why the module declares Track B.

## Worked demo

The `demo` preset at seed 0 renders three rows with `a=6`, `b=1`, and `s=3`:

```text
0: 277451
1: 329057
2: 501680363
```

The answer is `<answer>[0,-1,0]</answer>`. Calling `verify(inst, [0,-1,0])` returns `(True, "ok")`. Swapping the unique `-1` into the first row gives `[-1,0,0]`, and verification returns `(False, "row 0 correction does not expose a factor")`. This smallest preset is genuinely hand-solvable: divide each number by `6^3=216` and check at most two small gcds.

## Difficulty presets

| Preset | `s=n` | Rows | Representative maximum operand bits | Status |
|---|---:|---:|---:|---|
| `demo` | 3 | 3 | hand scale | illustration only |
| `easy` | 18 | 24 | 219 | **shipping; held the oracle pool** |
| `medium` | 24 | 24 | 351 | available, not needed |
| `hard` | 32 | 24 | 461 | available, not needed |

Difficulty grows by widening the operands while the witness remains fixed at 24 entries. Doubling the shipping exponent to 36 still built and verified; `escalate()` continues this width axis and returns `cap_bound` at its stated ceiling rather than mislabelling an answer-cap limit as easiness.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed planted witnesses verified and were JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged answer round-tripped through realistic surrounding prose; garbage returned `None` |
| G4 | pass | 1 hit / 2,000,000 structure-aware balanced guesses; exact density `1/2,704,156 = 3.698e-7` |
| G5 | pass | one exact shipping witness; reference cost 75,626 operations, 3,888 gcds, 0.0055 s on the measured seed |
| G6 | pass | four attacks, 0/8 successes each; reference algorithm 8/8 as expected |
| G7 | pass | `n=36` build and verification succeeded; answer length stayed 24 |
| G8 | pass | 60/60 row-symmetry invariance and carried-answer checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted pool still hardened; 61 characters, 16 estimated tokens, 24 atoms, 240 intended operations |

The four failed attacks were magnitude ranking, a first-half greedy assignment, 256 structure-aware random restarts, and a last-decimal-digit rounding ansatz. Rows and signs are shuffled, and the plus/minus prime constructions use matched smooth forms, so the plant is not deliberately placed or given a separate decoy distribution.

## Bare oracle loop

| Preset | Seed | Oracle | Solved | Recorded reason |
|---|---:|---|---|---|
| `easy` | 2103391489 | GPT-5.6 Terra | no | parsed vector failed at row 2 |
| `easy` | 425465337 | Grok 4.6 | no | parsed vector failed at row 0 |
| `easy` | 261796761 | Claude Sonnet 5 | no | exhausted 32k tokens and emitted no answer |

The script-owned verdict was `hardened` at `easy` with no escalation.

## G9 arms

| Arm | Solved / attempts | Observation |
|---|---:|---|
| bare | 0 / 3 | two invalid vectors; one empty length-limited response |
| structural hint | 0 / 3 | all identified or attempted the invariant but returned invalid vectors |
| placebo hint | 0 / 3 | two invalid vectors; one empty length-limited response |

Hinted minus placebo success rate is `0.0`. The structural hint bought no verified solves, although the responses show that it did communicate the intended invariant; exact arithmetic execution, not recognition alone, remained the bottleneck. The shipping answer has 61 serialized characters, approximately 16 tokens, and 24 atomic elements. The intended compressed route is counted at 240 exact operations.

## Use

From the repository root:

```python
import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "rbd_generator", "results/2605.08846/gen_2605_08846.py"
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
ok, reason = g.verify(inst, candidate)
```

The directory name begins with digits, so the snippet uses the same portable file loader as the repository scripts. To emit dataset records, run:

```bash
bash scripts/emit.sh 2605.08846 20 easy
```

The module is standard-library-only. It attempts the repository `gvlib` import requested by the harness but degrades cleanly because this family needs only exact Python integers.

## Caveats

This family becomes easy immediately when a solver has reliable big-integer division or gcd; the reference implementation takes milliseconds. It is not evidence that these semiprimes resist factoring software, GNFS, ECM, Pollard methods, or the paper's own algorithm, and those general-purpose methods were not benchmarked because the successful paper-specific method already settles that question.

The G4 probability is uniform over balanced binary correction vectors—the complete answer language after enforcing the stated count. It measures blind whole-vector guessing, not an arithmetic-informed prior, partial-label accuracy, or independence between rows. The four attacks require a completely verified vector to count as success; magnitude or digit statistics could still leak partial information even though their tested full-vector forms failed 0/8. Prime factors come from finite cached smooth-form pools for each exponent while smaller factors vary by seed, so this is a very large deterministic instance supply, not a claim of cryptographic distributional indistinguishability.

Canonicalization exactly quotients the explicit row-reordering symmetry and tests reversals, rotations, and their compositions. No other nontrivial instance relabelling is known here because each public row is a scalar integer. Wall times are hardware-dependent, and the operation counter treats each arbitrary-precision remainder as one high-level operation even though Section 5 correctly charges bit complexity.
