# Rejected: no supported hard witness-search family

Paper: Kazumi Kasaura, [*Homotopy-Aware Multi-Agent Path Planning on Plane*](https://arxiv.org/abs/2310.01945), arXiv:2310.01945.

## Decision

This paper does not support a problem generator satisfying all of G, H, and V. The blocking gate is **H (hardness)**. I therefore did not create `gen_2310_01945.py`, did not fabricate passing gate measurements, and did not run the LLM hardening harness.

## What the paper actually defines

Section 3 gives a finite undirected planar roadmap, labeled agent starts and goals, and synchronous discrete moves. A solution is a tuple of agent paths with neither vertex conflicts nor opposite-direction edge swaps. The paper then asks, for a supplied `K`, for `K` mutually non-homotopic solutions with small sums of costs.

This is not an exact automatically gradable optimization specification as written: “small” has no threshold, approximation factor, or other Boolean acceptance condition. Removing “small” would leave a witness problem whose answers are collision-free paths in distinct homotopy classes. Such witnesses are generatable and can be checked by replay plus the paper's braid/Dynnikov calculations, but the paper does not show that finding them is hard.

## Why H fails

- Section 4.6 and Algorithm 1 give Homotopy-Aware Revised Prioritized Planning specifically to generate multiple homotopically distinct solutions. The experiments report scaling to 500 agents and roughly quadratic observed runtime over that tested range (Section 5.2), so those experiments are evidence against claiming the sampled regime is hard.
- Proposition 3 in Section 4.7 proves completeness when boundaries, obstacles, starts, and goals are sufficiently separated and the roadmap is dense enough. Corollary 4 gives the corresponding four-connected-grid conditions.
- More decisively for inverse generation, the proof of Proposition 3 explicitly constructs arbitrary required braid factors: after reaching its goal, an agent follows the boundary, circles a selected obstacle or goal clockwise/counterclockwise, and returns. The following remark says a modified version of Algorithm 1 can find a solution for a given target braid under the same assumptions. Planting a braid or homotopy class in that regime therefore does not create an unsupported one-way search problem.
- Section 4.5 states that equality of braid words can be checked with Dynnikov coordinates in `O(l^2)` time. Turning the task into braid-word equality would be verifiable, but it would be polynomial-time and fail H outright.
- Appendix A only shows that one earlier Dehn-algorithm treatment of the **pure** braid presentation is incomplete for four or more agents. It does not prove that a witness-search problem is hard; the paper avoids that issue by using the braid group and Dynnikov coordinates.
- The paper contains no NP-hardness, PSPACE-hardness, parameterized-hardness, or lower-bound theorem for finding a feasible solution, finding a prescribed homotopy, or generating `K` homotopy classes.

## Why the triaged generator is not acceptable

The proposed “plant starts, goals, obstacles, and feasible agent paths with homotopy classes; verify by replay” does establish G and V. It does not establish H. In the paper's complete separated regime, the constructive proof and target-braid search defeat the premise. Outside that regime, hardness would have to come from an independently chosen bounded-horizon or optimal MAPF variant and a separate reduction not supplied by this paper. That would be a new family and hardness argument rather than a verified extraction from this paper.

No oracle transcript is appropriate: `scripts/harden.py` tests empirical LLM resistance only after a theoretically defensible family passes the paper-reading gate. It cannot replace the missing hardness result.
