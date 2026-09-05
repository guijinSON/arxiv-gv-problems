# Rejected: arXiv 2504.11450

Paper: [Optimal Hardness of Online Algorithms for Large Independent Sets](https://arxiv.org/abs/2504.11450), v2.

## Decision

No single family in the paper passes **G, H, and V simultaneously** under either track. The native hard object fails **G**; the obvious inverse-generated replacement fails **H on Track A**; and the paper supplies no compact route that would make either replacement a meaningful **Track B** family. No generator module was written because this is a Step 0 rejection.

## What the paper actually proves

Definition 2.1 is an adaptive *online-information model*, not ordinary offline independent-set search. In round `t`, an algorithm chooses a previously unseen vertex using only information revealed so far, may query future pairs, and irrevocably decides whether to add that vertex. Its final answer must remain independent. Condition (1) makes the algorithm `c`-restricted by bounding queried future pairs contained in its final answer.

Theorem 2.2 applies only to an unconditioned Erdős–Rényi graph `G ~ G(n,p)`, with

`d/n <= p <= 1 - n^(-1/d)`, `c = min(epsilon^2,1)/8`, and target size at least `(1+epsilon) log_b(np)` where `b = 1/(1-p)`.

It proves a lower bound against that restricted online model. It does **not** prove hardness for arbitrary offline algorithms, and it does not cover graphs conditioned to contain a selected independent set.

## Why the native hard family fails G

For a genuine sample from `G(n,p)` at the above-threshold size, the paper does not construct an instance together with a known independent set. Section 1 explicitly says the near-maximum size result is obtained by the moment method and is nonconstructive.

The positive Theorem 2.3 does not repair this. Its construction is detailed in Section 6: after greedy and filtering phases, it obtains `J` by **brute-force search for a largest independent set** in `G[R] ~ G(r,p)`, examining up to

`C(r, floor(2 log_b r))`

candidates, and reports total running time `n^((2+o(1)) epsilon^2 log_b n)`. Thus the certificate-producing procedure is precisely a solver for the generated subproblem, which the G rule forbids. Lemmas 6.1 and 6.2 guarantee that a witness exists with high probability; they do not output an instance-specific witness that a generator can carry.

Rejection sampling an unconditioned graph until a selected `s`-set happens to be independent is also search, not construction. Theorem 2.2 itself gives that event probability as `(1-p)^C(s,2) = (np)^(-Theta((1+epsilon)^2) log_b(np))`, so it is not a scalable workaround.

## Why the proposed planted family fails H on Track A

Sampling an answer first, deleting its internal edges, and randomizing all other edges would pass G and V. It samples a planted/conditioned graph, however, not `G(n,p)`. Theorem 2.2's probability space and online lower bound therefore do not apply. The paper gives no average-case hardness theorem for this planted distribution, and worst-case NP-hardness says nothing about it. Declaring Track A for that generator would be an unsupported distributional-hardness claim.

The online restriction also cannot be faithfully restored by merely printing the graph in a one-shot prompt: once the entire graph is visible, a solver can use future edges when choosing every earlier vertex. Asking for an adaptive strategy on all possible reveal histories would require an exponentially large, non-writable object rather than the finite witness required here.

## Track B audit: mechanical cost versus compact route

Two possible certificate-producing methods were checked.

| candidate family | mechanical method and cost | compact route | outcome |
|---|---|---|---|
| Greedy-threshold independent set in an unconditioned `G(n,1/2)` | Algorithm 1; expected linear probes with early exit, `O(n log n)` probes with high probability if every current-set adjacency is checked, and `O(n^2)` in the worst case. A direct 20-seed early-exit measurement at `n=4096` used a mean of **8,209.45** adjacency probes (range 8,115–8,360) and returned about 12 vertices. | The same sequential adjacency scan; about **8,209** probes in the measured implementation. The paper gives no invariant or change of variables that shortens it. | The mechanical and compact costs are comparable, so this tests bulk execution rather than insight. |
| Above-threshold set from Theorem 2.3 / Section 6 | Enumerate `C(r, floor(2 log_b r))` subsets of `R`; even the illustrative `p=1/2, r=128` count is **1,739,040,916,651,368,000** candidates. | The same subset search on a genuinely random `G[R]`; no short instance-specific route is given. | There is a large cost, but no compression gap. Planting a shortcut changes the distribution and comes from the benchmark designer, not the paper. |

Remark 6.3 also gives a polynomial-time regime when `epsilon = C/sqrt(log_b n)`, with running time `n^(2C^2+O(1))`. That is another easy/algorithmic regime to avoid on Track A, but it still supplies no short no-tool route for Track B.

Accordingly, Track B is not a rescue: the easy family has no meaningful compression, while the hard family has no compact route at all. An artificial modular labeling, symmetry, or other planted decoding rule could create such a route, but that structure is absent from the paper and would benchmark the added encoding rather than its online-random-graph result.

## Gates

- **G:** fails for the paper's native above-threshold `G(n,p)` family because the witness is obtained by brute-force solving or by infeasible rejection sampling.
- **H / Track A:** fails for the inverse-generated planted alternative because Theorem 2.2 does not cover that distribution.
- **H / Track B:** fails because mechanical and compact routes are either the same scan or the same exponential search; there is no short structural route to test.
- **V:** would pass: a proposed vertex set is checked exactly by its cardinality and by testing every internal pair for nonadjacency. V alone is insufficient.

The prior-triage proposal—plant an independent set and randomize the remaining edges—was therefore not used.
