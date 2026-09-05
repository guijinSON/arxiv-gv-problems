# Generalized MinRank points from arXiv:1112.4411

The generator is a verified **Track B (no-tool compression)** family. The bare
oracle ladder hardened at the shipping preset. The required structural-hint and
placebo diagnostics were attempted afterward, but OpenRouter returned `403 Key
limit exceeded` on every redraw; those script-owned error transcripts are kept
rather than counted as model failures.

| Profile field | Value |
|---|---|
| Track | B -- an efficient reference algorithm exists |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | integer tuple (a native finite-field point) |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

Faugère, Safey El Din, and Spaenlehauer's [*On the Complexity of the
Generalized MinRank Problem*](https://arxiv.org/abs/1112.4411) asks for points
where a polynomial matrix over a field evaluates to rank at most a given bound.
This family hands the solver that native object: a `(d+1)` by `(d+1)` affine
polynomial matrix over a prime field, and asks for a point making its rank at
most 1. It uses `k=d^2=(n-r)(m-r)` in the paper's notation, hence the paper's
zero-dimensional parameter relation.

Generation samples a pairwise-distinct point `S` first. It then chooses a
random variable-to-cell assignment and random signs on Walsh characters and
constructs

```text
       [ H D (X-S)   0 ]
M(x) = [               ],
       [     0       1 ]
```

where `H` is the Walsh matrix and `D` is diagonal with entries `+1` or `-1`.
The isolated 1 implies `rank(M)=1+rank(H D (X-S))`; since `H D` is invertible
over every generated odd prime field, the planted point is the unique rank-at-
most-1 point. This is inverse generation, not solution by search.

Verification checks answer shape, canonical residues, and distinctness, then
substitutes exactly modulo the prime and checks the anchor 2-minors (equivalently
the exact rank condition). It never reads `inst["answer"]` and accepts every
witness satisfying the rendered problem.

## Why Track B

This is deliberately not a Track A claim. Section 6 of the paper forms the
`(r+1)`-minors, computes a grevlex Gröbner basis with F5, and converts it with
FGLM. Theorem 5 bounds this method for generic affine zero-dimensional inputs.
Sections 7.1--7.3 identify regimes where that arithmetic cost is polynomial in
the degree/output size, and Table 1 gives concrete FGb/Magma costs. The paper's
finite-field NP-completeness statement is worst-case and does not establish
hardness for this planted distribution.

On these intentionally nongeneric instances, the anchor minors are linear. The
strong reference algorithm extracts them, splits their incidence graph into
eight components, and applies exact modular Gaussian elimination. Its cost on
the measured shipping instance is 6,188 field operations and 0.031536 s
(`O(k^2)` on this generated `d`-block distribution); it solves 8/8 instances as
expected. The compact route recognizes the signed Walsh basis, shares butterfly
sums, and needs 278 exact arithmetic operations. Thus the mechanical route is
easy with a program but not realistic by hand, while the compact route fits the
300-operation cap if the solver discovers the basis change.

## Worked demo

For `make_instance(n=11, dimension=2, seed=11)`, the complete statement is:

```text
Generalized MinRank over a prime field

Work in the prime field F_11; every displayed integer is reduced modulo 11.
There are 4 variables x0,...,x3, numbered from 0.
The following is an affine 3 by 3 polynomial matrix M(x).
Entry (row,column) is shown below with both indices 0-based. A missing
variable has coefficient 0. Matrix rank means ordinary row rank over the field.
Find a point x in F_11^4 for which rank(M(x)) is at most
1. The required coordinates must be pairwise distinct.
Use canonical integer representatives 0 through 10, inclusive.

Matrix entries:
  (0,0) = 8 - x2 - x3
  (0,1) = 4 - x0 - x1
  (0,2) = 0
  (1,0) = 1 - x2 + x3
  (1,1) = 10 - x0 + x1
  (1,2) = 0
  (2,0) = 0
  (2,1) = 0
  (2,2) = 1

Give your final answer inside <answer></answer> tags, as one JSON list
of exactly 4 pairwise-distinct integers in x0,...,x3 order.
Example of the syntax only: <answer>[0, 1, 2, 3]</answer>
The example is not asserted to solve this instance. Output nothing else inside the tags.
```

The answer is `<answer>[7, 8, 10, 9]</answer>`.
`verify(inst, [7, 8, 10, 9])` returns `(True, "ok")`; dropping the last
coordinate returns `(False, "point must contain exactly 4 coordinates")`. A
person can solve this demo on paper by setting the four active entries to zero.

## Difficulty presets

| Preset | Field lower bound | `d` | Variables | Result |
|---|---:|---:|---:|---|
| demo | 11 | 2 | 4 | hand-solvable; skipped by hardener |
| easy | 1009 | 8 | 64 | defeated by Gemini in the original ladder |
| medium | 65521 | 8 | 64 | defeated by Gemini in the original ladder |
| **hard** | **655211** | **8** | **64** | **ships; all three oracle calls failed** |

The original 16-variable `F_1009` rung was also defeated and was dropped when
the ladder slid upward. Difficulty grows through the field size while the
answer remains 64 coordinates. `escalate()` continues that fixed-length axis up
to the largest supported prime that still respects the 2,000-character cap.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify across all current presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from surrounding prose/fence |
| G4 | pass | 0/200,000 structure-aware injective random points |
| G5 | pass | demo exact count 1/7,920; shipping sample 0/200,000; reference cost 6,188 ops / 0.031536 s |
| G6 | pass | four attacks at 0/8; reference elimination solves 8/8 |
| G7 | pass | field 655211 to 1310431 adds 64 candidate-space bits at fixed answer length |
| G8 | pass | 60 invariance + 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 510 chars, 64 atoms, about 128 tokens; compact route 278 ops |

The four failing attacks are a coefficient-support outlier guess, a
single-equation greedy guess, 256 structure-aware random restarts, and a
by-hand Walsh ansatz that ignores the hidden variable assignment and signs.

## Bare oracle loop

The current repository harness supplied two vendor models and made three calls
per level; `.meta.json` records that exact pool. A verified answer at any level
forced escalation.

| Preset / field | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| original easy / 1009, d=4 | 1567206985 | Gemini 3.8 Flash | solved | verified witness |
| original easy / 1009, d=4 | 102918762 | GPT-5.6 Terra | failed | rank at least 2 |
| original easy / 1009, d=4 | 1904473353 | Gemini 3.8 Flash | solved | verified witness |
| original medium / 1009, d=8 | 701196846 | Gemini 3.8 Flash | solved | verified witness |
| original medium / 1009, d=8 | 2061579252 | GPT-5.6 Terra | failed | rank at least 2 |
| original medium / 1009, d=8 | 324728615 | GPT-5.6 Terra | failed | rank at least 2 |
| original hard / 65521, d=8 | 53514140 | GPT-5.6 Terra | failed | rank at least 2 |
| original hard / 65521, d=8 | 1146825526 | Gemini 3.8 Flash | failed | rank at least 2 |
| original hard / 65521, d=8 | 501655072 | Gemini 3.8 Flash | solved | verified witness |
| **shipping / 655211, d=8** | **1690019051** | **GPT-5.6 Terra** | **failed** | rank at least 2 |
| **shipping / 655211, d=8** | **942383480** | **Gemini 3.8 Flash** | **failed** | rank at least 2 |
| **shipping / 655211, d=8** | **277080588** | **Gemini 3.8 Flash** | **failed** | empty length-limited response |

The harness verdict is `hardened` at shipping parameters
`{"n": 655211, "dimension": 8}`. The empty response counts as an unsolved
attempt under the harness policy, not an API error; the transcript preserves
its token-limit diagnostic.

## G9 diagnostic arms

| Arm | Solved / valid attempts | Status |
|---|---:|---|
| bare | 0 / 3 | measured from the held shipping level |
| structural hint | 0 / 0 | attempted; four redraws all returned HTTP 403 key-limit errors |
| placebo hint | 0 / 0 | attempted; four redraws all returned HTTP 403 key-limit errors |

`hinted - placebo` is therefore undefined, and no conclusion about hint value is
drawn. These arms are diagnostic rather than gating as of 2026-09-05; the
script-owned error rows are retained in `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl`. G9(c), the actual size/effort gate, passes with a
510-character, 64-element answer and a 278-operation intended route.

## Use

```python
import json
import gen_1112_4411 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
statement = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(wire)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit dataset records with:

```bash
bash scripts/emit.sh 1112.4411
```

## Caveats

- The matrices are deliberately nongeneric. Theorem 5 motivates the mechanical
  algebraic route but is not a hardness theorem for this distribution; the
  measured sparse linear solver is the honest Track B baseline.
- G4 samples uniformly from the explicitly stated injective-point language.
  Zero hits measure that prior, not computational hardness. Construction proves
  uniqueness; exhaustive enumeration confirms it only for the demo.
- The bare hardening pool exposed by the current harness had two vendors rather
  than the four described in the task text, and one held-level failure was an
  empty length-limited response. Both facts weaken the empirical claim and are
  visible in `.meta.json` and the transcript.
- The hint/placebo comparison is unavailable until OpenRouter quota is restored.
- No production F5/FGLM implementation was run because this specialization
  collapses exactly to sparse linear equations. Such tools are expected to solve
  it, as is the included reference algorithm.
- The attack panel does not cover every basis-learning or tensor-decomposition
  heuristic. Detecting the signed Walsh factors solves the family; that is the
  intended insight.
- `canonical_key` is exact for variable renaming and arbitrary row/column
  permutations. It is a strong cheap invariant, not a complete normal form under
  every invertible left/right matrix action, so it may miss more general
  rank-preserving equivalences or theoretically collide.
