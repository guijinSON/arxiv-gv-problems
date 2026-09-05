# Rejected at Step 0: arXiv 1209.0315

Paper: Min Yan, [*Combinatorial Tilings of the Sphere by
Pentagons*](https://arxiv.org/abs/1209.0315), v6 (2014).

## Decision

No problem generator is shipped. The paper's native positive witness is an
embedded graph whose faces are pentagons. Such a witness is generatable and
exactly checkable, so **G and V pass in isolation**, but the available families
fail **H on both Track A and Track B**.

Track A is unavailable because the paper proves no computational or
distributional hardness result. In the regimes it classifies, its proofs
explicitly construct the whole tiling layer by layer or timezone by timezone.
The proposed distribution would therefore be supported by a direct linear-time
construction, not by a hard search theorem.

Track B does not rescue the proposal. If the requested answer is the embedded
tiling, the paper's mechanical construction and the shortest possible route
both have linear cost merely to write the witness. If the answer is compressed
to the earth-map family or its parameters, Theorem 6 leaves only five families
and the input already determines the repetition count. There is no large answer
space or nontrivial compression gap.

This is a Step-0 rejection. In accordance with the task instructions, no module,
self-test report, README, or oracle transcripts were fabricated.

## The paper's exact native objects

Section 1 defines a combinatorial pentagonal tiling of the sphere as a graph
embedded in the sphere such that:

- every complementary tile is homeomorphic to a disk;
- the boundary of every tile is a simple closed path of exactly five edges; and
- every vertex has degree at least three.

This is combinatorics, not a metric geometry problem: edge lengths, angles, and
coordinates are explicitly discarded in Section 1. A faithful finite encoding
is a combinatorial map (a rotation system) or, equivalently for verification
here, a list of consistently oriented cyclic face boundaries. The checker can
traverse every dart, require each undirected edge to occur in two opposite face
boundaries, check five distinct vertices per face, check that every vertex link
is one cycle, check minimum degree three and connectedness, and verify Euler's
equation `V - E + F = 2`. These are exact linear-time checks.

Euler and Dehn--Sommerville counting in Section 1 give

`v_3 = 20 + sum_{i>=4} (3i-10) v_i`

and

`F = 12 + 2 sum_{i>=4} (i-3) v_i`.

They imply that the number of faces is even, but they do not supply a hard
search problem.

## Step-0 certificate-producing methods

The certificate-producing procedures are the paper's main constructions.

- Theorem 4 (Section 3) starts at a vertex of degree greater than three and
  constructs successive layers of pentagons. Under its distance hypothesis,
  all rays are forced to converge at the second pole, giving the distance-five
  earth map.
- Theorem 5 repeats a six-tile local development until the available pole edges
  are exhausted, giving the distance-four earth map.
- Section 4 develops any meridian of length one, two, or three to the next
  meridian. The resulting strip is a **timezone**, and repeating that same
  timezone closes the sphere.
- Theorem 6 classifies every tiling with exactly two vertices of degree greater
  than three into exactly five earth-map families, one for each pole distance
  from one through five.
- Section 1 also gives a connected-sum construction: delete one pentagonal face
  from each of two known tilings and glue the two five-edge boundaries.

None of these methods obtains the witness by solving a generated instance. That
is why G is available. It is also why the natural search task has no Track-A
hardness claim: the witness is exactly the output of a direct construction.

The paper also states the relevant easy/classified regimes. Theorem 1 rules out
exactly one high-degree vertex. Lemma 2 classifies the small disk boundaries
used by the reductions. Theorems 4 and 5 force earth maps under the stated
distance conditions, and Theorem 6 is a complete five-family classification
when there are exactly two high-degree vertices. In particular, the unique
16-face tiling is the distance-five earth map.

## Mechanical cost versus compact route

Consider the strongest faithful positive task suggested by the prior triage:
given a permitted face count and an earth-map regime, output an embedded
pentagonal tiling as cyclic face boundaries.

For any spherical pentangulation with `F` faces,

- `E = 5F/2`,
- `V = 3F/2 + 2`, and
- an explicit face-list certificate contains exactly `5F` vertex incidences.

The 256-atomic-element answer cap therefore permits at most `F = 48` among the
paper's admissible multiples (distance five uses multiples of four; the other
earth maps use multiples of twelve). At this largest cap-compatible size the
witness has `V = 74`, `E = 120`, and exactly **240 atomic vertex incidences**.

The paper's mechanical timezone/layer construction performs 48 constant-size
tile placements and emits those 240 incidences: `Theta(F)` work. A solver who
recognizes the repeated timezone still must emit the same **240 incidences**.
Thus the compact-route lower bound is 240 atomic writes and the mechanical
route's essential output work is also 240 atomic writes (plus constant work per
face). The operation ratio is approximately one, not the million-versus-dozen
gap required for Track B. Raising `F` only lengthens the answer and crosses the
cap at `F = 52`; it does not grow a fixed-length haystack.

There are three possible attempts to compress that answer, and each removes H:

1. Return only the pole distance/family. Theorem 6 restricts this to five values,
   so even a uniform guess succeeds with probability at least `1/5`, far above
   G4's `10^-6` limit.
2. Return the family and the timezone count. Both are read directly from the
   requested regime and `F`; the answer is a constant-size transcription of the
   input.
3. Let the checker expand a succinct timezone program. Then the program is just
   the displayed construction in Sections 3--4. The mechanical and compact
   routes are the same constant template plus a repeat count.

This supplies the required numerical comparison. The rejection is not based on
the mere existence of an efficient algorithm; it is based on the lack of any
solver-visible shortcut shorter than the certificate production/output itself.

## Other native formulations considered

| Candidate problem | Gate that fails | Reason |
|---|---|---|
| Construct an earth-map tiling with `F` faces | **H, Tracks A and B** | Sections 3--4 directly repeat a fixed layer/timezone; at `F=48`, construction and compact output both require the same 240 incidences. |
| Verify that a supplied combinatorial map is a spherical pentangulation | **H / witness rule** | Face traversal and Euler checking are linear-time verification; if the embedding is already the instance, there is no witness to find. |
| Recover faces/rotation from a plain graph | **H, Tracks A and B; domain fidelity** | Planar embedding is algorithmic, and recovering data deliberately removed from the paper's native embedded graph is a representational wrapper. An explicit answer is again linear-size. |
| Name the earth-map family | **G4 and H** | Theorem 6 leaves only five possibilities; the two poles are the only vertices of degree greater than three and their distance is at most five. |
| Return the poles or a meridian | **H / G6** | The poles are degree outliers. A meridian is an ordinary shortest path between them, found by breadth-first search, with length at most five. |
| Find a connected-sum seam | **G4 and H** | A nonfacial simple five-cycle separates the sphere into two pentagonally tiled disks. Once a structure-aware candidate also enforces the locally visible condition that each boundary vertex has an incident noncycle edge on each side, capping both disks gives two valid spherical tilings; every remaining candidate is already a valid seam. |
| Complete one of the small boundary configurations | **H** | Lemma 2 and the subsequent finite reduction tables classify the cases, while Lemma 3 forces the next face locally. |
| Certify that one high-degree vertex is impossible | **V or H** | Theorem 1's certificate is its unbounded diagrammatic reduction proof. Restricting to the finite configurations of Lemma 2 makes the answer a classification lookup. |
| Add labels, a mask, SAT constraints, or metric coordinates to hide a chosen embedding | **domain essentiality** | The resulting difficulty comes from an external convenience wrapper absent from this combinatorial paper. |

## Gate diagnosis

| Requirement | Result | Evidence |
|---|---|---|
| G -- generatable | Passes in isolation | The layer, timezone, and connected-sum constructions retain an exact embedding by construction. |
| V -- exact witness checking | Passes in isolation | Dart incidences, face lengths, degrees, connectedness, and Euler characteristic are checked exactly in linear time. |
| H -- Track A | **Fails** | No hardness theorem or hard generated distribution is given; the relevant theorems instead construct or completely classify the objects. |
| H -- Track B | **Fails** | At the answer cap, 240 mechanical incidence emissions versus a lower bound of 240 emissions for the compact route; compressed classifications have at most five choices. |
| G4 -- guess resistance | **Fails for compressed answers** | A five-family answer has success probability at least `0.2`; timezone parameters are input-determined. |
| G6 -- adversary panel | **Cannot pass** | Direct timezone expansion, degree-outlier pole detection, and breadth-first meridian search are successful standard/in-context attacks by construction. |
| G9(c) -- no-tool suitability | Incompatible with hardness | Explicit witnesses reach 240 of 256 atoms at only 48 faces; increasing size grows the needle, while compressed witnesses are trivial. |
| Overall | **Rejected at Step 0** | No paper-native family simultaneously satisfies G, H, and V on either track. |

The complete v6 source was read, including the definitions and counting identities
in Section 1, the full small-boundary reduction behind Theorem 1 and Lemmas 2--3,
the layer constructions of Theorems 4--5, and the meridian/timezone classification
and proof of Theorem 6 in Section 4.
