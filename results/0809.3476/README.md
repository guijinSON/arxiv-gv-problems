# Exact counts of inequivalent minimal cycle factorizations

| Profile | Value |
|---|---|
| Paper | Berkolaiko, Harrison, Novaes, [*On inequivalent factorizations of a cycle*](https://arxiv.org/abs/0809.3476) |
| Track | **B** — no-tool compression; not a Track A hardness claim |
| Native domain / regime | combinatorics / finite discrete |
| Computational core | other (exact enumeration) |
| Certificate | exact symbolic rising product, with an exact-integer alternative |
| Native objects | cycle-type vector, an n-cycle, equivalence classes of minimal cycle factorizations |
| Intended intuition | change of variables: factorization class → rooted plane tree → cyclic outdegree word |
| Domain essentiality | native; no reduction |

## What the family asks

An instance gives distinct cycle lengths `j`, each with multiplicity one, and
sets `N = 1 + sum(j-1)`. The solver must count equivalence classes of minimal
factorizations of `(1 2 ... N)` having precisely those factor lengths. Two
factorizations are equivalent when adjacent disjoint, hence commuting, factors
are swapped. The answer may be the integer count or a short increasing list of
integers whose product is that count. `verify` recomputes the count from the
type vector with exact integer arithmetic and never reads the planted answer.

The generator is theorem-backed, not solve-and-plant. Theorem 1 identifies the
classes with rooted plane trees whose internal degrees are `2j`. Removing the
distinguished root leaf gives internal outdegrees `2j-1`; the cycle lemma counts
the resulting Łukasiewicz words. If `R=sum(j-1)` and there are `m` distinct
types, then

```text
H = (2R+m)! / (2R+1)! = (2R+2)(2R+3)...(2R+m).
```

The planted witness is those `m-1` consecutive factors. This composition of
identities keeps the answer writable without asking the model to multiply a
large integer.

## Why Track B

Section 1 fixes type, minimality, multiplication order, and commuting-factor
equivalence. Theorem 1 supplies the tree bijection and an explicit deletion
reconstruction; this makes the tempting “order these planted cycles” family
constructively easy and rules out Track A. Lemma 1 fixes cycle orientation.
Theorem 2 and Section 4 supply the recurrence used by the mechanical reference.

Generic prefix dynamic programming on Łukasiewicz outdegree words takes
`O(2^m m R)` exact additions and `O(2^m R)` memory. On eight shipping instances
it solved 8/8, using 361,472 additions total (45,184 average) and 0.58 seconds in
the recorded self-test; repeated runs ranged from about 0.1 to 0.7 seconds.
This success is expected and is separate from the attack panel. The efficient
compact algorithm is also stated openly: recognize the tree/cycle-word identity
and form the rising product in `O(m)` time. Its symbolic answer needs 21 small
exact operations at shipping size. This tests discovery of the compression,
not worst-case complexity.

## Worked demo

The `demo` preset with seed 0 renders this hand-scale instance:

```text
Exact count of inequivalent minimal cycle factorizations

Work in the symmetric group on the labels 1,...,11.
Let C be the cycle (1 2 ... 11).  Permutations are composed
right-to-left: in sigma_m ... sigma_1, sigma_1 acts first.

A cycle factorization of C is a product sigma_m ... sigma_1 = C.
Its type records how many factors have each cycle length.  It is
minimal when sum over its factors of (cycle_length - 1) equals
11 - 1.  Two minimal factorizations are equivalent when one
can be obtained from the other by repeatedly swapping adjacent
disjoint cycles; disjoint cycles commute.

Here m = 2.  There must be exactly one factor of each of these
distinct lengths (the displayed order is irrelevant):
  7 5
Their sum of (length-1) values is 10, so minimality is exact.

Find the exact number H of equivalence classes of such minimal
factorizations.  Give one of the following exact certificates as JSON:
1. {"value": V}, where V is the integer H and 0 <= V < 61;
2. {"product": [a1]}, containing exactly one integer a1,
   with 2 <= a1 <= 61,
   and its exact product is H.  Order and distinctness are part of
   this canonical product format; repeats are not allowed.

Give your final answer inside <answer></answer> tags, as one JSON object
in exactly one of the two formats above.
Example format: <answer>{"product":[2]}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"product":[22]}</answer>`. It is hand-solvable
after the tree/cycle-word observation:
`verify(inst, {"product": [22]}) == (True, "ok")`. A corruption gives
`verify(inst, {"product": []}) == (False, "product factor list is empty")`.

## Difficulty presets

| Preset | Maximum length `n` | Distinct types `m` | Product atoms | Status |
|---|---:|---:|---:|---|
| demo | 7 | 2 | 1 | hand-solvable; skipped by hardening |
| easy | 24 | 7 | 6 | **ships; bare oracle held 0/3** |
| medium | 40 | 9 | 8 | not reached after `easy` held |
| hard | 64 | 11 | 10 | not reached after `easy` held |

Increasing `n` enlarges the coefficient/rank range and generic DP cost.
`escalate` multiplies this ambient range by four while holding answer length
fixed.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 preset–seed certificates verified; JSON round-trip checked |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware candidates valid; space `5,736,085,959,633,562` |
| G5 | pass | density 0/200,000; DP 361,472 additions, 0.58 s, 8/8 solved; demo exact count two |
| G6 | pass | all five in-context attacks 0/8; reference algorithm separately solved 8/8 |
| G7 | pass | `n=24→48`, larger space, same six-atom answer |
| G8 | pass | 60 invariance and 60 carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 37 characters, about 10 tokens, six atoms, 21 intended operations |

The failing attacks were largest-input-length product, smallest admissible
factors, independent-open-slot power, an off-by-one rising product, and 256
structure-aware random restarts per seed. Every cycle length is sampled by the
same rule; there is no planted-versus-decoy marker.

## Oracle loop

The harness returned `hardened` at `easy` without escalation. The third call
was a valid HTTP response but emitted no answer after using the 32,000-token
completion budget; this is recorded separately from the two wrong answers.

| Preset | Model | Seed | Solved | Reason |
|---|---|---:|---:|---|
| easy | `google/gemini-3.8-flash` | 1037224055 | no | parsed product had the wrong exact value |
| easy | `openai/gpt-5.6-terra` | 1882228916 | no | parsed product had the wrong exact value |
| easy | `google/gemini-3.8-flash` | 776643309 | no | empty length-limited response |

## G9 arms

| Arm | Solved / scored attempts | Outcome |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo | 0/1 | incomplete; four later calls were HTTP 403 quota errors |

The observed hinted-minus-placebo rate is `0.0`, so there is no observed
structural lift. That conclusion is weak because the placebo arm has only one
scored attempt: the OpenRouter key reached its total limit before the other two
could run. Errors are retained in `g9_placebo_transcript.jsonl` and are not
counted as failures. The hint names only the cyclic-word invariant. Answer size
is 37 characters (about 10 tokens), six atoms; the intended route uses 21 exact
operations.

## Use

```python
from gen_0809_3476 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert ok, reason
```

From the repository root:

```bash
bash scripts/emit.sh 0809.3476 20 easy
```

## Caveats

- Bare hardening is complete, but the non-gating placebo diagnostic is short by
  two scored attempts because external OpenRouter quota was exhausted. HTTP
  errors are not hardness evidence and were not counted.
- The closed form is an efficient `O(m)` algorithm and the compact route. The
  DP is the generic route from the recurrence, not the strongest known method;
  this distinction is why the family is Track B.
- Zero random hits estimates density only under the declared uniform prior over
  the two bounded, shape-constrained certificate forms. It is not a Bayesian
  model-success probability, and alternate product certificates may exist.
- The panel did not test CAS generating-function recognition, a model with
  tools, or every arithmetic ansatz. Recognizing the cycle lemma makes it easy.
- `canonical_key` quotients input reordering. Cycle lengths are semantic data,
  so arbitrary changes to their values are not isomorphisms.
- `gvlib` is imported when present, but this family only needs standard-library
  exact integers; verification uses no floating point.
