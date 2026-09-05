# Archived isogeny-path candidate — arXiv:1711.04062

| profile | value |
|---|---|
| Track considered | A (structural hardness), then B (no-tool compression) |
| Native domain | number theory |
| Object regime | finite field |
| Computational core | supersingular isogeny-path search |
| Certificate | exact sequence of degree-2 kernels |
| Intended intuition | forward/reverse meet-in-the-middle collision |
| Status | **rejected; do not ship** |

The retained module inverse-generates a non-backtracking sequence of degree-2
isogenies over `F_(p^2)` and verifies a proposed sequence by exact kernel
substitution and quotient replay. Thus generation and verification are sound
for the module's stated exact-model problem. The source is Luca De Feo's
[*Mathematics of Isogeny Based Cryptography*](https://arxiv.org/abs/1711.04062).

## Why it is archived

There are two independent blockers.

First, Section 9 defines an isogeny graph on **j-invariants**, and Section 11,
Theorem 47 proves expansion for that graph. The retained implementation instead
requires the replay to end at one exact coordinate-normalized Weierstrass model.
Its `canonical_key` identifies endpoints with the same j-invariant while
`verify` distinguishes them. The cited theorem therefore does not establish
Track A hardness for the distribution the code actually generates.

This was reproduced on an 8-step instance: scaling only the target by the
valid change of variables `x=u^2*x'`, `y=u^3*y'` preserved its j-invariant and
the canonical key, but `verify` rejected the original path with
`"replayed path ends at a different curve model"`. The corrected G8 record is
therefore failing as well.

Second, repairing the endpoint test to compare j-invariants does not create a
no-tool problem. Section 12's Problem 3 gives meet-in-the-middle path finding;
Section 13 identifies CGL preimages with that problem; and Section 14.2 gives
`O(2^(e/2))` time and storage for a hidden degree-`2^e` walk. At the retained
shipping setting `e=58`, recognizing the collision idea still leaves a
`2^29 = 536,870,912`-entry one-sided frontier. There is no shorter route in
the paper. The earlier report's value 290 counted **replaying an answer already
known**, not finding it; that was not the G9(c) quantity.

For `p=2^61-1`, Theorem 47 gives
`floor(p/12)+1 = 192,153,584,101,141,163` supersingular isomorphism classes.
The paper's generic birthday search is therefore about
`sqrt(#G) = 438,353,264` graph steps, comparable to the known-length
`2^29` route. Mechanical and compact-route costs are both hundreds of millions
of steps, far above the 300-operation cap.

## Preserved evidence

| check | retained result |
|---|---:|
| Planted replay | 12/12 verified |
| Corruptions | 5/5 rejected with distinct reasons |
| Structure-aware random guesses | 0/200,000 |
| Capped bidirectional attack | 0/8; 524,512 nodes; 16.74 s |
| G8 native target relabelling | same key, but witness rejected — **fails** |
| G9 answer size | 1,564 chars; 58 atoms |
| Corrected intended-route cost | 536,870,912-entry frontier — **fails** |

The prior bare, structural-hint, and placebo harness files are also preserved.
They contain only HTTP 403 key-limit errors, so they establish no model-hardness
result.

## Worked demo

`make_instance(n=4, seed=1, mersenne_exponent=5)` produced the retained answer
`["0","jt","i3","lp"]`; `verify` returns `(True, "ok")`. Dropping the last
kernel returns `(False, "path length is 3, expected 4")`. The demo is enumerable
by hand, but the shipping problem has no hand-scale solution route.

## How to inspect the archived code

```python
import rejected_gen_1711_04062 as g

inst = g.make_instance(seed=1, **g.DIFFICULTY["demo"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
report = g.selftest()  # expensive: the 200,000-sample gate takes several minutes
assert report["G9_no_tool_suitability"]["pass"] is False
```

## Caveats

The paper itself explicitly makes known-kernel isogeny computation easy via
Vélu's formulas and gives polynomial algorithms for explicit isogenies of known
degree (Section 12). Ordinary graphs have volcano structure (Section 9). Those
alternatives do not rescue this candidate: they either fail Track A or still
lack a measured short Track B route. Modern quaternion and endomorphism-ring
attacks were not implemented, and the failed OpenRouter calls are not evidence
against them or against language models.
