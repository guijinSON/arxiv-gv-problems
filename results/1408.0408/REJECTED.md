# Rejection: arXiv:1408.0408

## Decision

This paper does not yield an acceptable family under the proposed planted-path
construction.  Generation and verification are sound, but **H fails on both
tracks**.  This is a Step 0 rejection; no generator module was built.

Paper: Vincent Coll, Alexander Halperin, Colton Magnant, and Pouria
Salehi-Nowbandegani, [*Enomoto and Ota's conjecture holds for large
graphs*](https://arxiv.org/abs/1408.0408).

| gate | result |
|---|---|
| G | Passes by inverse generation: sample the ordered path partition first, then add graph edges while retaining every path edge. |
| H, Track A | **Fails.** The paper proves existence in a dense promise class, not hardness of finding a partition, and gives no average-case hardness result for any generated distribution. |
| H, Track B | **Fails for the natural planted distribution.** A routine dense-graph heuristic is already the compact route; there is no mechanical-versus-insight gap. |
| V | Passes: check roots, prescribed orders, disjointness, coverage, and consecutive graph edges exactly in linear time in the witness length. |

## What the paper actually proves

The exact problem is Conjecture 1 and Theorem 2 in Section 1.  For fixed
`k >= 3`, distinct
roots `x_1,...,x_k`, positive path orders `n_1,...,n_k` summing to `n`, and a
sufficiently large `n`-vertex graph satisfying

```text
sigma_2(G) >= n + k - 1,
```

where `sigma_2` is the minimum degree sum over a nonadjacent vertex pair, the
vertices can be partitioned into paths `P_i` such that `P_i` has order `n_i`
and starts at `x_i`.

The qualifier “sufficiently large” is not made effective.  Sections 3--7 apply
Szemerédi regularity and the blow-up lemma, handle low minimum degree in
Lemma 6, low connectivity of the reduced graph in Lemma 7, and a large
independent set in Lemma 8.  In the remaining case, Section 4 uses Ore's
theorem on the reduced graph, super-regular pairs, and the absorbing Claim 1.
These are the objects and parameter regimes actually used by the paper.

This matters for generation.  At practical benchmark sizes the main theorem
cannot be used as a theorem-backed constructor because its threshold is not
given.  Inverse generation remains valid—plant the paths first—but then the
paper supplies no hardness statement for the resulting distribution.

## Track A failure

Worst-case Hamiltonian-path hardness does not establish hardness here.  The
paper's promise is a fixed-`k`, high degree-sum class in which every sufficiently
large instance is a yes-instance.  Neither Theorem 2 nor any other result in the
paper states that finding the promised partition is hard, and no parameter
regime or average-case distribution is analyzed computationally.

I tested the direct version suggested by the prior triage:

1. uniformly shuffle the `n` vertices into three ordered planted paths of the
   prescribed sizes;
2. add every planted path edge;
3. add every other edge independently with probability `0.66`;
4. retain only instances whose degree sums satisfy Theorem 2's exact promise.

At `n=256`, `k=3` (the answer-atom ceiling), all eight seeds `0,...,7`
satisfied the degree-sum promise.  A smallest-remaining-degree depth-first
path extension found a valid partition on **8/8** instances without
backtracking:

| measurement | value |
|---|---:|
| successes / attempts | 8 / 8 |
| vertex extensions per instance | 253 |
| total extensions | 2,024 |
| median wall clock | 0.267545 s |
| total wall clock | 2.365924 s |
| implementation | Python standard library, one process |

The heuristic reserves the later roots, extends each current endpoint to the
unused neighbor with the fewest remaining choices, and moves to the next
prescribed path after reaching its required order.  It is the natural
constructive path-search attack for this dense distribution.  Its 8/8 success
would make the required Track A adversary panel fail.

The cardinality of the permutation space is therefore irrelevant: the plant
does not make this distribution hard, and the theorem's dense promise creates
many alternative witnesses.

## Track B audit: mechanical cost versus compact route

For the same shipping-size proposal, the mechanical route is the heuristic
above.  A straightforward implementation is `O(n^3)` adjacency/remaining-degree
work, required 253 successful extensions, and took 0.267545 s median at
`n=256`.  It is already far below a serious solver budget.

The planted answer is a uniformly shuffled path partition.  Consequently it
has no invariant, symmetry, change of variables, or other short description
visible in the instance.  The best “compact route” is the same sequence of 253
vertex extensions (and the witness itself contains all 256 vertices).  Thus:

```text
mechanical route: 253 extensions, O(n^3), median 0.267545 s
compact route:    253 extensions; no shorter structural route exists
gap:              none
```

This is exactly the Track B rejection condition: the compact route is no
shorter than the mechanical one.  Making the plant follow an artificial
arithmetic code would create such a shortcut, but that shortcut would come
from the benchmark encoding rather than from Theorem 2 or its proof.  It would
test recovery of the added code, not Enomoto--Ota path partitioning.

This is **not** a `cap_bound` decision.  The baseline already solves every
tested instance at the 256-atom ceiling, and increasing `n` only increases the
amount of routine polynomial work and the transcription length.  It does not
open a fixed-witness-size hardness axis or an insight gap.

## Other native witnesses considered

The paper's subsidiary finite witnesses do not repair H:

- Lemma 4 asks only for a path of length at most three in a super-regular pair;
  exhaustive common-neighbor checking is polynomial and hand-scale.
- Ore's long cycle, Williamson panconnectivity, matchings, and the star/matching
  split inside the proof of Lemma 8 all have direct classical constructive
  algorithms in the
  regimes used here.
- Claim 1 bounds a `v`-absorbing path by 17 vertices.  Blind bounded-depth
  enumeration is polynomial because 17 is constant, while an arbitrary hidden
  plant again has no compact route.  Adding a special label or modular encoding
  to reveal the plant would supply benchmark mathematics absent from the
  paper.
- Certifying that a displayed cluster pair is epsilon-regular or super-regular
  from the definition requires quantifying over subsets; making that property
  part of the answer would lose cheap exact verification rather than improve
  hardness.

Accordingly, the native main witness clears G and V but not H, and the paper is
rejected for this benchmark.
