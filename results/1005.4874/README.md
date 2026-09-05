# Quadratic-polarization witnesses for three-color CSP

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (the paper's color assignment) |
| Intended intuition | invariant: recognize polarized quadratic labels |
| Domain essentiality | native |
| Reduction | none |

This generator uses the literal, constraint, formula, and assignment objects in
Dominik Scheder's [*Using a Skewed Hamming Distance to Speed Up Deterministic
Local Search*](https://arxiv.org/abs/1005.4874). A solver receives a native
`(3,3)`-CSP: every displayed forbidden tuple is exactly one clause made from
literals `(x_i != c)`. It must return any satisfying three-color assignment.
`verify` checks the assignment's shape and evaluates every clause exactly; it
never reads the planted answer.

## Why this is Track B

Section 1 fixes the CSP definition. Section 2 gives the paper's recursive
Ball-CSP search, and Theorem 3.3 gives the directed-cycle deterministic bound;
for the displayed `(3,3)` regime it is about `2.077^n poly(n)`. That is an upper
bound, not evidence that a planted distribution is Track-A hard. This family
therefore makes the narrower Track-B claim and openly exposes the algorithm
that exists.

The required domain-standard reference is native finite-domain DPLL with
unit/functional propagation. It solves the promised shipping instance in five
nodes, 19,776 exact checks, and 0.0032 s; across eight seeds it solves 8/8 in 40
nodes, 177,760 checks, and 0.030 s. Its general worst case is exponential. A
second, guaranteed polynomial algorithm recognizes each block as a linear row
over `GF(3)` and applies dense exact Gaussian elimination in `O(B n^2)`. That
route used 622,510 scalar field operations and 0.064 s on the shipping
instance, and 5,000,741 operations/0.466 s across eight seeds.

The compact route is different. Labels are base-3 vectors and the block
constants are the polarization of `Q(v)=v_p v_q`. Affine terms cancel.
Basis-doubling blocks identify the constant, one exceptional basis-pair block
identifies `p,q`, and `Q(v)+c` is then a valid assignment. At shipping size this
requires at most 250 exact multiply/add/reduce or comparison operations. Even
the cheaper measured native reference therefore needs about 20,000 checks
against the compact route's 250 operations. The paper's bounded-radius method
is fixed-parameter tractable in radius, taking `(k(d-1))^r poly(n)` in Section 2;
this family supplies no small-radius promise. The generator also avoids a visible
triangular variable order (greedy propagation solved it) and a purely affine
label rule (the obvious ansatz would solve it). Variables and blocks are shuffled,
and the planted function always has a genuine cross term.

## Worked demo

With `seed=1`, the complete demo is:

```text
SATISFY A THREE-COLOR CSP

There are n=8 variables x0 through x7. Each color is 0, 1, or 2.
A literal (x_i != c) is true exactly when x_i is not color c.
A clause is an OR of its literals, and the formula is the AND of all clauses.

Clauses are displayed in blocks. If a block has scope [x_i,x_j,x_k],
a forbidden tuple abc denotes the clause
(x_i != a) OR (x_j != b) OR (x_k != c).
Thus every listed forbidden tuple is one ordinary CSP clause. Binary scopes
and two-digit tuples have the analogous meaning. Tuple order follows scope order.
All blocks and tuples are conjunctive; their displayed order has no meaning.

Each variable also has a distinct 2-digit base-3 label:
x0=20 x1=11 x2=12 x3=02 x4=01 x5=21 x6=22 x7=10

The 8 constraint blocks are:
B0 [x4,x3] forbid: 10 22 01 12 00 21
B1 [x7,x4,x1] forbid: 021 102 010 201 111 002 020 200 122 012 211 100 212 110 121 220 222 001
B2 [x5,x4,x0] forbid: 000 010 221 012 021 211 101 111 102 001 220 120 200 212 110 122 022 202
B3 [x7,x0] forbid: 01 00 10 22 12 21
B4 [x6,x5,x7] forbid: 222 001 202 121 200 011 120 210 012 110 112 022 102 000 211 101 020 221
B5 [x0,x6,x4] forbid: 122 220 101 202 212 102 012 120 111 001 000 021 211 110 200 010 221 022
B6 [x5,x4,x6] forbid: 220 100 221 022 212 021 101 122 210 000 011 111 202 010 120 201 112 002
B7 [x2,x4,x1] forbid: 102 212 222 011 200 221 022 121 020 010 002 120 111 201 100 001 112 210

Find any satisfying assignment as a JSON list of exactly 8 integers.
Entry i is the color of x_i; indexing is 0-based, order is fixed, and
only 0, 1, 2 are allowed. Repetitions are allowed.
Give your final answer inside <answer></answer> tags.
Example of syntax only: <answer>[0,0,0,0,0,0,0,0]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[1,0,2,0,2,1,1,1]</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last
entry returns `(False, "assignment is too short: got 7, expected 8")`.
There are nine valid demo assignments. A person can solve it on paper by
recognizing each block's linear relation and using the two-digit labels; it is
small enough to check all eight resulting colors directly.

## Difficulty presets

Measurements use `seed=20260905`; `medium` is the hardened shipping preset.

| Preset | n | blocks | native clauses | valid assignments | reference operations | rendered chars |
|---|---:|---:|---:|---:|---:|---:|
| demo | 8 | 8 | 120 | 9 | 5,157 | 1,731 |
| easy | 50 | 160 | 2,844 | 81 | 235,743 | 17,009 |
| **medium (ships)** | **80** | **320** | **5,712** | **81** | **622,510** | **33,115** |
| hard | 80 | 640 | 11,472 | 81 | 1,208,450 | 64,677 |

The current `easy` rung was solved by one of three bare oracles and was therefore
rejected. All three models failed `medium`, so the harness stopped there rather
than spending the larger `hard` rung. Escalation doubles the number of redundant,
same-distribution constraint blocks while keeping the 80-color witness and
250-operation compact route fixed.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | 12/12 tagged prose round trips; 12/12 JSON-native checks |
| G4 | pass | exact fraction `3^-76`; 0/200,000 structure-aware uniform assignments valid |
| G5 | pass | exactly 81 valid answers; DPLL 5 nodes/19,776 checks/0.0032 s; Gaussian 622,510 operations/0.064 s; all-affine attack 0/243 |
| G6 | pass | five attacks each 0/8; native DPLL and polynomial elimination both 8/8 as expected |
| G7 | pass | `n=160` builds; block escalation 320→640 keeps answer length fixed |
| G8 | pass | 80/80 invariant keys, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 161 chars, 41 estimated tokens, 80 atoms, 250 intended operations |

The five failing attacks are per-variable forbidden-tuple frequency, sequential
minimum-violation greedy, 256 uniform restarts, the by-hand digit-sum ansatz,
and exhaustive affine label functions. The successful GF(3) reference solver
is reported separately, as Track B requires.

## Oracle loop and G9 arms

The required bare harness used two providers and fresh seeds. `easy` was defeated
by one valid oracle answer; all three `medium` answers failed verification, so
the authoritative verdict is `hardened` at `medium` after one escalation.

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 357254191 | GPT-5.6 Terra | yes | valid witness |
| easy | 1778005085 | Gemini 3.8 Flash | no | no parseable tagged answer |
| easy | 987364346 | Gemini 3.8 Flash | no | empty length-limited response |
| medium | 2091100624 | GPT-5.6 Terra | no | tuple forbidden by block 2 |
| medium | 284554208 | Gemini 3.8 Flash | no | no parseable tagged answer |
| medium | 252737805 | GPT-5.6 Terra | no | tuple forbidden by block 1 |

| Arm | Solved/attempts | Errors | Conclusion |
|---|---:|---:|---|
| bare | 0/3 | 0 | hardened at the shipping parameters |
| structural | 1/3 | 0 | one model used the polarization information |
| placebo | 0/3 | 0 | no improvement from an information-free sentence |

`hinted - placebo = 1/3`. On this small diagnostic, the structural sentence
helped where a matched placebo did not, consistent with the intended difficulty
being discovery of the polarization invariant. The hint names only the invariant;
it does not give the recovery steps. The answer and route measurements are
161 characters, about 41 tokens, 80 atoms, and 250 operations.
The hinted scratch metadata says `cap_bound` only because its mandated one-rung
wrapper disables escalation after the solved attempt; the main bare metadata is
the authoritative `hardened` verdict at `medium`.

## Use

From the repository root:

```python
import importlib.util, json

path = "results/1005.4874/gen_1005_4874.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
text = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit records with `bash scripts/emit.sh 1005.4874 20 medium`. The module uses only
the Python standard library and performs no file I/O, network access, or import-time
printing.

## Caveats

- A CAS, SMT solver, or the included relation-recognition/Gaussian routine solves
  this promised family efficiently. That is the Track-B baseline, not a failed
  Track-A claim.
- The exact `3^-76` density is under uniform length-80 ternary assignments. It
  does not describe a solver that has recognized the quadratic invariant.
- The panel includes native DPLL/unit propagation and exact specialized
  Gaussian elimination, but not an external industrial SAT/SMT package;
  solver-specific preprocessing behavior remains unmeasured.
- `canonical_key` is invariant under the tested block/tuple reorderings, variable
  renamings, and independent cyclic color translations. It canonically records
  every block by its public base-3 label scope and omits only clause right sides,
  which are interchangeable under the declared per-variable color translations.
- The 33,115-character shipping statement is large. The answer and intended
  arithmetic remain within G9(c), but a future audit should distinguish failure
  to discover polarization from failure caused only by reading volume.
- The three-arm diagnostic has only three attempts per arm; `1/3` versus `0/3`
  is suggestive evidence about the invariant, not a precise effect estimate.
