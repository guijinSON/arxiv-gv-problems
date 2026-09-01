# Rejected: arXiv 2306.09948

Paper: [Constructing generalized Heffter arrays via near alternating sign matrices](https://arxiv.org/abs/2306.09948), Lorenzo Mella and Tommaso Traetta, arXiv:2306.09948v2.

## Decision

The natural witness family suggested by the paper—construct a (simple, zero-sum or nonzero-sum) generalized Heffter array with prescribed parameters—fails gate **H (hardness)**. It is generatable and exactly verifiable, but the paper's contribution is a collection of direct constructions and an explicit algorithm for precisely the parameter regimes in which existence is proved. Shipping those regimes would turn the task into reproducing a formula or algorithm from the paper, not a hard search problem.

No generator, self-test report, or oracle transcript was produced. This follows the task's Step 0 instruction to stop when a family fails G, H, or V; an LLM hardening run cannot establish computational hardness against a construction already supplied by the source paper.

## Exact definition checked

Definition 1.1 defines a GHA over a group as an `m x n` array whose nonzero entries have prescribed row and column weights and whose absolute-value multiset covers every noninvolution of `S` exactly `lambda` times and every involution exactly `lambda/2` times. Definitions 1.3 and 1.6 add the zero/nonzero row-and-column sum and simplicity conditions. Simplicity means that every proper consecutive run in every chosen row and column ordering has nonzero group sum, equivalently that the relevant partial sums are distinct (with the stated zero-sum exception).

These conditions would make verification cheap and exact: count weights and multiplicities, recompute group sums, and compare all partial sums. Thus V is not the problem.

## Why the proposed search is easy in the paper's regimes

The full paper gives the witness construction rather than merely proving existence:

- **Section 3, Theorem 3.6** proves that a uniform `NASM(m,n;h,k)` exists exactly when `mh = nk` and gives an entrywise formula for a base matrix followed by a block repetition/sign pattern. This is a closed-form construction.
- **Section 3, Theorem 3.8** constructs the stated nonuniform even-weight NASMs by taking a binary matrix with prescribed margins and replacing every 0 and 1 by fixed `2 x 2` blocks. The needed binary support is covered by the Gale–Ryser criterion in Theorem 1.2 and standard constructive margin algorithms.
- **Section 4, Theorem 4.3** converts any NASM into a nonzero-sum, naturally simple GHA over a cyclic group by placing the ordered elements of `S` in the NASM support and applying its signs. Lemma 4.1 proves simplicity and nonzero sums for this construction.
- **Section 4, Theorem 4.4** gives the corresponding explicit filling/doubling construction for zero-sum simple GHAs. Corollary 4.6 and Theorem 1.8 specialize it to the advertised infinite cyclic-group families, including the rectangular classic Heffter arrays.
- **Section 5, Theorem 5.2** explicitly describes an algorithm for constructing nonzero-sum naturally ordered GHAs over an arbitrary group when enough noninvolutions are present. Its proof specifies how to fill ordinary cells, isolated vertices, forest branches, and maximal paths while avoiding at most one or two forbidden values. The conclusion reiterates that Section 5 “provided an algorithm.”
- Theorems 6.5–6.10 and 7.4 then deterministically transform a supplied array/order into graph decompositions or a biembedding. Using those downstream objects as witnesses does not recover hardness.

The paper itself calls the zero-sum case “much harder,” but that phrase describes the mathematical construction problem relative to the nonzero-sum case; it is followed by an explicit construction. It is not a computational-hardness result.

## Other possible families considered

Finding compatible row/column orderings (Section 7) is verifiable, and answer-first generation could plant such orderings. However, this paper supplies no computational-hardness theorem or hard parameter regime for that search problem. Inventing a completion puzzle around the definition would therefore lack the required evidence for H and would no longer be justified by the paper's results.

The conclusions propose future variants and constant-period GHAs, but these are open construction directions rather than established hard witness families. They cannot support a generator that always knows a witness while making an honest hardness claim.

## Gate summary

| Gate | Result | Reason |
|---|---:|---|
| G — generatable | Pass in principle | The paper's formulas and algorithms construct witnesses directly. |
| H — hard | **Fail** | The same formulas and algorithms give polynomial-size direct constructions in the proved regimes; no hardness regime is established. |
| V — verifiable | Pass in principle | All array, sum, multiplicity, ordering, and partial-sum conditions are finite exact checks. |

Because all three gates are mandatory, the paper is rejected.
