# Rejected after full-text triage

Paper: Mario Galici and Alessandro Montinaro, [*The Flag-Transitive and Point-Imprimitive Symmetric \((v,k,\lambda)\) Designs with \(v<100\)*](https://arxiv.org/abs/2510.25360), arXiv:2510.25360v1.

## Decision

No self-contained generator is shipped. The paper fails **G (scalable generatability/diversity)** and **H on both Track A and Track B** for the native problems it actually studies. Exact verification of a supplied incidence structure, difference set, or permutation-group action would satisfy V, but that does not repair G or H.

This is not a rejection merely because an algorithm exists. It is a bounded classification: Theorem 1.1 and Corollary 1.2 explicitly classify the entire promised universe with \(v<100\). Table 1 contains only 11 rows and 12 design isomorphism classes. The only new native construction, Lemma 2.1 and Example 2.2, is fixed at \(v=64\); Table 2 prints the nine permutation generators and both 28-point base blocks explicitly.

## Step-0 findings

- **Exact definition.** Section 1 defines a nontrivial symmetric \(2\)-\((v,k,\lambda)\) design and flag-transitive, point-imprimitive automorphism groups. Theorem 3.2 (Camina--Zieschang) decomposes such a design relative to an invariant partition into the induced designs \(\mathcal D_0\) and \(\mathcal D_1\).
- **Parameter regime.** Theorem 1.1 assumes \(v<100\), not an asymptotic parameter regime. Proposition 4.1 reduces the symmetric cases to a finite table, and Theorems 4.3 and 4.10 complete the identification.
- **What makes it easy.** Corollary 1.2 says the promised designs are known completely. Cases with \(\lambda\le 10\) are imported from earlier classifications; Section 5 supplies further small-degree classification lemmas; the remaining \((63,32,16)\) case is identified as \(\overline{PG_5(2)}\) in Lemma 4.4, and the \((64,28,12)\) cases are finished in Theorem 4.10.
- **What produces the certificate.** For the new designs, Section 2 constructs the two block orbits directly and Table 2 gives concrete generators and base blocks. For the residual classification, the proof of Proposition 4.9 describes the GAP/DESIGN search: enumerate degree-64 coset actions, subgroup orbits of length 28, and test the resulting designs up to isomorphism. In its \(e=11\) branch it explicitly searches 1,395 candidate 8-subspaces over each of two 5-subspaces before retaining three conjugacy classes. These are finite classification/construction procedures, not evidence of an asymptotically hard generated distribution.

## Why Track A fails

There is no growing native distribution covered by a hardness theorem in the paper. Under the paper's promise, classification has at most 12 possible isomorphism-class answers (under four bits of entropy), and a parameter-only version has only six distinct \((v,k,\lambda)\) triples. A lookup or comparison against Theorem 1.1 is therefore the domain-standard attack and succeeds.

Randomly relabelling either 64-point construction does not fix this. Every such instance has the same canonical key as its source design. It gives arbitrarily many labelled encodings of at most two objects, not an unlimited supply of structurally distinct instances; it also cannot satisfy G7's size-doubling requirement. Enlarging to arbitrary projective spaces, arbitrary McFarland difference sets, or unrelated hidden-isomorphism instances would require a theorem and hardness regime not established in this paper, so doing that would turn the result into an external or convenience analogue.

## Why Track B also fails

Two plausible native tasks were costed before rejection:

| proposed task | mechanical cost at the largest paper setting | compact route | result |
|---|---:|---:|---|
| identify a promised design from the paper | compare with at most 12 rows/classes in Theorem 1.1 | the same at most 12 comparisons | no compression gap; tiny answer space |
| output a Section 2 base block for either new design | read/copy the 28 entries printed in Table 2 (or develop its orbit into 64 blocks) | the same 28 reads/copies | explicit answer, no hidden invariant |

The more elaborate GAP route in Proposition 4.9 has a mechanical branch of \(2\times1395=2790\) subspace candidates (plus finite orbit/isomorphism tests), but it still concerns one fixed 64-point classification. Its proof shortcut is not a short executable witness: it invokes the Atlas, the Perfect Groups library, conjugacy-class facts, and GAP computations. Consequently it does not yield a <=300-operation compact route that a checker can validate from the instance alone. At the opposite extreme, asking only for the final class reduces the answer to one of 12 table entries. Thus Track B offers either no meaningful compression gap or no executable witness.

## Gate summary

| gate | outcome | reason |
|---|---|---|
| G | fail | Native constructions have fixed sizes (chiefly 63, 64, or 96 points); relabellings collapse canonically and cannot size-double. |
| H, Track A | fail | Theorem 1.1 is a complete 12-class lookup for the promised universe; no distributional hardness claim or growing regime exists. |
| H, Track B | fail | Lookup costs <=12 comparisons versus <=12 for the compact route; printed base blocks cost 28 reads versus 28. The 2790-candidate GAP branch has no short instance-checkable route and still cannot scale. |
| V | pass in isolation | Incidence counts, difference multiplicities, and claimed permutations can all be checked exactly, but V alone is insufficient. |

No module was written, so there is no rejected generator to retain. The rejection occurs at Step 0, before implementation or oracle hardening.
