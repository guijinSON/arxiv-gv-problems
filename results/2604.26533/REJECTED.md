# Rejected at Step 0: arXiv 2604.26533

Paper: Malory Marin and Rémi Watrigant, [*Small Independent Sets versus
Small Separator in Geometric Intersection Graphs*](https://arxiv.org/abs/2604.26533)
(2026).

## Decision

No generator is shipped. The paper has three natural witness tasks, but none
supports all of G, H, and V under either track:

- the separator constructed by Theorem 1 is found by the proof's own linear
  histogram scan, and the scan is already the shortest route on an arbitrary
  explicit representation;
- the hard 2-Subcoloring and Two Sets Cut-Uncut instances in Theorems 17 and 19
  are reductions from **worst-case** monotone NAE-3-SAT, not an answer-first
  hard distribution; and
- asking for an *optimal* alpha-modulator would restore search hardness, but
  the paper supplies neither a cheaply checkable optimality certificate nor a
  theorem-backed way to generate one without solving Maximum Independent Set.

Thus the separator family fails **H on Track A and Track B**. The two target
problem families have worst-case lower bounds, but the obvious inverse-planted
distribution fails **H on Track A/G6**, while an arbitrary hard satisfiable
source does not satisfy **G**. There is no short solver-side route that could
turn those reductions into Track B without adding an artificial encoding not
present in the paper.

Implementation stopped before Step 1, as required. There is no generator,
self-test report, or oracle transcript to preserve.

## What the paper actually defines

Section 1 defines similarly sized beta-fat objects in `R^d`, their intersection
graph, and the following problems.

- A 2-subcoloring is a partition `(A,B)` of all vertices such that both induced
  graphs are disjoint unions of cliques. Equivalently, no induced three-vertex
  path is monochromatic. A proposed coloring is therefore an exact, cheap
  witness: scan all induced `P3`s.
- Two Sets Cut-Uncut asks for a minimum-weight partition `(A,B)` with the two
  prescribed terminal sets on opposite sides and connected on their respective
  sides. A feasible partition is easy to check, but optimality additionally
  needs a lower-bound certificate. The paper's lower-bound construction uses
  nonnegative weights and targets value zero, so a zero-weight feasible cut
  would certify optimality.
- Section 3 defines the alpha-modulator number as the minimum `k` for which a
  set `S` of at most `k` vertices leaves components of independence number at
  most `k`.

Theorem 1 gives, for fixed `d >= 2` and `beta >= 1`, a set `S` of size at most
`d n^(1-1/(d+1))` whose deletion leaves every component with independence
number at most `(2 beta d)^d n^(1-1/(d+1))`. The proof partitions every
coordinate into slabs indexed modulo

`p = ceil(n^(1/(d+1)))`

and, independently in each coordinate, selects a residue class containing at
most `n/p` object centers. The union of those classes is `S`. The theorem
explicitly says that this set is polynomial-time computable when the geometric
representation is supplied.

Section 4 gives the positive algorithms. With a corresponding modulator,
2-Subcoloring takes `2^O(k) n^O(1)` time (Theorem 11), yielding Theorem 12's
`2^O(n^(1-1/(d+1)))` geometric algorithm. Theorem 15 gives
`n^O(alpha-mod(G))` for Two Sets Cut-Uncut, and Theorem 16 specializes it to
`2^O(n^(1-1/(d+1)) log n)` on the geometric class. These are genuine
algorithms and cannot be hidden in a Track A claim.

Section 5 is a lower-bound framework, not a generator. Theorems 17 and 19 reduce
monotone NAE-3-SAT with exactly four occurrences per variable to the two target
problems. The resulting graph has `O(d^2 n^((d+1)/d))` vertices and is an
intersection graph of similarly sized fat objects for `d=2`, or a unit-ball
graph for `d>=3`. Under ETH the target problems cannot be solved in
`2^o(N^(1-1/(d+1)))` time. The theorem is a worst-case statement; it says
nothing about the distribution obtained by first sampling a truth assignment
and then conditioning random clauses on it.

The conclusion also identifies regimes the lower bound does **not** settle:
unit disk graphs in dimension two, and unweighted Two Sets Cut-Uncut, remain
open. Theorem 1 itself is not robust without the geometric representation.

## Why the separator does not give Track B

The certificate-producing algorithm is literally Claims 1--3 of the proof of
Theorem 1: make `d` histograms of the center coordinates modulo `p`, take a
minimum bucket in each, and output their union. On arbitrary explicitly listed
centers, every correct method must at least inspect the input coordinates; the
paper provides no invariant or change of variables that avoids this scan.

I measured the proof algorithm in standard-library Python on 20 deterministic
sets of integer center coordinates. The operation count below counts one
coordinate-to-bucket classification per center and dimension; finding the
minimum adds only `d*p` comparisons.

| objects `n` | `d` | `p` | classification updates | median / maximum wall time |
|---:|---:|---:|---:|---:|
| 1,448 | 2 | 12 | 2,896 | 0.000266 / 0.000283 s |
| 10,000 | 2 | 22 | 20,000 | 0.001850 / 0.002537 s |
| 100,000 | 2 | 47 | 200,000 | 0.019107 / 0.019767 s |

At `n=1,448`, the theorem's worst-case explicit separator already reaches the
256-atom output cap (`2*n^(2/3)` is about 256). The **mechanical cost** at that
plausible shipping boundary is 2,896 bucket updates plus 24 minimum
comparisons. The **compact route length is the same 2,920 operations**: it is
the histogram scan, and arbitrary input centers offer no shorter route. The
mechanical/compact ratio is therefore 1.

One could instead output only the `d` slab residues and let the checker expand
them, permitting much larger `n`. That does not create compression: at
`n=100,000` the mechanical route and the by-hand route are both the same
200,094-operation scan. Giving the centers through a specially designed
succinct formula with a hidden shortcut would create a new no-tool arithmetic
puzzle, not a family justified by this paper. It would also compile away the
geometric intersection structure before verification.

There is a second verification problem with interpreting `S` as an
alpha-modulator witness. Checking `|S|` and deleting it is easy, but checking
`alpha(G[C]) <= k` for every remaining component is not cheap. The volume
argument in Claim 3 is a proof, not a finite certificate supplied with an
arbitrary candidate. A checker-executable clique cover could certify the upper
bound, but Theorem 1 neither constructs such covers nor keeps their serialized
size within the witness cap. Restricting the requested witness to the low-count
slab residues fixes V, but leaves the histogram algorithm above and hence
still fails H.

## Why the lower-bound reduction does not give an answer-first hard family

The faithful way to carry a certificate through Section 5 would be:

1. generate a satisfiable four-occurrence monotone NAE-3-SAT instance together
   with its assignment;
2. apply the paper's grid, BFS-tree, clique, propagation, and clause gadgets;
   and
3. carry the assignment to the full 2-subcoloring or the zero-weight connected
   cut exactly as the proofs of Theorems 17 and 19 do.

This passes G and V **only if** Step 1 does not solve the formula. The theorem
does not provide such a generator. Sampling a random regular formula around a
planted assignment is not covered by the ETH reduction: worst-case NP/ETH
hardness does not establish average-case hardness of that distribution.

I tested the most direct construction rather than assuming cardinality implied
difficulty. For balanced planted assignments and `n` divisible by six, I made
four stubs per variable and formed exactly `2n/3` clauses of planted color
pattern `001` and `2n/3` of pattern `011`, rejecting repeated variables and
duplicate clauses. Thus every variable occurs exactly four times, every clause
is NAE-satisfied by construction, and the instance has `4n/3` clauses. A
standard DPLL search with NAE unit propagation solved all eight seeds:

| variables | clauses | solved | DPLL nodes, range | wall time, range |
|---:|---:|---:|---:|---:|
| 60 | 80 | 8/8 | 15--31 | 0.00124--0.00289 s |
| 120 | 160 | 8/8 | 38--50 | 0.00427--0.01255 s |
| 240 | 320 | 8/8 | 68--89 | 0.01722--0.02408 s |

The 240-variable row is the largest source assignment that fits the 256-atom
answer cap. Its nominal `2^240` assignment space is irrelevant: the
domain-standard attack needs fewer than 90 branch nodes on every tested seed.
Consequently the prior-triage proposal—plant a coloring or cut partition and
then realize it geometrically—fails G6 and H on Track A for the natural
distribution.

The hard source instances used by the ETH proof cannot simply replace these
samples. To carry a positive witness, the generator must already know a
satisfying assignment. Obtaining that assignment for arbitrary hard inputs is
the forbidden act of solving the instance. Relabeling a fixed solved hard
formula yields only one canonical instance and fails G8 diversity. Inventing a
new cryptographic or average-case-hard satisfiable distribution would be new
mathematics not supplied by this paper.

Track B does not rescue this route. The paper's general target algorithms are
subexponential/XP mechanical searches, but a planted formula has no compact
solver-side route merely because its generator retained the assignment. In the
only obvious answer-first regime, the measured mechanical route is already the
tiny DPLL computation above. Encoding the retained assignment in coordinates
or labels so a model can decode it in under 300 operations would add an
artificial side channel, and the resulting shortcut—not the paper's separator
or lower-bound framework—would be the entire problem.

The native target witness also hits G9(c) before the source can be hard. In
dimension two, the cell-gadget skeleton in Section 5.2 has ten positions. The
root gadget replaces each position by a clique containing all `4N` literal
occurrences of an `N`-variable E4 source formula, so that gadget alone has
`40N` vertices; 2-Subcoloring additionally has the `N`-vertex consistency
clique and three vertices for each of the `4N/3` clauses. Thus even before the
non-root propagation gadgets, a literal full coloring has at least `45N`
bits. The 256-atom cap forces `N <= 5` (and incidence counting actually makes
`N` a multiple of three), a hand-trivial source. Dimensions at least three use
an even larger skeleton. Theorem 19's cut construction removes the consistency
clique but adds five clause/terminal vertices per clause, already giving
`40N + 5(4N/3) = 140N/3` partition bits before non-root gadgets, so it has the
same obstruction.

A compact answer containing only an assignment of the variables *before* the
E4 and geometric reductions could stay under the cap and deterministically
expand to the coloring or cut. But then the solver is handed and graded on the
source NAE formula; the geometric objects and millions of target-graph colors
are never inspected. Under the required profile this is a convenience
surrogate with `computational_core="csp_sat"`, not native geometric coverage.
Applying the cited E4 equality-gadget reduction to a denser planted formula
only makes this mismatch larger: it adds occurrence copies and fixed auxiliary
variables while the compact answer remains the pre-reduction assignment. The
paper supplies no average-case theorem for that planted source, and filtering
generated formulas by running a capped SAT solver would be post-hoc benchmark
tuning, not theorem-backed hardness.

## Why the alpha-modulator hardness observation does not rescue the task

Section 3 observes

`alpha(G)/2 <= alpha-mod(G+G) <= alpha(G)`.

This transfers inapproximability from Maximum Independent Set, but it does not
identify the exact alpha-modulator number. A proposed modulator certifies only
an upper bound, and even that requires certificates for every remaining
component's independence-number upper bound. An independent set supplies a
lower bound on `alpha(G)`, not a matching lower bound on `alpha-mod(G+G)`.
Therefore an exact/optimal witness would require solving the hard source or
adding a new optimality certificate absent from the paper. This candidate
fails G and V before hardness testing.

## Gate diagnosis

| Candidate | G | H, Track A | H, Track B | V | Outcome |
|---|---:|---:|---:|---:|---|
| Theorem 1 separator / slab residues | Pass | **Fail:** polynomial histogram | **Fail:** 2,920 mechanical versus 2,920 compact operations | Pass only for slab residues; an alpha bound needs more certificate | Reject |
| Theorem 17 2-subcoloring reduction | Pass only with an answer-first source | **Fail for the natural source:** DPLL 8/8; worst-case ETH is not distributional | **Fail:** no compact route; the easy planted source already costs under 90 nodes | Pass for a full coloring | Reject |
| Theorem 19 zero-weight connected cut | Same source issue | Same NAE attack and distribution gap | Same absence of a paper-derived compact route | Pass for a zero-weight feasible cut | Reject |
| Exact alpha-modulator via Section 3 observation | **Fail:** exact optimum not carried through the factor-two bound | Not reached | Not reached | **Fail:** no matching executable lower-bound certificate | Reject |

The rejection is therefore not based merely on the existence of an algorithm.
For the only polynomial certificate construction, the measured mechanical and
compact routes are identical. For the hard results, the paper proves only
worst-case lower bounds and the measured inverse-planted distribution is easy.
