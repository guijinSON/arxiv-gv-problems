# Rejected: arXiv:1404.6800

Paper: Tao Feng, Xiaomiao Wang, and Ruizhong Wei, “Semi-cyclic holey group divisible designs with block size three and applications to sampling designs and optical orthogonal codes” ([arXiv:1404.6800](https://arxiv.org/abs/1404.6800)).

## Decision

No generator is shipped. The paper's native family can satisfy **G** and **V**, but it fails **H on Track A**, and it also fails the distinct **Track B** test. This is not a G9 or answer-cap rejection.

## Step 0 findings

Section 1 defines a `3-SCHGDD` of type `(n,m^t)` on `I_n x Z_(mt)`. A native finite witness is its set of base blocks. Developing every base block by the common cyclic shift must give triples that contain no pair from one group or one hole and cover every other point-pair exactly once. Equivalently, the directed difference multisets between each two groups must each be `Z_(mt) \ S`. This is exactly and cheaply checkable from the blocks.

The same section counts the required base blocks:

`B = (t-1)n(n-1)m/6`.

The certificate-producing method is not a hard search algorithm. Sections 2–4 give constructive recursions (Constructions 2.3 and 2.9–2.11), displayed parametric block lists (for example Lemmas 3.1, 3.3, 3.5, 3.8, and 4.8), and the explicit quasi-skew-starter formulas in Lemmas 4.2–4.3. Theorem 4.12 then classifies the settled existence regimes by congruences and a short exception list. Section 5 constructs the sampling plans and optical orthogonal codes by unions of those already-constructed block sets (Theorems 5.3 and 5.8).

Thus a positive certificate in every theorem-backed regime is produced in `Theta(B)` time by emitting the displayed or recursively composed blocks. The existence answer itself is even easier: in Theorem 4.12's settled regimes it is obtained by a constant number of comparisons, modular tests, and exception checks. A bare yes/no answer would also violate the witness rule because the theorem is not an executable certificate; supplying the actual blocks restores V but exposes the direct constructor.

## Why Track A fails

Track A would require a distribution for which no efficient general method is known. Here the paper's own method constructs the witness directly in time linear in its output size. It is the required domain-standard attack, and it succeeds on every generated instance in the cited regimes. The paper proves existence/classification results, not computational hardness for a search distribution.

Adding a large list of decoy triples and asking for an exact-cover subset could manufacture a hard-looking benchmark, but no theorem or reduction in this paper licenses that distribution. It would be `reduction_kind="convenience"` and `domain_essentiality="discretised_analogue"`, not native coverage of this paper.

## Why Track B also fails: mechanical cost versus compact route

The most favorable small native family is the odd-`t` case `n=3, m=1` covered by Lemma 1.3(1). In the difference coordinates of Section 1, for every nonzero `a in Z_t`,

`{(0,0), (1,a), (2,2a mod t)}`

is a base block. The three directed difference lists are permutations of the nonzero residues, so these `t-1` blocks are a complete witness by direct substitution.

For a concrete cap-compliant would-be shipping size `t=71`:

| quantity | measured/countable value |
|---|---:|
| base blocks | 70 |
| point IDs in the answer | 210 |
| compact JSON characters (points encoded as `group*t + coordinate`) | 813 |
| mechanical constructor cost | 280 elementary operations: one doubling, one modular reduction, and two point-ID offsets per block |
| compact route cost | the same 70 formula evaluations, at most the same 280 elementary operations |

The cost ratio is therefore 1, up to constant bookkeeping. There is no shorter invariant or change of variables hiding behind an expensive standard method: the displayed/difference construction **is** the shortcut, and a solver must still emit all 70 blocks. At `t=83` the same representation already takes 246 point IDs and about 328 operations; further scaling only grows the witness and never creates a mechanical-versus-compact gap. Other constructions in Sections 3–5 have the same output-linear character.

A compressed answer consisting only of the multiplier `2` does not rescue the family. Among affine maps `a -> c*a` over odd prime `t`, every `c` except `0` and `1` gives the same kind of complete mapping, so a random admissible coefficient succeeds with probability `(t-2)/t` (69/71 at the measured size), catastrophically failing G4. Adding interpolation constraints to select a secret coefficient would be an external puzzle, not a problem supplied by the paper.

## Failed gate

- **G:** passable by theorem-backed construction or composition of the paper's identities.
- **V:** passable by exact difference-multiset comparison and group/hole checks.
- **H / Track A:** fails because the paper supplies an output-linear certificate constructor for the generated regimes.
- **H / Track B:** fails because the mechanical method and compact route are the same `Theta(B)` construction (280 versus at most 280 operations at the cap-compliant measured size).

The correct outcome is rejection before module construction.
