# Missing-pair generator for arXiv:2104.09298

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | other (bounded Diophantine completion) |
| Certificate | strictly ordered integer pair (`integer_tuple`) |
| Intended intuition | invariant: a hidden first-power product equality exposes the missing sum |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The solver receives three integer pairs and one missing pair in

`(x1^5+x2^5)(x3^5+x4^5)=(y1^5+y2^5)(y3^5+y4^5)`

and must supply the two bounded missing coordinates in increasing order.  This
is the native Diophantine object of Choudhry and Couto,
[*A new diophantine equation involving fifth powers*](https://arxiv.org/abs/2104.09298),
not a graph or finite-field surrogate.  The checker independently substitutes
the candidate, computes four exact integer fifth-power sums, and compares the
two products; it never reads the planted answer.

Generation does not solve the completion.  Equations (2.26)--(2.27) are
evaluated at a seeded rational parameter, denominators are cleared, and the
known witness is carried through the independent signed cross-scalings of
(2.3), pair swaps, factor swaps, and a side swap.  Section 2.2 proves that these
coordinates satisfy both the fifth-power equation (1.1) and the first-power
analogue (2.8).  The demo instead uses the first explicit Section 3 solution,
embedded with `0^5+1^5=1`; the paper notes that this example also satisfies
(2.8).

## Why Track B

This paper supplies no hardness theorem, so Track A would be unsupported.  In
fact, (2.27) is an explicit parametric solution, and Section 2.3 says further
solutions can be computed with the elliptic-curve group law.  Merely asking for
any solution would therefore fail the hardness gate.  Section 2.1 also lists
trivial solutions, which the partial coordinates in this family rule out.

An efficient mechanical algorithm still exists for the generated completion:
compute the required fifth-power sum, scan `p=-B,...,B`, and test whether the
complement is an exact fifth power.  It uses `O(B)` candidate trials and `O(1)`
stored integers.  At the shipping preset `B=1,000,000`, the implementation
solved 8/8 instances, averaging 656,790 trials, 9,488,527 counted exact
operations, and 1.380 seconds locally.  That is the disclosed Track B baseline.

The compact route notices the extra equation
`(x1+x2)(x3+x4)=(y1+y2)(y3+y4)`, obtains the missing ordinary sum `s`, and uses

`p^5+q^5 = s^5 - 5s^3(pq) + 5s(pq)^2`

to recover the product `pq` and then the two quadratic roots.  The conservative
route budget is 96 exact operations.  The benchmark asks a no-tool model to
discover this invariant; it does not claim the million-step scan is unavailable
to ordinary software.

## Worked demo

This is the full rendered demo (seed 0):

```text
Complete an exact integer fifth-power product identity.

For an ordered pair (a,b), define F(a,b)=a^5+b^5, using ordinary integer
arithmetic (so a negative base has a negative fifth power).  Four pairs L1,
L2,R1,R2 must satisfy

  F(L1) * F(L2) = F(R1) * F(R2).

Exactly one pair is missing below:
  L1 = (-1, 8)
  L2 = (21, 25)
  R1 = (109, 213)
  R2 = (p, q)  [the missing pair]

Find the two missing integer coordinates p and q.  They must obey the inclusive
bound -1 <= p < q <= 1.  Thus the two coordinates
must be distinct and written in strictly increasing order.  The order of the
two entries inside each displayed known pair has no mathematical significance;
the p<q convention makes the requested output unique up to any genuinely
different representation of the same fifth-power sum.

Give your final answer inside <answer></answer> tags, as one JSON array [p,q]
of exactly two base-10 integers.
Example format only: <answer>[-1, 0]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[0, 1]</answer>`.  `verify(inst, [0, 1])` returns
`(True, "ok")`; the corrupted reversal `verify(inst, [1, 0])` returns
`(False, "coordinates must be in strictly increasing order")`.  A person can
solve this demo by hand: its complete structure-aware language has only the
three pairs `[-1,0]`, `[-1,1]`, and `[0,1]`.

## Difficulty presets

| preset | bound `B` | crowding | candidate pairs | status |
|---|---:|---:|---:|---|
| demo | 1 | 100% | 3 | hand example; skipped by harden.py |
| easy | 20,000 | 60% | 800,020,000 | first oracle rung |
| medium | 100,000 | 70% | 20,000,100,000 | local gates pass |
| hard | 1,000,000 | 80% | 2,000,001,000,000 | configured shipping preset; local gates pass |

`escalate()` doubles `B` and raises crowding while the witness remains exactly
two integers.  No preset has yet been accepted by the oracle pool because the
OpenRouter credential was exhausted before a scored call; “hard” is therefore
configured but **not yet oracle-verified for shipment**.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify across every preset |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged prose/fence/JSON round trip passes; answer is JSON-native |
| G4 | 0/200,000 structure-aware guesses; candidate space `2,000,001,000,000` |
| G5 | demo exact count 1/3; hard density 0/200,000; baseline 1.380 s / 656,790 trials / 9,488,527 operations |
| G6 | four attacks at 0/8 each; reference scan and compact route both 8/8 |
| G7 | doubled bound builds and verifies; candidate space grows by about 4x; answer stays two atoms |
| G8 | 100/100 key invariance and 100/100 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 17 serialized characters/tokens on the measured hard seed, 2 atoms, 96 operations; all caps pass |

## Oracle loop and G9 arms

The required scripts were invoked, but every OpenRouter request returned HTTP
403 `Key limit exceeded (total limit)`.  The harness correctly classified these
as errors, not model failures.  The script-owned transcripts are retained, but
they provide no hardness evidence and no `hardened`/`too_easy` verdict.

| run | preset | scored solved / attempts | unscored errors | result |
|---|---|---:|---:|---|
| bare ladder | easy | 0/0 | 4 | stopped: pool unreachable |
| structural hint | hard | 0/0 | 4 | diagnostic unavailable |
| placebo hint | hard | 0/0 | 4 | diagnostic unavailable |

Because both diagnostic denominators are zero, hinted-minus-placebo is recorded
as `0.0` only as a placeholder and supports no conclusion about the claimed
invariant.  The structural hint merely names the first-power parallel; it does
not give the Newton-sum procedure.  A funded key must rerun all three arms before
shipment.

## Use

```python
from gen_2104_09298 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, after a successful oracle rerun:

```bash
python3 results/2104.09298/gen_2104_09298.py
bash scripts/emit.sh 2104.09298 20 hard
```

## Caveats

This family is easy with ordinary integer software by design; its claim is only
Track B.  The 0/200,000 density estimate is uniform over every bounded strictly
increasing pair, which incorporates all shape, order, distinctness, and bound
constraints but not a language-model prior favoring algebraically related
numbers.  There are no decoys to compare with a plant.  The panel tried reuse of
a disclosed pair (including every position/magnitude choice), a greedy
single-fifth root, 256 random restarts, and balanced/consecutive/symmetric
ansatzes.  It did not try CAS factorization, modular sieving, or a
generator-aware lookup of the small rational-parameter pool; the latter could
exploit knowledge not present in the rendered statement and is the most
important remaining construction-specific attack.

The canonical key exactly handles swaps within known pairs, swaps of the two
factors on either side, swapping the sides of equality, and their tested
composition.  It does not canonicalize arbitrary Diophantine coincidences
between unrelated coordinate tuples.  Finally, the local gates establish exact
generation and verification, not no-tool hardness: that claim remains pending
until the required four-vendor loop produces scored attempts.
