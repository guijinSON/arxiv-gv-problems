# Rejected at Step 0: sequence planting does not inherit 3D-STAP hardness

Paper: Jakob Keller, Christian Rieck, Christian Scheffer, and Arne Schmidt,
[*Particle-Based Assembly Using Precise Global Control*](https://arxiv.org/abs/2105.05784),
arXiv:2105.05784 (version 3).

## Decision

No generator is shipped. The prior-triage proposal—sample a legal single-tile
assembly sequence, replay it to obtain a target shape, and ask for a sequence
constructing that shape—passes **G (inverse generation)** and **V (exact replay)**,
but fails **H under both tracks**.

For Track A, Theorem 7 proves worst-case NP-completeness only for the specially
engineered 3D polycubes obtained from the paper's Planar Monotone 3-SAT reduction.
It does not say that polycubes produced by replaying random legal sequences are
hard, and the reduction's soundness does not transfer to that inverse-planted
distribution. Claiming Track A would therefore make exactly the forbidden jump
from worst-case hardness to distributional hardness.

For Track B, the paper supplies no route that compresses recovery of an arbitrary
planted sequence. If the generator exposes enough of the plant to recover it,
the task is sequence transcription; if it does not, finding the sequence is the
same STAP search posed by the instance. The paper's constructive special cases do
not rescue this: Theorem 13's tree algorithm and Theorems 20 and 24's scaled-shape
proofs are themselves the step-by-step routes. There is no separate invariant,
symmetry, or change of variables reducing a large mechanical computation to a
short by-hand derivation.

This is a Step-0 rejection, so there is no shippable `gen_2105_05784.py`,
`selftest_report.json`, or README. An experimental generator was nevertheless
built to test a possible compressed Track-B formulation; as required for a
rejected build, it is retained as `rejected_gen_2105_05784.py`. The post-triage
audit below explains why that formulation is not a family from the paper. A
subsequent hardener invocation reached no oracle: four redraws all returned HTTP
403 "Key limit exceeded," and the script-owned error transcript is retained
without counting any call as a model failure.

## Post-triage audit of the retained experimental generator

The experiment makes a monotone tree-shaped polycube path, assigns every cube an
artificial vector tag over a prime field, and publishes a long list of reversible
coordinate shears. Its 24-integer answer is the slope and offset of an affine
rank-to-tag map. The checker expands those coefficients into a cube order and
checks the prescribed run-length construction paths exactly.

That module passes its local G1--G8 tests: the planted programs verify for all
presets, five corruptions receive five distinct failures, parsing round-trips,
0/200,000 structure-aware random programs verify, four attacks fail on 8/8
seeds, the disclosed reference succeeds on 8/8, and the canonical key passes 60
relabeling checks over 20 unrelated instances. At its provisional hard preset
(`n=540`, field modulus `100000007`, 12 tag axes, 120 shears), the implemented
reference accounts for 11,586 primitive operations, while using coordinate sum
as rank and reversing the shears costs 252 exact field operations. The serialized
answer is 238 characters and 24 atomic elements.

Those numbers do **not** cure H. Vector tags, affine rank codes, and shear
programs are not objects or transformations in Keller et al.; they were added by
the benchmark builder. Once they are removed, the target is merely a monotone
path with the seed at one endpoint, and Section 5.1's tree algorithm finds its
only connectivity-preserving order directly. Conversely, with the tags present,
the oracle is mainly being asked to invert an artificial finite-field program:
only the seed cube and its single successor are needed from the geometry. Deleting
the paper's motion model leaves essentially the same affine-key puzzle. Thus the
claimed 11,586-versus-252 gap belongs to the auxiliary encoding, not to STAP, and
cannot support Track B for this paper. Relabeling it as `domain_essentiality =
native` would overstate geometric coverage; declaring it a convenience analogue
would honestly archive it but still would not satisfy this task's request for a
problem family from the paper.

The attempted hardening run supplies no contrary evidence. Its four records are
all infrastructure errors from the same unavailable gateway, so there are zero
scored oracle attempts and G9 fails closed. Even a successful oracle failure would
not repair the provenance defect above: empirical difficulty on the invented tag
decoder is not hardness of particle assembly.

## What the paper actually defines

Section 2 defines a workspace of `2n` positions per coordinate, anchored at the
origin, with the seed tile fixed at `(n,n)` in 2D or `(n,n,n)` in 3D. Each of the
other `n-1` tiles starts at the origin. A construction step is a sequence of unit
grid moves by that one tile; the tile sticks as soon as it becomes adjacent to the
existing assembly. A construction sequence contains one such step for every
non-seed tile. Deconstruction reverses the moves while preserving connectivity.
The restated decomposability theorem in Section 2 says that construction and
connectivity-preserving deconstruction are equivalent.

The paper's relevant positive and negative results are:

- **Theorem 7, Section 3:** 3D-STAP is NP-complete, by a reduction from Planar
  Monotone 3-SAT using indestructible walls, paired-cuboid variable gadgets,
  conjunction gadgets, connector cuboids, and a connectivity frame.
- **Theorem 10, Section 4:** greedy boundary filling is an
  `Omega(n^(-1/d))` approximation for MaxSTAP; it does not certify an optimum.
- **Theorem 13 and Corollary 14, Section 5.1:** constructibility of tree-shaped
  polyominoes and polycubes is decidable in `O(n)` time by repeatedly removing
  removable leaves while maintaining reachable free positions.
- **Theorem 20, Section 5.2:** every 2-scaled non-degenerate polyomino is
  constructible.
- **Theorem 24, Section 5.2:** every 3-scaled non-degenerate polycube is
  constructible.

These distinctions matter. Trees and the guaranteed scaled shapes are explicitly
easy regimes, while arbitrary inverse-replay outputs are not instances of the
hardness reduction merely because they are 3D polycubes.

## Certificate-production test

For the proposed family, generation can sample the answer first. Starting from
the seed, replay a chosen list of legal unit moves, record where each added tile
sticks, and publish the resulting target shape. Reversing the recorded sequence
gives a deconstruction witness by Section 2. This is genuine inverse generation;
the generator did not solve the target instance.

Verification is also exact and cheap relative to the witness. For each construction
step a checker can confirm that positions stay in the workspace, consecutive
positions are unit-grid neighbors, the moving tile has the required clearance,
no premature contact occurs, the final move attaches it to the current connected
assembly, and the final occupied set equals the target. The checker need not read
the planted answer and could accept any legal construction sequence.

The failure is certificate *recovery*, not certificate validity. Theorem 7's
membership-in-NP proof says a single step has length `O(n)` and a complete
construction sequence has length `O(n^2)`. Nothing in that proof identifies a
short recovery rule for shapes produced by a random replay.

## Mechanical cost versus compact route

The native workspace gives a sharper size calculation than the asymptotic bound.
Let `p` be any tile of a connected 2D target containing the seed `s=(n,n)`.
Connectivity through `n` tiles implies `||p-s||_1 <= n-1`, hence

`||p||_1 >= ||s||_1 - ||p-s||_1 >= 2n-(n-1) = n+1`.

Every non-seed tile starts at the origin, so every 2D witness contains at least

`(n-1)(n+1) = n^2-1`

unit moves. In 3D the same calculation with `s=(n,n,n)` gives at least

`(n-1)(2n+1) = 2n^2-n-1`

unit moves. Before encoding tile separators or endpoints, the 256-atomic-element
limit therefore restricts a literal move witness to at most `n=16` in 2D
(`255` moves) or `n=11` in 3D (`230` moves). The 300-operation intended-route cap
only raises those bounds to `n=17` (`288` moves) and `n=12` (`275` moves).

Those are far below the Section 3 hardness construction: one variable gadget
already contains two indestructible cuboids sharing a layer, two bridges, two
L-shaped parts, and a frame, before any clause, connector, or conjunction gadget
is added. Thus no theorem-backed hard instance fits the native explicit-witness
regime.

The tractable tree regime also fails the Track-B compression test quantitatively.
At the largest 2D literal-witness size, `n=16`, Theorem 13's proof says only the
positions within Chebyshev distance two matter—at most `24n = 384` positions—and
each position changes state at most once. Its mechanical algorithm therefore has
only a few hundred state visits plus constant local updates. The alleged compact
route must still describe or reason through at least `n^2-1 = 255` unit moves.
The comparison is **hundreds of mechanical operations versus hundreds of witness
operations**, not a million-operation method versus a dozen-step insight. The
compact route is no shorter in the sense Track B requires.

Run-length encoding would reduce characters, but it would not create a result from
the paper that chooses the runs. For arbitrary inverse-planted shapes the solver
would still have to find a valid tile order and prove every expanded move legal.
Adding a decoder, PRNG seed, or bespoke macro language would manufacture an
auxiliary compression puzzle not present in the paper; it would not establish
hardness of STAP on the generated distribution.

## Why Track A fails

Theorem 7 is a worst-case reduction. Its converse extracts a satisfying assignment
from which side of each variable gadget is deconstructed first; its forward
direction turns a satisfying assignment into a gadget-by-gadget deconstruction.
To use it for generation one would still need an unlimited distribution of
satisfiable Planar Monotone 3-SAT instances with known assignments that is hard to
solve on that distribution. Planting the assignment does not supply that result,
and this paper makes no average-case claim about such formulas.

Direct sequence replay is even further removed from the reduction. It creates
generic positive STAP instances without walls, variable gadgets, conjunctions, or
the reduction's forced-choice argument. A large permutation space or a tiny
uniform-guess probability would not repair the missing distributional premise.

The obvious alternatives do not help:

| candidate | why it does not support Track A |
|---|---|
| Random legal sequence, then publish its target | Theorem 7 does not cover the generated distribution; the plant may leave easy reverse-removal signatures. |
| Tree-shaped target | Theorem 13 and Corollary 14 give a linear-time algorithm. |
| 2-scaled 2D or 3-scaled 3D target | Theorems 20 and 24 guarantee constructibility by constructive deconstruction arguments. |
| Paper's SAT-reduction target from a planted formula | Planting satisfiability does not inherit worst-case Planar Monotone 3-SAT hardness, and the native move certificate is far over the no-tool cap. |

## Why Track B also fails

Track B requires an efficient reference algorithm whose mechanical work is large
at shipping size and a genuinely shorter structural route. None of the paper's
candidate regimes has that shape:

| native candidate | mechanical route | compact route |
|---|---|---|
| Tree-shaped STAP | Theorem 13's `O(n)` reachable-free-position scan and leaf queue | The same leaf-removal rule; it still processes the shape and emits every construction step. |
| Guaranteed scaled shapes | Theorems 20/24 repeatedly expose free space, remove slabs, and cut holes | The same two-phase slab/hole argument; no shorter certificate-selection invariant is given. |
| Arbitrary inverse-replay target | General STAP search for a legal order and paths | No compact route is encoded; the hidden planted sequence is not derivable by a stated shortcut. |
| Replay with the sequence disclosed | Linear exact replay | Direct copying of the answer, not a problem. |

The two concrete numbers required at triage are therefore `384` relevant-position
visits for the paper's capped 2D tree scan and at least `255` unit moves in the
putative compact witness. They are comparable. At larger `n` both grow with the
input/witness; no fixed-answer-length axis or paper-backed shortcut separates them.

## Other witness formulations

- A negative answer to STAP is not usable: the paper gives no bounded refutation,
  coNP certificate, or other exact witness for non-constructibility in general.
- A claimed MaxSTAP optimum is not usable: Theorem 10 is an approximation theorem,
  not an executable optimality certificate or primal-dual equality.
- Returning only a tile permutation while letting the checker search for paths
  would violate the witness rule. The paths are part of what must be certified.
- Returning only the satisfying assignment for a reduction input would make the
  checker verify the SAT surrogate rather than replay a construction of the native
  polycube; it would also leave the planted-formula hardness gap unchanged.

## Gate outcome

| requirement | result |
|---|---|
| G — generatable | Passes for inverse sequence replay: sample legal moves first and construct the target by replay. |
| H — Track A | **Fails:** Theorem 7 is worst-case and does not cover random inverse-replay or planted-satisfiable-formula distributions. |
| H — Track B | **Fails:** `384` mechanical state positions versus at least `255` native witness moves at the cap; no separate compact route exists. |
| V — verifiable | Passes for an explicit full sequence by exact unit-move replay. |
| Negative/optimal variants | Fail V or become easy: the paper supplies neither a bounded no-certificate nor an exact MaxSTAP optimality witness. |
| Steps 1–4 | A retained experimental probe passed local G1--G8 but failed the provenance/H audit; Step 4 had zero scored attempts because OpenRouter returned four HTTP 403 errors. |

This rejection concerns the proposed generatable families, not the correctness of
the paper's NP-completeness theorem. A future construction could reopen the paper
only by supplying either (i) a hard known-certificate distribution that genuinely
lands in the Section 3 gadget regime, or (ii) a paper-faithful compressed
construction witness with a measured mechanical/compact gap. Neither is present
in the paper or in the prior triage proposal.
