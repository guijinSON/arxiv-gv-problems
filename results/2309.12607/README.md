# Fixed-cycle Hamilton transversals (arXiv:2309.12607)

> **Status:** the generator and every local gate pass, but the required external
> hardness verdict is incomplete. The refreshed bare run obtained one genuine
> failed oracle attempt, then OpenRouter rejected all redraws with HTTP 403
> `Key limit exceeded (total limit)`. The script-owned transcripts are retained
> and the three arms must be completed after quota is restored.

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `permutation` (implemented as bipartite matching) |
| Certificate | `integer_tuple`: one graph color per cycle edge |
| Intended intuition | `change of variables`: expose an affine perfect matching modulo the prime cycle length |
| Domain essentiality | `licensed_reduction` |
| Reduction | `paper_licensed`: Section 5, Lemma 5.1; not full native-domain coverage |

## Problem and trust

Anastos and Chakraborti’s [“Robust Hamiltonicity in families of Dirac
graphs”](https://arxiv.org/abs/2309.12607) defines a Hamilton
`G`-transversal as a Hamilton cycle together with a bijection from its edges to
the graph family, with every edge present in its assigned graph (Section 1.2).
Here the Hamilton cycle is displayed in advance. The solver receives `p` sparse
subgraphs `F_c` of the complete Dirac graph `K_p` and must assign the `p` graph
colors bijectively to the cycle edges. Verification is an exact permutation
check followed by `p` edge-membership tests.

This is **not full native coverage** of the paper's Hamilton-cycle search: fixing
the cycle discards the vertex-order search and leaves the edge-coloring step.
Section 5, Lemma 5.1 explicitly licenses that step as an auxiliary bipartite
matching, whose perfect matchings are exactly the rainbow colorings.

Generation is inverse. It samples nonzero `a` and `b` modulo prime `p`, plants
edge `e_(a*c+b)` in graph `F_c`, and adds same-marginal uniform cycle-edge
decoys. Thus `c = a^-1(t-b)` colors every cycle edge `e_t` exactly once. The
answer exists before any decoy, row order, edge order, or vertex name is drawn.
The first six rows are rejection-sampled so that this affine line is the unique
one consistent with them; that checks a known plant and does not solve the
finished instance.

## Why Track B

This cannot honestly be Track A. Section 4 constructs rainbow edge sets using
maximum matching in an auxiliary bipartite graph, and Section 5 explicitly
identifies perfect matchings with rainbow colorings of fixed path edges.
Hopcroft–Karp therefore solves this family in `O(E sqrt(V))`. At the shipping
preset the executable reference solved 8/8 instances, averaging **2,443 edge
scans and 0.0061 s in the final gate run**.
The certificate is easy for software.

The no-tool gap is the point: an unaided solver otherwise has to perform a
107-by-107 matching with 856 displayed incidences. Recognizing that the first
few rows share `t = a*c+b` reduces the work to modular differences, one inverse,
and an additive recurrence for the output. On shipping seed 314159 that route
was executed, verified, and counted at **266 exact arithmetic operations**.
Theorems 1.4 and 1.5 (v3) concern random subgraphs of Dirac graphs; this module
uses those native objects but inverse-conditions its fixed-width samples, so it
does not claim to sample the paper’s unconditioned binomial model.

The paper also states why its random regimes become impossible: after Theorem
1.5, the common sparsifier must retain minimum degree at least two and each
independently sparsified color graph must retain an edge. The counterexample
after Question 1.6 exhibits an additional parity obstruction. Those threshold
regimes are not used as a hardness claim here; fixing the cycle exposes the
polynomial matching algorithm and forces the Track B label.

## Worked demo

This is `make_instance(seed=7, **DIFFICULTY["demo"])`, small enough to solve
and check on paper:

```text
p=7; graph colors are 0,...,6.
Hamilton-cycle vertex order: 1 5 2 6 3 4 0 (then back to 1).
Edge e_t joins positions t and t+1 modulo 7.

F_3: 4 3
F_6: 5 0
F_2: 2 0
F_0: 3 1
F_4: 6 0
F_5: 2 3
F_1: 4 0
```

One answer is `<answer>[2,0,5,3,1,6,4]</answer>`, and `verify` returns
`(True, "ok")`. Changing it to `[0,2,5,3,1,6,4]` returns
`(False, "edge e_0 is not present in F_0")`. Exhaustive enumeration finds
exactly two valid demo permutations out of `7! = 5040`.

## Difficulty presets

| preset | prime `p` | row width | incidences | answer atoms | measured compact operations | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 7 | 2 | 14 | 7 | 36 | hand example; skipped by hardener |
| easy | 79 | 4 | 316 | 79 | 143 | bare oracle run blocked by HTTP 403 |
| medium | 97 | 6 | 582 | 97 | 208 | locally verified |
| hard | 107 | 8 | 856 | 107 | 266 | **intended shipping preset**, locally verified |

Escalation first increases row crowding, then offers one `p=127` rung while
holding the eight-entry row width fixed. Construction rejects decoy tables
whose compact route would exceed 300 operations there. Beyond that rung the
effort cap is binding, so `escalate()` returns `None`; it does not falsely call
this an answer-size `cap_bound`.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced prose round-tripped the 107-entry answer |
| G4 | 0/200,000 valid structure-aware guesses; candidate space `107!` (572 bits) |
| G5 | shipping density estimate 0/200,000; demo exact count 2/5040; reference 2,443 scans / 0.0061 s |
| G6 | frequency outlier, first-fit, 256 random greedy restarts, and shift/reversal ansatz: 0/8 each; Hopcroft–Karp 8/8 |
| G7 | requested doubled size 214 rounded to prime 223, built and verified |
| G8 | 100/100 invariance and 100/100 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 319 characters, about 80 tokens, 107 atoms; 266 intended exact operations |

## Oracle loop

The first row is a genuine model failure: the reply parsed, but contained 78
colors where 79 were required. After that, four redraws ended at OpenRouter
before a model saw the prompt, so the harness correctly exited without a
hardness verdict.

| preset | model | seed | solved | why |
|---|---|---:|---|---|
| easy | Google Gemini 3.8 Flash | 363626814 | no | parsed 78 entries; length check rejected it |
| easy | OpenAI GPT-5.6 Terra | 833680313 | error | HTTP 403 key-total-limit |
| easy | OpenAI GPT-5.6 Terra | 172429399 | error | HTTP 403 key-total-limit |
| easy | OpenAI GPT-5.6 Terra | 1836252985 | error | HTTP 403 key-total-limit |
| easy | OpenAI GPT-5.6 Terra | 805942805 | error | HTTP 403 key-total-limit |

## G9 arms

Each G9 copy likewise tried four redraws at shipping `hard`.

| arm | preset | usable solved/attempts | recorded outcome |
|---|---|---:|---|
| bare | hard | 0/0 | shipping-preset diagnostic not reached; main loop has one failed attempt at easy |
| structural hint | hard | 0/0 | four HTTP 403 errors |
| placebo hint | hard | 0/0 | four HTTP 403 errors |

With zero usable attempts, hinted minus placebo is substantively undefined
(stored as `0.0` only as a zero-attempt sentinel), so no hint-responsiveness
conclusion is warranted. The structural hint names only the invariant:
“Modulo the prime cycle length, the color-to-edge incidence contains an affine
permutation shared across all rows.”

## Use

```python
import json
from gen_2309_12607 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful oracle rerun, emit instances with:

```bash
bash scripts/emit.sh 2309.12607
```

## Caveats

This is the paper-licensed fixed-cycle coloring subproblem used inside the paper’s proof, not
the harder task of finding both the Hamilton cycle and its coloring. It becomes
easy immediately for Hopcroft–Karp or for a solver that detects the planted
affine line. The `0/200,000` number is only for a uniform random permutation,
the strongest freely implied prior; it says nothing about adaptive matching or
affine recovery. Samples are fixed-width, inverse-conditioned sparsifications,
not independent `G_p` draws, so the paper’s probability thresholds are not
being empirically tested.

The local panel did not test industrial ILP/CP-SAT, network-flow packages,
belief propagation, or specialized affine list-recovery code; all are expected
to make the mechanical route cheaper, which is compatible with Track B. Most
importantly, there is no four-vendor no-tool evidence until OpenRouter quota is
restored and the bare, hinted, and placebo harness runs are repeated. The
optional `p=127` rung exhausts the compact-route effort budget; if the oracle
solves it too, this family should be rejected as too easy under the current
no-tool cap rather than escalated beyond the cap.
