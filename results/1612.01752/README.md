# Improving single swaps in weighted metric facility location

> **Completion status:** every gated check passes and the bare oracle loop hardened
> at `medium`. The non-gating hinted diagnostic stopped after 0/2 valid attempts
> when OpenRouter reached its account limit; the placebo diagnostic completed 0/3.

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | optimization |
| object regime | rational exact |
| computational core | polynomial identity |
| certificate | integer tuple: one close/open facility-ID pair |
| intuition | change of variables: recognize an affine cube modulo a prime |
| domain essentiality | licensed reduction |
| reduction kind/source | paper licensed / paper central |
| reduction | Section 3, Proposition 3 and Lemma 5 |

## What the family asks

The solver receives a compact, exact weighted metric uncapacitated facility-
location instance and a current open set. It must give one facility to close and
its closed complementary mate to open, strictly decreasing cost. The metric and
weights are exactly those in Brauer's [*Complexity of Single-Swap Heuristics for
Metric Facility Location and Related Problem*](https://arxiv.org/abs/1612.01752).
`verify` decodes the pair, evaluates one cubic modulo `p`, and compares the exact
integer clause-weight gain; it accepts any improving replacement and never reads
the planted answer. An independent evaluator that scales all rational costs by 3
and uses only integers agreed with it on all 169 replacements on each of 25 demo
seeds (4,225 checks total).

Generation is inverse, not search. The generator samples `a != 0` and `b`, knows
the unique index satisfying `(a*i+b)^3 = -1 (mod p)`, and only then publishes the
expanded cubic. Because `p = 2 mod 3`, cubing permutes the field. Balanced clauses
make the flip gain `2*s*(P(i)-(p-2))-1`, positive exactly at that index. Section 3
then carries this flip to the MUFL swap.

## Why Track B

The paper's Theorem 1 proves tight PLS-completeness for weighted MUFL/Swap, via
Proposition 3. That worst-case theorem is not asserted for this generated
distribution. Track A would therefore be false. A generic finite-field algorithm
solves every generated instance by computing `gcd(x^p-x, P(x)+1)`: it uses
`O(log p)` arithmetic on degree-3 polynomials. At shipping seed 4242 it used 32
polynomial multiplications, 872 counted exact operations and milliseconds. For
comparison, literal swap enumeration used 1,090,108 candidates and 14,171,404
operations. The compact route recognizes `(a*i+b)^3`, recovers the affine form,
and takes 62 operations. The benchmark is the 872-to-62 no-tool compression gap,
not computational hardness for a program.

The reduction requires client weights. Section 5 explicitly leaves unweighted
variants open; the generator does not claim that easier/unknown regime. It also
asks for one improving move, not the PSPACE-hard endpoint of a prescribed local-
search trajectory. Section 1.3 records a polynomial-time variant that requires a
minimum improvement per step and gives a slightly worse approximation ratio; this
family uses the paper's exact strict-improvement neighborhood instead.

## Worked demo (`n=11`, seed 0)

This smallest setting is hand-solvable: evaluate the eleven cubic residues (or
recognize the affine cube), locate the unique residue 10, then apply the ID map.

```text
Weighted metric facility-location single replacement

All arithmetic is exact. Put p=11 and d=4. There are V=p+2=
13 complementary facility pairs, indexed i=0,...,p-1,
then z (index p) and y (index p+1). There are F=2V=26
facility IDs, 0 through F-1.

For pair i, its positive logical token is 2i and its negative token is 2i+1.
A token q has displayed facility ID

    id(q)=(17*q+15) mod 26.

The multiplier is invertible modulo F, so this names every facility once. The
currently open set contains every negative facility id(2i+1); all positive
facilities id(2i) are closed.

This compact rule defines a complete weighted metric uncapacitated facility-
location (MUFL) instance. A literal point is both a possible facility and a
client. Each literal client has integer weight W=1223287183900.
Every facility has opening cost 2W=2446574367800. A literal client is at
distance 0 from its own facility, 1 from its complementary mate, and 2 from all
other literal facilities.

A clause client is specified by two literal facilities A,B and a positive
integer weight. It is at distance 4/3 from A and B, 5/3 from their complementary
mates, and 2 from every other literal facility. Distinct clause clients are at
distance 2. Repeated (A,B) pairs below denote distinct clients. These rules,
symmetry, and distance 0 at a point define the whole metric. The cost of an open
set is opening cost plus, for every client, its weight times the distance to its
nearest open facility.

The clause clients follow this exact rule. For each ordinary i=0,...,p-1, let

    t_i=(2*i^3+2*i^2+8*i+7) mod 11,

using the least residue 0,...,p-1. Put B0=278019742 and s=
58. For each bit j=0,...,d-1 create two clients. If bit j of t_i is
1, create (positive_i,z_positive) with weight B0+s*2^j and
(negative_i,z_positive) with weight B0. If the bit is 0, exchange those weights.
The high weights are:

    j=0:278019800, j=1:278019858, j=2:278019974, j=3:278020206

For every ordinary i also create (negative_i,z_positive) with threshold weight
C=175. Finally create guard client
(z_negative,y_positive) with weight L=12232871839. Thus there are
exactly M=100 clause clients. All indices are 0-based and all
displayed finite ranges include both endpoints.

Task: replace exactly one open facility by exactly one closed facility so that
the exact MUFL cost strictly decreases. The heavy literal clients imply that an
improving replacement must use one complementary pair. Order matters: output
the closed negative ID first and its newly opened positive mate second. IDs must
be distinct.

Give your final answer inside <answer></answer> tags, as two decimal integers
close_id, open_id. Example: <answer>7, 12</answer>
Output nothing else inside the tags.
```

Answer: `<answer>8, 17</answer>`. `verify(inst, [8, 17])` returns `(True, "ok")`;
`verify(inst, [8])` returns `(False, "answer is incomplete: open_id is missing")`.

## Difficulty presets

| preset | `n` | certificate candidates | status |
|---|---:|---:|---|
| demo | 11 | 13 | hand example |
| easy | 1,250,003 | 1,250,005 | rejected: 1/3 bare oracles solved |
| medium | 2,500,049 | 2,500,051 | **shipping; bare hardened 0/3** |
| hard | 5,000,081 | 5,000,083 | reserve escalation |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses plus 4,225 direct exact swap checks |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged answer round-trips through prose/fence |
| G4 | pass | 0/200,000 hits; exact density 3.9999184e-7 over 2,500,051 pair flips |
| G5 | pass | one exact answer; strongest baseline 32 polynomial multiplies / 872 ops / milliseconds |
| G6 | pass | five attacks each 0/8; Frobenius-gcd reference 8/8, max 878 ops |
| G7 | pass | escalated to `n=5,000,111`, same two answer atoms |
| G8 | pass | 20 ID/pair relabellings invariant and 20/20 unrelated keys distinct |
| G9 | pass | 17 chars, 2 atoms, 5 tokens, 62 route ops; hint arms are diagnostic only |

## Bare oracle loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | gpt-5.6-terra | 450305304 | failed | parsed swap had negative gain |
| easy | grok-4.6 | 43946511 | solved | valid witness; escalated |
| easy | gemini-3.1-pro | 244687231 | failed | parsed swap had negative gain |
| medium | grok-4.6 | 1353114506 | error | incomplete HTTP read; not counted |
| medium | gpt-5.6-terra | 1381163386 | failed | parsed swap had negative gain |
| medium | gemini-3.1-pro | 564212102 | failed | parsed swap had negative gain |
| medium | claude-sonnet-5 | 2060679634 | failed | empty length-limited response |

## G9 arms

| arm | solved / valid attempts | status |
|---|---:|---|
| bare | 0/3 | hardened at medium |
| structural hint | 0/2 | incomplete diagnostic: third slot hit the API limit |
| placebo | 0/3 | hardened at medium |

The observed hinted-minus-placebo difference is `0.0`, but only two valid hinted
attempts completed, so this is weak evidence. Naming the affine-cube invariant did
not help either completed oracle; the failures suggest exact modular execution,
not merely recognition, remains material. Since 2026-09-05 these arms are recorded
diagnostics and only the measured size/effort caps gate G9.

## Use

```python
from gen_1612_01752 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=42, **DIFFICULTY["medium"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1612.01752 20 medium
```

## Caveats

This is Track B: a CAS or a short program implementing finite-field factorization
makes the family easy, and the measured reference algorithm takes milliseconds.
The exact G4 density is for a uniform prior over already-deduced complementary
flips, not all open/closed ID pairs and not a symbolic solver's prior. The panel
did not run a general MILP/SMT package; Frobenius-gcd root isolation is a strictly
more targeted successful attack on this compact subfamily, while direct exact
cost checks cover every demo swap. The paper gives worst-case PLS hardness, not
average-case hardness for these inverse-generated cubics. Unweighted MUFL remains
outside the paper's result, and the hinted diagnostic has only two valid attempts
because the external API limit interrupted its third slot.
