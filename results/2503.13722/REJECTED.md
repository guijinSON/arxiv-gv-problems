# Rejection: arXiv 2503.13722

Paper: [S. Rukavina and V. D. Tonchev, *Symmetric 2-(35,17,8) designs with an automorphism of order 2*](https://arxiv.org/abs/2503.13722)

## Decision

No generator is shipped. The prior triage suggestion—relabel a known design together with a known involution—passes G and V, but fails H on both tracks and also fails the required scaling and canonical-diversity gates. The paper's genuinely difficult classification question fails V: its completeness claim has no cheaply executable witness in the paper.

## What the paper actually establishes

Section 2 defines an orbit matrix by equations (1) and (2). The classification procedure is explicitly computational:

1. enumerate possible order-two actions;
2. construct orbit matrices satisfying (1) and (2);
3. expand them to 0/1 incidence matrices by Janko's indexing method; and
4. use GAP and the DESIGN package for automorphism groups and isomorphism rejection.

Table 2 reports 18,894 orbit matrices in total. Expansion and within-action isomorphism rejection produce 11,670,332 listed designs before the final cross-action de-duplication, and Theorem 2.2 reports 11,642,495 isomorphism classes. These are all for the single fixed parameter set 2-(35,17,8); the theorem supplies no growing parameter regime and no distributional hardness result.

Lemma 2.1 gives nonexistence only for the two fixed cases with 13 or 17 fixed points. Its proof says that the bounded row incompatibilities are “easy to check,” but does not provide an executable refutation certificate. Even if formalized, these would be only two canonical instances, not a scalable family.

Section 3 gives the only general construction in the paper: the direct extension of a 2-(4t-1,2t-1,t-1) design to a Hadamard 3-design by adjoining one point and complementary blocks. That formula is an easy transformation, not a hard search problem, and it does not construct a growing family of input 2-designs with involutions.

## Gate analysis

### G — generatable

The relabelling proposal is generatable. Starting from a stored incidence matrix `D`, a stored involution `sigma`, and a sampled point permutation `pi`, the generator can carry the certificate as `pi sigma pi^-1`. Verification can exactly check that the proposed permutation is nonidentity, squares to the identity, and maps every block of `D` to a block.

This route does not require solving the generated instance, so G itself is not the reason for rejection.

### H — hardness

**Track A fails.** Theorem 2.2 concerns exhaustive classification at one fixed size; it is not a hardness theorem for a generated distribution. Relabellings of one known design are all the same instance up to point and block renaming. Consequently, 20 seeds would produce one canonical key rather than 20 distinct keys, and increasing `n` cannot make the native 2-(35,17,8) object larger. A task that asks for any valid design can be answered by the same stored design every time. A task that supplies the relabelled design and asks for its involution merely turns label hiding into a graph-automorphism instance, with no Track-A evidence for this one-isomorphism-class distribution.

**Track B also fails.** There are two possible ways to expose the relabelling, and neither creates the required compression gap:

- If `pi` is part of the instance, the mechanical certificate algorithm is exactly the compact route: build the inverse table and evaluate `pi[sigma[pi_inv[y]]]` for each of 35 labels. There is no shorter insight hidden from the solver.
- If `pi` is not exposed, the solver must recover an automorphism of the 70-vertex bipartite incidence graph. No compact route is supplied by Section 2; arbitrary relabelling erases the coordinate description. The only route is the mechanical graph-automorphism/isomorphism work that Track B was supposed to compress.

The certificate-production cost was measured for the exposed-map version. Building the inverse table takes 35 writes and evaluating the conjugate takes 35 more, so both the mechanical method and the purported compact route use the same 70 coarse table writes: the gap is 1:1. A CPython microbenchmark took 2.483170 seconds for 200,000 certificates, or 12.42 microseconds per instance. The permutation witness itself has only 35 atoms and fits G9(c); answer length is not the obstacle. If instead the task asks the solver to output the whole relabelled design as its witness, the 35 blocks contain 595 point labels and exceed the 256-atom answer cap without creating a shorter route.

For comparison, the paper's classification route has a very large mechanical cost—at least 18,894 orbit matrices and 11,670,332 per-action design representatives—but there is no compact route at all. Asking for the final number 11,642,495 makes the answer a classification-table lookup, while asking the solver to establish completeness makes the checker rerun research-level enumeration and isomorphism rejection.

### V — verification

V passes only for a single design/involution witness: block sizes, pair incidences, involution order, and block preservation are all exactly checkable.

V fails for the paper's substantive result, namely completeness of the classification. A list of examples proves existence but not that no omitted isomorphism class exists. The integer 11,642,495 is not a witness. The paper offers no bounded refutation, canonical-generation trace, or other certificate whose local inspection establishes completeness without repeating orbit-matrix expansion and isomorphism classification.

## Why obvious repairs do not produce a paper-native family

- Taking disjoint unions to grow `n` destroys the 2-design condition: cross-component point pairs occur in zero blocks rather than in exactly eight.
- Orbit-matrix completion remains fixed-dimensional: the allowed involutions give only 19 through 25 point orbits. Hiding entries or duplicating candidate rows can enlarge a generic puzzle, but it does not enlarge a native parameter from the paper.
- Adding decoy rows or candidate automorphisms turns the task into a generic subset/clique or needle-in-a-haystack puzzle. That construction is not in the paper, has no distributional hardness theorem, and supplies no short structural route for Track B.
- Importing a separate Paley/Hadamard construction to vary `t` would rely on an external theorem. Section 3 only explains extension and derivation; it does not guarantee the needed scalable source designs or the required involutions.
- Embedding the authors' roughly 30 MB orbit-matrix tables would remain a finite fixed-parameter lookup and would not repair G7, G8, or either hardness claim.

Thus the native options divide cleanly: locally checkable single-design witnesses are generatable but not hard or scalable, while the hard-looking exhaustive classification has no cheap witness. No one-family module can satisfy G, H, and V for this paper without introducing a convenience benchmark that discards the paper's actual result.
