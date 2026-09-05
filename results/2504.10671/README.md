# Token Sliding Reconfiguration on DAGs — verified generator

| Profile field | Value |
|---|---|
| Track | **B** (no-tool compression) |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | exact symbolic bit string encoding a slide sequence |
| Intuition | change of variables: shuffled affine cyclic recurrences |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed; Section 4, depth-3 DAG reduction from 3-SAT |

## Problem and trust model

This generator implements the depth-3 construction in Dirks and Vigny,
[“Token Sliding Reconfiguration on DAGs” (arXiv:2504.10671v2)](https://arxiv.org/abs/2504.10671).
The solver receives a succinct specification of the paper's DAG: a 3-CNF formula,
its variable/clause/literal/timing gadgets, and its initial and target independent
sets. The requested bit string denotes the exact forward slide sequence from the
paper's proof. `verify` expands the XOR constraints to 3-CNF, constructs every DAG
arc, selects the stated moves, and replays all of them while checking direction,
occupancy, independence, and the final configuration. It never reads the planted
answer.

Generation is inverse: sample the answer first, choose several affine cycle steps,
and set each right-hand side from that answer. Every cycle subsystem is nonsingular
when `n` is not divisible by 3, since its homogeneous recurrence has period three.
Thus the certificate is known by construction, not found by solving the instance.

## Why Track B

The paper's Theorem 1.2 proves NP-completeness for depth-3 DAGs. Lemma 3.1 makes
depth 2 polynomial, Lemma 3.4 gives a `2k + 4^k` kernel at depth 3, and Theorem
1.4 is FPT in token count plus treewidth. Here the number of tokens and treewidth
both grow. I did not use the paper's depth-4 Theorem 1.3 reduction: Section 5
writes open-neighborhood edges but its soundness proof also invokes equality, an
apparent gap for loop-free graphs.

This particular generated distribution is nevertheless **not** claimed hard in the
Track-A sense. Generic Gauss–Jordan elimination over GF(2) solves every instance in
`O(m n^2)`. At the shipping preset the two recorded local runs used 0.026--0.081
seconds and exactly 766,164 scalar GF(2) operations. A solver that notices an affine
cycle instead needs 293 XOR operations: recover a constant-step order, run the
second-order recurrence with zero initial state, use cyclic closure to obtain the
two initial bits, and combine. The operation count fits the no-tool cap, but doing
that accurately from hundreds of shuffled rows is qualitatively different from
calling elimination.

## Worked demo

For `make_instance(n=7, cycles=1, seed=7)`, the common definitions in the rendered
statement say that a line `a b c | r` means `x_a XOR x_b XOR x_c = r`; it expands
to the four 3-CNF clauses excluding wrong-parity triples. Those clauses are put into
the paper's variable, signed-literal, clause, and timing gadgets. A bit string `z`
means: choose each `p_i^(z_i)`, move each true literal token, route every clause token
through its first true literal gate, move the timing token, finish the variable
tokens, then move the false literal tokens. The complete instance data are:

```text
n = 7; cycle families = 1
4 0 1 | 1
2 5 1 | 1
6 3 0 | 0
0 3 4 | 1
1 4 5 | 0
2 3 6 | 0
2 5 6 | 0

Give exactly seven bits in x_0,...,x_6 order:
<answer>1010001</answer>
```

This succinct statement expands to a depth-3 DAG with 198 vertices, 50 tokens,
28 CNF clauses, and 85 slides. It is genuinely hand-scale: one can reorder the
seven recurrence equations and propagate two trial bits. The planted answer gives
`verify(inst, "1010001") == (True, "ok")`; corruption gives
`verify(inst, "2010001") == (False, "out-of-range symbol '2': only 0 and 1 are allowed")`.

## Difficulty presets

| Preset | Variables | affine cycles / XOR rows | expanded slides | Status |
|---|---:|---:|---:|---|
| demo | 7 | 1 / 7 | 85 | hand example; never ships |
| easy | 31 | 2 / 62 | 621 | oracle run unavailable |
| medium | 61 | 3 / 183 | 1,709 | local gates pass |
| hard | 97 | 5 / 485 | 4,269 | **shipping preset; local gates pass** |

## Gate results

| Gate | Result |
|---|---|
| G1 | pass on four presets × four seeds |
| G2 | pass; five corruptions rejected with five distinct reasons |
| G3 | pass; fenced/prose-wrapped bit string round-trips |
| G4 | pass; 0 hits in 200,000 uniform valid-format strings (`P=2^-97` exactly) |
| G5 | pass locally; one solution by full rank, Gaussian reference succeeds, ~0.77M operations |
| G6 | pass; 0/8 for each of four attacks; Gaussian reference 8/8 as expected |
| G7 | pass; doubled size builds and its planted witness verifies |
| G8 | pass; 40 composed invariance and 40 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass; 99 serialized characters, 97 atoms, about 25 tokens, 293 exact operations |

The four failing attacks are per-variable RHS-incidence bias, deterministic
first-conflict greedy improvement, 256-restart parity random walk, and a by-hand
listed-order propagation ansatz. The first tests planting leakage; the next two test
local repair; the last tests the obvious strategy available from the prompt.

## Oracle loop and G9 arms

The mandatory harness was invoked, but the configured OpenRouter key had exhausted
its total limit. The harness returned HTTP 403 for every redraw and correctly refused
to score an API error as a model failure. Therefore there is **no external hardness
verdict**, and this directory is not submission-ready until the three runs are
repeated with a funded key.

| Bare preset | Seed | Solved | Why |
|---|---:|---|---|
| easy | 611919287 | error | HTTP 403 key limit |
| easy | 1382639272 | error | HTTP 403 key limit |
| easy | 1548024974 | error | HTTP 403 key limit |
| easy | 175497899 | error | HTTP 403 key limit |

| G9 arm | Solved / counted attempts | Error redraws | Result |
|---|---:|---:|---|
| bare | 0 / 0 | 4 | unavailable; HTTP 403 key limit |
| structural hint | 0 / 0 | 4 | unavailable; HTTP 403 key limit |
| placebo hint | 0 / 0 | 4 | unavailable; HTTP 403 key limit |

Hinted minus placebo is undefined (recorded as 0.0 only because both denominators are
zero). No conclusion about structural help is possible. The structural sentence names
only the cyclic-recurrence invariant; it does not give a procedure.

## Use

```python
from gen_2504_10671 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer("work... <answer>1010001</answer>")
assert verify(inst, candidate) == (True, "ok")
```

After a successful external hardening run, emit examples from the repository root:

```bash
bash scripts/emit.sh 2504.10671 20
```

## Caveats

The 0/200,000 estimate is under the exact declared prior—uniform `n`-bit strings—and
does not establish model hardness or average-case cryptographic hardness. The equation
systems are easy with a CAS, SAT/XOR solver, or the bundled elimination routine; this
is precisely why the family is Track B. I did not test industrial CDCL/XOR solvers,
Gröbner methods, or vendor models because the external account was unavailable.
`canonical_key` uses weighted closed-walk traces and is invariant under the tested
relabelings and coordinate flips, but it is a strong fingerprint rather than a
complete hypergraph isomorphism canonizer. Most importantly, the required four-vendor
evidence is missing for an external reason and must not be inferred from the passing
local gates.
