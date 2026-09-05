# Rooted twin blocks for nested-dissection reduction

**Status:** the module passes every local gate, including the G9(c) size/effort caps, but is **not shippable**. A refreshed bare run solved `easy`, `medium`, `hard`, and the first generated escalation on every call; at `n=3600` it solved 2/3 calls, which still defeats that level. OpenRouter then exhausted its total quota at `n=5400`, before `harden.py` could record a verdict. The structural-hint and placebo runs also remain unscored. API errors are preserved as errors, never counted as model failures.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: three left-vertex labels |
| Intended intuition | constraint propagation along a local codegree-2 chain |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust boundary

The source is Ost, Schulz, and Strash, [*Engineering Data Reduction for Nested Dissection*](https://arxiv.org/abs/2004.11315). Section 2 defines open neighborhoods and elimination fill. The Twin Reduction subsection of Section 4 defines twins by equal open neighborhoods; Theorem 4 shows that a twin pair can be consecutive in a minimum-fill ordering, and the following exact rule contracts and later expands a twin.

An instance is the paper's native undirected graph object, presented as both sides of a labelled 4-regular bipartite incidence list. A marked left vertex supplies a benchmark-specific root. The solver returns three left vertices with one common open neighborhood. `verify` checks shape, range, distinctness, ordering, and exact equality of four-element neighbor sets; it never reads `inst["answer"]`.

Generation is inverse. The chain and terminal twin triple are chosen first; two right vertices encode every chain link, and the terminal gadget gives the three twins the same four neighbors. Random decoy incidences complete all degrees to four. Independent left/right permutations and row shuffles carry the known witness. No twin detector produces the stored answer.

## Why Track B

Track A would be false. Section 4 explicitly describes twin detection by hashing, sorting, and comparing neighborhoods, with worst-case cost `O(mn + n log n)`. The fixed-degree reference implementation here is `O(nd log d + n log n)`, solves 8/8 shipping instances, and measured 250,141 counted operations total, at most 31,979 on one instance, in 0.028647 seconds on the latest (contended) run. This efficient algorithm is deliberately reported as `reference_algorithm`, not as a failed attack.

The compact route is genuinely shorter than a global scan. Starting at the marked left vertex, inspect only the four incident right rows and count the other left labels: exactly one unvisited label occurs twice at each chain step. At the endpoint, three labels occur twice and their complete rows agree. The measured maximum is 236 exact incidence/count comparisons. Section 3's linear-time perfect-elimination algorithm for chordal graphs and Section 4's direct twin detector are the easy regimes this Track-B claim acknowledges.

## Worked demo

This is the complete rendered `demo` instance for seed 0. A person can solve it on paper by following the two-link chain from `S=L12`.

```text
Find a three-vertex twin block in this rooted undirected bipartite graph.

Definitions and conventions:
The left vertices are L0,...,L15; the right vertices are R0,...,R15.
Left and right labels are separate even when their integers are equal.
Every edge has one left and one right endpoint, and no other edges exist.
Every left vertex and every right vertex has degree exactly 4.
The open neighborhood N(v) is the set of vertices joined to v; v itself is excluded.
Distinct vertices are twins when their open neighborhoods are exactly equal as sets.
Find exactly three distinct LEFT vertices that are pairwise twins.
Output zero-based integer labels in strictly increasing order; repeats are forbidden.
Row order and the order of labels within any row carry no meaning.
One distinguished left vertex is S = L12.

Left adjacency rows (`Li: ...` lists the four right neighbors of Li):
L12: 6 0 12 10
L10: 1 4 3 10
L2: 7 12 0 3
L7: 4 2 0 15
L3: 14 5 11 15
L14: 2 9 0 8
L5: 3 7 14 11
L6: 6 3 4 1
L9: 5 14 15 11
L4: 12 9 2 8
L1: 4 12 1 13
L0: 6 9 13 7
L13: 2 8 10 7
L15: 13 5 9 6
L11: 13 8 1 10
L8: 5 11 14 15

Right incidence index, in increasing right-label order (`Ri: ...` lists its four left neighbors):
R0: 2 12 7 14
R1: 1 6 10 11
R2: 13 4 7 14
R3: 5 6 2 10
R4: 6 10 7 1
R5: 8 15 3 9
R6: 0 15 6 12
R7: 13 5 0 2
R8: 11 4 14 13
R9: 0 4 14 15
R10: 13 11 12 10
R11: 8 5 9 3
R12: 1 12 4 2
R13: 15 0 11 1
R14: 5 8 9 3
R15: 8 3 9 7

Give your final answer inside <answer></answer> tags, as exactly three comma-separated left-vertex integer labels.
Example of the required syntax: <answer>1, 5, 9</answer>
Output nothing else inside the tags.
```

The answer is `[3, 8, 9]`, whose rows all equal `{5,11,14,15}`. `verify(inst, [3,8,9])` returns `(True, "ok")`; `verify(inst, [3,8,10])` returns `(False, "the three open neighborhoods are not equal")`.

## Presets and gates

| Preset | Left + right vertices | Chain links | Legal triples | Ships? |
|---|---:|---:|---:|---|
| demo | 16 + 16 | 2 | 560 | no; hand example |
| easy | 240 + 240 | 8 | 2,275,280 | no |
| medium | 700 + 700 | 8 | 56,921,900 | no |
| hard | 1,600 + 1,600 | 8 | 681,387,200 | no; solved 3/3 by the oracle pool |

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses and compact routes verify; answers are JSON-native |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged answer round-trips through prose/fences; garbage returns `None` |
| G4 | pass | 0/200,000 hits; exact density `1/681,387,200` |
| G5 | pass | exactly one shipping answer; 16,424 attack candidates in 2.095488 s on a contended host |
| G6 | pass | six attacks at 0/8; reference sorter and compact route each solve 8/8 |
| G7 | pass | `n=3200` builds and verifies; the answer remains three atoms |
| G8 | pass | 40/40 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 16 characters, 4 estimated tokens, 3 atoms, 236 intended operations |
| G9(a,b) | diagnostic incomplete | bare `hard` solved 3/3; hinted/placebo have no scored calls |

## Oracle loop and G9 arms

The refreshed bare loop evaluated five complete levels. A level is defeated if any oracle solves it, so the single failure at `n=3600` did not hold the level. Four redraws at `n=5400` then received HTTP 403 quota errors, and `harden.py` correctly stopped without writing `harden_verdict`. The isolated structural and placebo copies still contain four API-error records each and no scored calls.

| Arm/preset | Seeds | Scored solved/attempts | Outcome |
|---|---|---:|---|
| bare / easy (`n=240`) | 585975213, 1167855356, 1941907176 | 3/3 | defeated |
| bare / medium (`n=700`) | 1998490565, 1446418317, 47795606 | 3/3 | defeated |
| bare / hard (`n=1600`) | 1729849590, 1744737257, 383002517 | 3/3 | defeated |
| bare / escalated (`n=2400`) | 1869593379, 948243505, 1052096488 | 3/3 | defeated |
| bare / escalated (`n=3600`) | 1638285312, 623569129, 1388868799 | 2/3 | defeated |
| bare / escalated (`n=5400`) | 1476827086, 544843653, 1189562577, 1844963608 | 0/0 | four HTTP 403 quota errors |
| hinted / hard | 361096914, 1877115572, 1761900199, 278656356 | 0/0 | four earlier HTTP 403 quota errors |
| placebo / hard | 1681179071, 740274434, 631949931, 2106745858 | 0/0 | four earlier HTTP 403 quota errors |

Hinted-minus-placebo is undefined until scored calls exist, so the JSON records `null` alongside `hinted_verdict="not_run"`. These arms are diagnostic under the current specification; G9 passes because its only remaining gate, G9(c), is within caps. STEP 4 remains incomplete independently.

## Use

```python
import gen_2004_11315 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
statement = g.render(inst)
candidate = g.parse_answer("<answer>1, 5, 9</answer>")
ok, reason = g.verify(inst, candidate)
```

After valid oracle evidence exists, run from the repository root:

```bash
python3 results/2004.11315/gen_2004_11315.py
scripts/emit.sh 2004.11315
```

The module needs only the Python standard library; `gvlib` is unnecessary because the certificate uses finite set equality rather than rational algebra.

## Caveats

The paper does not study this planted rooted distribution; the root and codegree chain are benchmark scaffolding around its native twin object. Any sandboxed solver, database index, or row sorter solves the task in milliseconds, which is why this is Track B only. The exact density concerns the declared uniform prior over legal increasing triples; it says nothing about a solver using the root or duplicate-row statistics. The attack panel does not include production graph-isomorphism software or all possible local motif heuristics. The canonical key is a strong rooted Weisfeiler-Lehman invariant, not a complete graph-isomorphism canonical form. Most importantly, the live learned-model attack solved every completed level often enough to force escalation. The quota interruption means the run is incomplete, not that the family is hard; no hardness conclusion should be drawn and the current named `hard` preset must not ship.
