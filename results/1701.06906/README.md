# Verified generator for arXiv:1701.06906

## Profile

| field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate form | finite-field matrix certificate |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This generator turns the coefficient identity in the proof of Lemma 2.6 of
[Gavioli–Gül–Scoppola, *Metabelian thin Beauville p-groups*](https://arxiv.org/abs/1701.06906)
into an exact problem family. The solver is given selected monomials of the
native bivariate polynomial

`P(u,v) = sum_(r=0)^(p-1) (1+u)^r (1+v)^r` over `F_p`, followed by invertible
two-coordinate basis changes. It must return the resulting 32 by 2 coefficient
matrix.
The checker evaluates the paper's exact characteristic-`p` identity and performs
the displayed 2 by 2 matrix products; it never reads the planted answer.
The module is standard-library-only; it probes for the repository's optional
`gvlib` helpers but does not require or use them for this finite-field family.

## Why this is Track B

The literal definition gives
`c(i,j)=sum_r binom(r,i)binom(r,j) mod p`. The reference mechanical evaluator
uses factorial tables and binomial recurrences in `O(kp)`
field operations. On the hard shipping instance used by the saved self-test it
processed 2,053,947 binomial terms and 12,825,889 counted exact operations in
1.359 seconds; across eight shipping instances it averaged 13,342,769 operations
and 1.755 seconds.

The compression is the identity used between Lemmas 2.5 and 2.6:
with `w=(1+u)(1+v)=1+(u+v+uv)`, the full power sum collapses in characteristic
`p`. At total degree at most `p-1`, only one homogeneous boundary can survive.
Classifying 64 queries and applying 32 small matrices costs at most 288 exact
operations (including additions, comparisons, parity tests, signed additions,
and modular reductions). This is an efficient route and is disclosed; the
benchmark asks whether a no-tool solver can discover it and carry out the fixed-size coordinate
work. The easy regime avoided here is precisely a small `p`, where direct
coefficient accumulation is hand-scale. The paper's separate class-`<p`
Beauville criterion and its GAP classification of thin 3-groups are not used.

The prior triage suggestion—enumerate a finite group and find a Beauville
generating-pair structure—was rejected as the family, not mistaken for Track A.
Corollary 2.10, Remark 2.11, and Theorems 2.12–2.16 give a direct line-selection
construction with only bounded power-collision exclusions; natural Beauville
witnesses therefore become abundant rather than guess-resistant as `p` grows.

## Worked demo

With `make_instance(n=7, k=4, seed=0)`, the prime is 11 and the complete block
data are:

```text
0: (1,9) ; (2,8) ; [[6,4],[7,5]]
1: (1,7) ; (1,1) ; [[9,3],[8,2]]
```

The required answer is `<answer>[[9, 9], [0, 0]]</answer>`.
`verify(inst, [[9, 9], [0, 0]])` returns `(True, "ok")`; dropping the final row
returns `(False, "expected exactly 2 output rows")`. A person can solve
this demo on paper either by accumulating ten short binomial terms per query or
by spotting the identity.

## Difficulty presets

| preset | lower prime scale `n` | coefficients `k` | status |
|---|---:|---:|---|
| demo | 7 | 4 | hand example; never ships |
| easy | 1,009 | 64 | oracle solved 3/3 |
| medium | 10,007 | 64 | oracle solved 3/3 |
| hard | 100,003 | 64 | configured shipping candidate; oracle solved 2/3, so not approved |

Only the haystack grows: the direct sum gets longer while the answer remains 64
coordinates.

## Local gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified and JSON-round-tripped |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged fenced JSON with surrounding prose round-tripped |
| G4 | pass | 0/200,000 uniform structure-aware guesses |
| G5 | pass | unique answer; sampled density 0/200,000; 12,825,889-op reference run |
| G6 | pass | five attacks, 0/8 successes each; reference algorithm 8/8 as expected |
| G7 | pass | prime grew from 100,403 to 202,817; answer stayed at 64 atoms |
| G8 | pass | 20/20 invariant keys, 20/20 carried witnesses, 20/20 distinct instances |
| G9(c) | pass | 421 characters, 106 estimated tokens, 64 atoms, 288 operations; worst of 10,000 seeds |

The five failed attacks are all-zero source coefficients, all-one source
coefficients, an unsigned boundary rule, applying parity to every query, and a
uniform random coefficient matrix. Independent `GL(2,p)` matrices remove the
obvious raw `0,+1,-1` answer signature without changing the polynomial problem.

## Oracle loop

| rung (`n`) | model seeds | verified outcomes | why |
|---|---|---|---|
| easy (1,009) | 1293255200, 434788872, 2124501607 | 3 solved / 0 failed | all matrices verified |
| medium (10,007) | 212534747, 1022732073, 1921981004 | 3 solved / 0 failed | all matrices verified |
| hard (100,003) | 2070279993, 1314578831, 45386562 | 2 solved / 1 failed | failed answer first disagreed at block 1 |
| escalated (1,000,030) | 868568381, 696913825, 28563508 | 2 solved / 1 failed | failed answer first disagreed at block 0 |
| escalated (10,000,300) | 798960952, 1452995562, 1670463354 | 2 solved / 1 failed | failed answer first disagreed at block 28 |
| escalated (100,003,000) | 557976540, 1078720193, 1393645779 | 2 solved / 1 failed | failed answer first disagreed at block 2 |
| escalated (1,000,030,000) | 1092482406, 457261577 | 0 solved / 2 failed | disagreements at blocks 9 and 30; third slot had four HTTP 403 retries |

The bare harness reached its final configured round, where two distinct vendors
failed, but OpenRouter exhausted the key's total limit before a third valid
attempt. The script therefore issued no hardness verdict; errors are not counted
as model failures. The named `hard` rung is demonstrably too easy, while the
final escalated rung is promising but incomplete. The family is parked, not
rejected and not approved for emission.

## G9 diagnostics

| arm | solved/attempts | result |
|---|---:|---|
| bare at configured hard | 2/3 | one invalid matrix, so this rung did not hold |
| structural hint | 0/0 | all retries blocked by OpenRouter HTTP 403 key limit |
| placebo hint | 0/0 | all retries blocked by OpenRouter HTTP 403 key limit |

The hinted-minus-placebo difference is unavailable. Both comparison arms were
invoked in isolated scratch directories, but neither produced a valid attempt.
The local answer-size and intended-route caps are fully measured and pass.

## Use

```python
import random
import gen_1701_06906 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=42)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) != inst["answer"]
```

From the repository root, emit after a successful oracle run with:

```bash
bash scripts/emit.sh 1701.06906 20
```

## Caveats

This family becomes easy for any solver that recognizes the characteristic-`p`
power-sum identity and has reliable modular arithmetic; that is intentional for
Track B. The `0/200,000` guess result is only for the declared uniform prior on
all 32 by 2 matrices over `F_p`; it does not model a solver that has inferred
the hidden `0,+1,-1` source coefficients. The adversary panel does not include
a CAS generating-function simplifier, because that is the successful compact
route rather than a failing attack. It also does not benchmark alternative
hypergeometric-summation packages. Most importantly, the final bare panel lacks
its third valid vendor and both G9 comparison arms remain unmeasured because the
available API key exhausted its total limit. This directory is not
submission-ready until those runs complete and, if an escalated rung holds, the
difficulty ladder is slid upward and all local shipping measurements are rerun.
Escalation keeps the 32 by 2 shape fixed and returns `cap_bound` only when a
safe worst-case digit bound puts its compact JSON serialization over 2,000
characters.
