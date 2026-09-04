# Rejected at Step 0: planting an alignment does not inherit robust-GISO hardness

Paper: Ryan O'Donnell, John Wright, Chenggang Wu, and Yuan Zhou,
[*Hardness of Robust Graph Isomorphism, Lasserre Gaps, and Asymmetry of
Random Graphs*](https://arxiv.org/abs/1401.2436), arXiv:1401.2436.

## Decision

No generator is shipped. The prior-triage proposal—generate a graph, secretly
permute its vertices, optionally perturb some edges, and ask for a sufficiently
edge-preserving bijection—passes **G (inverse generation)** and **V (exact
verification)**. It does not pass **H**.

The paper proves a conditional hardness statement for the *general promise
problem* ROBUSTGISO through a specific reduction from Feige's random-3XOR
hypothesis. It does not prove that an answer-first distribution of permuted
graphs is hard. For the most natural version of the proposal, where the base
graph and edge noise are random, this is not merely an absent theorem: random
and correlated-random graphs are algorithmically favorable matching regimes.
The paper itself says in Section 1.1 that basic Weisfeiler--Lehman refinement
works on almost all dense Erdős--Rényi graphs. Later work gives polynomial-time
exact recovery for correlated Erdős--Rényi pairs with constant correlation in
specified sparse regimes.

The reduction's soundness side cannot rescue the construction. Those random
3XOR instances are useful because, with high probability, they have no highly
satisfying assignment and the resulting graph pairs have no sufficiently good
alignment. The paper supplies no bounded, cheaply executable certificate of
that universal negative claim for each sampled instance. Obtaining one would
require solving or certifying the hard side that the generator is forbidden to
solve.

Track B is also not an honest fit. The available successful routes—color
refinement/random-graph matching for the prior proposal, Gaussian elimination
for noiseless 3XOR, or a general graph-matching routine—process the whole
instance. The paper supplies no separate compact, at-most-300-operation route
to the hidden random permutation. Making the permutation come from a tiny
affine or pseudorandom family would create a new leakage-based puzzle, not a
family justified by this paper.

Per the task's Step 0 instruction, I stopped before writing
`gen_1401_2436.py`, inventing G1--G9 measurements, or running the oracle loop.

## The exact native problem

Section 2 defines, for equal-order undirected graphs (or hypergraphs) `G` and
`H` and a bijection `pi : V(G) -> V(H)`,

```text
GI(G,H;pi) = |{e in E(G) : pi(e) in E(H)}|
             / max(|E(G)|, |E(H)|).
```

The bijection is an `alpha`-isomorphism when this ratio is at least `alpha`.
ROBUSTGISO asks for a function `r(epsilon) -> 0` and an algorithm that, on
*every* pair promised to be `(1-epsilon)`-isomorphic, outputs a
`(1-r(epsilon))`-isomorphism. Thus a valid positive witness is a complete
vertex bijection, checked by testing bijectivity and recounting preserved edges.

The paper's actual reduction in Section 3 starts with a 3XOR system `C` and
forms `(G_C, G_hom(C))`. Each Boolean variable contributes two shared variable
vertices; each 3XOR constraint contributes four constraint vertices forming a
clique and joined to the consistent variable vertices. If `C` has `n`
variables and `m` constraints, each graph has

```text
N = 4m + 2n vertices,
M = 18m + n edges.
```

This is the paper-licensed route from 3XOR to graph isomorphism. An arbitrary
random graph followed by permutation and edge flips is not the image of this
reduction.

## Step-0 discriminator: what produces the certificate?

### 1. The proposed random-permutation construction

The generator samples `pi` first, applies it to `G`, and edits the permitted
number of edges. Certificate production costs `O(|V|+|E|)` and exact
verification has the same order of cost. This establishes G and V only.

It supplies no Track A hardness basis. Section 1.1 explicitly identifies almost
all `G(n,1/2)` graphs as an easy regime for Weisfeiler--Lehman. For the noisy
random analogue, Mao--Rudelson--Tikhomirov,
[*Exact Matching of Random Graphs with Constant
Correlation*](https://arxiv.org/abs/2110.05000), prove polynomial-time exact
recovery with high probability when

```text
(1+eta) log n <= np <= n^(1/(R log log n))
```

and the edge disagreement parameter is a sufficiently small constant. Their
final refinement stage has expected `n^(2+o(1))` time. Other density/noise
choices are not automatically hard; they are simply outside that particular
theorem and still lack a hardness result for this generator's distribution.

### 2. Plant a nearly satisfying 3XOR assignment, then use Section 3

This is closer to the paper. Sample an assignment `tau`, sample constraints
that `tau` satisfies except for an allowed noise fraction, and apply the gadget
reduction. Lemma 4.1 (Completeness) writes the graph witness down directly:

- map each variable vertex `x_j -> b` to `x_j -> b + tau(x_j)`;
- translate the four constraint vertices coordinatewise when the constraint is
  satisfied; and
- choose an arbitrary within-gadget bijection on violated constraints.

The proof constructs this mapping in linear time in the emitted graph and
guarantees overlap at least `1 - 2 epsilon/3`. This is a valid theorem-backed
certificate, but it still does not establish H. Theorem 1.2 says that an
algorithm working on *all* promised near-isomorphic inputs would contradict
the R3XOR hypothesis. It does not say that the inverse-planted positive
distribution above is hard, and the prompt expressly forbids replacing
distributional hardness with worst-case promise hardness.

The distinction is especially important here. Section 1.2 notes that
satisfiable 3XOR is solved by Gaussian elimination; noise is what removes that
algebraic route. Once the generator chooses how to plant that noise, its own
distribution needs an attack analysis and a hardness basis. Neither Theorem
1.2 nor Feige's one-sided random-refutation hypothesis supplies one for this
positive sampler.

### 3. Sample the theorem's soundness-side random 3XOR instances

Lemma 5.1 proves that for a random 3XOR instance with `m = cn` and sufficiently
large constant `c`, the two gadget graphs are, with high probability, not even
`(1 - 1/(95c^2))`-isomorphic. This side carries the conditional hardness, but
it loses G and V for the requested witness task:

- the conclusion is only high probability, not a per-seed construction with a
  held certificate;
- the claim quantifies over every vertex permutation; and
- the paper gives no Farkas, Nullstellensatz, bounded refutation, or other
  finite certificate that cheaply proves the required nonexistence for an
  emitted pair.

Brute-forcing the optimum alignment to certify the negative is exactly the
forbidden act of solving the generated instance.

### 4. Use the SOS/Lasserre gap itself as the answer

Theorem 1.1 concerns nonisomorphic pairs for which SOS needs degree
`Omega(n)` to refute isomorphism. It is a lower bound against a proof system,
not a short witness generator. A degree-`r` pseudoexpectation consists of
moments for all relevant monomials and a positive-semidefinite moment matrix;
at `r = Omega(n)` its explicit representation is exponential and cannot meet
G9's 2,000-character/256-atom cap. At fixed degree it can be sought by the SDP
defining the hierarchy, which is an efficient reference algorithm and hence
cannot support Track A. The paper also invokes Schoenebeck's high-probability
existence theorem rather than giving a compact exact pseudoexpectation that a
module can emit and verify for every seed.

## The stated hardness regime is not a shippable witness regime

The quantitative soundness proof sets `c >= 10^10` (Section 5) and uses random
simple 3-uniform hypergraphs with `m = cn`; the robust-asymmetry theorem for
3-uniform hypergraphs also states `kappa_3 = 10^4` and an asymptotic range for
`c`. Even ignoring those enormous constants, the witness for the native graph
problem has one image for each of `N = 4m+2n` vertices. It therefore has `N`
atomic elements and exceeds G9's 256-element cap as soon as a graph has more
than 256 vertices.

At the paper's displayed constants the mismatch is overwhelming: just
`N = 4cn+2n` is greater than `4 * 10^10 * n`. Replacing the full bijection by
the underlying `n`-bit 3XOR assignment changes the requested certificate
language and still does not fix the missing distributional-hardness theorem.
Lowering `c` to a practical empirical value leaves the generator outside the
only parameter regime the paper proves.

There is also a numerical inconsistency worth flagging rather than silently
choosing around: the final sentence of Section 1 says to choose `c = 10^6` for
Theorem 1.1, whereas Lemma 5.1 and its proof state `c >= 10^10`. This does not
affect the rejection—the positive planted distribution is unsupported at any
`c`, and either constant makes the native graph witness far too large—but it
prevents using the displayed constants as a clean shipping prescription.

## Easy regimes and attacks that a valid successor would need to confront

- **Dense random graphs:** Section 1.1 says basic Weisfeiler--Lehman works on
  almost all `G(n,1/2)` graphs.
- **Trees:** Section 1.2 cites an efficient robust-isomorphism algorithm for
  trees.
- **Dense approximate matching:** Section 1.2 cites an additive PTAS when
  `m = Omega(n^2)`.
- **Noiseless 3XOR:** Gaussian elimination recovers a satisfying assignment.
- **Correlated random pairs:** partition-tree signatures and refinement give
  polynomial-time exact matching in the regime quoted above; spectral and
  degree/profile methods are mandatory attacks outside it as well.
- **Paper gadget pairs:** a serious panel would additionally need gadget
  recognition, hypergraph alignment, Gaussian elimination/decoding, basic and
  higher-dimensional WL, and a graph-isomorphism implementation. None can be
  omitted in favor of four generic planting probes.

## Why neither track can be declared

| Track | Result | Reason |
|---|---|---|
| A — structural hardness | **Fails** | Theorem 1.2 is conditional worst-case promise hardness. It does not cover the answer-first positive distribution, while the natural random-graph version has efficient recovery regimes. The soundness distribution has no executable per-instance negative certificate. |
| B — no-tool compression | **Fails** | The paper gives no compact route to a random hidden permutation distinct from processing the graph or solving the encoded system. A full graph bijection also violates the output cap in any meaningful regime. Restricting the permutation to a tiny structured family would be a new puzzle and an obvious planting target. |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known by construction | Would pass for a planted bijection or planted near-satisfying 3XOR assignment | Direct inverse generation; Lemma 4.1 carries `tau` to a graph mapping. |
| H — hard for the generated distribution | **Fails / unsupported** | Theorem 1.2 does not cover the planted positive distribution; the ordinary random/correlated-random proposal has efficient matching regimes. |
| V — exact witness checking | Would pass for a positive bijection | Check a permutation and recount preserved edges using integers. |
| Certified negative alternative | **Fails G/V** | No bounded executable certificate is supplied for the universal nonalignment claim. |
| SOS alternative | **Fails G9 or H** | Linear-degree moment data are exponentially large; fixed-degree feasibility is an SDP. |
| Steps 1--4 | Not run | Step 0 requires stopping once no family satisfies G, H, and V simultaneously. |

The decisive failure is H for every generatable positive family supported by
the paper, and G/V for the soundness-side family where its conditional hardness
actually lives. An oracle failure on a hand-sized planted graph would not repair
that mismatch, so no module or hardening evidence was fabricated.
