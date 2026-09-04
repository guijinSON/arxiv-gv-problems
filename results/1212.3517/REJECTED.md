# Rejected: arXiv 1212.3517

Paper: Mikael Gast, Mathias Hauptmann, and Marek Karpinski,
[*Inapproximability of Dominating Set in Power Law Graphs*](https://arxiv.org/abs/1212.3517).

## Decision

No problem generator is shipped. The paper supports worst-case approximation hardness,
but it does not supply a hard **answer-first distribution**. The prior-triage proposal—plant
a dominating set and attach every remaining vertex to it—meets generation and exact
feasibility checking, but it is not the distribution in any hardness theorem in the paper
and it gives the plant a direct statistical/structural role. It therefore fails **H**, whose
test is explicitly distributional rather than worst-case.

The faithful alternative is also insufficient. Sections 5 and 6 compose Feige's promise
reduction with the paper's power-law embedding. A satisfying source assignment can be
carried through that construction to a set cover and then to a dominating set. To know such
an assignment without solving, however, the generator must sample a planted satisfiable
source formula. Theorems 1--4 do not establish hardness for that conditional/planted
distribution; their soundness concerns worst-case no-instances from the promise reduction.
Thus the theorem cannot be cited as evidence that generated instances are hard.

This is a Step 0 rejection. In accordance with the task, `gen_1212_3517.py`,
`selftest_report.json`, and hardening transcripts were deliberately not created. An oracle
run cannot repair a missing distributional hardness basis.

## What the paper actually defines

Section 1 defines a dominating set of an undirected graph `G = (V, E)` as a subset
`D` such that every vertex outside `D` has a neighbor in `D`; Minimum Dominating Set asks
for one of minimum cardinality. Section 1 also gives the exact Aiello--Chung--Lu degree
sequence: the maximum degree is `floor(exp(alpha / beta))`, and (apart from the stated
parity adjustment at degree one) the number of degree-`i` vertices is
`floor(exp(alpha) / i**beta)`.

The paper does not prove that arbitrary graphs with a planted dominating set are hard.
Its lower bounds use a specific chain:

1. Section 5 starts from Feige's `5OCC-MAX-E3SAT` promise construction and builds a Set
   Cover instance.
2. Section 5 turns that set system into the graph `G_(U,S)`, with vertices for elements and
   sets, incidence edges, and edges between intersecting sets. A set cover is a dominating
   set, and any dominating set can be converted to a set cover without increasing its size.
3. Section 4 and Algorithm 1 embed `G_(U,S)` in a power-law graph. The high-degree interval
   `X` dominates the residual wheel, while degree-two vertices connect the hard core to `X`.
4. Theorems 1--4 derive logarithmic inapproximability for `0 < beta <= 2` under the
   parameter choices and rescaling in Section 6.

For `beta > 2`, Section 7 instead gives polynomial-time approximation bounds based on the
standard greedy dominating-set algorithm. Lemma 4 decomposes an optimum into forced
neighbors of leaves, one endpoint from paired leaves, and an optimum solution on a residual
induced graph. Section 8, Theorem 5, likewise places the functional regime
`beta_f = 2 + 1/f(n)` in APX when `f(n) = o(log n)`.

## Step 0 certificate-cost test

| Candidate formulation | How its witness is produced | Cost | Outcome |
|---|---|---:|---|
| Find any dominating set of a declared size in the proposed planted graph | Sample `D`, then add an incident edge from every other vertex to `D` | `O(|V| + |E|)` generation and verification | G and V hold; H is unsupported and the planting mechanism is an attack surface absent from the paper's theorem. |
| Faithful yes-side image of Sections 5--6 | Sample a satisfying assignment, construct Feige's set cover, map its cover to `G_(U,S)`, then apply Algorithm 1 | Polynomial in the expanded output (with the large PCP/partition-system expansion described in Section 5) | G and V can hold; H does not follow for the planted satisfiable source distribution. |
| Output a minimum dominating set | A feasible set alone does not certify minimality | Not supplied by the paper | V fails unless an additional executable lower-bound certificate is included. |
| Output a certified optimum using private leaves or a matching lower bound | Build forced local gadgets around the chosen vertices | Linear | G and V hold, but the same local gadgets reveal an optimum and fail H. |
| Output the Section 7 greedy approximation for `beta > 2` | Run greedy after selecting the forced leaf-neighbor part | Polynomial | This is precisely an efficient algorithmic regime, so Track A is false; it offers no nontrivial compact route supporting Track B. |

The key distinction is that the reduction is a map from an already hard promise instance;
it is not an inverse sampler for hard yes-instances. Random relabelling of a single known
hard graph would not help: `canonical_key` must identify all such relabellings as the same
problem, so it cannot provide an unlimited diverse family.

## Why the prior-triage generator is not licensed by the hardness theorem

The suggestion “plant a dominating set, then attach remaining vertices to it” discards all
load-bearing parts of the paper's reduction: Feige's partition systems, the set-cover
incidence graph, the degree band from Lemma 1, the rescaling constraints in Section 6, and
the separating role of `Gamma` and `X` in Algorithm 1. Merely arranging for a power-law
degree histogram does not place an instance inside the hard distribution—indeed, the paper
contains no hard distribution at all.

In the naive construction, planted vertices receive all mandatory attachment incidences.
Degree ranking, closed-neighborhood coverage, greedy maximum uncovered-neighborhood, and
random-restart greedy are therefore construction-aware attacks that must be expected to
recover a small dominating set. Equalizing degrees would remove only the first signal; it
would create a new planted-dominating-set model whose average-case hardness still is not a
result of this paper. Retuning that model until a small attack panel or an LLM pool fails
would be empirical benchmark fitting, not the theorem-backed Track A claim required here.

## Track assessment

**Track A is unavailable.** Theorems 1--4 give worst-case gap inapproximability in the
specified `0 < beta <= 2` regimes. They do not claim that satisfiable Feige images, planted
dominating sets, ACL-random graphs, or any efficiently samplable yes-distribution are hard.
The prompt expressly forbids substituting worst-case NP-hardness for a distributional claim.

**Track B is also unavailable.** In the lower-bound regime the paper gives no efficient
algorithm for finding the hard-core dominating set, so there is no honest polynomial
reference algorithm to report. In the `beta > 2`/slow functional regimes, the paper's
efficient result is an approximation algorithm, not an exact optimum certificate, and the
obvious forced-leaf decomposition supplies the same kind of by-hand heuristic that Track B
requires to fail. No compact, paper-derived hidden route remains after accounting for the
mechanical algorithm.

## Gate outcome

| Requirement | Status | Evidence |
|---|---:|---|
| G — answer-first generation | Possible only for an artificial planted family or the planted yes-side of the reduction | The planted set/assignment is known before the graph is built. |
| H — hardness for the generated distribution | **Failed** | Theorems 1--4 are worst-case promise reductions, not average-case results for either planted distribution. The naive proposal additionally exposes the planted set through the edges added to certify it. |
| V — cheap exact checking | Passes for bounded feasibility; fails for an unaugmented optimum claim | Domination and cardinality are checked by a graph scan, but minimum cardinality is not. |
| Overall | **Rejected** | No paper-supported family clears G, H, and V simultaneously on either track. |

No G1--G9 measurements are reported because the mandatory Step 0 hardness gate failed
before a module existed.
