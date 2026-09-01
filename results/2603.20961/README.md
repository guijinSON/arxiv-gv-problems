# Cyclic distinct-partial-sums generator

This module turns Costa, Della Fiore, Fontana, and Vena’s [*Graham conjecture on small sets in abelian groups*](https://arxiv.org/abs/2603.20961) into a witness-search problem. The solver receives a set of distinct nonzero residues modulo a prime and must order every residue exactly once so that the modular partial sums are pairwise distinct and every nonfinal partial sum is nonzero. Verification is exact and linear-time: check the permutation, accumulate modulo the prime, and reject zero or repeated partial sums.

## Why this regime is nontrivial

Section 1 supplies the exact definition of a *sequencing*. Theorems 1.4–1.6 prove universal existence only through sizes 20, 22, or 23, depending on extra zero-sum and inverse-pair assumptions. Section 3’s computation is a breadth-first contradiction tree; its polynomial bound is per node, not for the full growing search tree. The generator therefore makes `n` grow and ships at `n=120`, with nonzero total and no reliance on the extra zero-sum cases.

The sparse rectification regime quoted in Theorem 1.3 is deliberately avoided. At the shipping preset, 120 of the 126 nonzero residues modulo 127 are present. This crowding makes locally legal choices easy early and prone to strand the final elements. The planted order is sampled first as a path with distinct vertices and distinct nonzero increments, after which its increments are independently shuffled. There is no separately distributed decoy class. The paper does **not** prove NP-hardness or average-case hardness; trust here rests on exact gates, explicit attacks, and the required independent oracle loop, not on a complexity-theoretic reduction.

## Worked demo

The `demo` preset with seed 17 renders in full as:

```text
Cyclic distinct-partial-sums problem

Work in the cyclic additive group Z/13Z.  Its elements are the integer residues
0, 1, ..., 12; addition and every sum below are reduced modulo 13.

The following is an unordered set A of 10 distinct nonzero residues:
A = [8, 2, 9, 4, 6, 7, 3, 5, 1, 10]

Find a sequencing of A: output an ordered list a_1, ..., a_10 that uses every
member of A exactly once, with no repetitions.  For each 1-indexed position i,
define the inclusive partial sum p_i = (a_1 + ... + a_i) mod 13.  The residues
p_1, ..., p_10 must be pairwise distinct, and p_i must be nonzero for every
1 <= i < 10.  (The total sum p_10 is fixed by A and is nonzero in this
instance.)  Order matters.  Only the displayed canonical representatives
0 through 12 may be used.

Give your final answer inside <answer></answer> tags, as exactly 10 base-10
integers separated by commas, in the desired order.  Do not put brackets around
the list.  Example of syntax only: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

One answer is `<answer>9, 8, 6, 4, 5, 2, 10, 7, 3, 1</answer>`. Calling `verify(inst, answer)` returns `(True, "ok")`; dropping the final `1` returns `(False, "wrong length: expected 10, got 9")`.

## Difficulty presets

| Preset | `n` | Prime modulus | Nonzero residues omitted | Status |
|---|---:|---:|---:|---|
| `demo` | 10 | 13 | 2 | Oracle solved; also far too guessable to ship |
| `easy` | 120 | 127 | 6 | **Shipping; all gates and oracle loop held** |
| `medium` | 144 | 157 | 12 | Reserve escalation rung; G1 checked, not reached by oracle |
| `hard` | 168 | 179 | 10 | Reserve escalation rung; G1 checked, not reached by oracle |

`escalate()` increases `n` faster than slack, so the unused fraction does not grow. Prime gaps can change the exact number omitted.

## Gate results at shipping difficulty

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted witnesses verified across every preset and four seeds |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 120 integers recovered through prose, a Markdown fence, whitespace, and copied brackets; garbage returned `None` |
| G4 | 0/200,000 uniform random permutations verified |
| G5 | Exact demo-scale check: 838/362,880 valid at `n=9`, modulus 11 (0.0023093) |
| G6 | Outlier 0/8, deterministic greedy 0/8, and 128-restart local random walk 0/8 |
| G7 | Doubled `n=240`, modulus 257 instance built and its plant verified |
| G8 | 7,420/7,420 checks preserved the key and carried witness: every cyclic automorphism composed with reversal, plus all 2,380 adjacent input-swap generators; 20/20 unrelated keys distinct |

The machine-readable measurements are in [selftest_report.json](./selftest_report.json).

## Oracle hardening loop

All non-error calls used medium reasoning effort. A level is solved if any model returns a verified witness.

| Preset | Model | Seed | Result | Why |
|---|---|---:|---|---|
| `demo` | Anthropic Claude Sonnet 5 | 367897430 | Solved | Parsed witness verified `ok` |
| `demo` | OpenAI GPT-5.6 Terra | 1638876883 | Solved | Parsed witness verified `ok` |
| `demo` | Google Gemini 3.1 Pro Preview | 1457160171 | Solved | Parsed witness verified `ok` |
| `easy` | Anthropic Claude Sonnet 5 | 1868462075 | Failed | Empty length-limited reply after 32,000 completion tokens |
| `easy` | OpenAI GPT-5.6 Terra | 1219817675 | Failed | Proposed order collided at partial sums 28 and 67 (residue 126) |
| `easy` | xAI Grok 4.6 | 1026399348 | Error, excluded | Connection reset; harness redrew this slot |
| `easy` | Google Gemini 3.1 Pro Preview | 667727418 | Failed | Proposed order collided at partial sums 13 and 22 (residue 74) |

The harness verdict is `hardened` at `easy` after one escalation. Full replies and timings are in [llm_loop_transcript.jsonl](./llm_loop_transcript.jsonl); seeds, vendor pool, and verdict are in [.meta.json](./.meta.json).

## Use

```python
import random
import gen_2603_20961 as gen

inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
answer = gen.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert gen.verify(inst, answer) == (True, "ok")
guess = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit fresh canonical-key-deduplicated samples with:

```bash
bash scripts/emit.sh 2603.20961 20 easy
```

## Caveats

The 0/200,000 G4 result is an empirical rate under one explicit prior—uniform permutations of the supplied set. It is not a statistical proof that the true probability is zero, and it says nothing by itself about a solver that prunes locally illegal prefixes. G6 addresses that gap only up to 128 random restarts on each of eight seeds. The demo exact count also shows why factorial search-space size alone is not evidence of hardness.

The attack panel did not try industrial SAT/CP encodings, deep backtracking, meet-in-the-middle methods, learned policies, or substantially larger restart budgets. One of the three decisive oracle failures was an empty length-limited response; the other two were parsed, concrete but invalid witnesses. The canonical key is exact for input reordering and every cyclic-group automorphism `x -> u*x`; translations are not symmetries of the increment-set problem. Finally, the source paper is an existence paper, not a computational-hardness paper. A future polynomial sequencing algorithm, or a better dense-instance construction heuristic, would invalidate the H claim even though G and V would remain intact.
