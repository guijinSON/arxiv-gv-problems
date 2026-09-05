# arXiv:1102.0041 — rejected after full-text audit

| field | result |
|---|---|
| Attempted track | B (no-tool compression) |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Core / certificate | permutation / integer tuple |
| Paper object | full ordering of a multiset |
| Final gate | **H failed on Tracks A and B** |

The paper is Battaglia, Grossi, and Scutellà,
[“Consecutive Ones Property and PQ-Trees for Multisets: Hardness of Counting
Their Orderings”](https://arxiv.org/abs/1102.0041). Section 2, Problem 1 asks
for a word using every occurrence of a universe multiset such that every
required multiset is exactly the multiset of some contiguous substring.

The retained prototype inverse-generates a doubled cubic residue cycle and
requirements certified by its contiguous windows. Generation is valid and
verification is cheap and exact. It is not a shippable hard family.

## Decisive easy algorithm

Each prototype requirement is represented as one copy of every alphabet
symbol plus a three-symbol excess set `E_i`. Run the ordinary consecutive-ones
algorithm on the *sets* `{E_i}`. If it returns an ordering `pi`, the word
`pi + pi` is an exact witness for every original multiset requirement. Section
1.2 states that Booth–Lueker PQ-trees find an ordinary set-C1P ordering in
linear time.

At the attempted shipping setting (`p=83`, 56 triples), that algorithm handles
168 incidences over 83 symbols and then writes 166 answer entries. The
prototype's supposedly compact cubic route uses 285–292 counted arithmetic
operations and writes the same answer length. The two routes are comparable;
there is no Track-B compression gap. Track A is also false because the
certificate is produced in polynomial time on every generated instance.

Theorem 16 (#P-completeness) and Corollary 17 (NP-completeness) apply to the
general multiset problem, not this easy generated distribution. This is the
exact distinction the STEP-0 audit is meant to catch.

## Evidence

The script-owned hardener was run only far enough to confirm the diagnosis.
All three scored calls at `easy` returned valid witnesses:

| model | seed | result | wall time |
|---|---:|---|---:|
| `openai/gpt-5.6-terra` | 197252367 | solved | 28.76 s |
| `google/gemini-3.8-flash` | 1108342424 | solved | 159.95 s |
| `openai/gpt-5.6-terra` | 820471512 | solved | 115.85 s |

The partial script output is preserved in
`rejection_easy_oracle_transcript.jsonl`. The older local report is renamed
`rejected_selftest_report_pre_audit.json`; its original all-pass conclusion is
explicitly invalidated because its G6 panel omitted the successful domain
algorithm.

## Retained prototype

```python
import sys
sys.path.insert(0, "results/1102.0041")
import rejected_gen_1102_0041 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

Do not emit this module into the corpus. See [REJECTED.md](REJECTED.md) for the
gate-by-gate decision and the reasons the paper's other direct problem objects
do not furnish an acceptable replacement family.
