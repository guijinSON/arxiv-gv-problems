# Multiset resolving sets from affine parity cycles

> **Build status:** the generator and all local G1--G9(c) gates pass at the
> provisional `hard` preset. The required oracle evidence is incomplete: `easy`
> and `medium` were each solved 3/3, then OpenRouter exhausted the key's total
> limit before `hard` received a scored attempt. Accordingly, this directory is
> not ready to submit and makes no claim that `hard` has been hardened.

| Profile field | Value |
|---|---|
| Track | **B -- no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT inside the paper's graph reduction |
| Certificate form | exact symbolic fixed-width hexadecimal word |
| Intended intuition | change of variables: cancel adjacent affine windows |
| Domain essentiality | licensed reduction |
| Reduction | Section 3, Theorem 3.1 and Claims 3.2--3.4; paper-central 3-SAT-to-Multiset-Dimension reduction |

## What the family is

[Hakanen and Yero, *Complexity and Equivalency of Multiset Dimension and
ID-colorings* (arXiv:2303.06986)](https://arxiv.org/abs/2303.06986) defines a
vertex's multiset representation as the unordered multiset of its distances to
a selected vertex set. The solver receives an exact, compact specification of a
connected graph made from the paper's variable and clause gadgets and must find
a canonical vertex set whose representations distinguish every graph vertex.

Generation is inverse. It samples the answer bits first, evaluates equations
`x_i XOR x_(i+d) XOR x_(i+2d) = b_i` around a non-unit affine cycle, expands each
equation into four 3-CNF clause gadgets excluding its false rows, and carries the
sampled assignment to Claim 3.3's set: every `e^1`, every clause gadget's `g^1`,
and one `a^1`/`b^1` truth vertex per variable. The generator never solves the
instance it emits.

Verification is exact. A candidate word fixes the full concrete vertex set. Each
parity row is evaluated with Boolean XOR; a false row means one clause gadget is
false and the proof gives the explicit unresolved pair `c^1,c^3`. If all rows
hold, Claim 3.3's distance identities and the validated pairwise-distinct path
lengths certify every other pair. `verify` never reads `inst["answer"]`. The
self-test also materializes each 1,890-vertex demo graph and recomputes all
distance multisets by BFS.

## Why Track B

Theorem 3.1 proves general Multiset Dimension NP-complete, but that worst-case
result does not make this structured distribution Track A. An efficient method
is disclosed and measured: Gauss--Jordan elimination over GF(2), `O(n^3)`. At
the provisional shipping preset `n=53`, eight seeds averaged **24,025 counted
scalar operations** and about **0.0026 seconds**. Clause-level DPLL also solved
8/8, averaging 68,495 literal inspections, 4.5 nodes, and 0.049 seconds.

The compact route notices that adjacent affine-window equations cancel to
`x_i XOR x_(i+3d) = b_i XOR b_(i+d)`. Since `3` and `n` are coprime, this is one
cycle. Traverse it once from an arbitrary first bit and use one original row to
choose between the result and its complement. The conservative worst-case count
is **273 exact XOR/index operations**. This is a Track-B claim about mechanical
work versus a compact change of variables, not average-case or cryptographic
hardness. The oracle results below show that the first two rungs did not create a
large enough no-tool gap.

The paper's easier construction regimes were deliberately avoided. Proposition
4.2 and Theorem 4.4 display constant-size resolving sets for king grids;
Theorem 5.1 and Corollary 5.2 give a whole-copy witness for suitable strong
products with `K_2`. Their certificate-producing formulas are already the
compact route, so they provide no useful mechanical/compact gap.

## Worked demo

For `make_instance(n=5, copies=1, seed=7)`, the complete rendered problem is:

```text
Find a multiset resolving set in the connected graph defined below.

Definitions (all indices and bounds are exact).
The graph is finite, simple and undirected. The distance d(u,v) is the
number of edges in a shortest u-v path. For a vertex set W, the multiset
representation of u is the unordered multiset {{d(u,w): w in W}}, including
0 when u belongs to W. W is multiset resolving if every two distinct graph
vertices have different multiset representations.

Variable gadgets (r is zero-based).
For each r=0,...,4, make vertices T_r,F_r,a_r^1,a_r^2,b_r^1,b_r^2,
d_r^1,...,d_r^t,e_r^1,e_r^2, where t=5(r+2). Add edges
  a_r^1--b_r^1, a_r^2--b_r^2,
  T_r--a_r^1, T_r--a_r^2, F_r--b_r^1, F_r--b_r^2,
  T_r--d_r^1, F_r--d_r^1, d_r^i--d_r^(i+1) for 1<=i<t,
  d_r^t--e_r^1 and d_r^t--e_r^2.

Parity rows and clause gadgets.
Each row has a tail-block h, ordered triple (u,v,w), bit b and four slot
patterns. It denotes x_u XOR x_v XOR x_w=b. For every copy c=0,...,C-1
and slot a with pattern p=(p0,p1,p2), make a clause gadget Q=(h,c,a).
Its literals are +x_u if p0=0 and -x_u if p0=1, and likewise for v,p1
and w,p2. The clause is false exactly at p; the four slots are precisely
the patterns whose parity differs from b.
Q has vertices c_Q^1,c_Q^2,c_Q^3,f_Q^1,...,f_Q^s,g_Q^1,g_Q^2, where
j=4(C*h+c)+a and s=5(n+j+2). Add edges c_Q^1--c_Q^2--c_Q^3,
c_Q^2--f_Q^1, f_Q^i--f_Q^(i+1) for 1<=i<s, and f_Q^s--g_Q^1,g_Q^2.
For every Q connect c_Q^1 to both T_r,F_r for every r. Connect c_Q^3 to
both T_r,F_r when x_r is absent; only F_r when +x_r occurs; and only T_r
when -x_r occurs. There are no other edges.
Here n=5, C=1, so there are 20 clause gadgets.
Rows are presented independently of h; triple order fixes slot coordinates.
  h=2: (0,2,4) b=1 slots=000,110,101,011
  h=3: (1,3,0) b=1 slots=000,110,101,011
  h=1: (2,4,1) b=0 slots=100,010,001,111
  h=4: (3,0,2) b=0 slots=100,010,001,111
  h=0: (4,1,3) b=0 slots=100,010,001,111

Required witness.
Return one hexadecimal word z of exactly 2 digits and value below 2^5.
Leading zeroes are required. Bit r of z (bit 0 is least-significant) defines
  W(z) = {e_r^1 for every r} union {g_Q^1 for every clause gadget Q}
         union {a_r^1 if bit r is 1, otherwise b_r^1, for every r}.
Thus W(z) has exactly 30 vertices. Find any z for which
W(z) is multiset resolving. Hexadecimal letter case is ignored on input.

Give your final answer inside <answer></answer> tags as exactly the required
2 hexadecimal digits, without a 0x prefix.
Example format only: <answer>07</answer>
Output nothing else inside the tags.
```

The answer is `<answer>12</answer>`. `verify(inst, "12")` returns
`(True, "ok")`; `verify(inst, "00")` returns `(False, "clause block h=2
leaves c^1 and c^3 with identical multiset-distance representations")`. A
person can solve this demo by checking 32 words or by using the five-row cycle.

## Difficulty presets

| Preset | `n` | copies per parity row | Clause gadgets | Implicit graph vertices | Compact operations | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 1 | 20 | 1,890 | 33 | hand-scale illustration; hardening skips it |
| easy | 29 | 1 | 116 | 54,462 | 153 | solved 3/3 by the oracle pool |
| medium | 41 | 2 | 328 | 345,138 | 213 | solved 3/3 by the oracle pool |
| hard | 53 | 4 | 848 | 2,040,924 | 273 | provisional candidate; 0 scored attempts because quota expired |

`n` enlarges the unique-witness language. `copies` enlarges the paper graph but
only duplicates logical clauses, so it is not claimed as independent search
hardness. One further escalation to `n=58, copies=5` fits at 298 intended
operations; beyond it the 300-operation G9(c) cap is binding.

## Gate results at provisional `hard`

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 planted checks; 3/3 independent demo BFS materializations |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: 14-digit answer recovered through prose and a Markdown fence |
| G4 | pass: 0/200,000 structure-aware guesses; exact density `1/2^53 = 1.1102e-16` |
| G5 | pass: exactly one valid answer; strongest failed attack ran 65,536 restart trials in 1.90 s across eight seeds |
| G6 | pass: five attacks each 0/8; Gaussian, DPLL and compact references each 8/8 as expected |
| G7 | pass: doubled `n=106`, `copies=4` instance built and verified (8,140,853 implicit vertices) |
| G8 | pass: 40/40 composed relabellings invariant, 40/40 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass: 16 JSON characters, about 4 tokens, 53 semantic atoms, 273 intended operations |

Exact timings live in `selftest_report.json` and vary slightly by run.

## Oracle loop

These are the scored calls from the bare run. The subsequent `hard` calls were
HTTP 403 errors and correctly did not count as failures.

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 1381450917 | google/gemini-3.8-flash | yes | parsed word verified |
| easy | 243966490 | openai/gpt-5.6-terra | yes | parsed word verified |
| easy | 1080601132 | openai/gpt-5.6-terra | yes | parsed word verified |
| medium | 2120454354 | google/gemini-3.8-flash | yes | parsed word verified |
| medium | 2105299560 | openai/gpt-5.6-terra | yes | parsed word verified |
| medium | 2102222664 | google/gemini-3.8-flash | yes | parsed word verified |
| hard | 575396669, 874068102, 1587582192, 673030198 | redraws across both models | unscored | HTTP 403 total-limit errors |

There is no script-owned `hardened`, `too_easy`, or cap verdict because the
harness aborted when every redraw errored. Re-run the bare loop after restoring
quota; do not infer hardness from the four error rows.

## G9 arms

Both diagnostics were rerun against the provisional `hard` preset, but all calls
hit the same account limit.

| Arm | Solved/attempts | Calls retained | Result |
|---|---:|---:|---|
| bare | 0/0 at hard | 4 error rows after the six earlier scored calls | no hard verdict |
| structural hint | 0/0 | 4 | HTTP 403; unrun |
| placebo hint | 0/0 | 4 | HTTP 403; unrun |

`hinted - placebo` is recorded as the neutral numeric placeholder `0.0` because
both denominators are zero. No conclusion about structural help is possible.
The answer-size and intended-route measurements are 16 characters, about four
tokens, 53 semantic atoms, and 273 exact operations.

## How to use it

```python
import random
import gen_2303_06986 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer("Reasoning... <answer>12</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.random_candidate(inst, random.Random(1)) is not None
```

Once the bare oracle loop returns `hardened`, update the ladder and shipping
preset if necessary, rerun every local gate and both G9 arms, then emit from the
repository root with:

```bash
bash scripts/emit.sh 2303.06986 20 hard
```

The module is standard-library-only and performs no file I/O, network access, or
printing at import.

## Caveats

- This is deliberately Track B. A SAT solver or GF(2) linear algebra makes it
  easy; no distributional Track-A hardness is claimed.
- `0/200,000` samples uniformly from the stated canonical one-bit-per-variable
  language. It says nothing about arbitrary subsets of the millions of graph
  vertices, which are outside the answer language.
- The scalable verifier executes the exact Claims 3.2--3.4 equivalence rather
  than expanding every pendant path. Independent BFS covers demo instances only.
- The panel tests incidence, literal-sign frequency, left-to-right greedy,
  8,192 random restarts, and the obvious step-one recurrence. It does not run an
  industrial CDCL solver; successful DPLL and Gaussian references already show
  tool-easiness.
- `copies` increases graph size without adding new logical information. The
  meaningful easy-to-hard growth is `n`; the first two values were insufficient.
- The renderer explicitly labels the XOR rows and presents them in affine order.
  That makes the intended cancellation pattern visible; the 6/6 oracle solves
  show this presentation is an easy route for current models at `n<=41`.
- Canonicalization covers this construction's storage permutations,
  triple-coordinate permutations, and independent truth-endpoint swaps. It is
  not a general graph-isomorphism algorithm outside this family.
- The certificate is a succinct exact definition of a large vertex set, not an
  explicit list of every forced `e^1` and `g^1` member.
- Most importantly, no oracle has yet evaluated `hard`. The current OpenRouter
  account limit is an infrastructure blocker, not evidence that H passes.
