# Coordinate certificates for arXiv:1407.4308

| profile axis | declaration |
|---|---|
| hardness track | **B — no-tool compression** |
| native domain | `algebra` |
| object regime | `finite_field` |
| computational core | `linear_algebra` |
| certificate form | `matrix_certificate` |
| intended intuition | `decomposition`: expose 3-coordinate blocks under a rank-one background and read their parity |
| domain essentiality | `native` |
| reduction | none |

The solver receives several binary bilinear forms `W_B(x,y)=x^T B y mod 2`.
Exactly one displayed `B` is invertible. The answer is its index and the exact
binary matrix `Q=B^-1`. Then `W_B(x,Qz)=x^Tz`, so `Q` transports the paper's
real PSD factorization of the inner-product communication matrix to the chosen
form. Verification is just exact multiplication over `GF(2)`. The source is
Lee, Wei, and de Wolf, [“Some upper and lower bounds on
PSD-rank”](https://arxiv.org/abs/1407.4308).

## Why it can be trusted, and why this is Track B

Section 2.1, Definition 1 fixes the trace-product definition of a PSD
factorization. Section 6.3 defines `IP_n(x,y)=x^Ty mod 2`; Theorems 50 and 51
give the upper bound, with Theorem 51 constructing a low-rank signed square
root and hence rank-one real PSD factors. The generator composes known
invertible `3x3` blocks into `D`, then publishes `B=D+11^T`. The matrix
determinant lemma over `GF(2)` says that `B` is invertible exactly when
`1^T D^-1 1=0`, and then

```text
(D + 11^T)^-1 = D^-1 + (D^-1 1)(1^T D^-1).
```

The generator samples that parity first, evaluates the identity only for the
plant, and carries the known inverse through independent row/column
permutations. It never eliminates a published candidate. Every decoy has the
opposite parity and is singular. Parity bits are uniform subject only to their
XOR; each allowed local block has five ones. Consequently, plant and decoys
have the same one-block marginals and exactly the same total zero count.

This is explicitly not Track A. Sequential Gauss–Jordan testing solves the
problem in `O(h*n^3)`. At provisional shipping `n=6, h=201`, it solved 8/8,
averaging 14,990 scalar XORs (maximum 24,552) and 0.020 seconds in the recorded
run. The compact route observes the complement-support components, reads one
bit from each block, XORs the two bits for every candidate, and inverts only
the unique even-parity candidate. Its conservative worst case is 300 exact bit
operations. The easy aligned regime to avoid is the paper's displayed `IP_n`
itself: once coordinates are exposed, Theorem 51 supplies the factorization.

## Worked demo (`n=3`, two candidates, seed 0)

A person can solve this smallest instance by ordinary row reduction over
`GF(2)`.

```text
Candidate 0:
0 1 1
0 0 1
0 1 0

Candidate 1:
1 0 1
1 0 0
0 1 0
```

The required answer is
`<answer>{"candidate":1,"matrix":[[0,1,0],[0,0,1],[1,1,0]]}</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Removing the final
entry of row 0 returns `(False, "wrong width in row 0: expected 3, got 2")`.
The full rendered problem additionally defines PSD factorization, indexing,
`GF(2)` arithmetic, and the exact JSON output contract.

## Difficulty presets and gates

| preset | `n` | candidates `h` | implicit matrices | answer atoms | status |
|---|---:|---:|---:|---:|---|
| `demo` | 3 | 2 | two `8x8` forms | 10 | hand-scale illustration |
| `easy` | 6 | 32 | 32 `64x64` forms | 37 | oracle rung; current run blocked by API quota |
| `medium` | 6 | 112 | 112 `64x64` forms | 37 | fixed-length escalation |
| `hard` | 6 | 201 | 201 `64x64` forms | 37 | provisional shipping preset |

An earlier one-candidate ladder at `n=9,12,15` was solved on all nine oracle
calls. It correctly ended at `cap_bound` because the `15x15` answer already
used 225 atoms. That failure motivated the current fixed-length decoy axis;
the superseded result is not used as evidence for this distribution.

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified and 12/12 instances had exactly one invertible candidate |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | JSON answer round-tripped through prose and a Markdown fence; JSON-native check passed |
| G4 | exact probability `1/(201*|GL(6,2)|) = 2.468e-13`; observed 0/200,000 structure-aware guesses |
| G5 | shipping density 0/200,000, exactly one valid answer, demo exact count 1; block-only near miss failed after 402 components |
| G6 | five attacks each scored 0/8; reference Gauss–Jordan candidate testing solved 8/8 |
| G7 | `n=12, h=201` instance built and verified; candidate-space bit length grew from 42 to 150 |
| G8 | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20 unrelated keys found in 23 seeds |
| G9(c) | 112 characters, about 28 tokens, 37 atoms, and 300 intended exact operations |

The G6 attacks are a row/column-profile outlier followed by greedy alignment,
greedy nearest-unit columns, transposition, 256 structure-aware random
restarts, and the in-context near miss that finds the right parity and `D^-1`
but omits the rank-one correction.

## Oracle loop and G9 diagnostics

The required rerun against the redesigned family was invoked, but the supplied
OpenRouter key had reached its total limit. All four retries were HTTP 403
errors, which the harness correctly refused to score. The stale `cap_bound`
field in `.meta.json` belongs to the superseded one-candidate run; the current
error transcript has no hardness verdict. This result is therefore **not
submission-ready** until a funded key reruns the bare arm.

| current bare call | preset | seed | result |
|---|---|---:|---|
| Terra retry 1 | `easy` | 1178489246 | HTTP 403; unscored |
| Terra retry 2 | `easy` | 469082548 | HTTP 403; unscored |
| Terra retry 3 | `easy` | 1867938261 | HTTP 403; unscored |
| Terra retry 4 | `easy` | 769126952 | HTTP 403; unscored |

| G9 arm at `hard` | solved / scored attempts | result |
|---|---:|---|
| bare | 0 / 0 | not reached after bare-loop quota failure |
| structural hint | 0 / 0 | four HTTP 403 retries; unscored |
| placebo hint | 0 / 0 | four HTTP 403 retries; unscored |

`hinted - placebo` is consequently not measurable. The structural hint names
only the block-parity invariant and does not reveal the inverse formula or a
sequence of steps. The size/effort part of G9 passes.

## Use

```python
from gen_1407_4308 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

After restoring OpenRouter quota, rerun the bare harness from this directory
and the two shipping-only wrappers from their scratch directories. From the
repository root, emission is:

```bash
bash scripts/emit.sh 1407.4308 20
```

## Caveats

With a sandbox this family is easy; it measures no-tool recognition and
execution, not computational complexity. The benchmark wrapper (one valid
bilinear form among singular forms) is new, although every object remains the
paper's native binary inner-product object and no discrete surrogate replaces
the mathematics. The returned witness is a coordinate transport, not the long
PSD-factor list itself; the paper's Theorem 51 is the fixed source factorization.

The 0/200,000 guess result applies only to the declared uniform prior over a
candidate index and `GL(6,2)`; it says nothing about a solver exploiting the
visible component parity. The 300-operation count includes exact bit
arithmetic after recognizing the decomposition but excludes visual comparisons
used to locate components. Numerical PSD-factorization, SAT/SMT encodings, and
alternative hand heuristics were not run because exact elimination already
solves the witness problem completely. The canonical key is complete for this
generator's component model and intentionally identifies candidate, row, and
column reorderings. Most importantly, no multi-vendor hardness or G9 diagnostic
claim can be made until the externally blocked calls are rerun successfully.
