# Disjoint transversal bases in an exact vector matroid

> **Build status:** the module and every local G1--G9(c) gate pass. The required
> four-vendor hardening evidence is currently blocked: all bare, structural-hint,
> and placebo calls received HTTP 403 `Key limit exceeded (total limit)` before
> inference. The script-owned error transcripts are retained and are not counted
> as model failures.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | exact rationals |
| Computational core | exact cover with exact linear independence |
| Certificate form | integer tuple (a naturally two-dimensional slot partition) |
| Intended intuition | change of variables: quotient out the common coordinate direction |
| Domain essentiality | **native** |
| Reduction | none |

## What the family is

[Bucić, Kwan, Pokrovskiy, and Sudakov, *Halfway to Rota's basis
conjecture* (arXiv:1810.07462)](https://arxiv.org/abs/1810.07462) considers
`n` given bases of a rank-`n` matroid. A transversal basis takes exactly one
distinguished element from each input basis; several such bases are disjoint
when they never reuse a colored input element. Theorem 1.1 proves that every
sufficiently large instance has `(1/2-epsilon)n` disjoint transversal bases.

This generator hands the solver the paper's own objects: `n` exact coordinate
bases in `Q^n`. It samples every vector coefficient first, then uses an affine
direction schedule to carry `k` known, disjoint transversal bases into the
instance. Thus generation is inverse and never solves its emitted instance.
The answer is a `k`-by-`n` matrix of zero-based slots. Checking disjointness is
linear in its size, and checking each selected basis is an exact determinant or
the equivalent exact sparse-rank calculation. `verify` never reads the planted
answer and accepts any valid canonical collection.

## Why this is Track B

This distribution is not claimed to be hard in the Track-A sense. Sections
2.1--2.3 of the paper already give a constructive sequence of simple swaps and
cascading swaps, and this generator has an even more direct polynomial
algorithm: inspect every coordinate to find the direction common to all
vectors, quotient it out, classify the remaining one-dimensional directions,
and cyclically factor the resulting incidence pattern. This reference method is
`O(n^3+kn)`. At shipping `n=18,k=6`, it solved 8/8 instances using exactly
**11,772** counted coordinate tests/lookups, averaging about **0.0024 s**.

The compact route notices directly that, modulo the common head direction,
each displayed row is an affine permutation of the unit directions. Following
the corresponding direction progression fills all six bases in at most
**152 exact arithmetic operations**. The mechanical method is trivial with a
sandbox but far beyond a hand calculation; the intended test is whether a
no-tool solver sees the quotient/affine invariant.

The easy regimes in the paper were recorded rather than hidden. Section 1 says
the full conjecture is known for strongly base-orderable and paving matroids,
for dimensions `p±1` in characteristic zero, and computationally through rank
four. Shipping uses rank 18, but its deliberately structured support pattern
still has the disclosed polynomial solver, hence Track B.

## Worked demo

For `make_instance(n=4, k=2, head_levels=2, seed=7)`, the complete rendered
instance is:

```text
Find disjoint transversal bases in an exact vector matroid.

Definitions.
All vectors lie in Q^4; all displayed coordinates are exact integers.
A list of n vectors is a basis exactly when its n-by-n coordinate
matrix has nonzero determinant over Q. There are n colored input bases
B_0,...,B_(n-1), each with slots 0,...,n-1. A transversal basis
chooses exactly one vector from every B_c and the chosen n vectors must
be a basis. Transversal bases are disjoint when no two choose the same
slot from the same B_c; equal coordinate vectors in different colors are
still distinct colored copies for this disjointness rule.

Here n=4. Find exactly k=2 pairwise disjoint transversal bases.
Vectors are listed as slot:[coordinate 0,...,coordinate n-1].
B_0: 0:[-2,0,0,1] | 1:[-2,0,1,0] | 2:[-2,1,0,0] | 3:[1,0,0,0]
B_1: 0:[-2,0,0,0] | 1:[-1,0,0,1] | 2:[-2,0,1,0] | 3:[-2,1,0,0]
B_2: 0:[2,1,0,0] | 1:[2,0,0,0] | 2:[-2,0,0,1] | 3:[-1,0,1,0]
B_3: 0:[-2,0,1,0] | 1:[2,1,0,0] | 2:[-2,0,0,0] | 3:[-2,0,0,1]

Required answer.
Return a JSON list of exactly k lists. Answer row t is transversal basis
t and must contain exactly n slot indices in color order: entry c selects
that slot of B_c. Indices are zero-based integers in [0,n-1]. Repeats
inside one color column are forbidden. The order of the k bases is
canonical: their selected slots from B_0 must be strictly increasing.
Any collection satisfying these rules and the exact basis tests is valid.

Give your final answer inside <answer></answer> tags as the JSON matrix.
Example format only: <answer>[[0,2,1,3],[1,3,0,2]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[2,2,2,2],[3,3,3,3]]</answer>`.
`verify` returns `(True, "ok")`. Replacing the second row by `[2,2,2,2]`
returns `(False, "transversal bases are not in canonical B_0-slot order")`.
This smallest preset is genuinely hand-solvable: both displayed constant-slot
selections visibly use all four coordinate directions.

## Difficulty presets

| Preset | `n` | `k` | head levels | answer atoms | intended operations | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 2 | 2 | 8 | 24 | hand-scale; hardening skips it |
| easy | 18 | 6 | 6 | 108 | 152 | ships locally; oracle run blocked |
| medium | 21 | 8 | 4 | 168 | 218 | reserve escalation rung |
| hard | 24 | 10 | 3 | 240 | 296 | reserve escalation rung |

No preset was rejected by a local gate. The named ladder grows both the ambient
matroid and requested collection, while `head_levels` crowds projective points.
After the hard rung, `escalate` first lowers the fixed-length head-level axis,
then grows the ambient rank through `(n,k)=(30,7)` and `(36,6)`: those answers
have 210 and 216 atoms, so the haystack grows without lengthening the 240-atom
hard witness. A further useful ambient increase would cross the 300-operation
no-tool cap, at which point `escalate` reports `cap_bound`.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 planted witnesses verify; every answer is JSON-native |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: realistic prose plus fenced JSON round-trips |
| G4 | pass: 0/200,000 structure-aware random candidates verify |
| G5 | pass: demo has 308 valid answers among 10,368 candidates; shipping density sample is 0/200,000; strongest failed attack ran 2,048 restarts in 0.872 s |
| G6 | pass: five attacks are each 0/8; the disclosed reference is 8/8 |
| G7 | pass: doubled `n=36`, fixed `k=6`, 1,296-vector instance builds and verifies |
| G8 | pass: 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass: measured 256-seed worst case 283 characters, about 71 tokens, 108 atoms, 152 intended operations |

The complete timing and count fields are in `selftest_report.json`.

## Oracle loop and G9 diagnostics

The configured key reached OpenRouter, but the account rejected every request
before any model ran. Errors are correctly excluded from solved/attempt counts.

| Arm | Preset | Seeds attempted | Scored solved/attempts | Result |
|---|---|---|---:|---|
| bare | easy | 1750949722, 1021536625, 1317433951, 975045978 | 0/0 | four HTTP 403 errors; no STEP-4 verdict |
| structural | easy | 1624444239, 1891825219, 614492422, 1682536810 | 0/0 | four HTTP 403 errors; hinted verdict unrun |
| placebo | easy | 684686697, 241398174, 192796606, 1056858830 | 0/0 | four HTTP 403 errors; no comparison |

`hinted - placebo` is recorded as the neutral placeholder `0.0` because both
denominators are zero; no conclusion about the structural hint is possible.
The hint names only the quotient invariant, not the recovery procedure.

## How to use it

```python
import gen_1810_07462 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
answer = gen.parse_answer(
    "Reasoning... <answer>[[2,2,2,2],[3,3,3,3]]</answer>"
)
assert gen.verify(inst, answer) == (True, "ok")
```

After OpenRouter quota is restored, rerun all three hardening arms and update
the recorded diagnostics. Once the bare run returns `hardened`, emit from the
repository root with:

```bash
bash scripts/emit.sh 1810.07462 20 easy
```

The module performs no file I/O, network access, or printing at import. It uses
`gvlib.exact_matrices` when available and has a standard-library Bareiss
determinant fallback.

## Caveats

- This is deliberately Track B. The quotient algorithm makes the distribution
  easy with tools, and neither the paper's existential theorem nor worst-case
  difficulty implies average-case hardness here.
- `0/200,000` samples uniformly from the exact bounded answer language after
  enforcing its visible shape, disjointness, and canonical ordering. It is an
  observed density, not a proof that the true probability is zero, and says
  nothing about priors biased toward the affine support pattern.
- The attack panel covers fixed columns, diagonal slots, coefficient magnitude,
  support size, and random restart. It does not implement the paper's full
  cascading-swap construction or an industrial CSP/ILP solver; the successful
  polynomial reference already establishes tool-easiness.
- The fast checker uses an exact rank characterization for generated
  `h e_0 + e_d` vectors. Its G8 transformation path falls back to a full exact
  determinant, which independently checks change-of-basis invariance.
- `canonical_key` is invariant under input reordering, slot reordering,
  projective scaling, and global `GL(n,Z)` coordinate changes. It keys on the
  strongest cheap projective-flat multiplicity invariant, not a complete
  represented-matroid isomorphism test, so rare non-isomorphic collisions can
  occur.
- Most importantly, the required no-tool oracle evidence is absent because of
  account quota. The local family is verified, but it must not be represented
  as hardened until the retained error-only transcripts are replaced by scored
  runs.
