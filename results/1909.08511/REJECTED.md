# Rejected at Step 0: arXiv 1909.08511

Paper: Rui Li and Tao Wang, [*DP-4-coloring of planar graphs with some
restrictions on cycles*](https://arxiv.org/abs/1909.08511) (v2, 2021).

## Decision

No generator is shipped.  The paper supplies an exact, cheaply checkable native
witness, but it does not supply a problem family that clears **G and H together**.
The prior-triage proposal (sample a DP-coloring and add compatible cover
matchings) passes inverse generation and verification, but it has no Track-A
hardness basis.  In the clean theorem-backed subfamily, the standard coloring
algorithm succeeds on every tested instance in a fraction of a millisecond.
The paper also provides no shorter solver-visible invariant that would turn the
same construction into a Track-B compression problem.

This is a failure of **H on Track A** for the inverse-planted proposal, and a
failure of **G** for the alternative that merely samples a graph and invokes an
existence theorem without constructing its coloring.  Track B was considered
separately below; it fails because the mechanical and compact routes are the
same linear scan, or because no compact route exists at all.

## What the paper actually proves

Definitions 1 and 2 give the native object and witness.  A 4-matching assignment
places four labels in each vertex fiber.  Every base-graph edge carries a
matching between the two endpoint fibers.  An `M`-coloring is an independent
transversal: exactly one label is chosen from every fiber, and no selected pair
is one of the displayed matched pairs.  A submitted list of labels is therefore
an excellent witness—shape, range, one-per-fiber, and every edge constraint are
all checked exactly in `O(|V|+|E|)` time.

The substantive results are universal extension theorems, not hardness results:

- Theorem 1.3 says that, for a plane graph avoiding the three configurations in
  Figure 2, every DP-coloring of one vertex or of a cycle of length at most six
  extends to a DP-4-coloring.
- Theorem 1.4 proves the analogous statement for the Figure 3 restrictions and
  a precolored cycle of length at most six.
- Theorem 1.7 uses the Figure 4 restrictions and a precolored cycle of length at
  most seven.

Sections 2, 3, and 4 prove these statements by assuming a minimal
counterexample, deriving structural properties, and discharging to a
contradiction.  They do **not** output an independent transversal for an input
cover.  Several reduction arguments also invoke minimality after vertex
identification; the final discharging contradiction is an existence proof, not
a finite coloring certificate carried by a sampled graph.

This distinction defeats the tempting theorem-backed generator.  Sampling an
arbitrary graph/cover in one of the stated regimes makes existence known, but
does not make the concrete witness in `inst["answer"]` known by construction.
Obtaining that witness by backtracking or by turning the reducibility proof into
a recursive coloring routine would be solving the generated instance, which G
forbids.

## Audit of the inverse-planted proposal

Inverse planting repairs G: first sample one label per vertex, then choose every
edge matching subject to excluding the planted endpoint pair.  It also repairs
V: a checker need only inspect the candidate and the cover.  It does not repair
H.

The paper contains no complexity-hardness theorem, average-case theorem, or
hard planted parameter regime.  Its theorems assert colorability for *every*
matching assignment in their graph classes.  Worst-case hardness for some
broader coloring problem could not establish hardness of this conditioned
planted distribution, and no such result appears in the paper in any event.

I tested the most conservative native regime rather than inferring hardness
from the answer-space size.  A square grid is triangle-free and hence avoids all
three Figure 2 configurations.  I fixed one corner label (the `|S|=1` case of
Theorem 1.3), sampled the other planted labels uniformly, and placed an
independent uniformly shuffled perfect matching on each grid edge conditioned
only on preserving the plant.  A structure-aware random candidate is simply an
arbitrary choice from the four labels at every unpinned vertex.

At an 8-by-8 grid (64 vertices and 112 edges), the language has `4^63`
candidates after the pinned label.  A direct sample had **0 valid answers in
200,000 guesses**.  Nevertheless, the standard exact algorithm peels a vertex
of current degree at most three while retaining the pinned corner, restores the
vertices in reverse order, and takes any label not forbidden by already colored
neighbors.  It solved **20/20** independently planted instances.  With one
operation charged for a queue/removal step, a label trial, or an inspected
incidence, it used **506–553 operations** (mean 537.0) and mean wall time
**0.140 ms** in CPython 3.12.

The same measurement at other sizes was:

| grid | vertices | edges | solved | counted operations (min–max, mean) | mean wall time |
|---|---:|---:|---:|---:|---:|
| 6 x 6 | 36 | 60 | 20/20 | 270–312, 288.8 | 0.071 ms |
| 8 x 8 | 64 | 112 | 20/20 | 506–553, 537.0 | 0.140 ms |
| 12 x 12 | 144 | 264 | 20/20 | 1,218–1,304, 1,259.8 | 0.518 ms |
| 15 x 15 | 225 | 420 | 20/20 | 1,955–2,048, 1,994.4 | 0.806 ms |

The 225-vertex answer still fits the 256-atom output cap, so this is not a
`cap_bound` conclusion.  It is an easy-distribution conclusion: a huge answer
space and zero sampled random hits coexist with a deterministic linear-time
solver.  This is precisely why G4 alone cannot establish H.

The grid is not claimed to represent every graph covered by Theorem 1.3.  It is
the scalable, construction-safe version of the proposed planted family.  Moving
to denser Figure-2-free graphs might make this particular peeling routine less
immediate, but the paper gives no theorem that the resulting planted
distribution is hard.  Claiming Track A after that move would be speculation,
not a paper-backed parameter regime.

## Mechanical cost versus compact route (Track B audit)

An efficient method existing is not itself a rejection; the possible Track-B
gap was checked explicitly.

| candidate construction | mechanical certificate-producing route | compact route after seeing the paper's structure | Track-B outcome |
|---|---|---|---|
| Triangle-free planar/grid cover | Degree-at-most-three peeling plus reverse greedy DP-coloring, `O(|V|+|E|)`; 537 operations and 0.140 ms on the 64-vertex probe | The identical peeling and edge inspection; about 537 operations | No compression gap; the two routes coincide |
| Full cover consistent on every cycle (Lemma 1.1) | Propagate four-label permutations along a spanning tree, straighten the cover, then color the base graph, `O(4|E|+|V|)` | The identical permutation propagation licensed by Lemma 1.1 | No compression gap; at 225 grid vertices even normalization alone is about `4*420+225 = 1,905` table operations |
| Arbitrary Figure-2-free cover with Theorem 1.3 only | Backtracking, or a new constructive implementation extracted from the minimal-counterexample proof | None stated in the paper; the theorem gives existence but not the labels | No compact route to test, so this is not Track B |
| Arbitrary inverse-planted cover | Generic CSP/DPLL search | The privately sampled coloring is not solver-visible; there is no invariant in the instance that reveals it | No compact route; adding one would be an external benchmark encoding rather than this paper's result |

At the 6-by-6 setting, the complete mechanical route is already approximately
the 300-operation no-tool cap (270–312 operations), and the purported compact
route is the same length.  At larger settings both grow together.  Thus there
is no regime in which the paper replaces a large mechanical computation with a
short invariant-driven derivation.  Lemma 1.1 is a useful normalization lemma,
but executing it requires reading and composing the edge permutations; it is
the algorithm, not a shortcut around the algorithm.

## Why no alternative witness fixes the issue

- Returning only the precolored vertex or boundary cycle is not a witness that
  an extension exists.  The checker would still have to search for the missing
  transversal or appeal non-executably to the theorem.
- Returning the full independent transversal is exactly verifiable, but either
  it is obtained by solving the sampled instance (failure of G) or planted first
  (no Track-A hardness result for the distribution).
- Returning a discharging table certifies only the global counting contradiction
  used in the proof.  It does not locally certify that a particular list of
  chosen labels exists.
- Restricting to consistent full matchings makes Lemma 1.1 executable, but also
  exposes the direct linear-time normalization route described above.
- Encoding SAT or a different hard CSP into a graph cover would require a
  reduction not present in this paper and would abandon the cycle-restricted
  planar regime that constitutes its contribution.

## Gate outcome

| requirement | outcome |
|---|---|
| G — theorem-backed construction | **Fail:** Theorems 1.3/1.4/1.7 prove existence but do not construct the concrete transversal stored as the answer |
| G — inverse-planted construction | Pass: choose labels first and condition edge matchings on them |
| V — exact witness checking | Pass: one label per fiber and all matched edge pairs are checked locally |
| H — Track A | **Fail:** no distributional-hardness theorem or hard parameter regime; the natural theorem-safe probe is solved 20/20 in under 0.001 s |
| H — Track B | **Fail:** the mechanical and compact routes coincide on the tractable subfamilies; for arbitrary covers the paper gives no compact route |
| G4 — guess resistance | Passes in isolation on the 64-vertex probe: 0/200,000 valid random candidates in a `4^63` language |
| G9(c) — intended route | Fails beyond hand scale without creating a compression gap: roughly 537 operations at 64 vertices, while the same route is the reference algorithm |
| overall | **Rejected at Step 0:** no single paper-native family simultaneously clears G, H, and V under either track |

No generator, self-test report, README, or oracle transcript was created.  Once
the G/H incompatibility was established, producing those files or running the
LLM hardening loop would only turn model difficulty with a long explicit cover
into a false hardness claim.
