# Paired-root tensor decompositions from arXiv:1303.6914

| profile | value |
|---|---|
| track | **B — no-tool compression** |
| native domain / regime | algebra / rational exact |
| computational core | linear algebra |
| certificate | rational vector of signed unit fractions |
| intuition | invariant: a barycentric functional from an even polynomial |
| domain essentiality | native |
| reduction | none |

**Release status:** ready. All local gates pass. The script-owned bare loop
rejected `easy` after 3/3 solves and returned `hardened` at `medium` after 0/3
solves across OpenAI and Google. Both G9 control runs also completed normally.

## Problem and construction

Chiantini, Mella, and Ottaviani's [*One example of general unidentifiable
tensors*](https://arxiv.org/abs/1303.6914) defines identifiability as uniqueness
of a sum of simple (rank-one) tensors (Definition 2.1). Theorem 3.5 proves that a
general rank-eight tensor in `C^3 tensor C^6 tensor C^6` has at least six such
decompositions. Lemmas 3.2–3.3 use a special Segre-Veronese fourfold and an
ancillary Macaulay2 calculation; Remark 3.7 says the exact number is unknown.

The theorem is existential, so it does not itself output alternate exact
decompositions for a generator. This module instead composes a certificate in
the paper's native objects. It chooses eight positive integer nodes and their
negatives. For

`P(z) = product_j (z^2 - x_j^2)`,

the exact functional `sum_{P(t)=0} f(t)/P'(t)` vanishes for every polynomial
`f` of degree at most 14. Each displayed simple tensor has coordinate products
of degrees 0 through 14. Normalized reciprocal derivatives therefore give a
dependence among sixteen simple tensors. Moving its eight positive and eight
negative terms to opposite sides produces two eight-term decompositions of one
tensor in `Q^3 tensor Q^6 tensor Q^6`. Verification uses exact integer moments;
it accepts either normalized witness and never reads `inst["answer"]`.

## Why Track B

This is explicitly not Track A. A specialist can flatten the tensors into a
`108 x 16` matrix and find its nullspace by exact rational Gaussian elimination.
That `O(d^4)` reference algorithm solved 8/8 shipping instances, with a median
**12,837 rational operations and 0.019 s** in the final self-test (observed
range 0.019–0.10 s across repeated local runs). Its operands grow with the node-bit
parameter `n`.

The compact route recognizes the paired roots and evaluates
`P'(x_j)=2*x_j*product_{k!=j}(x_j^2-x_k^2)`, divides all magnitudes by their gcd,
and restores tensor order. It takes **136 exact operations** for eight pairs.
That is a substantial no-tool compression from dense elimination, while still
remaining below G9's 300-operation cap. The Introduction's Kruskal discussion
and quoted BCO Corollary 8.4 identify easy generic regimes; no Track-A claim is
made for this special rational distribution.

An earlier consecutive-node prototype exposed an ordinary finite-difference
row and was solved 3/3 by both available oracle vendors through `n=24`.
Random paired nodes and barycentric denominators replace that failed design.
For the final version, `easy` was again solved 3/3, but `medium` held 0/3 and is
the first rung supported by the oracle evidence.

## Worked demo (`seed=0`)

The demo is hand-scale: `d=3`, five node pairs, identity-derived signed basis
changes, and a 55-operation paired-root calculation. Its complete rendering is:

```text
Exact dependence among simple tensors

All arithmetic is over Q. For exponents E and integer t, phi_E(t) is the
column vector [t^e for e in E], in the displayed order.

E_A = [0,1,2]
E_B = [0,1,2]
E_C = [0,3,4]
M_A = [[0,-1,0],[1,0,0],[0,0,1]]
M_B = [[1,0,0],[0,-1,0],[0,0,1]]
M_C = [[0,-1,0],[-1,0,0],[0,0,1]]

For each t_i below form a_i=M_A phi_E_A(t_i), b_i=M_B phi_E_B(t_i),
c_i=M_C phi_E_C(t_i), and the simple tensor T_i=a_i tensor b_i tensor c_i.
Its (r,s,u) coordinate is a_i[r]*b_i[s]*c_i[u]. All indices are 0-based.
The 10 parameters, in tensor-index order, are
t = [-1,1,4,-4,-3,3,-8,7,-7,8]

Find exactly 10 pairwise-distinct nonzero rationals lambda_i with
sum_i lambda_i T_i = 0 in Q^3 tensor Q^3 tensor Q^3.
A coefficient is [s,q], meaning s/q, where s is exactly -1 or 1 and
1 <= q <= 2970. The unordered coefficient set must be closed under negation:
[1,q] occurs iff [-1,q] occurs, each exactly once. Order matters: coefficient
i multiplies T_i. Any witness obeying all rules is accepted. Moving the two
signs to opposite sides gives equal-length tensor decompositions.

Give your final answer inside <answer></answer> tags as one JSON list of exactly
10 pairs [[s_0,q_0],...,[s_9,q_9]].
Example: <answer>[[1,2],[-1,2],[1,5],[-1,5]]</answer>
Output nothing else inside the tags.
```

One answer is:

```json
[[-1,54],[1,54],[1,99],[-1,99],[1,55],[-1,55],[-1,2970],[-1,990],[1,990],[1,2970]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final pair
returns `(False, "expected 10 coefficients, received 9")`. A person can solve
the demo on paper by forming the five values
`2*x_j*product_{k!=j}(x_j^2-x_k^2)` and taking normalized reciprocals.

## Difficulty presets

All non-demo presets use the paper's `3 x 6 x 6`, rank-eight dimensions. Larger
`n` means larger random nodes and exact operands, not a longer witness.

| preset | node bits `n` | dimension | terms | compact operations | status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 3 | 10 | 55 | hand example |
| easy | 5 | 6 | 16 | 136 | rejected rung: bare oracle solved 3/3 |
| medium | 9 | 6 | 16 | 136 | **shipping; bare oracle held 0/3** |
| hard | 13 | 6 | 16 | 136 | local gates pass; not needed |

`escalate()` raises node bit size at fixed 16-entry witness length and returns
`"cap_bound"` before the conservative 2,000-character bound would be crossed.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed plants; 12/12 JSON round trips |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced prose round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware signed-unit-fraction guesses |
| G5 | pass | sampled density 0/200,000 at shipping; reference 12,837 ops / 0.019 s |
| G6 | pass | four well-formed attacks x 8 seeds, all 0 successes; reference 8/8 |
| G7 | pass | `n=9` to `n=18`; denominator bound 93 to 241 bits; plant verifies |
| G8 | pass | 100/100 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst of 1,000 seeds: 696 chars, 174 estimated tokens, 32 scalar atoms; 136 ops |

The four failed attacks are factor-height ordering, greedy minimization of the
degree-one moment, 256 random restarts, and the obvious “pair opposite nodes”
ansatz. The standard exact-nullspace algorithm is correctly reported under
`reference_algorithm`, not as a failed attack, because this is Track B.

## Oracle loop and G9 arms

The bare loop had six scored calls and no API errors. The two `length` rows
below contained no valid final witness; inspection confirmed that the apparent
parse miss did not hide an answer, so it is not a G3 bug.

| preset | model | seed | solved | exact grading result |
|---|---|---:|---:|---|
| easy | OpenAI `gpt-5.6-terra` | 1860952289 | yes | `ok` |
| easy | Google `gemini-3.8-flash` | 763016502 | yes | `ok` |
| easy | Google `gemini-3.8-flash` | 465759610 | yes | `ok` |
| medium | Google `gemini-3.8-flash` | 511940620 | no | malformed coefficient pair; length stop |
| medium | OpenAI `gpt-5.6-terra` | 677898623 | no | duplicate coefficients |
| medium | Google `gemini-3.8-flash` | 431886481 | no | no answer block; length stop |

| G9 arm | solved / scored | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping rung held |
| hinted | 0 / 3 | `hinted_verdict="hardened"` |
| placebo | 0 / 3 | control also held; one empty length-limited response |

`hinted - placebo = 0.0`. The structural hint bought no measured improvement,
so this diagnostic does not isolate discovery of the named invariant as the
only difficulty: deriving and executing the 136-operation large-integer route
remains substantial even after the invariant is named. The answer cap measures
696 characters, about 174 tokens and 32 scalar atoms at worst over 1,000 seeds.

## Use

```python
import json
import gen_1303_6914 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
reply = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(reply)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1303.6914 20
```

## Caveats

- This is a rational special family in the paper's native tensor language. It
  certifies two decompositions, not the theorem's generic lower bound of six,
  and does not prove that their common tensor has minimal rank eight.
- G4 is uniform over the explicitly bounded language: choose eight distinct
  denominators, include both signs, then permute. The 0/200,000 observation is
  an empirical density, not an exact count or a proof of a sub-millionth true
  probability, and it says nothing about a solver that recognizes barycentric
  interpolation. Exact enumeration at the shipping preset is infeasible and
  `enumerate_all()` correctly returns `None` there.
- Exact rational elimination already solves every instance. Gröbner-basis,
  homotopy-continuation, and numerical CP-decomposition attacks were not run;
  they would not strengthen the deliberately narrow Track-B claim.
- The compact route is short by the stated operation metric but operates on
  integers up to roughly the reported 93-bit denominator scale. The identical
  hinted/placebo result suggests some measured difficulty is exact arithmetic,
  not just recognizing the barycentric invariant.
- `canonical_key` is invariant under column order, equal-mode exchange,
  unimodular mode-basis changes, and common node scaling. It is not a complete
  invariant under arbitrary projective transformations.
- The oracle pool configured by the repository at run time had two vendors,
  not the four described in the original task prose; each level still received
  three fresh seeded calls, with one vendor necessarily repeated.
