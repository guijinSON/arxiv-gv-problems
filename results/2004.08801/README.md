# arXiv:2004.08801 — carefully synchronizing a partial automaton

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | other (power-automaton reachability versus a compressed word) |
| Certificate | exact symbolic straight-line program (SLP) |
| Native objects | partial finite automaton, careful reset word, subset trajectory |
| Intended intuition | invariant: a reset transversal exposes fixed-point counts and two-step path signatures |
| Domain essentiality / reduction | native / none |

## What the problem is

The source is Jakub Ruszil, [*On synchronization of partial automata*](https://arxiv.org/abs/2004.08801). A solver receives the complete transition table of a partial finite automaton. It must choose and order letters in a small recursive SLP whose exponentially expanded word is defined from every initial state and sends all states to one state. The checker composes partial state maps exactly, so it never expands that word and never reads the planted answer.

Generation follows the paper rather than solving a finished instance. Lemma 1 supplies the recursive base-`d` counter word. Section 3, Theorem 2 transforms a one-letter constant-reset DFA into the carefully synchronizing PFA used here, and Corollary 2 gives its exponential reset length. Simultaneous state/alphabet relabelling and padding states carry this known certificate. Every true digit letter receives a decoy with the same one-letter functional-graph type, defined count, rank, fixed-point count and component multiset; the decoy agrees on the first tick but is undefined on the second.

## Why Track B

Fact 1 gives the standard exact method: breadth-first search in the power automaton, with worst-case cost `O(|Sigma| |Q| 2^|Q|)`. At the shipping preset it succeeded 8/8, as it should: mean 2,189 visited subsets, 115,427.625 exact transition lookups, and 0.0171 s (maximum 0.0187 s). The raw shortest word has 2,188 letters. This is fast on a computer and unreasonable by hand. Once the joint invariant is seen, the SLP is recovered in 154 table operations: inspect the total letter's image, classify each digit candidate there by fixed/undefined behavior, and distinguish its real/decoy pair by the second tick.

This is not a Track-A claim. The paper itself gives both the power-automaton characterization (Fact 1) and explicit recursive construction (Lemmas 1–3). Small counter depth is easy, as is the unscrumbled paper notation where `b_i` already reveals each role. The generator therefore shuffles names and uses matched decoys; omitting either makes the compact route nearly explicit.

## Worked demo (`n=3`, `d=3`, seed 7)

The following is the full rendered instance, apart from the repeated output-format example at the end:

```text
Carefully synchronizing a partial finite automaton

A partial finite automaton has a finite state set, an alphabet, and at most one transition for each (state, letter) pair. A word is carefully synchronizing when every letter can be applied at every currently possible state and, after the whole word, all initial states have the same final state.

This instance has 18 states, counter depth n=3, and radix d=3.
State order: s00 s01 s02 s03 s04 s05 s06 s07 s08 s09 s10 s11 s12 s13 s14 s15 s16 s17
Alphabet: x00 x01 x02 x03 x04 x05 x06 x07

x00: [s15 - - s07 s04 s13 s06 s02 s08 - s10 s01 s12 - - - - s17]
x01: [s00 - - s07 s16 s13 s06 - s08 - s04 s01 s12 - - s15 - s17]
x02: [s13 s01 s03 s03 s01 s13 s01 s03 s01 s01 s13 s01 s03 s13 s13 s03 s13 s03]
x03: [- s09 s02 s03 - s05 s08 s07 - - s00 - - s13 s14 - s17 s15]
x04: [- - s13 - - s13 - - - - - s13 - - - - - -]
x05: [- - s02 s03 s04 - s10 s07 s16 - - s01 - s14 s05 s15 - s17]
x06: [s04 - s02 s03 s12 - s06 s07 s15 - s10 s01 - s14 - - - s17]
x07: [- s09 s02 s03 - s05 - s07 s04 s11 - - s15 s13 s14 - s06 -]

start class: x02
digit class: x00 x01 x03 x05 x06 x07
finish class: x04

For ordered digits [g1,g2,g3], W0 is empty and Wi=(W(i-1) gi)^2 W(i-1).
The submitted SLP denotes start W3 finish, an expanded word of 28 letters.
```

The answer is:

```json
{"start":"x02","digits":["x07","x05","x00"],"finish":"x04"}
```

`verify` returns `(True, "ok")`. Swapping the first two digits gives `{"start":"x02","digits":["x05","x07","x00"],"finish":"x04"}` and returns `(False, "compressed word encounters an undefined transition")`. This demo is genuinely hand-solvable: `x02` has image `{s01,s03,s13}`; the real member of each matched pair is the one whose moved image permits a second tick, and their fixed-point counts on that transversal determine the order.

## Difficulty

| preset | n | radix | states | digit candidates | candidate SLPs | expanded length | route ops |
|---|---:|---:|---:|---:|---:|---:|---:|
| demo | 3 | 3 | 18 | 6 | 120 | 28 | 42 |
| **easy (ships)** | **7** | **3** | **42** | **14** | **17,297,280** | **2,188** | **154** |
| medium | 8 | 3 | 48 | 16 | 518,918,400 | 6,562 | 192 |
| hard | 9 | 4 | 72 | 18 | 17,643,225,600 | 262,145 | 252 |

No named preset was rejected by a local gate. The available OpenAI oracle held `easy`, so the ladder did not advance. Radix escalation grows the expanded counter trajectory without lengthening the answer and stops before the 300-operation no-tool cap.

## Gate results

| gate | result |
|---|---|
| G1 | 16/16 preset/seed certificates verified; 16/16 answers JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered through surrounding prose and a Markdown fence |
| G4 | 0/200,000 structure-aware guesses; exact density `1/17,297,280 = 5.7813e-8` |
| G5 | one valid bounded SLP by construction; BFS mean 2,189 nodes / 115,427.625 lookups |
| G6 | four attacks each 0/8; reference BFS 8/8 as expected on Track B |
| G7 | doubled `n=14` verified; space 3,497,296,636,753,920,000; expanded length 4,782,970 |
| G8 | 60/60 composed relabellings invariant, 60/60 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 83 characters, 21 estimated tokens, 9 atoms, 154 intended operations |

The failing attacks are single-letter outlier ranking, fixed public order, 256 structure-aware random restarts, and a one-tick transversal greedy rule. The domain-standard power-automaton BFS is intentionally reported separately as the successful Track-B reference algorithm.

## Oracle loop and G9 diagnostics

The script-generated provisional bare run used the one reachable pool member:

| preset | seed | model | solved | outcome |
|---|---:|---|---:|---|
| easy | 176016504 | openai/gpt-5.6-terra | no | parsed SLP hit an undefined transition |
| easy | 1903256366 | openai/gpt-5.6-terra | no | parsed SLP hit an undefined transition |
| easy | 1690339596 | openai/gpt-5.6-terra | no | incorrectly claimed no valid SLP |

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/3 | held |
| structural hint | 0/3 | held |
| placebo hint | 0/3 | held |

Hinted minus placebo is `0.0`. For this vendor, naming the intended invariant bought nothing; that may mean the remaining table execution was still too demanding, so it is weak evidence for the declared intuition rather than proof of it. Each arm has its own script-written transcript.

## Use

```python
from gen_2004_08801 import make_instance, verify, DIFFICULTY

inst = make_instance(seed=7, **DIFFICULTY["demo"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit 20 shipping instances with:

```bash
bash scripts/emit.sh 2004.08801 20 easy
```

## Caveats

The mandatory cross-vendor run could not finish: the default Google member returned OpenRouter HTTP 403 `Key limit exceeded (total limit)` on every redraw. `multi_vendor_failed_transcript.jsonl` and `multi_vendor_failed_meta.json` preserve those errors. The shipping transcript is therefore a transparent **single-vendor provisional result**, not the requested multi-vendor hardness evidence; rerun `python3 ../../scripts/harden.py gen_2004_08801.py` when that key limit is repaired.

The generator augments the paper's automaton with padding and matched decoys, although the paper's native PFA and theorem-backed word remain visible and exact. The question asks for a word in the stated recursive SLP language, not an arbitrary raw reset word. The G4 probability is uniform over all ordered `n`-selections from the public digit class; it does not model a solver using cross-letter correlations. Color refinement is a strong relabelling invariant, not a complete automaton-isomorphism canonical form, so exotic non-isomorphic collisions remain possible. I did not test SAT/SMT encodings, bidirectional subset search, or automata-semigroup packages; exact power-automaton BFS is the paper's own standard characterization and was tested directly. Finally, the mechanical algorithm is extremely fast on a computer—this is precisely a no-tool compression benchmark, not a computational-hardness claim.
