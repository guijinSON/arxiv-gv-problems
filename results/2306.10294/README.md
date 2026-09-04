# Verified generator for arXiv:2306.10294

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | exact linear algebra |
| Certificate | integer tuple `[p,t]` |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

This module instantiates Problem 1 (symmetric MinRank) from Couvreur, Mora, and
Tillich, [“A new approach based on quadratic forms to attack the McEliece
cryptosystem”](https://arxiv.org/abs/2306.10294). The solver receives a symmetric
matrix `A` over the prime field `F_p` and must find the unique scalar `t` for
which `A+tI` has rank exactly three. The answer is checked by exact modular
Gaussian elimination; no floating-point tolerance or stored answer is used.

## Why it can be trusted

Generation is inverse. It first samples `t`, a full-column-rank `n x 3` matrix
`U`, and three nonzero diagonal coefficients `c_i`. The last coefficient is
chosen so that

`R = U diag(c_1,c_2,c_3) U^T`

has trace zero. Thus `R` has rank three and setting `A=R-tI` gives the witness
before the public instance exists. For any other shift `s`, `A+sI` acts as the
nonzero scalar `s-t` on the `(n-3)`-dimensional kernel of `R`; because `n>=7`,
its rank is at least four. The witness is therefore unique. The checker first
uses a nonzero leading `4 x 4` minor to reject almost every wrong shift cheaply,
then computes exact rank for the remaining candidates.

## Why Track B, not Track A

Section 1, Problem 1 defines symmetric MinRank, while Section 4, Fact 1 exhibits
rank-three matrices arising from quadratic relations in odd characteristic.
The paper itself warns against a blanket hardness claim: Section 5 gives a
Pfaffian/Gröbner approach in characteristic two, and Sections 6.2–6.3 find
rank-defective pencil members by a determinant polynomial as part of a
polynomial-time attack. Section 6 attacks every square-distinguishable generic
alternant code after combining with the cited filtration, with the paper's own
restrictions for the Goppa subcase. Those are the easy regimes found at Step 0.

This planted distribution is easier still. Since the hidden residual has trace
zero, `trace(A)+n*t=0`, so the construction-aware reference solver returns
`t=-trace(A)/n mod p` in `O(n)` exact field operations. At shipping `n=192`, it
solved 8/8 instances in a median **0.00000828 s** using **193 counted
operations**. This is explicitly not structural or average-case MinRank
hardness. The Track B claim is only that a no-tool model must first notice the
unstated trace invariant and then accurately accumulate 192 ten-digit residues.

## Worked demo

The `demo` preset with seed 0 is hand-scale. This is its complete rendered
instance:

~~~text
RANK-THREE MEMBER OF A SYMMETRIC MATRIX PENCIL

Work in the prime field F_p, represented by integers 0,...,p-1 with every
addition, multiplication, inverse, and equality taken modulo p=101.

The input is a symmetric 7 by 7 matrix A. Let I be the
7 by 7 identity matrix. Find the unique field element t with
0 <= t < p for which A+tI has rank exactly 3 over F_p. Matrix rank means the
number of pivots under exact Gaussian elimination modulo p; it is not a
floating-point rank.

Only the upper triangle of A is listed. The line labelled i contains, in order,
A[i,i], A[i,i+1], ..., A[i,6]. Indices are 0-based. The omitted
lower triangle is fixed by A[j,i]=A[i,j]. There are no omitted choices, and the
instance is promised to have exactly one valid t.

Upper triangle of A:
  0: 100 16 73 39 84 76 10
  1: 25 65 52 7 78 65
  2: 74 25 93 14 31
  3: 72 98 28 70
  4: 15 87 27
  5: 96 72
  6: 83

Give your final answer inside <answer></answer> tags, as two comma-separated
base-10 integers: first the literal modulus p, then t. Do not use brackets.
Example format: <answer>101, 0</answer>
Output nothing else inside the tags.
~~~

The answer is `<answer>101, 49</answer>`.

~~~python
>>> verify(demo, [101, 49])
(True, 'ok')
>>> verify(demo, [101, 0])
(False, 'rank exceeds 3 (a leading 4x4 minor is nonzero)')
~~~

A person can solve the demo on paper by summing its seven diagonal entries
modulo 101 and using `t=-trace(A)/7`; rank three can then be checked by row
reduction. The exact brute-force enumerator also confirms one valid shift.

## Difficulty presets

| Preset | Dimension | Upper-triangle entries | Reference operations | Status |
|---|---:|---:|---:|---|
| demo | 7 | 28 | 8 | hand-solvable illustration |
| easy | 128 | 8,256 | 129 | rejected: structural hint solved 2/3 |
| medium | 192 | 18,528 | 193 | **ships; bare and hinted hardened** |
| hard | 256 | 32,896 | 257 | available, not needed |

The move from easy to medium is the single escalation allowed by G9(b). The
rejected easy hint transcript is retained as `g9_hinted_easy_transcript.jsonl`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset–seed plants verify; 12/12 JSON round trips |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | realistic fenced response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 uniform field shifts; exact probability `1/2147483647` |
| G5 | pass | shipping density 0/200,000; demo count 1; 4,096 restarts in 0.065469 s |
| G6 | pass | four attacks each 0/8; disclosed reference algorithm 8/8 |
| G7 | pass | doubled `n=384` builds and verifies; route cost grows 193 to 385 |
| G8 | pass | 80/80 symmetry and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted oracle 0/3; 23 chars, 6 tokens, 2 elements; 193 operations |

The failing G6 attacks were diagonal-mode outlier selection, a greedy leading
minor choice among diagonal shifts, 4,096 uniform random restarts, and the
in-context heuristic that extrapolates from only the first 12 diagonal entries.

## Oracle loop at the shipping preset

| Model | Seed | Solved | Exact outcome |
|---|---:|---|---|
| xAI Grok 4.6 | 726812181 | no | parsed `t=0`; nonzero leading `4 x 4` minor |
| Anthropic Claude Sonnet 5 | 824108218 | no | parsed `t=0`; nonzero leading `4 x 4` minor |
| OpenAI GPT-5.6 Terra | 953075 | no | parsed `t=0`; nonzero leading `4 x 4` minor |

The script-owned verdict is **hardened** with zero escalations in the final
shipping-only rerun. Full replies and timing are in `llm_loop_transcript.jsonl`.

## G9 arms

| Arm | Solved / attempts | Note |
|---|---:|---|
| bare | 0/3 | three parsed wrong shifts |
| structural hint | 0/3 | three parsed wrong trace computations; hardened |
| placebo hint | 0/3 | two parsed wrong shifts; one length-limited empty reply |

Hinted minus placebo is **0.0** at shipping size. The hint plainly contains the
right invariant, but this small diagnostic shows no benefit at `n=192`; the
remaining obstacle was exact arithmetic. At `n=128`, by contrast, the hint
produced 2/3 successes. The measured shipping answer is 23 characters (about
six tokens) and two atomic elements; the intended trace route is 193 exact
operations, within both G9 caps.

## Use

From this directory:

~~~python
from gen_2306_10294 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
candidate = parse_answer("<answer>2147483647, 123</answer>")
ok, reason = verify(inst, candidate)
~~~

From the repository root, emit deterministic samples with:

~~~bash
bash scripts/emit.sh 2306.10294 20
~~~

The module uses only the Python standard library. `gvlib` is unnecessary because
all arithmetic is over one prime field and the verifier carries its own small
modular rank routine.

## Caveats

- The trace solver is efficient, public, and successful 8/8. This family must
  never be cited as Track A hardness, a hard MinRank distribution, or evidence
  about Classic McEliece security.
- The family covers the paper's native symmetric MinRank Problem 1, not its full
  alternant/Goppa matrix-code distribution and not key recovery. No domain was
  discretised, but much of the paper's coding-theoretic structure is out of scope.
- `P(guess)` is uniform over the exact stated scalar language after fixing `p`.
  It says nothing about a solver informed by the trace-zero generator prior.
- The shipping prompt has 18,528 field entries (about 196,000 characters). The
  intended route touches only 192 diagonal entries, but model failures may partly
  measure locating and accumulating those entries. The 0/3 G9 arms are too small
  to separate recognition from exact-arithmetic reliability.
- General determinant-polynomial, Support Minors, Gröbner, and CAS attacks were
  not run in G6. The disclosed `O(n)` trace algorithm strictly dominates them on
  this distribution and already establishes that tool-equipped solving is easy.
- The canonical key uses `n`, `p`, `trace(A)`, and `trace(A^2)`. It is invariant
  under all tested coordinate permutations and sign changes but is not a complete
  canonical form for arbitrary finite-field orthogonal equivalence; rare invariant
  collisions are possible.
