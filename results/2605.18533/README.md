# Minimal forbidden propagation sets from arXiv:2605.18533

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | exact symbolic cyclic-row descriptor |
| Intuition | change of variables |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 2.1's propagation-to-precedence map and Section 3, Proposition 2 |

This generator instantiates the central forbidden-propagation-set (FPS) objects in
[Lucci, Delle Donne, and Escalante, *Capacitated power dominating set problem: a solution approach based on forbidden propagation sets*](https://arxiv.org/abs/2605.18533).
The solver receives an exact, succinctly defined finite graph, its zero-injection
helpers, and a propagation set. It must identify a row whose propagations form a
minimal FPS. The three-integer answer denotes that entire cyclic set without a long
transcription. Verification expands the descriptor, checks every propagation is
present, runs exact directed-cycle detection, deletes each propagation in turn, and
checks acyclicity. It never reads the planted answer.

## Why this is Track B

This is deliberately not a Track A claim. Section 4.3, Algorithm 1 gives a
polynomial-time separator: construct the precedence digraph, find a cycle, trim it
to a chordless cycle, and use Proposition 2 to recover a minimal FPS. On the succinct
shipping instance, the reference row scan is `O(q*d)` for field size `q` and
polynomial degree `d`; over eight seeds it solved 8/8 in 25.142599 seconds and
1,157,250,752 exact modular operations (mean 3.14 seconds and 144,656,344 operations).
An explicit implementation of the paper's DFS is linear in the logical precedence
graph, which has over 160 million target vertices at the shipping preset.

The compact route is at most 64 exact operations. Normalize the leading coefficient,
recognize the degree-25 activation polynomial as
`lambda*((r-s)^5-c)^5`, recover `s` from the top two coefficients and `c` from the
degree-20 coefficient, and invert the fifth-power permutation of `GF(q)`. The paper's
introductory NP-hardness and its easy PDS graph classes are not used: the FPS
separator itself is polynomial in every regime, which is why the module says Track B.

## Worked demo

The demo is genuinely hand-scale: there are only 17 rows, so a person can evaluate
the six-term polynomial row by row even without spotting its composition.

```text
Find a minimal forbidden propagation set in the following exact finite graph.

All arithmetic on row labels is in the prime field GF(17), represented by the integers 0 through 16. Positions are integers modulo 6.

Displayed row labels y are a relabelling of semantic rows r. Decode and encode them by
  r = 16 * (y - 11) mod 17,
  y = 16 * r + 11 mod 17.

The row-activation polynomial is over GF(17). It is given as [exponent, coefficient] pairs; term order is irrelevant and omitted coefficients are zero:
  P(r) = [[0,4], [1,11], [2,1], [3,7], [4,16], [5,2]]
meaning P(r) is the sum of coefficient*r^exponent modulo 17.

For a semantic row r define
  d(r) = 1 + ((r mod 2) mod 5),
  b(r) = (5*r + 1) mod 6.
A row-position (r,i) is active precisely when either P(r)=0, or
  (i - b(r)) mod 6 >= d(r).

Graph and propagation set. For every row r and position i there is a target vertex v(r,i). For every active (r,i) there is a zero-injection helper vertex h(r,i), adjacent to exactly v(r,i) and v(r,i+1 mod 6). The given propagation set F contains p(r,i)=(h(r,i),v(r,i)) for every active (r,i), and no other propagation.

A propagation (u,v) imposes a directed precedence arc (w,v) for every w in the closed neighbourhood N[u] except v. For W subset F, D_W is the union of all arcs imposed by propagations in W. W is a forbidden propagation set (FPS) when D_W contains a directed simple cycle. It is minimal when deleting any one propagation from W makes D_W acyclic.

Your witness is a cyclic-row descriptor [y,6,-1]. It denotes all 6 propagations p(r,i), one for each i=0,...,5, where y is the displayed label of r. The -1 records that the imposed target-vertex cycle runs from position i+1 to i. Find a descriptor whose denoted propagation set is a minimal FPS. Integers are exact; intervals and repeats are not involved.

Give your final answer inside <answer></answer> tags, as one JSON array [row_label,6,-1].
Example of format only: <answer>[0, 6, -1]</answer>
Output nothing else inside the tags.
```

For `seed=0`, the answer is `<answer>[2, 6, -1]</answer>` and `verify` returns
`(True, "ok")`. Dropping its last field gives `[2, 6]`, rejected as
`(False, "descriptor has too few fields")`.

## Difficulty presets

| Preset | Lower bound `n` | Actual `q` | Cycle length | Polynomial degree | Logical targets | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 17 | 17 | 6 | 5 | 102 | hand example |
| easy | 5,000,011 | 5,000,077 | 32 | 25 | 160,002,464 | **ships; bare oracle held** |
| medium | 10,000,019 | 10,000,019 | 40 | 30 | 400,000,760 | reserve escalation |
| hard | 20,000,003 | 20,000,003 | 48 | 35 | 960,000,144 | reserve escalation |

An earlier 5,003-row easy prototype was removed even though the oracle failed it:
its answer density was too high for G4. A 2,000,003-row prototype then recorded one
hit in 200,000 samples and was enlarged without changing the witness.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified across every preset |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from surrounding prose/fences |
| G4 | pass | 0/200,000 uniform row guesses; exact probability `1/5,000,077` |
| G5 | pass | one solution by construction; strongest failed probe 13,824 ops / 0.002882 s |
| G6 | pass | four attacks at 0/8; reference scan 8/8 |
| G7 | pass | doubled build has `q=10,000,079`, 320,002,528 targets, and verifies |
| G8 | pass | 20/20 relabellings, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 17 chars, 5 estimated tokens, 3 atoms, 64 intended operations |

## Bare oracle loop

| Preset | Seed | Model | Solved | Exact reason |
|---|---:|---|---|---|
| easy | 1,382,254,042 | openai/gpt-5.6-terra | no | chosen row inactive at position 0 |
| easy | 1,336,526,383 | google/gemini-3.8-flash | no | chosen row inactive at position 0 |
| easy | 1,964,315,787 | google/gemini-3.8-flash | no | chosen row inactive at position 0 |

All three replies parsed successfully. The harness verdict is `hardened` with zero
escalations and shipping preset `easy`.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `0.0`. The structural hint bought no measured improvement.
That may mean the hint is too weak, or that recognizing the composition was not the
only obstacle; it weakens any claim that the oracle failures isolate this intuition.
The answer is 17 characters / 3 atoms, and the intended route is bounded at 64 exact
operations.

## Use

```python
from gen_2605_18533 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=123, **DIFFICULTY["easy"])
print(render(inst))
candidate = parse_answer("<answer>[1234, 32, -1]</answer>")
print(verify(inst, candidate))
```

From the repository root, emit JSONL instances with:

```bash
bash scripts/emit.sh 2605.18533 20 easy
```

## Caveats

- This benchmarks the paper's FPS separation object, not optimal CPDS monitor placement and not realistic power-network topology. The graph is synthetic and succinctly represented.
- The special row is a global full-cycle outlier. A complete scan finds it efficiently; this is the declared Track B reference algorithm, not hidden hardness.
- The `P(guess)` prior is uniform over all structurally valid cyclic-row descriptors. It does not model an informed solver that recognizes the polynomial composition.
- A CAS polynomial decomposer, finite-field factorizer, or a tool-using model was not attacked. Any of those should solve the family quickly.
- The canonical key is complete for the generated disjoint-row component family, not a general graph-isomorphism canonicalizer.
- `gvlib` is unnecessary here: every operation is modular integer arithmetic supplied by the standard library.
