# Spanning Halin certificates from arXiv:1505.06181

| Profile field | Value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain / regime | combinatorics / finite discrete |
| Computational core | graph |
| Certificate | matrix certificate over GF(2) |
| Native objects | a GF(2)-labelled simple graph and the paper's explicit `H_1`/`Q` template specification |
| Intended intuition | invariant: affine relabelling preserves XOR differences |
| Domain essentiality / reduction | native / none |

## What the problem is, and whether to trust it

[Chen and Shan, *Dirac's Condition for Spanning Halin Subgraphs*](https://arxiv.org/abs/1505.06181) defines a Halin graph in Section 1 as a planar spanning tree with no degree-two vertex together with a cycle on exactly its leaves. Section 2 defines the ladder-based graph `H_1`; Proposition 1 deletes one leaf-cycle edge from each of two such graphs and joins the pieces with three edges to make a pancyclic Halin graph `Q`.

This generator samples the `Q` parameters and an invertible affine map on the binary vertex labels first, then carries the known tree and cycle through that map. The solver receives the complete, native graph and must recover the template parameters, matrix rows, and translation. Verification expands the proposed map and compares every edge exactly. It independently checks that the expanded tree is connected and acyclic, has no degree-two vertex, that the cycle contains exactly its leaves, and that every tree-edge leaf split is a cyclic interval. No planted answer is read by `verify`.

The local evidence is complete: all nine gates pass, including 0/200,000 structure-aware guesses, four attacks failing on eight seeds, exact demo enumeration, and 20/20 distinct canonical structures. The required external hardness evidence is **not complete**: on 2026-09-05 all bare, hinted, and placebo OpenRouter calls returned HTTP 403 `Key limit exceeded (total limit)`. The script-owned error transcripts are retained; no API error was counted as an oracle failure, and the family must not be called hardened until that account limit is repaired and the harness is rerun.

## Why Track B

The paper says in Section 1 that unrestricted spanning-Halin containment is NP-complete, but that worst-case statement does not justify Track A for this promise distribution. The main Dirac theorem (Theorem 1.1), and the Extremal Case 1 result in Section 3, are existence results; the non-extremal proof also invokes the Regularity and Blow-up Lemmas. Section 3's Extremal Case 2 proof exposes an easy regime—a universal vertex plus a Hamiltonian cycle in the remaining Dirac graph is a spanning wheel—which these maximum-degree-four instances avoid. This module therefore names the efficient recovery method rather than hiding it.

The successful reference algorithm enumerates the bounded `Q` templates, applies Weisfeiler-Lehman refinement with exact backtracking, and interpolates an affine map. Its template-enumeration phase is `O(N^4)` on this promise language. At the shipping preset it solved 8/8, took at most **1,252,040 counted operations**, and averaged **1.754 s** per instance. Once the topology and XOR invariant are recognized, a one-pass topological labelling plus seven-bit affine-basis interpolation takes **187 operations** and averaged **0.083 s**, also solving 8/8. The benchmark is this mechanical-to-compact gap, not a complexity-theoretic hardness claim.

## Worked demo

This is the complete output of `render(make_instance(n=16, seed=0))`:

```text
Find a spanning Halin certificate for the graph below.

A Halin graph is a simple planar graph H=T union C.  T is a spanning tree
on at least four vertices with no vertex of degree 2.  Its leaves are exactly
the vertices of the cycle C, and T and C share no edges.  This instance is
promised to be one of the pancyclic Halin graphs Q constructed in Section 2,
Proposition 1 of the source paper, under an unknown affine relabelling.

There are N=16=2^4 vertices, numbered 0 through 15.  Read each number
as a 4-bit column vector over GF(2), with bit 0 the least significant bit.
All edges are undirected.  The following is the complete edge list; there are
no loops, repeated edges, or unlisted edges:
9 15
1 14
5 7
0 14
5 15
4 12
7 11
4 11
7 8
4 8
3 11
1 9
6 14
5 8
2 13
2 3
0 10
12 13
0 1
1 3
2 10
6 9
10 13
6 15
3 12

Your certificate specifies the hidden Q template and affine relabelling.
Let M=(N-4)/2=6.  Choose integers m1,u1,u2.  Put m2=M-m1.  They must
satisfy m1>m2>=2, 0<=u1<ceil(m1/2), and 0<=u2<ceil(m2/2).

For H1(m) starting at offset s, name its vertices
  x=s, y=s+1, a_i=s+2+2i, b_i=s+3+2i  (0<=i<m).
Its edges are a_i--b_j exactly when |i-j|<=1, together with
x--a_0, x--b_0, y--a_(m-1), y--b_(m-1), and x--y.
Build H1(m1) at offset 0 and H1(m2) at offset 2m1+2.  Delete both x--y
edges.  Add x1--x2 and y1--y2.  Finally define c_i=b_i for even i and
c_i=a_i for odd i, and add c_(u1) in the first H1 joined to c_(u2) in
the second H1.  This is Q.

The field "rows" must contain exactly 4 integers r_0,...,r_3 in
0..15.  Their 4-bit expansions are the rows of an invertible matrix A
over GF(2).  "shift" is an integer in 0..15.  A canonical vertex v is
relabelled as w=A v XOR shift, where output bit i is the parity of the 1-bits
in (r_i AND v).  The resulting edge set must equal the displayed graph.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys "m1", "u1", "u2", "rows", and "shift".  Integer bounds
are inclusive; indices are 0-based; rows are ordered and repeats are allowed
only when the matrix nevertheless has full rank (which in fact forbids them).
Example format: <answer>{"m1":4,"u1":0,"u2":0,"rows":[1,2,4,8],"shift":3}</answer>
Output nothing else inside the tags.
```

The answer is:

```text
<answer>{"m1":4,"u1":1,"u2":0,"rows":[15,3,11,13],"shift":10}</answer>
```

`verify(inst, answer)` returns `(True, "ok")`. Changing the shift from 10 to 11 returns `(False, "expanded template does not equal the instance graph")`. The demo is genuinely hand-scale: its language has 645,120 candidates, but the four-bit XOR arithmetic and 25 edges can be checked on paper after spotting the invariant.

## Presets and gates

| Preset | N | Edges | Candidate-space bits | Status |
|---|---:|---:|---:|---|
| demo | 16 | 25 | 20 | hand example; skipped by harden.py |
| easy | 32 | 49 | 29 | oracle run blocked before a valid attempt |
| medium | 64 | 97 | 41 | not reached |
| hard | 128 | 193 | 55 | provisional shipping preset; further escalation is `cap_bound` because the compact route would exceed 300 operations |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted certificates verify; all JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced model-style response round-trips; garbage returns `None` |
| G4 | 0/200,000 valid guesses after fixing the visible `Q` signature; candidate language size 20,972,799,094,947,840 |
| G5 | demo exact count 1/645,120; shipping density 0/200,000; 2,048-restart attack 0 hits; reference mean 1.754 s |
| G6 | four attacks each 0/8; reference and compact algorithms each 8/8 |
| G7 | doubled `N=256` instance builds and verifies; search language grows from 55 to 71 bits |
| G8 | 40/40 affine/reordering invariance checks; 20/20 unrelated keys distinct |
| G9(c) | 73-character conservative worst-case bound, 11 atoms, 37 tokens, 187 intended operations |

## Oracle and G9 diagnostics

| Arm | Preset | Valid solved/attempts | Script-recorded errors | Conclusion |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 HTTP 403 | no hardness verdict possible |
| structural hint | hard | 0/0 | 4 HTTP 403 | diagnostic blocked |
| placebo hint | hard | 0/0 | 4 HTTP 403 | diagnostic blocked |

Thus hinted minus placebo is undefined as an oracle statistic (stored as `0.0` only because both denominators are zero). Nothing can yet be concluded about whether the XOR hint helps. The size and operation caps—the only gated part of G9—do pass.

## Use

```python
from gen_1505_06181 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
prompt = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit after a successful oracle rerun with:

```bash
scripts/emit.sh 1505.06181 20 hard
```

## Caveats

- The GF(2) affine hiding layer is a structure-preserving vertex relabelling added by the benchmark; it is not a construction used in the paper. The underlying handed object and every checked edge are still the paper's native `Q` graph, so this is not a surrogate reduction.
- The generator covers Proposition 1's two-`H_1` composition, not arbitrary graphs satisfying the paper's asymptotic Dirac condition. Removing the affine promise changes the recovery problem substantially.
- The 0/200,000 result is relative to the declared prior: the cap/bridge signature is treated as free and fixes the shipping template, after which the matrix is uniform over invertible matrices and the shift is uniform in range. It is not a claim about a solver with a learned prior over graph isomorphisms.
- The panel tests identity, smallest-translation, coordinate-permutation, and random-restart attacks. It does not run nauty/Traces, SAT, or ILP software; the executable exact template matcher is the domain reference used instead.
- `canonical_key` is complete for the generated `Q` signatures used at named presets, with a rooted-distance fallback for the 16-vertex demo. The explicit G8 tests cover affine relabelling and edge-order changes, which are the declared family symmetries.
- Most importantly, the four-vendor loop remains blocked by account quota. Do not submit or describe this family as hardened on the strength of local gates alone.
