# Verified generator for arXiv:0909.2769

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Solver domain | algebra |
| Object regime | finite field |
| Computational core | graph (a translation perfect matching, encoded algebraically) |
| Certificate | exact symbolic translation vector |
| Intended intuition | decomposition: recognize a normalized rank-one update |
| Domain essentiality | licensed reduction |
| Reduction | Section 8, Theorem 12 |
| Shipping preset | **medium** (`n=42`, `p=2147483647`) |

This is a paper-licensed representational reduction, not native graph-domain
coverage. The paper's graph object remains explicit in the statement, and
Theorem 12 licenses the perfect-matching witness, but the finite-field encoding
that makes the matching succinct is this benchmark's construction rather than
an object studied in the paper.

## Problem and trust model

Saeed Shaebani's [*On Fall Colorings of Graphs*](https://arxiv.org/abs/0909.2769)
defines a fall coloring as a proper coloring in which every closed neighborhood
sees every color. Section 8, Theorem 12 proves that a fall coloring of the
complement of a bipartite graph is exactly a perfect matching on its
positive-degree vertices, together with singleton colors for isolated vertices.

An instance defines a bipartite graph on two copies of `F_p^n` by a finite-field
edge predicate. The solver returns a vector `d`; it denotes the matching
`L_x -- R_(x+d)` and hence the color classes `{L_x,R_(x+d)}`. Verification uses
only exact modular arithmetic: it checks the shape/range of `d` and every row of
`A*d=b`. Translation is bijective, each claimed pair is an edge, and the two
same-side cliques in the complement make every closed neighborhood see all
`p^n` colors.

Generation is inverse. It samples `d` first, samples normalized `u,v`, forms the
invertible matrix `A=I+u*v^T`, and sets `b=A*d`. It never solves the generated
system. A star-shaped extra edge fiber changes the graph's isomorphism type
across seeds without changing or statistically marking `d`.

## Why Track B

Track A would be false. Theorem 12 itself says the relevant explicit-graph
decision problem is polynomial-time via perfect matching. For the succinct
system printed here, dense Gaussian elimination is an exact `O(n^3)` reference
algorithm and solved 8/8 shipping instances. At `medium` it used 78,477 field
operations, at most 0.009906 seconds in the final selftest on this host.

The compact route is to notice that `A-I` has rank one and is normalized by its
first row and column. Extracting `u,v` gives
`d = b - u*(v·b)/(1+v·u)` in `F_p`. That route costs 254 counted exact
operations, within the 300-operation no-tool cap, but still requires 42-coordinate
31-bit modular arithmetic. Section 7, Theorem 11 is an unusable easy regime
(Mycielskians have no fall coloring), while Sections 2--4 provide direct product
constructions; this family deliberately uses the Section 8 characterization and
does not claim hardness for those regimes.

## Worked demo

The demo is hand-scale: solve three linear congruences modulo 7. Seed 0 renders:

```text
SUCCINCT FALL COLORING OF A BIPARTITE COMPLEMENT

Work over the prime field F_7; all arithmetic is modulo 7, and
residues are written as integers 0,...,6.
A vector has exactly 3 coordinates, indexed 0,...,2.

Define a bipartite graph G. Its left vertices L_x and right vertices
R_y are indexed by all vectors x,y in F_7^3. There are no edges
within either side. A cross-pair {L_x,R_y} is an edge when at least
one of these exact conditions holds:
  (1) A*(y-x) = b coordinatewise modulo p; or
  (2) x=c and dot(w,y-c), represented in 0,...,p-1, is less than s.

Let H be the simple complement of G: distinct vertices are adjacent in
H exactly when they are not adjacent in G. A proper k-coloring assigns
k colors with different colors on adjacent vertices. It is a fall
k-coloring when every closed neighborhood (the vertex itself and all
its H-neighbors) contains all k colors.

Find d in F_7^3 satisfying A*d=b. It compactly witnesses the fall
p^n-coloring whose color indexed by x is {L_x,R_(x+d)}.

A =
  2 1 3
  4 5 5
  4 4 6
b = 6 4 4
c = 1 4 1
w = 3 2 4
s = 1

Output d as a JSON list of exactly 3 integers in coordinate order.
Give your final answer inside <answer></answer> tags.
```

The answer is `<answer>[4,3,3]</answer>`.
`verify(inst, [4,3,3])` returns `(True, "ok")`; dropping the last
coordinate returns `(False, "answer must have exactly 3 coordinates")`.

## Difficulty ladder

| preset | n | p | status |
|---|---:|---:|---|
| demo | 3 | 7 | hand-solvable illustration |
| easy | 36 | 131071 | bare 0/3, but structural hint solved 1/3; rejected by G9(b) |
| medium | 42 | 2147483647 | **ships; bare and hinted both hardened** |
| hard | 48 | 2305843009213693951 | available, not needed |

Escalation first raises the modulus at fixed witness length, growing answer
entropy without adding coordinates; it reports `cap_bound` before crossing the
2,000-character output limit.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified; JSON round-trip held |
| G2 | empty, dropped, out-of-range, swapped, and duplicated corruptions rejected with five distinct reasons |
| G3 | realistic prose/fenced response round-tripped; garbage returned `None` |
| G4 | 0/200,000 structure-aware uniform guesses; exact density `p^-42`, log10 = -391.94 |
| G5 | exactly one answer; Gaussian elimination 78,477 operations, max 0.009906 s |
| G6 | diagonal, greedy repair, 256 restarts, and copy-`b`: each 0/8; reference Gaussian solve 8/8 as expected |
| G7 | doubled `n=84` instance built and verified; search space increased |
| G8 | 80 invariance checks, 200 real-transform checks, 20/20 unrelated keys distinct |
| G9 | final three arms 0/3; 450 chars, 113 estimated tokens, 42 atoms, 254 intended operations |

## Oracle evidence

The shipping bare transcript is `llm_loop_transcript.jsonl`:

| model | seed | result | exact grading reason |
|---|---:|---|---|
| x-ai/grok-4.6 | 603813698 | failed | row 0 gave 983089426, expected 1845316118 |
| anthropic/claude-sonnet-5 | 1928472635 | failed | row 0 gave 0, expected 446853289 |
| google/gemini-3.1-pro-preview | 554179494 | failed | row 0 gave 1801885483, expected 1041938522 |

| G9 arm at medium | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; G9(b) passes |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`: at the shipping rung, naming rank one bought no
measured success. This does **not** show that the insight was irrelevant. One
hinted model explicitly invoked Sherman--Morrison but returned bad arithmetic,
and another consumed its 32k reasoning budget without visible output. At the
discarded easy rung the hint did matter (1/3 solved), which is why the single
permitted move to medium was used.

## Use

```python
from gen_0909_2769 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 0909.2769 20
```

The module is standard-library-only and performs no I/O or network access.

## Caveats

- This is no claim of computational hardness. A normal computer solves the
  shipping system in milliseconds; the benchmark measures no-tool compression
  and exact execution after recognizing a low-rank decomposition.
- The finite-field encoding is not in Shaebani's paper, so this row must not be
  counted as native combinatorics coverage. The paper licenses only the central
  perfect-matching-to-fall-coloring correspondence.
- The `0/200,000` guess result samples uniform, correctly shaped vectors in
  `F_p^42`. It establishes negligible uniform density, not difficulty under an
  informed or language-model prior.
- The expanded graph has `2*p^42` vertices, so Hopcroft--Karp was not run on an
  explicit edge list. The stronger succinct Gaussian solver was run instead.
  No external CAS, SMT solver, or alternative black-box rank-revealing solver
  was tested.
- Oracle failures partly reflect long exact modular arithmetic: the intended
  route is below the formal operation cap but near enough that this family may
  measure arithmetic reliability as much as discovery of the decomposition.
- The canonical key is complete for this constructed matching-plus-star graph
  shape (`p`, `n`, and star-fiber width). Tests cover equation reorder/rescale,
  coordinate permutation, global translation, and their compositions; they do
  not enumerate every abstract graph automorphism.
