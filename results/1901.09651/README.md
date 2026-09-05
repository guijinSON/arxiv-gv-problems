# Complementary directed tours from arXiv:1901.09651

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation |
| Certificate | integer tuple of switch-component indices |
| Intended intuition | decomposition into repeated relative-permutation tiles |
| Domain essentiality | native; no reduction |

## Problem and trust model

The solver receives two explicit directed Hamiltonian tours and the nontrivial
cycles of their relative successor permutation. Selecting a listed component
swaps which input supplies the outgoing arc at all three of its tail vertices.
The requested witness is a fixed-size set of components for which the selected
arcs and their complement are both single Hamiltonian tours, different from the
inputs. `verify` reconstructs the two successor permutations and traverses their
cycles exactly; it never reads the planted answer.

This is the native sufficient certificate in Lemma 1 of Kozlova and Nikolaev,
[*Simulated annealing approach to verify vertex adjacencies in the traveling
salesperson polytope*](https://arxiv.org/abs/1901.09651). The generator starts
from an explicit 12-vertex four-tour identity. It composes copies by a cyclic
splice, subdivides vertices, conjugates labels, swaps the inputs, and carries the
known switch through every transformation. It does not search an emitted
instance for its answer.

## Why Track B

This is not a Track A distributional-hardness claim. The theorem quoted in
Section 1 concerns worst-case NP-completeness of polytope nonadjacency, whereas
the complementary-tour condition is only sufficient. Section 6 also identifies
regimes that are easy in practice or in theory: pyramidal pairs have a linear-time
test, and the paper's random undirected pairs were solved in essentially every
experiment. Neither observation supports Track A for a planted distribution.

The successful reference method here is an exact singleton relative-cycle scan:
test every listed component by traversing both complete successor permutations.
It costs `O(cV)` and, for shipping seed 20260905, used 24,128 pointer visits and
0.0016 seconds in the final audit (0.001–0.004 seconds across repeated runs). Across
the eight audit seeds it succeeds 8/8, as a
Track B reference algorithm should. This complements the paper's mechanical
annealing moves, whose directed cycle covers use Hopcroft–Karp matching in
`O(sqrt(V) E)` per move (Sections 3–4).

The compression is to recognize that the relative 3-cycles recur as independent
12-vertex identities joined only by a cyclic splice. Local masks of weights
0, 1, 3, and 4 preserve both tours; the planted route takes the certified
weight-one mask in each tile. At the shipping preset this needs at most 116
local exact checks, versus tens of thousands of full-tour pointer visits.

## Worked demo

This is `make_instance(n=1, padding=1, seed=11)` in full:

```text
Complementary directed Hamiltonian tours

A directed Hamiltonian tour is a cyclic ordering of every vertex exactly once;
the last listed vertex has an arc back to the first. Two input tours x and y
on vertices 0 through 11 are given below.

A switch component is a listed triple of tail vertices. Choose exactly 1
distinct component indices. For every tail in a chosen component, put y's
outgoing arc in z and x's outgoing arc in w. At every other tail, put x's
outgoing arc in z and y's outgoing arc in w. The listed components are
pairwise disjoint. This rule uses every occurrence of every input arc exactly
once, including parallel occurrences.

Find indices for which z and w are each a single directed Hamiltonian tour
and the unordered pair {z,w} is different from {x,y}.

All indexing is 0-based. Order does not matter mathematically, but output the
indices in strictly increasing order; repeats are forbidden.

x: 0 11 5 2 1 10 4 7 6 3 8 9
y: 10 7 11 0 8 4 9 1 2 5 3 6

Switch components (index: tail vertices):
0: 1 5 6
1: 2 9 11
2: 0 3 7
3: 4 8 10

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly 1 distinct increasing component indices.
Format example only: <answer>[0]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[3]</answer>`. `verify(inst, [3])` returns
`(True, "ok")`; `verify(inst, [])` returns `(False, "answer must not be empty")`.
A person can solve this smallest case on paper by trying its four switches.

## Difficulty presets

| Preset | Tiles | Subdivision cap | Vertex range | Candidate space | Status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 1 | 12 | 4 | hand-solvable illustration |
| easy | 13 | 2 | 156–312 | `C(52,13)` | **ships; hardened 0/3** |
| medium | 16 | 3 | 192–576 | `C(64,16)` | escalation rung |
| hard | 20 | 4 | 240–960 | `C(80,20)` | escalation rung |

The easy rung held immediately, so the harness did not escalate to medium or
hard.

## Gate results

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verified across all presets |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | fenced model-style answer round-tripped; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses valid |
| G5 | exact shipping density `351352 / 635013559600 = 5.5329842e-7`; baseline 24,128 visits / 0.0016 s |
| G6 | five attacks × 8 seeds, 0 successes; reference scan 8/8 |
| G7 | doubled 26-tile instance built and verified; candidate space increased |
| G8 | 60 relabelling/swap/reversal/composition checks and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 51 characters, 13 atoms, about 13 tokens, 116 intended-route operations |

The exact solution count is the coefficient of `x^13` in
`(1 + x + x^3 + x^4)^13`; this is independently sampled in G4.

## Oracle loop

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 58,282,299 | Gemini 3.8 Flash | no | response hit its length limit without an answer |
| easy | 408,466,000 | GPT-5.6 Terra | no | parsed 13 indices; selected tour had 17 cycles |
| easy | 2,023,813,507 | Gemini 3.8 Flash | no | response hit its length limit without an answer |

The harness verdict is `hardened` at easy with zero escalations. The two
length-limited calls count as unsolved under the harness contract, but they are
weaker evidence than completed wrong answers; the caveat is retained below.

## G9 arms

| Arm | Solved / scored attempts | Service errors | Result |
|---|---:|---:|---|
| bare | 0 / 3 | 0 | hardened |
| structural hint | 0 / 3 | 0 | hardened diagnostic |
| placebo hint | 0 / 3 | 0 | hardened diagnostic |

Hinted-minus-placebo is `0.0`: naming the repeated-tile invariant bought no
measured success in this six-call comparison. This does not show that
decomposition is irrelevant—all three hinted replies attempted tile groupings—but
it does show that the one-sentence hint was insufficient to make the exact local
choices reliable. The shipping answer is 51 characters / 13 atoms (about 13
tokens), and the intended post-insight route is bounded at 116 exact checks.

## Use

```python
from gen_1901_09651 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=11, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer("My result is <answer>[3]</answer>.")
assert verify(inst, answer) == (True, "ok")
```

After a successful hardening run, emit records from the repository root with:

```bash
bash scripts/emit.sh 1901.09651
```

## Caveats

This family is deliberately easy for software: the successful reference scan
takes milliseconds. Its Track B claim is only that 24,128 exact pointer steps
do not fit a no-tool response, while the repeated-tile observation compresses
them. A solver that recognizes or reconstructs the tiles immediately makes the
family easy.

The random-guess probability is for a uniform `n`-subset of the `4n` listed
components, exactly the declared output language. It is not a probability under
a human or model prior, and the family has many valid certificates (351,352 at
shipping). I tested cyclic-span and successor-distance outliers, input-order and
orientation ansätze, 256 random restarts, and the exact singleton scan. I did not
implement the paper's full simulated-annealing temperature schedule or an external
SAT/SMT solver. The canonical key is exact up to relabelling, tour rotation, input
swap, and global arc reversal before a SHA-256 digest; only the negligible digest
collision caveat remains. Two of the three bare oracle failures exhausted the
response budget without a final answer, so the bare 0/3 result is not three
independent completed wrong certificates. The successful software reference scan
also takes only milliseconds: this is strictly a Track B no-tool benchmark, not a
claim that the generated instances are computationally hard.
