# Rejected: arXiv 2012.11953

Paper: Tony Johansson,
[*Hamilton cycles in weighted Erdős–Rényi graphs*](https://arxiv.org/abs/2012.11953)
(2020).

## Decision

No problem family supported by this paper simultaneously clears G, H, and V.
The natural proposal—sample edge-disjoint Hamilton cycles first and then add
random edges—does clear inverse generation and exact verification. It fails H
on **Track A** because neither Theorem 1.2 nor Theorem 1.3 is a computational
hardness result for that planted distribution. It also fails **Track B**: a
uniformly sampled hidden cycle supplies no compact, instance-visible route, and
in the dense random regime the mechanical Hamilton-cycle algorithm is already
output-optimal up to constants.

This is a Step 0 rejection. No generator, self-test report, README, or oracle
transcripts were created; recording later gates after the hardness-basis failure
would manufacture evidence for a distribution the paper does not analyze.

## What the paper actually studies

“Weighted” does not mean that the requested Hamilton cycles carry numerical
edge weights. Section 1 defines a symmetric nonnegative **rate matrix** `R`.
Every unordered pair `{u,v}` receives an independent exponential arrival time
of rate `R(u,v)`, and `G_(n,R)(t)` contains the pairs that have arrived by time
`t`. Equivalently, a fixed-time sample is an inhomogeneous Erdős–Rényi graph
with independent inclusion probabilities `1-exp(-R(u,v)t)`.

For fixed `k`, the paper's property `A_k` is the existence of
`floor(k/2)` pairwise edge-disjoint Hamilton cycles, together with a perfect
matching when `k` is odd; every one of these subgraphs must also be mutually
edge-disjoint. This exact definition is in Section 1 and is restated through
the `k`-graph extremal quantity `s_k(G)` in Section 2.2.

Definition 1.1 gives the theorem's actual parameter regime. The transition
matrix induced by `R` must have `lambda(R)=o(1)` and satisfy

```text
lambda(R) <= (n ||M||)^(-alpha-gamma),
min_u d_R(u) >= d,       d_R(V) <= b d n,
sigma(A) <= b (|A|/n)^(1-2 alpha),
||R|| <= d n^(-gamma),
```

for constants `alpha < 1/2`, `gamma > 0`, and `b > 0`. Theorem 1.2 then says
that, for `k=O(1)`, the random graph process reaches `A_k` at the same hitting
time at which its minimum degree reaches `k`, with high probability. Theorem
1.3 gives the corresponding fixed-time limiting probability
`exp(-gamma_k)`. The pseudorandom-host special case assumes an `(n,d,mu)` graph
with `mu <= d(d/n)^alpha`.

These are **existence and threshold statements**, not average-case lower bounds
for finding the cycles. Indeed, the proof outline explicitly defines `s_k` by
a maximum over all `k`-graphs, conditions on some maximizing `F`, and proves
that random sprinkling is overwhelmingly likely to increase `s_k` until it is
full. Sections 4–6 prove that many bounded-size boosters exist via alternating
walks. They neither output the initial maximizing paths/cycles nor give a
finite per-instance construction of the final Hamilton cycles. Consequently,
sampling `G_(n,R)` honestly does not satisfy G: the paper guarantees a witness
only with high probability, and obtaining the witness still requires solving
the instance.

## Assessment of the proposed inverse plant

The triage proposal samples the answer first, so its G and V properties are
straightforward:

1. sample `floor(k/2)` random Hamilton cycles, rejecting overlaps while the
   answer is still being constructed;
2. sample any extra graph edges; and
3. verify a submitted answer by checking its vertex permutations, closing
   edges, membership in the graph, and pairwise edge-disjointness.

The verifier would be exact and linear in the certificate size and could accept
any valid decomposition, not merely the planted one. The answer space is also
far too large for uninformed guessing. None of that establishes H.

If the planted edges are forced while the other sparse edges have probability
about `log(n)/n`, the result is not a sample from the independent process in the
paper. Encoding the force as inclusion probability 1 also violates the sparse
rate condition `||R|| <= d n^(-gamma)`: here `||R||=1` while
`d=Theta(log n)` makes the right-hand side tend to zero. If instead all edges
are made dense enough that deterministic planted edges fit Definition 1.1, the
instance moves into a regime where random-graph Hamilton cycles are easy to
find. In either case, Theorems 1.2 and 1.3 do not establish hardness for the
generator's distribution.

Conditioning an honest independent sample on containing a particular cycle is
the same problem in different notation: it gives inverse generation, but it is
not the independent `G_(n,P)` law to which the theorem applies. The paper gives
no distribution-preserving transformation that carries a known cycle into an
unconditioned sample.

## Mechanical cost measured on the candidate

To avoid rejecting merely because “an algorithm exists,” I measured the natural
two-cycle candidate at the largest useful answer size under the 256-atom cap:

```text
n = 120, k = 4
plant = two independent uniform Hamilton cycles, conditioned edge-disjoint
decoys = every remaining edge independently present with
         q = 8 log(n)/n = 0.3191661161854697
answer = two length-120 vertex orderings (240 atomic elements)
```

The reference attack fixed vertex 0, ran depth-first Hamilton search with
least-onward-degree ordering and randomized tie breaking, allowed four
restarts, deleted the first recovered cycle, and repeated on the residual
graph. This is a deliberately simple exact-search baseline, not the stronger
specialized random-graph algorithm.

| measured over seeds 0–39 | result |
|---|---:|
| verified two-cycle recoveries | **40/40** |
| recursive search states, median | 258 |
| recursive search states, maximum | 175,825 |
| adjacency tests, median | 217,115 |
| adjacency tests, maximum | 15,351,421 |
| wall clock per instance, median | 0.01123 s |
| wall clock per instance, mean | 0.02700 s |
| wall clock per instance, maximum | 0.48900 s |

The run used CPython's standard library only. A separate 100-seed, one-cycle
run at the same `n` and `q` was solved 100/100 with at most four restarts
(median 122 recursive states and 0.00309 s).

This empirical failure is consistent with the relevant algorithmic literature.
Nenadov, Steger, and Su, Theorem 1.1 in
[*An O(n) time algorithm for finding Hamilton cycles with high probability*](https://arxiv.org/abs/2012.02551),
give a randomized `O(n)` algorithm for `G_(n,p)` when
`p >= C log(n)/n` for a sufficiently large constant `C`; their Section 1.1
notes that this is optimal because writing a Hamilton cycle itself costs
`Omega(n)`. Their introduction also records polynomial algorithms down to the
ordinary Hamiltonicity threshold. Johansson's Section 2 uses the same
rotation/extension phenomenon existentially: random expansion leaves many
boosters rather than a hidden combinatorial needle.

Thus the domain-standard attack is expected to succeed in the very random
regime used to justify existence. It cannot honestly appear as a failing Track
A adversary.

## Mechanical cost versus compact route (Track B audit)

Track B does not rescue the planted proposal. The two quantities required at
triage are:

| quantity at the candidate shipping size | value |
|---|---:|
| mechanical route | 258 median recursive states in the measured two-cycle search; 217,115 median low-level adjacency tests; 0.01123 s |
| best possible compact-route output work | at least 240 vertex emissions, plus checking/deriving 240 closing edges |
| actual instance-visible compact route | **none** |

At the meaningful decision level, 258 path states versus 240 answer entries is
not a compression gap. More fundamentally, each planted cycle is a uniformly
random permutation and the instance exposes only the union graph. The seed and
the planted decomposition are not available to the solver, and there is no
invariant, change of variables, symmetry, or short ansatz in the paper that
recovers them. “Follow the planted cycles” would merely smuggle the hidden
answer into the purported insight.

For a single cycle in the dense random regime, the published mechanical route
is `O(n)` and every route is `Omega(n)` just to write the witness. Hence the
mechanical and compact costs have the same order and there is nothing for Track
B to test. For a much sparser planted graph an exact solver may take far more
work, but the compact route does not become shorter—it remains the same search.
That produces neither Track A evidence nor Track B compression.

Adding visible structure does not repair this without changing the benchmark:

- Marking planted edges through exceptional rates makes a per-edge
  probability/outlier attack recover them.
- Using a circulant or affine planted decomposition creates a short modular
  ansatz, but that ansatz is an artifact of the generator, is not a construction
  in this paper, and would be the mandatory in-context attack.
- Revealing the random seed or the pre-plant permutation directly reveals the
  certificate.
- Making `n` larger lengthens the answer; for `k=4`, `n=120` already uses 240 of
  the 256 permitted atomic elements. It does not create a hidden compact route.

## Other paper-native candidates

| candidate | failed gate | reason |
|---|---|---|
| Sample `G_(n,R)(tau_k)` honestly and ask for `A_k` | G | Theorems 1.2 and 1.3 are high-probability existence results; the proof does not construct the certificate for the sampled instance. |
| Plant the full `A_k` witness, then add sparse independent edges | H / theorem regime | Inverse generation works, but the conditioned/forced law is not the sparse independent law analyzed by the theorem and has no average-case hardness result. |
| Plant the witness and add dense random edges | H on Track A | Random-graph Hamilton algorithms and the measured baseline recover witnesses efficiently. |
| Treat Section 4's alternating booster walk as the answer | H or V | If a current maximum path/matching is supplied, obvious endpoint augmentation is short; if maximality or improvement of `s_k` must be certified, checking it reintroduces the global optimization search. |
| Ask only for the perfect matching when `k` is odd | H | Perfect matching is found by standard polynomial-time matching algorithms, with no special compact insight from this paper. |
| Ask for the hitting time or limiting probability | witness rule / H | The displayed limit is a theorem-level asymptotic statement, not a finite object inspectable against one instance; finite minimum degree itself is a direct scan. |

## Exact gate outcome

| requirement | result | evidence |
|---|---:|---|
| G — known certificate by construction | Pass only for the altered planted law | Sample cycles before edges. Honest theorem-distributed sampling does not provide the certificate. |
| V — cheap exact checking | Pass | Check permutations, graph-edge membership, matching endpoints, and edge disjointness. |
| H — Track A | **Fail** | The paper proves threshold/existence, not hardness for the inverse-planted distribution; a standard attack solved 40/40 measured dense instances. |
| H — Track B | **Fail** | Dense random-graph search is already output-linear in theory, and the random hidden plant has no shorter instance-visible route. |
| Overall | **Rejected at Step 0** | No one family satisfies G, H, and V simultaneously. |

The important distinction is that Hamilton-cycle lists are perfectly valid
witnesses. The rejection is not about verification. It is about the missing
hardness claim for an inverse-planted distribution and the absence of a
no-tool compression gap.
