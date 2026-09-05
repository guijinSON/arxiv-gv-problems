# Shuffle Product witness generator for arXiv:2605.03727

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style interleaving search |
| Certificate form | integer tuple (one native source choice per target position) |
| Intuition | change of variables: alternating bits of a target-position index identify its source coordinate |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

This module implements the native **Shuffle Product** object from Section 3,
Definition 1 of Bodlaender and Mallem, [“The Parameterized Complexity of
Scheduling with Precedence Delays: Shuffle Product and Directed
Bandwidth”](https://arxiv.org/abs/2605.03727).  A solver receives indexed source
words and a target word.  It must name, at every target position, which source's
next symbol was consumed.  The checker advances those source cursors, compares
symbols exactly, and checks that every source is exhausted.  Generation is
inverse: the complete interleaving map is chosen first and the target is composed
from it, so the generator never solves its own instance.

## Why this is Track B

Theorem 3.1 proves Binary Shuffle Product XNLP-complete when the number of source
words is the parameter.  That worst-case theorem is **not** asserted as hardness
evidence for this planted distribution.  The paragraph preceding the theorem
also states the easy regime that matters here: a fixed number of sources is
polynomial-time solvable by multidimensional dynamic programming.  With `k`
equal-length sources of length `m`, the implemented memoized form has at most
`(m+1)^k` states and `k` transitions per state.  It is disclosed as the successful
reference algorithm.

At the shipping preset (`n=192, k=8, m=24`), that reference algorithm solved all
8 measured seeds after 1,381,309 search-node visits total (maximum 469,299 for one
instance) in 9.14 seconds in the final gate run.  A family-aware projection scan also solved 8/8 in
53,184 counted operations.  The compact route is different: view target positions
in binary, use their alternating coordinates as the class name, and identify the
random source relabelling from the unique two-symbol prefixes.  Producing the
192-entry witness then takes 232 counted classifications, signature reads, and
lookups.  The benchmark tests whether a no-tool solver finds that coordinate
change, not whether Shuffle Product lacks an algorithm.

## Worked demo

For `make_instance(n=8, k=2, alphabet_size=4, signature_length=1, seed=0)`, the
complete rendered data are:

```text
Source words (0-based index: word):
0: dacb
1: abdc

Target word:
daabcdbc
```

The answer is `[0,1,0,1,0,1,0,1]`.
`verify(inst, answer)` returns `(True, "ok")`.  Dropping the last entry returns
`(False, "wrong length: expected 8, got 7")`.  This smallest setting is genuinely
hand-solvable: two four-symbol cursors suffice.

## Difficulty presets

| preset | target length `n` | sources `k` | source length | alphabet | signature | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 2 | 4 | 4 | 1 | paper-scale illustration; never ships |
| easy | 64 | 4 | 16 | 4 | 2 | first oracle rung |
| medium | 128 | 8 | 16 | 4 | 2 | second oracle rung |
| hard | 192 | 8 | 24 | 4 | 2 | **shipping preset** pending external oracle evidence |

After the named ladder, `escalate()` first reduces the alphabet to three and then
to two while keeping the 192-element answer fixed.  The next supported target
length is 256: its answer would sit exactly at the atom cap, but its compact route
would require 312 counted operations because the binary alphabet needs a
three-symbol signature.  It therefore reports `cap_bound` without crossing G9(c).

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verify; 16/16 are JSON-native |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | realistic fenced response round-trips; 4/4 garbage cases rejected |
| G4 | 0/200,000 structure-aware random guesses; candidate space has 553 bits |
| G5 | shipping sampled density 0/200,000; demo has exactly 1 valid answer among 70 |
| G6 | four attacks each 0/8; reference DP 8/8, 1,381,309 search-node visits, 9.14 s |
| G7 | doubled `n=384` instance verifies; language grows from 553 to 1125 bits |
| G8 | 80/80 invariance checks and 80/80 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | 576 characters, 385 lexical tokens, 192 atoms, 232 intended operations |

## Oracle loop and G9 arms

The required `harden.py` invocation was made, but OpenRouter rejected every
redraw with HTTP 403 `Key limit exceeded (total limit)`.  The harness correctly
counted none of these as a model failure and produced no hardness verdict.  The
four script-owned error records are retained in `llm_loop_transcript.jsonl`; they
are infrastructure evidence, **not** evidence that the family is hardened.

| run | preset | counted attempts | solved | status |
|---|---|---:|---:|---|
| bare hardening | easy | 0 | 0 | blocked by exhausted OpenRouter key |
| structural hint | hard | 0 | 0 | invocation blocked by the same exhausted key |
| placebo hint | hard | 0 | 0 | invocation blocked by the same exhausted key |

Thus hinted-minus-placebo is not yet measured.  Locally, the answer and intended
route are within G9(c)'s caps.  Re-run all three script-owned arms when the key has
credit; do not treat the zero-attempt placeholders as oracle results.

## Use

```python
from gen_2605_03727 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
candidate = parse_answer("<answer>" + str(inst["answer"]).replace(" ", "") + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2605.03727 20
```

## Caveats

The XNLP theorem is worst-case and does not establish hardness of this inverse
distribution.  G4 samples uniformly from all exact-multiplicity index sequences;
its 0/200,000 result estimates density under that prior only and is not a bound
against informed search.  The reference DP proves the family is mechanically
solvable, as Track B requires.  The panel did not test an optimized C/C++ DP, a
general SAT/SMT encoding, beam search wider than the stated random restarts, or
the four-vendor model pool because the supplied OpenRouter key was exhausted.
The two-symbol prefix signatures deliberately enable the compact invariant route;
if a solver recognizes the alternating-bit construction, the problem becomes
straightforward.  Finally, `canonical_key` exactly handles source reordering,
alphabet renaming, and simultaneous reversal, but it does not claim to canonicalize
every accidental equivalence between unrelated word tuples.
