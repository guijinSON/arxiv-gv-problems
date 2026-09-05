# Rejected: arXiv:2101.12205

Paper: Simón Piga and Nicolás Sanhueza-Matamala, [“Cycle decompositions in
3-uniform hypergraphs”](https://arxiv.org/abs/2101.12205), arXiv:2101.12205v2.

## Decision

No generator is shipped.  The natural inverse-generated family passes **G** and
**V**, but fails **H on both tracks**.  This is not a G9(b) rejection and it is
not a claim that an algorithm merely exists: the mechanical and compact costs
are quantified below.

The paper proves an extremal existence threshold, not computational hardness.
Theorem 1.1 applies when the requested tight-cycle length is divisible by 3 and
at least 9, or is at least $10^7$, and the host 3-graph has asymptotic minimum
codegree above $2n/3$ together with the divisibility conditions.  Neither that
theorem nor any other result in the paper gives distributional hardness for
recovering a decomposition.  It therefore cannot support Track A.

## Candidate 1: plant tight cycles and take their edge-disjoint union

Section 1.1 fixes the exact object: a length-ℓ tight cycle has the ℓ triples
of consecutive vertices in a cyclic ordering.  Sampling the cyclic orderings
first and publishing the union is valid inverse generation, and a checker can
exactly verify that the submitted orderings induce distinct triples and
partition the input edge set.

The clean version of this construction is algorithmically transparent.  For
ℓ at least 7, index every hyperedge by its three unordered vertex pairs.
Within a vertex-disjoint planted tight cycle, precisely the consecutive
hyperedges share a pair, so the overlap graph on hyperedges is itself a cycle.
Traversing its connected components recovers the complete witness.

I measured the largest $C^3_9$ instance that fits the 256-atom answer cap:
28 cycles, 252 hyperedges, and 252 submitted vertex entries.  Building the pair
index took 756 pair insertions and traversal took 252 steps, for **1,008 primary
operations**.  Across 100 shuffled seeds, standard-library Python averaged
**0.000357 seconds** (maximum 0.010080 seconds).  It succeeded on every seed.

The compact route after noticing pair overlaps is exactly the same 756
insertions plus 252 traversal steps: **1,008 operations**, not a shorter
by-hand route.  Thus the mechanical cost and compact route have ratio 1, and
there is nothing Track B can test.  Reducing the instance only makes both
numbers smaller.  Increasing the number or length of cycles increases the
answer itself and reaches the output cap rather than creating a useful gap.

Allowing planted cycles to overlap on vertices or pairs can turn reconstruction
into an exact-cover search, but the paper proves no hardness for that generated
distribution.  More importantly, a random hidden decomposition supplies no
compact invariant or symmetry: the intended route is the same search as the
mechanical route.  Such a variant fails Track A for lack of a distributional
hardness result and Track B for lack of compression.

## Candidate 2: certify the Section 2 counterexample

Lemma 2.1 is an excellent finite negative certificate.  For a partition
$(U_0,U_1,U_2)$ with no edge meeting all three parts, every tour has

\[
 |W[U_1,U_1,U_2]|\equiv |W[U_1,U_2,U_2]|\pmod 3.
\]

This can be checked as a bounded telescoping refutation, not merely trusted as a
theorem: on ordered colour pairs use the potential
φ(1,2)=1, φ(2,1)=2, and φ=0 otherwise.  For every allowed ordered colour
triple $(a,b,c)$, the contribution of a 112 edge minus that of a 122 edge is
φ(b,c)−φ(a,b) modulo 3.  A closed tour telescopes to zero.  An input whose
global two counts differ modulo 3 therefore has no tour decomposition.

Definition 2.2 and Theorem 1.4, however, explicitly construct the three parts
with sizes $6k,6k-2,6k+2$, remove the displayed perfect matching of Lemma 2.5,
and add a displayed cycle.  When the paper's native labels are retained, the
certificate-producing algorithm is direct evaluation: copy one class label per
vertex and the fixed nine-entry potential.  At the largest atom-safe value
$n=234$, this is **243 atomic entries** plus 21 local identity checks, or
**264 elementary output/check actions**.  The compact route has the same 264
actions.  Again the routes are the same length.

The regular variant in the remark after Theorem 1.4 removes the degree signal,
but hiding the displayed partition under an arbitrary relabelling does not
create Track B structure.  At $n=234$ that regular counterexample contains
**1,405,638 hyperedges**.  Recovering the parts from a materialised incidence
table requires scanning or clustering that table; there is no paper-provided
sub-300-operation shortcut.  Encoding the hidden parts into artificial vertex
tags would create a tag-decoding puzzle, not native coverage of this paper.

## Full-paper checks

- Section 3 obtains the auxiliary cycle used for Corollary 1.2 greedily.
- Section 7.2 says that, when ℓ is divisible by 3, an approximate packing is
  obtained by greedily removing copies until only $o(n^3)$ edges remain.
- Sections 4–8 prove Theorem 1.1 by iterative absorption: a vortex, absorbers for
  every bounded remainder, random extensions, a cover-down argument, and tour
  transformers.  This is an asymptotic existence proof; executing its choices
  to obtain the submitted decomposition would be solving the generated host,
  not knowing the certificate by construction.
- Section 9 identifies the uncovered short-cycle range and open threshold
  questions, but gives no computational hardness regime.

Consequently the prior triage hypothesis is only half right: cycle unions are
generatable and exactly verifiable, but the natural distribution is immediately
reconstructible, while overlapped variants have neither a theorem-backed Track
A claim nor a distinct compact Track B route.  The paper therefore fails **H**
for this benchmark, and no module, self-test report, or oracle transcripts were
created.
