# Rejected: no supported hard generated distribution

Paper: Jean Cardinal and Raphael Steiner,
[*Inapproximability of shortest paths on perfect matching polytopes*](https://arxiv.org/abs/2210.14608),
arXiv:2210.14608v1 (26 October 2022).

## Decision

No problem generator is shipped. The native two-flip-path task has **G** by
planting an intermediate perfect matching and has **V** by replaying the two
flips, but the paper proves worst-case hardness, not hardness for a
certificate-first distribution. The concrete planted distribution in the
workspace is in fact broken by a construction-aware attack on every tested
shipping instance. It therefore fails **H** and mandatory gate **G6**.

This is an honest rejection under Step 0. The pre-existing
`gen_2210_14608.py` is an unshippable draft retained for audit; its Track-A
declaration and passing G6 report are not valid. No `selftest_report.json`,
README, or successful oracle evidence was created from it.

## What the full paper actually says

The full 15-page paper and its LaTeX source were reviewed, including the
proofs and figures rather than only the abstract.

- Section 1.1 defines the perfect matching polytope `P_G` as the convex hull
  of incidence vectors of perfect matchings in a balanced bipartite graph.
- Lemma 1 gives the executable adjacency test: two perfect matchings are
  adjacent in the skeleton exactly when their symmetric difference is one
  alternating cycle. Shared matching edges outside that cycle are allowed.
- Theorem 1.1 is the hard regime. For every fixed `k >= 2`, it is NP-hard to
  output a skeleton path of length at most `k`, even for maximum-degree-three
  bipartite graphs whose two supplied matchings are promised to be at distance
  at most two. Under ETH, the lower bound extends to
  `(1/4-o(1)) log N / log log N`.
- Section 2.2 proves the result by starting with a Hamiltonian digraph `D`,
  replacing its vertices by subcubic bipartite gadgets, and defining endpoint
  matchings `M1` and `M2`. The promised two-flip witness is obtained by using
  a Hamiltonian cycle of `D` twice. Thus the proof does not hand a generator a
  path unless the generator already knows the hard source witness.
- Lemma 3 is explicitly constructive in the opposite direction: its cycle
  certificate is produced by a polynomial-time algorithm using connected
  components, directed-cycle decomposition, path finding, and recursion.
- Lemma 4 is also explicit: once a two-step path is known, it writes down edge
  weights making the endpoint the unique optimum. Neither lemma supplies a
  separate Track-A certificate-search family.

The longest-cycle result imported as Theorem 2.1 is likewise a worst-case
result. The cited Bjorklund-Husfeldt-Khanna paper explicitly distinguishes its
worst-case lower bound from typical sparse instances: its Section 6 gives a
simple polynomial algorithm finding linear-length paths in bounded-outdegree
expanders and notes that most bounded-outdegree random digraphs are expanders.
It also cites algorithms for recovering hidden Hamiltonian cycles in most
random graphs. Planting a Hamiltonian cycle and adding random arcs therefore
cannot inherit the worst-case theorem by assertion.

## Why inverse generation does not preserve the hardness theorem

The tempting construction is to sample an intermediate matching `P` first,
then choose endpoint matchings so that both `M1 -> P` and `P -> M2` are valid
cycle flips. This knows a certificate without search and verification is
linear-time. But it produces a new planted distribution. Theorem 1.1 says
nothing about that distribution, and a solver may return any valid
intermediate matching rather than recover the plant.

The paper's own reduction does not repair this gap. To instantiate it while
retaining the certificate, a generator must know a Hamiltonian cycle in the
source digraph. Sampling that cycle first again creates a planted Hamiltonian
distribution not covered by Theorem 2.1. Starting with an arbitrary hard
source instance preserves the theorem but loses G, because obtaining the cycle
is the hard search problem itself. Generating satisfiable source formulas from
a planted assignment has the same unsupported average-case step.

There is no honest Track-B relabelling of this argument. The draft's successful
attack below is a mechanical randomized search; the instance exposes no
shorter invariant or change of variables from which its randomly sampled
intermediate matching can be reconstructed within the 300-operation intended
route cap. Calling that search the reference algorithm would therefore supply
the mechanical route without the compact route Track B requires.

## Direct break of the draft distribution

The draft uses shipping parameters `n=240, decoys=2`. After normalizing START
to the identity and deleting START and FINISH edges, every left vertex has
three options. By construction this residual 3-regular bipartite graph is the
union of the planted matching and two decoy perfect matchings.

The missing construction-aware attack was:

1. Randomize the order of each residual adjacency list.
2. Run the polynomial Kuhn augmenting-path algorithm to extract a perfect
   matching, remove it, and repeat; the remaining edges give the third factor.
3. Check all three factors with the public verifier.
4. Restart with fresh row orders.

With a fixed RNG rule and a cap of 3,000 factorizations per instance, this
found a verified two-spanning-flip witness on **8/8** panel seeds:

| instance seed | factorizations to first verified witness | wall-clock seconds |
|---:|---:|---:|
| 100 | 97 | 0.334 |
| 101 | 1,148 | 3.136 |
| 102 | 43 | 0.127 |
| 103 | 2,142 | 5.853 |
| 104 | 625 | 1.725 |
| 105 | 442 | 1.237 |
| 106 | 334 | 1.012 |
| 107 | 514 | 1.414 |

G6 requires zero successes. The result is eight, so increasing the DPLL node
cap or relying on oracle failures cannot save this distribution.

The same break exposes a G4 measurement error. The draft samples uniformly
from all `(n-1)!` full cycles relative to START, almost all of which use edges
that are not present in the sparse graph. A solver who has read the statement
searches among graph-respecting perfect matchings, and randomized
1-factorization samples exactly such candidates. Reporting zero hits among
200,000 mostly non-edges is therefore not the required structure-aware guess
probability.

There is also a theorem-alignment problem: Lemma 1 requires one alternating
cycle, which need not span every graph vertex, while the draft asks both flips
to be spanning cycles. That is a legitimate stricter puzzle, but Theorem 1.1
does not establish hardness for this newly restricted output language or for
the draft's random union-of-permutations distribution.

## Gate outcome

| requirement | result | evidence |
|---|---:|---|
| G - certificate known by construction | Pass | Sample an intermediate matching first and compose two cycle flips. |
| H - claimed hardness for the generated distribution | **Fail** | The theorem is worst-case only; the actual shipping distribution is solved 8/8 by randomized 1-factorization. |
| V - cheap exact witness verification | Pass | Check matching incidence and that each consecutive symmetric difference is one cycle. |
| G4 - structure-aware guess resistance | **Fail as measured** | The draft sampler ignores the graph-edge constraint and measures the wrong candidate prior. |
| G6 - adversary panel | **Fail: 8/8 successes** | Construction-aware factorization attack, maximum 5.853 seconds. |
| G9 / oracle loop | Not reached | H and G6 already fail. The existing transcript contains HTTP 402 errors rather than three completed oracle attempts. |

## What would be needed to revisit this paper

A viable Track-A attempt would need a certificate-first sampler with an
independent distributional-hardness justification, not merely Theorem 1.1,
and it would need to defeat randomized factorization, proper SAT/CP encodings,
and the paper's reduction-aware long-cycle attacks. A viable Track-B attempt
would need both a measured polynomial reference algorithm and a genuinely
short construction-visible route distinct from that algorithm. The paper and
the tested draft provide neither combination, so further hardening would tune
against one run instead of establishing the required family.
