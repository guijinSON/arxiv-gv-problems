# Rejected at Step 0: the paper classifies and explicitly constructs the certificates

Paper: Mark Pankov, [*Symmetric \((2^k-1,2^{k-1},2^{k-2})\)-designs
which are \((2^{k-1}-1)\)-pyramidal over abelian groups*](https://arxiv.org/abs/2508.16963),
arXiv:2508.16963v1 (2025).

## Decision

No generator is shipped. I read the complete ten-page paper, including the exact
design definition in Section 2, the sum construction and its automorphisms in
Section 3, and Theorem 6 with its proof in Sections 4--5. The prior-triage idea
is generatable and exactly verifiable, but it fails **H on both tracks**.

- **Track A fails H.** The paper proves no worst-case, average-case, or
  distributional hardness result. Its native construction is an explicit union
  and complement formula (Example 2), while the canonical projective example is
  emitted directly from binary dot products. A generator based on either formula
  gives the solver the same polynomial-time construction.
- **Track B also fails H.** For a full incidence certificate, the standard
  simplex-code algorithm and the purported compact route are the same XOR-span
  construction. For a compressed generator-matrix certificate they are again
  the same short periodic-row formula. Randomly relabelling points can hide that
  formula, but it also removes the solver-visible compact route; the generator's
  private relabelling is not an insight.

This is an H rejection, not a witness-rule rejection. Incidence rows, a binary
simplex generator matrix, a center block, or explicit point permutations are all
finite objects that can be checked exactly. The problem is that the faithful
ones are either constructed directly, are readily read from supplied action
data, or have no paper-backed short route once hidden.

Steps 1--4 were intentionally not run. In particular, no generator,
`selftest_report.json`, README, or oracle transcript was fabricated after the
Step-0 failure.

## What the paper actually proves

Section 2 defines a symmetric `(v,k,lambda)` design as `v` points together with
`v` distinct `k`-point blocks, every two distinct blocks meeting in exactly
`lambda` points. For the paper,

```
v = 2^k - 1,        block size = 2^(k-1),
lambda = 2^(k-2),   k >= 3.
```

The same section identifies the projective example: on the nonzero vectors
`x` of `F_2^k`, its blocks are the hyperplane complements

```
B_a = {x != 0 : a dot x = 1},       a != 0.
```

These incidence vectors are precisely the nonzero words of a binary simplex
code. Their weights and pairwise intersections are checked by bit counts.

Section 3 defines a center block `O` by closure under symmetric difference:
`O XOR B` must be another block for every `B != O`. Example 2 gives the native
sum construction. Given smaller symmetric designs `D_O` and `D_Z` and any
bijection `delta` between their block sets, the larger blocks are

```
O,
X union delta(X),
X union (O \ delta(X))                 for every block X of D_O.
```

Thus producing the larger design from its components is a single pass of exact
set unions and complements. Proposition 3 handles the projective component;
the proof explicitly constructs the involutions. Proposition 4 shows that the
resulting elementary abelian group is independent of the selected `Z`.

Theorem 6 is a classification, not a hardness theorem. If a symmetric design is
`(2^(k-1)-1)`-pyramidal over an abelian group `G`, the complement `O` of the
fixed-point set is a center block, the design has exactly the Section 3 sum
form, and `G` is the elementary abelian group `C_2^(k-1)`. Lemma 8 derives the
center block and Lemma 9 derives the group type. For `k=2`, Remark 7 says the
statement is trivial; Section 2 also notes that the relevant designs for
`k in {2,3}` are all the projective example.

## Step-0 mechanical cost versus compact route

I quantified the most favorable faithful Track-B proposal: ask for the full
projective design and pyramidal action, encoding each incidence row as one
integer bitmask. At `k=6`, the answer has 63 block masks and five generator
parameters. Compact JSON occupies **1,286 characters and 68 atomic elements**,
so it fits the output cap. `k=7` already takes **5,029 characters**, and `k=8`
takes **19,845 characters and 262 atoms**. Hence `k=6` is the largest rung of
this representation that can ship.

At `k=6`, direct evaluation of every displayed dot product makes
`63^2 = 3,969` membership tests, or at most `6*63^2 = 23,814` coordinate-level
bit operations. On this host, a standard-library Python implementation averaged
**0.000162899 seconds** per construction over 20,000 repetitions.

That is not the honest Track-B reference algorithm, however. The nonzero block
rows are an XOR span of six coordinate rows. After those periodic rows are
formed, Gray-code order emits all 63 nonzero words with exactly **62 word XORs**;
forming the rows by a plain scan adds `6*63 = 378` bit inspections, while their
periodic patterns admit the same closed word construction a human would use.
The measured implementation averaged **0.000016492 seconds** per construction
over 20,000 repetitions.

The comparison is therefore:

| Candidate | Strongest mechanical route at the largest shippable size | Compact route after the insight | Result |
|---|---:|---:|---|
| Full 63-block projective incidence certificate (`k=6`) | Six simplex rows followed by 62 Gray-code XORs; 0.000016492 s | **The same six rows and the same XOR closure** | Track B fails: route ratio 1 |
| Six-row simplex generator matrix only | Emit six periodic coordinate masks | **The identical periodic-mask formula** | Track B fails: already directly executable |
| Example 2 sum from `D_O`, `D_Z`, and `delta` | One union and one relative complement per component block, `Theta(2^k)` set operations | **The identical displayed formula** | Track B fails: route ratio 1 |
| Recover `O` when the abelian action is supplied | Take the complement of the common fixed-point set, as in Theorem 6 | **The identical support/fixed-point scan** | Track B fails: route ratio 1 |

Quoting the 3,969-test dot-product loop as the mechanical cost and the XOR span
as a separate compact route would be misleading: XOR-span generation is the
domain-standard simplex-code algorithm and must itself be the reference
algorithm. Once that correction is made, there is nothing to compress.

## Other native witness tasks considered

| Candidate task | Failure | Reason |
|---|---|---|
| Construct a pyramidal symmetric design | H on A and B | The projective dot-product formula and Example 2 directly emit it; the optimized mechanical algorithm is already the compact XOR/union construction. |
| Output a simplex-code generator matrix | H | The coordinate-evaluation rows are an explicit periodic matrix formula. Making the point labels random hides the formula but supplies no public shorter route. |
| Find the center block in the projective example | G4 and H | Every block is a center block in the maximal singular/projective example, so sampling any displayed block succeeds. |
| Find the center block in a generic Example 2 sum | H unsupported | Symmetric-difference closure tests candidates in polynomial time. The paper proves no hardness for the random-`delta` distribution, and it gives no compact alternative to that scan. If the action is supplied, `O` is simply the moved orbit. |
| Decompose a design when `O` is known | H | Section 3 obtains `D_O`, `D_Z`, and `delta_Z` by intersections with `O` and its complement; these are direct set operations. |
| Return the abstract pyramidal group | G4/H | Theorem 6 and Lemma 9 say it is always `C_2^(k-1)`, so the abstract answer is a lookup. A basis of an already supplied action is found by elementary binary linear algebra. |
| Certify nonexistence over a non-elementary abelian group | Witness rule / G4 | Theorem 6 proves the negative, but the group type or a higher-order element is not by itself an executable refutation of every possible design; citing the theorem is not a checker certificate. A yes/no answer is also guessable. |
| Recover an action from an incidence design after a private random relabelling | Track A unsupported; Track B has no compact route | This is a design/graph-automorphism or isomorphism problem introduced by the benchmark. The paper supplies neither distributional hardness nor a solver-visible shortcut for it. |
| Return a point relabelling between two planted isomorphic copies | Track A unsupported | This is an inverse-generated isomorphism puzzle, not the classification theorem's native search problem; random highly structured projective copies also have many automorphisms. |

The center-block option also cannot be rescued merely by a large nominal search
space. In the projective family its structure-aware success probability is 1,
because every input block works. If a random sum happened to have a unique
center, choosing among its `v` displayed blocks would have probability `1/v`;
passing `10^-6` by cardinality alone would require over a million displayed
blocks, far beyond the no-tool setting, while still providing no hardness
theorem.

## Easy regimes and scaling obstruction

The paper's easy mechanisms are its main results:

- Section 2 supplies the binary-projective/simplex construction and says the
  `k=2,3` designs are all of this type.
- Example 2 constructs every proposed sum by a direct formula from two smaller
  designs and a bijection.
- Propositions 3--4 explicitly produce the elementary abelian automorphisms in
  the projective-component case.
- Theorem 6 and Lemmas 8--9 classify every abelian pyramidal action under study.

Increasing `k` only lengthens an explicitly produced incidence object. With the
full native certificate, the next rung after the 1,286-character `k=6` answer is
already 5,029 characters. Compressing to a code basis keeps the answer short but
makes the public closed formula even more immediate. Neither axis yields a hard
Track-B question.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- certificate known by construction | Pass in isolation | Section 2's hyperplane complements or Example 2's sum formula |
| H -- Track A structural hardness | **Fail** | No computational/distributional hardness theorem; all natural generated certificates have explicit polynomial-time constructions |
| H -- Track B no-tool compression | **Fail** | The strongest mechanical algorithms are exactly the proposed XOR, union/complement, or fixed-point compact routes |
| V -- exact witness checking | Pass in isolation | Exact block sizes, pair intersections, symmetric differences, bit-span membership, and permutation action checks |
| G4 for center-block search | **Fail in the canonical family** | Every projective block is a center block; a structure-aware displayed-block sample succeeds with probability 1 |
| G9(c) for full-design scaling | **Fail beyond `k=6`** | `k=7` needs 5,029 serialized characters; `k=8` needs 262 atoms |
| Overall | **Rejected at Step 0** | No paper-backed family satisfies G, H, and V simultaneously on either track |

The prior triage was correct that abelian actions with fixed points give a clean
generator and verifier. It was not correct that this yields a hard witness
family: the action and design are precisely what Sections 2--5 construct and
classify explicitly.
