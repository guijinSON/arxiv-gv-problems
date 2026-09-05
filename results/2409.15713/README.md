# Verified problem generator for arXiv:2409.15713

Status: **verified and hardened**. The generator passes every local gate, and the
shipping `easy` preset defeated all three valid calls in the required bare oracle
run. The structural-hint and placebo diagnostics also each finished at 0/3.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | other — a time-varying projective recurrence |
| Certificate | integer tuple — three exact barycentric lattice points |
| Intended intuition | change of variables via a moving-pole cross-ratio |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Gao, Roghani, Rubinstein, and Saberi, [*Hardness of Approximate
Sperner and Applications to Envy-Free Cake Cutting*](https://arxiv.org/abs/2409.15713).
Definitions 4, 7, and 9 give the simplex, Sperner boundary condition, and
trichromatic witness; Remark 10 identifies the two-dimensional case with ordinary
2D-Sperner.

The solver receives a dyadic lattice in the continuous 2-simplex and a compact
description of a valid three-color Sperner circuit. The circuit places one color in
the interior and the other two on opposite sides of a boundary transition. The
solver must return the three vertices of the elementary triangle crossing that
transition. `verify` checks the barycentric sums, adjacency template, circuit value,
and three distinct colors using exact integer arithmetic and never reads
`inst["answer"]`.

Generation composes identities. For moving poles `R(t)` and `R(t)+A`, the recurrence
is built so the cross-ratio

```text
u_t = (s_t - R(t) - A) / (s_t - R(t))  (mod P)
```

satisfies `u_(t+1)=Q*u_t`. A quadratic non-residue is chosen for `u_0` and a square
for `Q`, proving every denominator is nonzero. The terminal state and witness are
then carried through this identity; no simplex is searched.

## Why Track B

Theorem 15 proves PPAD-completeness for the paper's recursively constructed
**symmetric** circuits when `k=poly(n)` and the side length is `2^(-4kn)`; Section
7.4 gives the corresponding `2^(Omega(n))/poly(n,k)` black-box query lower bound.
That is worst-case evidence for a different distribution, so this module makes no
Track-A claim. The Introduction also identifies the easy boundary: finding only two
colors admits binary search, and Section 6 warns that exposed color switches create
easy spurious trichromatic regions.

An efficient algorithm is disclosed. Directly evaluating this instance's displayed,
time-varying Möbius recurrence takes `O(n)` field steps (`O(n log P)` counted
Euclidean/word operations). At shipping `n=250003`, seed 314159, it used 250,003
iterations, 28,470,558 counted exact operations, and about 0.65 seconds. The compact
cross-ratio route takes `O(log n + log P)` operations and at most 172 operations over
64 audited shipping seeds. The gap is what Track B measures: a machine runs the long
route easily, while a no-tool solver must discover the projective coordinate and
execute the short exact computation.

The earlier constant-affine prototype was rejected during Step 0: generic 2-by-2
matrix powering already solved it in `O(log n)`, so its alleged mechanical and
compact routes had comparable cost.

## Worked demo

`make_instance(n=7, bits=5, seed=0)` renders the following complete task. It is
hand-solvable: seven steps modulo 31 suffice even without noticing the cross-ratio.

```text
SUCCINCT TRICHROMATIC SPERNER TRIANGLE

The exact witness lattice in the continuous 2-simplex is
    D = {(x1,x2,x3): each xr >= 0 and x1+x2+x3 = M},
where M=32. Dividing all coordinates by M embeds D in the standard
triangle, and consecutive lattice points are exactly 1/M=2^-5
apart.  Color numbers and coordinate numbers are both 1-based.

A coloring is a Sperner coloring when a point may receive color r only if its
coordinate xr is positive.  The coloring below is specified by an exact
integer circuit with prime modulus P=31.  "mod P" always means the
canonical residue in 0,...,P-1.

Define
    R(t) = (28*t^2 + 12*t
            + 24) mod P.
Let A=2 and Q=8.  Start with
s_0=25.  For t=0,...,6, set

    s_(t+1) = R(t+1) + A*(s_t-R(t))
               * ((1-Q)*(s_t-R(t)) + Q*A)^(-1)  mod P.

Here z^(-1) is the unique multiplicative inverse of nonzero z modulo P;
the displayed denominators are guaranteed nonzero for this instance.  Reduce
every intermediate expression to its canonical residue.
Let T=1+s_7 (so 1 <= T <= P).  For x=(x1,x2,x3) in D:

  * if x3>0, set C(x)=3;
  * if x3=0 and x2<T, set C(x)=1;
  * if x3=0 and x2>=T, set C(x)=2.

This rule is a valid Sperner coloring: every returned color names a positive
coordinate.  Find the face-straddling elementary triangle at which all three
colors occur.  Your answer must be exactly three distinct rows [x1,x2,x3],
listed in lexicographically increasing order.  Two rows must be consecutive
points on the active face x3=0, and the third must be their unique adjacent
point with x3=1.  Equivalently, every pair of rows differs by at most 1 in
each coordinate.  Repetitions are forbidden and all bounds are inclusive.

Give your final answer inside <answer></answer> tags as one JSON 3-by-3 integer
matrix.  A syntax example (not necessarily a solution) is
<answer>[[0,0,32],[0,1,31],[1,0,31]]</answer>.
Output nothing else inside the tags.
```

The states are `25,16,16,24,12,10,2,3`, so `T=4` and the answer is
`[[28,3,1],[28,4,0],[29,3,0]]`.

```python
>>> verify(inst, [[28,3,1],[28,4,0],[29,3,0]])
(True, "ok")
>>> verify(inst, [[28,3,1],[28,3,1],[29,3,0]])
(False, "repeated_point")
```

## Difficulty presets

The lattice and answer stay fixed at 31-bit coordinates after `demo`; only the
mechanical circuit horizon grows.

| Preset | Horizon `n` | Field `P` | Minimum non-inversion step operations | Status |
|---|---:|---:|---:|---|
| demo | 7 | 31 | 133 | hand example |
| easy | 250,003 | 2,147,483,647 | 4,750,057 | **shipping; hardened 0/3** |
| medium | 1,000,003 | 2,147,483,647 | 19,000,057 | available |
| hard | 4,000,037 | 2,147,483,647 | 76,000,703 | available |

No preset was rejected or required escalation; `easy` held on its first hardening
round.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses and JSON round trips |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and Markdown |
| G4 | pass | 0/200,000 structured guesses; exact density `1/2,147,483,647` |
| G5 | pass | demo count 1/31; shipping count analytically 1; reference cost 28,470,558 ops, 0.494 s |
| G6 | pass | 6 attacks, each 0/8; direct evaluator 8/8 as expected |
| G7 | pass | doubled horizon verifies; mechanical lower bound doubles |
| G8 | pass | 140/140 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 79 chars, ~20 tokens, 9 atoms, at most 172 intended operations |

The failing attacks are endpoint/midpoint outliers, one-step greed, linear
extrapolation, frozen moving poles, a terminal-pole ansatz, and 256 random restarts.
The successful direct evaluator is reported separately as Track B requires.

## Oracle loop and G9 diagnostics

The bare run is the shipping evidence. Every parsed answer below was checked exactly;
none was a valid witness.

| Preset | Model | Seed | Solved | Why |
|---|---|---:|---:|---|
| easy | `openai/gpt-5.6-terra` | 1744330579 | no | parsed triangle was not trichromatic |
| easy | `google/gemini-3.8-flash` | 1816735196 | no | parsed triangle was not trichromatic |
| easy | `openai/gpt-5.6-terra` | 824369685 | no | parsed rows were not the required face-straddling unit triangle |

The separately run G9 arms were:

| Arm | Solved/attempts | Seeds | Verdict |
|---|---:|---|---|
| bare | 0/3 | 1744330579, 1816735196, 824369685 | hardened |
| structural hint | 0/3 | 712975997, 351453383, 904098605 | hardened |
| placebo hint | 0/3 | 1695835148, 802587053, 344804862 | hardened |

Thus `hinted - placebo = 0.0`: on this three-call diagnostic, naming the
cross-ratio invariant bought no measured success. This does not disprove the stated
change-of-variables intuition; it says that recognizing the coordinate is not, by
itself, enough to carry out the remaining exact modular arithmetic reliably without
tools. The answer is at most 79 characters (about 20 tokens), with 9 atomic elements,
and the intended compact route uses at most 172 counted exact operations.

## Use

```python
import json
import gen_2409_15713 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
text = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(text)
assert g.verify(inst, answer) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2409.15713
```

## Caveats

- The installed hardening harness recorded a two-model pool (OpenAI and Google),
  so the three calls used two distinct models rather than the four-vendor pool
  described in the task text. This passes the current script's pool-aware validator
  but is weaker evidence than a four-vendor run.
- The algebraic circuit carries most of the difficulty. The simplex, exact Sperner
  boundary rule, and trichromatic triangle are native and are checked, but this is
  not evidence that the paper's PPAD construction is hard on this distribution.
- With a genuine black-box oracle this monotone boundary coloring is easy by binary
  search; with a CAS or calculator the cross-ratio identity is also easy. This is
  intentionally a no-tool benchmark.
- `P(random guess)` is uniform over all face-straddling elementary triangles, the
  exact shape required by the statement. It does not model a solver whose prior
  already favors states derived from projective invariants.
- The panel does not include a symbolic-recurrence solver, program synthesis, or a
  computer-algebra system. Such tools are expected to solve the family.
- Definition 5 uses denominator `2^n-1` while Definitions 7 and 9 simultaneously
  impose distance `2^-n`; distinct points on that literal lattice cannot meet that
  bound. Following the paper's continuous construction in Sections 6–7, this module
  uses denominator `2^n`, so adjacent witnesses are exactly `2^-n` apart. This
  representational repair should be revisited if the paper is corrected.
