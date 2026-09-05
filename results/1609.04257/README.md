# Verified generator for arXiv:1609.04257

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate | polynomial (a sparse vector of multipliers in `Z[x]`) |
| Intended intuition | invariant: a signed power-sum sequence has a low-degree annihilator |
| Domain essentiality | native |
| Reduction | none |

This is a generator for a sparse standard-representation problem based on Eder,
Pfister, and Popescu, [*New Strategies for Standard Bases over Z*](https://arxiv.org/abs/1609.04257).
The solver receives exact generators

`f_i(x) = 1 + a_i*x + a_i^2*x^2 + ... + a_i^9*x^9`

and a target `T` in `Z[x]`. It must return five nonzero polynomial multipliers,
each `+(1+x)` or `-(1+x)`, proving `T = sum(q_i*f_i)`. The checker parses the
polynomials as exact rationals and expands the identity exactly; there are no
floats, tolerances, searches, or reads of the planted answer. Ten moments also
make the bounded answer unique: subtracting two valid five-term representations
would give a nonzero signed measure on at most ten distinct nodes with its first
ten moments zero, contradicting invertibility of the corresponding Vandermonde
matrix.

## Why Track B

The paper does **not** prove hardness for a distribution. Section 1, Algorithm 1
gives Buchberger's strong-standard-basis algorithm; Section 3, Algorithm 2
(`preIntegerCheck`) computes a basis over `Q` and syzygies to expose an integer
in an ideal; its Example 1 writes out such a polynomial combination. Section 4,
Algorithm 3 gives a terminating normal-form procedure for local and mixed
orders. A Track A claim would therefore be false.

The paper nevertheless documents mechanical cost: the ALL and JUST pair
strategies can differ by factors up to 38,000, one Appendix example took almost
30 hours over `Z`, and the 70-generator Section 3 example first exposes
6,133,248 before the smaller constant 18. For this deliberately bounded family,
the disclosed reference algorithm is more modest but still unfit for mental
execution: meet in the middle over a positive pair and negative triple, in
`O(n^3)` exact additions and `O(n^2)` memory. At the shipping preset it averaged
205,840 operations and about 0.01 seconds over eight local runs, solving 8/8.

The compact route is different. Divide `T` by `1+x`; the ten quotient
coefficients are `s_r=sum epsilon_j*a_j^r`. Solve the 5-by-5 Hankel recurrence,
factor its characteristic polynomial by trial division through the printed
prime nodes, and use `s_1` to assign the positive pair. The included exact
implementation solved 8/8 and used at most 231 arithmetic operations. The task
tests noticing this invariant; a program can solve it quickly.

## Worked demo

This is the full instance rendered by `make_instance(n=6, seed=0,
moment_count=10, prime_min=2, prime_span=12)`:

```text
Work in the integer polynomial ring Z[x].

There are 6 generators.  Generator i has the printed positive integer node a_i and is

    f_i(x) = sum from r=0 through r=9 of a_i^r x^r.

Generator labels are 1-based.  Here are all label:node pairs; their printed order is part of the instance:
1:23, 2:13, 3:29, 4:17, 5:11, 6:19

The target is T(x)=sum from r=0 through r=10 of t_r x^r.  Its coefficients are listed in ascending degree order [t_0,t_1,...,t_10]:
[-1, -38, -1166, -33542, -944174, -26431718, -740644046,
 -20823544262, -587842282094, -16661328178598, -16093594316677]

Find a sparse standard representation T(x)=sum_i q_i(x)f_i(x) with exactly five nonzero multipliers.  Each q_i must be +(1+x) or -(1+x), exactly two must be positive and three negative, and the five distinct entries must be sorted by increasing generator label.  No other generators are implicitly present.

Encode the answer as JSON.  Each entry is [generator_label, polynomial].  A polynomial is a list of [coefficient, exponent-list] terms in ascending exponent order; an exact rational coefficient is [numerator,denominator], and this problem has the single-variable exponent lists [0] and [1].

Give your final answer inside <answer></answer> tags, in exactly this JSON format:
<answer>[[1,[[[1,1],[0]],[[1,1],[1]]]],[2,[[[-1,1],[0]],[[-1,1],[1]]]],[3,[[[1,1],[0]],[[1,1],[1]]]],[4,[[[-1,1],[0]],[[-1,1],[1]]]],[5,[[[-1,1],[0]],[[-1,1],[1]]]]]</answer>
The displayed JSON is only a syntax example, not the solution.  Output nothing else inside the tags.
```

The exact answer is:

```json
[[1,[[[-1,1],[0]],[[-1,1],[1]]]],[2,[[[1,1],[0]],[[1,1],[1]]]],[3,[[[-1,1],[0]],[[-1,1],[1]]]],[4,[[[-1,1],[0]],[[-1,1],[1]]]],[6,[[[1,1],[0]],[[1,1],[1]]]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final entry
returns `(False, "expected exactly five certificate entries")`. A person can
solve this six-node demo on paper by testing its 60 already-structured
candidates; the larger presets are not meant for enumeration by hand.

## Difficulty presets

| preset | n | prime window | structure-aware space | status |
|---|---:|---:|---:|---|
| demo | 6 | 2 + 12 | 60 | hand-scale illustration |
| easy | 40 | 100 + 800 | 6,580,080 | rejected by oracle: 1/3 solved |
| medium | 80 | 1,000 + 8,000 | 240,400,160 | **ships; 0/3 solved** |
| hard | 128 | 10,000 + 50,000 | 2,645,664,000 | available, not needed by the ladder |

`SHIPPING_DIFFICULTY` is `medium`. Increasing `n` grows the generator haystack
without lengthening the five-polynomial witness; `escalate` next grows to 96
and then 112/128/144 before increasing coefficient sizes at fixed witness
length.

## Gate results

| gate | result |
|---|---|
| G1 planted verifies | pass, 12/12 preset/seed checks |
| G2 corruptions | pass, 6/6 rejected with six distinct reasons |
| G3 parser round-trip | pass for prose/tags and direct tags; garbage gives `None` |
| G4 guessing | pass, 0/200,000; exact language size 240,400,160 |
| G5 density/baseline | unique fraction `4.1597310085e-9`; demo exact count 1/60; baseline seed used 140,914 operations in 0.007 s |
| G6 adversaries | pass; four attacks each 0/8; reference algorithm 8/8 |
| G7 scaling | pass at doubled `n=160`, still five answer entries |
| G8 canonical key | 80/80 invariant, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9 caps | pass; 162 chars, 35 atoms, about 41 tokens, 231 intended operations |

The exact machine-readable measurements, including wall-clock variation, are
in [`selftest_report.json`](selftest_report.json).

## Bare oracle loop

| preset | seed | model | solved | observed reason |
|---|---:|---|---|---|
| easy | 1337423823 | GPT-5.6 Terra | no | parseable candidate failed at quotient coefficient `x^2` |
| easy | 432978551 | Gemini 3.8 Flash | no | reasoning exhausted the response limit |
| easy | 410761113 | GPT-5.6 Terra | **yes** | exact certificate verified |
| medium | 1853299541 | Gemini 3.8 Flash | no | reasoning exhausted the response limit |
| medium | 1568621575 | GPT-5.6 Terra | no | answered that no representation exists |
| medium | 1897740609 | Gemini 3.8 Flash | no | response ended during arithmetic without an answer |

The untouched script-owned evidence is in
[`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) and [`.meta.json`](.meta.json).

## G9 diagnostic arms

| arm | solved / attempts | interpretation |
|---|---:|---|
| bare shipping rows | 0/3 | held |
| structural hint | 0/3 | held |
| placebo hint | 1/3 | one independently solved instance |

Hinted minus placebo is `-1/3`. In this small sample, naming the annihilator
invariant bought no measurable help; the placebo result also shows substantial
instance/model variance. The answer is 162 characters, 35 atomic elements and
about 41 tokens; the measured compact route is 231 exact operations. The two
arm transcripts are [`g9_hinted_transcript.jsonl`](g9_hinted_transcript.jsonl)
and [`g9_placebo_transcript.jsonl`](g9_placebo_transcript.jsonl).

## Use

From the repository root:

```python
import importlib.util

path = "results/1609.04257/gen_1609_04257.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
assert g.verify(inst, inst["answer"]) == (True, "ok")
prompt = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate)[0]
```

Emit dataset rows with:

```bash
bash scripts/emit.sh 1609.04257 20 medium
```

## Caveats

This is intentionally not evidence of complexity-theoretic hardness. A CAS,
the included meet-in-the-middle reference, or the included annihilator solver
makes it easy; no external Singular run, Gröbner-basis engine, LLL attack, or
general sparse-recovery package was tested. It covers exact global univariate
standard representations, not the paper's local/mixed-order termination issue
or its worst coefficient-growth examples.

The 0/200,000 guessing result is uniform over the *stated* prior: five distinct
labels and exactly two positive signs. It does not model a solver exploiting
moments, and the exact unique-answer probability is the more informative
`1/240400160`. Prime nodes and the common multiplier are deliberate structure,
not natural random ideals. Finally, the oracle sample is only three attempts per
arm from two vendors, with some length-limited replies; the transcripts expose
that uncertainty rather than turning it into a Track A claim.
