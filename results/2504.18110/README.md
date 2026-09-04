# Exact Gram-dependence generator for arXiv:2504.18110

| profile axis | declaration |
|---|---|
| hardness track | **B — no-tool compression** |
| native domain | `geometry` |
| object regime | `rational_exact` |
| computational core | `linear_algebra` |
| certificate form | `matrix_certificate` |
| intended intuition | `invariant`: transport an equality of vector sums through pairwise generator changes |
| domain essentiality | `native` |
| reduction | none |

The solver receives an exact positive-semidefinite integer Gram matrix and must
return its unique primitive, sign-normalized integer null vector. A Gram matrix
records Euclidean inner products, so this is the paper's native geometry rather
than a graph encoding. Verification is just exact matrix-vector multiplication,
integer bounds, a gcd, and sign normalization. The source is Ge, Koolen, and
Munemasa, [“A 2-distance set with 277 points in the Euclidean space of dimension
23”](https://arxiv.org/abs/2504.18110).

## Why this family is trustworthy and hard in Track B's sense

Section 2, Lemma 2 states that vectors with Gram matrix
`[[nI,J],[J,nI]]` satisfy `sum(a_i)=sum(b_i)`; its proof computes the
squared norm of the difference as exactly zero. `make_instance` starts with
that known dependence, applies an independently sampled unimodular 2-by-2
recombination to every `(a_i,b_i)` pair, transports the two coefficients by the
inverse map, and finally relabels every vector. Thus the certificate exists
before the displayed matrix does; the generator never computes a nullspace.

This is deliberately not a Track A claim. Exact rational RREF solves every
instance in polynomial time. At the shipping preset, the instrumented reference
implementation used 261,006 exact arithmetic operations and about 0.09 seconds
on seed 314159; over eight seeds it averaged 262,924 operations and 0.089 seconds.
The compact route recognizes the pair invariant, recovers each pair's primitive
slice from local Gram norm `2(n-1)`, and aligns its sign against one anchor pair:
161 exact operations by the accounting used in G9. This is short enough once
seen, but the 64-by-64 elimination is not executable by hand in the evaluation
context.

The Step-0 distinction matters especially here. Theorem 1 explicitly gives the
headline extra point as `u=x_1+x_2+x_3-r`, and Section 2 explicitly gives the
switching root, so that construction cannot support Track A. Conversely,
Proposition 3 and Appendix A establish maximality by enumerating 16,689,170
short dual-lattice vectors; the paper reports 788.600 seconds and 4584.38 MB in
Magma. An explicit shortcut therefore does not justify rejecting the paper; it
motivates Track B. The easy unmixed form of Lemma 2 was avoided by mixing every
pair and randomly relabelling the vectors.

## Worked demo (`n=2`, seed 0)

This is the complete rendered instance; a person can solve its four equations
on paper.

```text
Exact dependence in a Euclidean Gram matrix

A Gram matrix K of vectors v_0,...,v_{m-1} is defined by
K[i,j] = <v_i,v_j>, their Euclidean inner product.  The symmetric integer
matrix below is promised to be positive semidefinite, to have a one-dimensional
nullspace, and therefore to describe m vectors with exactly one linear
dependence up to scale.  You need not construct coordinates.  A coefficient
vector c is a dependence exactly when Kc=0 over the integers, equivalently
sum_i c_i v_i is the zero vector.

Here m=4 and n=2.  The vector positions are 0-based.
For structural bookkeeping, the m positions are partitioned into the following
2 unordered pairs; pair order and order inside a pair are irrelevant:

2 3
0 1

The exact 4 by 4 Gram matrix K, one row per line, is:

6 3 2 -1
3 2 1 0
2 1 6 -3
-1 0 -3 2

Return the unique normalized dependence c.  It must contain exactly
4 integers, one for each position in matrix order.  Every
coefficient is in the inclusive interval [-3,3].
The coefficients are not all zero, their nonzero absolute values have greatest
common divisor 1, and the first nonzero coefficient is positive.  These rules
fix both scale and global sign.  Repeated coefficient values are allowed; vector
positions may not be omitted or reordered.

Give your final answer inside <answer></answer> tags as one JSON object with the
single key "coefficients" and an integer array of length 4.
Example format only: <answer>{"coefficients":[1,-1]}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"coefficients":[1,-2,1,2]}</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping its last
coefficient returns `(False, "wrong coefficient count: expected 4, got 3")`.

## Difficulty and gates

| preset | pairs `n` | matrix dimension | status |
|---|---:|---:|---|
| `demo` | 2 | 4 | hand-solvable illustration; skipped by hardening |
| `easy` | 32 | 64 | **shipping; hardened bare and hinted** |
| `medium` | 40 | 80 | construction and G1 pass; escalation not needed |
| `hard` | 48 | 96 | construction and G1 pass; escalation not needed |

| gate | measured result at shipping unless noted |
|---|---|
| G1 | 12/12 planted witnesses verified: 4 presets × 3 seeds |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with 5 distinct reasons |
| G3 | planted JSON object recovered through prose and a Markdown fence; JSON round-trip exact |
| G4 | 0/200,000 uniform structure-aware guesses; candidate language size has 179 bits |
| G5 | shipping density 0/200,000; demo exact count 1; RREF 261,006 operations in about 0.09 s |
| G6 | 0/8 successes for each of 5 attacks; reference RREF solved 8/8 as expected |
| G7 | doubled instance has dimension 128, verifies, and expands the language from 179 to 359 bits |
| G8 | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9 | hinted verdict `hardened`; 188 chars, about 47 tokens, 64 atomic elements, 161 intended operations |

The G6 attacks were a diagonal-median outlier rule, alternating public signs,
myopic row cancellation, 256 random restarts, and the stronger in-context rule
that gets every local pair slice right but does not align their global signs.

## Oracle loop and G9 arms

| bare oracle | seed | solved | exact grading result |
|---|---:|---|---|
| x-ai/grok-4.6 | 1138900853 | no | row 0 residual 31 |
| google/gemini-3.1-pro-preview | 241212074 | no | row 0 residual 6 |
| openai/gpt-5.6-terra | 246285590 | no | row 0 residual 23 |

| G9 arm | solved / scored attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

The hinted-minus-placebo solve-rate difference is `0.0`. The structural hint
bought no observed solves, so this small sample does not establish that the
claimed invariant wording helped; it only establishes the gated fact that the
hint did not break the family. One hinted and one placebo model exhausted the
32k completion budget without an answer; a placebo Grok call timed out and was
properly redrawn. All three bare models returned parseable witnesses that failed
exact verification, so the shipping hardness result itself is not a parser or
empty-response artifact.

## Use

```python
from gen_2504_18110 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit fresh verified shipping instances with:

```bash
bash scripts/emit.sh 2504.18110 20
```

## Caveats

This family is easy with a sandbox: exact RREF takes about a tenth of a second,
and a purpose-built decoder that uses the displayed pairs is faster still. It
tests no-tool recognition and exact execution, not computational complexity.
Revealing the sampled 2-by-2 transforms, leaving the original two blocks
unmixed, or reducing `n` makes the dependence immediate.

The 0/200,000 guess result concerns the declared uniform prior on primitive,
sign-normalized vectors in `[-3,3]^64`; it is not a bound for a model that uses
the Gram entries. The intended pair-and-anchor decoder succeeds by design and
is not misreported as a failing attack; RREF separately documents that an exact
algorithm succeeds. Numerical eigensolvers, LLL, and wider heuristic searches
were not run because exact nullspace elimination already dominates the problem
class. The canonical key is a strong invariant built from Gram row and entry
profiles, not a complete weighted-Gram isomorphism canon, so a
theoretical collision between nonisomorphic instances remains possible.
