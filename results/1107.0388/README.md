# Compact certificates for the Masser chain

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | exact symbolic |
| Intended intuition | change of variables: undo a weighted Walsh mixing, expose a triangular difference-of-powers chain, and keep its geometric-series telescope factored |
| Domain essentiality | native (no reduction) |

## What this family asks

The source is Mats Andersson and Elizabeth Wulcan, [*Global effective versions of the Briançon–Skoda–Huneke theorem*](https://arxiv.org/abs/1107.0388). The solver receives an ordered list of multivariate polynomials `G_i` over `Q` and must give a compact exact specification of polynomials `Q_i` satisfying

`G_0 Q_0 + ... + G_(m-1) Q_(m-1) = 1`.

The underlying polynomials are precisely the triangular Nullstellensatz chain in Example 6.3, after an invertible weighted Walsh–Hadamard change of ideal generators and a variable relabelling. The submitted lists specify that change exactly. Verification rebuilds every displayed `G_i` by sparse integer coefficient arithmetic, checks the Walsh parameters, and executes the local monomial equalities that compose the difference-of-powers telescope. It uses neither floating point nor a probabilistic identity test, and it never reads the planted answer.

## Why Track B, and what is easy

Track A would be false. Section 1 explicitly treats polynomial ideal membership as an effective problem, gives Hermann's doubly-exponential general degree bound, and identifies the much easier Macaulay regime when the generators have no common zero even at infinity. Theorem A is the paper's global effective membership result. Example 6.3 is the regime used here: for its `m`-generator chain, any representation of `1` forces `deg(F_1 Q_1) >= d^m`, up to the displayed convention, and the example exhibits the role of codimension at infinity.

The reference route first recovers coefficient columns exactly and then performs successive elimination with expanded geometric sums. At the shipping setting `m=8,d=7`, it materializes 960,799 monomial terms: 1,921,598 counted integer multiply/add operations and 0.83 seconds in the measured self-test. That is easy for a symbolic program and not executable by hand. Once the structure is seen, Walsh orthogonality and seven local difference-of-powers identities give the compressed answer in 148 exact operations. The benchmark therefore tests discovery of the compression, not computational intractability.

## Worked demo (`seed=0`)

The complete default `render()` output, apart from line wrapping, is:

```text
Find a compact exact Nullstellensatz certificate.

Work in Q[x0,...,x1]. A monomial x0^e0*...*x1^e1 has the usual
nonnegative integer exponents. The ordered list has m=2, d=2:
G0 = 2 - 2*x0*x1 - 2*x0^2
G1 = -2 + 2*x0*x1 - 2*x0^2

Encode exact Q0,Q1 with G0*Q0+G1*Q1=1. Return six length-2 lists.
variables, row_codes, and column_codes permute [0,1]; row_signs and
column_signs use {-1,1}; weights use {1,2}. The last column code is 0
and the last column sign is 1. Indexing is zero-based and order matters.

H(r,c)=(-1)^popcount(r bitwise-AND c), and
A[i,j]=row_signs[i]*H(row_codes[i],column_codes[j])
       *column_signs[j]*weights[j].
With y=x_(variables[-1]), F0=x_(variables[0])^2 and
F1=x_(variables[0])*y-1, the certificate must make G_i=sum_j A[i,j]Fj.

Put T_r=x_(variables[r])*y^(2^(2-r-1)-1) and S_r=1+T_r. Define
q0=y^(2^2-2), q1=-S_0, and
Q_i=sum_j A[i,j]*qj/(2*weights[j]^2). Walsh orthogonality and
U^2-V^2=(U-V)(U+V) give G0*Q0+G1*Q1=1. The checker uses exact
integer coefficient comparisons and exact local telescoping relations.

Give the final answer inside <answer></answer> tags as one JSON object
with exactly the six named integer-list keys. Output nothing else in the tags.
Example: <answer>{"variables":[0,1],"row_codes":[0,1],
"column_codes":[1,0],"row_signs":[1,1],"column_signs":[1,1],
"weights":[1,1]}</answer>
```

The answer is:

```json
{"variables":[0,1],"row_codes":[0,1],"column_codes":[1,0],"row_signs":[-1,1],"column_signs":[1,1],"weights":[2,2]}
```

`verify(inst, answer)` returns `(True, "ok")`. Changing the first weight to `3` returns `(False, "weights entries must lie in 1..2")`. This smallest setting is genuinely hand-solvable: add and subtract the two displayed rows, then use `U^2-1=(U-1)(U+1)`.

## Difficulty ladder

| preset | m | d | max weight | status |
|---|---:|---:|---:|---|
| demo | 2 | 2 | 2 | hand example; not eligible to ship |
| easy | 4 | 3 | 3 | local gates pass |
| medium | 8 | 5 | 4 | local gates pass |
| hard | 8 | 7 | 5 | selected shipping preset; local gates pass |

Increasing `d` grows the expanded coefficient space while the six certificate lists stay fixed in length. Doubling `n` grows the chain from 8 to 16 and still builds and verifies.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verify; 12/12 JSON round trips |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered from surrounding prose; garbage returns `None` |
| G4 | 0 hits / 200,000 structure-aware samples; language size 104,877,313,228,800,000,000,000 |
| G5 | shipping density 0/200,000; demo exact count 2/128; reference 1,921,598 operations, 0.83 s |
| G6 | four no-tool attacks each 0/8; exact reference recovery 8/8 |
| G7 | doubled `m=16` instance verifies; expanded-operation count becomes 11,077,643,523,198 |
| G8 | 20/20 composed relabellings preserve the key and carried witness; 20/20 unrelated keys distinct |
| G9(c) | 249 characters, 63 estimated tokens, 48 atoms, 148 intended operations |

## Oracle loop and G9 arms

The required harness has been invoked twice, but the configured OpenRouter key currently returns HTTP 403 `Key limit exceeded (total limit)` before any oracle answer is scored. The script-owned transcript records those errors; they are not counted as model failures. These tables must be updated from successful harness-owned runs before submission.

| preset | seed | solved | reason |
|---|---:|---|---|
| easy | — | not scored | OpenRouter total-key quota blocked the pool |

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 | pending successful harness access |
| hinted | 0 / 0 | pending successful harness access |
| placebo | 0 / 0 | pending successful harness access |

The hinted-minus-placebo difference is not yet measurable. The structural hint names only the Walsh coefficient-column invariant; it does not give the recovery procedure.

## Use

```python
import gen_1107_0388 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
text = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit samples with `bash scripts/emit.sh 1107.0388 20` after the oracle evidence is complete.

## Caveats

The family becomes easy if the weighted Walsh columns or the triangular chain are recognized; that is intentional for Track B. The 0/200,000 density estimate concerns the declared syntax-aware prior, not a posterior that has already recovered coefficient signatures. The adversary panel tests row norms, a greedy chain with an unmixed-Walsh guess, 256 random restarts, and a direct unmixed ansatz. It does not test a general-purpose Gröbner implementation from a third-party CAS; instead the standard expanded elimination is implemented and counted directly because the shipping module must remain standard-library-only. `canonical_key` proves invariance under variable renaming, input reordering, and their composition; it does not try to decide arbitrary polynomial-ideal equivalence under every `GL_m(Q)` generator change. Finally, the oracle evidence is incomplete solely because of the external total-key quota, so this directory is not yet submit-ready.
