# Rejected: no hardness gap after optimal line-graph reconstruction

This paper is rejected for this generator, not because generation or verification
failed, and not merely because an algorithm exists. The candidate clears G and V:
it composes a known Euler circuit in an even-degree bipartite root graph, maps root
edges to vertices of its line graph, carries the Euler order into a Hamiltonian
cycle, and checks any submitted cycle by exact edge membership. The retained
module and `selftest_report.json` record 0/200,000 structure-aware guesses, five
attacks at 0/8, and all correctness gates passing.

## The paper results used

[Wahlstrom's paper](https://arxiv.org/abs/1301.1517) defines a K-cycle in
Section 3, Definition 1 as a simple cycle through every terminal, with additional
vertices allowed. Section 1 observes that K=V is Hamiltonian Cycle and hence
NP-hard. Lemma 3 notes that the one-terminal case is polynomial-time. Section
3.3, Theorem 2 gives a randomized O*(2^|K|) determinant-sum decision algorithm;
Theorem 3 gives an O(|K|^3)-bit randomized compression but explicitly does not
provide a small NP witness. Those general results do not imply hardness for the
line-graph distribution generated here.

## Which gate fails

**H fails on both tracks.** Track A is unavailable because every emitted instance
is recognizably a line graph of an even-degree connected root graph, so a
polynomial algorithm recovers a witness on the whole generated distribution.

Track B also fails after using the strongest relevant algorithm. Philippe Lehot's
1974 paper, [*An Optimal Algorithm to Detect a Line Graph and Output Its Root
Graph*](https://doi.org/10.1145/321850.321853), gives an optimal `E + O(N)`-step
algorithm that both recognizes a line graph and outputs its root. Hierholzer then
finds the root's Euler circuit in linear time, and that edge order is the requested
Hamiltonian cycle.

At the would-be shipping preset the displayed line graph has `N=64` vertices and
`E=160` edges; the recovered root has 40 vertices and 64 edges. Thus the mechanical
route scans about `64+160 + 40+64 = 328` graph items, up to constant bookkeeping.
The claimed compact route in G9 was measured at 224 incidence/traversal operations.
They are the same linear reconstruction-and-traversal idea and differ by only about
1.46x. There is no million-versus-dozen or even qualitatively different route to
test.

The retained module's 266,848-operation, 0.0065-second reference was a deliberately
dense O(N^3) clique reconstruction. It is not an honest hardness baseline once the
optimal linear algorithm is known. The bare oracle happened to hold the medium
preset at 0/3, but two replies merely omitted a vertex from a 64-element answer and
the third exhausted its output budget; that result cannot repair the failed H gate.
The diagnostic structural arm solved 2/3 and the placebo arm 1/3.

The mechanical cost (about 328 graph-item visits) and compact route (224 operations)
are therefore comparable. This family tests transcription and implementation of a
known linear line-graph duality, not no-tool compression. It must not ship.
