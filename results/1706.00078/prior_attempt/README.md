# Low-rank infinity-norm approximation — parked Track B prototype

**Status: not shippable.** The generator and exact checker pass G1–G9(c), but the
script-owned bare oracle loop solved every tested level and ended
`budget_bound`. The paper is therefore parked, not rejected: `SHIPPING_DIFFICULTY`
is only the configured local test preset, not a level that held against the pool.

| profile field | value |
|---|---|
| track | `B` |
| native domain | `logic` |
| object regime | `finite_discrete` |
| computational core | `linear_algebra` |
| certificate form | `exact_symbolic` binary string |
| intuition | `change of variables` |
| domain essentiality | `licensed_reduction` |
| reduction | Section 3, Lemma 3 and Theorem 2 |

## What the family is

This prototype uses Gillis and Shitov, [*Low-Rank Matrix Approximation in the
Infinity Norm*](https://arxiv.org/abs/1706.00078). The solver receives dense
GF(2) parity equations and a deterministic inline compilation of them into the
paper's NAE-3SAT oriented graph and signed matrix `M(G,D)`. It must return the
base bits. The checker expands those bits through ternary-XOR and NAE gates,
switches the directed graph, topologically orders it, constructs rational
rank-one factors, and checks the infinity-norm bound with `Fraction` arithmetic.
It never reads `inst["answer"]`.

Generation is inverse: sample the answer first, define each right-hand side from
it, then carry the witness through the paper's reduction. For even `n` not
divisible by three, the hidden cyclic backbone is nonsingular. Seed-dependent
extra missing triples make the support hypergraph genuinely diverse; RHS values
are correctly omitted from `canonical_key` because signed-variable
complementation transports them.

## Why Track B, and why it did not ship

The paper's Theorem 3 proves NP-completeness for rank-one infinity-norm
approximation. Theorem 1 simultaneously identifies the easy cases that must be
avoided: a known sign pattern gives linear feasibility, `M >= 0` is polynomial,
and only `O(log n)` components in the threshold graph is polynomial. Section 4.3
also reports that rank-one quantized instances are easy in practice, so the
triage proposal was not used. The Section 3 matrices here have only diagonal
entries above the threshold and hence the maximum component count.

This distribution nevertheless has a disclosed efficient algorithm. Exact
GF(2) Gaussian elimination solves the 26-variable, 32-equation configured hard
preset in `O(R*n^2)` scalar bit operations: 8/8 instances, 8,123 mean bit
operations and 0.00030 s mean in the saved final self-test. The intended shortcut
notices that each equation omits a triple. With `S = XOR_j z_j`, the involution
`x_i = z_i XOR S` converts the missing triples to a cyclic 3-XOR system; a
step-three recurrence and inverse transform use 128 exact XORs.

That is a real mechanical/compact gap, so Track B was the right track. It was not
hard enough for the evaluated models: every named rung was defeated, as were
fixed-length escalations through 52 extra equations. Near-cap 56- and 58-bit
follow-up sweeps could not be completed after the shared key exhausted its total
quota. This evidence is not a `hardened` verdict and must not be presented as one.

## Worked demo

`make_instance(n=8, decoys=0, seed=0)` has these seed-dependent equations:

```text
Certified rank-one approximation of a sparse signed matrix

XOR means addition modulo 2.  There are 8 base bits y0,...,y7.
Submit their values in exactly this displayed order:
  y0, y1, y2, y3, y4, y5, y6, y7

They must satisfy all 8 dense parity equations below.
  e0: y0 XOR y1 XOR y3 XOR y6 XOR y7 = 0
  e1: y0 XOR y2 XOR y4 XOR y5 XOR y7 = 1
  e2: y0 XOR y2 XOR y3 XOR y4 XOR y5 = 0
  e3: y0 XOR y1 XOR y2 XOR y6 XOR y7 = 1
  e4: y0 XOR y1 XOR y2 XOR y4 XOR y7 = 1
  e5: y1 XOR y3 XOR y5 XOR y6 XOR y7 = 0
  e6: y2 XOR y3 XOR y4 XOR y5 XOR y6 = 0
  e7: y1 XOR y3 XOR y4 XOR y5 XOR y6 = 0

For completeness, these equations define an exact q-by-q signed integer matrix
M, q=818, by the following deterministic compilation.

1. Process equations in displayed order and variables in increasing subscript
   order. Replace each five-way XOR by a left-associated chain of ternary XOR
   relations, introducing fresh connector bits from y8 onward. This produces
   24 ternary relations and 24 logical bits.
2. Introduce F=y24=0. For each a XOR b XOR c=r and each forbidden triple
   (fa,fb,fc) whose XOR is not r, introduce a fresh gate g and clauses
   NAE(L(a,fa),L(b,fb),+g) and NAE(-g,L(c,fc),+F), where L(y,0)=+y,
   L(y,1)=-y, and NAE means not all three literal values are equal. This gives
   121 Boolean variables and 192 NAE clauses.
3. Create vertices P(a)=2a and N(a)=2a+1 for every Boolean variable, and
   O(t,h)=2*121+3t+h for clause position h. Put 2 on the matrix diagonal; put
   symmetric -1 entries between P(a),N(a) and between each occurrence vertex
   and the vertex for the opposite literal; orient every clause three-cycle,
   putting -1 forward and +1 backward. Every other matrix entry is 0.

The exact threshold is k=802948799/535299200. Submit one 8-character binary
string in y0,...,y7 order.

Give your final answer inside <answer></answer> tags.
Example format only: <answer>01010101</answer>
Output nothing else inside the tags.
```

The answer is `<answer>11101111</answer>`.
`verify(inst, "11101111")` returns `(True, "ok")`; dropping the last bit returns
`(False, "bit string is too short: expected 8, got 7")`. A person can solve the
demo on paper by elimination or by checking its 256 possible strings.

## Difficulty and gates

| preset | base bits | extra equations | candidate space | status |
|---|---:|---:|---:|---|
| `demo` | 8 | 0 | 256 | hand-scale |
| `easy` | 14 | 2 | 16,384 | oracle solved 3/3 |
| `medium` | 20 | 4 | 1,048,576 | oracle solved 3/3 |
| `hard` | 26 | 6 | 67,108,864 | oracle solved 2/3; configured only |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses and 16/16 compilation identities passed |
| G2 | 5/5 corruptions rejected with distinct reasons |
| G3 | tagged prose/Markdown round-trip passed; garbage returned `None` |
| G4 | 0/200,000 informed uniform guesses; exact language size `2^26` |
| G5 | demo exactly 1/256; shipping sample 0/200,000; Gaussian cost above |
| G6 | six attacks 0/8; NAE-DPLL exhausted 128 nodes on 8/8; Gaussian 8/8 |
| G7 | `n=52` and fixed-answer crowding both built and verified |
| G8 | 80/80 invariant keys, 80/80 transported witnesses, 20/20 distinct seeds |
| G9(c) | 28 characters, 26 atomic bits, about 7 tokens, 128 intended XORs |

## Bare oracle loop

| round | parameters | solved / attempts | outcome |
|---:|---|---:|---|
| 0 | `n=14, decoys=2` | 3/3 | escalated |
| 1 | `n=20, decoys=4` | 3/3 | escalated |
| 2 | `n=26, decoys=6` | 2/3 | escalated |
| 3 | `n=26, decoys=19` | 3/3 | escalated |
| 4 | `n=26, decoys=32` | 2/3 | escalated |
| 5 | `n=26, decoys=45` | 3/3 | escalated |
| 6 | `n=26, decoys=52` | 2/3 | `budget_bound` |

The full per-model seeds and replies are in `llm_loop_transcript.jsonl`. The
transcripts explicitly show models deriving the global-XOR transformation; the
failures are not parser false negatives.

## G9 arms

| arm | solved / valid attempts | result |
|---|---:|---|
| bare hard preset | 2/3 | defeated |
| structural hint | 0/0 | provider quota exhausted; four errors recorded |
| placebo hint | 0/0 | provider quota exhausted; four errors recorded |

`hinted - placebo` is not measurable. The saved arm transcripts contain only API
errors and are not counted as model failures. The size/effort caps still pass.

## Use the retained prototype

```python
import gen_1706_00078 as gen

params = gen.DIFFICULTY["hard"]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
answer = gen.parse_answer(model_output)
ok, reason = gen.verify(inst, answer)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
```

If a future rerun obtains a genuinely `hardened` level, emit from the repository
root with `bash scripts/emit.sh 1706.00078 20`. Do not emit the current parked
prototype.

## Caveats

- This is a paper-licensed logic reduction, not native numerical-optimization
  coverage; the solver manipulates parity equations, not floating-point factors.
- Zero G4 hits estimates only the uniform prior over exact 26-bit strings. It
  says nothing about a model that recognizes complements of triples—which the
  transcript shows is the relevant prior.
- More redundant equations made the oracle task easier, not harder. They remain
  useful for canonical diversity but are not a hardness axis.
- The bounded dependency-free DPLL attack is not an industrial CDCL/XOR solver.
  The successful Gaussian reference is the appropriate standard algorithm for
  the displayed linear system.
- The exact checker validates sparse nonzero entries and bounds all implicit
  zeros by an exact product maximum; it does not materialize the full matrix.
- The rank-two quantized regime in Section 4.3 is empirically difficult for the
  paper's heuristic, but the paper gives no distributional hardness theorem for
  it, and a full useful factor witness breaches this benchmark's output/effort
  caps. That unexplored regime is why the paper is parked rather than rejected.
