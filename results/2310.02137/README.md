# Prime-coordinate quadratic witness generator

This module turns Philippa Holdridge's [*Random Diophantine Equations in the Primes II*](https://arxiv.org/abs/2310.02137) into a finite witness-search task.  An instance gives integer weights and the homogeneous quadratic form

\[
F(x)=\left(\sum_i a_i x_i\right)\left(\sum_i x_i\right).
\]

Each ordered coordinate must be one of the primes `1000000007` and `1000000009`, exactly half must use the larger prime, and the solver returns those 1-based positions. Checking consists only of rebuilding the tuple and evaluating the two integer sums. Any valid half-set is accepted, not just the planted one.

## Why this is a defensible hard family

Section 1 of the paper defines a prime point as a non-diagonal prime vector on an integral homogeneous form. Here `d=2` and the paper's parameter is `n_paper = variables - 1`; all presets therefore satisfy Theorem 1.2's `n_paper >= d` hypothesis and avoid `(2,2)` and `(3,3)`. Theorem 1.1 identifies `(2,2)` as having zero prime-local density. The comments on degree 1 and Section 3's sieve bounds are existence/counting results, not search algorithms.

The paper does **not** prove computational hardness. Hardness instead follows from the bounded specialization: because `sum(a_i)=0` and `q-p=2`, `F(x)=0` is exactly the problem of choosing half the weights with sum zero. Equal-cardinality partition reduces to this by sending inputs `w_i` of total `2T` to `a_i = m*w_i - 2T`; hence a polynomial algorithm here would solve an NP-complete problem. The generator samples the half-set first, then draws its weights and the complement's weights independently from the same bounded zero-sum distribution. The shipping space has 118,264,581,564,861,424 structurally valid witnesses.

## Worked shipping-preset example

This is the complete `render(make_instance(n=60, weight_bits=60, seed=0))` output. It is collapsed only to keep this page scannable.

<details>
<summary>Rendered instance (click to expand)</summary>

```text
BALANCED PRIME-COORDINATE QUADRATIC EQUATION

There are 60 ordered variables x_1,...,x_60.  Each variable must be one of
the two primes p=1000000007 and q=1000000009.  Exactly 30 variables must equal q; all
other variables must equal p.  Thus repeats of prime values are required, but
an index can be chosen only once.  Indices are 1-based and run from 1 through
60, inclusive.

For the integer weights a_i below, define

  A(x) = sum from i=1 to 60 of a_i*x_i,
  S(x) = sum from i=1 to 60 of x_i,
  F(x) = A(x)*S(x).

This is a homogeneous polynomial of degree 2.  Equivalently, the coefficient
of x_i^2 is a_i and the coefficient of x_i*x_j for i<j is a_i+a_j.  All
arithmetic is exact integer arithmetic.  Find a permitted, non-diagonal prime
tuple for which F(x)=0.  (The exact-30 rule already makes it non-diagonal.)

Weights, in `index: a_i` format:
  1: 444500560911110212
  2: -26919162524079900
  3: 21524567751985737
  4: 375002474751919893
  5: -357738276389416552
  6: 166749978646065768
  7: -264538599045635867
  8: -294035421664953074
  9: -81011915832258201
  10: 535901218287879192
  11: -233579695276306410
  12: -529804665365866313
  13: 2675242021609661
  14: -449594979634422325
  15: -380664428921146131
  16: -169976666952403442
  17: 133554742210626644
  18: 459461694019970712
  19: 274386636301577758
  20: 169742514958843270
  21: 43798510459063443
  22: -314148228750941894
  23: 38877714918341644
  24: 90268784651920754
  25: 134108486322708828
  26: -320683219782218231
  27: 191356547707240903
  28: 362731371076632996
  29: -151628685590538701
  30: -125853526345826888
  31: -229081360754367993
  32: -509432320394462503
  33: 300968200632788782
  34: 236662124588187984
  35: -374722938414627289
  36: 324277405273446759
  37: 58697103124128006
  38: -502125376652678512
  39: -50429728871161755
  40: 414008487325383455
  41: 192900122770390948
  42: 87380993002038452
  43: 469754357983742577
  44: 387617486776815431
  45: 399050536706513619
  46: 229248102970626795
  47: -531402378219700050
  48: -493759629926847521
  49: 482359716574810481
  50: -221227453527444161
  51: -121686093864434947
  52: -552021713085609724
  53: 47405437875804075
  54: -117559606561136897
  55: 227768815074311189
  56: 184020221196690739
  57: -277560552108049982
  58: 7482438338181358
  59: 476733734961917207
  60: -289789705716740009

Output the 30 distinct indices whose variables equal q.  Their order in the
answer does not matter; every unlisted index is assigned p.

Give your final answer inside <answer></answer> tags, as 30 comma-separated
base-10 integers.  Example of format only:
<answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30</answer>
Output nothing else inside the tags.
```

</details>

One answer is:

```text
<answer>3, 5, 7, 9, 10, 14, 17, 18, 19, 20, 22, 23, 25, 26, 27, 31, 32, 33, 35, 38, 40, 41, 44, 49, 50, 53, 54, 55, 57, 58</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing position 3 by position 1 returns `(False, "equation_nonzero")`.

## Difficulty presets

| Preset | Variables | Weight bits | Structured space | Status |
|---|---:|---:|---:|---|
| `easy` | 60 | 60 | 118,264,581,564,861,424 | **shipping; held immediately** |
| `medium` | 72 | 72 | 442,512,540,276,836,779,204 | not reached |
| `hard` | 84 | 84 | 1,678,910,486,211,891,090,247,320 | not reached |

No preset was rejected. `escalate()` adds 12 variables and 12 weight bits, up to 120 variables. Increasing `n` raises the balanced-subset search exponent; merely widening a fixed-dimensional prime interval was deliberately avoided because that would leave a polynomial-size enumeration in the interval length.

## Mandatory gates

| Gate | Result | Measurement |
|---|---|---|
| G1 planted verifies | pass | 12/12, every preset × 4 seeds |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | pass | 30 positions recovered through prose/fence; garbage → `None` |
| G4 structured guessing | pass | 0/200,000; prior uniform over exactly-30 subsets |
| G5 sparse | pass | 2/48,620 = 4.1135e-5 at enumerable `n=18` |
| G6 adversaries | pass | magnitude tails 0/16; greedy 0/8; 48-restart best-swap 0/8 |
| G7 scaling | pass | `n=120` built and verified; space 96,614,908,840,363,322,603,893,139,521,372,656 |
| G8 canonical key | pass | 120/120 invariance checks, 80 carried witnesses, 20/20 unrelated keys distinct |

The canonical key removes coefficient gcd/global sign and sorts weights. It is exactly invariant under every variable permutation, positive rescaling, sign change, and tested composition; this family has no unresolved graph-isomorphism caveat.

## Oracle hardening loop

The repository-owned harness returned `hardened` at `easy` with effort `medium`, no escalation.

| Model | Seed | Parsed | Solved | Why |
|---|---:|---|---|---|
| Gemini 3.1 Pro Preview | 277821171 | yes | no | proposed half-set gave `equation_nonzero` |
| Claude Sonnet 5 | 61291208 | no | no | exhausted 32,000 completion tokens in hidden reasoning and emitted no answer |
| Grok 4.6 | 1481451135 | yes | no | proposed half-set gave `equation_nonzero` |

The full replies and timings are in `llm_loop_transcript.jsonl`; `.meta.json` records the master seed, four-vendor pool, and verdict.

## Use

From this directory:

```python
import random
import gen_2310_02137 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
answer = gen.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
guess = gen.random_candidate(inst, random.Random(9))
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2310.02137 20
```

## Caveats

- Theorem 1.2 concerns almost all locally soluble forms as coefficient height grows. These deliberately reducible, planted forms are a measure-zero specialization, so the theorem supplies the definition and safe parameter regime—not a hardness or distributional guarantee. Satisfiability comes from inverse generation; worst-case hardness comes from the reduction above.
- `0/200,000` is the measured frequency under one explicit prior: uniform exactly-half subsets, with all statement-obvious structure enforced. It is not a confidence proof that every solver prior has probability below `1e-6`, nor does it rule out seed-specific extra roots. The smaller exhaustive audit found exactly the planted subset and its complement.
- The two zero-sum blocks guarantee the complementary solution and create higher-order correlations. Their one-coordinate distributions are identical, but this is not a proof of indistinguishability against every statistical method.
- The panel did not run lattice reduction, SAT/MILP solvers, or a full meet-in-the-middle search. Generic meet-in-the-middle takes about `2^(n/2)` partial assignments (roughly `2^30` at shipping), and specialized native implementations may solve some instances. This is exponential, not a polynomial-time method.
- One of the three decisive oracle failures was length-limited with an empty visible reply; the other two parsed correctly and failed exact verification. Oracle failure is empirical evidence, not a complexity proof.
