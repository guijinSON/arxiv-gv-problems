# Rejected: arXiv 2603.25113

Paper: [Impact of local girth on the S-packing coloring of k-saturated subcubic graphs](https://arxiv.org/abs/2603.25113), Ayman El Zein and Maidoun Mortada.

## Decision

The candidate family passes **G** and **V**, but fails **H on both tracks**.

- **G passes.** The retained draft composes already-colored triangle and square tiles into 1-saturated subcubic graphs. Its `(1,2,2,2)` coloring is carried through a vertex relabelling, so generation never solves the completed instance.
- **V passes.** A proposed coloring can be checked exactly with bounded-radius graph searches: equal copies of color 1 must be nonadjacent, and equal copies of each color 2 must be at graph distance at least 3.
- **H fails on Track A.** Section 1 states that the paper's constructive arguments yield efficient algorithms. More specifically, Section 2, Theorem 2 proves that every 1-saturated subcubic graph with `g_3(G) <= 4` is `(1,2,2,2)`-packing colorable by repeatedly deleting one vertex of a local triangle, or two vertices of a local 4-cycle, and extending the coloring. On a subcubic graph those configurations are found by constant-radius inspection, so a maintained implementation is linear in `|V|+|E|`. The general NP-hardness cited in Section 1 concerns deciding `chi_rho(G) <= 4` on unrestricted graphs; it gives no hardness for this promised distribution.
- **H also fails on Track B.** There is no meaningful gap between the mechanical algorithm and the proposed shortcut. Both inspect the same bounded-radius local blocks and assign every output color.

## Mechanical cost versus compact route

The retained draft's shipping preset has 36 tiles, 216 vertices, 252 edges, and a 216-entry answer.

The draft originally claimed 155,520 operations for a reference algorithm by running all-pairs BFS (46,656 queue pops plus 108,864 edge inspections). That is not the algorithm supplied by the theorem and is unnecessary: all cycles used by Theorem 2 have length at most four. A linear implementation needs one vertex scan, one edge scan, and one output pass—684 high-level object visits at this preset, plus only constant bounded-degree checks. In a final 800-run check over eight shipping instances, the retained structural solver took 6.42 seconds total (0.00803 seconds per coloring), even though that draft still contains an avoidable quadratic partner-pair scan.

The proposed compact route was reported as 288 steps (216 assignments plus 72 quotient-cycle steps). This understates the work because it omits reading the 252-edge input and recognizing the blocks. Any actual by-hand route must already read the graph and write 216 colors, at least 468 object operations before local checks. Thus the compact route is **no shorter in the relevant sense** than the 684-visit mechanical construction; both are linear scans dominated by input/output. There is no million-operation mechanical route versus a short invariant, only an artificially inserted all-pairs computation.

Reducing the answer to one orientation bit per tile does not rescue Track B: once that compressed language is stated, the domain-standard algorithm is ordinary bipartite coloring of the quotient cycle, again linear and identical to the supposed insight. Increasing the graph merely increases both the mechanical work and the required coloring output together, so it creates a transcription task rather than a fixed-witness haystack.

## Paper coverage checked

- Section 1 fixes the exact definition of an `S`-packing coloring and explicitly describes the proofs as constructive and efficiently algorithmic.
- Section 2, Theorem 2 is the strongest match for the attempted unlimited positive family and supplies its certificate by a local inductive procedure.
- Section 5 gives finitely many explicit sharpness counterexamples and open conjectures. The finite counterexamples do not form an unlimited family, while the conjectures cannot support theorem-backed generation.

Accordingly, the paper does not support a reviewable Track A distribution, and its native constructive family has no Track B compression gap at the writable sizes allowed here. The attempted module is retained as `rejected_gen_2603_25113.py` so this decision can be audited or reopened.
