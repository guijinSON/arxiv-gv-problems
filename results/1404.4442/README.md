# Distant successors in the middle-levels Dyck permutation

**Status: locally verified, but not shippable yet.** The required four-vendor run is incomplete because the supplied OpenRouter key reached its total spending limit during the one G9-permitted upward move. G9 is therefore recorded as failed/pending, not silently passed, and this paper is not rejected.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation iteration |
| Certificate form | exact symbolic (one Dyck bitstring) |
| Intended intuition | change of variables: view the word as a rooted plane-tree contour |
| Domain essentiality | native |
| Reduction | none |

This module uses native intermediate objects from Torsten Mütze’s [*Proof of the middle levels conjecture*](https://arxiv.org/abs/1404.4442). A solver receives a Dyck word (p), the exact Section 5 successor rule (g_1), and a large exponent (T); it must return (g_1^T(p)). The checker enumerates the finite (g_1)-orbit and compares the submitted bitstring exactly. It never reads `inst["answer"]`.

## Why this is Track B

This is not an average-case hardness claim. The paragraph after Theorem 2 says the paper’s Hamilton cycles are constructible in time polynomial in the middle-level graph size, and Lemmas 15–18 make this particular intermediate permutation explicitly tractable. The exact reference algorithm enumerates at most 2n orbit states, taking O(n^2) symbol operations. On eight current shipping instances at n=36, it used 82,092 operations total (10,261 average) and 0.003985 seconds.

The compact route uses Lemma 16, (h\circ g_0=g_1\circ h). Under the Dyck-word/ordered-tree bijection of Section 5, (g_0) merely advances the distinguished root corner of the underlying plane tree. Thus a solver who sees the change of variables can invert (h), reroot once by the reduced exponent, and apply (h) again. The audited post-insight bound is 145 exact integer updates; without it, the solver tabulates the orbit. Generator answers are made as (h(g_0^T(q))) from a sampled source (q), so generation composes a proved identity rather than solving the visible iterate.

Small (n) is the easy regime because there are at most (2n) states to write down. The original (n=18) rung held against the bare pool but failed G9(b): one of three structurally hinted oracles solved it. The single allowed upward move is (n=36). Its first new bare oracle failed, but the remaining calls could not be made after the OpenRouter key reported `limit_remaining: 0`; that external quota is not evidence of hardness or of failure.

## Worked demo

At `seed=0`, the demo renders the definitions shown by `render()` and the following instance data:

```text
Starting Dyck word p: 101100
Cosmetic query label: query-c2094ca
Semilength n: 3
Requested number of iterations T: 14
```

The answer is `<answer>110010</answer>`. A person can solve this demo by listing its three-state orbit. `verify(inst, "110010")` returns `(True, "ok")`; dropping the final bit returns `(False, "answer word is too short: expected 6 bits")`.

## Difficulty presets

| Preset | (n) | Full laps in (T) | Answer bits | Candidate space | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 2 | 6 | 5 | hand-solvable; hardener skips it |
| **easy (provisional ship)** | **36** | **100,003** | **72** | (C_{36}=11,959,798,385,860,453,492) | final oracle evidence blocked by quota |
| medium | 60 | 10,000,019 | 120 | (C_{60}) | locally verified |
| hard | 96 | 100,000,007 | 192 | (C_{96}) | locally verified |

The old (n=18) easy rung was removed after G9(b), and the ladder was slid upward once as permitted. `SHIPPING_DIFFICULTY` points at the new `easy`, but emission should wait until G9 is completed.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted words verified; compact construction matched 12/12 |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose and fenced output both round-tripped |
| G4 | pass | 0/200,000 structured Dyck guesses; exact density (1/C_{36}=8.3613\times10^{-20}) |
| G5 | pass | exactly one valid output; reference cost 82,092 operations/8 instances |
| G6 | pass | five attacks at 0/8 each; reference orbit algorithm 8/8 as expected |
| G7 | pass | doubled (n=72) instance built and verified; all preset spaces increase |
| G8 | pass | 60 invariance and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **incomplete** | 74 JSON characters, 72 bit atoms, 19 estimated tokens, 145 intended operations; final hinted and placebo arms not run |

## Oracle evidence

The initial bare (n=18) run held 0/3, but its transcript was overwritten when the required upward rerun began. The preserved G9 diagnostic for that rejected rung is `g9_rejected_easy_transcript.jsonl`:

| Arm/rung | Model outcome | Result |
|---|---|---|
| structural hint, (n=18) | GPT-5.6 Terra | failed, incorrect iterate |
| structural hint, (n=18) | Claude Sonnet 5 | failed, empty length-limited completion |
| structural hint, (n=18) | Grok 4.6 | **solved** |
| final bare, (n=36) | GPT-5.6 Terra | failed, incorrect iterate |
| final bare, (n=36) | four redraws | HTTP 403 key-total-limit errors; not scored |

At the final (n=36) rung the valid G9 arm counts are bare 0/1, hinted 0/0, and placebo 0/0, so hinted-minus-placebo is undefined. No conclusion about the intended intuition is drawn from missing calls. The old (n=18) result does show that explicitly naming the root-corner conjugacy can materially help a solver at smaller size.

## Use

```python
import random
import gen_1404_4442 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer(f"<answer>{inst['answer']}</answer>")
assert g.verify(inst, candidate) == (True, "ok")
guess = g.random_candidate(inst, random.Random(7))
```

After the oracle quota is restored and G9 passes, emit from the repository root with:

```bash
bash scripts/emit.sh 1404.4442 20 easy
```

## Caveats

- A sandbox makes the family easy: exact orbit enumeration solves every instance quickly. This is precisely why the module declares Track B.
- The (0/200{,}000) guess result is relative to the structure-aware prior uniform over all Dyck words, not arbitrary binary strings. Uniqueness gives the exact density independently of that sample.
- The adversary panel tried the fixed-point guess, one and four visible iterations, the lexicographically extreme Dyck word, and 256 uniform restarts. A raw cyclic-rotation heuristic was deliberately not listed as failing: it solved 1/8 at the discarded (n=18) rung. No external symbolic algebra system was tried; the exact orbit enumerator is the relevant successful reference method.
- `canonical_key` removes cosmetic query labels and data-line order and reduces the exponent by the exactly observed orbit. It does not attempt to identify different Dyck encodings of isomorphic unrooted plane trees, because those are different starting states of the stated permutation problem.
- The compact-operation figure counts exact height/root-index updates. Recursive applications of (h) also require symbol rearrangement; the 72-bit output remains well below the transcription cap, but the operation figure should not be read as a wall-clock model.
- The current `llm_loop_transcript.jsonl` is a script-written but incomplete quota-blocked run, while `.meta.json` still contains the preceding (n=18) verdict because the interrupted rerun could not update it. Neither is valid final shipping evidence. Restore quota and rerun bare, hinted, and placebo arms; do not submit the present directory.
