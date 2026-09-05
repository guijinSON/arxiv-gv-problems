# Verified S-empty L(2,1)-labeling generator

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP / graph coloring |
| certificate form | integer-valued labeling vector |
| intended intuition | constraint propagation through overlapping neighborhoods |
| domain essentiality | native |
| reduction | none |

This module turns Colucci and Győri's [*On L(2,1)-labelings of oriented
graphs*](https://arxiv.org/abs/1902.05467) into an exact witness problem.  A
solver receives an oriented simple graph and must assign every vertex one of a
fixed set of even integer labels.  For the paper's `S = empty` variant there is
no two-step-path condition; an arc only requires its endpoint labels to differ
by at least two.  The checker scans the label vector and every arc using integer
comparisons.  It never reads the planted answer.

**Trust status:** every local mandatory gate passes, including seven attacks on
eight shipping seeds.  The directory is nevertheless **not submission-ready**:
the required bare and G9 oracle runs reached OpenRouter, but all twelve redraws
returned HTTP 403 `Key limit exceeded`.  There are zero completed oracle
attempts, so these errors are not counted as evidence that a model failed.

## Family and Track-A basis

Section 3 defines the three oriented two-path types `P1`, `P2`, and `P3`, then
defines `L_S` labelings and explicitly identifies the `S = empty` case with
ordinary graph coloring (up to the paper's span convention).  Generation first
draws a shuffled balanced partition and then samples only cross-class edges;
each edge is oriented independently.  The certificate is therefore known by
inverse generation before the public graph exists.

The shipping distribution has `q=5`, `n=240`, and expected degree 14.  In the
balanced planted-coloring/SBM notation its within-class rate is `a=0` and its
cross-class rate is `b=17.5`, so
`SNR=(a-b)^2/[q(a+(q-1)b)]=0.875`.  Theorem 1 of Abbe and Sandon's
[Kesten–Stigum achievability result](https://arxiv.org/abs/1512.09080)
provides `O(n log n)` acyclic-belief-propagation detection above `SNR=1`, not
an efficient guarantee for this regime.  Its converse is not proved here, and
community detection is not the same task as finding any proper coloring.  The
theorem therefore calibrates the distribution but does **not** prove
average-case hardness.  The concrete Track-A evidence is the adversary panel:
symmetry-normalized exact DSATUR/DPLL, Walk-COL-style repair, adjacency and
nonbacktracking spectral recovery, greedy restarts, and a planting-signature
probe all fail 0/8.

The paper's easy regimes were deliberately avoided.  Theorem 1 and Theorems
3–5 give greedy labelings when a much larger degree-dependent palette is
allowed, and Section 2 notes the constant upper bound for directed trees.  The
shipping instances instead have cycles and exactly five required labels.  An
earlier `q=4,d=9` candidate was discarded after a stronger min-conflicts run
repaired a shipping instance in about 6.3 million local operations.

## Worked demo (`demo`, seed 0)

```text
S-EMPTY L(2,1)-LABELING OF AN ORIENTED GRAPH

The vertices are the integers 1 through 8, inclusive.  The graph
is oriented: each listed ordered pair u>v denotes the arc u -> v.
There are no loops, no repeated arcs, and never arcs in both directions
between one pair of vertices.

For this problem S is empty.  Thus no condition is imposed by any
two-arc path.  Only an arc imposes a condition: its endpoint labels
must differ by at least 2.  Find a labeling using exactly the even
labels 0, 2, ..., 6 and using every one of those
labels at least once.

Equivalently, each even label is one nonempty independent class: no
listed arc may have endpoints carrying the same label.

The 12 arcs are listed below (u>v means u -> v):
  1>6  6>5  7>4  1>3  5>3  4>3  3>2  4>5  6>2  8>3
  7>6  6>8

Output one JSON array of exactly 8 integers.  Entry i is the label
of vertex i (so indexing is 1-based in the graph but array position 1
is the first entry).  Use every allowed even label at least once.
Do not put explanatory text inside the tags.

Give your final answer inside <answer></answer> tags, as a JSON
array of labels in vertex order.
Format example only (not a solution to this instance): <answer>[0,2,4,6,0,2,4,6]</answer>
Output nothing else inside the tags.
```

A valid response is
`<answer>[4,0,2,4,0,2,6,6]</answer>`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last
entry returns `(False, "too few labels: expected 8, got 7")`.  This smallest
setting is genuinely hand-scale: a person can color eight vertices and inspect
all twelve arcs.

## Difficulty presets

| preset | vertices | labels | expected degree | status |
|---|---:|---:|---:|---|
| demo | 8 | 4 | 3 | hand example; hardening skips it |
| easy | 48 | 4 | 7 | local gates pass; oracle unavailable |
| medium | 120 | 4 | 9 | local gates pass; oracle unavailable |
| **hard** | **240** | **5** | **14** | **shipping candidate; local gates pass, oracle unavailable** |

`escalate()` raises both the class count and constraint density at fixed
240-entry answer length (`5/14 -> 6/22 -> 8/42 -> 10/70 -> 12/100 ->
15/171 -> 16/197`).  It grows the search haystack without lengthening the
witness; beyond 16 colors, maintaining the calibrated SNR requires more than
the 225 available cross-class vertices unless `n` grows past the answer cap.

## Gate results

| gate | measured result | pass |
|---|---|:---:|
| G1 | 12/12 preset/seed plants verify and JSON-round-trip | yes |
| G2 | 5/5 corruptions rejected with five distinct reasons | yes |
| G3 | realistic fenced/prose answer round-trips; garbage returns `None` | yes |
| G4 | 0/200,000 onto-label-vector guesses; candidate space 557.263 bits | yes |
| G5 | shipping density 0/200,000; demo has 384/40,824 valid vectors; normalized DSATUR used 800,008 nodes and 43.15 s | yes |
| G6 | all seven attacks below fail 0/8 | yes |
| G7 | 240→480 vertices and 1,697→3,429 arcs; planted witness still verifies | yes |
| G8 | 100/100 invariance and 100/100 carried-witness checks; 20/20 unrelated keys distinct | yes |
| G9(c) | 720 chars, 180 estimated tokens, 240 atoms, 240 intended assignments | yes |

| G6 attack | successes | measured work over 8 seeds |
|---|---:|---:|
| orientation-imbalance outlier | 0/8 | 15,372 operations |
| largest-degree greedy | 0/8 | 10,374 operations |
| 64 randomized greedy restarts | 0/8 | 653,348 operations |
| min-conflicts `16 x 200n` | 0/8 | 40,705,589 operations |
| bottom-spectrum subspace + k-means | 0/8 | 9,077,760 operations |
| nonbacktracking subspace + k-means | 0/8 | 129,893,440 operations |
| symmetry-normalized exact DSATUR/DPLL, 100,000-node cap | 0/8 | 800,008 nodes |

Exact wall times and full per-gate records are in
[`selftest_report.json`](selftest_report.json).

## Oracle loop and G9 arms

The bare script stopped during the first `easy` attempt group, before any
completed answer.  These are service errors, not solver failures.

| preset | seed | model | solved | reason |
|---|---:|---|:---:|---|
| easy | 128954383 | GPT-5.6 Terra | error | HTTP 403 key limit |
| easy | 2048132012 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 1191777237 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 617113691 | GPT-5.6 Terra | error | HTTP 403 key limit |

| G9 arm | shipping parameters | solved/attempts | errors | conclusion |
|---|---|---:|---:|---|
| bare | not reached by ladder | 0/0 | 4 | unavailable |
| structural hint | `n=240,q=5,d=14` | 0/0 | 4 | unavailable |
| placebo hint | `n=240,q=5,d=14` | 0/0 | 4 | unavailable |

The recorded hinted-minus-placebo value is numerically `0.0`, but it has no
evidentiary meaning with zero completed attempts.  The isolated transcripts
are retained as `g9_hinted_transcript.jsonl` and
`g9_placebo_transcript.jsonl`.  Re-run all three arms with working quota before
submission.

## Use

```python
from gen_1902_05467 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

After a successful bare hardening run, emit from the repository root with:

```bash
bash scripts/emit.sh 1902.05467 20 hard
```

## Caveats

- Track A is empirical.  The Kesten–Stigum theorem concerns correlated
  community detection in the asymptotic SBM, not exact five-coloring of this
  finite connected conditioning; being below its efficient regime is not a
  runtime lower bound.
- G4 samples uniformly from all length-240 vectors using every allowed label.
  It enforces every syntactic constraint and does not quotient global label
  names because valid answers have the same renaming symmetry.  Its 0/200,000
  result is a density estimate under that prior, not evidence against targeted
  search.  A generator-aware balanced prior would be narrower and was not
  claimed to be freely deducible from the statement.
- The panel ran a nonbacktracking spectral approximation, but not the full
  cycle-corrected Abbe–Sandon ABP algorithm, an industrial SAT/ILP package, an
  SDP relaxation, or min-conflicts beyond the stated 40.7-million-operation
  budget.  Any of these could still make the distribution easy.  A separate
  audit also exhausted 500,000 symmetry-normalized DSATUR nodes on each of the
  same eight seeds, but that longer run is not used as a gate measurement.
- Increasing density into `SNR>1`, allowing the paper's large greedy palette,
  or using trees would make the family easy.  The discarded `q=4,d=9` version
  shows that even a boundary-calibrated plant can succumb to local repair.
- Direction is deliberately irrelevant for `S=empty`; this is native coverage
  of the paper's Section 3 variant, not coverage of the classical `P1` problem
  from Sections 1–2.
- `canonical_key` uses one-dimensional color refinement on the underlying
  graph.  It is invariant under the tested vertex/arc symmetries but is not a
  complete graph-isomorphism algorithm, so rare nonisomorphic collisions remain
  possible.
- Most importantly, the script-owned oracle hardness evidence is missing
  because of the OpenRouter quota failure.  Do not treat the local gates alone
  as a completed Track-A certification.
