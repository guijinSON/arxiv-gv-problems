# Verified IPDS-Extension generator for arXiv:2306.09870

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (a vertex set, the paper's native witness) |
| Native objects | IPDS-Extension graph, propagating vertices, implication arcs, selectable/excluded vertices |
| Intuition | reduction recognition |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 3.4, Lemma 10 |

## What this is and whether to trust it

The family asks for a fixed-cardinality implicating power dominating set. The
solver receives exactly the IPDS-Extension objects introduced in Thomas Bläsius
and Max Göttlicher, [*An Efficient Algorithm for Power Dominating Set*](https://arxiv.org/abs/2306.09870):
an undirected graph, directed implication arcs, propagating vertices, and an
excluded/selectable partition. A candidate is checked by exact set operations:
closed-neighborhood domination, implication closure, and the rule that an
observed propagating vertex with exactly one unobserved neighbor observes it.

Generation is inverse, not solve-then-hide. It samples a Boolean assignment,
draws clauses that it satisfies, turns each Boolean variable into two monotone
input vertices, and applies the paper's Lemma 10 AND/OR gadget. The chosen input
vertices are therefore a certificate by construction. `verify()` never reads
`inst["answer"]`, and accepts any correctly formatted selected set whose exact
observation closure is the whole graph.

Each planted four-literal clause uses a nonzero relative truth pattern. A
specific weight-1 pattern has probability `3/32`, weight-2 has `2/32`, weight-3
has `1/32`, and `1111` has `4/32`. Thus every clause is satisfied, every literal
is true with probability `1/2`, every pair is jointly true with probability
`1/4`, and the two XOR parities are balanced. The latter matters: an earlier
3-CNF prototype accidentally made every clause an exact XOR equation, so
Gaussian elimination recovered the plant and that prototype was discarded.

## Why Track A is the honest claim

Section 3.4, Lemma 10 gives a parameterized reduction from Weighted Monotone
Circuit Satisfiability to IPDS-Extension. Lemmas 9, 7, and 3 carry the reduction
to ordinary/simple PDS, and Corollary 11 proves PDS W[P]-complete with respect to
solution size. Shipping uses `k=n=240`, so the parameter grows with the instance
rather than sitting in an easy fixed-`k` regime.

Worst-case W[P]-completeness does **not** establish hardness of this planted
distribution. The distributional evidence is the measured panel: frequency,
greedy, WalkSAT, signed pair-spectral recovery, signed third-moment tensor
recovery plus local repair, and watched-literal DPLL all failed on 8/8 shipping
seeds. DPLL used its full 50,000-node budget on every seed; on the baseline seed
that meant 12,907,046 literal inspections.

The paper is unusually explicit about what can be easy. Its introduction cites
linear-time algorithms at fixed treewidth. Section 4 gives safe preprocessing
rules and an exact implicit-hitting-set method, and Section 5 reports practical
power-grid instances of 2,000 and 10,024 vertices solved in roughly a second,
with much larger networks solved in minutes. Those facts are why this is not a
theorem-only claim: the generated dense 4-CNF circuit regime was attacked
directly, `k` grows, and no bounded-treewidth promise is made.

## Worked demo (`seed=3`)

This is the complete output of `render(make_instance(seed=3, **DIFFICULTY["demo"]))`:

```text
IMPLICATING POWER DOMINATING SET EXTENSION

There are 62 vertices, with integer IDs 0 through 61. Every vertex is
propagating. The only vertices that may be selected are IDs 0 through 11; every
other vertex is excluded from selection. Select exactly 6 distinct vertices.

Starting from the selected set, repeatedly apply these rules until no rule can
add a vertex:

1. Domination: every selected vertex and every endpoint joined to it by an
   undirected edge is observed.
2. Implication: if the source of a directed implication arc is observed, its
   target is observed.
3. Propagation: if an observed vertex has exactly one unobserved undirected
   neighbor, that neighbor is observed.

Your selected set is valid iff eventually every vertex is observed. Rule order
does not matter because rules only add observed vertices.

The graph is specified exactly by the following tables and formulas. A pair row
"i: a b -> q" creates implication arcs a->q and b->q. A clause row
"j: a b c d -> q" creates implication arcs from all four listed IDs to q. IDs in each
literal pair are distinct, pairs are disjoint, and clause rows never repeat a
pair. The pair order is only descriptive; the answer itself is a set.

Literal-pair checks:
  0: 2 0 -> 12
  1: 1 6 -> 13
  2: 10 11 -> 14
  3: 5 9 -> 15
  4: 3 8 -> 16
  5: 4 7 -> 17

Four-input clause checks:
  0: 6 9 11 4 -> 18
  1: 1 11 7 8 -> 19
  2: 6 7 10 2 -> 20
  3: 7 5 10 1 -> 21
  4: 10 3 5 4 -> 22
  5: 8 2 7 10 -> 23
  6: 11 4 9 3 -> 24
  7: 7 10 9 3 -> 25
  8: 6 4 5 0 -> 26
  9: 6 0 5 11 -> 27
  10: 4 5 2 3 -> 28
  11: 0 7 3 11 -> 29
  12: 11 6 4 0 -> 30
  13: 5 10 4 8 -> 31
  14: 9 8 0 4 -> 32
  15: 6 2 7 8 -> 33
  16: 8 2 5 7 -> 34
  17: 10 9 7 0 -> 35

For every check vertex q above, in table order (all pair checks, then all clause
checks), create one proxy p=36+its_zero_based_table_position, add implication
q->p, and add the undirected edge {p,60}. Also add the undirected edge {60,61}
and the implication arcs 61->v for every selectable vertex v. There are no other
edges or implication arcs.

Give your final answer inside <answer></answer> tags as exactly 6 comma-separated
base-10 vertex IDs in strictly increasing order. Repeats are forbidden. The IDs
must choose exactly one member of every displayed literal pair. Do not use
brackets.
Example of the required syntax (not necessarily a valid solution):
<answer>1, 2, 3, 4, 5, 10</answer>
Output nothing else inside the tags.
```

The constructed answer is `<answer>1, 2, 3, 4, 9, 11</answer>` and
`verify(inst, [1,2,3,4,9,11]) == (True, "ok")`. Flipping one pair gives
`[0,1,3,4,9,11]`, rejected with `clause-check 2 has no selected implication
source`. A person can solve this demo by hand: after taking one ID from each
pair there are only 64 assignments to check (18 happen to work).

## Difficulty presets

| Preset | Variables / answer atoms | Clauses | IPDS vertices | Status |
|---|---:|---:|---:|---|
| demo | 6 | 18 | 62 | hand example; harden.py skips it |
| easy | 240 | 2,424 | 5,810 | **ships; bare and hinted oracle pools held** |
| medium | 240 | 2,472 | 5,906 | fixed-answer denser fallback, not reached |
| hard | 240 | 2,520 | 6,002 | fixed-answer denser fallback, not reached |

Two earlier prototypes were rejected internally. At 3-CNF `n=160`, ratio 4.25,
DPLL solved 7/8 panel seeds and WalkSAT solved 1/8; worse, the planting law had
an exact XOR shortcut. The first 4-CNF rung at ratio 9.5 was then solved by the
third-moment tensor/repair attack on 1/8 seeds. Both are deliberately absent
from the shipping ladder.

## Gate results

| Gate | Result at shipping preset |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON round-trips |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic prose/fenced response round-trips 240 IDs; garbage returns `None` |
| G4 | 0 valid in 200,000 structure-aware guesses from `2^240` pair choices |
| G5 | shipping density sample 0/200,000; DPLL 50,000 nodes, 12,907,046 literal inspections, 1.68 s; demo exact count 18/64 |
| G6 | all six attacks 0/8; DPLL 400,000 nodes, WalkSAT 48,386,176 operations, pair-spectral 36,864,000, tensor/repair 925,218,193 |
| G7 | doubled instance: 480 variables, 11,618 vertices; planted witness verifies |
| G8 | 80/80 vertex/row/within-row/order invariance and 80/80 carried witnesses; 20/20 unrelated keys distinct |
| G9 | 1,148 answer characters, 240 atoms, 287 estimated tokens; 240 post-insight Boolean/output operations |

The G4/G5 value is an observed density under the declared prior—uniformly choose
one member of every literal pair—not an exact solution count and not a proof of
average-case hardness. With zero hits, the simple rule-of-three 95% upper bound
is `1.5e-5`; the stronger hardness evidence is the attack cost, not cardinality.

## Oracle loop

| Arm/preset | Model | Seed | Solved? | Exact grading result |
|---|---|---:|---|---|
| bare/easy | Anthropic Claude Sonnet 5 | 926468780 | no | empty length-limited response after 32k completion tokens |
| bare/easy | Google Gemini 3.1 Pro Preview | 1060985735 | no | clause-check 4 unhit |
| bare/easy | xAI Grok 4.6 | 168064319 | no | clause-check 10 unhit |

The Google and xAI replies parsed and failed exact verification. Anthropic
returned no content with `finish_reason=length`; the official harness explicitly
counts that as an unsolved attempt, not an API error. `harden.py` returned
`hardened` at the first non-demo rung with zero escalations.

## G9 arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0 / 3 | shipping evidence |
| structural hint | 0 / 3 | `hardened`; G9(b) passes |
| placebo hint | 0 / 3 | diagnostic control |

Hinted minus placebo is `0.0`. The explicit reduction-recognition hint bought
no measured success in this small sample; recognition alone did not make a
240-variable SAT witness executable in context. The answer is 1,148 characters,
240 atoms, and about 287 tokens on the measured gate seed (290 tokens worst over
200 shipping seeds). The intended post-recognition route is bounded at 240
Boolean/output operations, below the 300-operation cap.

## Use

```python
import importlib.util

path = "results/2306.09870/gen_2306_09870.py"
spec = importlib.util.spec_from_file_location("pdsgen", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

inst = mod.make_instance(seed=17, **mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY])
print(mod.render(inst))
answer = mod.parse_answer("<answer>...</answer>")
print(mod.verify(inst, answer))
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2306.09870 20
```

The module is standard-library-only. It does not import `gvlib` because the
native certificate and verifier use only finite graph sets and integer IDs.

## Caveats

- Corollary 11 is worst-case parameterized hardness; it does not prove this
  random planted distribution hard. The attack and oracle panels are finite
  empirical evidence only.
- I did not run a production CDCL solver, the authors' Gurobi-backed implicit
  hitting-set implementation, an SDP relaxation, or belief propagation. I did
  run one signed third-moment tensor-power attack with local repair, but that is
  not exhaustive of higher-order recovery methods.
- The quiet plant cancels first- and second-order signatures and parity exactly
  in the sampling law, but third moments contain signal. The tensor/repair probe
  found that signal insufficient at shipping parameters; a stronger method may
  not.
- `canonical_key` uses eight rounds of typed incidence refinement. General CNF
  isomorphism is not canonicalized exactly; rare non-isomorphic collisions are
  possible. The tested vertex, row, within-row, edge-order, and clause
  relabelings are invariant and 20 unrelated samples were distinct.
- Fixed-treewidth graphs and small `k` are easy regimes. This generator promises
  neither: `k=240`, and it does not certify treewidth.
- A solver can always verify a guessed witness cheaply. The reported 0/200,000
  guess rate says only that uniform one-per-pair guessing failed; it says nothing
  about a prior informed by untested higher-order structure.
- One bare and one hinted oracle call returned empty length-limited responses;
  the placebo Anthropic call emitted only an unterminated partial answer before
  its length limit. Those rows are official harness failures but weaker evidence
  than the six parsed candidates rejected by exact verification.
