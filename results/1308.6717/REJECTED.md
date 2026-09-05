# Rejected: arXiv 1308.6717

This paper does not yield an acceptable hard generator from the natural
Hamiltonian-cycle construction tested here.  **G and V pass, but H fails on both
tracks.**  The attempted generator is retained as
`rejected_gen_1308_6717.py`, as required.

## Paper result used

The paper is [Maity–Upadhyay, *Hamiltonian Cycle in Semi-Equivelar Maps on the
Torus*](https://arxiv.org/abs/1308.6717).  Section 1 defines a map, its face
sequence, semi-equivelarity, normal cycles, and the planar `T(r,s,k)`
representation.  Section 6, Definition 5.1 defines the normal path for maps of
type `{4,8,8}`.  Section 6, Theorem 5.1 proves that every such toroidal map has a
contractible Hamiltonian cycle by joining homologous normal rows with adjacent
4-faces.  The global Theorem 2 includes `{4,8^2}` among the Hamiltonian types.

The attempted native family used exactly these objects: a `{4,8^2}` toroidal
map obtained by truncating a square-torus quotient, and a Hamiltonian transition
system checked by expanding it to the map.  The certificate was known by a
structure-preserving row-gauge relabelling, not by solving the generated
instance.  Verification used only modular arithmetic, degree checks, and one
graph traversal.

## Track decision and costs

Track A is unavailable.  Theorem 5.1 is itself a constructive row-concatenation
method.  Once the `T(r,s,k)` rows are known, its cycle can be emitted in linear
time in the number of map vertices; this distribution therefore cannot support
a claim that no efficient general method is known.

Track B was tested rather than rejected merely because that method exists.  At
the attempted shipping instance `r=204, s=160` (130,560 truncation vertices),
the mechanical reference construction plus exact expansion visited 130,720
states and took 0.101290 seconds in CPython.  The compact row-gauge route used
103 nibble/parity operations, and its two-mask JSON answer was 126 characters.
Thus there is a real mechanical/compact gap; the reason for rejection is that
the answer distribution is nevertheless easy, not that the two costs are
comparable.

## Failing gate

The family fails **H on Track B**, concretely G4 and G6 when the candidate prior
is made construction-aware.

The initially naive G4 prior sampled both masks uniformly and observed 0 hits in
200,000 samples.  That number is misleading.  From the map definition, the
vertical matching has the obvious alternating phase.  Fixing only that phase
and sampling the other mask uniformly gave:

| intrinsic dimensions | valid one-cycle masks | samples | success rate |
|---|---:|---:|---:|
| 40 by 40 | 2,079 | 5,000 | 41.58% |
| 80 by 80 | 1,945 | 5,000 | 38.90% |
| 160 by 160 | 407 | 1,000 | 40.70% |

This is the relevant structure-aware prior: an answer is obtainable with one
obvious half-mask and an arbitrary other half-mask at a probability many orders
of magnitude above `1e-6`.

The first eight-seed adversary panel independently exposed the same defect.  It
recorded 3/8 successes for “largest seam outlier,” 4/8 for a local seam-parity
greedy rule, and 5/8 for the period-two phase probe; only the fully uniform
256-restart attack scored 0/8.  G6 requires every attack to have zero successes.
Filtering presentations against those named attacks would only tune to the
panel: row gauges are isomorphisms, and the 25–40% alternating-mask density is
invariant under the gauge.

## Why no module ships

A full vertex-list certificate avoids the compressed-mask density, but under
the 256-atom output cap the paper's linear row construction and the act of
writing the answer are both only a few hundred steps.  There is then no useful
Track B compression gap.  The tested compressed certificate creates a large
mechanical/compact gap, but also creates a high-density answer space that is
guessable by an in-context structural heuristic.  Consequently no natural
version tested here clears H, even though generation and exact verification are
sound.

No LLM hardening run was made: STEP 3 had already failed, so running the paid
oracle loop would not provide admissible hardness evidence.
