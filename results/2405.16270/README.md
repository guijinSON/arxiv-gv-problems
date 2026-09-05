# arXiv:2405.16270 — bounded-degree multiple-Hamiltonicity

Status: the generator and every local G1–G9(c) gate pass at the candidate
shipping preset. STEP 4 is **not complete**: the configured OpenRouter key
returned HTTP 403 “Key limit exceeded” on every bare, structural-hint, and
placebo redraw. The harness-owned transcripts preserve those errors; they are
0 scored attempts, not model failures, so this directory must not be submitted
as hardened until the three arms are rerun with a working key.

| Profile | Value |
|---|---|
| Track | A — structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: normalized cyclic vertex order |
| Intended intuition | decomposition: a Hamilton cycle in a cubic graph is the complement of a perfect matching, and the construction hides a two-page cyclic order |
| Domain essentiality | native |
| Reduction | none |

## Problem and construction

This is Definition 1 of Liu, Sheffield, and Westover’s
[“Complexity of Multiple-Hamiltonicity in Graphs of Bounded Degree”](https://arxiv.org/abs/2405.16270):
the solver receives a simple undirected 3-regular graph and must exhibit a
closed walk visiting every vertex exactly once, the paper’s native
`[1,1]-HAM` witness. Verification is exact and linear in the answer length: it
checks normalization, that the list is a permutation, every consecutive edge,
and the closing edge. It accepts any valid Hamilton cycle and never reads the
planted answer.

Generation is inverse. It chooses the spanning cycle first, places a perfect
decoy matching on two noncrossing pages of that cyclic order, and applies a
uniform vertex permutation. At the shipping preset, one vertex from each
initially alternating page changes pages. This retains the nested decoy
structure while guaranteeing that the old all-same-parity matching—and its
exact signed adjacency eigenvector—cannot survive. An interval dynamic program
samples only decoy matchings in `O(n^3)`; it never solves for the certificate.
The two pages also give every generated graph a planar embedding, although the
solver is promised only the native cubic graph.

## Why Track A

Section 2, Theorem 1 proves `[a,b]-HAM` NP-hard on odd `d`-regular graphs when
`b<d`; here `d=3` and `a=b=1`. This avoids Section 2’s automatic Euler-tour
regime (`b>=d` for odd regular graphs), Lemma 10’s linear-time tree algorithm,
Theorem 2’s polynomial high-`b/a` maximum-degree regimes, and Lemma 16’s
directed degree-three equality algorithm.

The theorem is worst-case, not an average-case result for this generator, so
the distributional claim rests on the measured panel. At `n=252`, randomized
exact search over complementary perfect matchings, with propagation, subtour
pruning, and twelve relabelling restarts, exhausted 120,012 nodes on each of
eight seeds: 960,096 nodes and 191.040 seconds total, with 0 witnesses. A
tempting earlier page construction leaked an exact −1 eigenvector and was
discarded; the final exact-eigenspace attack and an approximate-parity plus
20,000-node repair attack are both 0/8.

## Worked demo

`make_instance(n=8, page_mix=2, seed=731)` renders this complete instance:

```text
[1,1]-HAMILTONICITY IN A CUBIC GRAPH

An undirected closed walk is a cyclic sequence of vertices in which each
consecutive pair is an edge, including the pair formed by the last and first
entries. A graph is [a,b]-HAM when such a walk visits every vertex at least a
times and at most b times. Here a=b=1, so give a Hamilton cycle.

Vertices: 0,1,...,7
Unordered edges:
0-3 2-4 5-6 0-4 2-5 0-1 1-6 2-7 6-7 3-4 1-3 5-7

Return a JSON list of exactly 8 distinct integers, containing 0 through 7.
Every consecutive pair and the last/first pair must be edges. Begin with 0;
the second entry must be smaller than the last.
```

The answer is `<answer>[0, 1, 6, 5, 7, 2, 4, 3]</answer>`.
`verify` returns `(True, "ok")`; deleting the last entry returns
`(False, "wrong_length:7_expected_8")`. The demo has exactly 4 valid normalized
cycles among 2,520 candidates and is hand-solvable.

## Difficulty

| Preset | `n` | `page_mix` | Answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 8 | 2 | 8 | paper illustration |
| easy | 252 | 1 | 252 | candidate shipping preset; all local gates pass |
| medium | 254 | 1 | 254 | escalation reserve |
| hard | 256 | 1 | 256 | final rung at the atom cap |

`SHIPPING_DIFFICULTY = "easy"`. Lower experiments were rejected rather than
hidden: `n=240, page_mix=4` was solved on 1/8 standard-search seeds (38,849
nodes on the successful seed), and `n=220, page_mix=4` was solved by the
construction-aware parity-repair route. Past `n=256`, the full-cycle witness
exceeds the 256-atom limit, so `escalate()` returns `"cap_bound"`.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 preset–seed plants verify; answers JSON-round-trip |
| G2 | pass | 5/5 corruptions rejected with five distinct reason codes |
| G3 | pass | prose/fence/tag response parses and verifies; garbage returns `None` |
| G4 | pass | 0/200,000 normalized random permutations; 13.236 s |
| G5 | pass | shipping density 0/200,000; demo exact 4/2,520; baseline 960,096 nodes / 191.040 s |
| G6 | pass | eight attacks, every one 0/8 at shipping |
| G7 | pass | doubled `n=504` instance builds and verifies |
| G8 | pass | 60/60 key invariance, 60/60 witness transport, 20/20 unrelated keys distinct |
| G9(c) | pass | 899 chars, about 225 tokens, 252 atoms, 252 intended operations |

G6 includes label order, local triangle/four-cycle statistics, constrained
greedy walking, 64 random restarts, spectral seriation, exact −1-eigenspace
rounding (355,416,129 counted operations), near-parity min-conflicts plus exact
repair, and the standard complementary-matching search.

## Oracle loop and G9 arms

No row below is a solve or a model failure. Each arm made four redraws, all of
which failed before inference with HTTP 403; therefore solved/attempts is 0/0
and hinted-minus-placebo is unavailable.

| Arm | Preset | Seeds | Scored | Outcome |
|---|---|---|---:|---|
| bare | easy | 2076450408, 1257034599, 988005296, 1041157712 | 0/0 | four key-limit errors |
| structural | easy | 469874021, 1281905583, 500087968, 925771255 | 0/0 | four key-limit errors |
| placebo | easy | 2110878832, 1392712506, 1684195832, 1729012097 | 0/0 | four key-limit errors |

The hint-effect diagnostic has no conclusion until a working-key run produces
scored attempts. The output and intended-route measurements already satisfy
G9(c).

## Use

```python
import json
import gen_2405_16270 as g

inst = g.make_instance(**g.DIFFICULTY[g.SHIPPING_DIFFICULTY], seed=42)
raw = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = g.parse_answer(raw)
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit with:

```bash
bash scripts/emit.sh 2405.16270 20
```

After replenishing `OPENROUTER_API_KEY`, rerun the bare arm here with
`python3 ../../scripts/harden.py gen_2405_16270.py`. Run structural and placebo
arms only in their separate scratch directories because the harness overwrites
its transcript.

## Caveats

The paper proves worst-case hardness, not hardness of this planted
distribution. The 0/200,000 guess rate uses a uniform prior over normalized
vertex permutations; it does not represent a graph-conditioned solver. The
exact searches are budgeted, not proofs that no faster specialized solver
exists. I did not run a full planar-embedding dynamic program, an external
SAT/ILP solver, or a specialized planar-Hamiltonicity package. The canonical
key is a strong distance-profile invariant rather than a complete
graph-isomorphism canonical form. Most importantly, there is no multi-vendor
no-tool evidence while the OpenRouter key is exhausted.
