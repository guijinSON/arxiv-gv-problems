# Superseded prior-triage rejection: arXiv 2503.05218

> This note correctly rejects the initially proposed dense random planting, but
> it is not a rejection of the later Proposition 4.1 Track B construction in
> `gen_2503_05218.py`. It is retained as audit history only.

Paper: Mingyang Guo and Klas Markstrom, [*Density conditions for k
vertex-disjoint triangles in tripartite graphs*](https://arxiv.org/abs/2503.05218).

## Decision

No module is shipped.  The suggested planted-random family passes **G** by inverse
generation and **V** by three exact edge-membership checks per submitted triangle,
but it fails **H on both tracks**.

- **Track A fails:** Theorem 1.3 is an extremal existence theorem, not a
  computational- or distributional-hardness theorem.  At the theorem's own
  `n >= 5k+2` boundary, the suggested random distribution is solved by a much
  cheaper greedy algorithm on every measured seed.
- **Track B fails:** the successful mechanical route is already a by-hand route.
  At a shipping-size, answer-cap-compatible preset it needs about 82 exact edge
  lookups, while any answer must write 48 vertex labels.  There is no meaningful
  mechanical/compact compression gap and no hidden invariant to discover.

This is a rejection before implementation, so there is no `gen_*.py` to retain and
no oracle transcript or self-test report to manufacture.

## What the paper actually proves

Section 1 defines a `(k,n)`-cyclic density triple by six strict inequalities.
Theorem 1.3 states that a balanced tripartite graph with `n >= 5k+2` and such
densities contains `k` vertex-disjoint triangles.  Corollary 1.4 specializes this
to a common lower density `d(G) > tau_k(n)`.

The theorem does not produce a certificate from density data alone.  Its Section 3
proof argues by a smallest counterexample and begins by taking a maximal packing
`T={T_1,...,T_{k-1}}`; finding such a packing is already the search problem that a
generator is not allowed to solve.  Consequently, a generator still has to plant
and retain its triangles (inverse generation), exactly as the prior triage proposed.

The paper also identifies what makes its two natural regimes easy:

- In Section 1, triangles are explicitly converted to hyperedges of a balanced
  3-uniform hypergraph, making the requested witness an ordinary set packing.
- In Section 4, the triangle-factor proof reduces the dense remainder to two
  bipartite perfect matchings using Hall's theorem.  Proposition 4.1 is the clearest
  case: if one bipartite pair is complete, two perfect matchings directly compose
  to a triangle-factor.  This is a polynomial certificate-producing route, so that
  regime cannot support Track A either.
- The sharpness example following Theorem 1.3 has only `k-1` usable vertices in one
  block.  Adding one edge to cross the equality exposes precisely the rare bridge
  needed for the kth triangle.  It is an outlier construction; camouflaging it with
  more such edges merely creates more interchangeable bridges and makes the witness
  easier.

## Measured mechanical cost

I tested the prior-triage distribution at `n=82, k=16`, exactly
`n=5k+2`.  Each of the three bipartite pairs had exactly 4,517 edges, so

```text
q = 4517 / 6724
q * (q - 15/82) + q
  = 1 + 7511/45212176 > 1.
```

Because all three densities equal `q`, this is every one of the six strict
`(k,n)`-cyclic inequalities.  For each seed, 16 disjoint triples were sampled
first.  Their three sets of required edges were forced into independently sampled
4,517-edge bipartite graphs by equal-count swaps, preserving the exact densities
and the planted certificate.

The attack scanned unused `A`, `B`, and `C` labels in increasing order and accepted
the first available triangle.  It did not read or score the planted triangles.

| measurement | result |
|---|---:|
| greedy successes | **128 / 128** |
| exact edge-membership lookups, mean | **81.969** |
| exact edge-membership lookups, median | **80** |
| exact edge-membership lookups, maximum | **105** |
| greedy-loop median wall time | **0.00002286 s** |
| triangle candidates tested, mean | **35.0** |
| actual triangles per graph, 32-seed mean | **167,124.75** |
| actual triangle-count range | **166,691--167,595** |

The same attack succeeded 32/32 at each additional measured rung:

| `(n,k)` | density | mean counted probes in the original coarse counter | max |
|---|---:|---:|---:|
| `(12,2)` | 0.645833 | 7.81 | 16 |
| `(27,5)` | 0.661180 | 18.94 | 33 |
| `(52,10)` | 0.669009 | 36.94 | 50 |
| `(82,16)` | 0.671773 | 58.31 | 66 |
| `(132,26)` | 0.673726 | 94.84 | 115 |

That table's coarse counter charges one unit for a candidate `C` even though it can
perform two edge lookups; the 128-seed figures above are the authoritative exact
lookup counts.

This also shows why candidate-space size would be misleading.  A random labeled
triangle has heuristic probability `q^3 = 0.3031567` of existing, and 16
independently modeled triples have probability about `q^48 = 5.09e-9`.  Thus a
structure-aware G4 sampler could easily report zero hits in 200,000 guesses while
the elementary greedy attack still solves every instance in tens of operations.
The `q^48` figure is only the independent-edge heuristic--disjoint sampling and
plant conditioning create small dependencies--and is not presented as an exact
solution density.

## Mechanical cost versus compact route

The mechanical method for this generated distribution is the greedy
triangle-enumeration scan above.  In the balanced adjacency representation its
worst-case bound is `O(k n^3)`, but the relevant measured distributional cost is
only 82 exact lookups on average and 105 at worst over the 128 shipping-size seeds.
It succeeds without identifying the planted packing because incidental triangles
are abundant.

There is no shorter structural route supplied by the construction.  The three
edge sets are independently random conditional on their counts and the forced
certificate, so the planted triangles carry no solver-visible invariant.  The best
compact route is the same greedy scan.  Merely writing a certificate takes 48
vertex labels (`3k`), and checking it takes 48 edge lookups (`3k`).  The measured
mechanical cost is therefore less than twice the irreducible witness/checking work
and is already far below G9's 300-operation limit.  The two costs are comparable,
which is exactly the condition for rejecting rather than relabeling the family
Track B.

## Why escalation cannot repair the proposed family

Growing `n` while keeping `k` fixed does not hide the witness: the common threshold
tends to the positive root near 0.618, so an arbitrary triple continues to be a
triangle with constant probability.  The greedy cost remains `O(k)` on this random
distribution.  Growing `k` only lengthens the answer, and throughout the paper's
`k <= (n-2)/5` regime the measured greedy cost scales linearly with the certificate.
Adding random decoy edges increases triangle abundance and makes the attack still
easier.

A deliberately adversarial hard distribution might exist for the general
tripartite triangle-packing problem, but this paper supplies neither such a
distribution nor an average-case hardness theorem.  Importing an external SAT/3DM
gadget distribution would no longer be the paper's density construction, and its
hardness would have to be established independently.  Inventing that surrogate
cannot turn the rejected planted-random proposal into a supported Track A claim.

## Final gate assessment

| requirement | assessment |
|---|---|
| G -- generatable | Pass for the proposed family: sample the `k` triples first and force their edges by swaps. |
| V -- verifiable | Pass: exact part/range/disjointness checks and three edge lookups per triangle. |
| H -- Track A | **Fail:** no distributional hardness result, and greedy solved 128/128 at the theorem boundary. |
| H -- Track B | **Fail:** 82 mechanical lookups versus 48 output/checking operations; no compression gap. |
| Overall | **Rejected at Step 0; no builder or oracle run is warranted.** |
