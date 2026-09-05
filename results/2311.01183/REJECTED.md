# Rejection: arXiv:2311.01183

Paper: Qi Yuan and Erxiao Wang, [*Tilings of the sphere by congruent regular triangles and congruent rhombi*](https://arxiv.org/abs/2311.01183v2).

## Decision

This paper fails **H**, not G or V, for the natural theorem-backed family proposed in the triage. It fails H on **Track A**, and it does not become a meaningful **Track B** family. I therefore stopped after STEP 0 and did not build a generator.

The native candidate was: choose the parameter `n >= 3` in the paper's generalized anti-triangular-prism class, hand the solver the resulting spherical protoset or tiling data, and ask for the tile counts, anglewise vertex combination, and/or a completed tiling certificate. The introductory classification theorem and Section 5.1, case `beta^2 gamma`, give the answer directly:

- 2 regular triangles and `6n - 3` congruent rhombi;
- 6 vertices of type `alpha beta gamma^n`;
- `6n - 6` vertices of type `beta^2 gamma`;
- `gamma = 2 pi - 2 beta` and `alpha = (1-n)2 pi + (2n-1) beta`;
- the remaining geometric parameter is the unique solution in the stated interval of the displayed trigonometric equation.

This is a valid theorem-backed construction (G), and the integer incidence/count part is exactly checkable (V). It is not a hard search distribution.

## STEP 0 findings

### Exact definition

Sections 1 and 2 define an `(a^3,a^4)`-tiling as an edge-to-edge tiling of the unit sphere by congruent regular spherical triangles and congruent spherical rhombi of common edge length `a`, with every vertex having degree at least 3. The angles are `alpha` for a triangle and `beta >= gamma` for a rhombus. An anglewise vertex combination records the multiplicities of these three angles around every vertex.

### What the paper proves and what produces the certificate

The unnumbered main theorem in Section 1 is a complete classification: three parameterized classes and 26 sporadic protosets. Section 5.1 constructs the only class whose combinatorial size is unbounded. Its proof says that one local vertex determines successive tiles and then obtains the two variable counts from

`y + 3 = x` and `3n + y/2 = x`,

giving `x = 6n - 3` and `y = 6n - 6`. The Appendix repeats these formulas and the exact angle equation. Thus the certificate producer on this generated distribution is direct formula evaluation/local forced propagation, not a hard general tiling algorithm.

The other possible sources do not repair this:

- Section 3 handles the concave and degenerate cases by forced local propagation and produces only fixed combinatorial types.
- Section 4 shows that the equal-rhombus-angle cases have one vertex type and explicitly constructs the few resulting tilings.
- Proposition 10 classifies the rational convex cases; the only non-icosahedral answer is a single displayed tiling. Lemma 9's cyclotomic computation produces a finite classification table, not an unlimited hard distribution.
- Lemma 11 (the Irrational Angle Lemma) reduces admissible vertex types to a determinant-zero condition in three dimensions. Turning that necessary condition into a planted low-rank-vector puzzle would discard spherical realizability and be a convenience linear-algebra analogue, not the paper's native tiling problem.
- The two entries marked with many uncounted tilings are fixed-size protosets. Relabellings or rotations provide syntactically unlimited instances but collapse under the required canonical key and therefore do not provide unlimited structural diversity.

### Easy regimes that kill the proposed generator

The paper is a classification paper rather than a computational-hardness paper. It gives no NP-hardness theorem, average-case hardness claim, or parameter regime with an unknown efficient method. In the generated generalized anti-prism distribution, the classification theorem itself identifies every instance and Section 5.1 supplies the witness. For rational angles, Proposition 10 makes the situation even smaller: it is an explicit lookup among the icosahedral type and one exceptional tiling.

## Track A failure

There is no theorem supporting structural hardness for this distribution. More strongly, the paper's classification and construction solve it. Randomizing labels, rotating the sphere, or reordering faces does not change that conclusion and cannot count as diversity under `canonical_key`.

An alternative completion puzzle made by deleting faces would be inverse-generatable and exactly checkable, but the paper proves neither hardness nor a hard parameter regime for such deletions. Any hardness would come from an external exact-cover formulation or from the masking scheme, not from a result in this paper. It therefore cannot support an honest Track A claim.

## Why Track B also fails

Both relevant representations were costed.

| representation at a putative shipping size | mechanical cost | compact route | conclusion |
|---|---:|---:|---|
| Parameter `n` plus the requested count/AVC summary | evaluate `6n-3` and `6n-6`: 2 multiplications and 2 subtractions (or about 6 arithmetic operations if one first solves the two displayed linear equations) | the same 4 formula operations | No compression gap; the compact route is not shorter in a meaningful sense. |
| Explicit native face/angle-incidence list | inspect `3*2 + 4*(6n-3) = 24n-6` incidences, hence Theta(n) reads/counter updates | also Omega(n), because an arbitrary reordered input must be read to certify that no face or incidence differs | A large mechanical cost is obtained only by making the prompt proportionally large; there is no short invariant route. |

For a concrete cap-compatible point, `n=10` already has 234 angle incidences. A full incidence witness therefore has at least 234 atomic entries; `n=11` has 258 and exceeds G9(c)'s 256-atom answer cap before vertex labels or coordinates are included. At `n=10`, the direct scan is only 234 incidence inspections (under roughly 500 read-and-count operations), while the summary route remains 4 operations. Raising `n` to force a million-operation scan also forces a million-item prompt/certificate and leaves the compact route at the same linear input-reading cost.

Exact geometric output does not create a useful Track B gap either. The Appendix already displays the defining equation and uniqueness interval. Asking for that equation is a direct transcription/formula task. Asking instead for a rational isolating interval for an algebraic transform of the angle makes root isolation the certificate-producing algorithm; the solver has no shorter route supplied by the paper, so this would be a calculator/root-isolation task rather than a structural-compression task.

## Gate summary

- **G:** passes for the count/AVC family by theorem-backed construction in Section 5.1.
- **H / Track A:** fails because the main classification theorem and Section 5.1 explicitly produce the answer on the generated distribution.
- **H / Track B:** fails because the mechanical route is either the same 4--6 operations as the compact route, or both routes require a linear scan of the explicit input. There is nothing structural to compress.
- **V:** passes for the count/AVC witness by exact integer recomputation. Full spherical coverage would require a substantially richer exact algebraic representation, but improving V cannot repair the failure of H.

No G9 or oracle-loop rejection is being claimed. The family was rejected at the required STEP 0 discriminating test, before code or hardening runs.
