# Edge-group three-coloring generator — arXiv:1512.08995

| profile field | value |
|---|---|
| Track | **A — structural hardness** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple, serialized as a 252-symbol color word |
| Objects shown | bipartite graph, input-centered edge groups, conflict outputs |
| Intended intuition | constraint propagation: recognize the balanced hidden tripartition |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 1 fixed-`k` reduction |

## What the problem is and why the result is trustworthy

Jonathan Turner's [The Edge Group Coloring Problem with Applications to Multicast Switching](https://arxiv.org/abs/1512.08995) defines an edge group as incident edges sharing a center. Edges sharing an endpoint must receive different colors exactly when they belong to different groups. Section 1 reduces ordinary vertex `k`-coloring to the paper's restricted bipartite problem: subdivide every source edge, make the original edges at each input one principal group, and add `k-1` singleton stubs. With three colors, the two stubs force the principal group to be monochromatic, so its color word is precisely a proper 3-coloring of the source graph.

The generator samples three equal hidden classes first, builds a simple 5-regular graph using only cross-class matchings, performs degree-preserving switches, randomly relabels all inputs, and applies that exact reduction. It never solves the generated instance. The checker expands the compact principal-group word and performs exact symbol and conflict comparisons; it accepts any normalized valid coloring, not just the plant.

## Why this is hard (Track A)

Section 1 proves NP-completeness even for fixed `k=3`. The shipping regime has 252 source vertices, degree 5, equal hidden classes, and 50 rounds of switches per class vertex. That theorem is worst-case evidence, not a distributional theorem; the distributional claim is instead the explicitly limited one that no efficient exact method is known for this generated regime and that the measured attacks all failed. Exact DSATUR/DPLL exhausted 1,000,000 nodes in 16.018 seconds on the G5 instance and did so on all eight G6 seeds. Greedy, min-conflicts, and non-backtracking spectral attacks were also 0/8. As a supplemental, non-module diagnostic, SciPy/HiGHS MILP was 0/8 with a 30-second limit on independently seeded shipping instances.

This parameter choice matters. An earlier 6-regular, lightly switched version was discarded after HiGHS found witnesses on 2/3 samples in 4.4–23.2 seconds. Section 2's one-group-per-input case is directly colorable output by output; this family avoids it by having a principal group and two singleton stub groups at every input. Sections 2–5 give layering, greedy/recoloring, few-colors, and matching-based approximation methods, but none is an exact recovery algorithm for the promised three-coloring used here.

## Worked demo

The `demo` preset with seed 7 is hand-solvable. This is its complete rendering:

```text
Exact three-coloring of a bipartite edge-group graph

An edge group is a set of graph edges sharing one common endpoint.  A valid
edge-group coloring assigns colors to edges so that two edges with a common
endpoint have different colors exactly when they belong to different groups.
Edges in the same group may share a color.  Only colors 1, 2, and 3 may be used.

This instance has inputs I0,...,I11.  Every line below defines one
degree-two conflict output Oj and its two incident inputs.  At each input Iu,
all edges from Iu to listed conflict outputs form one principal group P[u].
In addition, Iu has two private degree-one stub outputs, with one incident edge
in singleton group A[u] and the other in singleton group B[u].  Thus the three
groups at Iu are P[u], A[u], and B[u].  This compact description specifies the
entire bipartite graph, every edge, and every group; private stub outputs have
no other incident edge.

Conflict outputs (input order within a line is irrelevant):

O0: I0 I4
O1: I0 I6
O2: I0 I7
O3: I1 I6
O4: I1 I8
O5: I1 I11
O6: I2 I3
O7: I2 I5
O8: I2 I9
O9: I3 I4
O10: I3 I5
O11: I4 I10
O12: I5 I11
O13: I6 I10
O14: I7 I9
O15: I7 I11
O16: I8 I9
O17: I8 I10

Find a valid edge-group coloring with the three allowed colors.  Return its
principal-group color word: symbol u is the common color assigned to every
edge in P[u].  Once that symbol is chosen, assign the two other colors to the
singleton stub groups A[u] and B[u], in increasing order.  Because the two
stubs and P[u] are distinct groups at one input, any valid three-coloring has
exactly this form.  A degree-two output Oj requires its two displayed
principal colors to differ.

The answer must be one word of exactly 12 symbols from the alphabet 1,2,3,
in input order I0 through I11; spaces, commas, and repeated indexing are
not allowed.  To remove global color-name symmetry, symbol 0 must be 1 and
symbol 4 (the least-numbered conflict neighbor of I0)
must be 2.

Give your final answer inside <answer></answer> tags, as that exact color word.
Syntax-only example (not instance data): <answer>123132</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>133122231231</answer>`, and `verify` returns `(True, "ok")`. Corrupting its last symbol to `4` returns `(False, "every symbol must be one of 1, 2, or 3")`. Exact enumeration finds 40 normalized valid words for this demo, so a person can find one without reconstructing the particular plant.

## Difficulty and gates

| preset | n | regular degree | switch rounds | status |
|---|---:|---:|---:|---|
| demo | 12 | 3 | 0 | hand example; not shipped |
| easy | 252 | 5 | 50 | **shipping preset; oracle held** |
| medium | 252 | 5 | 75 | available; not reached |
| hard | 252 | 5 | 100 | available; not reached |

| gate | measured result |
|---|---|
| G1 | 16/16 plants verify; answers JSON-round-trip |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | realistic tagged response round-trips, 252 elements |
| G4 | 0/200,000 uniform normalized color words valid; language size `3^250` |
| G5 | shipping density 0/200,000; demo has 40 answers; DPLL 1,000,001 nodes / 16.018 s, unsolved |
| G6 | five attacks, each 0/8; DPLL total 8,000,008 nodes |
| G7 | doubled `n=504`, 1,260 source edges, plant verifies |
| G8 | 40/40 relabelings invariant, 40/40 carried witnesses valid, 20/20 unrelated keys distinct |
| G9 | all three arms 0/3; 254 chars, 254 conservative tokens, 252 atoms, 252 operations |

The bare shipping loop used these decisive attempts; the Grok timeout is an error and was redrawn, not counted as a model failure.

| model | seed | result | reason |
|---|---:|---|---|
| Claude Sonnet 5 | 1455522895 | failed | no answer after the 32k-token reasoning limit |
| Gemini 3.1 Pro Preview | 905765635 | failed | returned a word with an edge conflict |
| GPT-5.6 Terra | 345977992 | failed | returned the wrong word length |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; G9(b) passes |
| placebo | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. Naming the equal hidden tripartition did not improve the solve rate in this small sample, so the evidence does not show that the claimed constraint-propagation intuition itself caused the failures. The answer and route remain under the caps: 254 serialized characters, 252 atomic symbols, and 252 post-insight color placements/checks.

## Use

```python
import importlib.util

path = "results/1512.08995/gen_1512_08995.py"
spec = importlib.util.spec_from_file_location("edge_groups", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
inst = m.make_instance(seed=123, **params)
print(m.render(inst))
answer = m.parse_answer("<answer>" + inst["answer"] + "</answer>")
print(m.verify(inst, answer))  # (True, "ok")
```

From the repository root, emit examples with `bash scripts/emit.sh 1512.08995 20`.

## Caveats

NP-completeness does not prove average-case hardness for this planted distribution. Polynomial spectral algorithms are known for some denser random planted 3-coloring models; degree 5 is outside the explicit sufficiently-large-density guarantee I found, but a specialized belief-propagation, SDP, modern SAT/CP solver, or a sharper planted-coloring algorithm could still break this family. The dependency-free panel includes non-backtracking spectral clustering and exact DPLL, but not a full industrial SAT/SMT solver, SDP, or belief propagation. The supplemental HiGHS test is not part of `selftest()` because the module must remain standard-library-only.

The G4/G5 density samples are uniform over normalized words with the two stated color symmetries fixed. They do not model a solver's learned or spectral prior, and zero hits is only an upper-frequency observation, not a proof of uniqueness. The structural key uses exact degree, triangle, common-neighbor, and closed-walk invariants; it is relabeling-invariant but is not a complete graph-isomorphism canonical form. Finally, 252 of the 256 allowed answer atoms are already used. Harder presets therefore erase more matching-layer structure at fixed answer length; after 100 switch rounds, `escalate()` honestly returns `"cap_bound"` rather than claiming that the mathematics has no harder instances.
