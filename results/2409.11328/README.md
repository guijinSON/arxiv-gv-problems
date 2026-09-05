# Burning game — verified generator for arXiv:2409.11328

> Status: **parked at `cap_bound`**. Every local gate passes, but the bare oracle
> loop solved easy 3/3, medium 2/3, and hard 2/3. The next ambient-size step would
> exceed the 300-operation no-tool cap, so the harness correctly refused both a
> shipping claim and a rejection of the paper.

## Profile

| field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple, compactly encoded as a fixed-width word |
| Intended intuition | symmetry: one hidden relabelling is shared across many games |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The source is Chiarelli, Iršič, Jakovac, Kinnersley, and Mikalački,
[*Burning game*](https://arxiv.org/abs/2409.11328). Section 1 defines the game on a
finite simple graph: fire spreads at the start of a round, then Burner and Staller
alternately ignite one unburned vertex. For every target graph, the solver must give
a Burner first move that guarantees completion by round 3 against every Staller
reply.

The generator uses inverse construction plus a certificate-preserving
transformation. In each reference graph it constructs a unique Proposition 10
winner from named vertex roles; it never searches the finished graph for that
winner. One common random vertex permutation is then applied to every target graph,
and the known moves are carried through it. `verify` never reads `inst["answer"]`:
it evaluates Proposition 10's exact maximum-degree and neighborhood condition for
every submitted move. The self-test also compares that condition with the literal
three-round game tree on all demo candidates.

## Why Track B

This paper proves no distributional hardness result for computing the new game
burning number, so Track A would be unsupported. Proposition 10 instead gives the
honest standard algorithm: scan all vertices and test its first- and
second-neighborhood condition. At the shipping preset (`g=48`, `n=31`), the scan is
`O(g n^3)` in the adjacency representation and averaged **74,524 exact adjacency
operations and about 0.006 seconds** over eight seeds. It solved 8/8, as expected.

The compact route reads each vertex's displayed degree in the first four reference
and target graphs. Those cross-layer profiles are unique and preserved by the one
shared relabelling. Matching them transports all 48 audited reference moves in at
most `2*4*31 + 48 = 296` degree reads/lookups. Without recognizing the shared
symmetry, the solver must repeat the Proposition 10 scan for every target.

A construction-aware graph attack also succeeds, as Track B requires us to admit:
one-dimensional Weisfeiler–Leman color refinement uniquely aligns every individual
reference/target pair. On the same eight shipping seeds, the simple exact
implementation solved 8/8 with a mean of **86,645 reads/updates and about 0.006 seconds**.
That is still a mechanical route far beyond unaided execution, and it is reported
beside—not hidden inside—the failing attack panel.

The easy regimes identified by the paper were avoided: Proposition 9 characterizes
game burning numbers 1 and 2 by degrees; Proposition 11 collapses diameter-at-most-2
graphs to ordinary burning; Theorems 23 and 24 give direct path/cycle strategies;
and Theorem 29 writes down the hypercube sources. The present gadget instead has
exactly one three-round winning first move. Its winner is degree-tied with at least
two decoys, while the maximum-degree and largest-two-neighborhood vertices are
losing.

## Worked demo

This is `render(make_instance(seed=3, **DIFFICULTY["demo"]))` in full. A person can
solve it on paper: form the four-degree profile of each reference label and match it
to the corresponding target profile, then transport the four audited moves.

```text
BURNING GAME: THREE-ROUND FIRST-MOVE CERTIFICATES

A finite simple undirected graph has vertices 0 through n-1. Initially all
vertices are unburned. In round 1 the first player, Burner, selects one
unburned vertex, which burns immediately. At the start of every later round,
every unburned neighbor of any burned vertex burns; afterward the player
whose turn it is selects one still-unburned vertex, if one exists. Burner
moves in odd rounds and Staller in even rounds. Burned vertices stay burned.
The game ends as soon as all vertices are burned, including immediately after
a spreading phase. Burner wants this to happen quickly; Staller delays it.

For each numbered pair below, the reference graph comes with an audited
Burner first move that guarantees the reference game ends by the end of round
3 against every legal Staller move. Find one such first move for every target
graph. Each graph row has the form v(degree):comma-separated-neighbors; '-'
means no neighbors. Rows are separated by semicolons. The neighbor lists are
symmetric and contain neither loops nor repeated neighbors.

There are 4 pairs and n=14. Vertex labels are zero-based.
A move must be one vertex of its corresponding target graph. Different games
are independent, order follows the pair numbers, and repeated labels across
different games are allowed.

Pair 0: audited reference move=10
  R 0(4):1,3,4,13 ; 1(6):0,4,7,9,11,12 ; 2(4):4,5,7,12 ; 3(4):0,4,12,13 ; 4(6):0,1,2,3,11,12 ; 5(3):2,7,10 ; 6(1):10 ; 7(4):1,2,5,12 ; 8(3):9,10,11 ; 9(4):1,8,11,12 ; 10(4):5,6,8,13 ; 11(4):1,4,8,9 ; 12(6):1,2,3,4,7,9 ; 13(3):0,3,10
  T 0(3):3,5,9 ; 1(4):4,6,8,10 ; 2(1):5 ; 3(4):0,6,9,13 ; 4(3):1,5,8 ; 5(4):0,2,4,11 ; 6(6):1,3,9,10,12,13 ; 7(4):10,11,12,13 ; 8(4):1,4,10,13 ; 9(4):0,3,6,10 ; 10(6):1,6,7,8,9,13 ; 11(3):5,7,12 ; 12(4):6,7,11,13 ; 13(6):3,6,7,8,10,12
Pair 1: audited reference move=13
  R 0(4):2,4,6,11 ; 1(4):6,8,9,12 ; 2(3):0,4,13 ; 3(3):5,7,13 ; 4(4):0,2,9,11 ; 5(4):3,6,7,9 ; 6(6):0,1,5,7,9,11 ; 7(4):3,5,6,11 ; 8(4):1,9,11,12 ; 9(6):1,4,5,6,8,11 ; 10(1):13 ; 11(6):0,4,6,7,8,9 ; 12(3):1,8,13 ; 13(4):2,3,10,12
  T 0(4):1,5,9,10 ; 1(3):0,3,6 ; 2(6):3,4,7,8,12,13 ; 3(4):1,2,6,12 ; 4(4):2,7,8,9 ; 5(1):0 ; 6(4):1,3,7,12 ; 7(6):2,4,6,11,12,13 ; 8(4):2,4,9,12 ; 9(3):0,4,8 ; 10(3):0,11,13 ; 11(4):7,10,12,13 ; 12(6):2,3,6,7,8,11 ; 13(4):2,7,10,11
Pair 2: audited reference move=9
  R 0(4):3,4,10,12 ; 1(4):2,4,7,13 ; 2(4):1,4,7,10 ; 3(3):0,9,12 ; 4(6):0,1,2,6,10,13 ; 5(4):6,10,11,13 ; 6(4):4,5,11,13 ; 7(3):1,2,9 ; 8(1):9 ; 9(4):3,7,8,11 ; 10(6):0,2,4,5,12,13 ; 11(3):5,6,9 ; 12(4):0,3,10,13 ; 13(6):1,4,5,6,10,12
  T 0(6):2,4,5,6,10,13 ; 1(4):5,6,8,13 ; 2(4):0,4,6,12 ; 3(4):5,6,9,10 ; 4(4):0,2,5,12 ; 5(6):0,1,3,4,6,10 ; 6(6):0,1,2,3,5,13 ; 7(4):8,9,11,12 ; 8(3):1,7,13 ; 9(3):3,7,10 ; 10(4):0,3,5,9 ; 11(1):7 ; 12(3):2,4,7 ; 13(4):0,1,6,8
Pair 3: audited reference move=4
  R 0(3):4,8,10 ; 1(3):4,5,9 ; 2(4):3,6,11,13 ; 3(6):2,7,8,9,10,11 ; 4(4):0,1,6,12 ; 5(4):1,7,9,11 ; 6(3):2,4,13 ; 7(6):3,5,9,10,11,13 ; 8(4):0,3,10,11 ; 9(4):1,3,5,7 ; 10(4):0,3,7,8 ; 11(6):2,3,5,7,8,13 ; 12(1):4 ; 13(4):2,6,7,11
  T 0(4):1,2,8,12 ; 1(4):0,2,9,12 ; 2(3):0,1,6 ; 3(3):5,6,11 ; 4(4):7,8,12,13 ; 5(4):3,8,9,11 ; 6(4):2,3,10,13 ; 7(4):4,8,9,13 ; 8(6):0,4,5,7,9,12 ; 9(6):1,5,7,8,11,12 ; 10(1):6 ; 11(4):3,5,9,12 ; 12(6):0,1,4,8,9,11 ; 13(3):4,6,7

OUTPUT ENCODING
Use the alphabet '0123456789abcd': its character at position v denotes vertex v.
Output exactly one 4-character word. Character i is the move for target
game i; there are no separators or spaces inside the word.
Give your final answer inside <answer></answer> tags, as that exact word.
Example shape for 4 entries: <answer>0123</answer>
The example illustrates encoding only and is not an answer to this instance.
Output nothing else inside the tags.
```

The answer is `5076`. `verify(inst, "5076")` returns `(True, "ok")`.
Changing the first symbol gives `verify(inst, "0076") ==
(False, "entry 0 is not a three-round winning first move")`.

## Difficulty presets

| preset | vertices/game | games | profile layers | compact operations | status |
|---|---:|---:|---:|---:|---|
| demo | 14 | 4 | 4 | 116 | hand-solvable example |
| easy | 18 | 48 | 4 | 192 | solved by oracle pool 3/3 |
| medium | 24 | 48 | 4 | 240 | solved by oracle pool 2/3 |
| **hard** | **31** | **48** | **4** | **296** | solved by oracle pool 2/3; last in-cap candidate |

The module retains `SHIPPING_DIFFICULTY="hard"` as the last tested candidate, but
it is not approved for emission. `escalate()` returns `"cap_bound"` beyond hard
because one more vertex would push the measured compact route past 300 operations.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12 preset/seed instances; 444 unique-winner audits; 168 literal game-tree cross-checks |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | 48-symbol fenced/prose response round-tripped |
| G4 | pass | 0/200,000 structure-aware guesses; exact probability `31^-48 = 2.598e-72` |
| G5 | pass | exactly 1 valid shipping word; strongest failed attack used 2,048 restarts total |
| G6 | pass | nine attacks, each 0/8; Proposition 10, pairwise 1-WL, and compact transport each 8/8 |
| G7 | pass | doubled `n=62` instance built and verified |
| G8 | pass | 80 invariance checks, 80 carried witnesses, 20/20 distinct unrelated keys |
| G9(c) | pass | 50 serialized characters/tokens (conservative one-character-per-token bound), 48 atoms, 296 operations |

## Oracle loop and G9 diagnostics

The bare harness completed nine scored calls and returned `cap_bound`.

| bare preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 718440280 | openai/gpt-5.6-terra | yes | verified answer |
| easy | 236681933 | google/gemini-3.8-flash | yes | verified answer |
| easy | 1837855291 | openai/gpt-5.6-terra | yes | verified answer |
| medium | 1993814552 | openai/gpt-5.6-terra | yes | verified answer |
| medium | 848511904 | google/gemini-3.8-flash | yes | verified answer |
| medium | 1607784165 | google/gemini-3.8-flash | no | entry 36 failed verification |
| hard | 1694840190 | openai/gpt-5.6-terra | yes | verified answer |
| hard | 449161329 | google/gemini-3.8-flash | yes | verified answer |
| hard | 1700128929 | google/gemini-3.8-flash | no | answer had too few symbols |

| arm | preset | solved/attempts | raw calls | conclusion |
|---|---|---:|---:|---|
| bare | hard | 2/3 | 3 scored | hard did not hold |
| structural hint | hard | 0/0 | 4 errors | diagnostic blocked |
| placebo hint | hard | 0/0 | 4 errors | diagnostic blocked |

`hinted - placebo` is undefined evidentially; the report stores `0.0` only because
both scored denominators are zero. Those two earlier script-owned attempts hit a key
limit; they were not rerun after the bare `cap_bound` terminal verdict, as the task
contract says to park at that point.

## Use

```python
from gen_2409_11328 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
question = render(inst)
answer = parse_answer(f"Result: <answer>{inst['answer']}</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a future redesign obtains a valid bare hardening
verdict (do not emit this parked version):

```bash
bash scripts/emit.sh 2409.11328 20 hard
```

The module is deterministic, standard-library-only, performs no file or network IO,
and prints only when executed as a script.

## Caveats

- The completed bare oracle loop is negative evidence: all three presets were
  solved, and the harness returned `cap_bound`. This version must not be emitted or
  described as hardened. Per the contract it is parked, not rejected.
- The exact `P(guess)` uses a uniform prior over correctly sized words—one in-range
  vertex per game. It does not model a solver that recognizes the reference/target
  correlation; that informed route is measured separately at 296 operations.
- The shared relabelling is benchmark scaffolding, not a theorem in the paper. The
  objects and verifier remain native burning-game graphs, but the intended symmetry
  is supplied by the generator.
- The failing panel includes degree extremes, largest two-neighborhood, single-pair
  degree matching, a one-layer shared-map guess, unchanged-label and cyclic-shift
  ansatzes, and random restart. Pairwise 1-WL was tried and succeeds 8/8, so Track B
  records it as a reference algorithm. A full individualization/refinement graph-
  isomorphism package was not run because the cheaper 1-WL attack already solves.
- `canonical_key` uses a multiset of rooted-reference/unrooted-target
  Weisfeiler–Leman fingerprints and deliberately forgets the hidden cross-layer
  alignment. It passed common and independent graph relabellings plus pair reorderings,
  but it is not a complete canonical form for graph isomorphism.
- Forty-eight output symbols are within the cap but still require careful
  transcription. The fixed-width encoding keeps the serialized answer to 50
  characters.
