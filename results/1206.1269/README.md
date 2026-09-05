# Fourfold-cycle Delta-1 coloring generator

This is a locally verified generator for [Cranston and Rabern, *Coloring claw-free graphs with Delta-1 colors*](https://arxiv.org/abs/1206.1269). It is **not yet shippable**: every local gate passes, but the required multi-vendor oracle run was refused by OpenRouter with HTTP 403 `Key limit exceeded (total limit)`. Those errors are preserved in the script-owned transcript and are not counted as model failures.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: one color per multigraph edge |
| Objects | 8-regular multigraph, four-edge parallel bundles, its claw-free line graph |
| Intuition | decomposition: contract parallel twins to quotient cycles |
| Domain essentiality | native |
| Reduction | paper-licensed line-graph equivalence from Section 6 |

## The problem and why the witness is trustworthy

The solver receives a multigraph whose components are cycles with every link replaced by four parallel edges. It must assign one of ten displayed labels to each edge so that incident edges have different labels. This is exactly vertex coloring the line graph: multigraph edges become line-graph vertices and shared endpoints become adjacency.

Every base vertex has degree 8. A parallel edge conflicts with its three mates and four other edges at each endpoint, so the line graph has `Delta=11`. The quotient has girth at least five, so every line-graph clique has at most eight vertices; Theorem 5.5 therefore puts it in the paper's `Delta-1=10` regime. Section 6 treats line graphs in these native multigraph terms, Theorem 6.1 states the line-graph case, and Theorem 6.6 proves the stronger list-coloring bound when the multigraph has minimum degree at least 7.

The answer is known by composition, not by solving. Even quotient cycles alternate the disjoint sets `0123` and `4567`. Odd cycles use that alternation followed by the five-set closing identity `0123, 4567, 0189, 2345, 6789`. Consecutive sets, including the wraparound pair, are disjoint; their four labels can be assigned arbitrarily within each parallel bundle.

## Why Track B

This is deliberately not a Track A claim. The polynomial reference algorithm contracts the bundles and runs dynamic programming over the `C(10,4)=210` possible color sets, with complexity `O(n*C(10,4)*C(6,4))`. At the hard preset, eight runs took 0.544 seconds total and at most 220,134 counted operations. Once the decomposition and five-set identity are seen, the compact route needs 236 color placements. The paper itself identifies the nearby easy/failing boundary after Theorem 6.6: tripling every edge of a 5-cycle gives the sharp `delta(H)=6`, `Delta=8` counterexample in Figure 1(d); multiplicity four here gives `delta(H)=8` and `Delta=11`.

## Worked demo

The `demo` preset with seed 7 renders as follows; a person can solve it on paper by following the five bundles around the quotient cycle and using the five-set identity.

```text
Base vertices: 0, 1, 2, 3, 4
Allowed labels: 1950, 9779, 1791, 2542, 9313, 4517, 2186, 6991, 7468, 3471
0--1 : 1 19 18 12
4--0 : 8 2 7 0
2--3 : 10 11 9 16
4--3 : 4 17 6 13
2--1 : 5 15 14 3
```

One answer, in edge-id order, is:

```text
[4517, 7468, 1791, 9779, 9779, 2542, 7468, 9313, 2542, 2186,
 9313, 4517, 6991, 3471, 1950, 1791, 6991, 1950, 3471, 2186]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the second edge color in the first displayed bundle by the first returns `(False, "parallel bundle 0 repeats a color")`.

## Difficulty presets

| Preset | Quotient bundles `n` | Max components | Answer entries | Status |
|---|---:|---:|---:|---|
| demo | 5 | 1 | 20 | hand-scale example |
| easy | 39 | 5 | 156 | first oracle rung; service unavailable |
| medium | 49 | 6 | 196 | locally verified |
| hard | 59 | 7 | 236 | current shipping designation; locally verified |

`escalate()` reaches 63 bundles (252 entries) and then reports `cap_bound`; further growth would violate the 256-element output cap.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses and structural promises verified |
| G2 | pass | five corruption modes rejected with five distinct reasons |
| G3 | pass | 236-entry tagged response round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware random candidates valid |
| G5 | pass | exact log10 density `-67.3506`; DP max 220,134 operations |
| G6 | pass | four attacks, 0/8 successes each; reference DP 8/8 as expected |
| G7 | pass | 63-bundle escalation and doubled `n=118` both verify |
| G8 | pass | 100 invariance and 100 carried-witness checks; 20/20 distinct structures |
| G9(c) | pass | 1,181 chars, 296 estimated tokens, 236 atoms, 236 intended operations |

## Oracle loop and G9 arms

No valid oracle attempt has occurred. On the final bare retry, `harden.py` drew OpenAI and Google at the easy rung, but four consecutive calls returned the account-level HTTP 403 before the harness stopped. The two G9 scratch runs independently saw the same error from Anthropic and xAI as well. This is infrastructure evidence, not hardness evidence.

| Preset | Seed(s) | Valid solved/attempts | Outcome |
|---|---|---:|---|
| easy | 980340024, 497899936, 277203518, 172221090 | 0/0 | four API errors; no verdict |

| G9 arm | Solved/attempts | Verdict |
|---|---:|---|
| bare | 0/0 | not run |
| structural hint | 0/0 | not run |
| placebo hint | 0/0 | not run |

The hinted-minus-placebo statistic is therefore undefined in substance (stored as `0.0` only because both denominators are zero). No conclusion about hint responsiveness is warranted until the three script-owned runs complete.

## Use

```python
from gen_1206_1269 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
question = render(inst)
answer = parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful oracle rerun and updated G9 evidence:

```bash
bash scripts/emit.sh 1206.1269 20 hard
```

## Caveats

The generated distribution is a structured subfamily, not arbitrary claw-free graphs. It becomes easy with a script because bundle contraction and a 210-state DP solve every instance; this is exactly why the module declares Track B. The `0/200,000` guess result samples candidates that already use four distinct labels inside every bundle, but it deliberately does not enforce disjointness between incident bundles—that is the problem itself. It measures density under that prior, not semantic difficulty for a reasoner.

The panel did not run a general SAT/ILP encoding or a production graph-coloring package; the exact cycle-CSP DP is stronger for this distribution and is reported openly. Random relabeling removes degree, position, and palette-label outliers, but it cannot hide the promised multicycle representation. Most importantly, the required four-vendor bare, hinted, and placebo measurements remain missing until the OpenRouter account limit is restored.
