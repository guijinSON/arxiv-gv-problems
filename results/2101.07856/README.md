# arXiv 2101.07856 problem generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (indexed Boolean pairs) |
| Intuition | invariant: the two-bit support of the least binary address selects a coordinate product |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 5 proof of Theorem 3 |

This module turns Martin, Paulusma, and Smith’s [*Colouring Graphs of Bounded Diameter in the Absence of Small Cycles*](https://arxiv.org/abs/2101.07856) into a succinct 3-colouring-certificate problem. The solver receives a signed NAE formula and the paper’s exact graph-gadget construction: a central vertex, literal pairs, clause triangles, and uniformly subdivided literal–clause paths. With six subdivisions the resulting graph has diameter 4 and no induced `C4` or `C6`. The answer gives one Boolean choice per literal pair; `verify` expands it to all graph vertices and checks every generated edge exactly.

This is a paper-licensed reduction, not a claim that the solver directly searches arbitrary graphs from the paper’s native class. The computational search exposed to the solver is the NAE system. The graph structure remains visible and load-bearing: the witness is expanded to a colouring of the 13,261-vertex shipping graph and all 26,442 edges are checked.

## Why Track B is honest

Theorems 1 and 2 are positive results: their diameter-2 List 3-Colouring regimes are polynomial-time solvable by constant-size precolouring, exhaustive propagation, and linear-time 2-list colouring. The generator therefore uses the diameter-4 construction from Theorem 3 instead. That theorem proves worst-case NP-completeness for `(C4,C6,...,Ct)`-free graphs when even `t >= 6`; it says nothing about the average-case hardness of this planted distribution, so no Track-A claim is made.

An efficient promised-distribution algorithm does exist. There are seven address coordinates at shipping size, so exhaustive testing of all 21 possible coordinate-pair products is guaranteed to find a certificate. Across the measured seeds it stopped after at most 20 candidates, costing at most 63,960 Boolean operations and 0.006254 seconds. Exact NAE-DPLL also solved 8/8 (at most 40 nodes and 140,388 counted operations), and a stronger WalkSAT-style routine solved 8/8. The compact route is shorter: find the lexicographically least address, read its two `1` coordinates, then evaluate their product on every address—162 comparisons/Boolean operations at shipping size. The benchmark tests whether a no-tool solver discovers that support invariant.

The source NP-hardness reduction begins with variables appearing at most three times. The target-class argument after subdivision does not use that occurrence bound; this generator deliberately uses denser regular source formulas while retaining the same target graphs. Every witness is sampled before the clauses: addresses determine the Boolean product first, and clause signs are drawn only afterward from NAE patterns satisfied by it.

## Worked demo (`seed=0`)

The complete demo rendered data are:

```text
PROPERLY 3-COLOUR A SUCCINCT DIAMETER-4 GRAPH

All graphs here are finite, undirected, and simple.  A proper 3-colouring gives
each vertex one of colors 0, 1, 2 and gives adjacent vertices different colors.
The graph below has 139 vertices and is defined completely
by the following gadget rules, so no external paper or convention is needed.

There are 6 Boolean variables x0 through x5.  A positive literal x_i
has Boolean value x_i; a written negation !x_i has value 1-x_i.  A three-literal
NAE clause is satisfied exactly when its three literal values are not all equal.
The order of clauses and the order of literals inside a clause have no meaning.

The variables have distinct public 4-bit addresses.  Bits
are written from coordinate 0 on the left to coordinate 3
on the right:
  x0=1101  x1=0101  x2=1100  x3=1001  x4=0110  x5=1010

The 6 signed NAE clauses are:
  C0: !x5 x3 x0
  C1: !x5 x2 !x3
  C2: x0 !x4 !x1
  C3: !x1 !x2 !x4
  C4: x3 x1 !x4
  C5: !x5 x2 x0

These clauses define the graph exactly as follows.

* Make one vertex z.
* For each xi make adjacent vertices P_i and N_i, and join both to z.
* For every clause Cj make a triangle T_j0,T_j1,T_j2.
* Occurrence k of clause j selects P_i when it is xi and N_i when it is !xi.
  Join that selected literal vertex to T_jk by a path obtained by subdividing
  the edge exactly 6 times.  Each such path therefore has 6 new internal
  vertices and 7 edges.  Paths are otherwise vertex-disjoint.
* Join every new internal path vertex to z.  There are no other edges.

This construction has diameter exactly 4 and has no induced 4-cycle or induced
6-cycle.  You need not write colors for all 139 vertices.
Instead give a compact certificate with one pair [i,b_i] for every variable.
The checker gives z color 0.  If b_i=1 it gives (P_i,N_i) colors (1,2), and if
b_i=0 it gives them colors (2,1).  On each subdivided path, colors 1 and 2 then
alternate away from its selected literal endpoint.  The checker gives each
clause triangle the lexicographically first permutation of colors (0,1,2)
that differs from the adjacent path-end color at all three positions.  Such a
permutation exists exactly when the corresponding NAE clause is satisfied.
Finally the checker explicitly scans every graph edge for equal endpoint colors.

Submit exactly 6 pairs, in increasing index order [0,b_0],[1,b_1],...,
[5,b_5].  Every index appears once; every b_i is the integer 0 or 1.
Repeated bit values are allowed.  Indices are 0-based and all bounds are inclusive.

Give your final answer inside <answer></answer> tags as one JSON array of pairs.
Example syntax only: <answer>[[0,0],[1,0],[2,0],[3,0],[4,0],[5,0]]</answer>
Output nothing else inside the tags.
```

The least address is `0101`; its two-bit support is coordinates 1 and 3. Their coordinate product gives:

```text
<answer>[[0,1],[1,1],[2,0],[3,0],[4,0],[5,0]]</answer>
verify(...) -> (True, "ok")
```

Flipping `b1` gives `[[0,1],[1,0],[2,0],[3,0],[4,0],[5,0]]`, and `verify` returns `(False, "NAE clause C2 has three equal literal values")`. The demo has 12 valid certificates and is genuinely hand-solvable, either by the six clauses or by the selector invariant.

## Difficulty presets

| preset | n | occurrence degree | clauses | graph vertices | graph edges | answer pairs | status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 6 | 3 | 6 | 139 | 270 | 6 | hand example; skipped by hardener |
| easy | 78 | 24 | 624 | 13,261 | 26,442 | 78 | **shipping; hardened** |
| medium | 78 | 36 | 936 | 19,813 | 39,546 | 78 | reserve, denser at fixed answer length |
| hard | 78 | 48 | 1,248 | 26,365 | 52,650 | 78 | reserve, denser at fixed answer length |

Earlier `n=30` and `n=54` rungs were retired even though the first was oracle-hardened: randomized one-pass greedy solved 1/8 and 2/8 seeds respectively. The shipping rung is the first that clears the adversary panel.

## Gate results

| gate | measured result |
|---|---|
| G1 | planted certificate verified on 12/12 preset/seed combinations |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | realistic prose/fenced response round-tripped; garbage returned `None` |
| G4 | 0/200,000 uniform structure-aware Boolean guesses; space `2^78` |
| G5 | shipping sampled density 0/200,000; guaranteed scan max 63,960 operations, 20 candidates, 0.006254 s |
| G6 | degree/sign, greedy, two random-greedy restarts, and affine ansatz each 0/8; promised reference 8/8 |
| G7 | doubled `n=156` instance built and verified; 26,521 graph vertices |
| G8 | 80/80 relabelling invariance checks and 80/80 carried witnesses; 20/20 unrelated keys distinct |
| G9 | 537 answer characters, 135 estimated tokens, 156 atoms; intended route 162 operations |

## Bare oracle loop

The repository hardener used its current two-vendor pool at medium reasoning effort. All calls were at the shipping `easy` preset.

| seed | model | result | reason |
|---:|---|---|---|
| 630717927 | `google/gemini-3.8-flash` | failed | no parseable answer |
| 774324574 | `openai/gpt-5.6-terra` | failed | parsed candidate violated C6 |
| 1502099306 | `google/gemini-3.8-flash` | failed | no parseable answer |

Verdict: `hardened`, zero escalations, shipping parameters `n=78, degree=24, subdivisions=6`.

## G9 arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 3/3 | too easy at shipping; diagnostic only |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is `1.0`. The structural sentence made all three attempts succeed while an equal-register placebo made none succeed. This strongly supports the intended interpretation: the difficulty is finding the two-bit support invariant, not executing or transcribing it. The hinted result is diagnostic and does not block shipping. The answer and route remain below the 2,000-character, 256-atom, and 300-operation caps.

## Use

From this directory:

```python
import random
import gen_2101_07856 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=7, **params)
statement = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** 78
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2101.07856 20
```

The module is standard-library-only. It makes the repository `gvlib` import available when present but does not depend on it.

## Caveats

- `0/200,000` estimates density only under uniform Boolean vectors with the required index structure. It does not bound a solver that uses clauses, addresses, local search, or the guaranteed coordinate scan.
- This family is intentionally easy with tools: the promised coordinate scan, exact DPLL, and WalkSAT measurements all succeed. It is only a Track-B no-tool benchmark.
- The bare pool produced two unparseable responses and one explicit invalid certificate. The hardness evidence is therefore weaker than three fully formed wrong witnesses, although the 3/3 hinted solves and 0/3 placebo result give a clean diagnostic contrast.
- Industrial SAT/SMT solvers, SDP/spectral methods on the expanded graph, and large-restart local search were not run. Their likely success would be consistent with Track B rather than a defect in the declared claim.
- `canonical_key` deliberately ignores clause signs to be invariant under literal-pair swaps. Rare switching-inequivalent formulas sharing the same unsigned scopes can collide; the tested generated seeds did not.
- The graph is presented succinctly and the answer is a compact gadget certificate, not a 13,261-entry color vector. Exact expansion and edge checking prevent that compression from weakening verification.
