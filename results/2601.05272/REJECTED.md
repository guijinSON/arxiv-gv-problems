# Rejected at Step 0: no defensible hard, scalable family

Paper: [A Rank 23 Algorithm for Multiplying 3 x 3 Matrices with an Arithmetic Complexity of 59](https://arxiv.org/abs/2601.05272), arXiv:2601.05272v1.

I read the complete paper and its LaTeX source, not only the abstract. The paper has one substantive section (Section 1), two displayed versions of a single algorithm (Tables 1 and 2), and the same fixed algorithm in machine-readable form (Appendix A / Table 3). It contains no hardness theorem, no parameterized family of search instances, and no scalable parameter regime. Although the source declares a theorem environment, it never states a theorem. Section 1 instead says that the technical details of the search method and the implications will appear in a future publication.

## G/H/V assessment

| Requirement | Assessment | Reason |
|---|---|---|
| G — generatable | Only for an unsupported generalization | The paper supplies one fixed decomposition of the fixed 3-by-3 matrix-multiplication tensor. Randomly changing coordinates or permuting terms produces isomorphic copies, not an unlimited supply of genuinely new problems. Sampling arbitrary rank-one summands first would generate arbitrary tensors, but that is a new tensor-decomposition family not defined or analyzed by this paper. |
| H — hard | **Fail** | For the actual object in the paper, Tables 1 and 3 publicly give a witness. Coordinate permutations and other known relabellings can be applied directly to that witness. Direct sums merely repeat known components. The paper proves neither worst-case nor average-case hardness of recovering a decomposition, and identifies no regime in which recovery is hard. |
| V — verifiable | Pass in principle | A proposed bilinear decomposition can be expanded and its integer coefficients compared exactly with the matrix-multiplication tensor. This does not rescue the missing hardness and scaling properties. |

## Why the inverse-construction hypothesis is not enough

The proposed approach—sample a hidden bilinear decomposition and publish the tensor obtained by expanding it—would give a planted witness and an exact checker. However, the generated target would generally not be a matrix-multiplication tensor, so the construction leaves the problem studied in the paper. The paper provides no constraints on dimensions, rank, coefficient field, sparsity, or overcompleteness that would avoid known easy tensor-decomposition regimes or justify an H claim. Choosing those parameters here would be inventing an unrelated hardness assumption.

Keeping the target as the 3-by-3 multiplication tensor does not work either:

- it is fixed-size, so increasing `n` cannot increase difficulty (G7 fails);
- its rank-23 witness is printed in the paper, so the search is a lookup;
- term permutations, coefficient rescalings, and coordinate relabellings yield equivalent witnesses/instances rather than structural diversity (G8 would collapse them);
- block/direct-sum scaling exposes independent copies whose known decompositions concatenate immediately.

## Decision

Rejected before implementation, as required by Step 0. No generator, fabricated gate report, or oracle transcript was produced. Running the hardening loop would not repair the missing problem-family definition or hardness regime.
