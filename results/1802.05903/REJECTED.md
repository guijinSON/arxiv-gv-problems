# Rejected at Step 0: no compact route around the paper's recovery algorithm

Paper: Maria Chiara Angelini, [*Parallel Tempering for the planted clique
problem*](https://arxiv.org/abs/1802.05903), arXiv:1802.05903v2 (2019).

## Decision

No generator is shipped. The native planted-clique and planted-independent-set
families both pass **G** and **V** in isolation, but fail **H** for the two
available tracks.

- **Track A fails:** Sections 3 and 5 give Parallel Tempering (PT) as the
  distribution-specific recovery algorithm, and the paper reports that it succeeds
  throughout the studied hard regimes with polynomial empirical scaling. Putting
  this successful standard algorithm in the required Track-A adversary panel would
  make G6 fail.
- **Track B fails:** on the paper's genuine distributions, the planted vertex set is
  random and the other edges are random. There is no shorter invariant, symmetry,
  change of variables, or ansatz from which a no-tool solver can read the set. The
  only paper-supported route after recognizing the structure is to execute PT (or
  another recovery search), so the compact route is no shorter than the mechanical
  route and violates the 300-operation intended-route cap.

This is not a rejection merely because an efficient method exists. The measured
mechanical and compact-route costs are compared below. Steps 1--4 were intentionally
not run after this Step-0 failure, as the task directs; there is therefore no module,
self-test report, README, or fabricated oracle transcript.

## The exact native objects and witnesses

Section 2, Eq. (1), defines the dense planted-clique distribution. Choose a hidden
set `C` of exactly `K` among `N` vertices. Every pair inside `C` is an edge; every
other pair is independently an edge with probability `1/2`. The solver is given the
graph and the known value `K` and must identify `C`. A concrete list of `K` vertices
is an exact witness: the checker verifies its length, distinctness, range, and all
`K(K-1)/2` induced edges. The generator knows this witness by inverse generation.

Section 4 defines the sparse planted-independent-set distribution. Choose a hidden
set `I` of size `K=rho*N`; put no edges inside it; use

`c_in = d(1-2*rho)/(N(1-rho)^2)`

between two vertices outside `I`, and

`c_out = d/(N(1-rho))`

between `I` and its complement. These probabilities equalize expected degrees, so
the plant is not a degree outlier. Again, the generator knows `I` before drawing the
edges, and a checker verifies the proposed `K` distinct vertices and the absence of
all induced edges. Thus neither family has a G or V problem.

## What the paper says is easy and hard

For dense planted clique, Section 2 identifies the BP threshold
`K_BP=sqrt(N/e)`. Above it, randomly initialized belief propagation recovers the
plant and the paper calls the phase easy. Its finite-size hard phase is
`K_s(N) < K < K_BP`: the planted solution is the global free-energy minimum but
randomly initialized BP stops at a paramagnetic local minimum. Below the static
threshold, recovery is called impossible rather than hard. Section 2 also notes the
information threshold near `2 log_2 N` and the quasi-polynomial exhaustive route
`O(exp(c log^2 N))`.

Section 3 applies PT with 19 replicas, inverse temperatures
`beta_i=1-0.05*i`, five Metropolis sweeps between exchanges, and exact rejection of
configurations containing a missing clique edge. Figure 3 reports successful
recovery in the hard phase and the empirical convergence law

`t(N,K_tilde) proportional to N^5.78/(K_tilde-K_tilde_s(N))^3.64`.

The author explicitly says the purpose is to show that PT is a polynomial
algorithm, while also correctly limiting the conclusion to numerical evidence at
the analyzed sizes.

For the cleaner sparse experiment, Sections 4--5 fix `d=40`. The cited fixed-degree
thresholds are `rho_max=0.1273` and `rho_l=0.138`; the paper's own numerical values
are `rho_s=0.1217(1)` and `rho_l=0.135(1)`. It runs at `rho=0.13`, explicitly inside
the hard recovery band, and reports successful PT recovery with best-fit exponent
`3.15(9)`. Figure 5 averages roughly `10^3`--`10^4` graph realizations. This is the
most favorable paper-native candidate because degree is not a planting signature
and the graph is sparse, but it is also the clearest evidence against Track A.

## Mechanical cost versus compact route

Consider the natural candidate shipping point used in the paper's sparse hard
regime: `N=1000`, `d=40`, `rho=0.13`, hence an answer of 130 vertex indices. This
fits the 256-atom answer cap.

Section 5 states that one sparse-IS Monte Carlo sweep costs `O(dN)`. With the
paper's 19 replicas and five sweeps between exchanges, one PT exchange round costs
approximately

`19 * 5 * 40 * 1000 = 3,800,000`

local neighbor-update operations, before counting the 18 replica-exchange tests.
The paper's Figure 5 then measures many PT steps to convergence and finds total
time scaling as `N^3.15` in the hard `rho=0.13` regime. Thus the mechanical route is
already millions of operations per exchange round at the smallest plotted scale,
far outside by-hand execution.

The **compact route length is the same 3,800,000-plus operations per round**, not a
dozen operations. Section 4 deliberately removes the obvious per-vertex degree
signal, and a genuine sample gives no public description of `I`: its `binom(1000,130)`
possible locations are exchangeable before the random edges are inspected. Knowing
that temperature swaps cross the free-energy barrier explains *why PT works* but
does not reveal any vertex of the witness. A solver must still maintain the 19
configurations, perform the local updates, and test swaps. There is therefore no
mechanical-versus-compact compression gap; both routes are the same algorithmic
workload and both exceed G9(c)'s 300-operation cap by more than four orders of
magnitude after only one round.

The dense model has the same defect. At the paper's `N=2000`--`5000` scales, a
single sweep costs `O(KN)` per replica and PT empirically has exponent `5.78`; the
uniform random location of `C` supplies no compact route. Moving to larger `N`
only increases unavailable computation. Moving to smaller `N` makes ordinary
maximum-clique branch-and-bound, greedy expansion, or direct inspection practical
and does not create an insight-based benchmark.

## Why the other regimes do not rescue a family

- Choosing `K>K_BP` makes BP the paper's direct easy-regime solver.
- Choosing `K_s<K<K_BP` is the intended hard phase, but PT is reported to recover
  there; this prevents Track A, while executing PT prevents Track B.
- Choosing `K<K_s` moves into the paper's impossible phase, where the graph does not
  contain enough information to distinguish the planted set from competing random
  cliques. A hidden commitment to the sampled set would add a new cryptographic
  problem not present in the paper and still would not create a compact recovery
  route.
- Asking for any clique rather than the planted clique preserves cheap verification
  but makes the near-threshold region contain unrelated witnesses. It does not
  manufacture a short intended solution, and at small rendered sizes ordinary
  clique algorithms become the fatal standard attack.
- Encoding the plant in vertex numbers, residues, repeated neighborhoods, or another
  visible pattern would no longer be the paper's exchangeable planted distribution.
  It would also be solved by the corresponding outlier or obvious-ansatz attack.
- The sparse complement relation in Section 4 is only a representation change:
  clique vertices become independent-set vertices, but their location remains
  unknown. It is not a recovery shortcut.

## Gate diagnosis

| requirement | result | evidence |
|---|---:|---|
| G -- generatable | Passes in isolation | Sample the hidden set first, then draw all allowed edges as in Section 2 or 4. |
| V -- verifiable | Passes in isolation | Check exactly all induced vertex pairs. |
| H -- Track A | **Fail** | Sections 3 and 5 report successful distribution-standard PT recovery with polynomial empirical scaling. |
| H -- Track B | **Fail** | PT costs about 3.8 million local operations per exchange round already at `N=1000,d=40`; the compact route is the same computation. |
| G6 | **Would fail on Track A** | The required standard attack is the paper's successful PT algorithm. |
| G9(c) | **Would fail on Track B** | The intended route is over 3.8 million operations after one round, versus the 300-operation cap. |
| Overall | **Rejected at Step 0** | No paper-native family makes G, H, V, and the declared track hold simultaneously. |

No probability-of-guess or oracle result is claimed: once H fails analytically,
those measurements cannot repair it.
