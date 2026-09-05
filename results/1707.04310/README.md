# Constrained shuffle into `(ab)*` — arXiv:1707.04310

Status: all local gates pass, but the required multi-vendor oracle verdict is
**not yet available**. The script-owned run on 2026-09-05 scored 13 attempts,
found the family too easy through word length 2,048, and then received HTTP 403
“Key limit exceeded” on every redraw. API errors are not model failures, so this
directory must not be submitted until `harden.py` completes its ladder.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer-tuple set-system partition |
| Intended intuition | invariant: project onto power-of-two positions |
| Domain essentiality | native |
| Reduction | none |

## The family

The source is Amarilli and Paperman, [*Topological Sorting under Regular
Constraints*](https://arxiv.org/abs/1707.04310). Section 2 defines constrained
shuffle: the solver is handed a tuple of words, equivalently a disjoint union
of labeled directed paths, and must interleave them while preserving each
path’s internal order. Here the fixed target language is `(ab)*`.

Every instance contains pointwise-complementary pairs of equal-length path
words. The requested witness is a partition of the path indices into those
pairs. For each pair, reading its `a` at a column and then its `b` produces
`ab`; concatenating the pairs gives a legal topological order. `verify` checks
the index partition and every symbol comparison exactly. It never reads the
planted answer.

## Why Track B, and what is actually hard

Theorem 3.6 proves that unrestricted `CSh[(ab)*]` is NP-hard, using the Section
3 shuffle reduction from the unary 3-PARTITION family in Lemma 3.2. That is not
a distributional hardness claim for this generator. This subclass has a known
linear algorithm: hash all words and look up each pointwise complement. Its
complexity is `O(nL)` time and storage; at the shipping preset the measured
mean is below 0.001 seconds and the accounting is 43,029 symbol/hash operations.

The no-tool compression is a projection. At 1-based positions 1, 2, 4, 8, 16,
and 32, every long word carries a unique six-symbol signature whose complement
identifies its partner. Reading 42 signatures and doing 21 lookups costs 273
operations. A solver that misses this invariant must process 21,504 displayed
symbols or reproduce the reference hashing route unaided.

The easy regimes were checked explicitly. Theorem 4.3 puts monomial target
languages in NL. Proposition C.2 gives an `O(k log n)`-space nondeterministic
algorithm for width `k`, and for CSh takes `k` to be the number of input
strings; it also notes a prior PTIME result. Neither is hidden here as Track-A
evidence. The successful special-purpose complement algorithm is reported as
the Track-B reference algorithm.

## Worked demo

For `make_instance(n=4, word_length=8, signature_bits=2, seed=0)`, the complete
word table is:

```text
0: aabbaabb
1: baabaabb
2: abbabbaa
3: bbaabbaa
```

The answer is `[[0,3],[1,2]]`. Calling `verify(inst, [[0,3],[1,2]])` returns
`(True, "ok")`. The corrupted partition `[[0,1],[2,3]]` returns
`(False, "paths 0 and 1 are not pointwise complements")`. A person can solve
this demo on paper by comparing the four eight-symbol rows.

## Difficulty presets

| Preset | Paths `n` | Word length `L` | Signature bits | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 8 | 2 | 4 | hand-scale illustration |
| easy | 22 | 64 | 5 | 22 | solved 3/3; rejected |
| medium | 34 | 256 | 6 | 34 | solved 2/3; rejected |
| hard | 42 | 512 | 6 | 42 | solved 3/3; rejected as a shipping rung |

`escalate` first doubles word length while leaving the 42-index witness fixed;
only after that axis is exhausted does it increase the number of paths. It now
returns `"cap_bound"` before the compact route would exceed 300 operations.

## Gate results

| Gate | Result |
|---|---|
| G1 planted verifies | 12/12 |
| G2 corruption | 5/5 rejected with five distinct reasons |
| G3 round trip | passed with prose and fenced JSON |
| G4 structure-aware guessing | 0/200,000; matching space 13,113,070,457,687,988,603,440,625 |
| G5 density and baseline | 0/200,000 shipping guesses; demo has exactly 1 answer; 43,029 reference operations |
| G6 attacks | four attacks, each 0/8; reference algorithm 8/8 as expected |
| G7 scaling | 84 paths of length 1,024 builds and verifies |
| G8 canonical key | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) caps | 200 chars, 127 conservative tokens, 42 atoms, 273 operations |

## Oracle loop and G9 arms

The bare run rejected all three named rungs and the first two fixed-answer-length
escalations. It stopped during the length-2,048 round after one scored success
and four HTTP-403 redraws, so the harness correctly produced no
`harden_verdict`.

| Preset | `L` | Seed | Model | Result / reason |
|---|---:|---:|---|---|
| easy | 64 | 791040540 | Terra | solved, `ok` |
| easy | 64 | 1838405354 | Gemini | solved, `ok` |
| easy | 64 | 1077956018 | Gemini | solved, `ok` |
| medium | 256 | 1580403849 | Gemini | solved, `ok` |
| medium | 256 | 1089158353 | Terra | solved, `ok` |
| medium | 256 | 582618203 | Terra | failed, non-complement pair |
| hard | 512 | 1389084143 | Gemini | solved, `ok` |
| hard | 512 | 1832101485 | Terra | solved, `ok` |
| hard | 512 | 571510731 | Terra | solved, `ok` |
| escalated | 1,024 | 1387194023 | Terra | failed, non-complement pair |
| escalated | 1,024 | 1399687967 | Gemini | solved, `ok` |
| escalated | 1,024 | 58156186 | Gemini | solved, `ok` |
| escalated | 2,048 | 1273432269 | Gemini | solved, `ok` |

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 3 / 3 at named `hard` | structural task was easy at this rung |
| structural hint | 0 / 0 scored | run blocked by account limit; no inference |
| placebo hint | 0 / 0 scored | run blocked by account limit; no inference |

The hinted-minus-placebo diagnostic is undefined until both scratch runs
complete; the module currently records `0.0` only because both diagnostic
denominators are zero. No claim about hint usefulness should be drawn from it.

## Use

```python
import importlib.util
import json

path = "results/1707.04310/gen_1707_04310.py"
spec = importlib.util.spec_from_file_location("gen_1707_04310", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

Because a dotted numeric directory is awkward in normal Python import syntax,
loading by `importlib.util.spec_from_file_location` is the portable alternative.
From the repository root, emit examples with:

```bash
bash scripts/emit.sh 1707.04310 20
```

The module is standard-library-only; it does not need `gvlib`.

## Caveats

The measured random prior is uniform over all perfect matchings after enforcing
the obvious shape and coverage constraints. It says nothing about a solver that
recognizes complementation; that solver succeeds in linear time and is disclosed
as the reference algorithm. Full lexicographic sorting or complement hashing
also makes the family easy with tools. The four failing attacks cover label-
frequency outliers, first-symbol greedy pairing, input adjacency, and 128 random
restarts; they do not cover every possible language-model pattern heuristic.

All paths have equal length and exactly half `a` symbols, and tuple order is
uniformly shuffled, so those simple planting signatures are absent. The
canonical key is exact under path reordering and global reverse-plus-label-swap;
its SHA-256 digest retains only the usual theoretical collision caveat. Most
importantly, the present oracle evidence is adverse, not merely absent: every
tested level had at least one successful oracle. The final ladder verdict is
still unavailable because the account limit interrupted the next required
attempts; this remains a release blocker rather than being presented as
hardness.
