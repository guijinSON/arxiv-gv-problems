# Rejected at Step 0: the hard random law and a known witness cannot be obtained together

Paper: Will Perkins and Yuzhou Wang, [*On the hardness of finding balanced
independent sets in random bipartite graphs*](https://arxiv.org/abs/2307.13921),
arXiv:2307.13921v1.

## Decision

No generator is shipped.  The paper's native above-threshold random family has
the desired hardness evidence but does not provide a certificate by construction.
The proposed repair--choose a balanced independent set first and omit all edges
between its two parts--provides an exact witness, but changes the instance
distribution and therefore loses that hardness evidence.

Thus the native candidate fails **G**, while the inverse-planted candidate fails
**H as a justified Track A family**.  Verification **V** would be immediate in
either case.  Track B does not rescue the paper: in the paper's constructive easy
regime the successful method and the shortest instance-visible route are the same
edge scan, whereas in the above-threshold regime the existence of any efficient
algorithm is precisely the paper's open question.

This is not a rejection merely because an algorithm exists.  It is a rejection
because no paper-supported distribution simultaneously has a construction-time
witness and the claimed hardness, and because the only paper-native algorithmic
regime has no mechanical-versus-compact compression gap.

## Exact problem and parameter regimes

Definition 2 says that, for a bipartite graph with specified parts `(L,R)`, a set
`I` is `gamma`-balanced when it is independent and

`abs(|I intersect L| - gamma |I|) < 1`.

For `gamma = 1/2` and an answer of even size `2k`, this forces exactly `k`
vertices from each side.  This is slightly more precise than the triage phrase
"equal numbers": odd answers are allowed by the paper and differ by one between
the sides.  A generator could remove the ambiguity by requesting exactly `k` from
each side.

The native probability space is `G_bip(n,d)`: `|L|=|R|=n`, and each of the `n^2`
possible cross-edges is present independently with probability `d/n`, for fixed
large `d` and `n` tending to infinity.

- Theorem 8 proves that the largest balanced independent set has total density
  `(2 + o_d(1)) log(d)/d`.  Equivalently, it typically contains about
  `2 n log(d)/d` vertices from **each** side.
- Theorem 9 proves that local algorithms reach only
  `(1 + o_d(1)) log(d)/d` vertices per side.
- Theorem 10(2) rules out the paper's low-degree algorithms when both requested
  side sizes are at least `(1+epsilon) n log(d)/d`, with `d >= d0(epsilon)`,
  sufficiently large `n`, degree
  `D <= C1 n/(xi log n)`, and the theorem's exponentially small failure bound.
  This is a restricted-algorithm lower bound on the **unconditioned** random law,
  not a theorem about all polynomial-time algorithms.
- Proposition 11 and Theorem 10(1) give the easy side: select left vertices
  independently with probability `p`, then include every right vertex having no
  selected neighbor.  With `p=(1-epsilon)log(d)/d`, this is both 1-local and a
  degree-1 polynomial construction.  The paper explicitly leaves surpassing the
  `log(d)/d` per-side barrier by unrestricted efficient algorithms open in
  Section 1.3.

The introductory statement that maximum balanced independent set is NP-hard on
arbitrary bipartite graphs is worst-case background.  It does not establish
average-case hardness for any answer-first sampler.

## The certificate-producing question

For the hard unconditioned distribution, Theorem 8 does not output an
instance-specific set.  Section 4 proves the lower bound by defining balanced
`P`-independent sets and combining a second-moment bound (Lemma 26) with Azuma
concentration (Lemma 25).  These arguments show that a set exists with high
probability; they do not give the generator a set without performing the search
posed to the solver.

Fixing candidate parts `S_L,S_R` of size `k` before drawing an unconditioned graph
does not help.  Their exact probability of being independent is

`(1-d/n)^(k^2)`.

At the hard scale `k=(1+epsilon)n log(d)/d`, this is
`exp(-Theta(n log(d)^2/d))`, so rejection sampling needs exponentially many
trials in `n`.  Searching the completed graph for one of the many witnesses is
exactly the forbidden certificate search.

The triage proposal instead samples `S_L,S_R` first and independently samples all
edges except those in `S_L x S_R`.  This is valid inverse generation, and a
candidate answer is checked by two cardinality tests and `k^2` adjacency lookups.
But its law is a mixture of graphs conditioned on a hidden set being independent,
not `G_bip(n,d)`.  Relative to the unconditioned law, its likelihood is weighted by
the number of balanced independent `k`-sets in the graph.  The paper proves no
quiet-planting, contiguity, or distribution-transfer result that would let
Theorems 9 or 10 be applied to this mixture.  The Section 4 second-moment estimate
is used only to prove existence and does not establish such a transfer.

Consequently, declaring `TRACK = "A"` for the proposed module would turn a
restricted-algorithm theorem on one distribution into an unsupported hardness
claim about another.  A few failed heuristics or failed LLM calls could not repair
that missing theorem.

## Track B audit: mechanical cost and compact route

There are two native regimes to check.

| regime | mechanical route | compact route available from the instance | result |
|---|---|---|---|
| Below the barrier | Proposition 11: choose one side, inspect its cross-edges, and collect unblocked vertices on the other side; `Theta(n+number of inspected incidences)` | The same scan.  An ordinary random adjacency table exposes no symmetry, invariant, or change of variables that identifies the unblocked vertices without those inspections. | No compression gap; it tests bulk bookkeeping. |
| Above the barrier | General balanced-independent-set search; the paper gives no efficient unrestricted algorithm and proves only local/low-degree failure. | No short route is supplied; finding one would resolve the direction posed in Section 1.3. | Track B's required known efficient reference algorithm plus short insight route is absent. |

For a concrete scale below the answer cap, I measured the first route on 20
deterministic random trials with `n=2048`, `d=64`, and a fixed-by-symmetry set of
`k=80` left vertices.  The answer would contain 160 vertex indices.  Testing each
right vertex against the selected left set with early exit used a mean of
**60,320.25 adjacency probes** (range **58,723--62,113**) and **0.00411 seconds**
mean wall time; every trial exposed at least 139 unblocked right vertices.  The
compact route on the genuinely random table is the same approximately 60,320
probes, not a sub-300-operation structural calculation.  Mechanical and compact
costs therefore have ratio 1 under the same accounting.

An affine relabelling, modular marker, degree signature, or planted symmetry could
manufacture a short decoding trick.  None occurs in the paper's random model or
its proofs.  Adding one would make the benchmark about the added encoding, and it
would still require a new hardness analysis for the resulting planted
distribution.

## Other paper-native candidates

| candidate | G | H | V | outcome |
|---|---:|---:|---:|---|
| Find an above-threshold balanced set in genuine `G_bip(n,d)` | **fail** | supported only against local/low-degree algorithms | pass | Theorem 8 is existential; obtaining the witness requires search. |
| Find the inverse-planted `k+k` set | pass | **unsupported on Track A** | pass | Conditioning on the planted empty submatrix changes the theorem's distribution. |
| Run Proposition 11 and return a below-threshold balanced subset | pass as the theorem's direct construction | **fails Track A; no Track B compression** | pass | The method is explicitly 1-local/degree-1, and the same scan is the solver route. |
| Return a maximum balanced independent set | no construction-time optimum certificate | worst-case NP-hard only | **fail for optimality** | Feasibility of a set does not certify that no larger balanced set exists. |
| Certify that no requested set exists | no bounded certificate supplied | not reached | **fail** | The paper's moment/OGP arguments are distributional proofs, not executable refutations attached to one graph. |

## Gate outcome

| requirement | status | evidence |
|---|---:|---|
| G -- known certificate by construction | **Fails in the native hard law** | Theorem 8 uses moments and concentration; a fixed hard-scale set survives with exponentially small probability. |
| H -- Track A for the inverse plant | **Fails / unsupported** | Theorems 9 and 10 concern unconditioned `G_bip(n,d)`, not the conditioned planted mixture. |
| H -- Track B | **Fails for the constructive native regime** | The measured mechanical and compact routes are both the same roughly 60,320-probe scan; the hard regime has no known efficient reference algorithm. |
| V -- exact witness checking | Passes in isolation | Check distinct in-range indices, exactly `k` on each side, and absence of all `k^2` cross-edges. |
| overall | **Rejected at Step 0** | No paper-supported family clears G, H, and V simultaneously. |

Per the task instruction to stop after a Step 0 failure, no `gen_2307_13921.py`,
`selftest_report.json`, `README.md`, or oracle transcript was fabricated.
