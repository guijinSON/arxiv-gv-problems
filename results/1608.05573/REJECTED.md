# Rejection: arXiv 1608.05573

Paper: Boštjan Brešar, Sandi Klavžar, Douglas F. Rall, and Kirsti Wash,
[*Packing chromatic number, (1,1,2,2)-colorings, and characterizing the Petersen graph*](https://arxiv.org/abs/1608.05573).

## Decision

No generator is shipped. The candidate family clears **G** and **V**, but fails
**H on both tracks**.

- **G is available:** one can inverse-generate a graph together with an
  `(1,1,2,2)`-coloring and add only edges that preserve the four packing classes.
  The paper also gives theorem-backed constructions for generalized prisms and
  uniformly subdivided graphs.
- **V is available:** for a proposed four-class assignment, breadth-first search
  to depth 1 for the first two classes and depth 2 for the last two classes checks
  the witness exactly in polynomial time.
- **H fails:** the paper's native theorem-backed distributions have direct
  linear-time certificate constructions, while the proposed inverse-planted
  distribution has no theorem or evidence establishing average/distributional
  hardness. Worst-case hardness of S-packing coloring does not repair that gap.

This is not a rejection merely because an efficient algorithm exists. The
mechanical and compact costs were compared below, as required for a possible
Track B family.

## Exact definition and the results that decide the issue

Section 2 defines an `i`-packing as a vertex set whose distinct vertices have
graph distance strictly greater than `i`. An `(1,1,2,2)`-coloring partitions all
vertices into two independent sets and two sets whose pairwise distances are
strictly greater than 2. Lemma 2.4 gives an executable equivalent certificate:
partition `V(G)` into `V1,V2,V3`, require `V2` and `V3` to be independent, and
2-color `G^2[V1]`.

The results that make the natural generated regimes easy are:

| Result | Regime | How the certificate is produced |
|---|---|---|
| Proposition 2.1 | `G` connected bipartite, at least three vertices | `chi_rho(S(G)) = 3` |
| Proposition 2.3 | `G` is `(1,1,2,2)`-colorable | Converts that coloring to a 5-packing coloring of `S(G)` |
| Theorem 3.2 | Generalized prism of a cycle, except the Petersen graph | Explicit parity-and-case construction of the four classes |
| Corollary 3.3 | Subdivision of every generalized prism, including Petersen | Explicit 5-packing-colorability certificate |
| Theorem 4.1 | The stated cubic 2-factor/perfect-matching class, with at most one 5-cycle off the long cycle | Explicit cycle-by-cycle construction |
| Proposition 5.1 | `S_i(K_n)`, `n >= 3`, `i >= 3` | A displayed periodic word gives the optimal 3- or 4-packing coloring |
| Corollary 5.2 | `S_i(G)` for every connected `G` of order at least 3 and `i >= 3` | Restriction of the complete-graph construction; the value lies between 3 and 4 |
| Theorem 5.3 | Uniform subdivisions of trees | Explicit BFS-level or periodic-path coloring |

The Petersen exception does not supply a hard scalable family: it is one fixed
10-vertex graph, and Figure 4 explicitly displays a 5-packing coloring of its
subdivision. Proposition 3.4 only states a necessary feature of such a coloring.

The apparently harder `S_2(K_n)` case in Proposition 5.1 supplies only a growing
lower bound, not an exact optimum with a finite optimality witness. It therefore
does not give a scalable G+V family for the optimization question.

## Track A audit

Theorem 3.2 and Theorem 4.1 are existence theorems with constructive proofs, not
hardness theorems. Their proof procedures inspect the cycles and matching a
constant number of times, so certificate production is `O(|V|+|E|)` on those
families. Proposition 5.1 and Theorem 5.3 are more explicit still.

The paper cites Gastineau's worst-case complexity dichotomy, but does not give or
analyze a hard distribution for the inverse-planted graphs proposed in the prior
triage. In particular, adding only coloring-preserving edges says nothing about
the number of alternative colorings, phase-transition placement, or the cost of
DPLL/CP-SAT on the resulting distribution. Claiming Track A from worst-case
NP-completeness would violate the task's distributional-hardness requirement.

**Track A failure:** no theorem in this paper names a hard parameter regime for
the distribution that can be generated with a known witness.

## Track B audit: mechanical cost versus compact route

The strongest plausible Track B candidate is Theorem 3.2 on a generalized prism.
For the even-cycle branch with 128 vertices on each cycle (the largest full
color-vector witness allowed by the 256-atom cap), an instrumented direct
implementation of lines 300--311 of the source proof produced and independently
verified a certificate. It used **832 counted primitive assignments, parity tests,
and table accesses**, and averaged **48.278 microseconds per certificate** over
20,000 CPython runs. The answer itself has **256 atomic color entries**.

The compact route is not shorter: it is precisely the same parity construction,
and merely writing its required witness costs **256 atomic writes**. Thus the
comparison at the maximum writable setting is:

| Route | Cost |
|---|---:|
| Paper's mechanical certificate construction | 832 primitive operations; 48.278 microseconds measured |
| Compact/by-hand route after noticing the parity structure | at least 256 writes, plus the same per-vertex classifications |

This is a constant-factor implementation difference, not a mechanical-versus-
insight compression gap. It also exceeds the intended spirit of the 300-operation
cap as soon as the non-output classifications are counted.

The uniformly subdivided complete-graph alternative fares no better. Proposition
5.1 produces its certificate by one reduction modulo 4, at most two branches, one
integer division, and emission of a four- or five-symbol prefix/block: **at most
12 elementary operations in compressed form**. A solver's compact route is that
same displayed periodic formula: **at most 12 operations**. If the full coloring
is required, both routes instead take `Theta(i n^2)` writes and rapidly breach the
answer cap. Compressing the word therefore compresses the mechanical algorithm
and the human route equally; it does not create Track B hardness.

**Track B failure:** in every theorem-backed candidate, the shortest mechanical
certificate producer and the intended compact route have the same asymptotic and
essentially the same concrete cost. There is no hidden invariant whose discovery
replaces a large executable computation.

## Why the prior planting proposal is not retained

Planting a valid packing coloring and adding preserving edges is a valid inverse
generator and has an exact checker. It nevertheless has neither:

1. a theorem establishing hardness for that planted distribution (Track A), nor
2. an exposed, paper-native compact route by which a no-tool solver can recover
   the hidden planting (Track B).

Adding an artificial label code or a separate hard reduction would make the
search about that added surrogate rather than about the generalized prisms,
subdivisions, and packing-coloring constructions studied here. No such reduction
is central to this paper.

Accordingly, writing a module and running the oracle loop would only test a
builder-invented distribution whose required H claim is already unsupported at
Step 0.
