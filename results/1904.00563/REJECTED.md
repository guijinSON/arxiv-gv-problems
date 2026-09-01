# Rejected: proper 3-orientations of bipartite planar graphs

Paper: Kenta Noguchi, *Proper 3-orientations of bipartite planar graphs with
minimum degree at least 3*, [arXiv:1904.00563](https://arxiv.org/abs/1904.00563).

## Decision

The proposed family fails gate **H (hardness)**. I therefore did not create a
generator, a self-test report, or an oracle-loop transcript. Producing those
artifacts would incorrectly present a polynomial-time constructive problem as a
hard witness-search problem.

## Exact problem and regime

An orientation chooses one direction for every edge of a simple graph. It is
proper when adjacent vertices have different indegrees, and it is a
`k`-orientation when every indegree is at most `k`.

Theorem 3 states that every bipartite planar graph with minimum degree at least
3 has a proper 3-orientation. The prior-triage proposal was to give such an
undirected graph to the solver and request the edge directions as the witness.
That witness is cheap to verify exactly, and inverse generation is possible, so
G and V are not the issue.

## Why H fails

Section 2 does more than prove existence: the proof of Theorem 2 supplies a
direct construction. Specialised to Theorem 3 (`k = 2`):

1. A bipartite planar graph has maximum average degree below 4, by Lemma 1.
2. Hakimi's bounded-orientation result therefore gives an orientation in which
   every vertex has indegree at most 2.
3. For each vertex `x` on one bipartition side, reverse enough of its edges that
   currently point from `x` to the other side to make the indegree of `x`
   exactly 3. Minimum degree at least 3 guarantees enough such edges.
4. Every reversal only decreases the indegree at the opposite endpoint. Thus
   one side finishes with indegree exactly 3 and the other with indegree at most
   2. Every edge consequently joins vertices with unequal indegrees.

The bounded-indegree orientation in step 2 is polynomial-time computable with
an integral max-flow instance: create one unit-demand node per edge, connect it
to its two endpoint nodes, and give every vertex-to-sink arc capacity 2. The
endpoint receiving an edge's unit is its head. The remaining reversals are a
linear scan. Hence a solver does not need to search a large witness space or
recover a plant.

This is precisely an easy regime, not a hardness regime. Increasing the graph
size only enlarges a polynomial-time flow computation.

## Other results do not yield an acceptable family

- Theorem 4 completely determines the proper orientation number of the stated
  quadrangulations (3, except 2 for the cube), while the corresponding witness
  remains constructible by the same method.
- Theorem 5 constructs minimum-degree-2 bipartite planar graphs with no proper
  3-orientation. Asking a solver to certify nonexistence would violate the task's
  requirement that the answer be a positive, cheaply checked witness.
- The paper cites earlier complexity work but proves no hard parameter regime
  that can replace the easy planar/minimum-degree regime while retaining the
  requested paper-based justification.

Because the failure is established from the paper's construction itself, the
LLM hardening loop is neither necessary nor meaningful for this family.
