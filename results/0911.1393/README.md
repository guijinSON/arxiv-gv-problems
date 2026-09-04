# arXiv 0911.1393 — weighted Pascal zero singular vectors

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate | matrix certificate: three bounded integer vectors |
| Intuition | invariant — a top finite-difference stencil annihilates every lower-degree polynomial row |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The solver receives a rational `1 x n x n` tensor through an exact formula for
its sole matrix slice `A`.  It must return nonzero integer vectors `u`, `v`, and
`w` for which all three partial tensor contractions vanish.  With `u=[1]`, this
is exactly `A w=0` and `v^T A=0`, plus the consequently zero scalar contraction.
The checker expands the stated binomial formulas and performs only exact integer
products, sums, bounds, and zero comparisons.  It accepts every normalized
witness in the bounded language, not just the planted one.

This is Problem 3.1 (tensor bilinear feasibility), equivalently the zero
singular-value case in Section 6, of Hillar and Lim,
[“Most tensor problems are NP-hard”](https://arxiv.org/abs/0911.1393).
The tensor is represented succinctly by the same kind of slice formula used in
the paper; no graph, finite field, or discrete surrogate replaces it.

Generation does not solve the emitted instance.  For `N=n-1`, it composes

`sum((-1)^j binom(N,j) p(j), j=0..N) = 0`

for every polynomial `p` of degree below `N` with a visible linear dependence
among the rows.  Nonzero column weights and independently shuffled row/column
coordinates carry the two known nullvectors through exact transformations.

## Why Track B, not Track A

Theorem 3.8 proves unrestricted tensor bilinear feasibility NP-hard, but it is a
worst-case theorem and says nothing about this generated distribution.  More
decisively, the chosen `1 x n x n` regime collapses to matrix nullspaces.  Exact
Gauss–Jordan elimination solves every instance in `O(n^3)` rational operations.
At shipping `n=84`, the instrumented baseline used 774,638 operations and 0.652
seconds; across eight seeds it averaged 817,020 operations and 0.781 seconds,
solving 8/8 as expected.

The compact route is to recognize the finite-difference invariant.  It forms
`w_j=(-1)^j binom(n-1,j)/d_j`, reads the visible final-row coefficients for
`v`, and undoes the coordinate orders.  That route takes 250 exact arithmetic
operations at `n=84`, still unsafe to execute unaided while typing an 84-entry
weighted stencil.  The Introduction’s linear/multilinear tractability boundary
and the Conclusion’s warning about fixed small dimensions identify the easy
regime; neither the paper’s NP-hardness theorem nor its doubly exponential
Gröbner-basis discussion is used as this family’s hardness claim.

## Worked demo

The `demo` preset is hand-solvable.  Its complete `seed=0` rendering (before the
standard output footer) is:

```text
ZERO SINGULAR VECTORS OF A RATIONAL 3-TENSOR

All indices below are 0-based.  For integers j,r, binom(j,r) is the binomial coefficient, with binom(j,r)=0 when r>j.

n = 3
Tensor shape = 1 x 3 x 3
combination_coefficients c[0..n-2] = [1,3]
column_weights d[0..n-1] = [1,1,1]
row_order = [0,1,2]
column_order = [0,1,2]
row_anchor = 0
column_anchor = 0
B = 9

These arrays define the tensor completely.  It has one n x n slice A. First define a base matrix M.  For 0 <= r <= n-2 and 0 <= j < n,
    M[r,j] = d[j] * binom(j,r).
For its final row,
    M[n-1,j] = d[j] * sum(c[r] * binom(j,r) for r=0..n-2).
The displayed tensor coordinates are
    A[i,j] = M[row_order[i], column_order[j]].
Every operation in these formulas is exact integer arithmetic.

Find three NONZERO integer vectors u, v, w for which 0 is a tensor singular value.  Here u has length 1 and v,w each have length n.  They must satisfy all three exact contraction conditions:
    sum(v[i]*A[i,j]*w[j] for i=0..n-1, j=0..n-1) = 0;
    u[0] * sum(A[i,j]*w[j] for j=0..n-1) = 0 for every i;
    u[0] * sum(v[i]*A[i,j] for i=0..n-1) = 0 for every j.
Use the projective normalization u[0]=1, v[row_anchor]=1, and w[column_anchor]=1.  Every coordinate must be a base-10 integer in the inclusive interval [-B,B].  Vector order matters; repeated coordinate values are allowed.

Give your final answer inside <answer></answer> tags as one JSON array [u,v,w] of the three integer arrays.
Example: <answer>[[1],[1,2,-1],[1,-2,1]]</answer>
Output nothing else inside the tags.
```

The answer is `[[1],[1,3,-1],[1,-2,1]]`; `verify` returns `(True, "ok")`.
Dropping the final coordinate of `w` returns
`(False, "w has wrong length: expected 3, got 2")`.

## Difficulty and gates

| preset | n | status |
|---|---:|---|
| demo | 3 | hand example; exact enumeration finds one witness |
| easy | 48 | rejected by oracle gate: 2/3 solved |
| medium | 66 | rejected by oracle gate: 1/3 solved |
| hard | 84 | **ships**; 0/3 solved |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; all JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trips through prose and a Markdown fence |
| G4 | 0/200,000 valid guesses; bounded anchored language is 13,359 bits |
| G5 | shipping density 0/200,000; demo exact count 1; baseline 774,638 ops / 0.652 s |
| G6 | four attacks each 0/8; reference exact elimination 8/8 |
| G7 | `n=168` builds and its planted witness verifies; cubic cost ratio 8 |
| G8 | 100/100 key invariances, 100/100 carried witnesses, 20/20 unrelated keys distinct |
| G9 | hinted level hardened; worst of 1,000 seeds was 1,947 chars / 487 estimated tokens; 169 atoms, 250 route ops |

## Oracle loop

API errors do not count below.  Grok timed out twice on the hard bare rung and
was redrawn.  Terra’s hard bare reply gave the correct symbolic formula but no
concrete tagged witness, so this is a genuine witness/output failure rather than
a parser miss.

| preset | model | seed | solved | result |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 313210543 | no | left contraction nonzero |
| easy | Gemini 3.1 Pro | 1012338524 | yes | verified |
| easy | GPT-5.6-terra | 93150030 | yes | verified |
| medium | Claude Sonnet 5 | 974231440 | yes | verified |
| medium | GPT-5.6-terra | 1004592564 | no | right contraction nonzero |
| medium | Gemini 3.1 Pro | 886548125 | no | wrong vector length |
| hard | Claude Sonnet 5 | 1469426714 | no | empty length-limited response |
| hard | GPT-5.6-terra | 2029025376 | no | formula only; no tagged concrete vector |
| hard | Gemini 3.1 Pro | 189531843 | no | right contraction nonzero |

## G9 arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping hard rung held |
| structural hint | 0 / 3 | polarity-flipped gate passed |
| placebo hint | 0 / 3 | diagnostic control held |

Hinted minus placebo is `0.0`.  The supplied finite-difference hint bought this
pool no measured success, so this run does not establish that hint discovery is
the separating skill; arithmetic execution and transcription remain plausible
bottlenecks.  Across 1,000 shipping seeds, the largest answer was 1,947
characters / 487 estimated tokens; answers have 169 atomic elements, and the
route uses 250 exact operations.

## Use

From this directory:

```python
import gen_0911_1393 as gen

inst = gen.make_instance(**gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY], seed=7)
statement = gen.render(inst)
answer = gen.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 0911.1393 20
```

## Caveats

- This is deliberately an easy matrix-shaped specialization, not evidence of
  distributional NP-hardness.  A sandbox or CAS solves it quickly by exact
  elimination; that is the declared Track B reference algorithm.
- The 0/200,000 guess rate uses the exact stated prior: all bounded integer
  coordinates with the three anchors fixed.  It does not model a solver that
  has recognized the finite-difference stencil, at which point the witness is
  unique and deterministic.
- The tensor formula openly supplies the row-combination coefficients and
  coordinate orders.  Difficulty comes from producing the weighted order-83
  stencil exactly, not from discovering hidden instance data.
- I did not test floating-point SVD, modular nullspace reconstruction, or a
  specialized finite-difference recognizer.  Exact Gauss–Jordan is stronger for
  correctness but not necessarily fastest.  The generic attacks are diagnostic,
  not a claim that no other shortcut exists.
- The canonical key is exact for this generator’s row/column relabellings and
  second/third tensor-mode swap, and passed all carried-witness tests.  It uses the construction normal form
  `(n,c,d)`, not a complete canonical form for arbitrary weighted-matrix
  isomorphism, so an exotic collision between different normal forms is not
  ruled out.
- Claude’s decisive bare and hinted failures exhausted the 32,000-token response
  budget, while Grok timeouts were excluded.  Thus some oracle evidence includes
  budget exhaustion; the successful smaller rungs and the exact local baseline
  should be read alongside it.
