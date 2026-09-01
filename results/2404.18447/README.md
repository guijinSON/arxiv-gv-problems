# Finite-field PRODSAT core generator

This directory turns Lee, Macris, Ravelomanana, and Vantalon, [*The PRODSAT phase of random quantum satisfiability* (arXiv:2404.18447v2)](https://arxiv.org/abs/2404.18447) into an exact witness problem. The solver receives a connected square system of 3-local trilinear equations over `F_p`. It must give one projective single-qubit coordinate for every variable. A candidate is checked cheaply by substituting its coordinates into every eight-term equation modulo `p`; the checker accepts any common zero, not just the plant.

The module is deterministic from `(n, seed, p)`, uses only the Python standard library, samples the witness before the graph or tensors, and stores the plant only for generation tests. `verify` never reads it.

## Why this is the paper's problem, and why it is hard

Section 2.2 and Eq. (10) turn a product state into exactly these multiaffine local equations. Proposition 2.2 connects their solvability to a clause-covering dimer configuration. The generator uses the finite `N=M`, `k=3`, dimer-covered setting examined in Section 6: its factor graph is connected and 3-regular on both sides, and hence is entirely a nonempty 2-core with a perfect matching.

The easy regime had to be excluded. Section 2.1 and Appendix A give an `O(N)` transfer-matrix reconstruction when leaf removal empties the 2-core. Here no vertex is a leaf: all degrees are three. On a core, Section 4 uses Buchberger's algorithm; Appendix C records a doubly-exponential generic degree bound, and the Introduction says the actual algorithmic complexity of finding core solutions is open. Section 6 reports that even its square finite-size calculations are costly and stops at moderate sizes. General finite-field multivariate equation solving is also a standard hard search problem, but that worst-case fact is evidence rather than an average-case theorem for this particular planted distribution.

Complex amplitudes cannot be graded exactly from model text, so this implementation uses the paper's algebraic equations over an odd prime field and uses all of `P^1(F_p)`, including the point at infinity. Each local coefficient tensor is uniform in the seven-dimensional hyperplane annihilating the already-sampled local product vector. No tensor coordinate, graph edge, or coefficient magnitude marks the plant.

## Worked `small` example (`seed=0`)

The complete rendered instance is:

```text
Find a zero-energy product-state witness for this finite-field 3-QSAT core.

All arithmetic is in the prime field F_11: add and multiply modulo 11. Indices are 0-based.

There are 12 variables q[0],...,q[11]. Each variable is one projective point of P^1(F_11), encoded by exactly one integer in the inclusive range 0 through 11:
  q in 0,...,10 represents the nonzero two-vector v(q)=(1,q);
  q=11 represents the point at infinity v(q)=(0,1).
Vectors differing by a nonzero scalar represent the same point, which is why this encoding is canonical.

Each constraint lists three DISTINCT variable indices (a,b,c), in that order, and eight coefficients C000,C001,C010,C011,C100,C101,C110,C111 in that exact binary order. It is satisfied when
  sum over i,j,k in {0,1} of Cijk * v(q[a])[i] * v(q[b])[j] * v(q[c])[k] = 0 (mod 11).
All 12 constraints must be satisfied simultaneously. The factor graph is connected; every variable occurs in exactly three constraints and every constraint contains exactly three variables. Repeated q values are allowed, and the order of the 12 answer entries matters. Any satisfying witness is accepted.

Constraint data, one constraint per line:
0: vars 8 9 6 ; coeff 3 5 1 1 0 8 2 10
1: vars 2 3 11 ; coeff 1 5 6 4 3 10 0 3
2: vars 1 6 9 ; coeff 1 3 5 6 5 8 2 1
3: vars 3 4 10 ; coeff 2 9 6 10 10 6 8 6
4: vars 2 8 0 ; coeff 7 7 10 10 3 8 9 3
5: vars 7 0 11 ; coeff 2 5 5 0 8 2 4 9
6: vars 5 3 0 ; coeff 6 9 4 7 1 1 8 0
7: vars 7 9 10 ; coeff 3 2 0 4 0 7 5 2
8: vars 11 1 10 ; coeff 10 7 5 8 6 8 8 0
9: vars 7 4 5 ; coeff 10 8 9 1 6 3 4 8
10: vars 1 2 6 ; coeff 7 6 9 9 3 9 10 0
11: vars 5 8 4 ; coeff 4 8 7 4 5 1 7 4

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 12 integers, in variable-index order.
Example of the exact syntax (illustrates syntax only and normally is not a solution):
<answer>[0,0,0,0,0,0,0,0,0,0,0,0]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[6,6,0,4,8,7,6,4,7,5,9,3]</answer>`. `verify(inst, answer)` returns `(True, "ok")`. Dropping its last entry returns `(False, "answer has too few entries: expected 12, got 11")`.

## Difficulty presets

| preset | `n=m` | `p` | structure-aware candidate space | status |
|---|---:|---:|---:|---|
| `small` | 12 | 11 | `12^12 = 8,916,100,448,256` | **ships; all three oracles failed** |
| `standard` | 20 | 17 | `18^20 = 12,748,236,216,396,078,174,437,376` | fallback, not reached |
| `hard` | 30 | 29 | `30^30` | fallback, not reached |

`escalate` grows both the square core and the projective alphabet. No preset was rejected; the hardening loop stopped at its first held level as required.

## Gate results at the shipping preset

| gate | measured result |
|---|---|
| G1 | 9/9 plants verify (three presets times three seeds). |
| G2 | 5/5 corruptions rejected with five distinct reasons. |
| G3 | Tagged, fenced JSON with surrounding prose round-trips. |
| G4 | 0/200,000 uniform guesses from `(P^1(F_11))^12`; structured space `8,916,100,448,256`. |
| G5 | Exact small case: 17/46,656 assignments valid (`0.000364369`). |
| G6 | Local-slice outlier, greedy coordinate descent, and 64-restart min-conflicts each solved 0/8. |
| G7 | Doubling `n` from 12 to 24 verifies; candidate-space bit length grows 44 to 87. |
| G8 | 100/100 symmetry checks preserve both key and carried answer; unrelated keys are 20/20 distinct. |

## Oracle hardening loop

| preset | model | seed | result | exact reason |
|---|---|---:|---|---|
| `small` | Claude Sonnet 5 | 1543166915 | failed | Used all 32,000 completion tokens in reasoning and returned no content (`finish_reason=length`). |
| `small` | GPT-5.6 Terra | 413067525 | failed | Parsed `[0,1,...]`; constraint 3 had residue 10 modulo 11. |
| `small` | Gemini 3.1 Pro Preview | 531804392 | failed | Parsed a full proposed witness; constraint 0 had residue 4 modulo 11. |

The script-owned verdict is `hardened`, with zero escalations and `small` as `shipping_params`. The Claude result is weaker evidence than the two checkable wrong witnesses and is reported as such.

## Use

From this directory:

```python
import gen_2404_18447 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit a checked corpus with:

```bash
bash scripts/emit.sh 2404.18447 20 small
```

## Caveats

The paper's almost-sure theorems are over complex coefficients, whereas this generator is an exact finite-field analogue conditioned on a known root. The paper does **not** prove average-case hardness for this distribution, and general polynomial-system hardness does not prove that these sparse planted systems are hard. A new solver exploiting regular factor graphs, perfect matchings, finite-field geometry, or planting correlations could invalidate the hardness argument. The existence of a perfect matching is easy to detect; the claim is only that it does not directly reveal a common zero.

G4 is a statement about the uniform prior over every correctly shaped projective assignment. It rules out blind guessing under that prior, not a nonuniform algebraic attack. The adversary panel is cheap and does not include a full Gröbner/F4/F5 implementation, SAT/MQ encodings, belief propagation, tensor-network contraction, or spectral recovery. The shipping size is evidence against the tested LLM pool, not cryptographic security.

`canonical_key` is not a complete canonization of the coefficient-decorated tensor network. It combines exact graph trace/profile invariants with the square class of Cayley's local `2x2x2` hyperdeterminant, which is invariant under independent local `GL(2,p)` basis changes and nonzero rescaling of each equation. It can over-collapse nonisomorphic instances. Selftest covers clause order, variable numbering, tensor-axis order, local basis changes, equation rescaling, and their compositions, and observed 20/20 distinct unrelated keys.
