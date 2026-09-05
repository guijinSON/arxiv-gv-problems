# CM-field Thue-equation generator (arXiv:1407.6556)

**Status:** the generator and local gates G1--G8 are complete, but this result is **not
yet shippable**.  The OpenRouter account exhausted its total spend limit after only
one of the three required bare `hard` attempts.  G9's hinted and placebo arms could
not be run.  The partial script-owned transcript is preserved; no missing oracle
result is inferred or fabricated.

| Profile field | Value |
|---|---|
| Track | **B** -- a mechanical algorithm exists and is measured |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | other (bounded integral equation search) |
| Certificate | ordered integer tuple `[x,y]` |
| Intuition | change of variables: detect a rank-two normalized-coefficient recurrence |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Aubry and Poulakis, [*Thue equations and CM-fields*](https://arxiv.org/abs/1407.6556).
The solver receives an integer homogeneous binary form (F(X,Y)), a nonzero integer
(b), and a box, and must return any integral point in the box with (F(x,y)=b).
The checker evaluates the displayed form at the submitted pair using exact integer
arithmetic.  It never reads the planted answer.

Generation first chooses an integral unimodular coordinate pair (U=L_0(X,Y)),
(V=L_1(X,Y)), a power of ten (s), and nonzero integers (u,v).  It constructs

\[
F(X,Y)=L_0(X,Y)^d+(sL_1(X,Y))^d,\qquad b=u^d+s^dv^d,
\]

then expands and shuffles the coefficients.  The planted point is obtained with the
integral inverse of the unimodular matrix.  For power-of-two (d\ge4), the diagonal
form is a scaled cyclotomic form Φ₂d, so a root generates the cyclotomic CM-field
\(\mathbb Q(\zeta_{2d})\); an invertible rational change of variables preserves the
root field.  This is the paper's native Theorem 1 setting with (K=\mathbb Q), not a
graph or finite-field surrogate.

## Why Track B

Theorem 1 in Section 2 gives finite polynomial-type height and solution-count bounds.
Section 5 gives `SOLVE-THUE-1`: enumerate admissible bounded-height ρ, derive candidate
coordinates, and check them.  The paper also explicitly notes exhaustive search when
the bounds are useful, and says number-field bounded-height/root-of-unity algorithms
exist while the remaining calculations can be done in MAGMA or MAPLE.  Therefore a
Track-A claim would be dishonest.

The executable reference here first recovers the two rational modes exactly, then
scans the feasible absolute (V)-coordinates.  It costs (O(V\log d)); at `hard` it
solves 8/8 instances in 1.176 seconds mean, with 227,611 iterations and 3,414,289
counted exact operations in the worst measured trial.  The compact route notices that
the binomial-normalized coefficients have Hankel rank two, solves the resulting
second-order recurrence, splits one exact radix, and applies a unimodular inverse.
That route solves 8/8 in 116 counted operations.  This million-versus-116 gap is the
Track-B claim.

## Worked demo

For `seed=3`, the full demo is

```text
d = 4
F(X,Y) = 10016 X^4 + 80096 X^3Y + 240216 X^2Y^2
         + 320216 XY^3 + 160081 Y^4
b = 11296
-15 <= x,y <= 15
```

One answer is `<answer>[9,-4]</answer>`.  `verify(inst, [9,-4])` returns
`(True, "ok")`; deleting one coordinate returns
`(False, "answer has 1 coordinate; expected 2")`.  A person can solve this demo on
paper by recognizing the fourth-power decomposition; exhaustive checking is also only
31² substitutions.

## Presets

| Preset | scan radius `n` | degree | shear bound | radix digits | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 4 | 1 | 1 | hand example; skipped by hardener |
| easy | 20,000 | 8 | 3 | 4 | oracle solved 1/3 |
| medium | 80,000 | 16 | 4 | 6 | oracle solved 1/3 |
| hard | 240,000 | 32 | 5 | 8 | intended shipping rung; bare evidence incomplete |

## Local gate results at `hard`

| Gate | Result |
|---|---|
| G1 | pass, 12/12 planted certificates; JSON round-trips |
| G2 | pass, five corruptions rejected for five distinct reasons |
| G3 | pass, realistic tagged/prose response round-trips |
| G4 | pass, 0 hits / 200,000 box-uniform candidates; sampled fraction 0 |
| G5 | pass, demo has exactly 4 valid pairs; hard reference worst cost 3,414,289 operations |
| G6 | pass locally, four attacks each 0/8; reference and compact routes each 8/8 |
| G7 | pass, doubled radius builds/verifies with the two-element answer unchanged |
| G8 | pass, 160/160 signed-variable-permutation invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **incomplete/fail**, 22 chars, 2 atoms, 116 operations fit caps; hinted oracle gate not run |

## Bare oracle loop (partial)

| Preset | Model / seed | Outcome | Reason |
|---|---|---|---|
| easy | GPT-5.6 Terra / 1632085921 | solved | verified witness |
| easy | Gemini 3.1 Pro / 1712194540 | failed | parsed pair had nonzero residual |
| easy | Claude Sonnet 5 / 431448776 | failed | empty length-limited response |
| medium | Claude Sonnet 5 / 1889844734 | failed | empty length-limited response |
| medium | Gemini 3.1 Pro / 1965445435 | failed | parsed pair had nonzero residual |
| medium | Grok 4.6 / 1794243540 | solved | verified witness |
| hard | Gemini 3.1 Pro / 1280282591 | failed | parsed pair had nonzero residual |
| hard | remaining slots | not run | OpenRouter HTTP 403: total key limit exhausted |

Transport-error rows, including a discarded incomplete Grok response and the 403
redraws, remain in `llm_loop_transcript.jsonl` as required and are not scored as model
failures.

## G9 arms

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare (`hard` only) | 0/1 | insufficient: two vendor attempts are missing |
| hinted | 0/0 | not run |
| placebo | 0/0 | not run |

The hinted-minus-placebo statistic is undefined.  The measured 1,000-seed worst case
is 24 characters (about 6 tokens) and has 2 atomic elements; an additional 5,000-seed
sweep found the same 24-character/6-token maximum.  The intended route uses 116 exact
operations, under the 300-operation cap.

## Use

```python
from gen_1407_6556 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

After a fresh OpenRouter budget completes the bare, hinted, and placebo runs, emit with

```bash
bash scripts/emit.sh 1407.6556 20
```

## Caveats

The 0/200,000 guess figure is a sampled upper-resolution result for uniform pairs in
the explicitly stated box; it is not a proof that the solution density is zero, and it
does not model a solver that has recovered the hidden coordinates.  The reference is
the strongest executable generic attack implemented here, but full `SOLVE-THUE-1`,
PARI/GP, Sage/MAGMA Thue solvers, lattice reduction, and a general binary-form Waring
decomposition package were not run.  The canonical key covers coefficient-row order
and all eight signed permutations of (X,Y), but not arbitrary `GL(2,Z)` equivalence;
computing a full binary-form equivalence normal form is outside this checker.  Most
importantly, one hard-preset oracle failure is not a hardness verdict: the missing two
bare attempts and all G9 arms must be completed before submission.
