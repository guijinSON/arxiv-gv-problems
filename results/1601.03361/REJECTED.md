# Rejected at Step 0: arXiv 1601.03361

Paper: Clinton T. Conley, Andrew S. Marks, and Robin D. Tucker-Drob,
[*Brooks's theorem for measurable colorings*](https://arxiv.org/abs/1601.03361)
(v2, 1 June 2016).

## Decision

No generator is shipped. The paper's native search object is a measurable
coloring of a generally infinite (and potentially uncountable) Borel graph.
The existence proof does not produce a
bounded finite certificate on which `verify()` can decide measurability and
properness by exact computation, so that native task fails **V (executable
witness verification)**.

The prior-triage fallback—plant a coloring of a finite graph and add only
cross-color edges—does pass **G** by inverse generation and **V** by scanning
the edge list. It nevertheless fails **H on Track A** because it lies in the
promise regime of Brooks's theorem, for which a coloring can be found in
linear time. It also does not make a defensible **Track B** family: with fixed
degree, the mechanical Brooks algorithm and even writing the proposed answer
have the same linear size. A random planted coloring supplies no shorter
instance-visible invariant; adding a private encoding solely to hide and then
reveal the plant would make that encoding, not this paper's measurable
coloring mathematics, carry the benchmark.

This is therefore both a native-V rejection and a finite-surrogate-H
rejection. I stopped before Step 1, as required, rather than label ordinary
finite graph coloring as coverage of measurable/Borel coloring.

## What the full paper actually proves

Section 2 defines a Borel graph as a symmetric irreflexive Borel relation on a
standard Borel space. A coloring in the main theorem is not merely a finite
table: it is a function on that space that is measurable for the completion of
a probability measure, or Baire measurable for a compatible Polish topology.

The exact regimes are:

- **Theorem 1.1 (classical Brooks):** a finite graph of maximum degree at most
  `d` has a proper `d`-coloring when it has no `K_(d+1)`; for `d=2`, odd cycles
  are an additional exception.
- **Theorem 1.2 (the paper's main theorem):** for a Borel graph of degree at
  most finite `d >= 3` with no `K_(d+1)`, a `mu`-measurable `d`-coloring exists
  for every Borel probability measure, and a Baire measurable `d`-coloring
  exists for every compatible Polish topology.
- **Theorem 1.4:** if no connected component is a Gallai tree, the graph is
  Borel degree-list-colorable. Here a Gallai tree is a connected graph whose
  blocks are complete graphs or odd cycles.
- **Theorem 1.5:** under the stated end assumptions, an acyclic locally finite
  Borel graph has a one-ended Borel function on a conull or comeager set.
  Section 4 uses that function as a coloring skeleton.
- **Corollary 5.3:** except for the two degree-two groups, the Cayley graph has
  an automorphism-invariant random degree-coloring that is a factor of IID.
  Its witness is a measurable equivariant map from an infinite Bernoulli shift,
  not a finite local rule or finite table.

The easy/exceptional regimes matter. The introduction states that a greedy
procedure gives a Borel `(d+1)`-coloring, while Marks's examples show that even
an acyclic degree-`d` Borel graph may have no Borel `d`-coloring. For `d=2`,
the irrational-rotation graph has neither a Lebesgue-measurable nor a Baire
measurable 2-coloring. Section 6 characterizes the degree-two measurable
obstruction instead of extending Theorem 1.2 to it. These distinctions vanish
if the instance is replaced by a finite adjacency list.

## Step-0 certificate test

### Native measurable coloring

The certificate-producing proof is not a finite algorithm returning a bounded
JSON object. Proposition 2.1 passes to invariant conull/comeager Borel sets.
Section 3 constructs one-ended subforests through countable Borel operations.
Section 4 invokes Borel independent sets, point-away functions, degree-list
coloring, and Lusin--Novikov uniformization. Section 5 additionally invokes the
wired minimal spanning forest and an almost-sure one-endedness theorem.

A finite string purporting to describe a function on an arbitrary standard
Borel space is not enough for the requested checker. The checker would have to
establish, beyond finitely many substitutions, all of the following:

1. that the description denotes a total function on the relevant conull or
   comeager invariant domain;
2. that every graph edge in that infinite domain has differently colored
   endpoints; and
3. that every color preimage is measurable in the required completed
   sigma-algebra, or has the Baire property.

The paper supplies no bounded syntax and no decision procedure for those three
claims. A proof transcript would contain unbounded Borel codes and external
uniformization/existence results, contrary to the witness rule. Hence the main
problem clears existence but not executable verification.

### Finite planted fallback

For the proposed finite fallback, the plant is a valid certificate and edge
scanning is an exact verifier. The fatal algorithm is the constructive form of
Brooks's theorem. Baetz and Wood,
[*Brooks' Vertex-Colouring Theorem in Linear Time*](https://arxiv.org/abs/1401.8023),
give an `O(n+m)` algorithm for exactly the coloring promised by Theorem 1.1.
Thus a required domain-standard G6 attack would solve the family; it could not
appear among Track A's four zero-success attacks.

The construction "sample colors, then add cross-color edges" does not change
that conclusion. Its nominal random-coloring space may be exponentially large,
but solution-space cardinality is irrelevant once the promised graph class has
a linear-time coloring algorithm.

## Mechanical cost versus compact route

The most favorable faithful finite regime is fixed `d=3`, the first degree
covered by Theorem 1.2. Under the 256-atom answer cap, take the largest possible
explicit coloring, `n=256`. A subcubic graph has at most

```text
m <= 3n/2 = 384 edges.
```

The linear Brooks method therefore processes `n+m <= 640` vertex/edge records,
up to its implementation constants, and writes 256 colors. Any explicit
coloring certificate already requires **256 atomic outputs**, so even an
imagined compact route has length at least 256 assignments. The relevant work
counts are therefore at most **640 input records mechanically versus at least
256 output operations compactly**, a ratio no greater than 2.5 in the
fixed-degree regime. Both are `Theta(n)`, and the purported compact route is
already at the 256-operation cap. This does not create the required contrast
between a mechanical route that is out of reach in context and a short route
that becomes practical after one structural insight.

Allowing `d` to grow can make an explicit graph denser, but it does not provide
an insight from this paper. A randomly planted coloring remains hidden random
data, so the solver's route is still the general coloring algorithm. Conversely,
publishing a formula, checksum, affine mask, or other decoding invariant would
create a short route only by adding a new encoding problem absent from the
paper. Such a benchmark-convenience wrapper cannot repair native coverage, and
the paper gives no theorem about its generated distribution or decoding
hardness.

## Why nearby alternatives do not rescue a family

| Paper object or result | Candidate witness | Failure |
|---|---|---|
| Theorem 1.2 measurable/Baire coloring | finite program or Borel code | **V:** no bounded certificate language or exact checker for totality, properness on all edges, and measurability is supplied. |
| Theorem 1.4 degree-list coloring | finite list coloring after discretization | **H:** the finite promised problem has constructive algorithms; discretization removes the Borel content. |
| Theorem 1.5 one-ended subforest | parent map | **V/G:** on the native infinite graph, one-endedness and conull/comeager domain coverage are not finitely checkable from a bounded map description. On a finite graph, every forest has zero ends. |
| Corollary 5.3 factor-of-IID coloring | finite-radius local rule | **G:** the proof establishes a measurable equivariant factor through spanning-forest machinery; it does not provide a bounded-radius rule whose exhaustive local check certifies the corollary. |
| Section 6 degree-two obstruction | negative certificate | **V:** the obstruction quantifies over invariant measurable sets modulo null/meager sets; no Farkas-, Nullstellensatz-, or bounded-refutation-style certificate is given. |
| Finite Brooks graph | list of colors | **H Track A:** linear-time Brooks coloring succeeds. **H Track B:** at fixed degree, mechanical and output costs are both linear and differ only by a small constant factor at the writable limit. |

## Gate outcome

| Requirement | Result | Evidence |
|---|:---:|---|
| G -- answer known by construction | Passes only for the finite planted surrogate | Sample colors first and add edges only between unlike colors. The native theorem is existential and does not emit a bounded certificate. |
| H -- Track A | **Fails for the finite surrogate** | Constructive Brooks coloring is `O(n+m)` on the exact promised class; the planted distribution cannot be harder than this universal algorithm. |
| H -- Track B | **Fails for the finite surrogate** | At `d=3, n=256`, at most 640 input records versus at least 256 answer writes; no paper-backed compact invariant exists. |
| V -- exact witness checking | **Fails for the native measurable task** | The paper supplies no finite executable test for measurable/Baire correctness on an arbitrary Borel graph. |
| Domain essentiality | **Fails for the fallback** | A finite adjacency list plus edge scan retains graph coloring but discards standard Borel spaces, measures/topologies, conull/comeager sets, and factor-of-IID structure. |
| G4--G9 and oracle loop | Not run | Step 0 already rules out G+H+V; random-guess and oracle failures cannot reverse a deterministic algorithm or create a finite native witness. |

No `gen_1601_03361.py`, `selftest_report.json`, `README.md`, or oracle
transcripts were created. Those are release artifacts for a family that has
passed Step 0. The prior triage was correct about inverse generation and edge
verification, but it overlooked both the linear Brooks algorithm and the fact
that the paper's actual contribution is measurability on infinite Borel
graphs, not ordinary finite proper coloring.
