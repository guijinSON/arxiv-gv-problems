# Rejection: arXiv 2003.05015

Paper: [*PL1P -- Point-line Minimal Problems under Partial Visibility in Three Views*](https://arxiv.org/abs/2003.05015)

## Decision

**H fails on both tracks.**  Generation and exact verification are available, but the
paper does not yield a scalable hard distribution satisfying the requested gates.
This decision was made at Step 0, before writing a generator, so there is no
`rejected_gen_2003.05015.py` to retain.

- **G would pass:** choose rational calibrated cameras and a rational point-line
  arrangement, then project the visible features.  The chosen cameras and scene are
  an inverse-generated certificate.
- **V would pass:** reconstructing image points and lines from a proposed rational
  scene/camera tuple and comparing projective coordinates is exact substitution.
- **H fails:** Track A has neither a theorem nor evidence for hardness of that planted
  rational distribution.  Track B has no short structural route distinct from the
  paper's mechanical solve.  The only genuine scaling supplied by the paper adds
  features that its reduction theorem immediately removes.

## Exact paper objects and the obstruction

Definitions 1--4 in Section 3 define a problem using points in projective 3-space,
lines in the Grassmannian, incidences, partial visibility, and three calibrated
cameras `[R | t]`, with the first camera fixed to `[I | 0]` and the first coordinate
of the second translation fixed to 1.  I therefore considered native rational
camera/scene witnesses, not a graph or finite-field surrogate.

Theorem 1 and Theorem 2 in Section 4 are the decisive obstruction.  Reduction
preserves minimality and degree, every minimal PL1P in three views has a unique
reduced problem, and applying the inverse reductions merely restores superfluous
features.  Section 5 then encodes every reduced candidate by 27 nonnegative counts
whose weighted sum is the fixed camera budget 11.  Thus the apparent infinite
family has a bounded reduced core: the paper enumerates 845,161 balanced signatures,
143,494 label classes, and ultimately 140,616 reduced minimal classes.  Increasing
`n` by inverse reduction grows only an O(n)-scannable shell and leaves the algebraic
degree unchanged.  It cannot satisfy G7 as genuine growing difficulty.

Increasing coordinate heights instead would lengthen exact arithmetic without
adding mathematical structure.  That is a calculator/transcription axis, not a
no-tool insight axis, and it does not supply Track A distributional hardness.

## The certificate question asked first

Two native witness families were examined.

| proposed claim | witness | algorithm that produces/checks it | outcome |
|---|---|---|---|
| a balanced signature is minimal | a finite-field scene/camera evaluation whose joint-camera-map Jacobian has full rank | Section 7 and Section 13.2: random evaluation over `F_q`, followed by exact rank computation | The witness is valid, but this is precisely a randomized polynomial-time linear-algebra route, so Track A fails. |
| these images have a camera/scene solution | rational calibrated camera matrices and rational projective points/lines | Section 8 and Section 13.3 use the eliminated camera formulation with numerical monodromy/homotopy; the paper also says the sub-300-degree cases are solvable with existing solver technology | Inverse planting supplies G and exact substitution supplies V, but generic planted data offers no compact route shorter than solving the same polynomial system, so Track B fails. |

The degree table does not repair the second row.  Asking for a degree is a lookup in
the paper's classification, while asking for a camera solution requires the solver
machinery itself.  A deliberately nongeneric coordinate code could expose the
planted camera, but that would be a generator side channel rather than a consequence
of the PL1P theorems, and the resulting small linear recovery would be the efficient
algorithm for the generated distribution.

## Mechanical cost versus compact route

For the strongest exact-certificate option (the Section 7 minimality test), the
balance equation bounds a reduced Jacobian by 88 rows/columns: a weight-1 local
feature contributes at most 8 image dimensions, and the total weight is 11.

I benchmarked ordinary dense modular elimination on eight random full-rank 88 x 88
matrices over the prime field of order 1,000,003.  Counting one inversion, row
normalization multiplications, and multiply/subtract elimination operations gives
**458,260 field operations**.  Median CPython wall time was **0.040031 s** over eight
trials (individual times 0.038635--0.062904 s).  This excludes constructing the
Jacobian and any retry after an unlucky evaluation.

The paper supplies no invariant, symmetry, or change of variables that produces a
full-rank evaluation without performing that evaluation and rank test.  Consequently
the compact route is the same **458,260+ field operations**, a mechanical/compact
ratio of approximately **1.0**, not a route of at most 300 operations.  It therefore
fails Track B and G9(c), while the 0.04 s polynomial-time computation disqualifies a
Track A claim.

For reconstruction, Section 8's mechanical route is monodromy in the eliminated
camera variables, collecting solutions one by one (degrees below 300 are tabulated,
and some known cases exceed 1,000).  On generic generated images the compact route is
again the same polynomial-system solve: at degree `D`, both require the `D` solution
tracks/collection process rather than a paper-provided constant-step recovery.
There is therefore no Track B compression gap to measure or ship.

## Easy regimes that had to be checked

- Section 4's reduction rules delete the only features available for unbounded
  combinatorial growth while preserving degree.
- Section 7 reduces minimality certification to finite-field Jacobian rank.
- Section 8 explicitly identifies hundreds of degree-below-300 problems as solvable
  with existing technology and uses an eliminated camera formulation for efficiency.
- Section 10 (supplement) shows that the reduced two-view regime collapses to the
  classical five-point problem.
- Result 5 in Section 8 decomposes many three-view extensions into a five-point
  relative-pose problem plus camera registration.  This is composition of existing
  solvers, not a new hard distribution.

## Why the prior triage hypothesis is insufficient

Sampling cameras and 3D features and projecting them is a sound inverse generator,
and the planted scene is a sound exact witness.  It proves only G and V.  The paper's
minimality theorem is about generic finiteness and algebraic degree, not hardness of
the sampled distribution.  Worst-case or distributional hardness is not proved, and
the natural scalable extensions are explicitly reducible to a bounded core.  Shipping
that proposal as Track A would therefore make exactly the forbidden inference from
“many algebraic solutions” to “hard generated instances.”
