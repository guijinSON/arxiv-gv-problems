# Verified problem generator for arXiv:2302.03797

| Profile field | Value |
|---|---|
| Track | **B** — an efficient reference algorithm exists and is disclosed |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate | integer tuple: an ordered sequence of repeat identifiers |
| Intended intuition | invariant — compress matched adjacency directions to the signed word of run boundaries |
| Domain essentiality | native; no reduction or discretisation |

## Problem and trust model

This implements the native 2-balanced minimum symmetric-reversal problem from
[Tong et al., *Men Can't Always be Transformed into Mice*](https://arxiv.org/abs/2302.03797).
The solver receives two signed chromosomes and must give a shortest sequence of
legal inclusive reversals, each flanked by oppositely oriented copies of one
repeat. Verification recomputes the start–target adjacency matching, counts
maximal negative segments (MNS), replays every reversal, and compares the exact
result with the target. It never reads the planted answer.

Generation is inverse and theorem-backed. It samples a simple 2-balanced target,
then composes distinct reversals while requiring the exact MNS count to rise by
one at every step. Reversing those choices reaches the target. Section 4,
Lemma 4.1 says one reversal can remove at most one MNS, so the held sequence is
optimal by construction. All local gates pass.

## Why Track B

This is deliberately not a Track A claim. Section 5 gives an `O(L²)` decision
algorithm for general SSR, and Section 4, Algorithm 1 / Theorem 4.3 gives an
`O(L²)` optimum algorithm in this 2-balanced regime. The hard-preset reference
implementation succeeds on 8/8 instances, using exactly 7,651 counted
comparisons/updates and 0.0165 s per instance in the final recorded self-test
on this runner. Section 6, Theorem 6.3 proves NP-hardness only when the target need not contain both signs
of every repeat; this generator intentionally remains in the polynomial regime.

The compression task is to discover that all nonboundary symbols can be
discarded after the unique adjacency matching is oriented. The remaining signed
word has only 20 symbols at shipping size. Solving that word, including both
sides of the adjacency index, costs 216–248 measured operations (296 worst
case), versus the full quadratic route. That gap, not worst-case complexity, is
the Track B hardness basis.

## Worked demo

For `make_instance(n=6, genes=2, distance=2, seed=3)`, the complete instance is:

```text
START: +9 +8 -3 -7 +1 -6 -2 +4 +2 +1 +5 -4 +6 +3 -5 -9
TARGET: +9 +8 -3 -6 -2 +4 +2 +1 +5 -4 +6 -1 +7 +3 -5 -9
```

The answer is `[6, 3]`.

```python
>>> verify(inst, [6, 3])
(True, 'ok')
>>> verify(inst, [6, 6])
(False, 'repeat identifiers must be pairwise distinct')
```

This demo is genuinely hand-scale: two reversals can be replayed directly on 16
symbols, and all 42 formatted candidates could be checked if necessary.

## Difficulty presets

| Preset | Repeats `n` | Genes | Chromosome symbols | Answer length | Candidate space |
|---|---:|---:|---:|---:|---:|
| demo | 6 | 2 | 16 | 2 | 42 |
| easy | 28 | 4 | 62 | 10 | 72,684,900,288,000 |
| medium | 36 | 4 | 78 | 10 | 1,264,020,397,516,800 |
| **hard (selected)** | **44** | **4** | **94** | **10** | **11,576,551,623,436,800** |

No preset has been rejected by a local gate. `hard` is the selected shipping
preset, but the required external oracle verdict is still unavailable because
OpenRouter rejected every call with HTTP 403 “Key limit exceeded.”

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified across all presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged, fenced JSON round-trip recovered exactly |
| G4 | pass | 0/200,000 structure-aware guesses; space `1.158e16` |
| G5 | pass | shipping density 0/200,000; strongest failing attack was 2,048 random restarts over 8 instances; demo has 2/42 exact answers |
| G6 | pass | six attacks each scored 0/8; reference and compressed algorithms each scored 8/8 |
| G7 | pass | `n=88` builds and verifies with a still-10-element answer |
| G8 | pass | 60/60 invariance/carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 37 answer characters, about 10 tokens, 10 atoms; 296-operation route bound |

## Oracle and G9 runs

The scripts created all three transcripts, but no call became a graded attempt.
Errors are not counted as model failures, so these runs make no hardness claim.

| Arm | Preset | Seeds | Solved / usable attempts | Result |
|---|---|---|---:|---|
| bare | easy | 1882808902, 1449894462, 1749140253, 1767831222 | 0/0 | four HTTP 403 key-limit errors; no verdict |
| structural hint | hard | 552207097, 409458476, 91471557, 1519910384 | 0/0 | four HTTP 403 key-limit errors; no verdict |
| placebo hint | hard | 1683801861, 1770646643, 519889651, 1757539984 | 0/0 | four HTTP 403 key-limit errors; no verdict |

`hinted − placebo` is therefore undefined, not evidence of zero hint effect. The
module records both rates as 0 only because the schema requires numeric fields;
`attempts: 0` and `hinted_verdict: "unrun"` carry the operative meaning.

## Use

```python
from gen_2302_03797 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=17, **DIFFICULTY["hard"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit with:

```bash
scripts/emit.sh results/2302.03797/gen_2302_03797.py
```

To complete the missing external evidence after restoring the OpenRouter limit,
rerun `python3 ../../scripts/harden.py gen_2302_03797.py` here, then rerun the two
G9 scratch arms as specified in the task.

## Caveats

- This synthetic distribution is screened against numeric, span, sign-parity,
  positional-greedy, static-boundary, and 256-restart attacks. Screening improves
  those measured attacks but is not evidence against every heuristic.
- The 0/200,000 estimate samples uniformly from exact-length, repeat-only,
  pairwise-distinct sequences. It does not condition on every intermediate
  reversal being legal, so it measures the declared answer language, not a prior
  from a solver that has already inferred dynamic applicability.
- The full boundary algorithm is successful by design and is reported separately,
  as Track B requires. No SAT/ILP/spectral attack is relevant to this native
  signed-sequence problem; exhaustive boundary-order enumeration was not run at
  shipping size.
- START and TARGET cannot be swapped for canonicalisation: the Section 4 family
  requires the target, but not the start, to contain one positive and one negative
  copy of every repeat. Label renaming, independent orientation gauges, and
  simultaneous reverse-negation are tested symmetries.
- `gvlib` is unnecessary here: all objects and checks are exact signed-integer
  sequence operations implemented with the Python standard library.
- Most importantly, the oracle pool is presently unreachable. The module is
  locally verified but must not be treated as a hardened corpus entry until a
  script-owned bare run returns `verdict: "hardened"`.
