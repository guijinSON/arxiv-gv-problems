# Low-rank infinity-norm approximation — parked Track B generator

**Status: `cap_bound`; parked, not shipped and not rejected.** Every local
G1–G9(c) gate passes, but the required bare oracle loop solved all three `easy`
instances, two of three `medium` instances, and all three `hard` instances. The
next size would exceed the 300-operation intended-route cap, so the harness returned
`cap_bound` exactly as prescribed for an answer-format limit.

| profile field | value |
|---|---|
| track | `B` |
| native domain | `logic` |
| object regime | `finite_discrete` |
| computational core | `linear_algebra` |
| certificate form | `integer_tuple` (a fixed-length binary string) |
| intended intuition | `change of variables` |
| domain essentiality | `licensed_reduction` |
| reduction | Section 3, Lemma 3 and Theorems 2–3 |

## Problem family

This module is based on Gillis and Shitov, [*Low-Rank Matrix Approximation in
the Infinity Norm*](https://arxiv.org/abs/1706.00078). A solver receives dense
GF(2) parity equations and the complete inline definition of their compilation
through the paper's NAE-3SAT oriented graph into a sparse signed matrix
`M(G,D)`. The requested binary string extends deterministically to a valid
two-colouring, a topological order, and exact rational rank-one factors whose
entrywise error is at most the stated rational threshold.

Generation is inverse: the module samples the answer first, computes every
right-hand side from it, compiles the resulting witness through the paper's
reduction, and never solves its own instance. `verify` does not read
`inst["answer"]`; it checks the equations, NAE extension, switched-graph
acyclicity, and the rational matrix inequalities by exact integer
cross-multiplication. The full matrix is represented sparsely by deterministic
rules, so its implicit zero entries are bounded in one exact calculation.

This is paper-licensed logic coverage, not native numerical-optimization
coverage: the search exposed to the solver is the NAE/parity preimage in the
paper's reduction, not free real factors for an arbitrary numerical matrix.

## Why Track B

Problem 1 in Section 2 gives the exact rank-one decision/search problem. Lemma 1
shows that a known sign pattern reduces it to linear inequalities. Corollary 1
makes nonnegative matrices polynomial-time, and Theorem 1 gives
`O(2^d mn(m+n)^3 log(mn))`, hence polynomial time when the threshold graph has
`d=O(log min(m,n))` components. Section 4.3 further reports that the proposed
block-coordinate method succeeds on all tested rank-one quantized instances.
Those results invalidate the original idea of simply rounding a planted
rank-one matrix.

The generator instead uses Section 3's reduction. Its signed matrices have only
diagonal entries above the threshold, so the threshold graph has the maximal
number of components—the regime used in the proof of Theorem 3's
NP-completeness result.

The generated distribution still has a disclosed efficient algorithm, so this
is Track B rather than a false distributional Track A claim. Exact Gaussian
elimination solves the displayed 58-variable, 66-equation shipping preset in
`O(R n^2)` bit operations. Across eight seeds it took a mean of 47,782 scalar bit
operations (maximum 54,575) and 0.00072 seconds in Python in the latest run. The compact route
notices that each dense row omits a triple. Complementing by the global parity
turns those triples into one cyclic 3-XOR system; a step-three recurrence and
inverse transform take 288 XORs. That fits the 300-operation cap, while carrying
out roughly 48,000 elimination operations without tools does not.

The former 26-bit prototype was not hard enough: its saved historical run in
`prior_attempt/` was solved at every tested level, including 2/3 solves at its
configured hard rung. The present ladder was therefore moved to the largest
size allowed by the compact-route cap. The fresh bare run still solved every
58-bit hard instance, leaving no compliant harder rung.

## Worked demo

`make_instance(n=8, decoys=0, seed=0)` renders the following complete problem:

```text
Certified rank-one approximation of a sparse signed matrix

XOR means addition modulo 2.  There are 8 base bits y0,...,y7.
Submit their values in exactly this displayed order:
  y0, y1, y2, y3, y4, y5, y6, y7

They must satisfy all 8 dense parity equations below.
For each row, XOR every base bit exactly once except the three named after
"omit"; that XOR must equal the displayed right-hand side. Braces denote an
unordered set and do not add another operation.
  e0: omit {y2, y4, y5}; XOR of all other base bits = 0
  e1: omit {y1, y3, y6}; XOR of all other base bits = 1
  e2: omit {y1, y6, y7}; XOR of all other base bits = 0
  e3: omit {y3, y4, y5}; XOR of all other base bits = 1
  e4: omit {y3, y5, y6}; XOR of all other base bits = 1
  e5: omit {y0, y2, y4}; XOR of all other base bits = 0
  e6: omit {y0, y1, y7}; XOR of all other base bits = 0
  e7: omit {y0, y2, y7}; XOR of all other base bits = 0

For completeness, these equations define an exact q-by-q signed integer matrix
M, q=818, by the following deterministic compilation. This is part of the
instance, so no knowledge of the source paper is assumed.

1. Process equations e0,e1,... in displayed order. Within each equation use
   its variables in increasing subscript order. Replace an XOR of
   a0,...,a(w-1), where w=5, by a left-associated chain of ternary
   XOR relations. Introduce fresh connector bits starting at y8:
   a0 XOR a1 XOR p0=0; for each t=1,...,w-4 add
   p(t-1) XOR a(t+1) XOR pt=0; and finish with
   p(last) XOR a(w-2) XOR a(w-1)=the displayed right-hand side. Fresh bits are
   numbered consecutively across equations. This produces 24 ternary XOR
   relations and 24 logical bits.
2. Introduce the fixed bit F=y24=0. For each ternary relation
   a XOR b XOR c=r, take the four forbidden triples (fa,fb,fc) whose XOR is not
   r, in lexicographic order. For each forbidden triple introduce one fresh
   gate bit g and the two NAE clauses
       NAE(L(a,fa), L(b,fb), +g),  NAE(-g, L(c,fc), +F),
   where L(y,0)=+y, L(y,1)=-y, +y has value y, -y has value 1-y, and NAE means
   that the three literal values are not all equal. Gate bits are consecutive
   after F. This gives 121 Boolean variables and 192 NAE clauses, in the order
   just specified.
3. From those clauses build the oriented graph and matrix. For every Boolean
   variable ya create vertices P(a)=2a and N(a)=2a+1. For clause ct and
   position h create O(t,h)=2*121+3t+h. Set M[i,i]=2. Set both entries between
   P(a),N(a) to -1. If clause position (t,h) is +ya, set both entries between
   O(t,h),N(a) to -1; for -ya use P(a). Finally direct the three-cycle
   O(t,0)->O(t,1)->O(t,2)->O(t,0), putting -1 in each forward matrix entry and
   +1 in its reverse. Every unassigned matrix entry is 0.

No pair receives conflicting rules. The threshold is the exact rational
k=802948799/535299200. The checker extends valid base bits through the XOR
chains and NAE gates, applies the matrix construction, reverses directed edges
whose endpoint bits differ, topologically orders the result, constructs
explicit rational vectors u,v, and checks exactly that
max(i,j) |M[i,j]-u[i]*v[j]| <= k. Thus the submitted bits are a compressed,
executable certificate for a rank-one approximation; no floating point is used.

The answer is one string of exactly 8 characters from {0,1}. Bit position 0 is
the value of the first displayed base variable, and so on. Order matters and
there are no separators.

Give your final answer inside <answer></answer> tags, as that binary string.
Example format only: <answer>01010101</answer>
Output nothing else inside the tags.
```

The answer is `<answer>11101111</answer>`.
`verify(inst, "11101111")` returns `(True, "ok")`; deleting its final bit
returns `(False, "bit string is too short: expected 8, got 7")`. A person can
solve the demo by elimination or by checking its 256 strings.

## Presets and gates

| preset | bits | extra rows | implicit matrix dimension | compact XORs | status |
|---|---:|---:|---:|---:|---|
| `demo` | 8 | 0 | 818 | 38 | hand-scale |
| `easy` | 46 | 5 | 71,086 | 228 | solved 3/3 by oracle pool |
| `medium` | 52 | 6 | 92,674 | 258 | solved 2/3; one failed answer |
| `hard` | 58 | 8 | 118,918 | 288 | solved 3/3; `cap_bound` |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses and 16/16 compilation identities passed |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged prose/Markdown round-trip passed; garbage returned `None` |
| G4 | 0/200,000 informed uniform guesses; exact language size `2^58` |
| G5 | demo exactly 1/256; shipping sample 0/200,000; reference cost above |
| G6 | six attacks at 0/8; bounded NAE-DPLL exhausted 128 nodes on 8/8; Gaussian elimination solved 8/8 as expected |
| G7 | `n=116` and fixed-answer crowding both built and verified |
| G8 | 80/80 invariant keys, 80/80 transported witnesses, 20/20 unrelated keys distinct |
| G9(c) | 60 JSON characters, 58 atomic bits, about 15 tokens, 288 intended XORs |

The latest full local self-test took about 227 seconds; G8 really verifies all
80 transformed large matrix certificates rather than merely comparing keys.

## Oracle loop and G9 diagnostic

The script-owned bare loop produced the following valid calls:

| preset | seed | model | solved | reason |
|---|---:|---|---:|---|
| `easy` | 2038487010 | `openai/gpt-5.6-terra` | yes | verified |
| `easy` | 1155813224 | `google/gemini-3.8-flash` | yes | verified |
| `easy` | 619143084 | `google/gemini-3.8-flash` | yes | verified |
| `medium` | 741782434 | `openai/gpt-5.6-terra` | no | parity equation violated |
| `medium` | 44937052 | `google/gemini-3.8-flash` | yes | verified |
| `medium` | 1983855070 | `openai/gpt-5.6-terra` | yes | verified |
| `hard` | 300734325 | `openai/gpt-5.6-terra` | yes | verified |
| `hard` | 1494713338 | `google/gemini-3.8-flash` | yes | verified |
| `hard` | 1754874556 | `openai/gpt-5.6-terra` | yes | verified |

The harness verdict is `cap_bound` after two escalations. The configured pool
contained the two models shown above; this is weaker vendor coverage than the
four-vendor protocol described in the task and is an additional caveat.

| G9 arm at `hard` | valid solves / attempts | conclusion |
|---|---:|---|
| bare | 3/3 | the shipping candidate is too easy |
| structural hint | 0/0 | not rerun after `cap_bound` |
| placebo hint | 0/0 | not rerun after `cap_bound` |

The older hint/placebo files contain only script-recorded HTTP 403 quota errors;
they are retained as provenance, not counted as attempts. `hinted - placebo` is
undefined. The answer is 60 JSON characters (58 atomic bits, about 15 tokens),
and the intended route takes 288 counted XOR operations.

## Use

```python
import gen_1706_00078 as gen

params = gen.DIFFICULTY["hard"]
inst = gen.make_instance(seed=123, **params)
question = gen.render(inst)
answer = gen.parse_answer(model_output)
ok, reason = gen.verify(inst, answer)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
```

The module remains useful for reproduction:
`python3 ../../scripts/harden.py gen_1706_00078.py` reruns the bare ladder from
this directory. Do not emit it into the shipping corpus under the present caps;
the authoritative verdict is `cap_bound`.

## Caveats

- The oracle pool available to this run listed only two models rather than four,
  and both solved the hard preset; no shipping claim is made.
- G4 samples uniformly from the exact 58-bit output language. Zero hits supports
  guess resistance under that prior only; it says nothing about a solver that
  detects the omitted-triple cycle.
- The bounded 128-node NAE-DPLL probe is not an industrial CDCL/XOR solver. The
  successful exact Gaussian solver is the appropriate reference algorithm for
  the displayed system and is disclosed rather than counted as a failed attack.
- The matrix is handed by an exact sparse construction rather than as a
  118,918-square literal array. The verifier checks all nonzero entries and uses
  a rigorous product maximum for every implicit zero.
- Adding redundant equations made the historical oracle task easier, so it is
  not used as an escalation axis. Increasing `n` beyond 58 would push the compact
  route over the 300-operation cap; `escalate` therefore returns `"cap_bound"`.
- The hint/placebo comparison is unmeasured because the specification directs a
  builder to park and stop once the bare hardening loop returns `cap_bound`.
