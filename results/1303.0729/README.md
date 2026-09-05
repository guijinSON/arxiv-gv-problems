# Valued cyclic normal-form certificates (arXiv:1303.0729)

> **Status: `cap_bound` — parked, not shipped and not rejected.** Every local
> G1–G9(c) gate passes at the last writable preset, but the oracle pool solved
> that preset 3/3. The harness then reached the answer/route cap and explicitly
> returned `cap_bound`; this module must not be emitted as a hardened corpus row.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `algebra` |
| Object regime | `rational_exact` |
| Computational core | `polynomial_identity` |
| Certificate form | `rational` |
| Native objects | homogeneous linear polynomials over Q with the 2-adic valuation; rational weights; a strong zero-remainder certificate |
| Intended intuition | `invariant`: valuation-leading variables orient one multiplicative cycle, whose scaled rows telescope |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and trust model

The source is Chan and Maclagan, [*Gröbner bases over fields with
valuations*](https://arxiv.org/abs/1303.0729). Section 2 defines the valued
initial term and the polynomial order. Example 2.2 shows that naive reduction
by `x-2y, y-2z, z-2x` loops forever; Algorithm 2.4 repairs it with a terminating
strong normal form. An instance here gives a shuffled, scaled, longer cycle of
homogeneous linear forms over Q, an exact rational weight vector, and a target
variable. The answer is a rational vector `h` proving
`target = sum(h_i*g_i)` while satisfying Algorithm 2.4's leading-cost
inequalities.

Generation samples a bounded ±1 exponent walk with total one, odd row scales,
and a variable cycle before assembling or shuffling any polynomial. If the
prefix height before edge `i` is `H_i`, its carried multiplier is
`-2^H_i/q_i`; summing the scaled relations telescopes because the product of
the edge ratios is 2. This is composition of identities, not a solve of the
emitted system. `verify` recomputes the rational identity coefficient by
coefficient and recomputes every 2-adic leading cost. It never reads
`inst["answer"]`.

## Why Track B, and why it is parked

An efficient algorithm is explicit and is not being hidden. Algorithm 2.4 is
the valued normal-form route, Algorithm 2.9 is Buchberger's algorithm in this
setting, and Section 4's Algorithm 4.2 constructs the relevant homogeneous
coefficient matrix and inverts a full-rank submatrix. Dense exact Gaussian
elimination therefore solves these degree-one instances in `O(n^3)`: over
eight final-preset seeds it solved 8/8, averaging **794,968.25 counted exact
operations and 0.2318 s**, with maxima 795,148 and 0.2496 s.

The compact route recognizes the directed valuation cycle, accumulates its
powers of two, and normalizes by the closing product. The conservative bound is
**293 exact operations** at `n=73`. This is a genuine mechanical/compact gap,
but it is not a successful hardness claim: both vendors repeatedly found the
compact route. The final bare ladder solved all nine calls, including 3/3 at
`n=73`. Raising `n` further would exceed the 300-operation intended-route cap;
the harness accordingly returned `cap_bound`, not `hardened` or `too_easy`.

The paper's important easy regimes are thus directly respected: homogeneous
linear ideal membership is exact linear algebra, and recognizing the cycle
reduces it further to linear-time propagation. The family is useful and
verified, but this no-tool format cannot make it hard without turning the
witness into a transcription task.

## Worked demo

For `make_instance(seed=0, n=5, max_height=2, scale_bound=9)`, the complete
rendered problem is:

```text
Find a strong zero-remainder certificate over a valued field.

Work in Q[x0,...,x4].  For a nonzero rational c, v2(c) is the
exponent of 2 in its numerator minus the exponent of 2 in its denominator.
The weight of xj is wj.  The leading cost of a nonzero linear form
sum c_j*xj is min_j(v2(c_j)+w_j); a term attaining that minimum is
a leading term (lexicographic order x0>x1>... breaks a tie).
For a nonzero constant h, the leading cost of h*g is v2(h) plus
the leading cost of g.

The exact rational weights, in variable order x0,x1,..., are:
  0/1, -8/5, -2/5, -6/5, -4/5

The target is f = x0.  The following n=5 homogeneous generators are
indexed from 0.  Beside each row, q_i is the positive odd part common
to its two rational coefficients after powers of 2 are removed.
  0: g_0 = 3/1*x2 - 6/1*x3    (q_0=3)
  1: g_1 = -5/2*x0 + 5/1*x3    (q_1=5)
  2: g_2 = 9/1*x1 - 9/2*x2    (q_2=9)
  3: g_3 = 9/1*x0 - 18/1*x4    (q_3=9)
  4: g_4 = -6/1*x1 + 3/1*x4    (q_4=3)

Return rational constants h_0,...,h_4 satisfying both conditions:
  (1) f = sum_i h_i*g_i as an exact polynomial identity over Q;
  (2) every h_i*g_i has leading cost at least the leading cost of f.
The zero coefficient is not allowed.  For row i, h_i must be one of
  -1/q_i, -2/q_i, ..., -2^2/q_i,
reduced to lowest terms.  There is exactly one valid vector in this
bounded language.

Give your final answer inside <answer></answer> tags as JSON with exactly
5 entries [i,"num/den"], one for every i=0,...,4 in increasing order.
Rational strings use a positive denominator, including /1 for integers.
Example shape: <answer>[[0,"-1/3"],[1,"-2/5"],...,[4,"-1/7"]]</answer>
Output nothing else inside the tags.
```

The answer is
`<answer>[[0,"-2/3"],[1,"-4/5"],[2,"-4/9"],[3,"-1/9"],[4,"-2/3"]]</answer>`.
It gives `verify(inst, inst["answer"]) == (True, "ok")`. Replacing the first
coefficient by `-1/3` gives `(False, "row 0 violates the leading-cost
inequality")`. A person can solve this five-row demo on paper by orienting and
following the cycle.

## Difficulty and gates

| Preset | `n` | Max height | Odd-scale bound | Candidate space | Outcome |
|---|---:|---:|---:|---:|---|
| demo | 5 | 2 | 9 | 243 | hand-scale; not in oracle ladder |
| easy | 63 | 8 | 127 | `9^63` | solved 3/3 |
| medium | 69 | 8 | 127 | `9^69` | solved 3/3 |
| hard | 73 | 8 | 127 | `9^73` | last writable; solved 3/3; **cap-bound** |

`SHIPPING_DIFFICULTY` names `hard` only because it is the preset used for all
final local measurements; the harness did **not** authorize it for shipping.

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 16/16 preset/seed planted witnesses verify and JSON round-trip |
| G2 | pass | empty, drop, swap, duplicate-index, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged rational JSON recovered from surrounding prose/Markdown; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact space `9^73`; proved probability `2.1893e-70` |
| G5 | pass | demo exactly 1/243; last writable preset has one proved answer; Gaussian baseline 0.2318 s mean |
| G6 | pass | five attacks each 0/8; Track-B reference elimination 8/8 as expected |
| G7 | pass | `n=147` builds, verifies, and has larger space |
| G8 | pass | 20/20 relabelling invariance, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 1,023 chars, 256 estimated tokens, 219 atoms, 293 intended operations |

## Oracle and G9 diagnostics

| Preset | Seed | Model | Solved | Exact grading |
|---|---:|---|---|---|
| easy | 1769309985 | GPT-5.6 Terra | yes | `ok` |
| easy | 315853306 | Gemini 3.8 Flash | yes | `ok` |
| easy | 2137853913 | Gemini 3.8 Flash | yes | `ok` |
| medium | 128636755 | GPT-5.6 Terra | yes | `ok` |
| medium | 847059807 | Gemini 3.8 Flash | yes | `ok` |
| medium | 1380289783 | Gemini 3.8 Flash | yes | `ok` |
| hard | 197689505 | Gemini 3.8 Flash | yes | `ok` |
| hard | 86285304 | GPT-5.6 Terra | yes | `ok` |
| hard | 1720650588 | GPT-5.6 Terra | yes | `ok` |

| G9 arm at `hard` | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 3/3 | last writable instance is discoverable |
| structural hint | 2/3 | hint did not improve over placebo |
| placebo hint | 3/3 | generic prompt change did not explain success |

Hinted minus placebo is `-1/3`; with only three calls this is noise, but it
certainly provides no evidence that the declared invariant creates hidden
difficulty. The authoritative bare evidence is `llm_loop_transcript.jsonl`;
the two arm transcripts are separate so they did not overwrite it.

## Use

```python
import importlib.util

path = "results/1303.0729/gen_1303_0729.py"
spec = importlib.util.spec_from_file_location("gen_1303_0729", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer(
    "<answer>" + gen._answer_text(inst["answer"]) + "</answer>"
)
assert gen.verify(inst, candidate) == (True, "ok")
```

From the repository root, local generation would normally be:

```bash
python3 results/1303.0729/gen_1303_0729.py
bash scripts/emit.sh 1303.0729 20 hard
```

Do not run the emit command for corpus release while `.meta.json` says
`cap_bound`; it is shown only to document the standard interface.

## Caveats

The largest caveat is decisive: every bare oracle call solved, so this family
does not satisfy H at a writable preset. The 0/200,000 guess result samples the
declared row-wise coefficient language after all shape and range constraints;
it proves resistance to uninformed coefficient guesses, not to the much
stronger prior “follow the unique valuation-oriented cycle.” Once that prior
is used, the family is linear-time and easy—the intended Track-B behavior, but
too easy for the evaluated models here.

The panel did not include a learned cycle recognizer or a symbolic CAS running
the paper's full valued Mora/Buchberger implementation. The former omission is
covered empirically by the oracle failures of the benchmark; the latter would
solve, just like the disclosed Gaussian reference. This is the paper's
degree-one corner, not evidence about the difficulty of general valued
Gröbner-basis computation. `gvlib` is imported when available, but the module's
exact `Fraction` fallback is standard-library-only. No unresolved correctness
caveat remains in G, V, canonicalization, or bounded-language uniqueness; the
park is solely the no-tool hardness/output-cap interaction.
