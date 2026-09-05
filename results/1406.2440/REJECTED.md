# Rejected: arXiv 1406.2440

Paper: Felix Joos, [*Induced Matchings in Graphs of Bounded Maximum
Degree*](https://arxiv.org/abs/1406.2440) (2014).

## Decision

No generator is shipped. Exact induced-match witnesses make **G** and **V**
straightforward, but **H fails on Track A**, and both paper-native and attempted
salvage constructions fail **H on Track B**. The attempted module is retained as
`rejected_gen_1406_2440.py`, together with its local report and the error-only
oracle transcripts, as required.

## What the paper proves and what is easy

Section 1 defines an induced matching as vertex-disjoint edges with no graph edge
joining endpoints of two selected edges. Verification is therefore an exact scan
of the proposed edges and endpoint adjacencies.

Theorem 1 proves that every graph without isolated vertices and with maximum
degree `Delta >= 1000` has an induced matching of size at least

```text
n / ((ceil(Delta/2)+1)(floor(Delta/2)+1)).
```

The paragraph immediately before Section 2 explicitly says the proof is
constructive and yields a polynomial-time algorithm. The proof repeatedly chooses
an edge `uv`, deletes `N[u] union N[v]` and the vertices made isolated, recurses,
and adds `uv`; degrees, neighborhoods, isolated vertices, and the displayed weight
`f(v)` are all obtained by graph scans. Section 1 also gives a simpler greedy lower
bound for every graph without isolated vertices and notes that the same sharp bound
was already obtained by simple induction for girth at least six. Section 3 identifies
small-degree exceptions and leaves the general statement as Conjecture 2.

The introduction's NP-hardness statement concerns computing a *maximum* induced
matching, even for bipartite subcubic graphs. It does not establish average-case
hardness for an inverse-planted distribution, and it is not the guaranteed-size
search problem solved by Theorem 1.

## H failure on Track A

For the theorem-native task—find any matching of the guaranteed size—the paper's
own constructive polynomial-time procedure produces the certificate. A planted
feasible matching does not repair this: the paper proves no distributional hardness
for such instances. Asking for an optimum also loses G, because a planted matching
does not carry an upper-bound certificate and the paper supplies no unlimited hard
family with certified optima.

## Mechanical cost versus compact route on Track B

The paper's sharp examples in Section 1 are a clique of order
`ceil(Delta/2)+1` (or the floor variant) with the complementary half of `Delta`
private leaves attached at each clique vertex. Each component has induced matching
number one. For `Delta=1000` and 16 components, an explicit graph has 4,016,016
vertices and 6,012,000 edges; prior measurements enumerating all edges took
0.279436 s and 0.284577 s.

That apparent gap is only an encoding choice. In the paper's compact component
description, both the standard method and the supposed shortcut choose one displayed
pendant edge per component in 32 index operations: the obvious by-hand ansatz succeeds
16/16. Under an arbitrary explicit relabelling, both recovery and graph scanning must
read `Theta(n+m)` data (16,040,016 vertex/adjacency items here), which is far beyond
G9(c)'s 300-operation limit. A public succinct relabelling restores the same direct
formula. Thus the mechanical and compact routes are comparable in every honest
encoding.

## Audit of the retained cyclic-marker attempt

An attempted salvage inverse-generated a regular cyclic core, attached private
leaves, and translated each forbidden-difference set by hidden endpoint differences.
Its original report claimed a 15,497-operation `O(k^2 p)` reference method but only
138 operations for the compact route. That comparison was invalid:

- Recovery needs only the 15 star sets `F_0j` and the one triangle set `F_12`, not
  all 120 pair sets.
- At the hard preset (`k=16`, `p=127`), those 16 sets contain 1,008 listed residues.
  The recovery verified 8/8 instances in a mean 0.000109 s (maximum 0.000120 s),
  followed by 17 modular operations.
- The purported no-tool shortcut must inspect those same 1,008 residues to locate
  the cyclic runs, then perform the same 17 modular operations. Its corrected route
  length is therefore at least 1,025 operations, not 138.

The strongest mechanical method and compact route are the same `O(k p)` algorithm
with the same 1,025 counted operations. There is no compression gap, and the route
also independently fails G9(c)'s 300-operation cap. The mandatory hardening run
could not supply contrary evidence: the configured OpenRouter key returned HTTP 403
`Key limit exceeded` on every redraw, so the preserved transcripts contain zero
scored attempts and are not counted as model failures.

## Gate summary

| Gate | Result |
|---|---|
| G | Pass for feasible witnesses by inverse generation or Theorem 1's construction. |
| V | Pass by exact endpoint and adjacency checks. |
| H, Track A | **Fail:** Theorem 1 explicitly gives a polynomial-time certificate-producing method; planted average-case hardness is unsupported. |
| H, Track B, paper sharpness family | **Fail:** compact input makes the solution the obvious 32-operation algorithm; hidden explicit input removes the compression. |
| H, Track B, cyclic-marker attempt | **Fail:** mechanical and compact routes both inspect 1,008 residues and use 17 modular operations. |
| G9(c), cyclic-marker attempt | **Fail:** corrected intended route is at least 1,025 operations, above the cap of 300. |
| Overall | **Rejected after the Track B audit.** |
