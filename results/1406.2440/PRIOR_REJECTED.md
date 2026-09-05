# Rejected: arXiv 1406.2440

Paper: Felix Joos, [*Induced Matchings in Graphs of Bounded Maximum
Degree*](https://arxiv.org/abs/1406.2440) (2014).

## Decision

No generator is shipped.  The paper's theorem-native search problem passes G and
V but fails **H on Track A**, and it does not yield an honest **Track B**
compression task.  The NP-hard problem mentioned in the introduction is a
different problem--computing a *maximum* induced matching--and the paper gives no
distributional hardness result for an inverse-planted family.

This is a Step 0 rejection, before module code or oracle runs.  There is therefore
no `gen_1406_2440.py`, self-test report, or hardening transcript to retain or
fabricate.

## What the paper actually proves

Section 1 defines an induced matching as a set of edges which are pairwise
vertex-disjoint and have no graph edge joining endpoints of two selected edges.
Such a witness is exactly verifiable by checking the selected pairs and all
adjacencies among their endpoints.

Theorem 1 proves that a graph without isolated vertices and with maximum degree
`Delta >= 1000` has an induced matching of size at least

```text
n / ((ceil(Delta/2)+1)(floor(Delta/2)+1)).
```

The sentence immediately following the extremal and large-girth discussion says
that the proof is constructive and that it is easy to derive a polynomial-time
algorithm which computes a matching of the guaranteed size.  The proof gives the
routine: select a reducible edge `uv`, delete `N[u] union N[v]` and the vertices
made isolated by that deletion, recurse, and add `uv`.  Claims 1--3 and Cases 1--2
guarantee a choice deleting at most
`D=(ceil(Delta/2)+1)(floor(Delta/2)+1)` vertices for every output edge.  All the
quantities used to choose and check the edge--degrees, neighborhoods, isolated
vertices, and the rational weight `f(v)`--are computable by graph scans.

The easy/special regimes matter:

- The introduction gives an even simpler greedy induced-matching bound for every
  graph without isolated vertices.
- Theorem 1's stronger bound has the constructive polynomial-time procedure just
  described.
- The paper says the same sharp bound was already known by a simple induction for
  girth at least six.
- Section 3 says the displayed bound is false at maximum degrees three and four
  for two named exceptions and states the remaining small-degree claim only as
  Conjecture 2.
- The introduction's NP-hardness citations concern determining the *maximum*
  induced matching, even in bipartite subcubic graphs.  They do not make the
  guaranteed-size search task hard, and worst-case NP-hardness does not establish
  hardness for a planted random distribution.

## Track A failure

For the native task licensed by Theorem 1--"find any induced matching of the
guaranteed size"--the certificate is produced by the paper's own polynomial-time
recursive deletion algorithm.  Thus a Track A claim would be false for every
distribution in the theorem's regime, not merely unsupported on a special case.

The prior-triage proposal to plant an induced matching and add bounded-degree
distractors does not repair this.  Planting proves that one prescribed matching is
feasible, but the paper supplies no average-case theorem for that distribution.
The cited subcubic NP-hardness is worst-case hardness of the optimum and is outside
Theorem 1's `Delta >= 1000` regime.  In particular, it cannot serve as the required
hardness basis for random planted instances.

Asking for a maximum matching instead also loses the proposed generation route.
An inverse-planted feasible matching is not an upper-bound certificate.  The paper
does not provide an unlimited family of hard instances with carried optimality
certificates.  Its only explicit exact-optimum family is the sharpness construction
below, and that family is structurally trivial.

## Mechanical cost versus compact route: Track B audit

The sharp examples in Section 1 are `H1` and `H2`: start with a clique of order
`ceil(Delta/2)+1` (respectively `floor(Delta/2)+1`) and attach the complementary
half of `Delta` pendant vertices to every clique vertex.  Each component has
exactly `D` vertices and induced matching number one.  A disjoint union of `k`
such components therefore has a known `k`-edge certificate.

I quantified the tempting Track B presentation at `Delta=1000`, `k=16`.  Sixteen
copies of `H1` have **4,016,016 vertices**, **6,012,000 edges**, and an ordinary
adjacency-list scan visits **16,040,016 vertex/adjacency items**.  Two Python runs
which enumerated all 6,012,000 edges took **0.279436 s** and **0.284577 s** on this
machine.  In canonical component coordinates, directly naming one pendant edge
per component takes **32 integer index operations**; 200,000 repetitions averaged
**2.1988 microseconds** per 16-edge answer.

Those numbers do not justify Track B, because the apparent gap is an encoding
artifact:

- If the graph is rendered compactly as the paper's union of clique-with-leaves
  components, the strongest mechanical algorithm on the *actual encoded input* is
  the same 32-operation direct formula as the supposed compact route.  "Choose one
  displayed pendant edge from each component" is also the obvious by-hand ansatz,
  so the required fourth failing in-context attack would instead succeed on every
  instance.  Mechanical cost and compact-route length are the same `Theta(k)`.
- If vertex names are arbitrarily permuted and the full edge list is rendered so
  that the answer is not exposed, both the standard connected-component/graph
  scan and any route that exploits the extremal decomposition must read essentially
  the same `Theta(n+m)` data.  At the quantified setting the compact route is no
  shorter than the 16,040,016-item mechanical scan, far beyond G9(c)'s 300-operation
  intended-route cap; the multi-million-edge prompt is also not a no-tool problem.
- If a succinct relabelling map is supplied to avoid that edge list, applying the
  public map to one canonical pendant edge per block is again the direct mechanical
  algorithm.  Concealing the same fact behind laborious large-integer arithmetic
  would test calculation, not induced-matching structure.

Thus the one construction whose certificate and optimum the paper supplies has no
usable middle ground: in a self-contained compact statement the shortcut is the
obvious algorithm, while in a nonrevealing explicit statement there is no
compression gap.  Track B fails H rather than being rejected merely because a
polynomial algorithm exists.

## G/H/V summary

| Gate | Result |
|---|---|
| G for Theorem 1's guaranteed-size task | Pass: theorem-backed recursive deletion. |
| V | Pass: exact endpoint, edge, disjointness, and cross-adjacency checks. |
| H, Track A | **Fail:** the paper explicitly gives a polynomial-time certificate-producing procedure. |
| H, Track B | **Fail:** compact sharpness inputs have a 32-operation obvious solution; nonrevealing inputs make the compact route as long as the graph scan. |
| Maximum-induced-matching alternative | No acceptable family: worst-case hardness does not cover a planted distribution, and the paper supplies no hard optimality-certified construction. |
| Overall | **Rejected at Step 0.** |

