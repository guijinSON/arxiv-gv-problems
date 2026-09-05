# Rejected: arXiv 2512.00695

Paper: [Kempe changes in H-free graphs](https://arxiv.org/abs/2512.00695), Manoj Belavadi and Kathie Cameron.

## Decision

No generator is shipped.  The paper gives clean routes through **G** and **V**, but
the paper-backed families fail **H on both tracks**.  This decision was made at
Step 0, before writing a module.

- **G is available.**  Section 3 explicitly constructs the graphs `D_q` and `Y_r`
  and their Kempe-frozen colourings `psi` and `zeta` (Lemma 6 and Lemma 8).  Theorem 8
  also carries a known Kempe-frozen colouring through Operation 1.
- **V is available.**  Given a proposed colouring, a checker can test properness
  and, for every pair of colours, run connectivity in the induced bichromatic
  graph.  Lemma 1 then certifies non-equivalence when a second colouring has a
  different partition.
- **H is not available.**  The same structure that constructs the witness exposes
  it by a linear-time local test, and the paper contains no hardness result for
  finding Kempe-reconfiguration sequences or Kempe-frozen colourings.

## Step-0 reading

Section 1 fixes the exact notions: a Kempe chain is one connected component of
the graph induced by two colour classes, and a Kempe swap exchanges those two
colours on that whole component.  Lemma 1 is the finite non-equivalence
certificate used throughout the paper.  Theorem 2 is a complete structural
classification: every `H`-free graph is Kempe connected exactly when `H` is an
induced subgraph of `P4`.  This classification is not a hard search family;
testing the positive side only concerns induced subgraphs of a four-vertex path.

The scalable objects are in Section 3.  Remark 1 says that when every colour
class has size two, a Kempe-frozen colouring of `G` is a perfect matching in
`F = complement(G)` for which at most one `F`-edge joins any two matched edges.
The displayed formulas immediately give `psi` for `D_q` and `zeta` for `Y_r`.
Theorem 8 is likewise constructive: each application adds two vertices and
states exactly how to extend the old colouring.

The paper does not state a computational-hardness theorem, an FPT lower bound,
or a hard parameter regime for finding a sequence between two colourings.  Its
only open question (Question 1) is structural Kempe connectedness for two
hereditary graph classes, not sequence-search complexity.

## Strongest candidate and measured attack

The best native candidate was:

> Given a randomly relabelled `Y_r` together with another proper colouring, find
> a Kempe-frozen `3r`-colouring whose colour classes certify a different Kempe
> class.

It has a theorem-backed planted witness and an exact checker.  It also has a
large superficial answer space: `complement(Y_r)` has `2^(r+1)` perfect
matchings (confirmed by exact enumeration for `r = 2,...,8`), while exactly one
is Kempe frozen.  At `r = 40` this is `2^41` candidates and a 240-atom answer.

Nevertheless, it is solved without search.  In `F = complement(Y_r)`, each
three-vertex block is a triangle.  A matched edge lying in a triangle cannot be
a class of a Kempe-frozen pair-colouring: the triangle's third vertex belongs
to another pair, leaving that vertex disconnected in the corresponding
bichromatic subgraph of `G`.  Conversely, in the paper's `Y_r` construction the
edges lying in no triangle are exactly the `3r` disjoint pairs of `zeta`.
Therefore the standard attack is simply:

1. build adjacency sets for the sparse complement;
2. test each complement edge for a common neighbour;
3. return all edges having no common neighbour.

This costs
`O(sum_(uv in E) min(deg(u),deg(v))) = O(|E|)` on the cubic `Y_r`
complements.  A direct measurement on 20 independently relabelled `Y_40`
instances (`|V| = 240`, `|E(F)| = 360`) recovered the planted colouring **20/20**.
The maximum counted cost was **1,570 adjacency insertions/membership tests** and
the median wall time was **0.000169 seconds** on this runner.

### Why Track A fails

The domain-standard, construction-aware algorithm succeeds on every generated
instance in linear time.  This is a distributional failure, not merely the
absence of a worst-case theorem.  Random relabelling does not help because
triangle incidence is invariant under relabelling.  The required Track A G6
entry would therefore report 20 successes in 20 attempts rather than zero.

### Why Track B also fails

The compact route is **the same route** as the mechanical algorithm: notice
triangle incidence and filter the edge list.  At `r = 40` it still inspects 360
edges and writes 120 pairs, at least about **480 elementary inspect/write
actions**, versus the measured 1,567 primitive operations for the full routine.
Both routes are linear, differ by less than a factor of four, and neither hides
a short invariant behind a million-operation mechanical computation.  There is
nothing to compress.

The symbolically labelled version is even easier: the formula in Section 3
writes the `3r` pairs of `zeta` directly in `3r` pair constructions.  The
compact route is the displayed formula itself, again the same length as the
mechanical route.  Repeated use of Theorem 8 has the same defect: the theorem
states the constant-work colouring update at every operation.

## Why the prior reconfiguration hypothesis is not used

Inverse-generating two colourings by first planting a hidden Kempe-swap sequence
would satisfy G, and replaying the sequence would satisfy V.  It would not
satisfy H.  This paper proves no hardness theorem for recovering such a sequence
and gives no parameter regime or generated distribution on which recovery is
hard.  Exponential breadth-first search over all colourings is not an efficient
reference algorithm, so it cannot support Track B either.  Merely hiding an
arbitrary planted sequence would turn the benchmark author's encoding into the
source of difficulty rather than test a result of this paper.

The paper's cited reference [4] does prove worst-case PSPACE-completeness of
Kempe Reachability for fixed `k >= 3` (even for three-coloured planar graphs of
maximum degree six), while giving a constructive polynomial algorithm and a
`2 n log n` diameter bound for the `P4`-free regime used by this paper's Theorem
1.  Neither result repairs the proposed generator: worst-case hardness says
nothing about the distribution of inverse-planted random walks, while the
paper-backed `P4`-free distribution is explicitly in the easy regime.

Thus the natural certificate families are explicit/local, while the suggested
sequence family has no paper-backed hardness basis.  Building either would
mislabel a readily recovered witness—or an unsupported planted puzzle—as a hard
family.
