# Rejected: no hard witness-search family supported by the paper

Paper: Ingo Czerwinski and Alexander Pott, [*On large Sidon sets*](https://arxiv.org/abs/2411.12911), arXiv:2411.12911v3.

## Decision

This paper does not support a problem family satisfying all of G, H, and V. The natural Sidon-set witness is generatable and exactly verifiable, but the scalable constructions in the paper are explicit, so the required search is not hard. I therefore stopped at Step 0 and did not create `gen_2411_12911.py`, fabricate gate results, or run `scripts/harden.py`.

| Requirement | Result | Evidence |
|---|---:|---|
| G - generatable | pass | Proposition 1.5 identifies the graph of any APN function with a Sidon set. Corollaries 3.5-3.6 construct further sets by an explicitly chosen affine-hyperplane intersection. |
| H - hard | **fail** | The paper proves constructions and bounds, not search hardness. Its scalable examples come from named, explicit APN functions; a solver can reproduce a standard construction without recovering a plant. |
| V - verifiable | pass | For a proposed set, check its required size and uniqueness of every XOR sum of two distinct elements. A repeated pair sum is exactly a forbidden four-distinct-elements relation after pairs sharing an element are excluded. |

## Why the proposed APN-graph generator fails H

Definition 1.1 says that a binary Sidon set is a subset of `F_2^t` with no four distinct elements whose XOR is zero. Proposition 1.5 then states that `F : F_2^n -> F_2^n` is APN exactly when its graph `{(x, F(x))}` is a Sidon set in `F_2^(2n)`. This makes inverse generation easy, but it also publishes the solution method.

The problem remains easy in the paper's odd-dimensional construction. Corollary 3.6 obtains a set in `F_2^(2n-1)` by intersecting an APN graph (or a translate) with a hyperplane selected by a maximum Walsh coefficient. Section 4 applies that recipe to known functions. In particular, Theorem 4.3 gives an infinite family from the explicit inverse function for odd `n`. A solver asked for *any* valid witness can ignore the seed and emit the same standard construction. Relabelling or affine-transforming the planted set does not change this: unless the required answer is artificially tied to a hidden plant, any standard Sidon set of the stated size is acceptable.

The strongest finite example cannot yield an unlimited scalable family either. Theorem 4.1 concerns `n = 8` only, and Table 1 prints a complete 192-element Sidon set in `F_2^15`. Section 4 reports only four affine-inequivalent outcomes from the four relevant CCZ-inequivalent APN functions. That regime is a finite lookup, not an expanding answer space.

Remark 4.2 identifies the tempting genuinely unknown regime: no infinite family of APN functions with linearity `2^(n-1)` is known, and nonexistence is also unproved. That regime therefore fails G: the generator cannot sample an unlimited supply of known witnesses there. Remark 4.5's Dobbertin formula is conditional on a Walsh-spectrum conjecture, so it is not a basis for verified generation either; the finitely computed cases again do not scale.

## Other formulations considered

- **Find a maximum Sidon set.** This asks for an optimum whose optimality is the claim, expressly forbidden by the task. The paper also says the maximum is unknown from dimension 11 onward.
- **Find the best hyperplane intersection.** If the function is supplied by its truth table, a Walsh-Hadamard transform computes all Walsh coefficients in polynomial time in the input-table length. If the function is supplied succinctly, recomputing the coefficient by exhaustive substitution is exponential in `n`, undermining cheap verification.
- **Find a large Sidon subset of a supplied candidate pool containing a plant and decoys.** This could be made to resemble hypergraph independent set, but it is not a family analyzed in this paper. The paper provides no worst-case hardness theorem, parameter regime, or planted-distribution hardness result for it. Adding such a pool would be a new unsupported problem rather than an instance generator justified by the paper.
- **Output a code from Section 5.** The parity-check columns are the nonzero elements of the explicitly constructed Sidon set, so this merely repackages the same easy construction.

## Full-text checks

I read the complete 17-page v3 paper, including Definitions 1.1 and 1.4; Propositions 1.2, 1.5, 3.2, and 3.3; Corollaries 3.4-3.9; all of Section 4 and Theorems 4.1, 4.3, and 4.4; the code correspondence and Theorem 5.1 in Section 5; and the summary/table in Section 6. The paper contains no computational-complexity theorem or identified hard search regime; searches of the full text found no occurrence of “complexity,” “algorithm,” “NP,” “hard,” or “polynomial.”

The rejection is specifically an H failure, not a claim that Sidon-set research is mathematically easy. Determining extremal sizes may be open and difficult, but an open optimum problem is not the required efficiently checkable witness-search family.
