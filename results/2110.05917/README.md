# Non-Monotone 2-3Sat witness generator

This module turns Section 3 of Lü and Wu, [“On complexity of substructure connectivity and restricted connectivity of graphs”](https://arxiv.org/abs/2110.05917), into satisfiable Boolean-formula search instances. A solver receives 2- and 3-literal OR clauses and must return one signed literal for every variable. Checking is just exact substitution into every clause. Generation is inverse: the complete assignment is sampled first, then a connected cubic one-in-three core and its clauses are constructed around it.

## Why this family is hard

Section 3 defines **Non-Monotone 2-3Sat** precisely: clauses contain two or three distinct variables, and every 3-clause contains both signs. The paper’s Theorem 3.1 states that this problem is NP-complete. The generated subfamily encodes Cubic Monotone 1-in-3 SAT—NP-complete even with a planar cubic incidence graph in [Moore and Robson, Section 3.1](https://arxiv.org/abs/math/0003039)—using one mixed-sign 3-clause and three 2-clauses per exact-one constraint. Every variable occurs in exactly three core constraints, and the core is connected.

Two easy regimes had to be avoided. Mixed-sign 3-clauses alone are satisfied by both constant assignments, while 2-clauses alone are polynomial-time 2-SAT. The paper gives no FPT algorithm for this source problem; Section 4 instead lists parameterized complexity as future work. This generator mixes both arities, keeps degree 3, and grows `n`. A first balanced random-clause version was rejected because bounded WalkSAT solved 7/8 shipping trials; the regular locked-core version below passed the same attack 0/8.

## Worked example

<details><summary>Full <code>render(make_instance(n=12, degree=3, seed=0))</code></summary>

```text
Non-Monotone 2-3Sat witness problem

There are 12 Boolean variables, numbered 1 through 12 (1-indexed).
A positive literal +i is true exactly when variable i is true; a negative
literal -i is true exactly when variable i is false. A clause is an OR:
it is satisfied when at least one listed literal is true. Satisfy every
clause simultaneously. Each line below is one clause; literal order and
clause order have no meaning. Variables within a clause are distinct.
Every clause has two or three literals, and every three-literal clause
contains at least one positive and at least one negative literal.

Clauses (48):
C1: +10 -5 +11
C2: +3 -8
C3: +5 +12
C4: +5 -11
C5: +6 +9
C6: -1 -9 +8
C7: -10 -7
C8: -8 +1
C9: +3 -4
C10: -2 +6
C11: +9 -8
C12: +5 -11
C13: -11 -10
C14: -6 +7 +2
C15: -8 -11
C16: +9 +3
C17: +5 -10
C18: -5 +11 -12
C19: +12 +1
C20: +4 -12 -3
C21: +6 -2
C22: -4 +12
C23: +6 -2
C24: -10 -2
C25: -7 +5
C26: -4 +3
C27: -7 -2
C28: -11 +12
C29: +6 -10
C30: +3 +12
C31: -1 +4 -12
C32: +10 -6 +2
C33: -7 +3
C34: -4 -7
C35: -11 +1
C36: -8 +1
C37: -3 +7 +4
C38: +7 +10 -5
C39: -10 +5
C40: -2 +9
C41: -6 +2 -9
C42: +6 -7
C43: +11 -1 +8
C44: -4 +12
C45: +8 -3 -9
C46: -4 +1
C47: +9 +1
C48: -8 +9

Output exactly 12 comma-separated signed integers in variable order.
At position i write +i to set variable i true or -i to set it false.
Every variable must occur exactly once; repetitions are forbidden.
Order inside the answer therefore matters and is fixed as 1,2,...,n.

Give your final answer inside <answer></answer> tags, as signed integers.
Example: <answer>1, -2, 3</answer>
Output nothing else inside the tags.
```

</details>

The planted witness is `<answer>1, -2, 3, 4, -5, -6, -7, 8, 9, -10, -11, 12</answer>`. `verify(inst, inst["answer"])` returns `(True, "ok")`. Swapping its first and last entries returns `(False, "literals must appear in variable order")`.

## Difficulty presets

| Preset | `n` | Core degree | Clauses | Status |
|---|---:|---:|---:|---|
| `easy` | 12 | 3 | 48 | Readable example; all three oracles solved it |
| `hard` | 384 | 3 | 1,536 | **Shipping**; all three hard-level oracles failed |

`escalate()` increases `n` by 50% (rounded to a multiple of 3) without raising degree: larger degree made local search easier in development.

## Mandatory gates

| Gate | Result |
|---|---|
| G1 planted verifies | pass, 8/8 preset/seed pairs |
| G2 corruption | pass, 5/5 rejected with 5 distinct reasons |
| G3 round-trip | pass, all 384 signed entries recovered from prose/fence output |
| G4 structure-aware guessing | pass, **0/200,000** uniform valid-shape assignments |
| G5 sparse exact count | pass, 1 solution / 262,144 assignments at `n=18` |
| G6 adversaries | pass, occurrence 0/8; greedy 0/8; WalkSAT restart 0/8 |
| G7 scale | pass, `n=768`, 3,072 clauses, plant verifies |
| G8 canonical key | pass, 100/100 invariant/carry-through checks; 20/20 unrelated keys distinct |

## Oracle loop

The script-selected master seed and full replies are in `llm_loop_transcript.jsonl`; `.meta.json` records `verdict: hardened` and the shipping parameters.

| Preset | Model | Seed | Result | Checker reason |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6-terra | 2,026,641,607 | solved | `ok` |
| easy | Anthropic Claude Sonnet 5 | 356,851,352 | solved | `ok` |
| easy | Google Gemini 3.1 Pro Preview | 803,993,910 | solved | `ok` |
| hard | Google Gemini 3.1 Pro Preview | 929,392,153 | failed | clause 2 unsatisfied |
| hard | OpenAI GPT-5.6-terra | 1,504,949,052 | failed | clause 17 unsatisfied |
| hard | xAI Grok 4.6 | 263,488,228 | failed | clause 3 unsatisfied |

All six replies parsed; the hard failures are not parser failures.

## Use

```python
import random
import gen_2110_05917 as gen

inst = gen.make_instance(seed=42, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
prompt = gen.render(inst)
answer = gen.parse_answer("<answer>...</answer>")
ok, reason = gen.verify(inst, answer)
candidate = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit 20 independently seeded shipping instances with:

```bash
bash scripts/emit.sh 2110.05917 20 hard
```

## Caveats

The `0/200,000` guess result measures a uniform prior over all correctly shaped assignments; it does not estimate a CDCL solver, an exact-cover solver, or a learned prior. The attacks are deliberately cheap and bounded; no industrial SAT solver, spectral planted-partition attack, or exhaustive average-case study was run. NP-completeness is worst-case evidence, not a proof that every random planted core is hard; the three-vendor oracle result is additional but still finite evidence.

The structural key deliberately ignores literal signs because independent truth-name changes give a bijection between witnesses. It uses exact degree, hyperedge-intersection, and 14 closed-walk moments, so it is a strong polynomial invariant but not a complete isomorphism canonical form; rare non-isomorphic collisions are possible. `n` must be a multiple of 3. Repeated 2-clause lines can occur when two core hyperedges share a variable pair; they are semantically harmless but slightly reduce effective clause count.

Finally, this module intentionally does **not** use the paper’s proposed separator generator. The displayed RCTSVS definition in Section 3 has no separator-size budget, while Theorem 3.2’s proof silently assumes `|S| = n + 2m + p`; relying on that unstated constraint would overclaim the paper’s result. The present family uses the explicitly defined Theorem 3.1 source problem instead.
