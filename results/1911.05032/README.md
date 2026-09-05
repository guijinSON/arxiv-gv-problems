# Diverse 3-Hitting Set generator (arXiv:1911.05032)

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (natively, a pair of subsets) |
| Intended intuition | symmetry: quadratic character splits the multiplicative action into two classes |
| Domain essentiality | native |
| Reduction | none |

## What this is and whether to trust it

This module instantiates the paper [*FPT Algorithms for Diverse Collections of Hitting Sets*](https://arxiv.org/abs/1911.05032), specifically its native **Diverse 3-Hitting Set** problem. The solver receives a finite universe and 3-element constraints and must return two size-`k` hitting sets whose Hamming distance reaches the entire universe size. Consequently the answer is a balanced complementary bipartition in which neither side contains a constraint triple. Verification is exact set intersection, cardinality, and symmetric difference; it does not read the planted answer.

Generation is inverse, not search. Nonzero coordinates modulo a prime are split into quadratic residues and nonresidues, randomly renamed as universe IDs, and used as the two known hitting sets. Each base triple is sampled uniformly conditional on crossing this split, and its complete orbit under nonzero multiplication is included. Every triple therefore meets both planted sets by construction. Orbit closure also gives every element the same incidence degree, so the planted elements and decoys come from the same per-element distribution.

The exact definition comes from Section 1: a hitting set intersects every member of the family; each of the `r` solutions has size at most `k`; diversity is pairwise Hamming distance. With `r=2`, the paper's sum and minimum diversity objectives coincide. Setting the target to `2k=|U|` forces the exact balanced partition requested here.

## Why Track B, not Track A

The paper itself rules out an honest Track A claim. Lemma 1 enumerates at most `d^k` minimal hitting sets, Section 3 augments each `r`-tuple by maximum-cost flow, and Theorem 1 gives an `r² d^(kr) |U|^O(1)` algorithm. Section 6 gives another FPT algorithm for the minimum-distance objective. At shipping parameters `d=3`, `r=2`, `k=74`, and `|U|=148`, the theorem's parameter factor is `4·3^148`, far beyond hand execution, but it is still an explicit algorithm.

The implemented domain-standard reference algorithm is exact balanced NAE-3-SAT DPLL with unit and cardinality propagation. Its worst-case bound is `O(2^|U|·|F|)`; on eight shipping instances it solved 8/8, averaging 160,162 literal/cardinality inspections, 5.5 search nodes, and 0.0146 seconds. That success is expected and is deliberately outside the failing attack panel. The compact route is much shorter: once the multiplicative symmetry is recognized, 74 modular squares identify one coordinate class and a 148-item scan maps both classes to IDs, for 222 exact operations. Track B measures finding that compression, not computational hardness of this planted distribution.

## Worked demo

This is `make_instance(n=7, orbit_count=2, seed=0)` in full:

```text
Diverse 3-Hitting Set

Universe IDs: [1,2,3,4,5,6]
Each answer set has size 3; required Hamming distance: 6.
Coordinate-to-ID list for coordinates 1,...,6 modulo 7:
[5,3,2,1,6,4]

Constraint triples:
[2,3,6] [1,2,5] [1,5,6] [3,4,5]
[1,3,4] [1,3,6] [2,3,5] [1,2,4]
[2,3,4] [2,5,6] [1,4,6] [4,5,6]

Return <answer>[[...],[...]]</answer> as JSON.
```

The nonzero squares modulo 7 are coordinates `{1,2,4}`, which map to IDs `{5,3,1}`. Thus:

```python
answer = [[1, 3, 5], [2, 4, 6]]
verify(inst, answer)                 # (True, "ok")
verify(inst, [[1, 3], [2, 4, 6]])   # (False, "set 1 must contain exactly 3 distinct IDs")
```

This demo is genuinely hand-solvable: compute three small squares, use the coordinate map, and inspect the twelve triples.

## Difficulty presets

The named ladder was slid upward after the bare loop: the original `n=59` rung was dropped and the held escalated level became `hard`.

| preset | prime `p` | `|U|=2k` | orbits | triples | answer atoms | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 7 | 6 | 2 | 12 | 6 | hand example; not hardened |
| easy | 83 | 82 | 24 | 1,968 | 82 | current ladder |
| medium | 127 | 126 | 32 | 4,032 | 126 | current ladder |
| **hard** | **149** | **148** | **40** | **5,920** | **148** | **ships; bare 0/3** |

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verify and JSON-round-trip |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged JSON recovered from prose; garbage returns `None` |
| G4 | 0/200,000 valid structure-aware random balanced partitions; space `C(148,74) = 23,362,265,873,332,749,085,315,221,863,910,685,052,043,000` |
| G5 | shipping density sample 0/200,000; demo has exactly 2 valid ordered certificates out of 20; reference DPLL used 1,281,299 inspections and 0.117 seconds over 8 instances |
| G6 | degree, online greedy, coordinate interval, ID parity, and 256-restart attacks each solved 0/8; reference DPLL solved 8/8 as expected |
| G7 | doubling `n` built a 306-element universe and enlarged the balanced-partition space while preserving G1 |
| G8 | 60/60 invariance and carried-certificate checks; 20/20 unrelated keys distinct |
| G9(c) | 489 characters, about 123 tokens, 148 atoms, and 222 intended operations; all below caps |

## Bare oracle loop

The transcript uses the pre-slide preset names. Every failed reply parsed; failures are genuine verifier rejections, not output-contract bugs.

| level `(n, orbits)` | model | seed | result | verifier reason |
|---|---|---:|---|---|
| easy `(59,16)` | Gemini 3.8 Flash | 1510333468 | solved | ok |
| easy `(59,16)` | GPT-5.6 Terra | 1366698800 | failed | set 2 misses constraint 16 |
| easy `(59,16)` | GPT-5.6 Terra | 1893515443 | failed | set 1 misses constraint 10 |
| medium `(83,24)` | Gemini 3.8 Flash | 536132082 | solved | ok |
| medium `(83,24)` | GPT-5.6 Terra | 1853270758 | failed | set 2 misses constraint 10 |
| medium `(83,24)` | Gemini 3.8 Flash | 1807762376 | solved | ok |
| hard `(127,32)` | GPT-5.6 Terra | 1304797266 | solved | ok |
| hard `(127,32)` | Gemini 3.8 Flash | 693552949 | solved | ok |
| hard `(127,32)` | Gemini 3.8 Flash | 510494906 | solved | ok |
| escalated `(127,40)` | Gemini 3.8 Flash | 1976318548 | solved | ok |
| escalated `(127,40)` | GPT-5.6 Terra | 1625110119 | failed | wrong set size |
| escalated `(127,40)` | Gemini 3.8 Flash | 1338429995 | solved | ok |
| **escalated `(149,40)`** | Gemini 3.8 Flash | 1051753370 | failed | wrong set size |
| **escalated `(149,40)`** | GPT-5.6 Terra | 1699601694 | failed | set 2 misses constraint 4 |
| **escalated `(149,40)`** | Gemini 3.8 Flash | 174201500 | failed | set 1 misses constraint 3 |

## G9 prompt arms

| arm | solved / attempts |
|---|---:|
| bare | 0/3 |
| structural hint | 2/3 |
| placebo hint | 3/3 |

`hinted − placebo = -1/3`. The structural hint did not outperform the placebo in this three-call sample. Both prompt perturbations did much better than the independently seeded bare arm, so this diagnostic does **not** cleanly attribute success to the stated symmetry; it instead shows substantial prompt/seed sensitivity. This is recorded, not gated. The hinted arm's retired verdict is `too_easy`, while G9(c) passes.

## Use

From the repository root:

```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "gen_1911_05032", "results/1911.05032/gen_1911_05032.py"
)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
inst = gen.make_instance(n=149, orbit_count=40, seed=123)
ok, reason = gen.verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

Loading by path is the portable approach used by the repository scripts. Emit 20 shipping instances with:

```bash
scripts/emit.sh 1911.05032 20 hard
```

## Caveats

- This is an artificial planted distribution, not a distributional-hardness result from the paper. It is explicitly Track B, and exact DPLL solves it in milliseconds.
- The zero random-hit rate is under the uniform balanced-partition prior after enforcing shape, complementarity, and diversity. It says nothing about a solver using the coordinate map or a quadratic-character prior.
- Supplying 5,920 triples and asking for 148 IDs may still expose some transcription burden despite being under G9's caps. The G9 perturbation results make this a real concern.
- Full orbit closure equalizes single-vertex degrees, but pair-codegree or higher-order spectral signatures may reveal the partition. No industrial SAT/SMT solver, LP/SDP relaxation, or hypergraph spectral method was tested; exact DPLL already serves as the required standard CSP algorithm and is expected to win.
- `canonical_key` uses edge-size counts, vertex link signatures, and the multiset of pair codegrees. It is invariant under tested relabellings but is not a complete hypergraph-isomorphism canonical form, so rare non-isomorphic collisions may occur.
- A solver that recognizes quadratic residues can solve the family directly; that is the intended compression, not an attack the benchmark claims to resist.
