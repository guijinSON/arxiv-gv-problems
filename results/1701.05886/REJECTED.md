# Rejected at STEP 0: arXiv 1701.05886

Paper: Didem Gözüpek, Ademir Hujdurović, and Martin Milanič,
[*Characterizations of minimal dominating sets and the well-dominated property
in lexicographic product graphs*](https://arxiv.org/abs/1701.05886), v4
(2017).

## Decision

No generator is shipped. The prior-triage proposal—inverse-generate a
lexicographic product with a planted minimal dominating set and ask for a
minimal dominating set—clears **G** and **V**, but fails **H on both tracks**.

For Track A, finding *some* minimal dominating set is unconditionally easy:
greedily construct any maximal independent set. Every maximal independent set
is a minimal dominating set. The paper also gives no average-case hardness
theorem for a planted distribution; it says that even the complexity of
recognizing well-dominated graphs in general is open.

For Track B, the efficient algorithm and the compact route are the same scan.
Because the instance is presented as the two factors `G,H`, a solver need not
expand `G[H]`: compute maximal independent sets `I` of `G` and `J` of `H` and
return `I × J`. This product is a maximal independent set, hence a minimal
dominating set, of `G[H]`. There is no million-operation mechanical route being
compressed into a short structural one.

Implementation stopped before STEP 1, as required when G, H, and V cannot hold
simultaneously. Consequently there is no `gen_1701_05886.py`, self-test report,
README, or oracle transcript.

## Exact definitions and results from the paper

Section 2 defines the lexicographic product `G[H]` on `V(G) × V(H)`: two
vertices `(g,h)` and `(g',h')` are adjacent when either `gg'` is an edge of `G`,
or `g=g'` and `hh'` is an edge of `H`.

Section 3, Proposition 3.2 gives the executable minimality certificate. A
dominating set `D` is minimal exactly when every `u in D` has a private closed
neighbor `x`, meaning `N[x] ∩ D = {u}`. Thus a candidate can be checked by
exact adjacency and set-intersection scans; no theorem oracle is needed.

The central product characterization is Theorem 4.3. It says that `D` is a
minimal dominating set of `G[H]` exactly when:

1. its projection to `G` is an irreducible dominating set;
2. each fiber is a singleton at a totally dominated projected vertex and a
   minimal dominating set of `H` at a barely dominated projected vertex; and
3. the stated redundant-vertex/leaf condition holds.

The sentence immediately preceding Theorem 4.3 says that this gives a
constructive way to obtain all minimal dominating sets. It does not make the
task of obtaining *one* such set hard.

Theorem 5.1 completely characterizes connected well-dominated nontrivial
products: either `G` is well-dominated and `H` is complete, or `G` is complete
and `H` is well-dominated with domination number two. Section 6 then identifies
an easy regime that a generator must not mistake for hardness. Corollary 6.3
recognizes well-dominated graphs with domination number two in polynomial time,
and Theorem 6.6 does so for every fixed domination number `k`, by hypergraph
transversal dualization. Section 7 explicitly leaves general well-dominated
recognition open.

## The certificate-producing algorithm

For an arbitrary graph represented by adjacency lists, the following greedy
algorithm produces a certificate, not merely a decision:

1. scan vertices in any order;
2. select a vertex if no already selected vertex is adjacent to it; and
3. mark it and its neighbors as unavailable.

The result is independent and maximal. Maximality makes it dominating, while
independence makes each selected vertex its own private closed neighbor.
Proposition 3.2 therefore verifies that it is a minimal dominating set. With
ordinary adjacency lists the cost is `O(|V|+|E|)`.

The factor representation makes the product no harder. If `I` and `J` are
maximal independent sets of `G` and `H`, then `I × J` is independent in
`G[H]`. For any `(g,h)` outside it, either `g` has a neighbor in `I`, which
dominates the whole `g`-fiber through a product edge, or `g in I` and `h` has a
neighbor in `J`. Hence `I × J` is maximal and is a valid minimal dominating
set. The cost is

`O(|V(G)|+|E(G)|+|V(H)|+|E(H)|+|I||J|)`,

including writing the answer.

This attack accepts a different witness from the plant, as a correct `verify`
function must. Planting and random relabeling therefore do not defend the
family.

## Mechanical cost versus compact route

I measured the factor-aware greedy algorithm on a concrete version of the
prior-triage distribution. Each factor had a uniformly relabeled planted
independent dominating set; every outside vertex was attached to two planted
vertices, and pairs of outside vertices received independent edges with
probability `1/2`. This is valid inverse generation. The attack ignored the
plant and greedily found another valid maximal independent set.

One counted operation was a vertex-state inspection, selection, mark, neighbor
mark, or emitted product pair. Times are standard-library Python wall times over
20 deterministic seeds.

| vertices in each factor | attack successes | mean / max operations | mean / max wall time | mean / max answer pairs |
|---:|---:|---:|---:|---:|
| 32 | 20/20 | 234.05 / 272 | 0.00000646 / 0.00000996 s | 20.05 / 30 |
| 128 | 20/20 | 1214.6 / 1332 | 0.0000274 / 0.0000374 s | 65.55 / 81 |

The **compact route has exactly the same operation counts**, because it is the
same two factor scans followed by the same Cartesian-product output. At the
32-by-32 scale both routes fit under the 300-operation no-tool cap. At the
128-by-128 scale both exceed it together. Their mechanical-to-compact ratio is
one at every size; increasing the product only creates work that a
product-aware standard algorithm never performs.

This is the required Track B comparison:

- **Mechanical cost at the plausible hand-scale preset:** at most 272 counted
  operations and 0.00000996 seconds.
- **Compact route:** the same at most 272 operations; there is no shorter
  invariant-based route.

Quoting the cost of first materializing every edge of `G[H]` would manufacture a
false compression gap. The solver is handed `G` and `H`, the paper is explicitly
about their product structure, and the standard domain-aware algorithm uses
that representation.

## Why the other native formulations do not rescue a family

| Candidate problem | G | H | V | Outcome |
|---|---:|---:|---:|---|
| Find any minimal dominating set of `G[H]` | Pass by inverse generation or maximal-independent-set construction | **Fails A and B** | Pass by Proposition 3.2 | Linear greedy succeeds on every instance; compact route is identical. |
| Find an irreducible dominating set | Pass, since every minimal dominating set is irreducible | **Fails A and B** | Pass by Proposition 3.2(ii) | The same greedy minimal dominating set is already a valid answer. |
| Decide whether a displayed dominating set is reducible | Pass | **Fails A and B** | Pass | Proposition 3.2 gives a direct local scan for the offending vertex/leaf condition. |
| Find a minimal dominating set of a prescribed unusual size | Possible to plant | Unsupported on Track A; no general efficient Track B reference algorithm is supplied | Pass | The paper gives no hard planted distribution or hardness regime. Forcing a size/mask is extra benchmark machinery, not a consequence of its theorems. |
| Output a largest minimal dominating set | No construction of scalable certified optima | Not reached | **Fails** | Section 7 leaves an expression for the upper domination number of a lexicographic product as an open question; a feasible set alone is not an optimality certificate. |
| Certify that a product is well-dominated | Positive certificate not supplied in bounded executable form for general factors | Not reached | **Fails in general** | Theorem 5.1 is a characterization, but `G` or `H` being well-dominated is itself universal; the checker cannot accept an appeal to the theorem as a witness. |
| Certify that a product is not well-dominated | Sometimes constructible as two unequal minimal dominating sets | No hard generated distribution is proved | Pass | In the explicit cases from Theorem 5.1's proof, the witnesses come from short maximal-independent-set and local-deletion constructions; other cases inherit the open general recognition problem and lack an efficient Track B reference. |
| Recognize well-dominated graphs with fixed domination number | Pass as a decision computation | **Fails Track A** | Executable | Theorem 6.6 explicitly gives a polynomial-time algorithm; its output is the disqualifying algorithm, not a hard witness family. |

A custom cryptographic labeling, exact-cardinality mask, or unrelated hard CSP
could hide one chosen minimal dominating set. That would make the wrapper, not
the paper's lexicographic-product characterization, carry the difficulty. The
paper licenses no such reduction, so it cannot establish native Track A
coverage, and it would not repair the missing mechanical/compact distinction
for the natural Track B task.

## Gate diagnosis

| Requirement | Result | Evidence |
|---|---:|---|
| G — generatable | Passes in isolation | Inverse-generate private neighbors, or construct factor maximal independent sets and take their product. |
| V — exact witness verification | Passes in isolation | Test domination and one private closed neighbor per selected vertex, exactly as in Proposition 3.2(i). |
| H — Track A | **Fails** | Any maximal independent set is a minimal dominating set and greedy construction is linear; the paper proves no hard planted distribution. |
| H — Track B | **Fails** | Mechanical and compact costs are 272 versus 272 operations at the plausible hand-scale preset; the greedy attack solved 20/20 measured instances. |
| G6 — adversary panel | **Fails analytically and empirically** | The domain-standard maximal-independent-set attack succeeds on every graph, hence cannot have zero successes. |
| Overall | **Rejected at STEP 0** | No paper-native family identified here makes G, H, and V hold simultaneously under either track. |

No G1–G9 report or LLM-oracle evidence was fabricated after the mandatory H
failure.
