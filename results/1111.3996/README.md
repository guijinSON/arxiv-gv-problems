# Path avoiding forbidden pairs generator

> **Status:** complete. All local gates pass, the bare hardening loop held at the
> `easy` shipping preset, and the structural-hint and placebo diagnostics are
> retained as separate script-owned transcripts.

| Profile field | Value |
|---|---|
| Track | **B -- no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT carried through a PAFP graph |
| Certificate form | Boolean integer tuple, written as fixed-width hexadecimal |
| Intended intuition | reduction recognition: parity blocks and a hidden cycle |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed and paper-central: Section 2, Theorem 1 |

## What the family is

[Kovac, *Complexity of the path avoiding forbidden pairs problem revisited*
(arXiv:1111.3996)](https://arxiv.org/abs/1111.3996) asks for an `s`--`t`
path in a directed acyclic graph that contains at most one endpoint of every
forbidden vertex pair. The generator uses the paper's Theorem 1 reduction. Its
first graph part chooses one truth value per variable, its second part chooses
one occurrence per 3-CNF clause, and a forbidden pair blocks every false
occurrence.

Generation is inverse, not a solve. It samples an assignment, hides the variables
on a cycle, evaluates the equations
`x_i XOR x_(i+1) XOR x_(i+2) = b_i`, expands each equation to its four exact
3-CNF clauses, and carries the sampled assignment through Theorem 1. Public
`B`-labels group the four clause layers belonging to one parity block but are
randomly renamed; consecutive groups expose the intended overlapping-window
structure only if the solver notices it. The hexadecimal witness determines one
vertex in every variable layer and the first compatible occurrence in every
clause layer. `verify` expands that concrete path and checks all forbidden pairs
without reading `inst["answer"]`.

The solution is unique: a homogeneous equation obeys
`x_(i+3) = x_i`, so a cyclic solution has period three; every supported `n` is
not divisible by three, forcing the homogeneous solution to be zero.

## Why Track B

Theorem 1 is a worst-case NP-hardness result for overlapping forbidden pairs. It
does **not** establish hardness for this structured generated distribution, so a
Track A claim would be false. The distribution has two disclosed mechanical
solutions at shipping `n=127`:

| Reference route | Complexity / measured shipping cost | Result |
|---|---|---|
| Group parity blocks, Gauss--Jordan over GF(2) | `O(n^3)`; mean 155,060 scalar bit operations and about 0.017 s | 8/8 solved |
| Clause-level DPLL with unit propagation | `O(2^n M)` worst case; mean 10,956 literal inspections, 4.875 nodes, about 0.008 s | 8/8 solved |

The compact route recognizes consecutive length-three windows, subtracts adjacent
parity equations to obtain a step-three recurrence, and evaluates it with a
wide-word parallel prefix. Its conservative count is 127 block-parity evaluations
plus 96 XOR/shift operations, 223 exact operations total. That is within the
300-operation cap, whereas either mechanical route is unrealistic without tools.
Grouping and set-overlap bookkeeping is linear but uses no exact arithmetic; the
groups are explicit and contiguous, so the count does not hide a global clause
search.

The paper's easy regimes were excluded. Section 1.2 records polynomial skew-
symmetric and nested cases and FPT algorithms parameterized by the forbidden-pair
graph's vertex cover or by the union graph's treewidth. Table 1 calls the disjoint
case linear-time. Theorem 3 gives `O(N^3)` dynamic programming for well-
parenthesized pairs, Corollary 1 improves it to `O(N^omega)`, and Section 5 gives
`O(N^(omega+1))` for halving pairs. This family stays in Theorem 1's overlapping
regime.

## Worked demo

This is `render(make_instance(seed=7, **DIFFICULTY["demo"]))` in full:

```text
Find a safe path in a directed acyclic graph with forbidden vertex pairs.

Exact definition.
A forbidden pair is an unordered pair {u,v} of vertices. A directed path
is safe when it contains at most one endpoint of every forbidden pair.
All indices below are zero-based, every listed layer is nonempty, and a
path must contain exactly one vertex from every layer in the displayed order.

Graph.
There are n=5 variable layers and M=20 clause layers.
The vertices, in topological layer order, are:
  {s}; {T_0,F_0}; ...; {T_(n-1),F_(n-1)};
  {C_0,0,C_0,1,C_0,2}; ...; {C_(M-1),0,C_(M-1),1,C_(M-1),2}; {t}.
For every two consecutive layers, include every directed edge from every
vertex of the earlier layer to every vertex of the later layer. There are
no other directed edges. Thus any one choice per layer is an s-t path.

Clause labels and forbidden pairs.
Each clause layer Q_j below labels its three occurrence vertices C_j,0..2.
+v_i means the positive literal v_i; -v_i means its negation.
For every +v_i occurrence C_j,k, {F_i,C_j,k} is forbidden. For every -v_i
occurrence, {T_i,C_j,k} is forbidden. These are all forbidden pairs.
Consequently every forbidden pair starts in the variable part and ends in
the clause part, which is the paper's overlapping-pairs construction.

Each B-label is a public grouping label: clause layers with the same label
came from one four-clause parity block before the paper's reduction. B-labels
need not occur in numeric order, but equal labels are contiguous.
The clause layers, in their graph order, are:
  Q0000 [B0001]: +v1 -v2 -v3
  Q0001 [B0001]: +v2 -v1 -v3
  Q0002 [B0001]: +v2 +v1 +v3
  Q0003 [B0001]: +v3 -v2 -v1
  Q0004 [B0003]: +v4 +v3 +v2
  Q0005 [B0003]: -v2 +v4 -v3
  Q0006 [B0003]: -v4 +v2 -v3
  Q0007 [B0003]: -v4 +v3 -v2
  Q0008 [B0004]: -v0 +v4 -v2
  Q0009 [B0004]: +v0 -v4 -v2
  Q0010 [B0004]: -v0 +v2 -v4
  Q0011 [B0004]: +v0 +v4 +v2
  Q0012 [B0000]: -v0 -v1 -v4
  Q0013 [B0000]: +v0 +v4 -v1
  Q0014 [B0000]: -v4 +v0 +v1
  Q0015 [B0000]: +v4 +v1 -v0
  Q0016 [B0002]: +v1 -v3 -v0
  Q0017 [B0002]: +v3 +v1 +v0
  Q0018 [B0002]: -v3 +v0 -v1
  Q0019 [B0002]: +v3 -v1 -v0

Required witness and its exact path expansion.
Return one hexadecimal word w of exactly 2 digits and value below 2^5.
Leading zeroes are required. Bit i of w (least-significant bit is bit 0)
chooses T_i when it is 1 and F_i when it is 0. In each clause layer choose
the first displayed occurrence whose literal is true under those bits.
Together with s and t, those choices are the concrete path represented by w.
If a clause has no true occurrence, w represents no path certificate.
A candidate is valid exactly when the represented path exists and is safe.

Give your final answer inside <answer></answer> tags as exactly the required
2 lowercase hexadecimal digits, without a 0x prefix.
Example format only: <answer>07</answer>
Output nothing else inside the tags.
```

The answer is `<answer>12</answer>`. `verify(inst, "12")` returns
`(True, "ok")`; `verify(inst, "00")` returns
`(False, "clause layer Q0002 has no compatible occurrence")`. A person can
solve this demo by checking 32 masks or reconstructing the five-cycle.

## Difficulty presets

| Preset | `n` | Clause layers | Answer | Status |
|---|---:|---:|---:|---|
| demo | 5 | 20 | 2 hex digits | hand-solvable; hardening skips it |
| easy | 127 | 508 | 32 hex digits | **ships; bare oracle held 0/3** |
| medium | 163 | 652 | 41 hex digits | reserve escalation rung |
| hard | 191 | 764 | 48 hex digits | reserve rung; compact route is 299 operations |

After `hard`, `escalate` increases parity-block copies at fixed `n=191`, growing
the graph and generic clause-processing cost without lengthening the witness.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | pass: 12/12 planted witnesses verify across all presets |
| G2 | pass: 5/5 corruptions rejected with five distinct reasons |
| G3 | pass: 32-hex-digit witness round-trips through prose and a Markdown fence |
| G4 | pass: exact probability `1/2^127 = 5.877e-39`; sampled 0/200,000 |
| G5 | pass: exact solution count 1; strongest failed probe used 65,536 restarts over eight seeds and 2.05 s |
| G6 | pass: five attacks are each 0/8; both disclosed references and the compact route are 8/8 |
| G7 | pass: doubled `n=254` instance builds and verifies (3,558 graph vertices) |
| G8 | pass: 80/80 invariance checks, 80 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass: all three arms recorded; caps pass at 34 characters, 9 estimated tokens, 127 Boolean atoms, and 223 operations |

Exact timing fields are in `selftest_report.json` and naturally vary between runs.

## Oracle loop and G9 arms

The bare harness held `easy` without escalation. All three replies were parsed;
two hexadecimal candidates failed on an unsatisfied clause and one exceeded the
127-bit range.

| Preset | Seed | Model | Solved? | Why |
|---|---:|---|---|---|
| easy | 956,188,785 | Gemini 3.8 Flash | no | parsed; clause `Q0002` had no compatible occurrence |
| easy | 1,771,957,884 | GPT-5.6 Terra | no | parsed; clause `Q0006` had no compatible occurrence |
| easy | 1,357,989,114 | Gemini 3.8 Flash | no | parsed; value exceeded the `n`-bit range |

| G9 arm | Solved / scored attempts | Status |
|---|---:|---|
| bare | 0/3 | hardened |
| structural | 0/3 | hardened; one length-limited empty response, two invalid candidates |
| placebo | 0/3 | hardened; one length-limited empty response, one invalid candidate, one incomplete response without an answer |

`hinted - placebo = 0.0`: this pool showed no measurable benefit from explicitly
naming the parity-block/hidden-cycle invariant. That weakens evidence that the
failure specifically diagnoses `reduction recognition`; it does not affect the
hardness gate. The structural hint names only the invariant, not the recurrence or
a procedure.

## How to use it

```python
import random
import gen_1111_3996 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY["demo"])
question = gen.render(inst)
candidate = gen.parse_answer("Reasoning... <answer>12</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
assert gen.random_candidate(inst, random.Random(1)) is not None
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1111.3996 20 easy
```

The module uses only the standard library and does no file I/O, network access,
or printing at import.

## Caveats

- This is deliberately Track B. A sandbox, SAT solver, or GF(2) elimination makes
  it easy; no average-case or cryptographic hardness is claimed. The very small
  DPLL node count is disclosed and makes the missing oracle run especially
  important.
- The G4 prior is uniform over the statement-aware language of one Boolean choice
  per variable layer. It says nothing about arbitrary vertex subsets; those are
  not legal compressed witnesses. The exact probability uses the proved unique
  solution, while 0/200,000 alone would not statistically establish `1e-6`.
- The `B`-labels are redundant annotations introduced to make the Track B route
  auditable. They group clauses but their random numeric names carry no cyclic
  position.
- The attack panel covers incidence outliers, all-zero, greedy flips, 8,192 random
  restarts per seed, and the tempting public-variable-order recurrence. It runs an
  in-module DPLL and Gaussian reference but not an industrial external SAT/SMT
  solver or a general PAFP branch-and-bound implementation.
- `canonical_key` is exact for the generator's layered representation and tested
  endpoint, occurrence, and block-label relabellings. It is not a canonical
  labeller for arbitrary DAGs.
- One hinted and two placebo attempts ended without a candidate (length exhaustion
  or an incomplete response). Those are retained honestly; the bare shipping run,
  however, had three complete parsed candidates and therefore does not rely on
  empty-output failures for its hardness evidence.
