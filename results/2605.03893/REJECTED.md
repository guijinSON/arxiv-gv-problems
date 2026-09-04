# Rejected: arXiv 2605.03893

Paper: David Gamarnik, Miklós Z. Rácz, and Gabe Schoenbach,
[*Optimal Hardness of Online Algorithms for Large Common Induced
Subgraphs*](https://arxiv.org/abs/2605.03893), arXiv:2605.03893v1 (2026).

## Decision

No generator is shipped. The suggested family—plant matching vertex sets that
induce the same hidden graph in two host graphs—has an exact, inexpensive
witness, but it is **not in the distribution or algorithmic model covered by
the paper's hardness theorem**. It therefore fails **H (hardness)** at Step 0.

There are two ways to repair one side of that mismatch, and each breaks the
other side:

- Planting a common induced subgraph gives G and V, but correlates the two host
  graphs. Theorem 4 assumes two *independent* graphs from
  `G(n, 1/2)`, so it supplies no hardness claim for this planted distribution.
- Sampling the paper's independent `G(n, 1/2)` pair preserves its distribution,
  but the paper's Algorithm 1 constructs a valid witness in polynomial time in
  the half-optimal regime. Above that regime, where the online lower bound
  applies, the paper gives no answer-first construction or efficiently carried
  certificate.

The task explicitly says to stop when G, H, and V cannot hold together. Thus no
`gen_2605_03893.py`, `selftest_report.json`, `README.md`, or oracle transcript
was created; those artifacts would falsely suggest that a supported hard
family reached the later gates.

## The exact problem and theorem regime

Section 1 defines a solution to largest common induced subgraph (`LCIS`) as a
pair `(H1, H2)` of induced subgraphs of input graphs `(G1, G2)` for which there
is a graph isomorphism. Its size is the common number of vertices. In the
paper's average-case problem, `G1` and `G2` are mutually independent samples
from `G(n, 1/2)`.

Definition 1 then restricts the computational model. An online algorithm
processes one new vertex from each graph per round, sees their connections to
previously processed vertices, and may either retain its current partial
solution or add one matched pair. Every addition is irrevocable, both added
vertices must already have been processed, and at least one must be newly
processed in that round.

Theorem 4 is correspondingly narrow: for every fixed `epsilon > 0`, every
algorithm in this online class finds a solution of size at least

```text
(2 + epsilon) log_2(n)
```

with probability at most `n^{-Omega(log n)}` for all sufficiently large `n`.
It is not a lower bound for arbitrary offline algorithms, and it is not a
lower bound for planted or otherwise correlated graph pairs. Section 1.4
explicitly leaves hardness for other algorithm classes open and calls the
broader computation-to-optimization gap conjectural.

This distinction also cannot be enforced by the required static
`render`/`verify` interface. Once the entire graphs are rendered, a solver has
offline access. A submitted final mapping does not certify that it was chosen
using only the information available at each online round. Asking instead for
an algorithm whose behavior is online on every possible input would no longer
be a bounded, locally checkable witness.

## Step-0 discriminating test

The question required by the prompt is: *what algorithm produces the
certificate, and what does it cost?*

In the regime where the paper actually constructs certificates, the answer is
its `Greedy` Algorithm 1. It maintains a partial bijection and adds the first
available vertex pair having identical adjacency bits to all already matched
vertices. Theorem 3 proves that this produces a common induced subgraph of size
at least `(2 - epsilon) log_2(n)` with high probability. Claim 1 gives runtime

```text
O(n^2 log n) with high probability on the paper's random inputs,
O(n^3) in the worst case.
```

The paper sharpens the size to `2 log_2(n) - 9 log log(n)` in Corollary 1.
Consequently, a family that samples independent graphs and runs this procedure
to obtain `inst["answer"]` would ship exactly the output of a polynomial-time
algorithm. A large space of possible vertex tuples would not rescue H.

This also rules out an honest Track B declaration. Track B requires both an
acknowledged mechanical algorithm and a compact route after recognizing some
structure. Independent random graph pairs do not carry a planted symmetry or
invariant that lets a solver recover Algorithm 1's mapping in at most 300 exact
operations. Introducing such a shortcut would again replace the independent
random distribution with a new structured one not analyzed by the paper.

## Why the proposed planted generator is unsupported

Suppose a generator first chooses `k` vertices in each graph, samples one
`k`-vertex graph `F`, and copies `F` onto both selected sets. The witness is the
two selected lists together with the copying bijection, and verification takes
`O(k^2)` exact edge comparisons. This establishes G by inverse generation and
V by direct inspection.

It does not establish H. The two induced edge arrays agree by construction,
so corresponding edges across the two hosts are correlated rather than
independent. Conditioning independent `G(n, 1/2)` graphs on that agreement is
the same distributional change in different words. None of Theorem 4, the
multi-overlap-gap proof, or the interpolation argument analyzes recovery under
this planted law. In fact, the proof repeatedly uses independence: fixed edge
agreements have probability `1/2`, and the interpolated inputs are independent
after conditioning on the online history.

Relabelling the hosts, adding random decoy edges, or balancing degrees does not
restore joint independence. It may hide simple statistics, but it cannot turn
an unsupported planted distribution into the theorem's distribution. A clique,
association-graph, spectral, or branch-and-bound attack would still have to be
tested, yet even four failing empirical attacks could not supply the missing
Track A theorem for the generated distribution.

## Why nearby formulations do not qualify

- **Ask only for the paper's greedy-size witness.** Algorithm 1 is the required
  domain-standard attack and succeeds by construction in polynomial time. This
  fails Track A, and there is no separate compact Track B route.
- **Ask for a witness above `(2 + epsilon) log_2(n)`.** Theorem 4 says online
  algorithms almost surely fail to find one, but it does not construct one.
  The cited existential optimum near `4 log_2(n)` is obtained by probabilistic
  existence/concentration, not by a certificate-producing construction in this
  paper. Generating an independent pair and then searching for such a witness
  violates G.
- **Ask for an optimal common induced subgraph.** A feasible isomorphism proves
  only a lower bound. The paper provides no cheaply checkable optimality
  certificate, so this loses V as well as G.
- **Encode the online history in the answer.** Replaying a trace can verify that
  each addition remains an isomorphism, but cannot verify that the solver did
  not use future edges when deciding. The final static instance exposes those
  edges regardless.
- **Use worst-case LCIS hardness.** Section 1 cites external worst-case
  inapproximability, but that does not imply hardness of an answer-first planted
  distribution. The paper neither gives a certificate-carrying worst-case
  reduction nor licenses one as its central construction.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G—construction with a known witness | Pass only after planting, or below the online threshold via Algorithm 1 | Planting breaks the theorem's independent distribution; Algorithm 1 is polynomial-time. |
| H—hardness of the generated distribution | **Fail** | Theorem 4 covers only independent random inputs and online algorithms; the proposed distribution is planted and the static solver is offline. |
| V—cheap exact witness checking | Pass | Check distinct in-range vertices, bijection shape, and all `k choose 2` edge/non-edge equalities. |
| Track A | **Unavailable** | No theorem in the paper covers planted recovery or arbitrary offline algorithms. |
| Track B | **Unavailable** | The polynomial greedy route has no paper-backed compact shortcut within the 300-operation cap. |
| G4–G9 / oracle loop | Not run | An analytic Step-0 failure cannot be repaired by random-guess or LLM failure statistics. |

The prior triage was correct about the witness and verifier, but its phrase
“plant matching vertex sets” silently left the distribution on which the
paper proves hardness. That is the decisive failure.
